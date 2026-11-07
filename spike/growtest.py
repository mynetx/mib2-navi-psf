#!/usr/bin/env python3
"""Wachstumstest 1 (w1): darf ein Block laenger werden als sein Extent?

Die letzte offene Frage des Schreibwegs. Die alten Gegentests (4, 5) sind durch
Gotcha 1 entwertet -- beide hatten einen kaputten 13-B-LZMA-Kopf. Ausweichen in
"freien Platz" faellt aus: die fuenf unklassifizierten Regionen tragen dichte
Daten, die laengste Nullfolge der ganzen Datei ist 6.338 B (FINDINGS §6g).
Bleibt: in den Nachbarn wachsen, dessen Indexeintrag im selben Band umgebogen
wird -- das ist durch Test 7 einzeln belegt.

Drei Sonden, auf drei Zoomstufen getrennt ablesbar:

  z1-z9    @0x36ce94a  Kontrolle  Testort -> Kontrol   Strom EXAKT 12304
  z10-z11  @0x3392334  Wachstum   Testort -> Wachsba   Strom 13896 = Extent+64
  z12      unveraendert                                 zeigt weiter Testort

Der Kniff beim Wachstum: der Payload bleibt BYTEGLEICH LANG (nur 7 Zeichen
getauscht). Der Strom waechst allein ueber die Encoderwahl. Damit hat das
Label dieselbe Gestalt wie Test 11s bewaehrtes `Manneba` -- ein nicht
gezeichnetes Label kann das Ergebnis also nicht verfaelschen. Gemessen wird
ausschliesslich die Frage "darf der Strom laenger sein als der Extent".

Ablesen:
  z1-9 Kontrol + z10-11 Wachsba  -> Wachstum erlaubt, Ziel 3 wird Handwerk
  z1-9 Kontrol + z10-11 leer/alt -> Karte laedt, der gewachsene Block nicht
  Ablehnung oder Absturz         -> Wachstum ist fatal, nur Ersetzen bleibt
"""
import struct, lzma, json, pickle

SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='GermanyWest_Basic.w1.psf'
OLD=b'Testort'

# Block, Marker, mf, nice_len, Soll-Stromlaenge
KONTROLLE=(0x36ce94a, b'Kontrol', lzma.MF_BT2, 12, 12304)
WACHSTUM =(0x3392334, b'Wachsba', lzma.MF_BT2,  6, 13896)

OPFER   = 0x339593c        # direkter Nachfolger von WACHSTUM, 1995 B
PARTNER = 0x33a5403        # Layer-Partner des Opfers: identische BBox, 15740 B
# Referenzen auf OPFER (FINDINGS §6e) und auf WACHSTUM
IH_OPFER, HI_OPFER     = 0x74b7c, 0x3ab254d
IH_WACHST, HI_WACHST   = 0x74b58, 0x3ab1e57


def blk(d, P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:])
    return raw, len(d)-P-len(dec.unused_data)


def build(data, mf, nl):
    """LZMA-alone mit Kopf wie im Original: dict_size und size == len(data)."""
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':len(data),'lc':3,'lp':0,'pb':2,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':0}]
    o=bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
    struct.pack_into('<I',o,1,len(data))
    struct.pack_into('<Q',o,5,len(data))
    chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert chk.decompress(bytes(o))==data and len(chk.unused_data)==0
    return bytes(o)


d=open(SRC,'rb').read(); N=len(d); out=bytearray(d)

# --- die beiden Bloecke bauen -------------------------------------------------
for P, mark, mf, nl, soll in (KONTROLLE, WACHSTUM):
    raw, ext = blk(d, P)
    assert raw.count(OLD)==2, f"@0x{P:07x}: {raw.count(OLD)}x {OLD} statt 2"
    neu = raw.replace(OLD, mark)
    assert len(neu)==len(raw), "Payload muss gleich lang bleiben"
    nb = build(neu, mf, nl)
    assert len(nb)==soll, f"@0x{P:07x}: Strom {len(nb)} != Soll {soll}"
    assert nb[:13]==d[P:P+13], f"@0x{P:07x}: 13-B-Kopf weicht ab"
    out[P:P+len(nb)] = nb
    print(f"@0x{P:07x}  {OLD.decode()} -> {mark.decode()}  Payload {len(neu)} "
          f"(unveraendert)  Strom {len(nb)}  Extent {ext}  ({len(nb)-ext:+d})")

_, ext_wachst = blk(d, WACHSTUM[0])
_, len_partner = blk(d, PARTNER)
delta = WACHSTUM[4] - ext_wachst
print(f"\nWachstum {delta:+d} B laeuft in den Nachfolger @0x{OPFER:07x} hinein "
      f"(1995 B, davon {1995-delta} B tot)")

# --- Indexeintraege: neue Laenge fuer den gewachsenen Block -------------------
assert struct.unpack_from('<IH', d, IH_WACHST) == (WACHSTUM[0], ext_wachst)
assert struct.unpack_from('<HI', d, HI_WACHST) == (ext_wachst, WACHSTUM[0])
struct.pack_into('<H', out, IH_WACHST+4, WACHSTUM[4])
struct.pack_into('<H', out, HI_WACHST,   WACHSTUM[4])
print(f"Laenge im Index @0x{IH_WACHST:x} (<IH>) und @0x{HI_WACHST:x} (<HI>): "
      f"{ext_wachst} -> {WACHSTUM[4]}")

# --- Opfer umbiegen: beide Referenzen auf den Layer-Partner, im selben Band ---
assert struct.unpack_from('<IH', d, IH_OPFER) == (OPFER, 1995)
assert struct.unpack_from('<HI', d, HI_OPFER) == (1995, OPFER)
struct.pack_into('<IH', out, IH_OPFER, PARTNER, len_partner)
struct.pack_into('<HI', out, HI_OPFER, len_partner, PARTNER)
print(f"Opfer @0x{OPFER:07x} umgebogen auf @0x{PARTNER:07x} ({len_partner} B), "
      f"beide Referenzen (<IH> @0x{IH_OPFER:x}, <HI> @0x{HI_OPFER:x})")

assert len(out)==N
open(DST,'wb').write(bytes(out))
json.dump({'grow': {hex(WACHSTUM[0]): WACHSTUM[4]},
           'sacrificed': [hex(OPFER)],
           'note': 'Wachstumstest 1 -- Block waechst +%d B in den Nachfolger' % delta},
          open(DST.replace('.psf','.plan.json'),'w'), indent=1)

# --- Verifikation -------------------------------------------------------------
print("\n--- Verifikation ---")
o=bytes(out)
print(f"Dateigroesse {N} -> {len(o)}  unveraendert: {len(o)==N}")
print(f"geaenderte Bytes: {sum(1 for i in range(N) if d[i]!=o[i])}")
for P, mark, mf, nl, soll in (KONTROLLE, WACHSTUM):
    raw,L=blk(o,P); src,_=blk(d,P)
    assert raw==src.replace(OLD,mark) and L==soll
    print(f"@0x{P:07x}: Strom {L}, entpackt {len(raw)}, "
          f"{mark.decode()}x{raw.count(mark)}, {OLD.decode()}x{raw.count(OLD)}")
# Layer-Partner muss unversehrt sein, Opfer darf kaputt sein
pr,_=blk(o,PARTNER); assert pr==blk(d,PARTNER)[0]
print(f"@0x{PARTNER:07x} (Partner, jetzt doppelt referenziert): unveraendert")
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    if P==OPFER: continue
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke ausser dem Opfer: {ok} dekodieren, {bad} fehlerhaft")
print(f"\ngeschrieben: {DST}")
