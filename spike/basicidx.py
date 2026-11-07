#!/usr/bin/env python3
"""WEGWERF: _Basic-Indexlayout per Kreuzvalidierung gegen die Ankeroffsets finden."""
import struct, lzma, collections
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def anchors(path):
    d=open(path,'rb').read(); n=len(d); out={}; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz: out[p]=r[:siz]; p+=13; continue
                except Exception: pass
        p+=1
    return d, out

for path in ('Malta_Basic.psf','Malta_GlobalPOIIndices.psf','Netherlands_ExtZips.psf'):
    d, anc = anchors(path)
    A=set(anc)
    print(f"### {path}: {len(A)} Ankerblöcke")
    best=None
    for stride in range(12, 65, 2):
        for base in range(0x80, 0x400):
            for fpos in (0,4,8):
                cnt=0; o=base
                while o+stride<=len(d):
                    v=u32(d,o+fpos)
                    if v in A: cnt+=1; o+=stride
                    else: break
                if cnt>=8 and (best is None or cnt>best[0]):
                    best=(cnt,base,stride,fpos)
    if not best:
        print("    kein konsistentes Layout gefunden\n"); continue
    cnt,base,stride,fpos = best
    print(f"    Layout: base=0x{base:x} stride={stride} Offsetfeld @+{fpos}  "
          f"-> {cnt} Records treffen Ankeroffsets ({cnt*100//len(A)}% Abdeckung)")
    # Records auslesen und Felder charakterisieren
    recs=[]; o=base
    while o+stride<=len(d):
        v=u32(d,o+fpos)
        if v not in A: break
        recs.append(d[o:o+stride]); o+=stride
    print(f"    erste 4 Records:")
    for r in recs[:4]:
        print(f"      {' '.join(r[i:i+4].hex() for i in range(0,len(r),4))}")
    nf=stride//4
    print(f"    Feldcharakteristik ({nf} u32-Felder):")
    for k in range(nf):
        vs=[u32(r,4*k) for r in recs]
        print(f"      +{4*k:2d}: {len(set(vs)):5d} verschieden  "
              f"min={min(vs):12d} max={max(vs):12d}")
    print()
