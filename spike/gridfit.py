#!/usr/bin/env python3
"""WEGWERF: Kachelraster ausmessen und Level aus der Ausdehnung bestimmen."""
import sys, struct, collections
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

REG={ # west,east,south,north
 'Malta':(14.18,14.58,35.79,36.08),
 'Iceland':(-24.55,-13.49,63.39,66.57),
 'Albania':(19.26,21.06,39.62,42.67),
 'Moldova':(26.62,30.14,45.44,48.49),
 'Denmark':(8.07,15.19,54.56,57.75),
 'Portugal':(-9.50,-6.19,36.96,42.15),
}

def keys(path):
    d=open(path,'rb').read(); n=len(d); out=[]; o=0x102
    while o+20<=n:
        off,ln,k=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        out.append(k); o+=20
    return out[:-1]   # letzter Record ist Ueberlese-Artefakt

def deint(m, even_is_a=True):
    a=b=0; ai=bi=0
    for i in range(32):
        bit=(m>>i)&1
        if (i%2==0)==even_is_a: a|=bit<<ai; ai+=1
        else:                   b|=bit<<bi; bi+=1
    return a,b

for path,region in [('Malta_AdvancedRouting.psf','Malta'),
                    ('Iceland_AdvancedRouting.psf','Iceland'),
                    ('Albania_AdvancedRouting.psf','Albania'),
                    ('Moldova_AdvancedRouting.psf','Moldova'),
                    ('Denmark_AdvancedRouting.psf','Denmark'),
                    ('Portugal_AdvancedRouting.psf','Portugal')]:
    ks=keys(path)
    w,e,s,nn = REG[region]
    print(f"### {region}  ({len(ks)} Keys)  lon[{w},{e}] lat[{s},{nn}]  "
          f"Ausdehnung {e-w:.2f}deg x {nn-s:.2f}deg")
    grp=collections.defaultdict(list)
    for k in ks: grp[k>>21].append(k & 0x1FFFFF)
    for lay in sorted(grp):
        nrs=sorted(set(grp[lay]))
        print(f"  Gruppe {lay}: {len(nrs):4d} Kacheln, nr 0x{min(nrs):06x}..0x{max(nrs):06x}")
        for eia in (True,False):
            pts=[deint(x,eia) for x in nrs]
            A=[p[0] for p in pts]; B=[p[1] for p in pts]
            da=max(A)-min(A)+1; db=max(B)-min(B)+1
            lbl='even->a' if eia else 'odd->a'
            print(f"      {lbl}: a[{min(A)}..{max(A)}] ({da} breit)  "
                  f"b[{min(B)}..{max(B)}] ({db} breit)  Dichte {len(pts)}/{da*db}"
                  f" = {len(pts)/(da*db)*100:.0f}%")
            if da>1 and db>1:
                # implizierte Kachelgroesse und Level
                sa=(e-w)/da; sb=(nn-s)/db
                import math
                la=math.log2(360/sa)-1 if sa>0 else 0
                lb=math.log2(180/sb)    if sb>0 else 0
                print(f"          -> Kachel {sa:.4f}deg x {sb:.4f}deg  "
                      f"=> Level_lon={la:.2f}  Level_lat={lb:.2f}")
    print()
