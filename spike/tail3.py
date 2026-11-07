#!/usr/bin/env python3
"""Endabschnitt = Namens-Trie? Zeichenkette aus dem <char><u16>-Muster ziehen
und nach den Zielorten suchen."""
import struct, lzma, pickle, re, collections
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read()
FIRST=54408
tail=anc[FIRST:]
print(f"{len(tail)} Bloecke entpacken ...")
raw=[]
for p,c,s in tail:
    try:
        raw.append(lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                   .decompress(d[p:p+c+64])[:s])
    except Exception:
        raw.append(b'')
tot=sum(len(x) for x in raw)
print(f"{tot/1e6:.1f} MB entpackt")

# Kette: an jeder Position 3-Byte-Schritt <char><u16> -> Zeichen sammeln
def chain(b, start, maxlen=64):
    out=bytearray(); o=start
    while o+3<=len(b) and len(out)<maxlen:
        ch=b[o]
        if not (0x20<=ch<0x7f or ch in (0xdf,0xc4,0xd6,0xdc,0xe4,0xf6,0xfc)): break
        out.append(ch); o+=3
    return bytes(out)

hits=collections.Counter(); found=[]
NEEDLE=[b'TESTORT',b'ORTBETA',b'NIEDERORTBETA',b'OBERORTBETA',b'STRASSE',b'WEG']
for i,b in enumerate(raw):
    if len(b)<9: continue
    for o in range(0, len(b)-9):
        c=chain(b,o,20)
        if len(c)>=5:
            for nd in NEEDLE:
                if c.startswith(nd):
                    hits[nd]+=1
                    if len(found)<12 and nd in (b'TESTORT',b'ORTBETA'):
                        found.append((FIRST+i,o,chain(b,o,40)))
print("Treffer als Zeichenkette im 3-Byte-Raster:")
for k in NEEDLE: print(f"   {k.decode():15s} {hits[k]}")
print("\nBeispiele:")
for i,o,c in found[:12]:
    print(f"   Block #{i} @+{o}: {c!r}")
