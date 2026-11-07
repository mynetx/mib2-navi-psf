#!/usr/bin/env python3
"""Die nicht als Kachel erkannten Bloecke klassifizieren. Wo steckt das Ortsdetail?"""
import struct, lzma, math, collections, re, pickle
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)

def is_tile(b):
    if len(b)<16: return None
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): return None
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): return None
    L=round(math.log2(360.0/w))
    if not(4<=L<=16) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: return None
    return L

path='Malta_Basic.psf'   # klein, dieselbe Struktur
d=open(path,'rb').read(); n=len(d)
tiles=[]; others=[]; p=0
while True:
    p=d.find(b'\x5d',p)
    if p<0: break
    if p+13<=n:
        dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
        if dic==siz and 0<siz<=16_000_000:
            try:
                r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                    d[p:p+min(n-p,siz*4+4096)])
                if len(r)>=siz:
                    b=r[:siz]
                    L=is_tile(b)
                    (tiles if L else others).append((p,b,L))
                    p+=13; continue
            except Exception: pass
    p+=1
print(f"{path}: {len(tiles)} Kacheln, {len(others)} nicht erkannt\n")

# Klassifikation der nicht erkannten
print("Nicht erkannte Bloecke: Groessenverteilung")
sz=[len(b) for _,b,_ in others]
sz.sort()
print(f"  n={len(sz)}  min={sz[0]} p25={sz[len(sz)//4]} median={sz[len(sz)//2]} "
      f"p75={sz[3*len(sz)//4]} max={sz[-1]}")

print("\nErste 4 Bytes (Klassenbildung):")
c4=collections.Counter(bytes(b[:4]) for _,b,_ in others)
for k,v in c4.most_common(10):
    print(f"  {k.hex(' ')}: {v:6d} Bloecke ({v*100//len(others)}%)")

print("\nErstes Byte:")
c1=collections.Counter(b[0] for _,b,_ in others if b)
for k,v in c1.most_common(10):
    print(f"  0x{k:02x}: {v:6d} ({v*100//len(others)}%)")

# Hypothese: u16 @0x10 == Blockgroesse (wie bei Kacheln)?
h1=sum(1 for _,b,_ in others if len(b)>=18 and u16(b,16)==len(b))
h2=sum(1 for _,b,_ in others if len(b)>=2 and u16(b,0)==len(b))
h3=sum(1 for _,b,_ in others if len(b)>=1 and b[0]==min(len(b)//1,255) )
print(f"\nu16 @0x10 == Blockgroesse: {h1}/{len(others)}")
print(f"u16 @0x00 == Blockgroesse: {h2}/{len(others)}")

# Die [N][Tabelle][Records]-Struktur der AdvancedRouting-Bloecke?
h4=0
for _,b,_ in others:
    if len(b)<8: continue
    N=b[0]
    if N and 3+2*N+2<=len(b) and u16(b,3)==3+2*N: h4+=1
print(f"[N][Tabelle]-Struktur (byte0==N, erster Offset==3+2N): {h4}/{len(others)}")

# Enthalten sie Strings? Polylinien-Deltas?
def s8(v): return v-256 if v>127 else v
withstr=sum(1 for _,b,_ in others if re.search(rb'[A-Za-z]{6,}', b))
print(f"Bloecke mit ASCII-Woertern (>=6): {withstr}/{len(others)}")

print("\nBeispiele nicht erkannter Bloecke (erste 64 B):")
seen=set()
for off,b,_ in others:
    k=bytes(b[:2])
    if k in seen or len(b)<64: continue
    seen.add(k)
    if len(seen)>6: break
    print(f"  @0x{off:x} {len(b)} B")
    for r in range(0,64,16):
        row=b[r:r+16]
        print(f"    {r:04x}  {row.hex(' ')}  "
              f"{''.join(chr(c) if 32<=c<127 else '.' for c in row)}")
