#!/usr/bin/env python3
"""Blattkacheln (hohes Level, kleine Flaeche) = reine Geometrie. Struktur ansehen."""
import struct, lzma, math, collections, re
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)

def blocks(path):
    d=open(path,'rb').read(); n=len(d); out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz: out.append((p,r[:siz])); p+=13; continue
                except Exception: pass
        p+=1
    return out

bs=blocks('Malta_Basic.psf')
tiles=[]
for off,b in bs:
    if len(b)<16: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    L=round(math.log2(360.0/w))
    if not(4<=L<=16) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: continue
    tiles.append((L,off,b,x0,y0,x1,y1))
byL=collections.Counter(t[0] for t in tiles)
print(f"Kacheln nach Level: {dict(sorted(byL.items()))}\n")

# Blattkacheln = hoechstes Level mit vernuenftig vielen Bloecken
for L in (14,13):
    grp=[t for t in tiles if t[0]==L]
    if not grp: continue
    grp.sort(key=lambda t:-len(t[2]))
    print(f"=== Level {L}: {len(grp)} Kacheln, Groessen "
          f"{min(len(t[2]) for t in grp)}..{max(len(t[2]) for t in grp)} B, "
          f"Median {sorted(len(t[2]) for t in grp)[len(grp)//2]} B")
    for L_,off,b,x0,y0,x1,y1 in grp[:3]:
        span_m = x1-x0
        print(f"\n  Block @0x{off:x}  {len(b)} B  "
              f"lon[{lon_of(x0):.5f},{lon_of(x1):.5f}] lat[{lat_of(y0):.5f},{lat_of(y1):.5f}]  "
              f"{span_m} m breit")
        # Nach dem 16-Byte-BBox-Kopf: was kommt?
        print(f"    ab 0x10, 128 Bytes:")
        for r in range(16, min(len(b),16+128), 16):
            row=b[r:r+16]
            print(f"      {r:04x}  {row.hex(' ')}  "
                  f"{''.join(chr(c) if 32<=c<127 else '.' for c in row)}")
        strs=re.findall(rb'[\x20-\x7e]{5,}', b)
        if strs: print(f"    ASCII: {[s.decode()[:30] for s in strs[:6]]}")
        # int16-Werte relativ zur Kachel: spannen sie die Kachel?
        for bits,fmt,mx in ((16,'<H',65536),(16,'<h',32768)):
            vs=[struct.unpack_from(fmt,b,o)[0] for o in range(16,len(b)-1)]
            if vs: print(f"    {fmt}: {min(vs)}..{max(vs)}")
        print(f"    Entropie-Profil (64-B-Fenster):")
        import math as m2
        prof=[]
        for o in range(16,len(b)-64,64):
            c=collections.Counter(b[o:o+64]); nn=64
            e=-sum((v/nn)*m2.log2(v/nn) for v in c.values())
            prof.append(f"{e:.1f}")
        print(f"      {' '.join(prof[:28])}")
