#!/usr/bin/env python3
"""WEGWERF: Hypothese - Blockkopf ist eine Bounding Box in Mercator-Metern."""
import struct, lzma, math, collections
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

A=6378137.0
E=0.081819190842622

def sph_lat(y):            # EPSG:3857 sphaerisch
    return math.degrees(2*math.atan(math.exp(y/A)) - math.pi/2)
def ell_lat(y):            # EPSG:3395 ellipsoidal, iterativ
    t=math.exp(-y/A); phi=math.pi/2-2*math.atan(t)
    for _ in range(12):
        con=E*math.sin(phi)
        dphi=math.pi/2-2*math.atan(t*((1-con)/(1+con))**(E/2))-phi
        phi+=dphi
        if abs(dphi)<1e-12: break
    return math.degrees(phi)
def lon_of(x): return math.degrees(x/A)

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
                    if len(r)>=siz: out.append(r[:siz]); p+=13; continue
                except Exception: pass
        p+=1
    return out

REG={'Malta':(14.18,14.58,35.79,36.08),'Albania':(19.26,21.06,39.62,42.67),
     'Denmark':(8.07,15.19,54.56,57.75),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Portugal':(-9.50,-6.19,36.96,42.15)}

# Mercator-Fenster fuer Europa als Plausibilitaetsfilter
XMIN,XMAX=-3.7e6,5.4e6
YMIN,YMAX=3.6e6,1.20e7

for region in ('Malta','Albania','Denmark','Iceland','Portugal'):
    path=f'{region}_Basic.psf'
    try: bs=blocks(path)
    except FileNotFoundError: print(f"{path} fehlt"); continue
    rw,re_,rs,rn = REG[region]
    cand=[]
    for b in bs:
        if len(b)<16: continue
        x0,y0,x1,y1 = u32(b,0),u32(b,4),u32(b,8),u32(b,12)
        if not(x0<x1 and y0<y1): continue
        if not all(XMIN<=v<=XMAX for v in (x0,x1)): continue
        if not all(YMIN<=v<=YMAX for v in (y0,y1)): continue
        cand.append((x0,y0,x1,y1))
    print(f"### {region}: {len(bs)} Bloecke, {len(cand)} mit BBox-artigem Kopf "
          f"({len(cand)*100//max(1,len(bs))}%)")
    if not cand: print()
    for name,latf in (('sphaerisch 3857',sph_lat),('ellipsoidal 3395',ell_lat)):
        inside=0
        lons=[]; lats=[]
        for x0,y0,x1,y1 in cand:
            w,e = lon_of(x0), lon_of(x1)
            s,nn = latf(y0), latf(y1)
            lons += [w,e]; lats += [s,nn]
            if e>=rw and w<=re_ and nn>=rs and s<=rn: inside+=1
        if not cand: continue
        print(f"    {name}: {inside}/{len(cand)} = {inside*100/len(cand):5.1f}% "
              f"ueberlappen die Region")
        print(f"        Gesamtausdehnung lon[{min(lons):8.3f},{max(lons):8.3f}] "
              f"lat[{min(lats):8.3f},{max(lats):8.3f}]")
        print(f"        Region erwartet  lon[{rw:8.3f},{re_:8.3f}] "
              f"lat[{rs:8.3f},{rn:8.3f}]")
    print()
