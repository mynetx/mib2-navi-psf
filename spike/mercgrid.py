#!/usr/bin/env python3
"""WEGWERF: signed int32 + Rastertest. Echte Kachelecken sind quantisiert."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
A=6378137.0; E=0.081819190842622
def sph_lat(y): return math.degrees(2*math.atan(math.exp(y/A))-math.pi/2)
def lon_of(x): return math.degrees(x/A)
def merc_y(lat):
    p=math.radians(lat); return A*math.log(math.tan(math.pi/4+p/2))

def blocks(path, cap=None):
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
                        if cap and len(out)>=cap: return out
                        continue
                except Exception: pass
        p+=1
    return out

REG={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Portugal':(-9.50,-6.19,36.96,42.15),'Denmark':(8.07,15.19,54.56,57.75)}

def gcd_of(vals):
    from math import gcd
    g=0
    for v in vals: g=gcd(g,abs(int(v)))
    return g

for region in ('Malta','Iceland','Portugal','Denmark'):
    path=f'{region}_Basic.psf'
    bs=blocks(path, cap=40000)
    rw,re_,rs,rn = REG[region]
    mx0,mx1 = A*math.radians(rw), A*math.radians(re_)
    my0,my1 = merc_y(rs), merc_y(rn)
    print(f"### {region}: {len(bs)} Bloecke  Mercator-Fenster "
          f"x[{mx0:.0f},{mx1:.0f}] y[{my0:.0f},{my1:.0f}]")
    hit=[]
    for b in bs:
        if len(b)<16: continue
        x0,y0,x1,y1 = i32(b,0),i32(b,4),i32(b,8),i32(b,12)
        if not(x0<x1 and y0<y1): continue
        # muss das Mercator-Fenster der Region ueberlappen (mit 50 km Toleranz)
        T=50000
        if x1<mx0-T or x0>mx1+T or y1<my0-T or y0>my1+T: continue
        hit.append((x0,y0,x1,y1))
    print(f"    Bloecke mit BBox im Regionsfenster: {len(hit)}")
    if len(hit)<10: print()
    if len(hit)<10: continue
    for k,lbl in ((0,'x0'),(1,'y0'),(2,'x1'),(3,'y1')):
        vs=sorted({h[k] for h in hit})
        d=[vs[i+1]-vs[i] for i in range(len(vs)-1)]
        c=collections.Counter(d)
        print(f"    {lbl}: {len(vs)} verschiedene Werte, GGT={gcd_of(vs)}, "
              f"haeufigste Abstaende {c.most_common(4)}")
    ws=collections.Counter(h[2]-h[0] for h in hit)
    hs=collections.Counter(h[3]-h[1] for h in hit)
    print(f"    Kachelbreiten (m): {ws.most_common(5)}")
    print(f"    Kachelhoehen (m): {hs.most_common(5)}")
    lons=[lon_of(h[0]) for h in hit]+[lon_of(h[2]) for h in hit]
    lats=[sph_lat(h[1]) for h in hit]+[sph_lat(h[3]) for h in hit]
    print(f"    -> lon[{min(lons):8.3f},{max(lons):8.3f}]  "
          f"lat[{min(lats):8.3f},{max(lats):8.3f}]   (Region "
          f"lon[{rw},{re_}] lat[{rs},{rn}])")
    print()
