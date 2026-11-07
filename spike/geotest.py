#!/usr/bin/env python3
"""Geometrietest: einen Strassenrecord auf eine unverwechselbare Form umschreiben.

Die Deltakodierung (§6j) ist bisher NUR gegen OSM belegt, nie im Geraet. Dieser
Bau aendert an `Ortsgammaer Strasse` @12474 (2,3 km von Testort, 9 Deltas,
f=0x00) ausschliesslich die neun Deltabytes: statt des echten Verlaufs ein
geschlossenes Quadrat von 252 m Kantenlaenge.

  07 07  ->  2x (dx=+7, dy=0)   252 m nach Osten
  70 70  ->  2x (dx=0, dy=+7)   252 m nach Norden
  09 09  ->  2x (dx=-7, dy=0)   zurueck nach Westen
  90 90  ->  2x (dx=0, dy=-7)   zurueck nach Sueden   -> geschlossen
  <v>    ->  Vernier: letztes Byte stellt die Stromlaenge exakt ein

Basis ist der im Fahrzeug bestandene Test 11. Alle Invarianten bleiben:
props 93, dict/size == entpackte Groesse, Strom exakt == Extent, kein
Indexeintrag angefasst, Dateigroesse unveraendert.
"""
import lzma, struct, itertools, sys
sys.path.insert(0,'.')

BASE='GermanyWest_Basic.t11.psf'; DST='GermanyWest_Basic.geo.psf'
P=0x3392334; REC=12474; NDELTA=9
SQUARE=bytes([0x07,0x07,0x70,0x70,0x09,0x09,0x90,0x90])   # 8 Bytes, geschlossen
MF=[lzma.MF_BT2,lzma.MF_BT3,lzma.MF_BT4,lzma.MF_HC4,lzma.MF_HC3]
NICE=[8,16,32,64,96,128,192,273]; DEPTH=[0,16,64,256,1024]

def build(data,mf,nl,dp):
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':len(data),'lc':3,'lp':0,'pb':2,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':dp}]
    o=bytearray(lzma.compress(data,format=lzma.FORMAT_ALONE,filters=f))
    struct.pack_into('<I',o,1,len(data)); struct.pack_into('<Q',o,5,len(data))
    return bytes(o)

d=open(BASE,'rb').read()
dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
raw=dec.decompress(d[P:]); EXT=len(d)-P-len(dec.unused_data)
n=raw[REC+1]; f=raw[REC+2]; x,y=struct.unpack_from('<HH',raw,REC+3)
old=raw[REC+7:REC+7+NDELTA]
print(f"Record @{REC}: n={n} f={f:#04x} X={x} Y={y}")
print(f"   Deltas alt: {old.hex(' ')}")
assert n==NDELTA and f==0, "unerwarteter Record"
tc=lambda v: v-16 if v>=8 else v
p=[(x,y)]
for by in old: p.append((p[-1][0]+tc(by&15), p[-1][1]+tc(by>>4)))
print(f"   Verlauf alt: {p}")

import re
def sq(k):
    """geschlossenes Quadrat, Kantenlaenge 2*k Einheiten"""
    e=bytes([k]); n=bytes([k<<4]); w=bytes([(16-k)&15]); s_=bytes([((16-k)&15)<<4])
    return e+e+n+n+w+w+s_+s_
def zz(k):
    """Sagezahn: abwechselnd nach Nordost und Suedost"""
    a=bytes([(k<<4)|k]); b=bytes([(((16-k)&15)<<4)|k])
    return (a+b)*4
SHAPES=[('Quadrat %d'%k, sq(k)) for k in (7,6,5,4,3)] + \
       [('Sagezahn %d'%k, zz(k)) for k in (7,6,5,4)]
MARKS=[b'Manneba']+sorted({m for m in re.findall(rb'[A-Z][a-z]{6}',raw)}-{b'Manneba'})[:40]
hit=None
for shname,base8 in SHAPES:
    for mark in MARKS:
        src=raw.replace(b'Manneba',mark) if mark!=b'Manneba' else raw
        for tail in range(1,256):
            nd=base8+bytes([tail])
            mod=bytearray(src); mod[REC+7:REC+7+NDELTA]=nd
            for mf,nl,dp in ((lzma.MF_BT2,16,0),(lzma.MF_BT2,32,0),(lzma.MF_BT3,16,0),
                             (lzma.MF_BT4,273,0),(lzma.MF_BT4,128,0),(lzma.MF_HC4,16,64)):
                o=build(bytes(mod),mf,nl,dp)
                if len(o)==EXT:
                    chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                    assert chk.decompress(o)==bytes(mod) and len(chk.unused_data)==0
                    hit=(tail,o,bytes(mod),(nl,dp)); SQUARE=base8
                    print(f"   Treffer: {shname}, Marker {mark.decode()}, "
                          f"Vernier {tail:#04x}, cfg {nl}/{dp}")
                    break
            if hit: break
        if hit: break
    if hit: break
assert hit, "keine Kombination trifft den Extent exakt"
tail,o,mod,par=hit
nd=hit[2][REC+7:REC+7+NDELTA]
print(f"\n   Deltas neu: {nd.hex(' ')}   (Vernier-Byte {tail:#04x}, cfg {par[0]}/{par[1]})")
q=[(x,y)]
for by in nd: q.append((q[-1][0]+tc(by&15), q[-1][1]+tc(by>>4)))
print(f"   Verlauf neu: {q}")
assert o[:13]==d[P:P+13], "13-B-Kopf weicht ab"
out=bytearray(d); out[P:P+EXT]=o
assert len(out)==len(d)
open(DST,'wb').write(bytes(out))
print(f"\n   Strom {len(o)} == Extent {EXT}, Kopf byteidentisch, Datei {len(out)} B")
print(f"   geaenderte Bytes gegenueber t11: "
      f"{sum(1 for i in range(len(d)) if d[i]!=out[i])}")
