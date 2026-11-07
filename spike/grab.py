#!/usr/bin/env python3
"""Kachelbloecke ueber Zielorten aus GermanyWest_Basic extrahieren und cachen."""
import struct, lzma, math, pickle, sys
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)
def merc_x(lon): return R*math.radians(lon)
def merc_y(lat): return R*math.log(math.tan(math.pi/4+math.radians(lat)/2))

TARGETS={'Testort':(7.7,50.1),'Niederortbeta':(8.3,50.3)}
PT={k:(merc_x(v[0]),merc_y(v[1])) for k,v in TARGETS.items()}

path='GermanyWest_Basic.psf'
d=open(path,'rb').read(); n=len(d)
keep=[]; nblk=0; p=0
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
                    b=r[:siz]; nblk+=1
                    if len(b)>=16:
                        x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
                        if x0<x1 and y0<y1:
                            w=lon_of(x1)-lon_of(x0)
                            if 0.001<w<10:
                                L=round(math.log2(360.0/w))
                                if 4<=L<=16 and abs(w-360.0/2**L)/(360.0/2**L)<0.01:
                                    for name,(px,py) in PT.items():
                                        if x0<=px<=x1 and y0<=py<=y1:
                                            keep.append((name,L,p,b,x0,y0,x1,y1))
                    p+=13; continue
            except Exception: pass
    p+=1
print(f"{nblk} Bloecke gescannt, {len(keep)} Kacheln ueber den Zielorten")
import collections
for name in TARGETS:
    g=[k for k in keep if k[0]==name]
    print(f"  {name}: {len(g)} Kacheln, Level {sorted(set(x[1] for x in g))}, "
          f"Groessen {sorted(len(x[3]) for x in g)}")
pickle.dump(keep, open('../spike/gw_tiles.pkl','wb'))
print("gecacht: gw_tiles.pkl")
