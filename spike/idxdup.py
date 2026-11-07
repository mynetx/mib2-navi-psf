#!/usr/bin/env python3
"""Gibt es eine zweite (redundante) Kopie der Indexeintraege irgendwo in der Datei?
Und traegt der Dateikopf ein Groessenfeld?"""
import struct, pickle, os
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
N=os.path.getsize(SRC)
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:c for p,c,s in anc}
d=open(SRC,'rb').read()
FIRST=anc[0][0]
print(f"Datei {N} B, Kopfbereich {FIRST} B")
print("\n1) Kommt (Offset,Laenge) eines Zielblocks mehr als einmal in der GANZEN Datei vor?")
for t in (0x36ca22e,0x3392334,0x346c45e):
    pat=struct.pack('<IH',t,A[t]); pos=[]; p=0
    while True:
        p=d.find(pat,p)
        if p<0: break
        pos.append(p); p+=1
    print(f"   @0x{t:07x}: {len(pos)} Vorkommen {[hex(x) for x in pos]} "
          f"(im Kopf: {sum(1 for x in pos if x<FIRST)})")

print("\n2) u32 im Kopf 0x00..0x112 nahe der Dateigroesse oder Blockzahl?")
for o in range(0,0x112):
    v=struct.unpack_from('<I',d,o)[0]
    if abs(v-N)<0x20000 or v==len(anc) or abs(v-FIRST)<64:
        print(f"   @0x{o:03x} u32 {v:12d} 0x{v:08x}  "
              f"(Dateigroesse {v-N:+d}, Kopfende {v-FIRST:+d})")

print("\n3) Letzte 64 B der Datei:")
for r in range(N-64,N,16):
    print(f"   {r:08x}  "+d[r:r+16].hex(' '))
print(f"\n4) Endet der letzte Block exakt an der Dateigrenze? "
      f"{anc[-1][0]+anc[-1][1]==N}  (Rest {N-anc[-1][0]-anc[-1][1]} B)")
