#!/usr/bin/env python3
"""Mercator-Radius als einzigen freien Parameter fitten.
Bedingung: Kacheln sind gradquadratisch, also (x1-x0)/R == lat1(R)-lat0(R)."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

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

def lat_of(y,R): return 2*math.atan(math.exp(y/R))-math.pi/2

REG={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Portugal':(-9.50,-6.19,36.96,42.15),'Denmark':(8.07,15.19,54.56,57.75),
     'Albania':(19.26,21.06,39.62,42.67)}

# Kandidaten sammeln: BBox-artig, Breite nahe einem Vielfachen von ~2443*2^k
cand={}
for region in REG:
    bs=blocks(f'{region}_Basic.psf', cap=30000)
    got=[]
    for b in bs:
        if len(b)<16: continue
        x0,y0,x1,y1 = i32(b,0),i32(b,4),i32(b,8),i32(b,12)
        if not(x0<x1 and y0<y1): continue
        w=x1-x0; h=y1-y0
        if not(2000<w<80000 and 2000<h<200000): continue
        # Breite muss nahe 2443*2^k liegen
        k=round(math.log2(w/2443.0))
        if not(0<=k<=6): continue
        if abs(w-2443.0*2**k)>12: continue
        got.append((x0,y0,x1,y1,k))
    cand[region]=got
    print(f"{region}: {len(got)} gradquadratische Kachelkandidaten von {len(bs)} Bloecken")
print()

allc=[c for v in cand.values() for c in v]
print(f"Gesamt {len(allc)} Kandidaten\n")

best=None
for Ri in range(6300000, 6420000, 100):
    R=float(Ri); errs=[]
    for x0,y0,x1,y1,k in allc:
        dlon=(x1-x0)/R
        dlat=lat_of(y1,R)-lat_of(y0,R)
        errs.append(abs(dlon-dlat)/dlat)
    m=sum(errs)/len(errs)
    if best is None or m<best[0]: best=(m,R)
print(f"Grobfit: R = {best[1]:.0f} m  (mittlerer relativer Fehler {best[0]*100:.4f} %)")
R0=best[1]
best=None
for Ri in range(int(R0-2000), int(R0+2000)):
    R=float(Ri); errs=[]
    for x0,y0,x1,y1,k in allc:
        dlon=(x1-x0)/R
        dlat=lat_of(y1,R)-lat_of(y0,R)
        errs.append(abs(dlon-dlat)/dlat)
    m=sum(errs)/len(errs)
    if best is None or m<best[0]: best=(m,R)
ERR,R = best
print(f"Feinfit: R = {R:.0f} m  (mittlerer relativer Fehler {ERR*100:.4f} %)")
print(f"  Vergleich: WGS84 a = 6378137,  Erdmittelradius = 6371000,  "
      f"2piR/2^14 = {2*math.pi*R/2**14:.2f} m")
print(f"  Kachelbreite in Grad bei Level 14: {360/2**14:.7f}")
print()

print("=== Verifikation: liegen die Kacheln in ihrer Region? ===")
for region,(rw,re_,rs,rn) in REG.items():
    got=cand[region]
    if not got: continue
    ok=0; lons=[]; lats=[]
    for x0,y0,x1,y1,k in got:
        w=math.degrees(x0/R); e=math.degrees(x1/R)
        s=math.degrees(lat_of(y0,R)); nn=math.degrees(lat_of(y1,R))
        lons+=[w,e]; lats+=[s,nn]
        if e>=rw and w<=re_ and nn>=rs and s<=rn: ok+=1
    print(f"  {region:9s}: {ok}/{len(got)} = {ok*100/len(got):5.1f}% in der Region  "
          f"| Kachelbereich lon[{min(lons):8.3f},{max(lons):8.3f}] "
          f"lat[{min(lats):7.3f},{max(lats):7.3f}]")
    print(f"  {'':9s}  Region erwartet             "
          f"| lon[{rw:8.3f},{re_:8.3f}] lat[{rs:7.3f},{rn:7.3f}]")
