#!/usr/bin/env python3
"""WEGWERF: Den Block mit Key=1 (niedrigster Offset) entpacken und untersuchen."""
import sys, struct, lzma
sys.path.insert(0,'../spike')
import nds
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def recs(path):
    d=open(path,'rb').read(); n=len(d); out=[]; o=0x102
    while o+20<=n:
        off,ln,k=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        out.append((off,ln,k)); o+=20
    return d, out[:-1]

REG={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Albania':(19.26,21.06,39.62,42.67)}

for region in ('Malta','Iceland','Albania'):
    path=f'{region}_AdvancedRouting.psf'
    d,rs = recs(path)
    rs_sorted=sorted(rs)                     # nach Offset
    first=rs_sorted[0]
    key1=[r for r in rs if r[2]==1]
    print(f"### {region}  lon{REG[region][:2]} lat{REG[region][2:]}")
    print(f"    erster Block nach Offset: off=0x{first[0]:x} len={first[1]} key=0x{first[2]:x}")
    print(f"    Records mit key==1: {key1}")
    off,ln,_ = first
    out=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[off:off+ln])
    print(f"    entpackt: {len(out)} Bytes")
    for r in range(0, min(len(out),256), 16):
        row=out[r:r+16]
        print(f"      {r:04x}  {row.hex(' ')}  "
              f"{''.join(chr(c) if 32<=c<127 else '.' for c in row)}")
    # int32-Felder als NDS-Koordinaten deuten
    print(f"    int32-Felder als NDS-Koordinate (Einheit 360/2^32 Grad):")
    rw,re_,rs_,rn = REG[region]
    for o in range(0, min(len(out),160)-4):
        v=struct.unpack_from('<i',out,o)[0]
        deg=v*360.0/2**32
        if -180<=deg<=180 and abs(deg)>0.01:
            mark=''
            if rw-1<=deg<=re_+1: mark='  <== passt zu LON'
            if rs_-1<=deg<=rn+1: mark='  <== passt zu LAT'
            if mark: print(f"       +{o:3d}  {v:>12}  {deg:9.4f} deg{mark}")
    print()
