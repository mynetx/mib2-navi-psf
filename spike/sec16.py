"""Sektion 16 (Straßen) als Kette längenpräfixierter Elemente -- FINDINGS §6l.

    [n] n x (Klasse, Flags, x, 00, u16 Offset)     Gruppenindex, Offsets ab [n]
    Kette:  u16 L | Rumpf (L-2 B)                  L zählt das Längenfeld mit
    benannt (80 11):  80 11 | u16 L-1 | 01 n f X Y Δ.. | {<Typ> 03 Text 00} | k
                      Typ 00 = Name, 03 = Nummer; k = 1..4, Einzelname immer 01

Die Offsets im Gruppenindex zeigen auf Elementanfänge (B 18/18, C 14/14).
Wer mitten in die Kette einfügt, muss jeden späteren Offset nachziehen --
`z3`, `d1` und `e1` haben das nicht getan, `e1` hat das Gerät abstürzen lassen.
"""
import struct


def chain(raw, q, end=None):
    end = len(raw) if end is None else end
    items = []
    while q + 4 <= end:
        L = struct.unpack_from('<H', raw, q)[0]
        if L < 4 or q + L > end:
            break
        items.append((q, L, raw[q+2:q+4]))
        q += L
    return items, q


def find(raw, sec=0):
    """-> (c, [(pos_eintrag, klasse, flags, x, offset)], items, kettenende) oder None.
    Genommen wird der Index, dessen Offsets alle auf Elementanfänge treffen und
    dessen Kette am längsten ist."""
    best = None
    for c in range(sec, len(raw) - 8):
        n = raw[c]
        if not 1 <= n <= 80 or c + 1 + 6*n + 4 > len(raw):
            continue
        if struct.unpack_from('<H', raw, c+5)[0] != 1 + 6*n or raw[c+4] != 0:
            continue
        ent = [(c+1+6*j, raw[c+1+6*j], raw[c+2+6*j], raw[c+3+6*j],
                struct.unpack_from('<H', raw, c+5+6*j)[0]) for j in range(n)]
        if any(raw[e[0]+3] != 0 for e in ent):
            continue
        items, e = chain(raw, c + 1 + 6*n)
        st = {q for q, _, _ in items}
        if all(c + o in st for *_, o in ent):
            if best is None or len(items) > len(best[2]):
                best = (c, ent, items, e)
    return best


def named(rec, trailer=1):
    """Recordbytes `01 n f X Y Δ.. 00 03 Name 00` -> vollständiges Element."""
    L = 2 + 2 + 2 + len(rec) + 1
    return struct.pack('<H', L) + b'\x80\x11' + struct.pack('<H', L-1) + rec + bytes([trailer])


def insert(raw, pos, elem, sec=0):
    """Element `elem` bei `pos` (muss ein Elementanfang sein) einfügen und alle
    Gruppenoffsets HINTER pos nachziehen. Ein Offset == pos bleibt stehen: das
    neue Element gehört dann zur Gruppe, die dort beginnt."""
    c, ent, items, e = find(raw, sec)
    assert pos in {q for q, _, _ in items} or pos == e, f'{pos} ist kein Elementanfang'
    out = bytearray(raw[:pos] + elem + raw[pos:])
    for p, _, _, _, o in ent:
        if c + o > pos:
            struct.pack_into('<H', out, p+4, o + len(elem))
    return bytes(out)


def replace(raw, pos, elem, sec=0):
    """Element bei `pos` durch `elem` ersetzen (andere Länge erlaubt)."""
    c, ent, items, e = find(raw, sec)
    L = dict((q, l) for q, l, _ in items)[pos]
    d = len(elem) - L
    out = bytearray(raw[:pos] + elem + raw[pos+L:])
    for p, _, _, _, o in ent:
        if c + o > pos:
            struct.pack_into('<H', out, p+4, o + d)
    return bytes(out)


def check(orig, new, sec=0):
    """Fehlerliste für einen geänderten Block gegen sein Original."""
    a = find(orig, sec)
    if a is None:
        return []                       # Block ohne Straßenkette
    b = find(new, sec)
    if b is None:
        return ['Straßenindex/Kette nicht mehr auffindbar']
    err = []
    ca, enta, ia, ea = a
    cb, entb, ib, eb = b
    if ca != cb or len(enta) != len(entb):
        err.append(f'Gruppenindex verschoben/verändert ({ca}/{len(enta)} -> {cb}/{len(entb)})')
    if [e[1:4] for e in enta] != [e[1:4] for e in entb]:
        err.append('Klassen/Flags im Gruppenindex verändert')
    if len(orig) - ea != len(new) - eb:
        err.append(f'Kette endet nicht vor dem Rest (Rest {len(orig)-ea} -> {len(new)-eb} B, '
                   f'{len(ib)-len(ia):+d} Elemente)')
    for q, L, t in ib:
        if t == b'\x80\x11':
            if struct.unpack_from('<H', new, q+4)[0] != L-1:
                err.append(f'@{q}: 80 11 mit Innenlänge != L-1')
            r = q + 6
            if new[r] == 1 and new[r+2] == 0:
                # nach den Deltas: Namenseinträge <Typ> 03 Text 00, zuletzt 01
                # Schlussbyte 1..4, Semantik offen (Einzelname immer 01, Ortsteil als 2. Name auch 01)
                i, ok, k = r + 7 + new[r+1], True, 0
                while i < q + L - 1:
                    t = new.find(b'\x00', i + 2)
                    if new[i+1] != 3 or t < 0 or t >= q + L - 1:
                        ok = False; break
                    k += new[i] == 0
                    i = t + 1
                if not ok or i != q + L - 1 or not 1 <= new[q+L-1] <= 4:
                    err.append(f'@{q}: benannter f=0-Record passt nicht in sein Element')
    return err
