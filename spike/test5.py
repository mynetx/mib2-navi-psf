#!/usr/bin/env python3
"""Test 5: Blockwachstum bei KONSTANTER Dateigroesse -- nur Block A.

Test 4 (reloc2, +47.346 B) wurde sauber abgewiesen; die Stoerfaktoren
Schreibschutz und ._AppleDouble sind ausgeraeumt. Test 5 aendert gegenueber
Test 4 genau eine Sache: der Block waechst in seinen direkt angrenzenden
Nachfolger hinein statt an eine neue Position hinter dem alten Dateiende.
Kein Kettenumzug, kein Kopfzeiger, keine Groessenaenderung.

Warum nur Block A: Ziel A @0x36ca22e und sein Nachfolger @0x36ce94a sind die
einzigen beteiligten Bloecke OHNE Zweiteintrag im <HI>-Format (u16 Laenge,
u32 Offset) in der Region ab 0x3ab0873. Ziel B/C und deren Opfer haben dort
je einen -- die muessten mitgezogen werden, und das ist unbewiesen. Test 5
enthaelt damit nur Mechanik, die Test 3 belegt hat.

Kontrollwert: @0x36ce94a traegt `Hausbaz` und liefert laut §6a das Label fuer
z1-z8. Wird es geopfert, muss z1-z8 auf `Testort` umspringen -- daran ist
ablesbar, ob die Indexaenderung ueberhaupt gegriffen hat.

Basis: der akzeptierte Bau aus §6 (patched.psf), groessengleich zum Original.
"""
import struct, lzma, pickle

BASE = 'GermanyWest_Basic.patched.psf'
DST  = 'GermanyWest_Basic.t5.psf'
OLD, NEW = b'Testort', b'RELOBAY'
TGT, VIC, PART = 0x36ca22e, 0x36ce94a, 0x3392334

SET = [{'mf': lzma.MF_BT4, 'depth': 0,   'nice_len': 273},
       {'mf': lzma.MF_BT4, 'depth': 512, 'nice_len': 273},
       {'mf': lzma.MF_BT4, 'depth': 128, 'nice_len': 273},
       {'mf': lzma.MF_BT4, 'depth': 0,   'nice_len': 128},
       {'mf': lzma.MF_HC4, 'depth': 0,   'nice_len': 128},
       {'mf': lzma.MF_HC4, 'depth': 512, 'nice_len': 273},
       {'mf': lzma.MF_BT3, 'depth': 0,   'nice_len': 128}]

def bestc(data, dic):
    ds = max(4096, min(dic, 1 << 26)); best = None
    for s in SET:
        f = [{'id': lzma.FILTER_LZMA1, 'dict_size': ds, 'lc': 3, 'lp': 0,
              'pb': 2, 'mode': lzma.MODE_NORMAL, **s}]
        try: o = lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f)
        except Exception: continue
        if best is None or len(o) < len(best): best = o
    return best

def blk(d, P):
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw = dec.decompress(d[P:])
    return raw, len(d) - P - len(dec.unused_data)

def only(d, pat, what):
    q = d.find(pat)
    assert q >= 0, f"{what} nicht gefunden"
    assert d.find(pat, q + 1) < 0, f"{what} nicht eindeutig"
    return q

d = open(BASE, 'rb').read(); N = len(d)
traw, tlen = blk(d, TGT); vraw, vlen = blk(d, VIC); praw, plen = blk(d, PART)
assert TGT + tlen == VIC, "Nachfolger nicht angrenzend"
assert traw.count(OLD) == 1, f"{traw.count(OLD)}x {OLD} in Ziel A"

# Kein <HI>-Zweiteintrag fuer Ziel und Opfer -- Grundannahme des Tests
for P, L, n in ((TGT, tlen, 'Ziel A'), (VIC, vlen, 'Opfer A')):
    assert d.find(struct.pack('<HI', L, P)) < 0, f"{n} hat doch einen <HI>-Eintrag"

qt = only(d, struct.pack('<IH', TGT, tlen), 'Indexeintrag Ziel A')
qv = only(d, struct.pack('<IH', VIC, vlen), 'Indexeintrag Opfer A')

nb = bestc(traw.replace(OLD, NEW), struct.unpack_from('<I', d, TGT + 1)[0])
room = tlen + vlen
assert len(nb) <= room and len(nb) <= 0xFFFF
print(f"Ziel A  @0x{TGT:07x}  {tlen} -> {len(nb)} ({len(nb)-tlen:+d})   "
      f"Platz {room} (Ziel+Opfer), frei danach {room-len(nb)}")
print(f"Opfer A @0x{VIC:07x}  {vlen} B -> Eintrag zeigt auf Partner @0x{PART:07x} ({plen} B)")

out = bytearray(d)
out[TGT:TGT + len(nb)] = nb
struct.pack_into('<IH', out, qt, TGT, len(nb))     # Ziel: nur die Laenge
struct.pack_into('<IH', out, qv, PART, plen)       # Opfer -> Layer-Partner
assert len(out) == N
open(DST, 'wb').write(bytes(out))

print("\n--- Verifikation ---")
o = bytes(out)
print(f"Groesse {N} -> {len(o)}   unveraendert: {len(o)==N}")
print(f"geaenderte Bytes gegenueber der akzeptierten Basis: "
      f"{sum(1 for i in range(N) if d[i]!=o[i])}   "
      f"(Block {len(nb)} + 2 Laenge + 6 Umbiegung)")
raw, L = blk(o, TGT)
print(f"Ziel A neu: comp={L} plain={len(raw)} RELOBAY×{raw.count(NEW)} Testort×{raw.count(OLD)}")
assert L == len(nb) and raw == traw.replace(OLD, NEW)
print(f"Eintrag Ziel  @0x{qt:x}: {struct.unpack_from('<IH',o,qt)}")
print(f"Eintrag Opfer @0x{qv:x}: {struct.unpack_from('<IH',o,qv)}  (= Partner)")
print(f"Restverweise auf Opfer @0x{VIC:07x} als rohes u32: {o.count(struct.pack('<I',VIC))}")
anc = pickle.load(open('gw_anchors.pkl', 'rb'))
ok = bad = 0
for P, c, s in anc:
    if P == VIC: continue
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64], max_length=32); ok += 1
    except Exception:
        bad += 1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke pruefbar: {ok} ok, {bad} fehlerhaft (Opfer uebersprungen)")
