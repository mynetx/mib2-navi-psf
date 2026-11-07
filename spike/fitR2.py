#!/usr/bin/env python3
"""Mercator-Radius geschlossen bestimmen: cos(phi)=w/h liefert phi ohne R,
daraus R = y / ln(tan(45+phi/2)). Median ueber viele Kacheln."""
import struct, lzma, math, statistics
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def blocks(path, cap):
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
                    if len(r)>=siz:
                        out.append(r[:siz]); p+=13
                        if len(out)>=cap: return out
                        continue
                except Exception: pass
        p+=1
    return out

REG={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Portugal':(-9.50,-6.19,36.96,42.15),'Denmark':(8.07,15.19,54.56,57.75),
     'Albania':(19.26,21.06,39.62,42.67)}

cand={}
for region in REG:
    bs=blocks(f'{region}_Basic.psf', 6000)
    got=[]
    for b in bs:
        if len(b)<16: continue
        x0,y0,x1,y1 = i32(b,0),i32(b,4),i32(b,8),i32(b,12)
        if not(x0<x1 and y0<y1): continue
        w=x1-x0; h=y1-y0
        if not(2000<w<80000 and 2000<h<200000): continue
        k=round(math.log2(w/2443.0))
        if not(0<=k<=6) or abs(w-2443.0*2**k)>12: continue
        got.append((x0,y0,x1,y1))
    cand[region]=got
    print(f"{region:9s}: {len(got):5d} Kachelkandidaten aus {len(bs)} Bloecken")

allc=[c for v in cand.values() for c in v]
print(f"\nGesamt {len(allc)} Kandidaten")

Rs=[]
for x0,y0,x1,y1 in allc:
    w=x1-x0; h=y1-y0
    r=w/h
    if not(0.05<r<0.999): continue
    phi=math.acos(r)
    ym=(y0+y1)/2.0
    t=math.tan(math.pi/4+phi/2)
    if t<=1: continue
    Rs.append(ym/math.log(t))
Rs.sort()
R=statistics.median(Rs)
print(f"R-Schaetzungen: {len(Rs)}")
print(f"   Median  = {R:12.1f} m")
print(f"   Quartile= {Rs[len(Rs)//4]:12.1f} .. {Rs[3*len(Rs)//4]:12.1f}")
print(f"   Vergleich: WGS84 a=6378137   Erdmittelradius=6371000")
print(f"   2*pi*R/2^14 = {2*math.pi*R/2**14:.2f} m   (beobachtete Basisbreite ~2443)")

def lat_of(y,R): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)
print(f"\n=== Verifikation mit R={R:.0f} ===")
for region,(rw,re_,rs,rn) in REG.items():
    got=cand[region]
    if not got: continue
    ok=0; lons=[]; lats=[]
    for x0,y0,x1,y1 in got:
        w=math.degrees(x0/R); e=math.degrees(x1/R)
        s=lat_of(y0,R); nn=lat_of(y1,R)
        lons+=[w,e]; lats+=[s,nn]
        if e>=rw and w<=re_ and nn>=rs and s<=rn: ok+=1
    print(f"  {region:9s} {ok:5d}/{len(got):5d} = {ok*100/len(got):5.1f}% in Region | "
          f"Kacheln lon[{min(lons):8.3f},{max(lons):8.3f}] lat[{min(lats):7.3f},{max(lats):7.3f}]")
    print(f"  {'erwartet':9s} {'':11s}         | "
          f"        lon[{rw:8.3f},{re_:8.3f}] lat[{rs:7.3f},{rn:7.3f}]")
