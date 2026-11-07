#!/usr/bin/env python3
"""Polylinien mit absoluter Platzierung: Startpunkt vor dem Lauf, Deltas dahinter.
Test: bleiben alle Punkte im kachelrelativen Raster [0, 2^N]?"""
import struct, lzma, math, collections, statistics, sys
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
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

def delta_runs(b, start=16, thr=40, minlen=24):
    runs=[]; cur=None
    for i in range(start,len(b)):
        if abs(s8(b[i]))<=thr:
            if cur is None: cur=i
        else:
            if cur is not None and i-cur>=minlen: runs.append((cur,i))
            cur=None
    if cur is not None and len(b)-cur>=minlen: runs.append((cur,len(b)))
    return runs

bs=blocks('Malta_Basic.psf')
ts=tiles_of(bs)
leaves=[t for t in ts if 11<=t[0]<=14]
print(f"{len(leaves)} Kacheln Level 11-14\n")

# --- Ausdehnungsverteilung: welches 2^N begrenzt alle Laeufe?
exts=[]
for L,off,b,x0,y0,x1,y1 in leaves:
    for s,e in delta_runs(b):
        raw=b[s:e]
        pr=[(s8(raw[i]),s8(raw[i+1])) for i in range(0,len(raw)-1,2)]
        if len(pr)<12: continue
        x=y=0; xs=[0]; ys=[0]
        for dx,dy in pr:
            x+=dx; y+=dy; xs.append(x); ys.append(y)
        exts.append((max(xs)-min(xs), max(ys)-min(ys)))
if exts:
    ex=[e[0] for e in exts]; ey=[e[1] for e in exts]
    print(f"{len(exts)} Laeufe. Ausdehnung x: median {statistics.median(ex)}, "
          f"p99 {sorted(ex)[int(len(ex)*.99)]}, max {max(ex)}")
    print(f"                  y: median {statistics.median(ey)}, "
          f"p99 {sorted(ey)[int(len(ey)*.99)]}, max {max(ey)}")
    for N in (9,10,11,12):
        inN=sum(1 for a,b_ in exts if a<=2**N and b_<=2**N)
        print(f"   Ausdehnung <= 2^{N}={2**N}: {inN}/{len(exts)} = {inN*100/len(exts):.1f}%")

# --- Startpunkt-Hypothese: 4 Bytes vor dem Lauf = uint16 x, uint16 y in [0,2^N)
print()
for N in (10,11,12):
    G=2**N
    ok=0; tot=0
    for L,off,b,x0,y0,x1,y1 in leaves:
        for s,e in delta_runs(b):
            if s<4: continue
            raw=b[s:e]
            pr=[(s8(raw[i]),s8(raw[i+1])) for i in range(0,len(raw)-1,2)]
            if len(pr)<12: continue
            sx=u16(b,s-4); sy=u16(b,s-2)
            if not(0<=sx<G and 0<=sy<G): continue
            tot+=1
            x,y=sx,sy; inside=True
            for dx,dy in pr:
                x+=dx; y+=dy
                if not(0<=x<G and 0<=y<G): inside=False; break
            if inside: ok+=1
    print(f"N={N} (Raster {G}): Startpunkt gueltig fuer {tot} Laeufe, "
          f"davon bleiben {ok} komplett im Raster = {ok*100/max(1,tot):.1f}%")
