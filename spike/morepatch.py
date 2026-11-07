#!/usr/bin/env python3
"""Mehr patchbare Namen: Bloecke mit Spielraum im Zielgebiet."""
import struct, lzma, re, pickle
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read(); n=len(d)
NEEDLE=(b'Testort', b'Ortbeta', b'Ortsgamma', b'Niederortbeta')

blocks=[]; p=0
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
                    if any(x in b for x in NEEDLE):
                        blocks.append((p,dic,siz,len(d)-p-len(dec.unused_data),b))
                    p+=13; continue
            except Exception: pass
    p+=1

SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
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

print(f"{len(blocks)} Bloecke im Zielgebiet")
withslack=[]
for p,dic,siz,comp,b in blocks:
    base=bestc(b,dic)
    if base is None: continue
    slack=comp-len(base)
    if slack>0: withslack.append((p,dic,siz,comp,b,slack))
print(f"{len(withslack)} davon mit Spielraum\n")

patches=pickle.load(open('../spike/allpatches.pkl','rb'))
done={x[0] for x in patches}
added=0
for p,dic,siz,comp,b,slack in sorted(withslack, key=lambda x:-x[5]):
    if p in done: continue
    names=set()
    for part in b.split(b'\x00'):
        if 8<=len(part)<=40:
            try: t=part.decode('utf-8')
            except UnicodeDecodeError: continue
            if re.fullmatch(r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .\-']{7,39}", t): names.add(part)
    ok=None
    for nm in sorted(names, key=lambda x:-len(x))[:30]:
        rep=b'CLAUDETEST'+b'X'*(len(nm)-10)
        if len(rep)!=len(nm): continue
        mod=b.replace(nm,rep)
        if len(mod)!=siz: continue
        o=bestc(mod,dic)
        if o is None or len(o)>comp: continue
        blk=d[p:p+13]+o[13:]+b'\x00'*(comp-len(o))
        try: chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
        except Exception: continue
        if chk[:siz]==mod and len(blk)==comp:
            ok=(nm,rep,blk); break
    if ok:
        nm,rep,blk=ok
        patches.append((p,comp,blk)); done.add(p); added+=1
        print(f"@0x{p:x} Spielraum {slack:+4d}: {nm.decode()!r} => {rep.decode()!r}")
        if added>=8: break
pickle.dump(patches, open('../spike/allpatches.pkl','wb'))
print(f"\n{added} zusaetzliche Patches, gesamt {len(patches)}")
