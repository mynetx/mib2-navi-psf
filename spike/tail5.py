#!/usr/bin/env python3
"""Ist TESTORT spezifisch abwesend, oder fehlen kleine Orte generell?
Nachbarorte aus der vde-DB gegen den Trie halten."""
import lzma, pickle, sqlite3
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DB='../sdsrc/NO NAME/markets/eu/vde/common/vde_grammar_plugin/vde_common_c/EU/Germany/common_Germany_v1.db'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=open(SRC,'rb').read(); FIRST=54408
OK=set(range(0x20,0x7f))|{0xdf,0xc4,0xd6,0xdc}
raw=[]
for p,c,s in anc[FIRST:]:
    try: raw.append(lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[p:p+c+64])[:s])
    except Exception: raw.append(b'')
def inTrie(nd):
    n=len(nd); hit=0
    for b in raw:
        L=len(b)
        for o in range(max(0,L-3*n)):
            if b[o]!=nd[0]: continue
            ok=True
            for k in range(n):
                q=o+3*k
                if q>=L or b[q]!=nd[k]: ok=False; break
            if ok: hit+=1
    return hit
NB=['Testort','Ortsgamma','Nachbarort','Norath','Utzenhain','Dörfchen',
    'Nachbardorf B','Leiningen','Karbach','Dörth','Nachbarstadt','Boppard',
    'Niederortbeta','Oberortbeta','Ortbeta']
con=sqlite3.connect(DB)
print(f"{'Ort':16s} {'vde-DB':>7s} {'Trie':>5s}")
for o in NB:
    v=con.execute("select count(*) from Area where name=?", (o,)).fetchone()[0]
    up=o.upper().replace('Ö','Ö').encode('latin-1')
    print(f"  {o:16s} {v:5d} {inTrie(up):5d}")
