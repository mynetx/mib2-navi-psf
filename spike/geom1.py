#!/usr/bin/env python3
"""Stehen absolute Mercator-Koordinaten im Block? Nullfehler-Test gegen die Kachel-BBox."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
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
# Kacheln mit gueltiger BBox und ordentlicher Groesse
cand=[]
for off,b in bs:
    if len(b)<2000: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    L=round(math.log2(360.0/w))
    if not(4<=L<=16) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: continue
    cand.append((off,b,x0,y0,x1,y1,L))
cand.sort(key=lambda t:-len(t[1]))
print(f"{len(cand)} Kachelblöcke >=2000 B\n")

for off,b,x0,y0,x1,y1,L in cand[:6]:
    W,H = x1-x0, y1-y0
    # Zufallserwartung fuer einen int32 im Fenster
    p_x = W/2**32; p_y = H/2**32
    npos = len(b)-8
    exp_pairs = npos * p_x * p_y
    hits=[]
    for o in range(16, len(b)-8):
        X=i32(b,o); Y=i32(b,o+4)
        if x0<=X<=x1 and y0<=Y<=y1: hits.append((o,X,Y))
    print(f"Block @0x{off:x}  {len(b)} B  L{L}  "
          f"lon[{lon_of(x0):.4f},{lon_of(x1):.4f}] lat[{lat_of(y0):.4f},{lat_of(y1):.4f}]")
    print(f"   Kachel {W} x {H} m   Zufallserwartung: {exp_pairs:.6f} Paare")
    print(f"   GEFUNDEN: {len(hits)} int32-Paare in der BBox")
    if hits:
        print(f"   Positionen: {[hex(h[0]) for h in hits[:10]]}")
        for o,X,Y in hits[:6]:
            print(f"      @0x{o:04x}  lon={lon_of(X):.6f} lat={lat_of(Y):.6f}")
        # Abstaende der Trefferpositionen -> Recordgroesse?
        d=[hits[i+1][0]-hits[i][0] for i in range(len(hits)-1)]
        print(f"   Abstands-Histogramm: {collections.Counter(d).most_common(6)}")
    print()
