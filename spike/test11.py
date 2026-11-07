#!/usr/bin/env python3
"""Test 11: Marker unter Einhaltung JEDER gemessenen Invariante.

Ursache der vier Abstuerze/Ablehnungen (T5, T8, T9, T10), gefunden am
13-Byte-LZMA-Kopf: `lzma.compress(FORMAT_ALONE)` schreibt
    dict_size = aufgerundet (24576 statt 20467)
    size      = 0xFFFFFFFFFFFFFFFF (unbekannt)
waehrend JEDER der 76.003 Originalbloecke dict_size == entpackte Groesse und
die echte Groesse traegt. Der akzeptierte §6-Bau hatte den Kopf nachgezogen,
meine Skripte nicht. Alle daraus gezogenen Schluesse -- Bandwechsel,
Blockwachstum, Marker -- waren Artefakte davon.

Invarianten, die dieser Bau einhaelt (alle an 76.003 Bloecken gemessen):
  props-Byte      93 (lc=3 lp=0 pb=2), ausnahmslos in der ganzen Datei
  dict_size       == entpackte Groesse
  size            == entpackte Groesse
  Stromlaenge     == Extent, auf das Byte genau (kein totes Byte)
  Indexeintraege  unveraendert
  Dateigroesse    unveraendert
"""
import struct, lzma, pickle

BASE='GermanyWest_Basic.patched.psf'; DST='GermanyWest_Basic.t11.psf'
OLD=b'Testort'
JOBS=[('B', 0x3392334, b'Manneba', lzma.MF_BT2, 16, 0),
      ('C', 0x346c45e, b'Badenha', lzma.MF_BT2, 16, 0)]

def blk(d,P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

def build(data, mf, nl, dp):
    """LZMA-alone mit Kopf wie im Original: dict_size und size == len(data)."""
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':len(data),'lc':3,'lp':0,'pb':2,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':dp}]
    o=bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
    struct.pack_into('<I',o,1,len(data))      # dict_size  = entpackte Groesse
    struct.pack_into('<Q',o,5,len(data))      # size       = entpackte Groesse
    chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    r=chk.decompress(bytes(o))
    assert r==data and len(chk.unused_data)==0, "Kopfkorrektur bricht den Strom"
    return bytes(o)

d=open(BASE,'rb').read(); N=len(d); out=bytearray(d); plan=[]
for tag,P,mark,mf,nl,dp in JOBS:
    raw,ext=blk(d,P)
    occ=raw.count(OLD); assert occ>0
    nb=build(raw.replace(OLD,mark), mf, nl, dp)
    assert len(nb)==ext, f"{tag}: {len(nb)} != Extent {ext}"
    assert nb[:13]==d[P:P+13], f"{tag}: Kopf weicht vom Original ab"
    plan.append((tag,P,ext,nb,mark,occ))
    print(f"Ziel {tag} @0x{P:07x}  {occ}x {OLD.decode()} -> {mark.decode()}   "
          f"Strom {len(nb)} == Extent {ext}   Kopf byteidentisch zum Original")

for tag,P,ext,nb,mark,occ in plan: out[P:P+ext]=nb
assert len(out)==N
open(DST,'wb').write(bytes(out))

print("\n--- Verifikation ---")
o=bytes(out)
print(f"Groesse {N} -> {len(o)}   unveraendert: {len(o)==N}")
print(f"geaenderte Bytes: {sum(1 for i in range(N) if d[i]!=o[i])}"
      f"   (nur innerhalb der zwei Blockextents)")
for tag,P,ext,nb,mark,occ in plan:
    raw,L=blk(o,P); src,_=blk(d,P)
    assert raw==src.replace(OLD,mark) and L==ext
    hp,hd,hs=o[P],struct.unpack_from('<I',o,P+1)[0],struct.unpack_from('<Q',o,P+5)[0]
    print(f"Ziel {tag} @0x{P:07x}: props={hp} dict={hd} size={hs} plain={len(raw)}"
          f"  {mark.decode()}×{raw.count(mark)} {OLD.decode()}×{raw.count(OLD)}")
    q=d.find(struct.pack('<IH',P,ext))
    print(f"   Indexeintrag @0x{q:x}: {struct.unpack_from('<IH',o,q)} "
          f"== {struct.unpack_from('<IH',d,q)} unveraendert")
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke pruefbar: {ok} ok, {bad} fehlerhaft (kein Block uebersprungen)")
