#!/usr/bin/env python3
"""Layout der Kopf-Indextabelle: welche Byteposition im 32-B-Raster traegt
Blockoffsets, welche Blocklaengen?"""
import struct, pickle, collections
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:(c,s) for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)

BASE=0x112            # erster Treffer
STRIDE=32
starts=list(range(BASE, FIRST-STRIDE, STRIDE))
print(f"{len(starts)} Rasterplaetze ab 0x{BASE:x}, Stride {STRIDE}")

for r in range(0, STRIDE-3):
    hit=sum(1 for s in starts if struct.unpack_from('<I',d,s+r)[0] in A)
    if hit > len(starts)//20:
        print(f"  +{r:2d}: {hit:6d}/{len(starts)} u32 = Blockoffset "
              f"({hit*100//len(starts)} %)")
print()
# Monotonie und Laengenfeld pruefen
o1=[struct.unpack_from('<I',d,s+0)[0] for s in starts]
o2=[struct.unpack_from('<I',d,s+6)[0] for s in starts]
val1=[v for v in o1 if v in A]; val2=[v for v in o2 if v in A]
print(f"Feld +0: {len(val1)} gueltig, monoton steigend: "
      f"{all(val1[i]<val1[i+1] for i in range(len(val1)-1))}")
print(f"Feld +6: {len(val2)} gueltig, monoton steigend: "
      f"{all(val2[i]<val2[i+1] for i in range(len(val2)-1))}")
print(f"Ueberschneidung der beiden Mengen: {len(set(val1)&set(val2))}")

print("\nerste 6 Records ab 0x%x:" % BASE)
for s in starts[:6]:
    rec=d[s:s+STRIDE]
    f=[struct.unpack_from('<I',d,s+k)[0] for k in (0,6)]
    tag=['ANK' if x in A else '---' for x in f]
    print(f"  0x{s:06x} {rec.hex(' ')}")
    print(f"          +0=0x{f[0]:08x} {tag[0]}  +6=0x{f[1]:08x} {tag[1]}")
