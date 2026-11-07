#!/usr/bin/env python3
"""Wo im Kopfbereich stehen u32-Werte, die exakt Blockoffsets sind?"""
import struct, pickle, collections
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
hits=[]
for o in range(0, FIRST-4):
    v=struct.unpack_from('<I',d,o)[0]
    if v in A: hits.append((o,v))
print(f"Kopfbereich {FIRST} B, {len(A)} Anker")
print(f"u32-Treffer auf Blockoffsets: {len(hits)}")
if hits:
    m=collections.Counter(o%32 for o,v in hits)
    print(f"Position mod 32: {sorted(m.items(), key=lambda x:-x[1])[:6]}")
    m4=collections.Counter(o%4 for o,v in hits)
    print(f"Position mod  4: {sorted(m4.items(), key=lambda x:-x[1])}")
    print(f"erster Treffer @0x{hits[0][0]:x} -> 0x{hits[0][1]:x}")
    print(f"letzter Treffer @0x{hits[-1][0]:x} -> 0x{hits[-1][1]:x}")
    # Abstaende der Treffer
    dif=collections.Counter(hits[i+1][0]-hits[i][0] for i in range(len(hits)-1))
    print(f"Treffer-Abstaende: {dif.most_common(8)}")
