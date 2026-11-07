#!/usr/bin/env python3
"""Alle 'Testort'-Vorkommen patchen. Minimalmutationen erhalten den LZMA-Praefixmatch
und kosten dadurch fast nichts."""
import struct, lzma, pickle
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read(); n=len(d)
OLD=b'Testort'

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

# Kandidaten: von "nur letztes Byte" bis "ganzes Wort"
CANDS=[b'Hausbaz', b'HausbaZ', b'Hausba1', b'HausbaX', b'Hausbax',
       b'Hausbzy', b'HausbXy', b'Hauzbay', b'HauXbay', b'Haisbay',
       b'HXstort', b'Xestort', b'TESTBAY']

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
    base=bestc(b,dic)
    slack=comp-len(base) if base else None
    line=f"@0x{p:x} entpackt {siz:6d} komp {comp:6d} {occ:2d}x Spielraum "
    line+=f"{slack:+4d}" if slack is not None else "  n/a"
    found=None
    for c in CANDS:
        mod=b.replace(OLD,c)
        if len(mod)!=siz: continue
        o=bestc(mod,dic)
        if o is None or len(o)>comp: continue
        blk=d[p:p+13]+o[13:]+b'\x00'*(comp-len(o))
        try: chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
        except Exception: continue
        if chk[:siz]==mod and len(blk)==comp:
            found=(c,o,blk); break
    if found:
        c,o,blk=found
        patches.append((p,comp,blk)); rep.append((p,occ,c.decode()))
        print(line+f"  -> {c.decode()!r}  neu {len(o)} (+{comp-len(o)} Pad)  OK")
    else:
        print(line+f"  -> kein Kandidat passt")
print(f"\n{len(patches)}/{len(targets)} Bloecke patchbar, "
      f"{sum(r[1] for r in rep)} Namensvorkommen")
pickle.dump(patches, open('deeppatches.pkl','wb'))
pickle.dump(rep, open('deepreport.pkl','wb'))
