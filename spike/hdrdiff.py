#!/usr/bin/env python3
"""Kopf der Blattkacheln per Spaltenvergleich zerlegen: was ist konstant, was variiert?"""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)

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
leaves=[]
for off,b in bs:
    if len(b)<300: continue
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): continue
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): continue
    L=round(math.log2(360.0/w))
    if not(11<=L<=14) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: continue
    leaves.append((L,off,b))
print(f"{len(leaves)} Blattkacheln\n")

# 1) Ist u16 @0x10 die Blockgroesse?
ok=sum(1 for L,off,b in leaves if u16(b,16)==len(b))
print(f"u16 @0x10 == Blockgroesse: {ok}/{len(leaves)} = {ok*100/len(leaves):.1f}%")

# 2) Spaltenvergleich 0x12..0x60
sample=[b for L,off,b in leaves if len(b)>=0x80][:400]
print(f"\nSpaltenvergleich ueber {len(sample)} Bloecke (Byteposition: Anzahl "
      f"verschiedener Werte, haeufigster):")
for o in range(0x12, 0x60):
    vals=collections.Counter(b[o] for b in sample)
    mc,cnt=vals.most_common(1)[0]
    flag='KONST' if len(vals)==1 else ('fast '+f'{cnt*100//len(sample)}%' if cnt*2>len(sample) else '')
    print(f"  0x{o:02x}: {len(vals):3d} Werte, haeufigster 0x{mc:02x} "
          f"({cnt*100//len(sample):3d}%)  {flag}")

# 3) TLV-Hypothese pruefen: Paare (u16 tag, u16 offset) ab einem Startpunkt
print("\nTLV-Test: Folge von (u16 tag, u16 wert) mit aufsteigenden tags "
      "und wert < Blockgroesse")
best=collections.Counter()
for L,off,b in leaves[:400]:
    n=len(b)
    for start in range(0x12, 0x40):
        tags=[]; o=start; good=0
        while o+4<=min(n,0x100):
            t=u16(b,o); v=u16(b,o+2)
            if tags and t<=tags[-1]: break
            if not(0<t<0x200 and 0<v<n): break
            tags.append(t); good+=1; o+=4
        if good>=3: best[(start,good)]+=1
for (start,good),c in best.most_common(10):
    print(f"   Start 0x{start:02x}, {good} TLV-Paare: bei {c} Bloecken")
