#!/usr/bin/env python3
"""Passt der Marker in die ORIGINAL-Blocklaenge? Zweistufige Parametersuche.

Nach Test 9 steht fest: ein Block darf physisch nicht wachsen. Also muss der
neue Strom <= der alte sein. Gesucht sind 25 B bei Ziel B (0,18 %) und 23 B
bei Ziel C.

Stufe 1: lc/lp/pb vollstaendig (15x5 gueltige Kombinationen) bei BT4/273/0.
Stufe 2: fuer die besten fuenf alle mf x nice_len x depth.
"""
import lzma, struct, itertools, sys
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
d=open(SRC,'rb').read()
MF=[lzma.MF_BT4,lzma.MF_BT3,lzma.MF_BT2,lzma.MF_HC4,lzma.MF_HC3]
MFN={lzma.MF_BT4:'BT4',lzma.MF_BT3:'BT3',lzma.MF_BT2:'BT2',lzma.MF_HC4:'HC4',lzma.MF_HC3:'HC3'}
NICE=[16,32,64,128,192,273]; DEPTH=[0,64,256,512,1024]

def comp(data,ds,lc,lp,pb,mf,nl,dp):
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':lc,'lp':lp,'pb':pb,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':dp}]
    try: return lzma.compress(data,format=lzma.FORMAT_ALONE,filters=f)
    except Exception: return None

def blk(P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

MARK=sys.argv[1].encode() if len(sys.argv)>1 else b'Hausbaq'
for name,P in (('Ziel B',0x3392334),('Ziel C',0x346c45e),('z1-z9',0x36ce94a)):
    raw,orig=blk(P); ds=struct.unpack_from('<I',d,P+1)[0]
    data=raw.replace(b'Testort',MARK)
    s1=[]
    for lc,lp in [(a,b) for a in range(5) for b in range(5) if a+b<=4]:
        for pb in range(5):
            o=comp(data,ds,lc,lp,pb,lzma.MF_BT4,273,0)
            if o: s1.append((len(o),lc,lp,pb))
    s1.sort()
    best=(orig+10**9,None)
    for ln,lc,lp,pb in s1[:5]:
        for mf,nl,dp in itertools.product(MF,NICE,DEPTH):
            o=comp(data,ds,lc,lp,pb,mf,nl,dp)
            if o and len(o)<best[0]: best=(len(o),(lc,lp,pb,MFN[mf],nl,dp))
    print(f"{name} @0x{P:07x}  Original {orig}  Marker {MARK.decode()}")
    print(f"   Stufe 1 bestes lc/lp/pb: {s1[0][0]} B mit lc={s1[0][1]} lp={s1[0][2]} pb={s1[0][3]}"
          f"   (Original-props lc=3 lp=0 pb=2)")
    print(f"   Stufe 2 bestes gesamt:   {best[0]} B mit {best[1]}")
    print(f"   -> {'PASST' if best[0]<=orig else f'fehlen noch {best[0]-orig} B'}\n")
