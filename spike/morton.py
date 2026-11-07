#!/usr/bin/env python3
"""WEGWERF: Tile-ID-Kodierung per Doppel-Bounding-Box (Malta + Island) loesen."""
import sys, struct, itertools

def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def tile_ids(path, start, stride, idxfield=2):
    d=open(path,'rb').read(); n=len(d); ids=[]; o=start
    while o+12<=n:
        off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        ids.append(tid); o+=stride
    return ids

def deinterleave(m, nbits, first_is_a=True):
    a=b=0
    for i in range(nbits):
        bit=(m>>i)&1
        if (i%2==0)==first_is_a: a |= bit << (i//2)
        else:                    b |= bit << (i//2)
    return a,b

BBOX={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.6,-13.4,63.3,66.6)}

DATA={
 'Malta':   tile_ids('Malta_AdvancedRouting.psf',   0x102, 20),
 'Iceland': tile_ids('Iceland_AdvancedRouting.psf', 0x102, 20),
}
for k,v in DATA.items():
    print(f"{k}: {len(v)} tileIds, {hex(min(v))}..{hex(max(v))}")
    print(f"   erste: {[hex(x) for x in v[:8]]}")
print()

results=[]
for level in range(1,21):
    for strip_top in (True, False):      # oberstes gesetztes Bit als Level-Marker entfernen?
        for first_is_a in (True, False): # Bit-Reihenfolge
            for swap in (False, True):   # (a,b) = (x,y) oder (y,x)
                score={}
                for region,ids in DATA.items():
                    lo_x,hi_x,lo_y,hi_y = BBOX[region]
                    inb=0
                    for t in ids:
                        m=t
                        if strip_top and m:
                            m = m & ((1 << (m.bit_length()-1)) - 1)
                        a,b = deinterleave(m, 2*level, first_is_a)
                        x,y = (b,a) if swap else (a,b)
                        if x >= (1<<level) or y >= (1<<level): continue
                        lon = x/(1<<level)*360-180
                        lat = y/(1<<level)*180-90
                        if lo_x<=lon<=hi_x and lo_y<=lat<=hi_y: inb+=1
                    score[region]=inb/max(1,len(ids))
                both=min(score.values())
                if both>0:
                    results.append((both, sum(score.values()), level, strip_top,
                                    first_is_a, swap, dict(score)))

results.sort(reverse=True)
print("=== Kandidaten, die BEIDE Regionen treffen ===")
if not results:
    print("  KEINER. -> Tile-ID ist kein einfacher Morton-Code ueber (lon,lat)-Raster.")
else:
    for r in results[:10]:
        both,s,level,st,fa,sw,sc = r
        print(f"  level={level:2d} strip_top={st!s:5s} order={'even=x' if fa else 'even=y'} "
              f"swap={sw!s:5s}  Malta {sc['Malta']*100:5.1f}%  Iceland {sc['Iceland']*100:5.1f}%")
