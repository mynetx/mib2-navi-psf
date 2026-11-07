#!/usr/bin/env python3
"""WEGWERF: Koordinateneinheit aus der Spannweite der Kachelpositionen loesen."""
import struct, lzma, sys
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def i32(b,o): return struct.unpack_from('<i',b,o)[0]

def blocks(path):
    d=open(path,'rb').read(); n=len(d); out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz: out.append(r[:siz]); p+=13; continue
                except Exception: pass
        p+=1
    return out

REG={'Malta':(14.18,14.58,35.79,36.08),
     'Iceland':(-24.55,-13.49,63.39,66.57),
     'Albania':(19.26,21.06,39.62,42.67)}

for region in ('Malta','Albania','Iceland'):
    path=f'{region}_Basic.psf'
    try: bs=blocks(path)
    except FileNotFoundError:
        print(f"{path} fehlt"); continue
    bs=[b for b in bs if len(b)>=24]
    print(f"### {region}_Basic: {len(bs)} Bloecke >=24 B")
    w,e,s,nn = REG[region]
    # Feld 0/1 konstant?
    f0={u32(b,0) for b in bs}; f1={u32(b,4) for b in bs}
    print(f"    Feld0: {len(f0)} verschiedene Werte  Feld1: {len(f1)}")
    if len(f0)<=3: print(f"      Feld0-Werte: {[hex(x) for x in sorted(f0)]}")
    if len(f1)<=3: print(f"      Feld1-Werte: {[hex(x) for x in sorted(f1)]}")
    for a,bb,lbl in ((8,12,'Feld2/3'),(0,4,'Feld0/1')):
        xs=[u32(x,a) for x in bs]; ys=[u32(x,bb) for x in bs]
        rx=max(xs)-min(xs); ry=max(ys)-min(ys)
        print(f"    {lbl}: X {min(xs)}..{max(xs)} (Spanne {rx})   "
              f"Y {min(ys)}..{max(ys)} (Spanne {ry})")
        if rx>0 and ry>0:
            ux=(e-w)/rx; uy=(nn-s)/ry
            print(f"        Einheit aus X: {ux:.10f} deg/Schritt   "
                  f"aus Y: {uy:.10f} deg/Schritt   Verhaeltnis {ux/uy:.4f}")
            for nm,u in (('360/2^32',360/2**32),('1e-5',1e-5),('1e-6',1e-6),
                         ('1e-7',1e-7),('180/2^31',180/2**31),('1/3600000',1/3600000)):
                print(f"        {nm:10s}: X-> {min(xs)*u:10.4f}..{max(xs)*u:10.4f}  "
                      f"Y-> {min(ys)*u:10.4f}..{max(ys)*u:10.4f}")
            break
    print()
