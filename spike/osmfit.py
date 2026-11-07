#!/usr/bin/env python3
"""Koordinatenkodierung gegen OSM als Grundwahrheit fitten.

Ortsrecords in _Basic-Blöcken (Sektionsklasse 16):

    ff ff ff ff | u16 X | u16 Y | u16 ? | 00 01 03 | Name 00

X und Y sind relativ zur Kachelecke aus dem Blockkopf, isotrop, Maßstab je
Block. Gefittet gegen die echten Ortslagen aus OSM (osm/places.pkl, aus
Overpass, siehe osm/qp.overpass).

    python3 osmfit.py                 # alle bekannten Blöcke
    python3 osmfit.py 0x3392334       # einer
"""
import lzma, struct, pickle, math, sys, os
PSF=os.environ.get('PSF','../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf')
SEP=b'\xff\xff\xff\xff'; TAIL=b'\x00\x01\x03'
BLOCKS=[('L11 Band 1,2M  West (z10-11)',0x3392334),('L11 Band 1,2M  Ost',0x346c45e),
        ('L11 Band 280k  West (z1-9)',0x36ce94a),('L10 Band 2,5M  (z12)',0x2f4009f)]

def records(raw):
    """(X, Y, f3, Name) jedes Ortsrecords im entpackten Block."""
    out=[]; i=-1
    while True:
        i=raw.find(SEP,i+1)
        if i<0: break
        o=i+4
        if o+9>len(raw): break
        f1,f2,f3=struct.unpack_from('<3H',raw,o)
        if raw[o+6:o+9]!=TAIL: continue
        e=raw.find(b'\0',o+9)
        if e<0 or e-(o+9)>40: continue
        out.append((f1,f2,f3,raw[o+9:e].decode('utf-8','replace'),o))
    return out

def analyse(d,P,places):
    raw=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[P:])
    X0,Y0,X1,Y1=struct.unpack_from('<4i',raw,0)
    pts=[(f1,f2,places[n][0]-X0,places[n][1]-Y0,n)
         for f1,f2,f3,n,_ in records(raw) if n in places]
    if len(pts)<6: return None
    num=sum(f1*dx+f2*dy for f1,f2,dx,dy,_ in pts)
    den=sum(f1*f1+f2*f2 for f1,f2,dx,dy,_ in pts)
    s=num/den
    e=[dx-s*f1 for f1,f2,dx,dy,_ in pts]+[dy-s*f2 for f1,f2,dx,dy,_ in pts]
    return dict(n=len(pts), W=X1-X0, H=Y1-Y0, scale=s,
                rms=math.sqrt(sum(v*v for v in e)/len(e)),
                units=(X1-X0)/s, recs=len(records(raw)))

if __name__=='__main__':
    d=open(PSF,'rb').read()
    places=pickle.load(open(os.path.join(os.path.dirname(__file__),'osm','places.pkl'),'rb'))
    sel=[(n,P) for n,P in BLOCKS if len(sys.argv)<2 or P==int(sys.argv[1],0)]
    for name,P in sel:
        r=analyse(d,P,places)
        if not r: print(f"{name}: zu wenige Treffer"); continue
        print(f"{name}  @0x{P:07x}")
        print(f"   {r['recs']} Ortsrecords, {r['n']} mit OSM-Gegenstueck")
        print(f"   Kachel {r['W']}x{r['H']} m   Massstab {r['scale']:.4f} m/Einheit"
              f"   RMS {r['rms']:.0f} m   Breite/Massstab {r['units']:.1f}")
