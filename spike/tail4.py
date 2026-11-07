#!/usr/bin/env python3
"""Warum kein TESTORT? Praefixe und Blockgrenzen pruefen."""
import struct, lzma, pickle, collections
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read(); FIRST=54408; tail=anc[FIRST:]
raw=[]
for p,c,s in tail:
    try: raw.append(lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+c+64])[:s])
    except Exception: raw.append(b'')
OK=set(range(0x20,0x7f))|{0xdf,0xc4,0xd6,0xdc}
def chain(b,o,n=40):
    out=bytearray()
    while o+3<=len(b) and len(out)<n and b[o] in OK:
        out.append(b[o]); o+=3
    return bytes(out)
def search(nd, atstart=False):
    r=[]
    for i,b in enumerate(raw):
        rng=[0] if atstart else range(max(0,len(b)-2))
        for o in rng:
            c=chain(b,o,len(nd)+14)
            if c.startswith(nd): r.append((FIRST+i,o,chain(b,o,26)))
    return r
for nd in (b'TESTORT',b'HAUSB',b'HAUS',b'AUSBAY',b'USBAY',b'SBAY',b'BAY',
           b'KOBLENZ',b'BOPPARD',b'NACHBARSTADT',b'LIMBURG'):
    h=search(nd)
    ex=[x[2] for x in h[:2]]
    print(f"  {nd.decode():14s} {len(h):5d}  {ex}")
print("\nKetten, die am Blockanfang beginnen (Offset 0), Beispiele:")
c0=collections.Counter()
for i,b in enumerate(raw):
    c=chain(b,0,26)
    if len(c)>=4: c0[c[:20]]+=1
for k,v in list(c0.most_common(6)): print(f"   {v:5d}x {k!r}")
