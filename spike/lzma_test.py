#!/usr/bin/env python3
"""WEGWERF: Hypothese - Bloecke sind LZMA-alone Streams (Header inklusive)."""
import sys, struct, lzma

def u32(b,o): return struct.unpack_from('<I',b,o)[0]

path=sys.argv[1]
d=open(path,'rb').read(); n=len(d)
recs=[]; o=0x102
while o+12<=n:
    off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
    if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
    recs.append((off,ln,tid)); o+=20

print(f"### {path}   {len(recs)} Bloecke\n")
ok=0; fail=0; total_out=0
first=None
for i,(off,ln,tid) in enumerate(recs):
    blk=d[off:off+ln]
    want=struct.unpack_from('<Q',blk,5)[0]
    try:
        dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        out=dec.decompress(blk)
        if len(out)==want:
            ok+=1; total_out+=len(out)
            if first is None: first=(i,tid,out)
        else:
            fail+=1
            if fail<=3: print(f"  Block {i}: {len(out)} B, erwartet {want}")
    except Exception as e:
        fail+=1
        if fail<=3: print(f"  Block {i}: FEHLER {type(e).__name__}: {e}")

print(f"ERFOLG: {ok}/{len(recs)} Bloecke dekomprimiert, "
      f"Ausgabelaenge == angekuendigte Groesse")
print(f"FEHLER: {fail}")
print(f"Entpackt gesamt: {total_out} Bytes aus {n} Bytes Datei "
      f"(Faktor {total_out/n:.2f})\n")

if first:
    i,tid,out=first
    print(f"=== Block {i} (tileId 0x{tid:08x}), {len(out)} Bytes entpackt ===")
    for r in range(0, min(len(out), 320), 16):
        row=out[r:r+16]
        print(f"  {r:04x}  {row.hex(' ')}  "
              f"{''.join(chr(c) if 32<=c<127 else '.' for c in row)}")
    import collections, math
    c=collections.Counter(out); m=len(out)
    ent=-sum((v/m)*math.log2(v/m) for v in c.values())
    print(f"\n  Entropie der entpackten Daten: {ent:.3f} Bit/Byte")
    print(f"  Nullbytes: {c[0]*100/m:.2f} %")
    s=[x for x in out.split(b'\x00') if len(x)>=4 and all(32<=y<127 for y in x)]
    print(f"  ASCII-Fragmente (>=4): {s[:10]}")
