#!/usr/bin/env python3
"""Wieviel Spielraum habe ich? Unveraenderte Nutzlast neu komprimieren."""
import struct, lzma, itertools
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

d=open('GermanyWest_Basic.psf','rb').read()
for p in (0x2f4009f, 0x346c45e):
    dic=u32(d,p+1); siz=u64(d,p+5)
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[p:]); comp_len=len(d)-p-len(dec.unused_data)
    plain=raw[:siz]
    print(f"@0x{p:x}  entpackt {siz}  original komprimiert {comp_len}")
    best=None
    for mf in (lzma.MF_BT4, lzma.MF_BT3, lzma.MF_BT2, lzma.MF_HC4, lzma.MF_HC3):
        for depth in (0, 128, 512):
            for nice in (273, 128, 64):
                f=[{'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,'pb':2,
                    'mode':lzma.MODE_NORMAL,'mf':mf,'depth':depth,'nice_len':nice}]
                try: o=lzma.compress(plain, format=lzma.FORMAT_ALONE, filters=f)
                except Exception: continue
                if best is None or len(o)<best[0]: best=(len(o),mf,depth,nice)
    bl,mf,depth,nice=best
    print(f"   bestes Python-LZMA (unveraendert): {bl} B  -> Spielraum "
          f"{comp_len-bl:+d} B  (mf={mf} depth={depth} nice={nice})")
    if comp_len-bl>=0:
        print(f"   => Es gibt Spielraum. Aenderung darf bis {comp_len-bl} B kosten.")
    else:
        print(f"   => KEIN Spielraum. Original-Encoder ist besser als Python.")
    print()
