#!/usr/bin/env python3
"""Endgueltige Testdatei: 'Testort' -> 'TESTBAY' in allen patchbaren Bloecken."""
import struct, lzma, pickle, os, hashlib
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='../spike/GermanyWest_Basic.patched.psf'
patches=pickle.load(open('placepatches.pkl','rb'))
d=bytearray(open(SRC,'rb').read())
for p,comp,blk in patches:
    assert len(blk)==comp
    d[p:p+comp]=blk
open(DST,'wb').write(bytes(d))
print(f"{len(patches)} Bloecke gepatcht")
print(f"Groesse original {os.path.getsize(SRC)}  neu {os.path.getsize(DST)}  "
      f"identisch: {os.path.getsize(SRC)==os.path.getsize(DST)}")

# Vollverifikation
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
d2=open(DST,'rb').read(); n=len(d2)
ok=bad=0; q=0
names={b'TESTBAY':0, b'TESTBAYer Stra\xc3\x9fe':0, b'Testort':0,
       'Testorter Straße'.encode():0}
while True:
    q=d2.find(b'\x5d',q)
    if q<0: break
    if q+13<=n:
        dic=u32(d2,q+1); s2=struct.unpack_from('<Q',d2,q+5)[0]
        if dic==s2 and 0<s2<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                    d2[q:q+min(n-q,s2*4+4096)])
                if len(r)>=s2:
                    b=r[:s2]; ok+=1
                    for k in names: names[k]+=b.count(k)
                    q+=13; continue
            except Exception: bad+=1
    q+=1
print(f"alle Bloecke dekomprimierbar: {ok} ok, {bad} fehlerhaft")
for k,v in names.items(): print(f"   {k.decode('utf-8','replace')!r:22s} {v:3d}x")
diff=sum(1 for a,b in zip(open(SRC,'rb').read(), d2) if a!=b)
print(f"abweichende Bytes: {diff} von {n}")
