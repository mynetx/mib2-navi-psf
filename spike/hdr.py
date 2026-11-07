#!/usr/bin/env python3
"""WEGWERF: Header-Struct + Indextabelle parsen; Blockpraefix cross-file vergleichen."""
import sys, struct, collections

def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def parse(path, verbose=True):
    d=open(path,'rb').read(); n=len(d)
    if verbose:
        print(f"### {path}   size={n}")
        print("  Kopf-Felder (uint32 LE ab Offset 2):")
        for i in range(2, 98, 4):
            v=u32(d,i)
            note=''
            if 0 < v < n: note=f'  <- gueltiger Datei-Offset ({v*100//n}%)'
            print(f"    +{i:3d}  {v:12d}  0x{v:08x}{note}")

    # Indextabelle suchen: erster 22-Byte-Record, dessen offset im Bereich liegt
    # und dessen Folgerecord konsistent ist
    best=None
    for start in range(0x80, 0x180):
        ok=0
        for k in range(6):
            o=start+k*22
            if o+22>len(d): break
            off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
            if 0<off<n and 0<ln<1_000_000 and off+ln<=n: ok+=1
            else: break
        if ok==6: best=start; break
    if best is None:
        print("  !! Indextabelle nicht gefunden"); return None
    if verbose: print(f"\n  Indextabelle beginnt bei 0x{best:x}")

    recs=[]
    o=best
    while o+22<=n:
        off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<1_000_000 and off+ln<=n): break
        recs.append((off,ln,tid)); o+=22
    if verbose:
        print(f"  Records: {len(recs)}")
        print(f"  {'offset':>10} {'len':>8} {'tileId':>12}   reserved-Bytes")
        for off,ln,tid in recs[:6]:
            print(f"  0x{off:08x} {ln:8d} 0x{tid:08x}")
        print(f"  ... IDs {hex(recs[0][2])} .. {hex(recs[-1][2])}")
        tot=sum(r[1] for r in recs)
        print(f"  Summe Blocklaengen: {tot} ({tot*100/n:.1f} % der Datei)")
        print(f"  kleinster Block {min(r[1] for r in recs)}, groesster {max(r[1] for r in recs)}")
    return d, recs

files=sys.argv[1:]
prefixes={}
for p in files:
    r=parse(p, verbose=(p==files[0]))
    if not r: continue
    d,recs=r
    # gemeinsames Praefix ueber alle Bloecke dieser Datei
    blocks=[d[off:off+ln] for off,ln,_ in recs if ln>64]
    if not blocks: continue
    L=0
    while L<min(len(b) for b in blocks) and len(set(b[L:L+1] for b in blocks))==1: L+=1
    prefixes[p]=blocks[0][:L]
    print(f"\n>>> {p.split('/')[-1]}: {len(recs)} Bloecke, gemeinsames Praefix {L} Bytes")
    if L: print(f"    {blocks[0][:32].hex(' ')}")

print("\n=== CROSS-FILE VERGLEICH DER PRAEFIXE ===")
ks=list(prefixes)
for i,a in enumerate(ks):
    for b in ks[i+1:]:
        pa,pb=prefixes[a],prefixes[b]
        common=0
        while common<min(len(pa),len(pb)) and pa[common]==pb[common]: common+=1
        print(f"  {a.split('/')[-1]:42s} vs {b.split('/')[-1]:42s}  gemeinsam: {common} B")
