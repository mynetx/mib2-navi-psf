#!/usr/bin/env python3
"""WEGWERF: Gezielte Verifikation - echte Strassennamen im entpackten Basic-Layer."""
import sys, struct, lzma, re, collections

def decompress_all(path, limit=None):
    d=open(path,'rb').read(); n=len(d) if limit is None else min(len(d),limit)
    out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0 or p>=n: break
        if p+13<=len(d):
            dic=struct.unpack_from('<I',d,p+1)[0]; siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(len(d)-p,siz*4+4096)])
                    if len(r)>=siz:
                        out.append(r[:siz]); p+=13; continue
                except Exception: pass
        p+=1
    return out

path=sys.argv[1]; needles=sys.argv[2:]
blobs=decompress_all(path)
big=b'\x00'.join(blobs)
print(f"### {path.split('/')[-1]}: {len(blobs)} Bloecke, {len(big)} B entpackt\n")
for needle in needles:
    nb=needle.encode()
    pat=re.compile(re.escape(nb)+rb'[ \-][A-Za-z\xc0-\xff\'\-\. ]{2,50}')
    hits=[m.group() for m in pat.finditer(big)]
    uniq=sorted({h.strip().decode('latin-1') for h in hits})
    print(f"'{needle}': {len(hits)} Vorkommen, {len(uniq)} verschiedene Namen")
    for s in uniq[:25]: print(f"    {s}")
    if len(uniq)>25: print(f"    ... und {len(uniq)-25} weitere")
    print()
