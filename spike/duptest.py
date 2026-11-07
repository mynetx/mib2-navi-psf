#!/usr/bin/env python3
"""Entscheidender Versuch: den Block mit TESTBA2 aus dem Klartextindex nehmen.

Basis wieder GermanyWest_Basic.patched.psf (akzeptiert).
Beide Eintraege des L10-Layerpaares zeigen danach auf @0x2f34830 (TESTBA1).
@0x2f4009f (TESTBA2) ist dann von KEINEM Klartexteintrag mehr referenziert --
geprueft ueber die ganze Datei.

  z12 zeigt TESTBA1 -> der Klartextindex bestimmt, was geladen wird
  z12 zeigt TESTBA2 -> er tut es nicht; die Bloecke werden anders gefunden
"""
import struct, os, lzma
BASE='../spike/GermanyWest_Basic.patched.psf'
DST ='../spike/GermanyWest_Basic.dup.psf'
A=(0x2f4009f,15490)   # TESTBA2 - soll unerreichbar werden
B=(0x2f34830,16494)   # TESTBA1 - beide Eintraege zeigen danach hierher

d=bytearray(open(BASE,'rb').read())
qa=d.find(struct.pack('<IH',*A))
assert qa>=0 and d.find(struct.pack('<IH',*A),qa+1)<0
struct.pack_into('<IH', d, qa, *B)
open(DST,'wb').write(bytes(d))

o=open(BASE,'rb').read(); n=open(DST,'rb').read()
diff=[i for i in range(len(o)) if o[i]!=n[i]]
print(f"Groesse {os.path.getsize(BASE)} -> {os.path.getsize(DST)}  "
      f"gleich: {os.path.getsize(BASE)==os.path.getsize(DST)}")
print(f"geaenderte Bytes: {len(diff)} @0x{min(diff):x}..0x{max(diff):x}")
print(f"Kopf unveraendert: {o[:0x112]==n[:0x112]}   "
      f"Datenbereich unveraendert: {o[0x92b24:]==n[0x92b24:]}")
# Ist TESTBA2s Block wirklich nirgends mehr referenziert?
pat=struct.pack('<IH',*A); print(f"(Offset,Laenge) von @0x{A[0]:x} noch in der Datei: "
      f"{n.count(pat)}x")
pat4=struct.pack('<I',A[0]); print(f"blosser Offset 0x{A[0]:x} noch in der Datei: "
      f"{n.count(pat4)}x")
for q in (qa, d.find(struct.pack('<IH',*B))):
    off,ln=struct.unpack_from('<IH',n,q)
    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(n[off:off+ln])
    print(f"  Eintrag @0x{q:x} -> @0x{off:x}: "
          f"{[m.decode() for m in (b'TESTBA1',b'TESTBA2') if m in r]}")
