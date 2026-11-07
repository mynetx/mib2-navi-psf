#!/usr/bin/env python3
"""Alle Vorkommen von 'Testorter Straße' patchen. Pro Block Ersatz finden,
der in den Spielraum passt - notfalls per Match auf vorhandene Strings."""
import struct, lzma, re
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]
OLD='Testorter Straße'.encode('utf-8')
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read(); n=len(d)

SETTINGS=[]
for mf in (lzma.MF_BT4,lzma.MF_BT3,lzma.MF_BT2,lzma.MF_HC4,lzma.MF_HC3):
    for depth in (0,128,512):
        for nice in (273,128,64):
            SETTINGS.append({'mf':mf,'depth':depth,'nice_len':nice})
def bestc(data,dic):
    b=None
    for s in SETTINGS:
        f=[{'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,'pb':2,
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
                        targets.append((p, dic, siz, len(d)-p-len(dec.unused_data), b))
                    p+=13; continue
            except Exception: pass
    p+=1
print(f"{len(targets)} Blöcke mit '{OLD.decode()}'\n")

PREF='Testort Testweg 1'.encode('utf-8')
patches=[]
for p,dic,siz,comp,plain in targets:
    occ=plain.count(OLD)
    base=bestc(plain,dic)
    slack=comp-len(base)
    print(f"@0x{p:x}  entpackt {siz}  komprimiert {comp}  {occ}x  Spielraum {slack:+d}")
    cands=[PREF]
    # 17-Byte-Strings, die im Block schon vorkommen -> Match, spart Bytes
    for part in set(plain.split(b'\x00')):
        if len(part)==len(OLD) and part!=OLD:
            try: part.decode('utf-8')
            except UnicodeDecodeError: continue
            if re.fullmatch(rb'[\x20-\x7e\xc0-\xff][\x20-\x7e\x80-\xff]*', part):
                cands.append(part)
    found=None
    for c in cands:
        mod=plain.replace(OLD,c)
        if len(mod)!=siz: continue
        o=bestc(mod,dic)
        if len(o)<=comp:
            found=(c,o); break
    if found:
        c,o=found
        blk=d[p:p+13]+o[13:]+b'\x00'*(comp-len(o))
        chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
        assert chk[:siz]==plain.replace(OLD,c) and len(blk)==comp
        patches.append((p,comp,blk))
        print(f"   -> {c.decode()!r}  ({len(o)} + {comp-len(o)} Padding = {comp}) OK")
    else:
        print(f"   -> KEIN Ersatz gefunden ({len(cands)} Kandidaten geprueft)")
print(f"\n{len(patches)}/{len(targets)} Blöcke patchbar")
import pickle
pickle.dump(patches, open('../spike/allpatches.pkl','wb'))
