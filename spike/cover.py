#!/usr/bin/env python3
"""Abdeckung: wie viele der 76.003 Bloecke haben einen Klartext-Indexeintrag,
wenn die Laenge auch ohne die 14-B-Fuellung zaehlt?"""
import struct, pickle
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
u32=lambda o: struct.unpack_from('<I',d,o)[0]
u16=lambda o: struct.unpack_from('<H',d,o)[0]
gapof={p:c for p,c,s in anc}
ref=set(); refany=set()
for q in range(FIRST-6):
    v=u32(q)
    g=gapof.get(v)
    if g is None: continue
    L=u16(q+4)
    if L==g or L==g-14: ref.add(v)
    refany.add((v,L))
print(f"Bloecke mit Klartext-Eintrag (Laenge == Abstand oder Abstand-14): "
      f"{len(ref)} von {len(anc)} ({len(ref)*100//len(anc)} %)")
# Wo liegen die nicht abgedeckten?
missing=[p for p,c,s in anc if p not in ref]
print(f"nicht abgedeckt: {len(missing)}")
print(f"   erster @0x{missing[0]:x}, letzter @0x{missing[-1]:x}")
# Laufen abgedeckte und fehlende in Bloecken?
runs=[]; cur=None
allp=[p for p,c,s in anc]
for p in allp:
    m = p not in ref
    if cur is None or cur[0]!=m: 
        if cur: runs.append(cur)
        cur=[m,1]
    else: cur[1]+=1
runs.append(cur)
print(f"   {len(runs)} Laeufe abwechselnd; laengste fehlende Laeufe: "
      f"{sorted([r[1] for r in runs if r[0]], reverse=True)[:10]}")
print(f"   laengste abgedeckte Laeufe: "
      f"{sorted([r[1] for r in runs if not r[0]], reverse=True)[:10]}")
