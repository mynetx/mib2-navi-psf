#!/usr/bin/env python3
"""WEGWERF: stride-24-Index korrekt parsen, Rohwertebereiche der Felder zeigen."""
import struct
U = 360.0/2**32

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def i32(b,o): return struct.unpack_from('<i',b,o)[0]

for path,base in (('MountainPolygons.psf',0x10e),
                  ('WorldCartographicLayer_Basic.psf',0x10e)):
    d=open(path,'rb').read(); n=len(d)
    recs=[]; o=base
    while o+24<=n:
        off=u32(d,o)
        if not(0<off<n): break
        recs.append((o, d[o:o+24])); o+=24
    print(f"### {path}  {len(recs)} Records ab 0x{base:x}, stride 24")
    print("    erste 5 Records, Feldaufteilung u32/u16:")
    for pos,r in recs[:5]:
        print(f"      off=0x{u32(r,0):07x} len16={u16(r,4):6d} f6={u16(r,6):6d} "
              f"| u32@8={u32(r,8):10d} u32@12={u32(r,12):10d} "
              f"u32@16={u32(r,16):10d} u32@20={u32(r,20):10d}")
    # Pruefen: len16 == Abstand zum naechsten Offset?
    offs=[u32(r,0) for _,r in recs]
    lens=[u16(r,4) for _,r in recs]
    srt=sorted(range(len(offs)), key=lambda i: offs[i])
    ok=0
    for a,b in zip(srt, srt[1:]):
        if offs[a]+lens[a]==offs[b]: ok+=1
    print(f"    len16 schliesst luecklos an naechsten Block an: {ok}/{len(srt)-1}")
    # Rohwertebereiche
    print("    Rohwertebereiche:")
    for fo,fmt,name in ((8,'<i','i32@8'),(12,'<i','i32@12'),
                        (16,'<i','i32@16'),(20,'<i','i32@20')):
        vs=[struct.unpack_from(fmt,r,fo)[0] for _,r in recs]
        print(f"      {name}: {min(vs):12d} .. {max(vs):12d}   "
              f"als NDS-Grad {min(vs)*U:8.3f} .. {max(vs)*U:8.3f}")
    # Welcher Faktor bringt Feld auf Europa-Spanne?
    print("    Welche Zweierpotenz bringt die Spanne auf Europa (lon 70deg / lat 37deg)?")
    for fo in (8,12,16,20):
        vs=[struct.unpack_from('<i',r,fo)[0] for _,r in recs]
        span=(max(vs)-min(vs))*U
        if span<=0: continue
        import math
        for target,label in ((70.0,'lon'),(37.0,'lat')):
            f=target/span
            print(f"      i32@{fo}: Spanne {span:8.3f}deg -> Faktor {f:9.2f} "
                  f"fuer {label}  (log2={math.log2(f):6.2f})")
    print()
