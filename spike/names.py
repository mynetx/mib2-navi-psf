#!/usr/bin/env python3
"""WEGWERF: Alle LZMA-Bloecke entpacken und Namensstrings extrahieren."""
import sys, struct, lzma, re, collections

def decompress_all(path):
    d=open(path,'rb').read(); n=len(d); out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=struct.unpack_from('<I',d,p+1)[0]; siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz:
                        out.append(r[:siz]); p+=13; continue
                except Exception: pass
        p+=1
    return d, out

for path in sys.argv[1:]:
    raw, blobs = decompress_all(path)
    tot=sum(len(b) for b in blobs)
    print(f"### {path.split('/')[-1]}")
    print(f"    {len(raw)} B Datei -> {len(blobs)} Bloecke -> {tot} B entpackt "
          f"(Faktor {tot/len(raw):.2f})")
    big=b'\x00'.join(blobs)
    # Latin-1-faehige Namen: Buchstabe am Anfang, mind. 4 Zeichen
    pat=re.compile(rb'[A-Z\xc0-\xde][A-Za-z\xc0-\xff\'\-\. ]{3,60}')
    names=[m.group() for m in pat.finditer(big)]
    uniq=collections.Counter(n.strip() for n in names if len(n.strip())>=4)
    print(f"    Namenskandidaten: {len(names)} gesamt, {len(uniq)} verschieden")
    print(f"    Haeufigste 12:")
    for nm,c in uniq.most_common(12):
        try: s=nm.decode('latin-1')
        except Exception: s=repr(nm)
        print(f"       {c:5d}x  {s}")
    # Stichprobe seltener (echte Strassennamen sind meist selten)
    rare=[nm for nm,c in uniq.items() if c<=2 and 5<=len(nm)<=40]
    print(f"    Stichprobe aus {len(rare)} seltenen Namen:")
    for nm in rare[:18]:
        try: s=nm.decode('latin-1')
        except Exception: s=repr(nm)
        print(f"       {s}")
    print()
