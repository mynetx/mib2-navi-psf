#!/usr/bin/env python3
"""Ortsnamen 'Testort' -> 'TESTBAY' in allen Bloecken mit Spielraum.
Ortslabels sind auf vielen Zoomstufen sichtbar."""
import struct, lzma, pickle
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read(); n=len(d)
OLD=b'Testort'; NEW=b'TESTBAY'
assert len(OLD)==len(NEW)

SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':128,'nice_len':273},
     {'mf':lzma.MF_HC4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_BT3,'depth':0,'nice_len':128},
     {'mf':lzma.MF_BT2,'depth':0,'nice_len':64}]
def bestc(data,dic):
    ds=max(4096,min(dic,1<<26)); b=None
    for s in SET:
        f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':3,'lp':0,'pb':2,
            'mode':lzma.MODE_NORMAL,**s}]
        try: o=lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f)
        except Exception: continue
        if b is None or len(o)<len(b): b=o
    return b

targets=[]; p=0
while True:
    p=d.find(b'\x5d',p)
    if p<0: break
    if p+13<=n:
        dic=u32(d,p+1); siz=u64(d,p+5)
        if dic==siz and 0<siz<=16_000_000:
            try:
                dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                r=dec.decompress(d[p:])
                if len(r)>=siz:
                    b=r[:siz]
                    if OLD in b:
                        targets.append((p,dic,siz,len(d)-p-len(dec.unused_data),b))
                    p+=13; continue
            except Exception: pass
    p+=1
print(f"{len(targets)} Bloecke mit {OLD.decode()!r}\n")

patches=[]; rep=[]
for p,dic,siz,comp,b in targets:
    occ=b.count(OLD)
    mod=b.replace(OLD,NEW)
    assert len(mod)==siz
    o=bestc(mod,dic)
    base=bestc(b,dic)
    slack = comp-len(base) if base else None
    fits = o is not None and len(o)<=comp
    print(f"@0x{p:x} entpackt {siz:6d} komp {comp:6d} {occ:2d}x  "
          f"Spielraum {slack if slack is None else f'{slack:+d}'}  "
          f"neu {len(o) if o else '-'}  {'PASST' if fits else 'zu lang'}")
    if fits:
        blk=d[p:p+13]+o[13:]+b'\x00'*(comp-len(o))
        chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
        assert chk[:siz]==mod and len(blk)==comp
        patches.append((p,comp,blk)); rep.append((p,occ,siz))
print(f"\n{len(patches)}/{len(targets)} Bloecke patchbar, "
      f"{sum(r[1] for r in rep)} Namensvorkommen geaendert")
pickle.dump(patches, open('placepatches.pkl','wb'))
