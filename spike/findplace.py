#!/usr/bin/env python3
"""Ortsnamen in den Regionsdateien suchen + Kachelabdeckung der Region messen."""
import struct, lzma, math, sys, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)
def merc_x(lon): return R*math.radians(lon)
def merc_y(lat): return R*math.log(math.tan(math.pi/4+math.radians(lat)/2))

TARGETS={'Testort':(7.7,50.1),
         'Ortbeta (Region)':(8.3,50.3),
         'Niederortbeta':(8.3,50.3),
         'Oberortbeta':(8.3,50.3)}
NEEDLES=[t.encode() for t in TARGETS]+[b'Testort',b'Niederortbeta',b'Oberortbeta']

def scan(path):
    d=open(path,'rb').read(); n=len(d)
    found=collections.Counter(); tiles=[]; nblk=0; p=0
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
                        for nd in set(NEEDLES):
                            if nd in b: found[nd.decode()]+=1
                        if len(b)>=16:
                            x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
                            if x0<x1 and y0<y1:
                                w=lon_of(x1)-lon_of(x0)
                                if 0.001<w<10:
                                    L=round(math.log2(360.0/w))
                                    if 4<=L<=16 and abs(w-360.0/2**L)/(360.0/2**L)<0.01:
                                        tiles.append((x0,y0,x1,y1))
                        p+=13; continue
                except Exception: pass
        p+=1
    return nblk, found, tiles

for path in sys.argv[1:]:
    name=path.split('/')[-1]
    nblk, found, tiles = scan(path)
    print(f"### {name}: {nblk} Bloecke, {len(tiles)} Kacheln")
    if found:
        for k,v in sorted(found.items(), key=lambda kv:-kv[1]):
            print(f"    NAMENSTREFFER  {k!r}: in {v} Bloecken")
    else:
        print(f"    keine Namenstreffer")
    if tiles:
        lo=[lon_of(t[0]) for t in tiles]+[lon_of(t[2]) for t in tiles]
        la=[lat_of(t[1]) for t in tiles]+[lat_of(t[3]) for t in tiles]
        print(f"    Kachelabdeckung: lon[{min(lo):7.3f},{max(lo):7.3f}] "
              f"lat[{min(la):7.3f},{max(la):7.3f}]")
        for tn,(tlon,tlat) in TARGETS.items():
            px,py=merc_x(tlon),merc_y(tlat)
            c=[t for t in tiles if t[0]<=px<=t[2] and t[1]<=py<=t[3]]
            if c:
                lv=sorted({round(math.log2(360.0/(lon_of(t[2])-lon_of(t[0])))) for t in c})
                print(f"    {tn:18s} liegt in {len(c)} Kacheln, Level {lv}")
            else:
                print(f"    {tn:18s} in keiner Kachel")
    print(flush=True)
