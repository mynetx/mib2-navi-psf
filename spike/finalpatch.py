#!/usr/bin/env python3
"""Endgueltige Testdatei mit unterscheidbaren Markern pro Block.
Damit verraet die Anzeige im Auto, welcher Block welche Zoomstufe bedient."""
import struct, lzma, os
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='../spike/GermanyWest_Basic.patched.psf'
OLD=b'Testort'
# Kandidaten je Block, in Reihenfolge der Erkennbarkeit
WANT={0x2f34830:[b'TESTBA1',b'Hausba1',b'Hausbaz'],
      0x2f4009f:[b'TESTBA2',b'Hausba2',b'Hausbaz'],
      0x36ce94a:[b'TESTBA3',b'Hausba3',b'Hausbaz']}
SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':128,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':512,'nice_len':273},
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

d=bytearray(open(SRC,'rb').read()); n=len(d)
applied=[]
for P,cands in WANT.items():
    dic=u32(d,P+1); siz=u64(d,P+5)
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(bytes(d[P:])); COMP=len(d)-P-len(dec.unused_data)
    plain=raw[:siz]; occ=plain.count(OLD)
    for c in cands:
        mod=plain.replace(OLD,c)
        if len(mod)!=siz: continue
        o=bestc(mod,dic)
        if o is None or len(o)>COMP: continue
        blk=bytes(d[P:P+13])+o[13:]+b'\x00'*(COMP-len(o))
        chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
        if chk[:siz]==mod and len(blk)==COMP:
            d[P:P+COMP]=blk
            applied.append((P,c.decode(),occ,COMP,len(o)))
            print(f"@0x{P:x}  {occ}x {OLD.decode()} -> {c.decode()}  "
                  f"({len(o)} + {COMP-len(o)} Pad = {COMP})")
            break
    else:
        print(f"@0x{P:x}  kein Kandidat passt")
open(DST,'wb').write(bytes(d))
print(f"\nGroesse original {os.path.getsize(SRC)}  neu {os.path.getsize(DST)}  "
      f"identisch: {os.path.getsize(SRC)==os.path.getsize(DST)}")

# Vollverifikation
d2=open(DST,'rb').read(); ok=bad=0; q=0
cnt={b'TESTBA1':0,b'TESTBA2':0,b'TESTBA3':0,b'Hausbaz':0,b'Testort':0}
while True:
    q=d2.find(b'\x5d',q)
    if q<0: break
    if q+13<=n:
        dic=u32(d2,q+1); s2=u64(d2,q+5)
        if dic==s2 and 0<s2<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                    d2[q:q+min(n-q,s2*4+4096)])
                if len(r)>=s2:
                    b=r[:s2]; ok+=1
                    for k in cnt: cnt[k]+=b.count(k)
                    q+=13; continue
            except Exception: bad+=1
    q+=1
print(f"alle Bloecke dekomprimierbar: {ok} ok, {bad} fehlerhaft")
for k,v in cnt.items(): print(f"   {k.decode():10s} {v:3d}x")
