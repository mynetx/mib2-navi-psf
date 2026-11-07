#!/usr/bin/env python3
"""Gepatchte GermanyWest_Basic.psf erzeugen: nur ein Block, gleiche Dateigroesse."""
import struct, lzma, hashlib, os
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='../spike/GermanyWest_Basic.patched.psf'
OLD='Testorter Straße'.encode('utf-8')
NEW='Testort Testweg 1'.encode('utf-8')
assert len(OLD)==len(NEW)==17
P=0x2f4009f

d=bytearray(open(SRC,'rb').read())
dic=u32(d,P+1); siz=u64(d,P+5)
dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
raw=dec.decompress(bytes(d[P:])); COMP=len(d)-P-len(dec.unused_data)
plain=raw[:siz]
assert plain.count(OLD)==1
mod=plain.replace(OLD,NEW)
assert len(mod)==siz

best=None
for mf in (lzma.MF_BT4,lzma.MF_BT3,lzma.MF_BT2,lzma.MF_HC4,lzma.MF_HC3):
    for depth in (0,128,512):
        for nice in (273,128,64):
            f=[{'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,'pb':2,
                'mode':lzma.MODE_NORMAL,'mf':mf,'depth':depth,'nice_len':nice}]
            try: o=lzma.compress(mod, format=lzma.FORMAT_ALONE, filters=f)
            except Exception: continue
            if best is None or len(o)<len(best): best=o
assert len(best)<=COMP, f"passt nicht: {len(best)} > {COMP}"
newblk = bytes(d[P:P+13]) + best[13:] + b'\x00'*(COMP-len(best))
assert len(newblk)==COMP

back=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(newblk)
assert back[:siz]==mod, "Rundlauf fehlgeschlagen"

orig_md5=hashlib.md5(bytes(d)).hexdigest()
d[P:P+COMP]=newblk
open(DST,'wb').write(bytes(d))
print(f"Quelle   {SRC}")
print(f"Ziel     {DST}")
print(f"Groesse  original {os.path.getsize(SRC)}  neu {os.path.getsize(DST)}  "
      f"identisch: {os.path.getsize(SRC)==os.path.getsize(DST)}")
print(f"Block    @0x{P:x}, {COMP} B, komprimiert {len(best)} + {COMP-len(best)} B Padding")
print(f"Aenderung '{OLD.decode()}' -> '{NEW.decode()}' (1x, entpackte Groesse {siz} unveraendert)")
print(f"md5      original {orig_md5}")
print(f"         neu      {hashlib.md5(bytes(d)).hexdigest()}")
diff=sum(1 for a,b in zip(open(SRC,'rb').read(), bytes(d)) if a!=b)
print(f"abweichende Bytes in der Gesamtdatei: {diff} von {len(d)}")
print(f"Index unberuehrt, Dateigroesse unveraendert.")
