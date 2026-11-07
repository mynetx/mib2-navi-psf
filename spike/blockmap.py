#!/usr/bin/env python3
"""Vollvermessung aller Bloecke: echte komprimierte Laenge (der Anker-Abstand
luegt, siehe FINDINGS 6e), Typbyte @+20, 5. Kopffeld, BBox.
Ergebnis -> gw_blockmap.pkl
"""
import struct, lzma, pickle, collections
SRC = '../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d = open(SRC, 'rb').read()
anc = pickle.load(open('gw_anchors.pkl', 'rb'))
offs = [p for p, c, s in anc]
rows = []
bad = 0
for i, (P, gapc, s) in enumerate(anc):
    nxt = offs[i+1] if i+1 < len(offs) else len(d)
    try:
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        raw = dec.decompress(d[P:nxt+64])
        comp = (nxt+64 if nxt+64 <= len(d) else len(d)) - P - len(dec.unused_data)
    except Exception:
        bad += 1; continue
    typ = raw[20] if len(raw) > 20 else -1
    bb = struct.unpack_from('<4i', raw, 0) if len(raw) >= 20 else None
    fifth = struct.unpack_from('<i', raw, 16)[0] if len(raw) >= 20 else None
    rows.append((P, comp, nxt - P, len(raw), typ, fifth, bb))
pickle.dump(rows, open('gw_blockmap.pkl', 'wb'))
print(f"{len(rows)} Bloecke vermessen, {bad} nicht dekodierbar")

slack = [(P, gap - comp, comp, gap) for P, comp, gap, pl, t, f, bb in rows if gap - comp > 0]
tot = sum(s for _, s, _, _ in slack)
print(f"\nBloecke mit gap > echter Laenge: {len(slack)}, Summe {tot} B ({tot/1024/1024:.2f} MiB)")
h = collections.Counter()
for _, s, _, _ in slack:
    h['14' if s == 14 else ('<100' if s < 100 else ('<1k' if s < 1000 else ('<10k' if s < 10000 else '>=10k')))] += 1
print("  Verteilung:", dict(h))
print("  groesste Lueckenregionen:")
for P, s, comp, gap in sorted(slack, key=lambda x: -x[1])[:10]:
    print(f"    @0x{P:07x} Strom {comp:6d}, Abstand {gap:6d} -> {s:6d} B unklassifiziert")

t = collections.Counter(r[4] for r in rows)
print(f"\nTypbyte @+20: {dict(t)}")
