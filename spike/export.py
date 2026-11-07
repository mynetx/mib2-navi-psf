#!/usr/bin/env python3
"""Kacheln georeferenzieren, aufs 360/2^n-Raster einrasten, als GeoJSON exportieren.
Plus: Strassennamen je Kachel."""
import struct, lzma, math, json, re, collections, sys
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

region = sys.argv[1] if len(sys.argv)>1 else 'Malta'
bs=blocks(f'{region}_Basic.psf')
feats=[]; snapped=0; total=0
tilenames=collections.defaultdict(set)
NAME=re.compile(rb'(?:Triq|Vjal|Sqaq|Xatt|Misrah|Strada|Rruga|Rr\.|Bulevardi)'
                rb'[ \-][A-Za-z\xc0-\xff0-9\'\-\. ]{2,50}')
for off,b in bs:
    if len(b)<16: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    # Level aus der Breite: w == 360/2^L
    L=round(math.log2(360.0/w))
    if not(4<=L<=16): continue
    step=360.0/2**L
    if abs(w-step)/step > 0.01: continue
    total+=1
    W=lon_of(x0); S=lat_of(y0)
    # aufs Raster einrasten
    Wq=round(W/step)*step; Sq=round(S/step)*step
    if abs(W-Wq)<step*0.02 and abs(S-Sq)<step*0.02:
        snapped+=1
    E=Wq+step; N=Sq+step
    names={m.group().strip().decode('utf-8','replace') for m in NAME.finditer(b)}
    key=(L,round(Wq/step),round(Sq/step))
    tilenames[key] |= names
    feats.append({"type":"Feature",
        "properties":{"level":L,"col":round(Wq/step),"row":round(Sq/step),
                      "blockOffset":f"0x{off:x}","names":len(names)},
        "geometry":{"type":"Polygon","coordinates":[[
            [Wq,Sq],[E,Sq],[E,N],[Wq,N],[Wq,Sq]]]}})

print(f"### {region}: {len(bs)} Bloecke -> {total} Kacheln erkannt")
print(f"    aufs 360/2^L-Raster eingerastet: {snapped}/{total} = {snapped*100/max(1,total):.1f}%")
lv=collections.Counter(f['properties']['level'] for f in feats)
print(f"    Level-Verteilung: {dict(sorted(lv.items()))}")
uniq={}
for f in feats:
    p=f['properties']; uniq[(p['level'],p['col'],p['row'])]=f
print(f"    eindeutige Kacheln: {len(uniq)}")
gj={"type":"FeatureCollection","features":list(uniq.values())}
out=f'../spike/{region}_tiles.geojson'
json.dump(gj, open(out,'w'))
print(f"    GeoJSON: {out}  ({len(uniq)} Polygone)")

# Namen je Kachel
withn=[(k,v) for k,v in tilenames.items() if v]
withn.sort(key=lambda kv:-len(kv[1]))
print(f"\n    Kacheln mit Strassennamen: {len(withn)}")
for (L,c,r),ns in withn[:5]:
    step=360.0/2**L
    print(f"      Level {L} col {c} row {r}  lon[{c*step:.4f},{(c+1)*step:.4f}] "
          f"lat[{r*step:.4f},{(r+1)*step:.4f}]  {len(ns)} Namen")
    for n in sorted(ns)[:4]: print(f"          {n}")
csv=f'../spike/{region}_tile_names.csv'
with open(csv,'w') as fh:
    fh.write("level,col,row,lon_west,lat_south,lon_east,lat_north,name\n")
    for (L,c,r),ns in sorted(tilenames.items()):
        step=360.0/2**L
        for n in sorted(ns):
            fh.write(f'{L},{c},{r},{c*step:.6f},{r*step:.6f},'
                     f'{(c+1)*step:.6f},{(r+1)*step:.6f},"{n}"\n')
import os
print(f"\n    CSV: {csv}  ({os.path.getsize(csv)} Bytes)")
