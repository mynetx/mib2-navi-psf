#!/usr/bin/env python3
"""Nur deutsche, im Navi sichtbare Namen patchen. Aenderung am Wortende
(billig durch Praefix-Match). Patchliste neu aufbauen."""
import struct, lzma, re, pickle
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read(); n=len(d)
NEEDLE=(b'Testort', b'Ortbeta', b'Ortsgamma', b'Niederortbeta')
GERMAN=re.compile(r".*(stra(ß|ss)e|weg|gasse|platz|ring|allee)$", re.I)

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
print(f"{len(blocks)} Bloecke im Zielgebiet")

OLD='Testorter Straße'.encode('utf-8'); NEW='Testort Testweg 1'.encode('utf-8')
patches=[]; report=[]
for p,dic,siz,comp,b in blocks:
    base=bestc(b,dic)
    if base is None: continue
    slack=comp-len(base)
    if slack<=0: continue
    # 1. Prioritaet: der Zielname
    tries=[]
    if OLD in b: tries.append((OLD,NEW))
    # 2. deutsche Namen, Endung ersetzen
    for part in set(b.split(b'\x00')):
        if not(8<=len(part)<=40): continue
        try: t=part.decode('utf-8')
        except UnicodeDecodeError: continue
        if not re.fullmatch(r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .\-']{7,39}", t): continue
        if not GERMAN.match(t): continue
        if 'Huo Che Zhan' in t: continue
        for k in (4,5,6,7):
            if len(part)<=k: continue
            rep=part[:-k]+b'TEST'+b'1'*(k-4)
            if len(rep)==len(part): tries.append((part,rep))
    ok=None
    for nm,rep in tries:
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
        patches.append((p,comp,blk))
        report.append((p,slack,nm.decode(),rep.decode()))
        print(f"@0x{p:x} Spielraum {slack:+4d}: {nm.decode()!r} => {rep.decode()!r}")
pickle.dump(patches, open('../spike/allpatches.pkl','wb'))
pickle.dump(report, open('../spike/patchreport.pkl','wb'))
print(f"\n{len(patches)} Blockpatches, alle mit deutschen Namen")
