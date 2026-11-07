#!/usr/bin/env python3
"""Straßenrecords SCHREIBEN — Umkehrung von roadrec.py (§6j).

    01 <n> 00 │ u16 X │ u16 Y │ n Deltabytes │ 00 03 │ Name (UTF-8) │ 00

Je Stuetzpunkt ein Byte: hohes Nibbel dy, niedriges dx, 4-bit Zweierkomplement.
Schrittgrenze ist damit ±7 Einheiten; bei 18 m Quantum sind das ±126 m. Laengere
Segmente muessen verdichtet werden, das macht `densify()`.

0x00 als Deltabyte beendet die Geometrie -- ein Schritt (0,0) ist also verboten
und wird beim Kodieren uebersprungen.

Selbsttest: `python3 roadwrite.py` liest alle f=0x00-Records und kodiert ihre
Geometrie zurueck; die Bytes muessen identisch sein.
"""
import struct, math
R = 6371000.0

def to_units(lat, lon, X0, Y0, s):
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi/4 + math.radians(lat)/2))
    return (x - X0)/s, (y - Y0)/s

def densify(pts, maxstep=7):
    """Stuetzpunkte so einfuegen, dass kein Schritt |dx| oder |dy| > maxstep hat."""
    out = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        k = max(1, int(math.ceil(max(abs(bx-ax), abs(by-ay)) / maxstep)))
        for t in range(1, k+1):
            out.append((ax + (bx-ax)*t/k, ay + (by-ay)*t/k))
    return out

def encode_deltas(pts):
    """Gerundete Gitterpunkte -> Deltabytes. Nullschritte entfallen."""
    q = [(int(round(a)), int(round(b))) for a, b in pts]
    out = bytearray(); cur = q[0]
    for p in q[1:]:
        dx, dy = p[0]-cur[0], p[1]-cur[1]
        if dx == 0 and dy == 0: continue          # 0x00 waere Terminator
        if not (-8 <= dx <= 7 and -8 <= dy <= 7):
            raise ValueError(f"Schritt {dx},{dy} sprengt 4 Bit -- erst densify()")
        out.append(((dy & 15) << 4) | (dx & 15))
        cur = p
    return bytes(out), q[0]

def record(pts, name, flags=0):
    """Vollstaendiger Record aus Gitterpunkten."""
    deltas, (x, y) = encode_deltas(pts)
    nm = name.encode('utf-8')
    return (bytes([1, len(deltas), flags]) + struct.pack('<HH', x, y)
            + deltas + b'\x00\x03' + nm + b'\x00')

if __name__ == '__main__':
    import lzma, sys
    sys.path.insert(0, '.')
    from roadrec import parse_section
    d = open('../sdsrc/NO NAME/markets/eu/map/'
             'MapRegions/GermanyWest_Basic.psf', 'rb').read()
    total = same = 0
    for lab, P, S, start in (('B  West L11', 0x3392334, 18.0, 7709),
                             ('C  Ost  L11', 0x346c45e, 18.0, 11341),
                             ('L10 Strassen', 0x2f4009f, 38.0, 20)):
        raw = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[P:])
        X0, Y0, X1, Y1 = struct.unpack_from('<4i', raw, 0)
        W, H = int((X1-X0)/S), int((Y1-Y0)/S)
        ok = bad = 0
        for r in parse_section(raw, start, W, H):
            if r['flags'] != 0: continue
            orig = raw[r['offset']: r['offset']+7+r['n']+2+len(r['name'].encode())+1]
            built = record(r['points'], r['name'], r['flags'])
            total += 1
            if built == orig: ok += 1; same += 1
            else:
                bad += 1
                if bad <= 2:
                    print(f"   ABWEICHUNG @{r['offset']} {r['name']}")
                    print(f"      orig  {orig.hex(' ')}")
                    print(f"      neu   {built.hex(' ')}")
        print(f"{lab}: {ok} von {ok+bad} Records byteidentisch rekonstruiert")
    print(f"\nGesamt {same}/{total} — {'BESTANDEN' if same==total else 'FEHLER'}")
