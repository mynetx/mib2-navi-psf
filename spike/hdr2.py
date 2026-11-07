#!/usr/bin/env python3
"""WEGWERF: Indextabelle per Brute-Force finden (start, stride), dann Bloecke bewerten."""
import sys, struct

def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def find_table(d):
    n=len(d); best=None
    for stride in range(12, 41, 2):
        for start in range(0x40, 0x220):
            recs=[]; o=start
            while o+12<=n:
                off,ln,tid=u32(d,o),u32(d,o+4),u32(d,o+8)
                if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
                recs.append((off,ln,tid)); o+=stride
            if len(recs)<8: continue
            # Guete: Bloecke ueberlappen nicht, IDs streng fortlaufend
            srt=sorted(recs)
            nonoverlap=all(srt[i][0]+srt[i][1]<=srt[i+1][0] for i in range(len(srt)-1))
            ids=[r[2] for r in recs]
            seq=sum(1 for i in range(len(ids)-1) if ids[i+1]==ids[i]+1)/max(1,len(ids)-1)
            cov=sum(r[1] for r in recs)/n
            score=(len(recs), nonoverlap, seq, cov)
            if nonoverlap and seq>0.5 and (best is None or len(recs)>best[0]):
                best=(len(recs), start, stride, recs, seq, cov)
    return best

for path in sys.argv[1:]:
    d=open(path,'rb').read(); n=len(d)
    b=find_table(d)
    name=path.split('/')[-1]
    if not b:
        print(f"{name:44s} size={n:>10}  KEINE Tabelle gefunden"); continue
    cnt,start,stride,recs,seq,cov = b
    srt=sorted(recs)
    gaps=[srt[i+1][0]-(srt[i][0]+srt[i][1]) for i in range(len(srt)-1)]
    print(f"{name:44s} size={n:>10}")
    print(f"   Tabelle @0x{start:x}, stride={stride}, {cnt} Bloecke, "
          f"ID-Folge {seq*100:.0f}%, Abdeckung {cov*100:.1f}%")
    print(f"   Datenbereich 0x{srt[0][0]:x}..0x{srt[-1][0]+srt[-1][1]:x}  "
          f"Luecken: {sum(1 for g in gaps if g)}  (Summe {sum(gaps)} B)")
    print(f"   tileId {hex(recs[0][2])}..{hex(recs[-1][2])}   "
          f"Blocklaenge {min(r[1] for r in recs)}..{max(r[1] for r in recs)}")
    blocks=[d[o:o+l] for o,l,_ in recs if l>64]
    if blocks:
        L=0
        while L<min(len(x) for x in blocks) and len(set(x[L:L+1] for x in blocks))==1: L+=1
        print(f"   gemeinsames Blockpraefix: {L} B   {blocks[0][:24].hex(' ')}")
    print()
