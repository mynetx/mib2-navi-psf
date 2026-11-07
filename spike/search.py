#!/usr/bin/env python3
"""Ersatzstring finden, der in den Spielraum passt."""
import struct, lzma
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

d=open('GermanyWest_Basic.psf','rb').read()
p=0x2f4009f
dic=u32(d,p+1); siz=u64(d,p+5)
dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
raw=dec.decompress(d[p:]); COMP=len(d)-p-len(dec.unused_data)
plain=raw[:siz]
OLD='Testorter Straße'.encode('utf-8')
print(f"Zielblock @0x{p:x}: entpackt {siz}, komprimiert {COMP} B, "
      f"'{OLD.decode()}' {plain.count(OLD)}x\n")

SETTINGS=[]
for mf in (lzma.MF_BT4, lzma.MF_BT3, lzma.MF_BT2, lzma.MF_HC4, lzma.MF_HC3):
    for depth in (0,128,512):
        for nice in (273,128,64):
            SETTINGS.append({'id':lzma.FILTER_LZMA1,'dict_size':dic,'lc':3,'lp':0,
                             'pb':2,'mode':lzma.MODE_NORMAL,'mf':mf,'depth':depth,
                             'nice_len':nice})
def best_len(data):
    b=None
    for f in SETTINGS:
        try: o=lzma.compress(data, format=lzma.FORMAT_ALONE, filters=[f])
        except Exception: continue
        if b is None or len(o)<len(b): b=o
    return b

cands=[]
for s in ('Testort Testweg 1','Testorter Strasse','Testorter TestWeg',
          'Testorter Straß1','Testorter StraßX','Testorter Straßz',
          'Xestorter Straße','Testbayer Straße','Testorter Teststr'):
    e=s.encode('utf-8')
    if len(e)==len(OLD): cands.append((s,e))
# Einzelbyte-Mutationen
for i in range(len(OLD)):
    for ch in (b'X', b'1', b'Z'):
        e=bytearray(OLD); e[i:i+1]=ch; e=bytes(e)
        if len(e)==len(OLD):
            try: s=e.decode('utf-8')
            except UnicodeDecodeError: continue
            cands.append((s,e))
print(f"{len(cands)} Kandidaten, Grenze {COMP} B\n")
res=[]
for s,e in cands:
    o=best_len(plain.replace(OLD,e))
    res.append((len(o),s,e,o))
res.sort()
print(f"{'Laenge':>7} {'Delta':>6}  Passt  Ersatz")
for L,s,e,o in res[:18]:
    print(f"{L:7d} {L-COMP:+6d}  {'JA ' if L<=COMP else 'nein'}   {s!r}")
fit=[r for r in res if r[0]<=COMP]
print(f"\n{len(fit)} von {len(cands)} passen in den Spielraum")
if fit:
    L,s,e,o = fit[0]
    pad=COMP-L
    final = d[p:p+13] + o[13:] + b'\x00'*pad
    back=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(final)
    mod=plain.replace(OLD,e)
    print(f"\nGEWAEHLT: {s!r}  ({L} B + {pad} B Padding = {COMP} B)")
    print(f"  Rundlauf mit Original-Header: {len(back)>=siz} , "
          f"inhaltsgleich: {back[:siz]==mod}")
    print(f"  Blocklaenge identisch: {len(final)==COMP}")
    import pickle
    pickle.dump({'offset':p,'orig_len':COMP,'new_block':final,'old':OLD,
                 'new':e,'name':s}, open('../spike/patch.pkl','wb'))
    print(f"  gespeichert: patch.pkl")
