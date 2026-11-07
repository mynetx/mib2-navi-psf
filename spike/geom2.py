#!/usr/bin/env python3
"""Unterzellen-Array bestaetigen: Rastertreue, Z-Order, Umfeld, Blocklandkarte."""
import struct, lzma, math, collections, re
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)
def merc_x(lon): return R*math.radians(lon)
def merc_y(lat): return R*math.log(math.tan(math.pi/4+math.radians(lat)/2))

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

def zorder(i, bits):
    """Z-Order-Index i -> (col,row)"""
    c=r=0
    for k in range(bits):
        c |= ((i>>(2*k))   & 1) << k
        r |= ((i>>(2*k+1)) & 1) << k
    return c,r

bs=blocks('Malta_Basic.psf')
target=None
for off,b in bs:
    if off==0x23a1c0: target=(off,b); break
off,b = target
x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
print(f"Block @0x{off:x}  {len(b)} B")
print(f"  BBox lon[{lon_of(x0):.6f},{lon_of(x1):.6f}] lat[{lat_of(y0):.6f},{lat_of(y1):.6f}]\n")

hits=[(o,i32(b,o),i32(b,o+4)) for o in range(16,len(b)-8)
      if x0<=i32(b,o)<=x1 and y0<=i32(b,o+4)<=y1]
# nur die zusammenhaengende Kette bei Stride 8
start=hits[0][0]
arr=[]; o=start
while o+8<=len(b) and x0<=i32(b,o)<=x1 and y0<=i32(b,o+4)<=y1:
    arr.append((i32(b,o), i32(b,o+4))); o+=8
end=o
print(f"  Array: 0x{start:x}..0x{end:x}  {len(arr)} Paare  "
      f"({len(arr)*8} B = {len(arr)*8*100//len(b)}% des Blocks)")
print(f"  4^k ? {len(arr)} = 4^{math.log(len(arr),4):.3f}")

# Rastertreue auf Level 14
STEP14 = 360.0/2**14
snap=0
for X,Y in arr:
    lo=lon_of(X); la=lat_of(Y)
    if abs(lo/STEP14-round(lo/STEP14))<0.02 and abs(la/STEP14-round(la/STEP14))<0.02:
        snap+=1
print(f"  auf Level-14-Raster ({STEP14:.7f} deg): {snap}/{len(arr)} = "
      f"{snap*100/len(arr):.1f}%")

# Z-Order-Test
bits=int(round(math.log(len(arr),4)))
cols=1<<bits
base_c=round(lon_of(x0)/STEP14); base_r=round(lat_of(y0)/STEP14)
okz=0
for i,(X,Y) in enumerate(arr):
    c,r = zorder(i,bits)
    ec = base_c+c; er = base_r+r
    if abs(lon_of(X)/STEP14-ec)<0.02 and abs(lat_of(Y)/STEP14-er)<0.02: okz+=1
print(f"  Z-Order stimmt: {okz}/{len(arr)} = {okz*100/len(arr):.1f}%  "
      f"(Gitter {cols}x{cols}, Basis col{base_c} row{base_r})")

print(f"\n  32 Bytes VOR dem Array (0x{start-32:x}):")
print(f"    {b[start-32:start].hex(' ')}")
print(f"  16 Bytes NACH dem Array (0x{end:x}):")
print(f"    {b[end:end+16].hex(' ')}")
print(f"  Rest nach dem Array: {len(b)-end} B")

# Blocklandkarte
print(f"\n  Blocklandkarte:")
print(f"    0x0000..0x0010  BBox-Kopf")
names=[m.start() for m in re.finditer(rb'Triq |Vjal |Sqaq |Misra', b)]
if names:
    print(f"    0x{names[0]:04x}..0x{names[-1]:04x}  Namensbereich "
          f"({len(names)} Treffer, {names[0]*100//len(b)}%..{names[-1]*100//len(b)}%)")
print(f"    0x{start:04x}..0x{end:04x}  Unterzellen-Array ({len(arr)} Paare)")
# Laeufe kleiner signed Bytes = Delta-Kandidaten
runs=[]; cur=None
for i,c in enumerate(b):
    small = c<=0x28 or c>=0xd8
    if small:
        if cur is None: cur=i
    else:
        if cur is not None and i-cur>=24: runs.append((cur,i))
        cur=None
runs.sort(key=lambda r:-(r[1]-r[0]))
print(f"    Laeufe kleiner signed Bytes (Delta-Kandidaten), laengste 6:")
for s,e in runs[:6]:
    print(f"      0x{s:04x}..0x{e:04x}  {e-s} B  ({s*100//len(b)}%)")
