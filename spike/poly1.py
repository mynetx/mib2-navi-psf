#!/usr/bin/env python3
"""Polylinien in Blattkacheln rekonstruieren und die Koordinateneinheit fitten."""
import struct, lzma, math, collections, statistics
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)
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

def tiles_of(bs):
    out=[]
    for off,b in bs:
        if len(b)<16: continue
        x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
        if not(x0<x1 and y0<y1): continue
        w=lon_of(x1)-lon_of(x0)
        if not(0.001<w<10): continue
        L=round(math.log2(360.0/w))
        if not(4<=L<=16) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: continue
        out.append((L,off,b,x0,y0,x1,y1))
    return out

def delta_runs(b, start=16, thr=40, minlen=30):
    """Laeufe, in denen alle Bytes als signed betragsmaessig klein sind."""
    runs=[]; cur=None
    for i in range(start, len(b)):
        if abs(s8(b[i]))<=thr:
            if cur is None: cur=i
        else:
            if cur is not None and i-cur>=minlen: runs.append((cur,i))
            cur=None
    if cur is not None and len(b)-cur>=minlen: runs.append((cur,len(b)))
    return runs

bs=blocks('Malta_Basic.psf')
ts=tiles_of(bs)
leaves=[t for t in ts if t[0] in (13,14)]
leaves.sort(key=lambda t:-len(t[2]))
print(f"{len(leaves)} Blattkacheln (Level 13/14)\n")

allext=[]
for L,off,b,x0,y0,x1,y1 in leaves[:8]:
    W=x1-x0; H=y1-y0
    runs=delta_runs(b)
    runs.sort(key=lambda r:-(r[1]-r[0]))
    print(f"Block @0x{off:x} L{L} {len(b)}B  Kachel {W}x{H} m  "
          f"{len(runs)} Delta-Laeufe")
    for s,e in runs[:2]:
        raw=b[s:e]
        pairs=[(s8(raw[i]),s8(raw[i+1])) for i in range(0,len(raw)-1,2)]
        x=y=0; xs=[0]; ys=[0]
        for dx,dy in pairs:
            x+=dx; y+=dy; xs.append(x); ys.append(y)
        ex=max(xs)-min(xs); ey=max(ys)-min(ys)
        # Richtungskohaerenz: Laenge des resultierenden Vektors / Weglaenge
        pl=sum(math.hypot(dx,dy) for dx,dy in pairs)
        net=math.hypot(xs[-1]-xs[0], ys[-1]-ys[0])
        ux = W/ex if ex else 0; uy = H/ey if ey else 0
        allext.append((L,ex,ey,W,H))
        print(f"   Lauf 0x{s:04x}..0x{e:04x} {e-s}B {len(pairs)} Segmente: "
              f"Ausdehnung {ex}x{ey} Einheiten")
        print(f"      Kohaerenz net/len = {net/max(1e-9,pl):.3f}  "
              f"(Strasse hoch, Random Walk ~{1/math.sqrt(len(pairs)):.2f})")
        print(f"      Einheit, wenn Lauf die Kachel fuellt: "
              f"x {ux:.3f} m, y {uy:.3f} m")
print()
# Einheit global schaetzen: Verhaeltnis Kachelbreite / Ausdehnung
for L in (13,14):
    g=[a for a in allext if a[0]==L]
    if not g: continue
    ux=[a[3]/a[1] for a in g if a[1]]
    print(f"Level {L}: Median Einheit-x aus {len(ux)} Laeufen: "
          f"{statistics.median(ux):.3f} m/Einheit")
    print(f"   Kachelbreite {g[0][3]} m / 2^n: "
          + ", ".join(f"2^{n}->{g[0][3]/2**n:.3f}m" for n in (8,10,12,14,16)))
