#!/usr/bin/env python3
"""Traegt der Dateikopf eine Pruefsumme ueber Kopf-/Indexbereich?
Der frueher AKZEPTIERTE Patch aenderte nur Blockinhalte (Kopf/Index unberuehrt),
der jetzt ABGELEHNTE aenderte Kopf, Index und Dateigroesse. Eine Pruefsumme
ueber den Kopfbereich wuerde genau das erklaeren."""
import struct, zlib, pickle
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
FIRST=anc[0][0]
d=open(SRC,'rb').read(); N=len(d)
cand=[(o,struct.unpack_from('<I',d,o)[0]) for o in range(0,0x112)]
cand+=[(o,struct.unpack_from('>I',d,o)[0]) for o in range(0,0x112)]
vals={v for o,v in cand if v>0xFFFF}
print(f"{len(vals)} Kandidatenwerte im Kopf (>0xFFFF)")

RANGES={
 'Kopf 0..0x112': (0,0x112),
 'Index 0x112..FIRST': (0x112,FIRST),
 'Kopf+Index 0..FIRST': (0,FIRST),
 'Index 0x10e..FIRST': (0x10e,FIRST),
 'Daten FIRST..N': (FIRST,N),
 'alles': (0,N),
 'Kopf 0x56..0x112': (0x56,0x112),
}
def sum32(b): return sum(b)&0xFFFFFFFF
FUN={'crc32':lambda b: zlib.crc32(b)&0xFFFFFFFF,
     'adler':lambda b: zlib.adler32(b)&0xFFFFFFFF,
     'sum32':sum32,
     'xor32':lambda b: __import__('functools').reduce(
         lambda a,x:a^x,struct.unpack(f'<{len(b)//4}I',b[:len(b)//4*4]),0)}
hit=False
for rn,(a,b) in RANGES.items():
    seg=d[a:b]
    for fn,f in FUN.items():
        v=f(seg)
        if v in vals:
            pos=[hex(o) for o,x in cand if x==v]
            print(f"  TREFFER {fn} ueber {rn} = 0x{v:08x}  Feldposition {pos}")
            hit=True
if not hit: print("  kein Treffer")

# Variante: Pruefsumme mit ausgespartem Feld (klassisch: Feld selbst auf 0)
print("\nVariante 'Feld beim Rechnen genullt':")
hit=False
for o in range(0,0x112-3):
    v=struct.unpack_from('<I',d,o)[0]
    if v<=0xFFFF: continue
    for rn,(a,b) in RANGES.items():
        if not (a<=o<b): continue
        seg=bytearray(d[a:b]); struct.pack_into('<I',seg,o-a,0)
        if (zlib.crc32(bytes(seg))&0xFFFFFFFF)==v:
            print(f"  TREFFER crc32 ueber {rn}, Feld @0x{o:x}"); hit=True
        if sum32(seg)==v:
            print(f"  TREFFER sum32 ueber {rn}, Feld @0x{o:x}"); hit=True
if not hit: print("  kein Treffer")
