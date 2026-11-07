#!/usr/bin/env python3
"""WEGWERF: Header nach NDS packed Tile IDs durchsuchen, geprueft per Bounding Box."""
import sys, struct, collections
sys.path.insert(0,'../spike')
from nds import bbox_of_packed

TARGET={
 'Malta':   (14.18,14.58,35.79,36.08),
 'Iceland': (-24.6,-13.4,63.3,66.6),
 'Albania': (19.26,21.06,39.62,42.67),
 'Moldova': (26.6,30.2,45.4,48.5),
}

def scan(path, region, span=0x20000):
    d=open(path,'rb').read()
    tx0,tx1,ty0,ty1 = TARGET[region]
    hits=collections.defaultdict(list)
    lim=min(len(d), span)
    for o in range(0, lim-4):
        for endian,fmt in (('LE','<I'),('BE','>I')):
            pid=struct.unpack_from(fmt,d,o)[0]
            r=bbox_of_packed(pid)
            if r is None: continue
            (w,e,s,n),(lvl,nr)=r
            # Kachel muss das Zielgebiet ueberlappen
            if e>=tx0 and w<=tx1 and n>=ty0 and s<=ty1:
                hits[(endian,lvl)].append((o,pid,w,e,s,n))
    print(f"### {path.split('/')[-1]}  Ziel: {region} lon[{tx0},{tx1}] lat[{ty0},{ty1}]")
    if not hits:
        print("   keine Treffer\n"); return
    for (endian,lvl),v in sorted(hits.items(), key=lambda kv:-len(kv[1])):
        offs=[x[0] for x in v]
        # Rasterabstand der Trefferoffsets
        dd=collections.Counter(offs[i+1]-offs[i] for i in range(len(offs)-1))
        print(f"   {endian} level={lvl:2d}: {len(v):5d} Treffer, "
              f"Offsets 0x{min(offs):x}..0x{max(offs):x}, "
              f"haeufigster Abstand {dd.most_common(3)}")
        for o,pid,w,e,s,n in v[:3]:
            print(f"        @0x{o:05x} pid={pid:<12} lon[{w:9.4f},{e:9.4f}] "
                  f"lat[{s:8.4f},{n:8.4f}]")
    print()

for path,region in [('Malta_AdvancedRouting.psf','Malta'),
                    ('Iceland_AdvancedRouting.psf','Iceland'),
                    ('Albania_AdvancedRouting.psf','Albania'),
                    ('Moldova_GlobalPOIIndices.psf','Moldova')]:
    scan(path, region)
