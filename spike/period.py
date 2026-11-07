#!/usr/bin/env python3
"""WEGWERF: Periodizitaet der Wiederholung bestimmen."""
import sys, collections

data=open(sys.argv[1],'rb').read()
HDR=int(sys.argv[2],0)

def alloff(needle, buf=data):
    out=[]; s=0
    while True:
        i=buf.find(needle, s)
        if i<0: break
        out.append(i); s=i+1
    return out

for needle in [bytes.fromhex('1e45a0fb4897e7e0'),
               bytes.fromhex('47a049f59c422f65'),
               bytes.fromhex('91 60 c5 20 f6 e3 47 40'.replace(' ','')),
               bytes.fromhex('5de7060000e70600')]:
    offs=alloff(needle)
    print(f"{needle.hex(' ')}  -> {len(offs)} Treffer")
    print(f"   Offsets: {[hex(o) for o in offs[:12]]}")
    if len(offs)>1:
        d=[offs[i+1]-offs[i] for i in range(len(offs)-1)]
        print(f"   Deltas:  {d[:12]}")
        print(f"   Delta-Histogramm: {collections.Counter(d).most_common(5)}")
    print()

# Wie lang ist der wiederholte Bereich? Vergleiche ab den ersten zwei Offsets
o = alloff(bytes.fromhex('1e45a0fb4897e7e0'))
if len(o)>=2:
    a,b=o[0],o[1]; per=b-a
    # nach vorne/hinten ausdehnen
    fwd=0
    while a+fwd<len(data) and b+fwd<len(data) and data[a+fwd]==data[b+fwd]: fwd+=1
    bwd=0
    while a-bwd-1>=0 and b-bwd-1>=0 and data[a-bwd-1]==data[b-bwd-1]: bwd+=1
    print(f"Periode zwischen Treffer 1 und 2: {per} Bytes (0x{per:x})")
    print(f"Identischer Bereich: {bwd} Bytes davor + {fwd} danach = {bwd+fwd} Bytes")
    print(f"   Bereich A: 0x{a-bwd:x} .. 0x{a+fwd:x}")
    print(f"   Bereich B: 0x{b-bwd:x} .. 0x{b+fwd:x}")
    print(f"   Bruchstelle A vorher: {data[max(0,a-bwd-16):a-bwd].hex(' ')}")
    print(f"   Bruchstelle A danach: {data[a+fwd:a+fwd+16].hex(' ')}")
    print(f"   Bruchstelle B vorher: {data[max(0,b-bwd-16):b-bwd].hex(' ')}")
    print(f"   Bruchstelle B danach: {data[b+fwd:b+fwd+16].hex(' ')}")
