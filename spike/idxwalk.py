#!/usr/bin/env python3
"""Sequentiell durch den Kopfbereich laufen: Laeufe von 32-B-Records finden,
in denen (+0,+4) und (+6,+10) Anker mit passender Laenge sind."""
import struct, pickle
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:c for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
u32=lambda o: struct.unpack_from('<I',d,o)[0]
u16=lambda o: struct.unpack_from('<H',d,o)[0]

def good(s):
    if s+32>FIRST: return False
    oA,lA=u32(s),u16(s+4); oB,lB=u32(s+6),u16(s+10)
    return A.get(oA)==lA and A.get(oB)==lB

runs=[]; s=0
while s < FIRST-32:
    if good(s):
        start=s; k=s
        while good(k): k+=32
        runs.append((start,(k-start)//32)); s=k
    else:
        s+=1
runs=[r for r in runs if r[1]>=4]
print(f"{len(runs)} Laeufe mit >=4 Records, zusammen "
      f"{sum(r[1] for r in runs)} Records "
      f"({2*sum(r[1] for r in runs)} Blockverweise von {len(A)})")
for st,cnt in runs[:25]:
    k0=u32(st+28); k1=u32(st+(cnt-1)*32+28)
    print(f"  @0x{st:06x}  {cnt:6d} Records  key {k0>>21:3d}/{k0&0x1FFFFF:8d}"
          f" .. {k1>>21:3d}/{k1&0x1FFFFF:8d}")
if len(runs)>25: print(f"  ... {len(runs)-25} weitere")
