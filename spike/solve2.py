#!/usr/bin/env python3
"""WEGWERF: Vollen _Basic-Index lesen, dann Koordinateneinheit ueber beide Achsen loesen."""
import struct, lzma, itertools
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def anchors(path):
    d=open(path,'rb').read(); n=len(d); out=set(); p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz: out.add(p); p+=13; continue
                except Exception: pass
        p+=1
    return d, out

REG={'Malta':(14.18,14.58,35.79,36.08),'Albania':(19.26,21.06,39.62,42.67),
     'Iceland':(-24.55,-13.49,63.39,66.57),'Denmark':(8.07,15.19,54.56,57.75)}

for region in ('Malta','Albania','Denmark'):
    path=f'{region}_Basic.psf'
    d,A = anchors(path)
    STRIDE=32
    recs=[]
    o=0x32e
    while o+STRIDE<=len(d):
        if u32(d,o+8) in A: recs.append(d[o:o+STRIDE])
        o+=STRIDE
    w,e,s,nn = REG[region]
    print(f"### {region}: {len(A)} Anker, {len(recs)} Indexrecords (mit Luecken)")
    if len(recs)<20: print("   zu wenige\n"); continue
    fields={}
    for k in range(STRIDE//4):
        vs=[u32(r,4*k) for r in recs]
        fields[4*k]=vs
        print(f"   +{4*k:2d}: {len(set(vs)):5d} versch. {min(vs):12d}..{max(vs):12d} "
              f"Spanne {max(vs)-min(vs):12d}")
    # Paare suchen, deren Spannweiten dieselbe Einheit ergeben
    print("   Feldpaare mit konsistenter Einheit (Abweichung < 8 %):")
    hits=[]
    for a,b in itertools.permutations(fields,2):
        ra=max(fields[a])-min(fields[a]); rb=max(fields[b])-min(fields[b])
        if ra<50 or rb<50: continue
        ua=(e-w)/ra; ub=(nn-s)/rb
        dev=abs(ua/ub-1)
        if dev<0.08:
            hits.append((dev,a,b,ua,ub))
    hits.sort()
    for dev,a,b,ua,ub in hits[:6]:
        u=(ua+ub)/2
        lon0=min(fields[a])*u; lat0=min(fields[b])*u
        print(f"      LON=+{a:2d} LAT=+{b:2d}  Einheit {u:.3e} deg/Schritt "
              f"(Abw. {dev*100:.1f}%)  1/u={1/u:.1f}")
        print(f"          ohne Offset: lon {min(fields[a])*u:8.3f}..{max(fields[a])*u:8.3f}  "
              f"lat {min(fields[b])*u:8.3f}..{max(fields[b])*u:8.3f}")
    if not hits: print("      keine")
    print()
