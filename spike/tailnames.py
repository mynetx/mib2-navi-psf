#!/usr/bin/env python3
"""Namensbestand des Endabschnitt-Tries extrahieren (maximale Ketten)."""
import lzma, pickle, collections, re
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read(); FIRST=54408
OK=set(range(0x20,0x7f))|{0xdf,0xc4,0xd6,0xdc}
names=collections.Counter()
for p,c,s in anc[FIRST:]:
    try: b=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+c+64])[:s]
    except Exception: continue
    n=len(b); o=0
    while o+3<=n:
        if b[o] in OK:
            st=o; out=bytearray()
            while o+3<=n and b[o] in OK: out.append(b[o]); o+=3
            if len(out)>=4: names[bytes(out)]+=1
            # ueberlappende Ketten ab st+1 gehen verloren -> bewusst: maximale Ketten
            o=st+1
        else: o+=1
print(f"{len(names)} verschiedene maximale Ketten (>=4 Zeichen)")
srt=sorted(names.items(), key=lambda x:-len(x[0]))
print("\nlaengste 12:")
for k,v in srt[:12]: print(f"   {v:4d}x  {k.decode('latin-1')}")
strasse=[k for k in names if b'STRAS' in k or k.endswith(b'WEG') or b'GASSE' in k]
print(f"\nKetten mit STRAS/WEG/GASSE: {len(strasse)}")
orte=[k for k in names if b'STRAS' not in k and b'WEG' not in k and b'GASSE' not in k]
print(f"uebrige (Ortskandidaten): {len(orte)}")
with open('gw_trie_names.txt','w',encoding='utf-8') as f:
    for k,v in sorted(names.items()):
        f.write(f"{v}\t{k.decode('latin-1')}\n")
print("-> gw_trie_names.txt")
