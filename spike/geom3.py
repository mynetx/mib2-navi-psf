#!/usr/bin/env python3
"""Die 8192 Byte NACH dem Unterzellen-Array deuten: 1024 x 8 Byte pro Zelle?"""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)

def blocks(path):
    d=open(path,'rb').read(); n=len(d); out=[]; p=0
    while True:
        p=d.find(b'\x5d',p)
        if p<0: break
        if p+13<=n:
            dic=u32(d,p+1); siz=struct.unpack_from('<Q',d,p+5)[0]
            if dic==siz and 0<siz<=16_000_000:
                try:
                    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                        d[p:p+min(n-p,siz*4+4096)])
                    if len(r)>=siz: out.append((p,r[:siz])); p+=13; continue
                except Exception: pass
        p+=1
    return out

bs=blocks('Malta_Basic.psf')
b=[x[1] for x in bs if x[0]==0x23a1c0][0]
x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
# Array finden
start=None
for o in range(16,len(b)-8):
    if x0<=i32(b,o)<=x1 and y0<=i32(b,o+4)<=y1: start=o; break
arr=[]; o=start
while o+8<=len(b) and x0<=i32(b,o)<=x1 and y0<=i32(b,o+4)<=y1:
    arr.append((i32(b,o),i32(b,o+4))); o+=8
end=o
tail=b[end:]
print(f"Array 0x{start:x}..0x{end:x} ({len(arr)} Zellen). Tail: {len(tail)} B")
print(f"Tail == 1024*8 ? {len(tail)==1024*8}\n")

print("Tail, erste 96 Bytes:")
for r in range(0,96,16):
    print(f"  {r:04x}  {tail[r:r+16].hex(' ')}")
nz=[i for i,c in enumerate(tail) if c]
print(f"\nNicht-Null-Bytes im Tail: {len(nz)}/{len(tail)} "
      f"({len(nz)*100/len(tail):.1f}%)  erste bei {nz[:8] if nz else '-'}")
if nz:
    print(f"letzte bei {nz[-8:]}")
    print(f"Bereich mit Inhalt: 0x{nz[0]:x}..0x{nz[-1]:x}")
    s=(nz[0]//16)*16
    print("Erster Inhalt im Tail:")
    for r in range(s, min(s+96,len(tail)), 16):
        print(f"  {r:04x}  {tail[r:r+16].hex(' ')}")

# Tail als 1024 x 8 deuten
print("\nTail als 1024 Records a 8 Byte:")
recs=[tail[i*8:(i+1)*8] for i in range(len(tail)//8)]
nonzero=[i for i,r in enumerate(recs) if any(r)]
print(f"  belegte Records: {len(nonzero)}/{len(recs)}")
for i in nonzero[:12]:
    r=recs[i]
    print(f"    [{i:4d}] {r.hex(' ')}  u32={u32(r,0):10d},{u32(r,4):10d}  "
          f"u16={u16(r,0):5d},{u16(r,2):5d},{u16(r,4):5d},{u16(r,6):5d}")

# Gegenprobe: gibt es einen zweiten Koordinaten-Array (z.B. Level 15)?
print("\nWeitere int32-Paare in der BBox ausserhalb des Arrays:")
extra=[o for o in range(16,len(b)-8) if (o<start or o>=end)
       and x0<=i32(b,o)<=x1 and y0<=i32(b,o+4)<=y1]
print(f"  {len(extra)} Positionen: {[hex(o) for o in extra[:12]]}")
