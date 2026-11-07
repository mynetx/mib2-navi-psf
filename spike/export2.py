#!/usr/bin/env python3
"""Finaler Export: Kacheln + NDS packed Tile ID + Strassennamen -> GeoJSON/CSV."""
import struct, lzma, math, json, re, collections, sys, os
sys.path.insert(0,'../spike')
import nds
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)

def morton(col,row,level):
    c=col&((1<<(level+1))-1); r=row&((1<<level)-1); m=0
    for i in range(level+1):
        if c>>i & 1: m|=1<<(2*i)
        if i<level and (r>>i & 1): m|=1<<(2*i+1)
    return m

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

# Namen: NUL-terminiert, muss vollstaendig als UTF-8 dekodieren
PREF=rb'(?:Triq|Vjal|Sqaq|Xatt|Misra\xc4\xa7|Misrah|Rotunda|Strada|Rruga|Bulevardi|Vej|Gade|Alle)'
NAME=re.compile(PREF+rb"[ \-][^\x00]{2,60}")
def names_in(b):
    out=set()
    for m in NAME.finditer(b):
        s=m.group()
        try: t=s.decode('utf-8')
        except UnicodeDecodeError: continue
        t=t.strip()
        if 5<=len(t)<=60 and not any(ord(c)<32 for c in t): out.add(t)
    return out

region = sys.argv[1] if len(sys.argv)>1 else 'Malta'
bs=blocks(f'{region}_Basic.psf')
tiles={}; tilenames=collections.defaultdict(set); total=0; snapped=0
for off,b in bs:
    if len(b)<16: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    L=round(math.log2(360.0/w))
    if not(4<=L<=16): continue
    step=360.0/2**L
    if abs(w-step)/step>0.01: continue
    total+=1
    W=lon_of(x0); S=lat_of(y0)
    col=round(W/step); row=round(S/step)
    if abs(W-col*step)<step*0.02 and abs(S-row*step)<step*0.02: snapped+=1
    lvl=L-1
    nr=morton(col,row,lvl); pid=nr+(1<<(16+lvl))
    key=(L,col,row)
    tiles[key]=pid
    tilenames[key] |= names_in(b)

print(f"### {region}: {len(bs)} Bloecke -> {total} Kacheln, "
      f"{snapped*100/max(1,total):.1f}% rastertreu, {len(tiles)} eindeutig")
feats=[]
for (L,col,row),pid in sorted(tiles.items()):
    step=360.0/2**L
    W,S=col*step,row*step
    feats.append({"type":"Feature","properties":{
        "grid_level":L,"nds_level":L-1,"col":col,"row":row,
        "nds_packed_tile_id":pid,"n_names":len(tilenames[(L,col,row)])},
        "geometry":{"type":"Polygon","coordinates":[[
            [W,S],[W+step,S],[W+step,S+step],[W,S+step],[W,S]]]}})
gj=f'../spike/{region}_tiles.geojson'
json.dump({"type":"FeatureCollection","features":feats}, open(gj,'w'))
print(f"    {gj}  {os.path.getsize(gj)} B, {len(feats)} Polygone")

rows=0
csv=f'../spike/{region}_tile_names.csv'
with open(csv,'w') as fh:
    fh.write("nds_packed_tile_id,grid_level,col,row,lon_west,lat_south,lon_east,lat_north,name\n")
    for (L,col,row),ns in sorted(tilenames.items()):
        if not ns: continue
        step=360.0/2**L; pid=tiles[(L,col,row)]
        for n in sorted(ns):
            fh.write(f'{pid},{L},{col},{row},{col*step:.6f},{row*step:.6f},'
                     f'{(col+1)*step:.6f},{(row+1)*step:.6f},"{n}"\n')
            rows+=1
print(f"    {csv}  {os.path.getsize(csv)} B, {rows} Namenszeilen")
withn=sorted(((k,v) for k,v in tilenames.items() if v), key=lambda kv:-len(kv[1]))
print(f"    Kacheln mit Namen: {len(withn)}")
for (L,c,r),ns in withn[:3]:
    step=360.0/2**L
    print(f"      L{L} col{c} row{r} lon[{c*step:.4f},{(c+1)*step:.4f}] "
          f"lat[{r*step:.4f},{(r+1)*step:.4f}]  {len(ns)} Namen: "
          f"{', '.join(sorted(ns)[:3])}")
