#!/usr/bin/env python3
"""Test 9: Bisektion von Test 8 -- genau eine Variable anders: der Marker.

Zwei Hypothesen erklaeren alle sechs Fahrzeugtests gleich gut:

  (M) `RELOBAY` im Blockinhalt ist das Problem
  (W) ein physisch gewachsener Block ist das Problem

           Inhalt  Marker    Wachstum  Umbiegung  Format D  Ergebnis
  §6-Bau   ja      Hausbaz   nein      nein       nein      akzeptiert
  Test 6   nein    -         nein      nein       nein      akzeptiert
  Test 7   nein    -         nein      in-band    nein      akzeptiert
  Test 5   ja      RELOBAY   +18       cross-band nein      ABSTURZ
  Test 8   ja      RELOBAY   +25/+26   in-band    ja        ABSTURZ

Marker und Wachstum sind in beiden Abstuerzen gemeinsam vorhanden und in allen
akzeptierten Bauten gemeinsam abwesend. Format D und die Umbiegung sind durch
Test 5 (ohne Format D) bzw. Test 7 entlastet.

Test 9 ist Test 8 mit `Hausbaq` statt `RELOBAY` -- dieselbe Markerklasse wie
das im §6-Bau akzeptierte `Hausbaz` (nur das letzte Zeichen), aber von
`Testort` (Original, ab z10) und `Hausbaz` (z1-z9) unterscheidbar.

  Absturz    -> (W): ein Block darf physisch nicht wachsen. Marker entlastet.
                 Dann ist der Weg: in die Originallaenge hineinkomprimieren.
  z10+ zeigt
  `Hausbaq`  -> (M): Wachstum ist erlaubt, der Inhalt wird geprueft oder von
                 aussen referenziert. Schreibweg offen, Marker muss passen.
"""
import struct, lzma, pickle

BASE='GermanyWest_Basic.patched.psf'; DST='GermanyWest_Basic.t9.psf'
OLD, NEW = b'Testort', b'Hausbaq'
JOBS=[('B', 0x3392334, 0x339593c, 0x33a5403),
      ('C', 0x346c45e, 0x346ffe7, 0x346a990)]

SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},{'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':128,'nice_len':273},{'mf':lzma.MF_BT4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':0,'nice_len':128},{'mf':lzma.MF_HC4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT3,'depth':0,'nice_len':128}]

def bestc(data, dic, props):
    lc=props%9; lp=(props//9)%5; pb=props//45          # Parameter des ORIGINALS
    ds=max(4096,min(dic,1<<26)); best=None
    for s in SET:
        f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':lc,'lp':lp,'pb':pb,
            'mode':lzma.MODE_NORMAL,**s}]
        try: o=lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f)
        except Exception: continue
        if best is None or len(o)<len(best): best=o
    return best

def blk(d,P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

def only(d,pat,what):
    q=d.find(pat); assert q>=0, f"{what} fehlt"
    assert d.find(pat,q+1)<0, f"{what} nicht eindeutig"
    return q

d=open(BASE,'rb').read(); N=len(d); out=bytearray(d); plan=[]
for tag,tgt,vic,part in JOBS:
    traw,tlen=blk(d,tgt); vraw,vlen=blk(d,vic); praw,plen=blk(d,part)
    assert tgt+tlen==vic, f"{tag}: Nachfolger nicht angrenzend"
    occ=traw.count(OLD); assert occ>0
    nb=bestc(traw.replace(OLD,NEW), struct.unpack_from('<I',d,tgt+1)[0], d[tgt])
    assert len(nb)<=tlen+vlen and len(nb)<=0xFFFF
    p=dict(tag=tag,tgt=tgt,vic=vic,part=part,tlen=tlen,vlen=vlen,plen=plen,nb=nb,occ=occ,
           ih_t=only(d,struct.pack('<IH',tgt,tlen),f'{tag} <IH Ziel'),
           ih_v=only(d,struct.pack('<IH',vic,vlen),f'{tag} <IH Opfer'),
           hi_t=only(d,struct.pack('<HI',tlen,tgt),f'{tag} <HI Ziel'),
           hi_v=only(d,struct.pack('<HI',vlen,vic),f'{tag} <HI Opfer'))
    plan.append(p)
    print(f"Ziel {tag} @0x{tgt:07x} {occ}x{OLD.decode()}  {tlen} -> {len(nb)} ({len(nb)-tlen:+d})"
          f"   Platz {tlen+vlen}, frei danach {tlen+vlen-len(nb)}")
    print(f"        Opfer @0x{vic:07x} ({vlen} B) -> Partner @0x{part:07x} ({plen} B), BBox identisch")
    print(f"        <IH Ziel 0x{p['ih_t']:x}  <IH Opfer 0x{p['ih_v']:x}"
          f"  <HI Ziel 0x{p['hi_t']:x}  <HI Opfer 0x{p['hi_v']:x}")

for p in plan: out[p['tgt']:p['tgt']+len(p['nb'])]=p['nb']
for p in plan:
    struct.pack_into('<IH',out,p['ih_t'],p['tgt'],len(p['nb']))   # A-Record: Laenge
    struct.pack_into('<HI',out,p['hi_t'],len(p['nb']),p['tgt'])   # D-Record: Laenge
    struct.pack_into('<IH',out,p['ih_v'],p['part'],p['plen'])     # A-Record: Opfer -> Partner
    struct.pack_into('<HI',out,p['hi_v'],p['plen'],p['part'])     # D-Record: Opfer -> Partner
assert len(out)==N
open(DST,'wb').write(bytes(out))

print("\n--- Verifikation ---")
o=bytes(out)
print(f"Groesse {N} -> {len(o)}   unveraendert: {len(o)==N}")
print(f"geaenderte Bytes: {sum(1 for i in range(N) if d[i]!=o[i])}")
for p in plan:
    raw,L=blk(o,p['tgt'])
    assert L==len(p['nb']) and raw==blk(d,p['tgt'])[0].replace(OLD,NEW)
    print(f"Ziel {p['tag']} @0x{p['tgt']:07x}: comp={L} plain={len(raw)} "
          f"RELOBAY×{raw.count(NEW)} Testort×{raw.count(OLD)}")
    print(f"   <IH {struct.unpack_from('<IH',o,p['ih_t'])}  "
          f"<HI {struct.unpack_from('<HI',o,p['hi_t'])}")
    print(f"   Opfer-Records -> <IH {struct.unpack_from('<IH',o,p['ih_v'])}  "
          f"<HI {struct.unpack_from('<HI',o,p['hi_v'])}")
    print(f"   Restverweise auf Opfer @0x{p['vic']:07x} als rohes u32: "
          f"{o.count(struct.pack('<I',p['vic']))}")
skip={p['vic'] for p in plan}
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    if P in skip: continue
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke pruefbar: {ok} ok, {bad} fehlerhaft")
