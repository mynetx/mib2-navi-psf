#!/usr/bin/env python3
"""Zweiter Blocktyp: selbstkonsistente Offsettabelle finden."""
import struct, lzma, math, collections, re
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
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
print(f"{len(others)} nicht-Kachel-Bloecke, davon {len(big)} >=400 B\n")

def find_table(b):
    """Suche (start,N): u16@start == start+2N, Eintraege aufsteigend, < len(b)."""
    nb=len(b)
    for start in range(4, 40):
        if start+2>nb: break
        first=u16(b,start)
        if not(start+4<=first<nb): continue
        rest=first-start
        if rest%2: continue
        N=rest//2
        if N<4: continue
        tab=[]
        okk=True
        for i in range(N):
            o=start+2*i
            if o+2>nb: okk=False; break
            v=u16(b,o)
            if tab and v<tab[-1]: okk=False; break
            if not(first<=v<=nb): okk=False; break
            tab.append(v)
        if okk and len(tab)==N:
            return start, N, tab
    return None

hits=0; results=[]
for o,b in big:
    r=find_table(b)
    if r:
        hits+=1; results.append((o,b,r))
print(f"Selbstkonsistente Tabelle gefunden: {hits}/{len(big)} = "
      f"{hits*100/max(1,len(big)):.1f}%\n")

sc=collections.Counter(r[2][0] for r in results)
print(f"Tabellenstart-Verteilung: {sc.most_common(6)}")
recsz=collections.Counter()
for o,b,(st,N,tab) in results[:400]:
    for i in range(len(tab)-1): recsz[tab[i+1]-tab[i]]+=1
print(f"Recordgroessen (Top 10): {recsz.most_common(10)}")

print("\nBeispiele:")
for o,b,(st,N,tab) in results[:4]:
    print(f"  @0x{o:x} {len(b)} B: Tabelle @0x{st:x}, {N} Eintraege, "
          f"0x{tab[0]:x}..0x{tab[-1]:x}, Rest {len(b)-tab[-1]} B")
    print(f"     Kopf: {b[:st].hex(' ')}")
    for i in range(min(4,N-1)):
        s_,e_=tab[i],tab[i+1]
        rec=b[s_:e_]
        pr=[(s8(rec[k]),s8(rec[k+1])) for k in range(0,len(rec)-1,2)]
        print(f"     Rec[{i}] {e_-s_:3d}B  {rec[:24].hex(' ')}")
        if len(pr)>=4:
            xs=[0]; ys=[0]; x=y=0
            for dx,dy in pr:
                x+=dx; y+=dy; xs.append(x); ys.append(y)
            pl=sum(math.hypot(a,b_) for a,b_ in pr)
            net=math.hypot(xs[-1],ys[-1])
            print(f"            als Deltas: {len(pr)} Segmente, "
                  f"Ausdehnung {max(xs)-min(xs)}x{max(ys)-min(ys)}, "
                  f"Kohaerenz {net/max(1e-9,pl):.2f}")
