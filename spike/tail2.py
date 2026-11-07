#!/usr/bin/env python3
"""Endabschnitt: sind das Trie-Knoten einer Namenssuche?"""
import struct, lzma, pickle
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read()
FIRST=54408
def blk(i):
    p,c,s=anc[i]
    return lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+c+64])[:s]
for i in (74408, 59408):
    r=blk(i)
    print(f"=== Block #{i} @0x{anc[i][0]:x}, {len(r)} B entpackt ===")
    for o in range(0, min(len(r),160), 16):
        row=r[o:o+16]
        print(f"  {o:04x}  {row.hex(' ')}  "
              f"{''.join(chr(x) if 32<=x<127 else '.' for x in row)}")
    n=struct.unpack_from('<H',r,0)[0]
    print(f"  Kopf u16 = {n}; als {n} Eintraege a 3 B:")
    for k in range(min(n,10)):
        o=2+3*k
        ch=r[o]; ptr=struct.unpack_from('<H',r,o+1)[0]
        print(f"     {k}: {chr(ch) if 32<=ch<127 else hex(ch):>4s}  ptr {ptr:6d}"
              f"  -> Block #{FIRST+ptr} " if FIRST+ptr<len(anc) else "")
    print()
