#!/usr/bin/env python3
"""ENDE-ZU-ENDE-BEWEIS: Georeferenz vorhersagen -> Inhalt der Kachel pruefen."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

R = 6371000.0
TILE0 = 2*math.pi*R/2**14      # Basiskachelbreite in Mercator-Metern

def merc(lon,lat): return R*math.radians(lon), R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
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

bs=blocks('Malta_Basic.psf')
print(f"Malta_Basic: {len(bs)} Bloecke\n")

# --- Rasterausrichtung pruefen
tiles=[]
for off,b in bs:
    if len(b)<16: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=x1-x0
    if not(2000<w<200000): continue
    k=round(math.log2(w/TILE0))
    if not(0<=k<=8) or abs(w-TILE0*2**k)>15: continue
    tiles.append((off,b,x0,y0,x1,y1,k))
print(f"Kachelkandidaten: {len(tiles)}")
res=[(t[2] % (TILE0*2**t[6])) / (TILE0*2**t[6]) for t in tiles]
near=sum(1 for r in res if r<0.02 or r>0.98)
print(f"Rasterausrichtung: x0 liegt bei {near}/{len(res)} = {near*100/len(res):.1f}% "
      f"innerhalb 2 % einer Kachelgrenze")
print(f"   (Zufall waere ~4 %)\n")

# --- Ende-zu-Ende: Flughafen Malta
POIS=[('Malta International Airport', 14.4775, 35.8575),
      ('Valletta', 14.5146, 35.8989),
      ('Mdina', 14.4035, 35.8859),
      ('Marsaxlokk', 14.5433, 35.8419),
      ('Victoria', 14.2409, 36.0443)]
for name,lon,lat in POIS:
    px,py = merc(lon,lat)
    inside=[t for t in tiles if t[2]<=px<=t[4] and t[3]<=py<=t[5]]
    nb=name.encode()
    withname=[t for t in tiles if nb in t[1]]
    both=[t for t in inside if nb in t[1]]
    print(f"{name!r} @ {lon},{lat}")
    print(f"   Kacheln, die den Punkt geografisch enthalten: {len(inside)}")
    print(f"   Kacheln, die den Namen als Text enthalten:    {len(withname)}")
    print(f"   BEIDES:                                        {len(both)}")
    if withname and inside:
        # Wie gut deckt sich die Namensmenge mit der Geometriemenge?
        sn={t[0] for t in withname}; si={t[0] for t in inside}
        print(f"   Namenskacheln, die den Punkt enthalten: "
              f"{len(sn&si)}/{len(sn)} = {len(sn&si)*100//max(1,len(sn))}%")
        for t in list(both)[:2]:
            print(f"      Kachel @0x{t[0]:x} level~{14-t[6]}  "
                  f"lon[{lon_of(t[2]):.4f},{lon_of(t[4]):.4f}] "
                  f"lat[{lat_of(t[3]):.4f},{lat_of(t[5]):.4f}]")
    print()

# --- Gegentest: ein Name, der NICHT in Malta liegt
print("Gegentest - Kachelbereich aller Kandidaten:")
lons=[lon_of(t[2]) for t in tiles]+[lon_of(t[4]) for t in tiles]
lats=[lat_of(t[3]) for t in tiles]+[lat_of(t[5]) for t in tiles]
print(f"   lon[{min(lons):.3f},{max(lons):.3f}]  lat[{min(lats):.3f},{max(lats):.3f}]")
