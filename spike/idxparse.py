#!/usr/bin/env python3
"""Kopf-Indextabelle als 32-B-Records lesen:
   +0 u32 offsetA, +4 u16 lenA, +6 u32 offsetB, +10 u16 lenB, +12..+27 ?, +28 key"""
import struct, pickle, collections
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:(c,s) for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
u32=lambda o: struct.unpack_from('<I',d,o)[0]
u16=lambda o: struct.unpack_from('<H',d,o)[0]

BASE=0x112; ST=32
n=(FIRST-BASE)//ST
okA=okB=0; chainA=chainB=0; keys=[]; layers=collections.Counter()
prevA=prevB=None; lastgood=None
for i in range(n):
    s=BASE+i*ST
    oA,lA,oB,lB,k = u32(s),u16(s+4),u32(s+6),u16(s+10),u32(s+28)
    a=oA in A and A[oA][0]==lA
    b=oB in A and A[oB][0]==lB
    if a: okA+=1
    if b: okB+=1
    if a and prevA is not None and oA+lA==prevA: chainA+=1
    if b and prevB is not None and oB+lB==prevB: chainB+=1
    if a: prevA=oA
    if b: prevB=oB
    if a or b:
        lastgood=i; keys.append(k); layers[k>>21]+=1
print(f"{n} Rasterplaetze")
print(f"  +0/+4  Offset+Laenge stimmt mit Anker: {okA}")
print(f"  +6/+10 Offset+Laenge stimmt mit Anker: {okB}")
print(f"  Kette offset+len == vorheriger Offset: A {chainA}, B {chainB}")
print(f"  letzter guelter Record: i={lastgood} @0x{BASE+lastgood*ST:x}")
print(f"  Layer-Verteilung (key>>21): {sorted(layers.items())}")
tiles=collections.Counter()
for k in keys: tiles[k&0x1FFFFF]+=1
print(f"  Kachelnummern: {min(tiles)}..{max(tiles)}, {len(tiles)} verschiedene")
print(f"  erwartete Region GermanyWest Basis 6000 -> Index "
      f"{min(tiles)-6000}..{max(tiles)-6000}")
