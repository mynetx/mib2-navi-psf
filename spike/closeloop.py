#!/usr/bin/env python3
"""Kreis schliessen: eigene (level,col,row) -> NDS packed Tile ID -> nds.py-BBox.
Stimmt beides, ist das Ergebnis mit der Standard-NDS-Toolchain kompatibel."""
import sys, math
sys.path.insert(0,'../spike')
import nds

def morton(col,row,level):
    """col in die geraden Bits, row in die ungeraden; Zweierkomplement je Achse."""
    c = col & ((1<<(level+1))-1)
    r = row & ((1<<level)-1)
    m=0
    for i in range(level+1):
        if c>>i & 1: m |= 1<<(2*i)
        if i<level and (r>>i & 1): m |= 1<<(2*i+1)
    return m

TESTS=[  # (mein L, col, row) aus dem Export
 (12,164,408),(12,165,408),(13,330,816),(10,40,102),(9,20,50),(11,82,204),
]
print(f"{'L':>3} {'col':>5} {'row':>5} | {'NDS lvl':>7} {'tileNr':>9} {'packedId':>11} "
      f"| meine BBox                      | nds.py-BBox")
allok=True
for L,col,row in TESTS:
    step=360.0/2**L
    myw, mys = col*step, row*step
    mye, myn = myw+step, mys+step
    lvl=L-1
    nr=morton(col,row,lvl)
    pid=nr + (1<<(16+lvl))
    r=nds.bbox_of_packed(pid)
    if r is None:
        print(f"{L:3d} {col:5d} {row:5d} | packed ID {pid} ungueltig"); allok=False; continue
    (w,e,s,n),(l2,nr2)=r
    ok = (abs(w-myw)<1e-4 and abs(e-mye)<1e-4 and abs(s-mys)<1e-4 and abs(n-myn)<1e-4)
    allok &= ok
    print(f"{L:3d} {col:5d} {row:5d} | {lvl:7d} {nr:9d} {pid:11d} "
          f"| lon[{myw:8.4f},{mye:8.4f}] lat[{mys:7.4f},{myn:7.4f}] "
          f"| lon[{w:8.4f},{e:8.4f}] lat[{s:7.4f},{n:7.4f}]  {'OK' if ok else 'ABWEICHUNG'}")
print(f"\nAlle Kacheln stimmen mit der NDS-Referenz: {allok}")
