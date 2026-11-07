#!/usr/bin/env python3
"""Prototyp: Block entpacken, String tauschen, neu packen, Laenge pruefen."""
import struct, lzma
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

OLD='Testorter Straße'.encode('utf-8')
NEW='Testort Testweg 1'.encode('utf-8')
print(f"OLD {len(OLD)} B: {OLD!r}")
print(f"NEW {len(NEW)} B: {NEW!r}")
assert len(OLD)==len(NEW), "Laengen muessen gleich sein"
print()

path='GermanyWest_Basic.psf'
d=open(path,'rb').read()
for p in (0x2f4009f, 0x346c45e):
    props=d[p]; dic=u32(d,p+1); siz=u64(d,p+5)
    # exakte komprimierte Laenge via unused_data
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[p:])
    assert len(raw)>=siz
    comp_len = len(d)-p-len(dec.unused_data)
    plain = raw[:siz]
    print(f"@0x{p:x}: props=0x{props:02x} dictSize={dic} uncompressed={siz} "
          f"komprimiert={comp_len} B")
    assert OLD in plain, "String nicht im Block"
    n_occ = plain.count(OLD)
    mod = plain.replace(OLD, NEW)
    assert len(mod)==len(plain)
    print(f"   {n_occ}x ersetzt, entpackte Laenge unveraendert: {len(mod)==siz}")

    # neu komprimieren mit identischen Filtern
    filt=[{'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,'pb':2}]
    out=lzma.compress(mod, format=lzma.FORMAT_ALONE, filters=filt)
    print(f"   neu komprimiert: {len(out)} B  (alt {comp_len} B, "
          f"Differenz {len(out)-comp_len:+d})")
    print(f"   Header alt: {d[p:p+13].hex(' ')}")
    print(f"   Header neu: {out[:13].hex(' ')}")
    print(f"   Header identisch: {out[:13]==d[p:p+13]}")
    if out[:13]!=d[p:p+13]:
        # Header auf das Original zwingen und Rundlauf pruefen
        fixed = d[p:p+13] + out[13:]
        try:
            back=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(fixed)
            print(f"   mit Original-Header: Rundlauf ok, {len(back)} B, "
                  f"inhaltsgleich: {back[:siz]==mod}")
        except Exception as ex:
            print(f"   mit Original-Header: FEHLER {ex}")
    if len(out)<=comp_len:
        pad = comp_len-len(out)
        cand = out + b'\x00'*pad
        back=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(cand)
        print(f"   mit {pad} B Padding auf Originallaenge: "
              f"Rundlauf ok, inhaltsgleich: {back[:siz]==mod}")
    else:
        print(f"   PASST NICHT - neuer Strom ist laenger. Hoehere Kompression testen.")
        for pre in (9,):
            f2=[{'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,'pb':2,
                 'mode':lzma.MODE_NORMAL,'nice_len':273,'mf':lzma.MF_BT4,'depth':512}]
            o2=lzma.compress(mod, format=lzma.FORMAT_ALONE, filters=f2)
            print(f"      bt4/depth512: {len(o2)} B ({len(o2)-comp_len:+d})")
    print()
