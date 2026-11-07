#!/usr/bin/env python3
"""WEGWERF: Position des Level-Bits im packed Tile ID brute-forcen.
Randbedingung: ALLE Regionen muessen gleichzeitig plausibel werden."""
import sys, struct, collections
sys.path.insert(0,'../spike')
import nds

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def keys(path):
    d=open(path,'rb').read(); n=len(d); out=[]; o=0x102
    while o+20<=n:
        off,ln,k=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        out.append(k); o+=20
    return out[:-1]

REG={
 'Malta':(14.18,14.58,35.79,36.08),
 'Iceland':(-24.55,-13.49,63.39,66.57),
 'Albania':(19.26,21.06,39.62,42.67),
 'Moldova':(26.62,30.14,45.44,48.49),
 'Denmark':(8.07,15.19,54.56,57.75),
 'Portugal':(-9.50,-6.19,36.96,42.15),
}
FILES={r:f'{r}_AdvancedRouting.psf' for r in REG}
DATA={r:keys(f) for r,f in FILES.items()}
for r,k in DATA.items(): print(f"{r}: {len(k)} Keys, 0x{min(k):x}..0x{max(k):x}")
print()

def bbox(level, nr):
    if level==0:
        return (0.0,180.0,-90.0,90.0) if nr==0 else (-180.0,0.0,-90.0,90.0)
    m = nr << (32 + (15-level)*2)
    slon,slat = nds.morton_to_lonlat(m)
    north = slat + nds.LAT_RANGE//(1<<level) + (1 if slat<0 else 0)
    east  = slon + nds.LON_RANGE//(1<<(level+1)) + (1 if slon<0 else 0)
    w,s = nds.to_wgs84(slon,slat)
    e,n = nds.to_wgs84(min(east,nds.MAX_LON), min(north,nds.MAX_LAT))
    return w,e,s,n

print("k = Bitoffset des Level-Bits (level = hoechstes_gesetztes_Bit - k)")
print(f"{'k':>3} " + " ".join(f"{r[:7]:>8}" for r in REG) + "   min%")
best=[]
for k in range(0,25):
    frac={}
    for r,(rw,re_,rs,rn) in REG.items():
        ok=0; valid=0
        for v in DATA[r]:
            if v<=0: continue
            hb=v.bit_length()-1
            lvl=hb-k
            if lvl<0 or lvl>15: continue
            nr=v ^ (1<<hb)
            if nr > (1<<(2*lvl+1))-1: continue
            valid+=1
            w,e,s,n = bbox(lvl,nr)
            if e>=rw and w<=re_ and n>=rs and s<=rn: ok+=1
        frac[r]=ok/max(1,len(DATA[r]))
    row=" ".join(f"{frac[r]*100:7.1f}%" for r in REG)
    mn=min(frac.values())
    print(f"{k:>3} {row}   {mn*100:5.1f}%")
    best.append((mn,k,frac))
best.sort(reverse=True)
print(f"\nBester k: {best[0][1]}  (schlechteste Region {best[0][0]*100:.1f}%)")
