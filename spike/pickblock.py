#!/usr/bin/env python3
"""Bloecke mit 'Testort' finden, NUL-terminierte UTF-8-Strings auflisten."""
import struct, lzma, pickle
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

path='GermanyWest_Basic.psf'
d=open(path,'rb').read(); n=len(d)
found=[]; p=0
while True:
    p=d.find(b'\x5d',p)
    if p<0: break
    if p+13<=n:
        dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
        if dic==siz and 0<siz<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                    d[p:p+min(n-p,siz*4+4096)])
                if len(r)>=siz:
                    b=r[:siz]
                    if b'Testort' in b: found.append((p,siz,b))
                    p+=13; continue
            except Exception: pass
    p+=1
print(f"{len(found)} Bloecke mit 'Testort'\n")

def strings(b, minlen=5):
    out=[]
    for part in b.split(b'\x00'):
        if len(part)<minlen: continue
        try: t=part.decode('utf-8')
        except UnicodeDecodeError: continue
        if all(32<=ord(c)<127 or ord(c)>160 for c in t): out.append((part,t))
    return out

for off,siz,b in found:
    ss=strings(b)
    uniq=sorted({t for _,t in ss})
    print(f"@0x{off:x}  entpackt {siz} B, {len(ss)} Strings ({len(uniq)} eindeutig)")
    # Kandidaten: enthalten Testort oder sind Strassennamen
    cand=[t for t in uniq if 'Testort' in t or 'weg' in t.lower()
          or 'stra' in t.lower() or 'gasse' in t.lower()]
    for t in cand[:14]: print(f"     {t!r}")
    print()
pickle.dump(found, open('../spike/testort_blocks.pkl','wb'))
print("gecacht: testort_blocks.pkl")
