#!/usr/bin/env python3
"""WEGWERF: Kachelbasis aller AdvancedRouting-Regionen -> Katalog oder Geometrie?"""
import glob, struct, os
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
rows=[]
for path in sorted(glob.glob('*_AdvancedRouting.psf')):
    d=open(path,'rb').read(); n=len(d); ks=[]; o=0x102
    while o+20<=n:
        off,ln,k=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        ks.append(k); o+=20
    ks=ks[:-1]
    if not ks: continue
    lows=[k & 0xFFFF for k in ks]
    groups=sorted({k>>21 for k in ks})
    rows.append((path.replace('_AdvancedRouting.psf',''), len(ks),
                 min(lows), max(lows), groups))
rows.sort(key=lambda r: r[2])
print(f"{'Region':30s} {'Kacheln':>8} {'Basis dez':>10} {'max dez':>10} "
      f"{'Spanne':>7}  Gruppen")
for name,cnt,lo,hi,g in rows:
    print(f"{name:30s} {cnt:8d} {lo:10d} {hi:10d} {hi-lo:7d}  {g}")
print(f"\n{len(rows)} Regionen")
bases=[r[2] for r in rows]
print(f"Basen: {bases}")
mods=[b%1000 for b in bases]
import collections
print(f"Basis mod 1000: {collections.Counter(mods).most_common()}")
