#!/usr/bin/env python3
"""Bit-gepackte Deltas der Strassenrecords suchen.

Feste Breiten auf Byte-/Nibbelgrenze sind ausgeschlossen (§6j). Hier: fester
Bitbreiten-Strom, gesucht ueber Breite w, Startbitversatz und Vorzeichenform.

Bewertung schaerfer als beim ersten Versuch:
  - nur Punkte zaehlen, die >=MINDIST Einheiten vom Start weg sind
    (sonst misst man nur, dass der Startpunkt auf einer Strasse liegt)
  - Kontrolle sind DIESELBEN Bytes, nur gemischt -> identische Bytestatistik
"""
import lzma, struct, json, math, random
R=6371000.0; P=0x3392334; S=18.0; MINDIST=4
PSF='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(PSF,'rb').read()
raw=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[P:])
X0,Y0,X1,Y1=struct.unpack_from('<4i',raw,0)
W=int((X1-X0)/S)+2; H=int((Y1-Y0)/S)+2
ways=json.load(open('osm/osm_west.json'))['elements']
def q(n):
    x=R*math.radians(n['lon']); y=R*math.log(math.tan(math.pi/4+math.radians(n['lat'])/2))
    return (x-X0)/S,(y-Y0)/S
road=bytearray(W*H)
for w_ in ways:
    g=w_.get('geometry')
    if not g: continue
    pp=[q(n) for n in g]
    for (ax,ay),(bx,by) in zip(pp,pp[1:]):
        k=max(1,int(max(abs(bx-ax),abs(by-ay))*2))
        for t in range(k+1):
            a=int(round(ax+(bx-ax)*t/k)); b=int(round(ay+(by-ay)*t/k))
            if 0<=a<W and 0<=b<H: road[b*W+a]=1
starts={}
for w_ in ways:
    for n in w_.get('geometry') or []:
        a,b=q(n); a,b=int(round(a)),int(round(b))
        if not(0<=a<W and 0<=b<H): continue
        o=raw.find(struct.pack('<HH',a,b))
        if o>=0: starts[o]=(a,b)
starts=sorted(starts.items())
print(f"Raster {W}x{H}, {100*sum(road)/(W*H):.1f} % Strassenzellen, "
      f"{len(starts)} verifizierte Startoffsets, Maßstab {S}")

def bits(bs, off, w):
    v=0
    for i in range(w):
        p=off+i
        if p>>3 >= len(bs): return None
        v=(v<<1)|((bs[p>>3]>>(7-(p&7)))&1)
    return v
def tc(v,w): return v-(1<<w) if v>>(w-1) else v          # Zweierkomplement
def zz(v): return (v>>1)*(-1 if v&1 else 1)               # zigzag

def walk(bs,a,b,w,off,sign,order,npt=12):
    x,y=a,b; out=[]
    for _ in range(npt):
        u=bits(bs,off,w); off+=w
        v=bits(bs,off,w); off+=w
        if u is None or v is None: break
        du=tc(u,w) if sign=='tc' else zz(u)
        dv=tc(v,w) if sign=='tc' else zz(v)
        dx,dy=(du,dv) if order=='xy' else (dv,du)
        if dx==0 and dy==0: continue
        x+=dx; y+=dy
        if not(0<=x<W and 0<=y<H): break
        out.append((x,y))
    return out

def score(w,off,sign,order,shuffle=False,seed=5):
    rnd=random.Random(seed); hit=tot=0
    for o,(a,b) in starts:
        bs=bytearray(raw[o+4:o+4+14])
        if shuffle: rnd.shuffle(bs)
        for x,y in walk(bytes(bs),a,b,w,off,sign,order):
            if abs(x-a)+abs(y-b) < MINDIST: continue
            tot+=1; hit+=road[y*W+x]
    return (hit/tot if tot else 0), tot

best=[]
for w in range(3,11):
    for off in range(0,16):
        for sign in ('tc','zz'):
            for order in ('xy','yx'):
                p,t=score(w,off,sign,order)
                if t<200: continue
                pc,_=score(w,off,sign,order,shuffle=True)
                if pc>0: best.append((p/pc,p,pc,t,w,off,sign,order))
best.sort(reverse=True)
print(f"\n{'Faktor':>7s} {'Quote':>7s} {'Kontrolle':>10s} {'Pkt':>6s}  w  bitoff sign ord")
for f,p,pc,t,w,off,sign,order in best[:12]:
    print(f"{f:7.2f} {100*p:6.1f} % {100*pc:9.1f} % {t:6d}  {w:2d}  {off:4d}  {sign}  {order}")
print(f"\n{len(best)} Konfigurationen geprueft; bester Faktor {best[0][0]:.2f}x")
