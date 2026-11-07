#!/usr/bin/env python3
"""WEGWERF: _Basic-Bloecke - gilt dieselbe [N][Tabelle][Records]-Struktur?"""
import struct, lzma, collections, re
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]

path='Malta_Basic.psf'
d=open(path,'rb').read(); n=len(d)

# Bloecke per 0x5D-Anker (Index-Layout von _Basic noch offen)
blocks=[]; p=0
while True:
    p=d.find(b'\x5d',p)
    if p<0: break
    if p+13<=n:
        dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
        if dic==siz and 0<siz<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                    d[p:p+min(n-p,siz*4+4096)])
                if len(r)>=siz: blocks.append((p,r[:siz])); p+=13; continue
            except Exception: pass
    p+=1
print(f"{path}: {len(blocks)} Bloecke\n")

# Struktur-Hypothese pruefen: byte0 == N, erster Offset == 3+2N
ok=0; checked=0; sizes=collections.Counter()
for off,b in blocks:
    if len(b)<8: continue
    checked+=1
    N=b[0]
    if N==0: continue
    exp=3+2*N
    if exp+2>len(b): continue
    if u16(b,3)==exp:
        ok+=1
        tab=[u16(b,3+2*i) for i in range(N)]
        gaps={tab[i+1]-tab[i] for i in range(N-1)} if N>1 else set()
        if len(gaps)==1: sizes[gaps.pop()]+=1
        else: sizes['variabel']+=1
print(f"Hypothese 'byte0==N und erster Offset==3+2N': {ok}/{checked} Bloecke")
print(f"Recordgroessen-Verteilung: {sizes.most_common(10)}\n")

# Ein Block mit Strings: Struktur genauer ansehen
cand=[(o,b) for o,b in blocks if b'Triq' in b]
print(f"Bloecke mit 'Triq': {len(cand)}")
off,b = max(cand, key=lambda x: len(x[1]))
print(f"groesster: @0x{off:x}, {len(b)} B entpackt, byte0={b[0]} "
      f"erwarteter erster Offset={3+2*b[0]}, tatsaechlich=0x{u16(b,3):x}")
print(f"Kopf: {b[:16].hex(' ')}")
print("\nerste 160 Bytes:")
for r in range(0,160,16):
    row=b[r:r+16]
    print(f"  {r:04x}  {row.hex(' ')}  "
          f"{''.join(chr(c) if 32<=c<127 else '.' for c in row)}")

# Wo liegen die Strings?
pos=[m.start() for m in re.finditer(rb'Triq ', b)]
print(f"\n'Triq '-Positionen: {len(pos)}, erste {pos[:8]}, letzte {pos[-3:]}")
print(f"Blockgroesse {len(b)} -> Strings liegen bei "
      f"{pos[0]*100//len(b)}%..{pos[-1]*100//len(b)}% der Blocklaenge")
print(f"\nUmfeld des ersten Strings (32 B davor):")
s=pos[0]
print(f"  vor:  {b[max(0,s-32):s].hex(' ')}")
print(f"  text: {b[s:s+40]}")
print(f"  nach: {b[s+40:s+72].hex(' ')}")
