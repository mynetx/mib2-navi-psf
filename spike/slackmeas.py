#!/usr/bin/env python3
"""Steht zwischen den Bloecken Fuellmaterial? Echte LZMA-Stromlaenge gegen
den Abstand zum naechsten Anker messen."""
import struct, lzma, pickle, collections, random
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read()
random.seed(7)
sample=random.sample(range(len(anc)-1), 800)
TARGET={0x36ca22e,0x3392334,0x346c45e,0x2f4009f,0x2f34830,0x36ce94a}
idx={p:i for i,(p,c,s) in enumerate(anc)}
sample += [idx[t] for t in TARGET]
pad=collections.Counter(); details=[]
for i in sample:
    p,gap,siz = anc[i]
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    try: dec.decompress(d[p:p+gap])
    except Exception: continue
    real = gap - len(dec.unused_data)
    pad[gap-real]+=1
    if p in TARGET: details.append((p,gap,real,gap-real))
print(f"{sum(pad.values())} Bloecke gemessen")
print(f"Fuellbytes zwischen Blockende und naechstem Anker: {pad.most_common(10)}")
print(f"Bloecke mit Fuellung > 0: {sum(v for k,v in pad.items() if k>0)}")
print(f"maximale Fuellung: {max(pad)}")
print("\nZielbloecke:")
for p,gap,real,pd in sorted(details):
    print(f"  @0x{p:07x}  Abstand {gap:6d}  echter Strom {real:6d}  Fuellung {pd:+4d}")
