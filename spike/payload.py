#!/usr/bin/env python3
"""WEGWERF: Payload getrennt vom Header beurteilen. Verschluesselt oder strukturiert?"""
import sys, math, collections

def entropy(b):
    if not b: return 0.0
    c = collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def chi2_uniform(b):
    """Chi-Quadrat gegen Gleichverteilung. Verschluesselt/ideal komprimiert -> ~255."""
    n=len(b); exp=n/256
    c=collections.Counter(b)
    return sum((c.get(i,0)-exp)**2/exp for i in range(256))

def report(name, b):
    n=len(b)
    if n < 1024: return
    h=collections.Counter(b)
    print(f"{name}: {n} Bytes")
    print(f"   Entropie        {entropy(b):.4f} Bit/Byte   (Ideal fuer diese Groesse: "
          f"{min(8.0, math.log2(min(n,256))):.4f})")
    print(f"   Chi^2           {chi2_uniform(b):10.1f}   (Zufall/verschluesselt erwartet ~255, "
          f"kritisch >330)")
    print(f"   Nullbytes       {h[0]*100/n:6.3f} %      (Zufall: 0.391 %)")
    print(f"   0xFF-Bytes      {h[255]*100/n:6.3f} %      (Zufall: 0.391 %)")
    print(f"   haeufigstes Byte 0x{h.most_common(1)[0][0]:02x} bei {h.most_common(1)[0][1]*100/n:.3f} %")
    # Wiederholte 8-Byte-Bloecke: bei Verschluesselung praktisch null
    seen=collections.Counter(b[i:i+8] for i in range(0, n-8, 8))
    dup=sum(v-1 for v in seen.values() if v>1)
    print(f"   doppelte 8-Byte-Bloecke: {dup} von {n//8}  ({dup*100/max(1,n//8):.3f} %)")
    print()

path=sys.argv[1]; hdr_end=int(sys.argv[2],0)
data=open(path,'rb').read()
print(f"### {path}  (Header-Ende angenommen: 0x{hdr_end:x})\n")
report("HEADER ", data[:hdr_end])
report("PAYLOAD", data[hdr_end:])

# Feine Suche nach Blockgrenzen im Payload: Entropie-Einbrueche
print("Entropie-Einbrueche im Payload (1KB-Fenster, Schwelle < 7.6):")
BS=1024; found=0
for off in range(hdr_end, len(data)-BS, BS):
    e=entropy(data[off:off+BS])
    if e < 7.6:
        print(f"   0x{off:06x}  {e:.3f}"); found+=1
    if found>30: print("   ..."); break
if not found: print("   keine — Payload ist durchgehend maximal-entrop")
