#!/usr/bin/env python3
"""Sonde 1: ist die Geometrie im Block kachelrelativ oder absolut?

Basis ist der BESTANDENE Test 11 (…t11.psf), in dem Block B auf z10-z11
`Manneba` zeigt. Einzige Aenderung: im 20-B-Blockkopf werden minX und maxX
um +5000 m verschoben, die Kachel wandert also 5 km nach Osten. Breite,
Hoehe und alles andere bleiben.

  Inhalt wandert mit  -> Koordinaten sind KACHELRELATIV, der Blockkopf ist der
                         Anker. Damit ist die absolute Platzierung (§7.3) gelöst
                         und neue Geometrie platzierbar.
  Inhalt bleibt       -> Koordinaten sind ABSOLUT in Mercator-Metern, der Kopf
                         ist nur BBox/Clip.

Laengenzwang: der Strom muss wieder exakt 13832 B treffen. Vernier ist der
Markername -- 7-Zeichen-Ketten, die im Block vorkommen, kosten unterschiedlich
viel (§6h).
"""
import lzma, struct, re, itertools

BASE='GermanyWest_Basic.t11.psf'; DST='GermanyWest_Basic.p1.psf'
P=0x3392334; SHIFT=5000
MF=[lzma.MF_BT4,lzma.MF_BT3,lzma.MF_BT2,lzma.MF_HC4,lzma.MF_HC3]
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
bb=struct.unpack_from('<4i',raw,0)
print(f"Block B @0x{P:07x}: Extent {EXT}, plain {len(raw)}")
print(f"   BBox alt {bb}  Breite {bb[2]-bb[0]} m")

mod=bytearray(raw)
struct.pack_into('<i',mod,0,bb[0]+SHIFT)      # minX
struct.pack_into('<i',mod,8,bb[2]+SHIFT)      # maxX
print(f"   BBox neu {struct.unpack_from('<4i',mod,0)}  (+{SHIFT} m nach Osten)")

# Vernier: aktuellen Marker gegen Kandidaten tauschen, bis die Laenge exakt passt
CUR=b'Manneba'
cands=[CUR]+sorted({s for s in re.findall(rb'[A-Z][a-z]{6}',bytes(mod))}-{CUR})
hit=None
for m in cands:
    data=bytes(mod).replace(CUR,m) if m!=CUR else bytes(mod)
    for mf,nl,dp in itertools.product(MF,NICE,DEPTH):
        o=build(data,mf,nl,dp)
        if len(o)==EXT:
            chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            assert chk.decompress(o)==data and len(chk.unused_data)==0
            hit=(m,o,data,(mf,nl,dp)); break
    if hit: break
assert hit, "keine Kombination trifft den Extent exakt"
m,o,data,par=hit
print(f"   Marker {m.decode()}  Strom {len(o)} == Extent {EXT}  cfg={par[1]}/{par[2]}")

assert o[:13]==d[P:P+13], "13-B-Kopf weicht ab"
out=bytearray(d); out[P:P+EXT]=o
assert len(out)==len(d)
open(DST,'wb').write(bytes(out))
oo=bytes(out)
print("\n--- Verifikation ---")
print(f"Groesse unveraendert: {len(oo)==len(d)}   geaenderte Bytes: "
      f"{sum(1 for i in range(len(d)) if d[i]!=oo[i])}")
chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE); r2=chk.decompress(oo[P:])
print(f"BBox im Bau: {struct.unpack_from('<4i',r2,0)}")
print(f"Kopf byteidentisch: {oo[P:P+13]==d[P:P+13]}   Marker {m.decode()}×{r2.count(m)}")
q=d.find(struct.pack('<IH',P,EXT))
print(f"Indexeintrag @0x{q:x} unveraendert: {struct.unpack_from('<IH',oo,q)}")
import pickle
ok=bad=0
for Q,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(oo[Q:Q+c+64],max_length=32); ok+=1
    except Exception: bad+=1
print(f"Bloecke pruefbar: {ok} ok, {bad} fehlerhaft")
