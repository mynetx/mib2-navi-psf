#!/usr/bin/env python3
"""Bau f1 -- e1 stuerzte ab; f1 setzt dieselben Sonden mit KORREKTER Rahmung.

e1 hat neue Records ohne Laengenpraefix mitten in die Strassenkette von
Sektion 16 geschoben und den Gruppenindex nicht nachgezogen (FINDINGS §6l).
f1 benutzt sec16.named()/insert(): vollstaendige Elemente
`u16 L | 80 11 | u16 L-1 | Record | 01`, eingefuegt an einer Elementgrenze,
alle spaeteren Gruppenoffsets nachgezogen. validate.py [12] prueft das.

  P0  @0x36ce94a  Testort -> Kontro5                          z1-z9  Karte geladen
  P1  @0x3392334  + Kelsitstraße, vor Nachbarorter Straße     z1-z9
  P2  @0x3392334  + Quadrat 252 m `QUADRAT`, 330 m westlich   z1-z9
  P3  @0x346c45e  Testorter Straße -> `OSTTEST Testorter` (gleich lang)
  P4  @0x346c45e  Ortsgammaer Straße -> Quadrat (laengenneutral)
  Campingwege: bewusst NICHT -- Block C bleibt strukturell unveraendert.
  Stuerzt f1 ab, liegt es am Westblock.
"""
import sys, lzma, struct, math, json, pickle
sys.path.insert(0, '.')
import sec16
from roadrec import parse_section
from roadwrite import to_units, densify, record, encode_deltas

SRC = '../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST = 'GermanyWest_Basic.f1.psf'
R, S = 6371000.0, 18.0

KONTR = 0x36ce94a                                   # West 280k, z1-z9
WEST,  OPFER_W, PARTNER_W = 0x3392334, 0x339593c, 0x33a5403
OST,   OPFER_O, PARTNER_O = 0x346c45e, 0x346ffe7, 0x346a990
IH_W, HI_W = 0x74b58,  0x3ab1e57
IH_OW, HI_OW = 0x74b7c, 0x3ab254d
IH_O, HI_O = 0x7550c,  0x3ab1e5d
IH_OO, HI_OO = 0x75524, 0x3ab1eb1
SEC_W, SEC_O = 7709, 11341

# geschlossenes Quadrat, 252 m Kante, 9 Deltabytes (Nord 7+7, Sued 7+4+3)
QUAD9 = bytes([0x07, 0x07, 0x70, 0x70, 0x09, 0x09, 0x90, 0xC0, 0xD0])
QUAD_MITTE = (50.1, 7.6)        # freies Feld westlich Testort (P2)
BX0, BX1, BY0, BY1 = 28, 101, 12, 82    # Platzrechteck Camping (P5)


def blk(d, P):
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw = dec.decompress(d[P:])
    return raw, len(d) - P - len(dec.unused_data)


def build(data, mf, nl):
    f = [{'id': lzma.FILTER_LZMA1, 'dict_size': len(data), 'lc': 3, 'lp': 0,
          'pb': 2, 'mode': lzma.MODE_NORMAL, 'mf': mf, 'nice_len': nl, 'depth': 0}]
    o = bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
    struct.pack_into('<I', o, 1, len(data))
    struct.pack_into('<Q', o, 5, len(data))
    chk = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert chk.decompress(bytes(o)) == data and not chk.unused_data
    return bytes(o)


MFS = [lzma.MF_BT2, lzma.MF_BT3, lzma.MF_BT4, lzma.MF_HC3, lzma.MF_HC4]


def sweep(data, ziel=None):
    best = (None, None, None)
    for mf in MFS:
        for nl in range(2, 274):
            try: o = build(data, mf, nl)
            except Exception: continue
            if ziel is not None and len(o) == ziel: return len(o), mf, nl
            if best[0] is None or len(o) < best[0]: best = (len(o), mf, nl)
    return best


d = open(SRC, 'rb').read(); N = len(d); out = bytearray(d)
ll = lambda X0, Y0, x, y: (math.degrees(2*math.atan(math.exp((Y0+y*S)/R)) - math.pi/2),
                           math.degrees((X0+x*S)/R))

# ============================ Westkachel: P1 + P2 ============================
raw, ext = blk(d, WEST)
X0, Y0, X1, Y1 = struct.unpack_from('<4i', raw, 0)
W, H = int((X1-X0)/S), int((Y1-Y0)/S)
recs = parse_section(raw, SEC_W, W, H)

osm = json.load(open('osm/osm_west.json'))['elements']
kel = [e for e in osm if e.get('tags', {}).get('name') == 'Kelsitstraße']
assert len(kel) == 1
rec_kel = record(densify([to_units(p['lat'], p['lon'], X0, Y0, S)
                          for p in kel[0]['geometry']]), 'Kelsitstraße')

qx, qy = to_units(*QUAD_MITTE, X0, Y0, S)
qx, qy = int(round(qx)), int(round(qy))
rec_qd = (bytes([1, len(QUAD9), 0]) + struct.pack('<HH', qx, qy) + QUAD9
          + b'\x00\x03' + b'QUADRAT' + b'\x00')
assert 0 <= qx <= qx+14 <= W and 0 <= qy <= qy+14 <= H, \
    f'Quadrat {qx}..{qx+14} / {qy}..{qy+14} sprengt die Kachel {W}x{H}'

c16, ent16, it16, _ = sec16.find(raw, SEC_W - 40)
tag = b'\x00\x03' + 'Nachbarorter Straße'.encode() + b'\x00'
pos = [q for q, L, t in it16 if raw.find(tag, q, q+L) >= 0]
assert len(pos) == 1; pos = pos[0]
grp = max((e for e in ent16 if c16 + e[4] <= pos), key=lambda e: e[4])
print(f"Einfuegen vor Nachbarorter-Element @{pos}, Gruppe {grp[1]:02x} {grp[2]:02x} {grp[3]:02x}")
pw = sec16.insert(raw, pos, sec16.named(rec_qd), SEC_W - 40)
pw = sec16.insert(pw, pos, sec16.named(rec_kel), SEC_W - 40)
assert not sec16.check(raw, pw, SEC_W - 40), sec16.check(raw, pw, SEC_W - 40)
print(f"P1 Kelsitstraße  {len(rec_kel):3d} B  {ll(X0,Y0,*struct.unpack_from('<HH',rec_kel,3))[0]:.5f} N")
print(f"P2 Quadrat      {len(rec_qd):3d} B  X={qx} Y={qy}  "
      f"{ll(X0,Y0,qx,qy)[0]:.5f} N / {ll(X0,Y0,qx,qy)[1]:.5f} E  "
      f"(Kante 252 m, Name QUADRAT)")
print(f"   Payload West {len(raw)} -> {len(pw)} ({len(pw)-len(raw):+d} B)")

Lw, mfw, nlw = sweep(pw); nbw = build(pw, mfw, nlw)
assert nbw[0] == d[WEST] == 93
_, opferlen_w = blk(d, OPFER_W)
assert ext < Lw <= ext + opferlen_w, f"passt nicht ins Opfer ({opferlen_w} B)"
out[WEST:WEST+Lw] = nbw
print(f"   Strom {ext} -> {Lw} ({Lw-ext:+d}), Opfer bietet {opferlen_w} B")

# ============================ Ostkachel: P3 + P4 + P5 ========================
rawo, exto = blk(d, OST)
OX0, OY0, OX1, OY1 = struct.unpack_from('<4i', rawo, 0)
OW, OH = int((OX1-OX0)/S), int((OY1-OY0)/S)
oreg = parse_section(rawo, SEC_O, OW, OH)
po = bytearray(rawo)

# P4 zuerst (laengenneutral, Offsets bleiben gueltig)
pf = [r for r in oreg if r['name'] == 'Ortsgammaer Straße']
assert len(pf) == 1 and pf[0]['flags'] == 0 and pf[0]['n'] == len(QUAD9), pf
o4 = pf[0]['offset'] + 7
po[o4:o4+len(QUAD9)] = QUAD9
print(f"P4 Ortsgammaer Straße @{pf[0]['offset']} -> Quadrat 252 m "
      f"({pf[0]['n']} Deltas, laengenneutral)")

# P3 Umbenennung, gleich lang -> Kette und Index bleiben unberuehrt
alt = 'Testorter Straße'.encode(); neu = b'OSTTEST Testorter'
assert len(neu) == len(alt) == 17
o3 = po.find(b'\x00\x03' + alt + b'\x00')
assert o3 > 0 and po.count(b'\x00\x03' + alt + b'\x00') == 1
po[o3+2:o3+2+len(alt)] = neu
po = bytes(po)
assert len(po) == len(rawo) and not sec16.check(rawo, po, SEC_O - 40)
print(f"P3 Testorter Straße -> OSTTEST Testorter @{o3} (laengenneutral)")
print(f"   Payload Ost {len(rawo)} -> {len(po)} (+0 B)")

Lo, mfo, nlo = sweep(po); nbo = build(po, mfo, nlo)
assert nbo[0] == d[OST] == 93
_, opferlen_o = blk(d, OPFER_O)
assert exto < Lo <= exto + opferlen_o, f"passt nicht ins Opfer ({opferlen_o} B)"
out[OST:OST+Lo] = nbo
print(f"   Strom {exto} -> {Lo} ({Lo-exto:+d}), Opfer bietet {opferlen_o} B")

# ============================ P0 Ladeanzeige =================================
kraw, kext = blk(d, KONTR)
kneu = kraw.replace(b'Testort', b'Kontro5')
assert len(kneu) == len(kraw) and kneu != kraw
kL, kmf, knl = sweep(kneu, ziel=kext)
assert kL == kext, f"Kontrollsonde trifft {kext} nicht ({kL})"
kb = build(kneu, kmf, knl)
assert kb[:13] == d[KONTR:KONTR+13]
out[KONTR:KONTR+kext] = kb
print(f"P0 @0x{KONTR:07x}: Testort -> Kontro5, Strom {kL} == Extent {kext}")

# ============================ Index ==========================================
for ZIEL, L, extv, IHz, HIz, OPF, PART, IHo, HIo in (
        (WEST, Lw, ext,  IH_W, HI_W, OPFER_W, PARTNER_W, IH_OW, HI_OW),
        (OST,  Lo, exto, IH_O, HI_O, OPFER_O, PARTNER_O, IH_OO, HI_OO)):
    _, plen = blk(d, PART)
    _, olen = blk(d, OPF)
    assert struct.unpack_from('<IH', d, IHz) == (ZIEL, extv)
    assert struct.unpack_from('<HI', d, HIz) == (extv, ZIEL)
    struct.pack_into('<H', out, IHz+4, L); struct.pack_into('<H', out, HIz, L)
    assert struct.unpack_from('<IH', d, IHo) == (OPF, olen)
    assert struct.unpack_from('<HI', d, HIo) == (olen, OPF)
    struct.pack_into('<IH', out, IHo, PART, plen)
    struct.pack_into('<HI', out, HIo, plen, PART)
    print(f"Index @0x{ZIEL:07x}: {extv} -> {L}; Opfer @0x{OPF:07x} -> @0x{PART:07x}")

assert len(out) == N
open(DST, 'wb').write(bytes(out))
json.dump({'grow': {hex(WEST): Lw, hex(OST): Lo},
           'sacrificed': [hex(OPFER_W), hex(OPFER_O)],
           'note': 'f1 -- korrekte Rahmung: Kontro5, Kelsitstr., QUADRAT (West, Index nachgezogen), '
                   'OSTTEST Testorter + Ostquadrat (laengenneutral), keine Campingwege'},
          open(DST.replace('.psf', '.plan.json'), 'w'), indent=1)

# ============================ Verifikation ===================================
print("\n--- Verifikation ---")
o = bytes(out); assert len(o) == N
r2, _ = blk(o, WEST)
w2 = parse_section(r2, SEC_W, W, H)
print(f"West: Kelsitstraße {sum(1 for r in w2 if r['name']=='Kelsitstraße')}x, "
      f"QUADRAT {sum(1 for r in w2 if r['name']=='QUADRAT')}x, "
      f"Records {len(recs)} -> {len(w2)}")
assert not any(not r['name'] for r in w2)
o2, _ = blk(o, OST)
e2 = parse_section(o2, SEC_O, OW, OH)
ost = [r for r in e2 if r['name'] == 'OSTTEST Testorter']
pf2 = [r for r in e2 if r['name'] == 'Ortsgammaer Straße']
print(f"Ost:  OSTTEST Testorter {len(ost)}x, Ortsgammaer Deltas "
      f"{o2[pf2[0]['offset']+7:pf2[0]['offset']+7+9].hex(' ')}")
xs = [p[0] for p in pf2[0]['points']]; ys = [p[1] for p in pf2[0]['points']]
print(f"      Quadrat geschlossen: {pf2[0]['points'][0]==pf2[0]['points'][-1]}, "
      f"X {min(xs)}..{max(xs)}  Y {min(ys)}..{max(ys)}")
assert len(ost) == 1
k2, _ = blk(o, KONTR)
print(f"P0:   Kontro5 {k2.count(b'Kontro5')}x, Testort {k2.count(b'Testort')}x")
ok = bad = 0
for P, c, s in pickle.load(open('gw_anchors.pkl', 'rb')):
    if P in (OPFER_W, OPFER_O): continue
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64], max_length=32); ok += 1
    except Exception: bad += 1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke ausser den zwei Opfern: {ok} dekodieren, {bad} fehlerhaft")
print(f"\ngeschrieben: {DST}")
