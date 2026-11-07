#!/usr/bin/env python3
"""Isolierender Versuch: eine einzige neue Variable gegenueber einem Bau,
den das Geraet nachweislich akzeptiert hat.

Basis: GermanyWest_Basic.patched.psf (Akzeptanztest bestanden, §6/§6a).
       Marker TESTBA1 @0x2f34830, TESTBA2 @0x2f4009f, Hausbaz @0x36ce94a.
       Im Auto lieferte z12 'TESTBA2'.
Neu:   die Felder (Offset, Laenge) der beiden L10-Indexeintraege werden
       getauscht -- 10 Bytes. Nichts verschoben, Groesse gleich, Kopf und
       Dateiende unberuehrt.

Lesart im Auto, z12 ueber Testort:
  TESTBA1  -> Index wird befolgt und ist schreibbar. Der Fehlschlag vorhin
              lag am Dateiwachstum, nicht am Index.
  TESTBA2  -> Index wird ignoriert; Bloecke werden anders gefunden.
  Karte abgewiesen -> der Indexbereich ist geschuetzt.
"""
import struct, os, lzma
BASE='../spike/GermanyWest_Basic.patched.psf'
DST ='../spike/GermanyWest_Basic.swap.psf'
A=(0x2f4009f,15490)   # traegt TESTBA2, liefert das Label auf z12
B=(0x2f34830,16494)   # traegt TESTBA1, Layerpartner

d=bytearray(open(BASE,'rb').read())
qa=d.find(struct.pack('<IH',*A)); qb=d.find(struct.pack('<IH',*B))
assert qa>=0 and qb>=0
assert d.find(struct.pack('<IH',*A),qa+1)<0 and d.find(struct.pack('<IH',*B),qb+1)<0
assert struct.unpack_from('<4i',d,qa-16)==struct.unpack_from('<4i',d,qb-16)
struct.pack_into('<IH', d, qa, *B)
struct.pack_into('<IH', d, qb, *A)
open(DST,'wb').write(bytes(d))

o=open(BASE,'rb').read(); n=open(DST,'rb').read()
diff=[i for i in range(len(o)) if o[i]!=n[i]]
print(f"Basis {os.path.getsize(BASE)} -> neu {os.path.getsize(DST)}  "
      f"gleich: {os.path.getsize(BASE)==os.path.getsize(DST)}")
print(f"geaenderte Bytes: {len(diff)}, alle im Indexbereich: {max(diff)<0x92b24}")
print(f"Kopf 0..0x112 unveraendert: {o[:0x112]==n[:0x112]}")
print(f"Datenbereich ab 0x92b24 unveraendert: {o[0x92b24:]==n[0x92b24:]}")
for q,lbl in ((qa,'Eintrag der Label-Kachel'),(qb,'Eintrag des Layerpartners')):
    off,ln=struct.unpack_from('<IH',n,q)
    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(n[off:off+ln])
    mk=[m.decode() for m in (b'TESTBA1',b'TESTBA2') if m in r]
    print(f"  {lbl} -> @0x{off:x} len {ln}: Marker {mk}")
