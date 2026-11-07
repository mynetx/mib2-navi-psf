#!/usr/bin/env python3
"""Deltakodierung der Straßenrecords gegen OSM bestimmen.

Bewertung ist geometrisch, nicht ueber Wegzuordnung: OSM zerlegt Strassen
anders als die Navikarte, ein OSM-Weg entspricht keinem Blockrecord. Eine
rekonstruierte Polylinie ist richtig, wenn ihre Stuetzpunkte auf IRGENDEINER
echten Strasse liegen.

Raster: alle OSM-highway-Segmente der Kachel in Blockeinheiten rastern,
dann je Kandidatenkodierung den Anteil rekonstruierter Punkte messen, die
auf oder neben einer Strassenzelle landen. Kontrolle ist derselbe Startpunkt
mit gewuerfelten Deltabytes.
"""
import lzma, struct, json, math, random, collections
R=6371000.0
PSF='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
P=0x3392334; S=17.9695

d=open(PSF,'rb').read()
raw=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[P:])
X0,Y0,X1,Y1=struct.unpack_from('<4i',raw,0)
W=int((X1-X0)/S)+4; H=int((Y1-Y0)/S)+4

def q(lat,lon):
    x=R*math.radians(lon); y=R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
    return (x-X0)/S, (y-Y0)/S

# --- Strassenraster ---
road=bytearray(W*H)
def mark(a,b):
    if 0<=a<W and 0<=b<H: road[b*W+a]=1
ways=json.load(open('osm/osm_west.json'))['elements']
nseg=0
for w in ways:
    g=w.get('geometry')
    if not g: continue
    pts=[q(n['lat'],n['lon']) for n in g]
    for (ax,ay),(bx,by) in zip(pts,pts[1:]):
        n=max(1,int(max(abs(bx-ax),abs(by-ay))))
        for k in range(n+1):
            mark(int(round(ax+(bx-ax)*k/n)), int(round(ay+(by-ay)*k/n)))
        nseg+=1
cells=sum(road)
print(f"Kachel {W}x{H} Einheiten, {nseg} OSM-Segmente gerastert, "
      f"{cells} Strassenzellen ({100*cells/(W*H):.1f} % der Flaeche)")

def near(a,b,k=1):
    for da in range(-k,k+1):
        for db in range(-k,k+1):
            x,y=a+da,b+db
            if 0<=x<W and 0<=y<H and road[y*W+x]: return True
    return False

# --- Recordstarts: u16-Paare, die auf einer Strassenzelle liegen ---
starts=[]
for o in range(0,len(raw)-4):
    a,b=struct.unpack_from('<HH',raw,o)
    if a<W and b<H and road[b*W+a]: starts.append((o,a,b))
print(f"{len(starts)} Positionen im Block sind ein u16-Paar auf einer Strassenzelle")

# --- Kandidatenkodierungen ---
def zz(v): return (v>>1) * (-1 if v&1 else 1)
def nib_hl_zz(bs):
    return [(zz(x>>4), zz(x&15)) for x in bs]
def nib_lh_zz(bs):
    return [(zz(x&15), zz(x>>4)) for x in bs]
def nib_hl_off(bs):
    return [((x>>4)-8, (x&15)-8) for x in bs]
def nib_lh_off(bs):
    return [((x&15)-8, (x>>4)-8) for x in bs]
def byte_signed(bs):
    return [(struct.unpack('<b',bs[i:i+1])[0], struct.unpack('<b',bs[i+1:i+2])[0])
            for i in range(0,len(bs)-1,2)]
CAND={'Nibbel hi=dx zigzag':nib_hl_zz,'Nibbel lo=dx zigzag':nib_lh_zz,
      'Nibbel hi=dx -8':nib_hl_off,'Nibbel lo=dx -8':nib_lh_off,
      'i8-Paare':byte_signed}

def score(fn, nbytes=12, sample=4000, rnd=False):
    hit=tot=0
    for o,a,b in random.sample(starts, min(sample,len(starts))):
        bs=raw[o+4:o+4+nbytes]
        if rnd: bs=bytes(random.randrange(256) for _ in bs)
        x,y=a,b
        for dx,dy in fn(bs):
            x+=dx; y+=dy
            if not(0<=x<W and 0<=y<H): break
            tot+=1
            if near(x,y): hit+=1
    return hit,tot,(100*hit/tot if tot else 0)

random.seed(7)
print(f"\n{'Kodierung':24s} {'Treffer':>9s} {'Punkte':>8s} {'Quote':>7s}   Kontrolle")
for name,fn in CAND.items():
    h,t,p=score(fn)
    hr,tr,pr=score(fn,rnd=True)
    print(f"{name:24s} {h:9d} {t:8d} {p:6.1f} %   {pr:5.1f} %"
          f"{'   <== SIGNAL' if p>pr*1.5 and t>500 else ''}")
