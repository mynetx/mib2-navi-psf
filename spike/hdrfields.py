#!/usr/bin/env python3
"""Dateikopf 0x00..0x112: welche u32-Felder haengen an Dateigroesse,
Blockzahl oder Indexbereichen?"""
import struct, pickle, os
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
N=os.path.getsize(SRC)
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p for p,c,s in anc}
d=open(SRC,'rb').read(0x200)
print(f"Dateigroesse {N} = 0x{N:x}, {len(anc)} Bloecke, erster @0x{anc[0][0]:x}")
for o in range(0,0x112,2):
    v=struct.unpack_from('<I',d,o)[0]
    notes=[]
    if v==N: notes.append("== DATEIGROESSE")
    if v==len(anc): notes.append("== BLOCKZAHL")
    if v in A: notes.append("== Blockoffset")
    if 0<v<0x112: notes.append("-> in den Kopf")
    if anc[0][0]<=v<N: notes.append(f"-> Datei +{v}")
    if abs(v-N)<200000 and v!=N: notes.append(f"Dateigroesse {N-v:+d}")
    if notes and o%4==0:
        print(f"  @0x{o:03x} u32 {v:12d} 0x{v:08x}  {' '.join(notes)}")
print("\nKopf 0x00..0x60 als u32-Liste (4er-Raster):")
for o in range(0,0x60,4):
    v=struct.unpack_from('<I',d,o)[0]
    print(f"  @0x{o:03x} {v:12d} 0x{v:08x}")
