#!/usr/bin/env python3
"""Hypothese: Kopfindex-Record = 24 B
   minX(4) maxY(4) maxX(4) minY(4) offset(4) len(2) flags(2)
Global pruefen: Abstaende der (Offset,Laenge)-Fundstellen und BBox-Plausibilitaet."""
import struct, pickle, collections, math
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:c for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
u32=lambda o: struct.unpack_from('<I',d,o)[0]
u16=lambda o: struct.unpack_from('<H',d,o)[0]
R=6371000.0
hits=[q for q in range(FIRST-6) if A.get(u32(q))==u16(q+4)]
print(f"{len(hits)} Fundstellen (Offset+Laenge)")
gap=collections.Counter(hits[i+1]-hits[i] for i in range(len(hits)-1))
print(f"Abstaende: {gap.most_common(6)}")

# BBox der Records pruefen
GRID=[2*math.pi*R/2**L for L in range(4,17)]
ok=bad=0; lev=collections.Counter(); flags=collections.Counter()
for q in hits:
    if q<16: continue
    mnx,mxy,mxx,mny = u32(q-16),u32(q-12),u32(q-8),u32(q-4)
    w=mxx-mnx; h=mxy-mny
    if not (0<w<3_000_000 and 0<h<3_000_000): bad+=1; continue
    best=min(range(len(GRID)), key=lambda i: abs(GRID[i]-w))
    if abs(GRID[best]-w)/w < 0.02:
        ok+=1; lev[best+4]+=1; flags[u16(q+6)]+=1
    else: bad+=1
print(f"BBox 16 B VOR (Offset,Laenge): plausibel {ok}, unplausibel {bad} "
      f"({ok*100//len(hits)} %)")
print(f"Level-Verteilung (Breite = 2piR/2^L): {sorted(lev.items())}")
print(f"flags @+6: {flags.most_common(6)}")

# Gegenprobe: BBox 16 B DANACH
ok2=0
for q in hits:
    if q+24>FIRST: continue
    mnx,mxy,mxx,mny = u32(q+8),u32(q+12),u32(q+16),u32(q+20)
    w=mxx-mnx
    if 0<w<3_000_000 and min(abs(g-w)/w for g in GRID)<0.02: ok2+=1
print(f"Gegenprobe BBox 16 B DANACH: plausibel {ok2} ({ok2*100//len(hits)} %)")
