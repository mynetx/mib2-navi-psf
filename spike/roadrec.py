#!/usr/bin/env python3
"""Straßenrecords eines _Basic-Blocks dekodieren (§6j).

    u16 X │ u16 Y │ Deltabytes │ 00 │ 03 │ Name (UTF-8) │ 00

X, Y absolut, relativ zur Kachelecke aus dem Blockkopf, in Einheiten des
Bandquantums (§6i: L11 Band 1,2M = 18 m, L10 = 38 m).
Je Stützpunkt EIN Byte: hohes Nibbel = dy, niedriges = dx, beide 4-bit
Zweierkomplement (−8..+7). 0x00 beendet die Geometrie.
"""
import lzma, struct, math
R=6371000.0
QUANT={0x3392334:18.0, 0x346c45e:18.0, 0x2f4009f:38.0, 0x2f34830:38.0}
tc=lambda v: v-16 if v>=8 else v

def block(psf,P):
    d=open(psf,'rb').read()
    return lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[P:])

def decode(raw, o):
    """Record ab Offset o -> (Punkte in Einheiten, Name) oder None."""
    if o+4>len(raw): return None
    x,y=struct.unpack_from('<HH',raw,o)
    pts=[(x,y)]; i=o+4
    while i<len(raw) and raw[i]!=0:
        dy,dx=tc(raw[i]>>4),tc(raw[i]&15)
        x+=dx; y+=dy; pts.append((x,y)); i+=1
    if i+1>=len(raw) or raw[i+1]!=3: return None      # 00 03 erwartet
    e=raw.find(b'\0',i+2)
    if e<0 or e-(i+2)>60: return None
    return pts, raw[i+2:e].decode('utf-8','replace')

def to_wgs84(pts,X0,Y0,s):
    out=[]
    for a,b in pts:
        x=X0+a*s; y=Y0+b*s
        out.append((math.degrees(2*math.atan(math.exp(y/R))-math.pi/2),
                    math.degrees(x/R)))
    return out

def parse_section(raw, start, W, H, tol=1):
    """Sequentiell ab `start` alle Straßenrecords lesen.

    `tol` ist die Randtoleranz in Kacheleinheiten. Sie muss >0 sein: Straßen am
    Kachelrand ragen legitim darueber hinaus, und ein hartes 0<=x<=W verwirft
    sie. Genau das hat Testorts `Hauptstraße` und `Nachbarorter Straße`
    unsichtbar gemacht -- Testort liegt 108 m vor der Ostgrenze der Kachel.
    tol=1 genuegt und saettigt sofort (B 38->41, C 31->32, L10 119->119;
    ±2 bis ±32 finden nichts mehr), ist also kein Aufweichen des Kriteriums.

    Zwischen zwei Records stehen 7 B:  01 <v> 00 | 80 11 <v-1> 00
    Der Anker ist  01 <n> <f>  direkt vor X,Y.  `n` ist IMMER die exakte Zahl
    der Deltabytes (gemessen: nd-n == 0 bei allen 38 Records mit f=0x00).
    Sequentiell lesen statt Muster suchen hebt die Trefferquote von 31 % auf 90 %.

    Bei f=0x10 stehen hinter den Deltas noch 1-5 Zusatzbytes vor dem `00 03`,
    die fast immer auf 0x01 enden. Diese Records erreichen nur 48,9 % gegen
    OSM statt 89,4 % -- ihre Geometrie ist noch nicht vollstaendig verstanden
    (FINDINGS 6j).
    """
    out=[]; i=start
    while i < len(raw)-10:
        if raw[i]!=1: i+=1; continue
        n=raw[i+1]; f=raw[i+2]
        if n<1 or n>120: i+=1; continue
        x,y=struct.unpack_from('<HH',raw,i+3)
        if not (-tol<=x<=W+tol and -tol<=y<=H+tol): i+=1; continue
        nd = n
        a,b=x,y; pts=[(x,y)]; ok=True
        for k in range(nd):
            if i+7+k >= len(raw): ok=False; break
            by=raw[i+7+k]; a+=tc(by&15); b+=tc(by>>4)
            if not (-tol<=a<=W+tol and -tol<=b<=H+tol): ok=False; break
            pts.append((a,b))
        j=i+7+nd
        if not ok or j+1>=len(raw) or raw[j]!=0 or raw[j+1]!=3: i+=1; continue
        e=raw.find(b'\0',j+2,j+2+60)
        if e<0: i+=1; continue
        nm=raw[j+2:e].decode('utf-8','replace')
        if not nm: i+=1; continue
        out.append(dict(offset=i, n=n, flags=f, points=pts, name=nm, end=e+1))
        i=e+1
    return out

if __name__=='__main__':
    import sys
    PSF=sys.argv[1] if len(sys.argv)>1 else \
        '../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
    P=0x3392334; raw=block(PSF,P)
    X0,Y0,_,_=struct.unpack_from('<4i',raw,0); s=QUANT[P]
    found=0
    for o in range(len(raw)-6):
        r=decode(raw,o)
        if r and len(r[0])>=3 and r[1] and r[1][0].isupper():
            found+=1
            if found<=8:
                pts,nm=r
                w=to_wgs84(pts[:3],X0,Y0,s)
                print(f"@{o:6d} {len(pts):3d} Punkte  {nm[:32]:32s} "
                      f"{w[0][0]:.5f},{w[0][1]:.5f} …")
    print(f"\n{found} Records mit >=3 Punkten und großgeschriebenem Namen")
