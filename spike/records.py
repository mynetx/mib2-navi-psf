#!/usr/bin/env python3
"""WEGWERF: Recordstruktur des Payload + Header-Dump."""
import sys, collections, struct

data=open(sys.argv[1],'rb').read()
HDR=int(sys.argv[2],0)
MARK=bytes.fromhex('5de7060000e70600')

offs=[]; s=0
while True:
    i=data.find(MARK,s)
    if i<0: break
    offs.append(i); s=i+1
print(f"Marker-Treffer: {len(offs)}, erster 0x{offs[0]:x}, letzter 0x{offs[-1]:x}")
print(f"Payload 0x{HDR:x}..0x{len(data):x}")

# Sind die 473 Bytes ab jedem Marker identisch?
ref=data[offs[0]:offs[0]+473]
same=sum(1 for o in offs if data[o:o+473]==ref)
print(f"Bytes ab Marker identisch (473 B): {same}/{len(offs)}")
# maximale gemeinsame Laenge ueber ALLE Treffer
L=0
while True:
    b=set(data[o+L:o+L+1] for o in offs)
    if len(b)!=1 or L>4000: break
    L+=1
print(f"Maximale ueber ALLE {len(offs)} Treffer identische Laenge ab Marker: {L} Bytes")
# rueckwaerts
B=0
while True:
    b=set(data[o-B-1:o-B] for o in offs if o-B-1>=0)
    if len(b)!=1 or B>4000: break
    B+=1
print(f"...und rueckwaerts: {B} Bytes  => konstanter Block {B+L} Bytes\n")

print("=== KONSTANTER BLOCK (erste 128 B) ===")
print(data[offs[0]-B:offs[0]-B+128].hex(' '))
print()

# Recordgrenzen: Abstaende
d=[offs[i+1]-offs[i] for i in range(len(offs)-1)]
print(f"Abstaende: min={min(d)} max={max(d)} mean={sum(d)/len(d):.1f}")
print(f"Variabler Anteil pro Record: {min(d)-(B+L)} .. {max(d)-(B+L)} Bytes\n")

print("=== HEADER-DUMP (0x000..0x{:x}) ===".format(HDR))
for off in range(0, HDR, 16):
    row=data[off:off+16]
    if row == b'\x00'*16:
        continue
    print(f"{off:04x}  {row.hex(' ')}  {''.join(chr(c) if 32<=c<127 else '.' for c in row)}")
