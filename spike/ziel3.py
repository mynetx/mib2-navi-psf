#!/usr/bin/env python3
"""Ziel 3, erster Bau (z3): eine fehlende OSM-Strasse ins Navi schreiben.

Nach dem bestandenen Wachstumstest w1 (20.09.2026) darf ein Block laenger
werden als sein Extent. Damit ist Einfuegen moeglich, ohne etwas zu streichen.

Eingefuegt wird die `Kelsitstraße` in Testort -- der einzige benannte Weg, den
OSM im Umkreis von 1 km kennt und der im Block fehlt (FINDINGS §6j).

  z1-z9    @0x36ce94a  Kontrollsonde  Testort -> Kontro2   Strom EXAKT 12304
  z10-z11  @0x3392334  Testort bleibt Testort, + Kelsitstraße, Block waechst
  Opfer    @0x339593c  beide Referenzen auf den Layer-Partner @0x33a5403

Die Kontrollsonde sagt, ob die neue Karte ueberhaupt geladen ist -- sonst waere
eine fehlende Kelsitstraße nicht von einer alten Karte zu unterscheiden.
"""
import struct, lzma, json, pickle, math, sys
sys.path.insert(0,'.')
from roadrec import parse_section
from roadwrite import to_units, densify, record

SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='GermanyWest_Basic.z3.psf'
R=6371000.0
ZIEL   = 0x3392334        # Block B, Westkachel, z10-z11
KONTR  = 0x36ce94a        # Westkachel 280k, z1-z9
OPFER  = 0x339593c
PARTNER= 0x33a5403
IH_OPFER, HI_OPFER   = 0x74b7c, 0x3ab254d
IH_ZIEL,  HI_ZIEL    = 0x74b58, 0x3ab1e57
STRASSE='Kelsitstraße'

def blk(d,P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

def build(data, mf, nl):
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':len(data),'lc':3,'lp':0,'pb':2,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':0}]
    o=bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
    struct.pack_into('<I',o,1,len(data)); struct.pack_into('<Q',o,5,len(data))
    chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert chk.decompress(bytes(o))==data and len(chk.unused_data)==0
    return bytes(o)

MFS=[lzma.MF_BT2,lzma.MF_BT3,lzma.MF_BT4,lzma.MF_HC3,lzma.MF_HC4]
def sweep(data, ziel=None):
    """Kleinste Stromlaenge, oder exakter Treffer auf `ziel`."""
    best=(None,None,None)
    for mf in MFS:
        for nl in range(2,274):
            try: o=build(data,mf,nl)
            except Exception: continue
            if ziel is not None and len(o)==ziel: return len(o),mf,nl
            if best[0] is None or len(o)<best[0]: best=(len(o),mf,nl)
    return best

d=open(SRC,'rb').read(); N=len(d); out=bytearray(d)

# --- 1. Kelsitstrasse aus OSM zu Recordbytes ---------------------------------
raw,ext = blk(d, ZIEL)
X0,Y0,X1,Y1 = struct.unpack_from('<4i', raw, 0); S=18.0
W,H = int((X1-X0)/S), int((Y1-Y0)/S)
osm=json.load(open('osm/osm_west.json'))['elements']
w=[e for e in osm if e.get('tags',{}).get('name')==STRASSE]
assert len(w)==1, f"{len(w)} OSM-Wege namens {STRASSE}"
pts=[to_units(p['lat'],p['lon'],X0,Y0,S) for p in w[0]['geometry']]
rec=record(densify(pts), STRASSE)

recs=parse_section(raw,7709,W,H)
assert not any(r['name']==STRASSE for r in recs), f"{STRASSE} steht schon drin"
ling=[r for r in recs if r['name']=='Nachbarorter Straße'][0]
ins=ling['end']; rahmen=raw[ins:ins+7]
neu_payload = raw[:ins] + rahmen + rec + raw[ins:]

ll=lambda x,y:(math.degrees(2*math.atan(math.exp((Y0+y*S)/R))-math.pi/2),
               math.degrees((X0+x*S)/R))
la,lo = ll(*[int(round(v)) for v in pts[0]])
print(f"{STRASSE}: {len(w[0]['geometry'])} OSM-Stuetzpunkte -> Record {len(rec)} B")
print(f"   Startpunkt {la:.5f} N / {lo:.5f} E")
print(f"   eingefuegt @{ins} hinter 'Nachbarorter Straße', Rahmung {rahmen.hex(' ')}")
print(f"   Payload {len(raw)} -> {len(neu_payload)} ({len(neu_payload)-len(raw):+d} B)")

L,mf,nl = sweep(neu_payload)
nb = build(neu_payload, mf, nl)
# Der Payload waechst -> dict_size und size MUESSEN sich aendern. Geprueft wird
# deshalb die echte Invariante (Gotcha 2), nicht Byteidentitaet zum Original:
assert nb[0]==d[ZIEL]==93, "props-Byte"
assert struct.unpack_from('<I',nb,1)[0]==len(neu_payload), "dict_size != entpackte Groesse"
assert struct.unpack_from('<Q',nb,5)[0]==len(neu_payload), "size != entpackte Groesse"
assert len(nb)==L
print(f"   Strom {L}, Extent {ext} ({L-ext:+d}) -- waechst in den Nachfolger")
assert ext < L <= ext+1995, "Wachstum passt nicht in den Opferblock"
out[ZIEL:ZIEL+L]=nb

# --- 2. Kontrollsonde, laengenneutral ----------------------------------------
kraw,kext = blk(d, KONTR)
kneu = kraw.replace(b'Testort', b'Kontro2')
assert len(kneu)==len(kraw)
kL,kmf,knl = sweep(kneu, ziel=kext)
assert kL==kext, f"Kontrollsonde trifft {kext} nicht"
kb = build(kneu,kmf,knl)
assert kb[:13]==d[KONTR:KONTR+13]
out[KONTR:KONTR+kext]=kb
print(f"Kontrollsonde @0x{KONTR:07x}: Testort -> Kontro2, Strom {kL} == Extent {kext}")

# --- 3. Index: neue Laenge fuers Ziel, Opfer umbiegen ------------------------
_, len_partner = blk(d, PARTNER)
assert struct.unpack_from('<IH', d, IH_ZIEL)==(ZIEL, ext)
assert struct.unpack_from('<HI', d, HI_ZIEL)==(ext, ZIEL)
struct.pack_into('<H', out, IH_ZIEL+4, L)
struct.pack_into('<H', out, HI_ZIEL,   L)
assert struct.unpack_from('<IH', d, IH_OPFER)==(OPFER, 1995)
struct.pack_into('<IH', out, IH_OPFER, PARTNER, len_partner)
struct.pack_into('<HI', out, HI_OPFER, len_partner, PARTNER)
print(f"Index: Ziel-Laenge {ext} -> {L}; Opfer @0x{OPFER:07x} -> @0x{PARTNER:07x}")

assert len(out)==N
open(DST,'wb').write(bytes(out))
json.dump({'grow':{hex(ZIEL):L}, 'sacrificed':[hex(OPFER)],
           'note':f'Ziel 3 Bau 1 -- {STRASSE} eingefuegt, Block waechst +{L-ext} B'},
          open(DST.replace('.psf','.plan.json'),'w'), indent=1)

# --- Verifikation -------------------------------------------------------------
print("\n--- Verifikation ---")
o=bytes(out)
print(f"Dateigroesse {N} -> {len(o)}  unveraendert: {len(o)==N}")
r2,L2 = blk(o, ZIEL)
r2recs = parse_section(r2, 7709, W, H)
treffer=[x for x in r2recs if x['name']==STRASSE]
print(f"Ziel @0x{ZIEL:07x}: Strom {L2}, entpackt {len(r2)}, "
      f"Testort x{r2.count(b'Testort')}")
print(f"   {STRASSE} vom Decoder wiedergefunden: {len(treffer)}x, "
      f"n={treffer[0]['n']}, Punkte {len(treffer[0]['points'])}")
assert len(treffer)==1
k2,_ = blk(o, KONTR)
print(f"Kontrolle @0x{KONTR:07x}: Kontro2 x{k2.count(b'Kontro2')}, "
      f"Testort x{k2.count(b'Testort')}")
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    if P==OPFER: continue
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke ausser dem Opfer: {ok} dekodieren, {bad} fehlerhaft")
print(f"\ngeschrieben: {DST}")
