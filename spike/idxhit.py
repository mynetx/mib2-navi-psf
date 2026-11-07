#!/usr/bin/env python3
"""Direkt: kommt der u32-Offset eines Zielblocks irgendwo im Kopfbereich vor?"""
import struct, pickle
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:c for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
TARGET=[0x36ca22e,0x3392334,0x346c45e,0x2f4009f,0x2f34830,0x36ce94a,0x29d48b8,0x3b25e2a]
for t in TARGET:
    pat=struct.pack('<I',t); pos=[]; p=0
    while True:
        p=d.find(pat,p)
        if p<0: break
        pos.append(p); p+=1
    ok=[q for q in pos if struct.unpack_from('<H',d,q+4)[0]==A[t]]
    print(f"@0x{t:07x} komp {A[t]:6d}: {len(pos)} Vorkommen im Kopf, "
          f"davon mit Laenge @+4: {len(ok)} {[hex(x) for x in ok[:3]]}")
# Gegenprobe: wie viele ALLER Bloecke stehen ueberhaupt im Kopf?
import collections
have=0; sample=[]
byoff={p:c for p,c,s in anc}
S=set()
for q in range(FIRST-6):
    v=struct.unpack_from('<I',d,q)[0]
    if byoff.get(v)==struct.unpack_from('<H',d,q+4)[0]: S.add(v)
print(f"\nBloecke mit (Offset,Laenge)-Paar im Kopf: {len(S)} von {len(anc)}")
lo=min(S); hi=max(S)
print(f"  Bereich 0x{lo:x}..0x{hi:x}")
srt=sorted(S)
gaps=[(srt[i+1]-srt[i]) for i in range(len(srt)-1)]
print(f"  Nachbarn in Datei-Reihenfolge, Luecke > 100 kB: "
      f"{sum(1 for g in gaps if g>100000)}")
pickle.dump(S, open('gw_headrefs.pkl','wb'))
