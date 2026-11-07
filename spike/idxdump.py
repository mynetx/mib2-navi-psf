#!/usr/bin/env python3
"""WEGWERF: Indexrecords vollstaendig als Hex + Feldstatistik."""
import sys, struct, collections
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]

for path,start,stride in [('Malta_AdvancedRouting.psf',0x102,20),
                          ('Iceland_AdvancedRouting.psf',0x102,20),
                          ('Albania_AdvancedRouting.psf',0x102,20)]:
    d=open(path,'rb').read(); n=len(d)
    recs=[]; o=start
    while o+stride<=n:
        off,ln,f3=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        recs.append((o,d[o:o+stride])); o+=stride
    print(f"### {path}  {len(recs)} Records, stride={stride}")
    print("    rohe Records (Hex), erste 10:")
    for pos,r in recs[:10]:
        print(f"      @0x{pos:04x}  {r[:4].hex()} {r[4:8].hex()} {r[8:12].hex()} "
              f"{r[12:16].hex()} {r[16:20].hex()}")
    print("    letzte 4:")
    for pos,r in recs[-4:]:
        print(f"      @0x{pos:04x}  {r[:4].hex()} {r[4:8].hex()} {r[8:12].hex()} "
              f"{r[12:16].hex()} {r[16:20].hex()}")
    # Feldstatistik
    for fo in range(0, stride, 4):
        vals=[u32(r,fo) for _,r in recs if len(r)>=fo+4]
        u=set(vals)
        print(f"    Feld +{fo:2d}: {len(u):4d} verschieden, "
              f"min=0x{min(vals):08x} max=0x{max(vals):08x}")
    # high16/low16 des Feldes +8
    hi=collections.Counter(u16(r,10) for _,r in recs)
    lo=[u16(r,8) for _,r in recs]
    print(f"    Feld+8 high16: {dict(sorted(hi.items()))}")
    print(f"    Feld+8 low16 : {len(set(lo))} verschieden, "
          f"0x{min(lo):04x}..0x{max(lo):04x}")
    print()
