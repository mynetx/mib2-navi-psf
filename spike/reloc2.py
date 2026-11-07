#!/usr/bin/env python3
"""Korrigierte Blockverschiebung.

Fehler des ersten Versuchs (§6d Test 1): die Bloecke hingen HINTER der
verketteten Metadatensektion. Deren Kette endet in jeder .psf exakt an der
Dateigrenze -- diese Invariante war gebrochen.

Jetzt: die Bloecke werden VOR die Metadatenkette eingefuegt (@79.314.569),
die Kette rueckt um denselben Betrag nach hinten, ihre fuenf Kopfzeiger
werden mitgezogen. Die Datei endet wieder mit der Metadatenkette.

Marker RELOBAY in den drei bisher unerreichbaren Bloecken, Basis ist das
unveraenderte Original.
"""
import struct, lzma, os
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='../spike/GermanyWest_Basic.reloc2.psf'
OLD=b'Testort'; NEW=b'RELOBAY'
INS=79314569                       # Beginn der Metadatenkette
PTR=[0x096,0x00a,0x07a,0x035,0x04d]
TARGETS=[0x36ca22e,0x3392334,0x346c45e]
SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':128,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT3,'depth':0,'nice_len':128}]
def bestc(data,dic):
    ds=max(4096,min(dic,1<<26)); b=None
    for s in SET:
        f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':3,'lp':0,'pb':2,
            'mode':lzma.MODE_NORMAL,**s}]
        try: o=lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f)
        except Exception: continue
        if b is None or len(o)<len(b): b=o
    return b

d=open(SRC,'rb').read(); N0=len(d)
# 1) Sicherstellen: nur die fuenf bekannten Zeiger liegen hinter dem Einfuegepunkt
late=[o for o in range(N0-4) if o<0x112 and INS<=struct.unpack_from('<I',d,o)[0]<=N0]
print(f"Kopf-u32 >= Einfuegepunkt: {[hex(o) for o in late]}")
assert set(late)==set(PTR), "unerwarteter Zeiger im Kopf"

# 2) neue Bloecke bauen
newblocks=[]; plan=[]
for P in TARGETS:
    dic=struct.unpack_from('<I',d,P+1)[0]; siz=struct.unpack_from('<Q',d,P+5)[0]
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); COMP=N0-P-len(dec.unused_data)
    plain=raw[:siz]; occ=plain.count(OLD)
    q=d.find(struct.pack('<IH',P,COMP))
    assert q>=0 and d.find(struct.pack('<IH',P,COMP),q+1)<0
    mod=plain.replace(OLD,NEW); assert len(mod)==siz
    nb=bestc(mod,dic); assert len(nb)<=0xFFFF
    plan.append((P,COMP,q,occ,nb,siz)); newblocks.append(nb)
    print(f"@0x{P:07x} {occ}x  alt {COMP} -> neu {len(nb)} ({len(nb)-COMP:+d})  Index @0x{q:x}")
payload=b''.join(newblocks); delta=len(payload)

# 3) zusammensetzen
out=bytearray(d[:INS]) + payload + bytearray(d[INS:])
assert len(out)==N0+delta
# 4) Kopfzeiger verschieben
for o in PTR:
    v=struct.unpack_from('<I',out,o)[0]
    struct.pack_into('<I',out,o,v+delta)
# 5) Indexeintraege auf die neuen Positionen
pos=INS
for (P,COMP,q,occ,nb,siz) in plan:
    struct.pack_into('<IH',out,q,pos,len(nb))
    print(f"@0x{P:07x} -> neu @{pos} (0x{pos:x}), Laenge {len(nb)}")
    pos+=len(nb)
open(DST,'wb').write(bytes(out))
print(f"\n{N0} -> {len(out)} B (+{delta})")
