#!/usr/bin/env python3
"""WEGWERF: LZMA-Bloecke ohne Indexkenntnis finden, daraus Indexlayout ableiten."""
import sys, struct, lzma

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

def scan_blocks(d, limit=None):
    """Kandidaten: 0x5D + u32 dict + u64 size, dict==size, LZMA dekomprimierbar."""
    n=len(d) if limit is None else min(len(d), limit)
    out=[]; p=0
    while True:
        p=d.find(b'\x5d', p)
        if p<0 or p>=n: break
        if p+13<=len(d):
            dic=u32(d,p+1); siz=u64(d,p+5)
            if dic==siz and 0<siz<=16_000_000:
                try:
                    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                    res=dec.decompress(d[p:p+min(len(d)-p, siz*4+4096)])
                    if len(res)>=siz:
                        out.append((p,siz))
                        p += 13
                        continue
                except Exception: pass
        p+=1
    return out

def derive_index(d, offsets):
    """Suche im Header eine Tabelle, die diese Offsets als uint32 LE enthaelt."""
    hits={}
    for target in offsets[:40]:
        pat=struct.pack('<I', target)
        s=0
        while True:
            i=d.find(pat, s)
            if i<0 or i>0x4000: break
            hits.setdefault(target, []).append(i); s=i+1
    # Stride bestimmen: Differenz der Tabellenpositionen aufeinanderfolgender Offsets
    seq=[]
    for t in offsets[:40]:
        if t in hits: seq.append((t, hits[t]))
    if len(seq)<3: return None
    # nimm fuer jeden Offset die Position, die ein konsistentes Raster ergibt
    import collections
    cand=collections.Counter()
    for i in range(len(seq)-1):
        for a in seq[i][1]:
            for b in seq[i+1][1]:
                if 0 < b-a <= 64: cand[b-a]+=1
    if not cand: return None
    stride=cand.most_common(1)[0][0]
    base=min(min(p) for _,p in seq)
    return base, stride

for path in sys.argv[1:]:
    d=open(path,'rb').read()
    name=path.split('/')[-1]
    LIM = 4_000_000
    blocks=scan_blocks(d, LIM)
    tot=sum(s for _,s in blocks)
    print(f"### {name}  size={len(d)} (gescannt: {min(len(d),LIM)})")
    print(f"    LZMA-Bloecke gefunden: {len(blocks)}, entpackt {tot} B")
    if blocks:
        print(f"    erste Offsets: {[hex(o) for o,_ in blocks[:6]]}")
        print(f"    Groessen: {[s for _,s in blocks[:6]]}")
        di=derive_index(d, [o for o,_ in blocks])
        if di:
            base,stride=di
            print(f"    -> Indextabelle: base~0x{base:x}, stride={stride}")
            print(f"       Rohbytes @0x{base-8:x}: {d[base-8:base+3*stride].hex(' ')}")
        else:
            print(f"    -> Indextabelle nicht ableitbar (Offsets stehen nicht als uint32 im Header)")
        # Inhalt des ersten grossen Blocks
        big=max(blocks, key=lambda x:x[1])
        dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        out=dec.decompress(d[big[0]:])[:big[1]]
        print(f"    groesster Block @0x{big[0]:x}: {big[1]} B entpackt")
        print(f"       {out[:64].hex(' ')}")
        txt=''.join(chr(c) if 32<=c<127 else '.' for c in out[:96])
        print(f"       {txt}")
        # ASCII-Suche
        import re
        strs=re.findall(rb'[\x20-\x7e]{6,}', out)
        if strs: print(f"       ASCII: {[s.decode() for s in strs[:8]]}")
    print()
