#!/usr/bin/env python3
"""Endabschnitt charakterisieren: wo beginnt er, was steht drin, wie gross."""
import struct, lzma, pickle, collections, numpy as np
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
ref=set(np.load('gw_refblocks.npy').tolist())
d=open(SRC,'rb').read()
# Grenze: ab wo sind fast alle Bloecke ohne Klartexteintrag?
win=200; first=None
for i in range(len(anc)-win):
    if sum(1 for j in range(i,i+win) if anc[j][0] not in ref)==win:
        first=i; break
p0=anc[first][0]
print(f"Endabschnitt beginnt bei Block #{first} @0x{p0:x} ({p0/1e6:.2f} MB)")
tail=anc[first:]
print(f"  {len(tail)} Bloecke, davon mit Klartexteintrag: "
      f"{sum(1 for p,c,s in tail if p in ref)}")
cs=[c for p,c,s in tail]; ss=[s for p,c,s in tail]
print(f"  komp   min {min(cs)} median {sorted(cs)[len(cs)//2]} max {max(cs)}")
print(f"  entpackt min {min(ss)} median {sorted(ss)[len(ss)//2]} max {max(ss)}")
print(f"  Gesamt komp {sum(cs)/1e6:.1f} MB, entpackt {sum(ss)/1e6:.1f} MB")

print("\nInhalt von 8 Bloecken aus dem Endabschnitt:")
for k in (0, 1, 2, 100, 5000, 20000, 40000, len(tail)-2):
    p,c,s = tail[k]
    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+c+64])[:s]
    txt=''.join(chr(x) if 32<=x<127 else '.' for x in r[:48])
    print(f"  #{first+k:5d} @0x{p:08x} komp {c:7d} ent {s:7d}  {r[:24].hex(' ')}  |{txt}|")
