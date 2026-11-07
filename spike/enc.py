#!/usr/bin/env python3
import sys, struct, lzma, re
d=open(sys.argv[1],'rb').read(); out=[]; p=0
while True:
    p=d.find(b'\x5d',p)
    if p<0: break
    if p+13<=len(d):
        dic=struct.unpack_from('<I',d,p+1)[0]; siz=struct.unpack_from('<Q',d,p+5)[0]
        if dic==siz and 0<siz<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+min(len(d)-p,siz*4+4096)])
                if len(r)>=siz: out.append(r[:siz]); p+=13; continue
            except Exception: pass
    p+=1
big=b'\x00'.join(out)
# Strings mit Nicht-ASCII: als UTF-8 vs Latin-1 vergleichen
pat=re.compile(rb'(?:Triq|Vjal|Sqaq)[ \-][\x20-\xff]{2,50}')
n_utf=n_lat=0; samples=[]
for m in pat.finditer(big):
    s=m.group().split(b'\x00')[0]
    if all(c<0x80 for c in s): continue
    try:
        u=s.decode('utf-8'); n_utf+=1
        if len(samples)<10: samples.append(('UTF-8', u))
    except UnicodeDecodeError:
        n_lat+=1
        if len(samples)<10: samples.append(('latin-1', s.decode('latin-1')))
print(f"Strings mit Nicht-ASCII-Bytes: als UTF-8 dekodierbar {n_utf}, nicht dekodierbar {n_lat}")
for e,s in samples: print(f"   [{e}] {s}")
