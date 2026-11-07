#!/usr/bin/env python3
"""Ankerliste (Offset, komprimierte Laenge, entpackte Groesse) fuer eine .psf,
gecacht. Validierung billig: dic==siz plus Praefix-Dekompression."""
import struct, lzma, pickle, os, sys
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

def scan(path, cache):
    if os.path.exists(cache):
        return pickle.load(open(cache,'rb'))
    d=open(path,'rb').read(); n=len(d)
    anc=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=u64(d,p+5)
            if dic==siz and 0<siz<=64_000_000:
                try:
                    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                    r=dec.decompress(d[p:p+4096], max_length=64)
                    anc.append((p,siz)); p+=13; continue
                except Exception: pass
        p+=1
    out=[]
    for i,(p,siz) in enumerate(anc):
        end = anc[i+1][0] if i+1<len(anc) else n
        out.append((p, end-p, siz))
    pickle.dump(out, open(cache,'wb'))
    return out

if __name__=='__main__':
    path=sys.argv[1] if len(sys.argv)>1 else \
      '../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
    cache=sys.argv[2] if len(sys.argv)>2 else 'gw_anchors.pkl'
    a=scan(path,cache)
    n=os.path.getsize(path)
    print(f"{os.path.basename(path)}: {n} B, {len(a)} Anker")
    print(f"erster Block @0x{a[0][0]:x} ({a[0][0]}), davor Platz fuer "
          f"{a[0][0]//32} Records a 32 B")
    print(f"letzter Block @0x{a[-1][0]:x}, endet bei {a[-1][0]+a[-1][1]} (Datei {n})")
    tot=sum(x[2] for x in a); cmp_=sum(x[1] for x in a)
    print(f"komprimiert {cmp_} B ({cmp_*100//n} % der Datei), entpackt {tot} B")
    print("\nerste 6 Anker:")
    for p,c,s in a[:6]: print(f"   @0x{p:08x}  komp {c:8d}  entpackt {s:8d}")
