#!/usr/bin/env python3
"""WEGWERF: Koordinatenkodierung per Bounding-Box-Orakel bestimmen."""
import sys, struct, lzma, collections

def blocks_of(path, limit=None):
    d=open(path,'rb').read()
    n=len(d) if limit is None else min(len(d),limit)
    out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0 or p>=n: break
        if p+13<=len(d):
            dic=struct.unpack_from('<I',d,p+1)[0]; siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(len(d)-p, siz*4+4096)])
                    if len(r)>=siz:
                        out.append(r[:siz]); p+=13; continue
                except Exception: pass
        p+=1
    return out

BBOX={'Malta':(14.18,14.58,35.79,36.08), 'Iceland':(-24.6,-13.4,63.3,66.6)}

# Kandidaten-Skalen: Einheiten pro Grad
SCALES={
 'NDS 2^32/360':      4294967296/360,
 'NDS 2^31/180':      2147483648/180,
 '1e-5 deg':          1e5,
 '1e-6 deg':          1e6,
 '1e-7 deg':          1e7,
 '2^24/360':          16777216/360,
 '2^25/360':          33554432/360,
 '2^26/360':          67108864/360,
 '2^27/360':          134217728/360,
 '2^28/360':          268435456/360,
 '2^30/360':          1073741824/360,
 'milliarcsec':       3600*1000,
 '2^23/180':          8388608/180,
}

def test(name, region, blobs, width, signed):
    lo_x,hi_x,lo_y,hi_y = BBOX[region]
    fmt = {2:('<h' if signed else '<H'), 4:('<i' if signed else '<I')}[width]
    best=[]
    for sname,upd in SCALES.items():
        hits=0; total=0
        for blob in blobs:
            m=len(blob)-2*width
            for o in range(0, m, 1):
                total+=1
                a=struct.unpack_from(fmt,blob,o)[0]
                b=struct.unpack_from(fmt,blob,o+width)[0]
                x=a/upd; y=b/upd
                if lo_x<=x<=hi_x and lo_y<=y<=hi_y: hits+=1
                else:
                    x=b/upd; y=a/upd
                    if lo_x<=x<=hi_x and lo_y<=y<=hi_y: hits+=1
        best.append((hits, hits*1e6/max(1,total), sname))
    best.sort(reverse=True)
    print(f"  {name} ({width*8} bit, {'signed' if signed else 'unsigned'}):")
    for h,ppm,s in best[:4]:
        print(f"     {s:16s} {h:8d} Treffer  ({ppm:.1f} pro Mio Positionen)")

for path,region in [(sys.argv[1],'Malta')]:
    print(f"### {path}")
    blobs=blocks_of(path)
    # nur eine Stichprobe, sonst zu langsam
    sample=blobs[:40]
    tot=sum(len(b) for b in sample)
    print(f"  Stichprobe: {len(sample)} Bloecke, {tot} Bytes entpackt\n")
    for w in (4,):
        for sg in (True,False):
            test(path.split('/')[-1], region, sample, w, sg)
    print()
