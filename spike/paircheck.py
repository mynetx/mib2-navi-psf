#!/usr/bin/env python3
"""WEGWERF: NDS-Koordinatenpaare suchen. Paarbedingung schliesst Einzelzufaelle aus.
Ein echtes Koordinatenfeld trifft ~100%, Rauschen ~0%."""
import sys, struct, collections
U = 360.0/2**32   # NDS-Einheit: Grad pro Schritt

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def i32(b,o): return struct.unpack_from('<i',b,o)[0]

EUROPE=(-32.0, 48.0, 33.0, 72.0)

def idx_records(path, start, stride, nfields):
    d=open(path,'rb').read(); n=len(d); out=[]; o=start
    while o+stride<=n:
        off,ln=u32(d,o),u32(d,o+4)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        out.append(tuple(i32(d,o+4*k) for k in range(nfields))); o+=stride
    return d, out[:-1]

print("=== A) Indexfelder stride-24-Dateien als Koordinatenpaare ===")
for path in ('MountainPolygons.psf','WorldCartographicLayer_Basic.psf'):
    d,rs = idx_records(path, 0x10e-8, 24, 6)
    print(f"\n{path}: {len(rs)} Records, 6 Felder")
    w,e,s,n = EUROPE
    for a in range(6):
        for b in range(6):
            if a==b: continue
            hit=0
            for r in rs:
                lon=r[a]*U; lat=r[b]*U
                if w<=lon<=e and s<=lat<=n: hit+=1
            if hit*100/max(1,len(rs)) > 40:
                print(f"   Feld{a} als LON, Feld{b} als LAT: "
                      f"{hit}/{len(rs)} = {hit*100/len(rs):.1f}% in Europa")
                for r in rs[:5]:
                    print(f"        lon={r[a]*U:9.4f}  lat={r[b]*U:9.4f}")
    # Einzelfeld-Statistik zur Orientierung
    print("   Feldwertebereiche in Grad (Einheit 360/2^32):")
    for k in range(6):
        vs=[r[k]*U for r in rs]
        print(f"      Feld{k}: {min(vs):10.4f} .. {max(vs):10.4f}")

print("\n\n=== B) Dateikopf von AdvancedRouting als Koordinatenpaare ===")
REG={'Malta':(14.18,14.58,35.79,36.08),'Iceland':(-24.55,-13.49,63.39,66.57),
     'Albania':(19.26,21.06,39.62,42.67),'Portugal':(-9.50,-6.19,36.96,42.15),
     'Denmark':(8.07,15.19,54.56,57.75)}
for region,(rw,re_,rs_,rn) in REG.items():
    d=open(f'{region}_AdvancedRouting.psf','rb').read()
    print(f"\n{region}: erwartet lon[{rw},{re_}] lat[{rs_},{rn}]")
    found=[]
    for o in range(0, 0x102-8):
        for oa,ob in ((o,o+4),):
            lon=i32(d,oa)*U; lat=i32(d,ob)*U
            if rw-0.6<=lon<=re_+0.6 and rs_-0.6<=lat<=rn+0.6:
                found.append((oa,ob,lon,lat))
            lon2=i32(d,ob)*U; lat2=i32(d,oa)*U
            if rw-0.6<=lon2<=re_+0.6 and rs_-0.6<=lat2<=rn+0.6:
                found.append((ob,oa,lon2,lat2))
    if found:
        for oa,ob,lon,lat in found:
            print(f"   PAAR @+{oa}/+{ob}:  lon={lon:9.4f}  lat={lat:9.4f}")
    else:
        print("   kein Paar im Kopf")
