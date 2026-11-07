#!/usr/bin/env python3
"""Zweiter Blocktyp: Endianness und Tabellenstart per exakter Selbstkonsistenz."""
import struct, lzma, math, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16le(b,o): return struct.unpack_from('<H',b,o)[0]
def u16be(b,o): return struct.unpack_from('>H',b,o)[0]
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def s8(v): return v-256 if v>127 else v

def is_tile(b):
    if len(b)<16: return None
    x0,y0,x1,y1=i32(b,0),i32(b,4),i32(b,8),i32(b,12)
    if not(x0<x1 and y0<y1): return None
    w=lon_of(x1)-lon_of(x0)
    if not(0.001<w<10): return None
    L=round(math.log2(360.0/w))
    if not(4<=L<=16) or abs(w-360.0/2**L)/(360.0/2**L)>0.01: return None
    return L

d=open('Malta_Basic.psf','rb').read(); n=len(d)
others=[]; p=0
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
                    if not is_tile(b): others.append((p,b))
                    p+=13; continue
            except Exception: pass
    p+=1
big=[(o,b) for o,b in others if len(b)>=400]
print(f"{len(big)} nicht-Kachel-Bloecke >=400 B\n")

def test(b, start, rd):
    nb=len(b)
    if start+2>nb: return None
    first=rd(b,start)
    if (first-start)%2 or first<=start: return None
    N=(first-start)//2
    if N<4 or start+2*N!=first: return None
    tab=[]
    for i in range(N):
        o=start+2*i
        if o+2>nb: return None
        v=rd(b,o)
        if tab and v<tab[-1]: return None
        if not(first<=v<=nb): return None
        tab.append(v)
    return tab

score=collections.Counter()
for o,b in big:
    for name,rd in (('LE',u16le),('BE',u16be)):
        for start in range(4,32):
            t=test(b,start,rd)
            if t: score[(name,start,)]+=1
print(f"{'Endian':>7} {'Start':>6} {'Treffer':>8}  Anteil")
for (name,start),c in score.most_common(10):
    print(f"{name:>7} {start:>6} {c:>8}  {c*100/len(big):.1f}%")

if score:
    (EN,ST),_=score.most_common(1)[0]
    rd = u16be if EN=='BE' else u16le
    print(f"\n=== Bester Kandidat: {EN} @0x{ST:x} ===")
    ok=[]
    for o,b in big:
        t=test(b,ST,rd)
        if t: ok.append((o,b,t))
    print(f"passt bei {len(ok)}/{len(big)} = {len(ok)*100/len(big):.1f}%")
    rs=collections.Counter()
    for o,b,t in ok:
        for i in range(len(t)-1): rs[t[i+1]-t[i]]+=1
    print(f"Recordgroessen (Top 12): {rs.most_common(12)}")
    print(f"Tabelleneintraege: median "
          f"{sorted(len(t) for _,_,t in ok)[len(ok)//2]}, max {max(len(t) for _,_,t in ok)}")
    print(f"\nKopfbytes 0x00..0x10 der ersten 5:")
    for o,b,t in ok[:5]:
        print(f"  @0x{o:x} {len(b):6d}B  {b[:16].hex(' ')}  N={len(t)}")
    print(f"\nRecords des ersten Blocks (Delta-Test):")
    o,b,t = ok[0]
    for i in range(min(6,len(t)-1)):
        rec=b[t[i]:t[i+1]]
        pr=[(s8(rec[k]),s8(rec[k+1])) for k in range(0,len(rec)-1,2)]
        line=f"  Rec[{i}] {len(rec):3d}B {rec[:20].hex(' ')}"
        if len(pr)>=4:
            x=y=0; xs=[0]; ys=[0]
            for dx,dy in pr:
                x+=dx; y+=dy; xs.append(x); ys.append(y)
            pl=sum(math.hypot(a,c) for a,c in pr); net=math.hypot(x,y)
            line+=f"  {len(pr)}seg ext {max(xs)-min(xs)}x{max(ys)-min(ys)} koh {net/max(1e-9,pl):.2f}"
        print(line)
