#!/usr/bin/env python3
"""Startpunkt der Polylinien als bit-gepacktes Paar suchen.
Kriterium: der komplette rekonstruierte Pfad muss im Raster [0,2^N) bleiben."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def s8(v): return v-256 if v>127 else v

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

def bits_msb(b, bitpos, nbits):
    v=0
    for i in range(nbits):
        byte=(bitpos+i)//8; bit=7-((bitpos+i)%8)
        if byte>=len(b): return None
        v=(v<<1)|((b[byte]>>bit)&1)
    return v
def bits_lsb(b, bitpos, nbits):
    v=0
    for i in range(nbits):
        byte=(bitpos+i)//8; bit=(bitpos+i)%8
        if byte>=len(b): return None
        v |= ((b[byte]>>bit)&1)<<i
    return v

def runs(b, start=16, thr=40, minlen=24):
    out=[]; cur=None
    for i in range(start,len(b)):
        if abs(s8(b[i]))<=thr:
            if cur is None: cur=i
        else:
            if cur is not None and i-cur>=minlen: out.append((cur,i))
            cur=None
    if cur is not None and len(b)-cur>=minlen: out.append((cur,len(b)))
    return out

bs=blocks('Malta_Basic.psf')
leaves=[]
for off,b in bs:
    if len(b)<300: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    L=round(math.log2(360.0/w))
    if 11<=L<=14 and abs(w-360.0/2**L)/(360.0/2**L)<0.01: leaves.append((L,off,b))
print(f"{len(leaves)} Blattkacheln\n")

cases=[]
for L,off,b in leaves[:600]:
    for s,e in runs(b):
        raw=b[s:e]
        pr=[(s8(raw[i]),s8(raw[i+1])) for i in range(0,len(raw)-1,2)]
        if 12<=len(pr): cases.append((b,s,pr))
print(f"{len(cases)} Polylinien-Kandidaten\n")

best=[]
for N in (10,11,12):
    G=2**N
    for order,rd in (('MSB',bits_msb),('LSB',bits_lsb)):
        for backbits in range(1,33):     # wie viele Bits vor dem Lauf liegt (x,y)
            ok=0; tot=0
            for b,s,pr in cases:
                bp = s*8 - backbits
                if bp<0: continue
                x=rd(b,bp,N); y=rd(b,bp+N,N)
                if x is None or y is None: continue
                if not(0<=x<G and 0<=y<G): continue
                tot+=1
                cx,cy=x,y; good=True
                for dx,dy in pr:
                    cx+=dx; cy+=dy
                    if not(0<=cx<G and 0<=cy<G): good=False; break
                if good: ok+=1
            if tot>=40:
                best.append((ok/tot, ok, tot, N, order, backbits))
best.sort(reverse=True)
print(f"{'Rate':>7} {'ok':>6} {'von':>6}  N  Ordnung  Bits-vor-Lauf")
for r,ok,tot,N,order,bb in best[:12]:
    print(f"{r*100:6.1f}% {ok:6d} {tot:6d} {N:2d}  {order:4s}     {bb:3d}")
if best:
    print(f"\nZufallserwartung: ein Pfad mit ~{len(cases[0][2])} Segmenten bleibt")
    print(f"per Zufall selten im Raster -> hohe Rate ist aussagekraeftig")
