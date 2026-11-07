#!/usr/bin/env python3
"""WEGWERF-Analyse: Entropie-Profil + Codec-Fingerprints fuer .psf-Container."""
import sys, math, collections, zlib, lzma, bz2

def entropy(b):
    if not b: return 0.0
    c = collections.Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def main(path):
    data = open(path,'rb').read()
    n = len(data)
    print(f"### {path}\nsize={n} ({n/1024:.1f} KB)\n")

    # --- 1. Grob-Profil: Entropie pro 4KB
    BS = 4096
    blocks = [(off, entropy(data[off:off+BS])) for off in range(0, n, BS)]
    ents = [e for _, e in blocks]
    print(f"Gesamt-Entropie: {entropy(data):.4f} Bit/Byte")
    print(f"4KB-Bloecke: {len(blocks)}  min={min(ents):.3f} max={max(ents):.3f} "
          f"mean={sum(ents)/len(ents):.3f}")
    lo = [(o,e) for o,e in blocks if e < 7.5]
    print(f"Bloecke mit Entropie < 7.5: {len(lo)} von {len(blocks)}")
    for o,e in lo[:20]:
        print(f"   0x{o:08x}  {e:.3f}")
    print()

    # --- 2. Fein-Profil am Dateianfang: wo kippt es ins Rauschen?
    print("Fein-Profil (256-Byte-Fenster, erste 8 KB):")
    for off in range(0, min(n, 8192), 256):
        e = entropy(data[off:off+256])
        bar = '#' * int(e*6)
        print(f"  0x{off:05x} {e:5.3f} {bar}")
    print()

    # --- 3. Byte-Histogramm: Auffaelligkeiten
    hist = collections.Counter(data)
    print("Top-10 Bytes:", [(f"0x{b:02x}", f"{c*100/n:.2f}%") for b,c in hist.most_common(10)])
    print(f"Verschiedene Bytewerte: {len(hist)}/256")
    print(f"Nullbytes: {hist[0]*100/n:.2f}%")
    print()

    # --- 4. Magic-Byte-Suche
    magics = {
        b'\x1f\x8b': 'gzip', b'\x78\x01': 'zlib(no/low)', b'\x78\x9c': 'zlib(default)',
        b'\x78\xda': 'zlib(best)', b'\x78\x5e': 'zlib(fast)', b'BZh': 'bzip2',
        b'\xfd7zXZ': 'xz', b']\x00\x00': 'lzma-alone', b'\x04"M\x18': 'lz4',
        b'SQLite format 3': 'sqlite', b'NDS': 'NDS-ascii', b'PK\x03\x04': 'zip',
        b'\x89PNG': 'png', b'\xaf\xbe': 'cff-container',
    }
    print("Magic-Treffer:")
    found_any = False
    for m, name in magics.items():
        hits = []
        start = 0
        while True:
            i = data.find(m, start)
            if i < 0 or len(hits) >= 6: break
            hits.append(i); start = i+1
        if hits:
            found_any = True
            print(f"  {name:16s} {len(hits)}+ Treffer, erste: {[hex(h) for h in hits]}")
    if not found_any: print("  keine")
    print()

    # --- 5. Dekompressions-Versuche an plausiblen Offsets
    print("Codec-Versuche:")
    offsets = [0, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000]
    offsets += [o for o,_ in blocks[:4]]
    tried = set()
    for off in sorted(set(offsets)):
        if off >= n or off in tried: continue
        tried.add(off)
        chunk = data[off:off+65536]
        for name, fn in [
            ('zlib',        lambda c: zlib.decompress(c)),
            ('raw-deflate', lambda c: zlib.decompressobj(-15).decompress(c)),
            ('gzip',        lambda c: zlib.decompressobj(31).decompress(c)),
            ('lzma',        lambda c: lzma.decompress(c)),
            ('lzma-raw',    lambda c: lzma.LZMADecompressor(lzma.FORMAT_ALONE).decompress(c)),
            ('bz2',         lambda c: bz2.decompress(c)),
        ]:
            try:
                out = fn(chunk)
                if out and len(out) > 64:
                    print(f"  TREFFER off=0x{off:x} {name}: {len(out)} Bytes -> {out[:48]!r}")
            except Exception:
                pass
    print("  (keine Ausgabe = kein Standard-Codec greift an diesen Offsets)")

if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p); print("\n" + "="*70 + "\n")
