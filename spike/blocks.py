#!/usr/bin/env python3
"""WEGWERF: Bloecke ueber den Index auslesen, Blockheader parsen, Duplikate zaehlen."""
import sys, struct, collections, zlib, lzma, bz2, hashlib

def u32(b,o): return struct.unpack_from('<I',b,o)[0]

path=sys.argv[1]
d=open(path,'rb').read(); n=len(d)
START, STRIDE = 0x102, 20
recs=[]; o=START
while o+12<=n:
    off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
    if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
    recs.append((off,ln,tid)); o+=STRIDE
print(f"### {path}  size={n}  Bloecke={len(recs)}\n")

# Duplikate: wie viele Bloecke sind byte-identisch?
h=collections.Counter(hashlib.sha1(d[off:off+ln]).digest() for off,ln,_ in recs)
print(f"Verschiedene Blockinhalte: {len(h)} von {len(recs)}")
print(f"Haeufigster Blockinhalt kommt {h.most_common(1)[0][1]}x vor")
print(f"  => {len(recs)-len(h)} Bloecke sind Duplikate "
      f"(Malta ist eine Insel: leere Seekacheln)\n")

print(f"{'#':>4} {'offset':>9} {'idxLen':>7} {'tileId':>10} {'tag':>4} "
      f"{'lenA':>7} {'lenB':>7} {'f3':>5}  ratio  ersteDatenbytes")
seen=set()
shown=0
for i,(off,ln,tid) in enumerate(recs):
    blk=d[off:off+ln]
    tag=blk[0]; a=u32(blk,1); b=u32(blk,5); f3=u32(blk,9)
    key=hashlib.sha1(blk).digest()
    dup = '(dup)' if key in seen else ''
    seen.add(key)
    if dup and shown>12: continue
    if shown>24: break
    shown+=1
    print(f"{i:4d} 0x{off:07x} {ln:7d} 0x{tid:08x} 0x{tag:02x} "
          f"{a:7d} {b:7d} {f3:5d} {ln/max(1,a):6.3f}  {blk[13:33].hex(' ')} {dup}")

print("\n=== Konsistenzpruefung Blockheader ===")
tags=collections.Counter(d[off] for off,ln,_ in recs)
print(f"Tag-Byte-Verteilung: {dict(tags)}")
eq=sum(1 for off,ln,_ in recs if ln>=13 and u32(d,off+1)==u32(d,off+5))
print(f"lenA == lenB: {eq}/{len(recs)}")
z=sum(1 for off,ln,_ in recs if ln>=13 and u32(d,off+9)==0)
print(f"Feld3 == 0:   {z}/{len(recs)}")
ratios=[ln/u32(d,off+1) for off,ln,_ in recs if ln>=13 and u32(d,off+1)>0]
print(f"idxLen/lenA: min={min(ratios):.3f} max={max(ratios):.3f} "
      f"mean={sum(ratios)/len(ratios):.3f}")
# Ist lenA == ln-13?
m=sum(1 for off,ln,_ in recs if ln>=13 and u32(d,off+1)==ln-13)
print(f"lenA == idxLen-13: {m}/{len(recs)}")
m2=sum(1 for off,ln,_ in recs if ln>=13 and u32(d,off+1)==ln)
print(f"lenA == idxLen:    {m2}/{len(recs)}")

print("\n=== Codec-Versuche auf Blockdaten (ab +13) ===")
for i,(off,ln,tid) in enumerate(recs[:40]):
    payload=d[off+13:off+ln]
    for name,fn in [('zlib',zlib.decompress),
                    ('raw-deflate',lambda c: zlib.decompressobj(-15).decompress(c)),
                    ('lzma',lzma.decompress),
                    ('bz2',bz2.decompress)]:
        try:
            out=fn(payload)
            if out and len(out)>32:
                print(f"  TREFFER Block {i} {name}: {len(out)} B -> {out[:40].hex(' ')}")
        except Exception: pass
print("  (leer = kein Standard-Codec)")
