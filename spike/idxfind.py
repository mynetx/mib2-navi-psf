#!/usr/bin/env python3
"""Kopfindex-Record: key(4) offA(4) lenA(2) offB(4) lenB(2) minX(4) maxY(4) maxX(4) minY(4)
Seitenraster: 12 B Seitenkopf + 255 Records a 32 B = 8172 B.
Frage: sind die drei blockierten Testort-Bloecke direkt referenziert?"""
import struct, pickle, math
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
A={p:c for p,c,s in anc}
FIRST=anc[0][0]
d=open(SRC,'rb').read(FIRST)
u32=lambda o: struct.unpack_from('<I',d,o)[0]
u16=lambda o: struct.unpack_from('<H',d,o)[0]
R=6371000.0
def lon(x): return math.degrees(x/R)
def lat(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)

REC0=0x10e; PAGE=8172; NREC=255
npage=(FIRST-REC0)//PAGE+1
recs=[]
for pg in range(npage):
    base=REC0+pg*PAGE
    for i in range(NREC):
        s=base+i*32
        if s+32>FIRST: break
        k,oA,lA,oB,lB = u32(s),u32(s+4),u16(s+8),u32(s+10),u16(s+14)
        if A.get(oA)!=lA or A.get(oB)!=lB: continue
        bb=(u32(s+16),u32(s+20),u32(s+24),u32(s+28))
        recs.append((s,k,oA,lA,oB,lB,bb))
print(f"{npage} Seiten a {PAGE} B, {len(recs)} gueltige Records "
      f"-> {2*len(recs)} Blockverweise von {len(A)} Bloecken")
ref=set()
for r in recs: ref.add(r[2]); ref.add(r[4])
print(f"verschiedene referenzierte Bloecke: {len(ref)}")

TARGET=[0x36ca22e,0x3392334,0x346c45e,0x2f4009f,0x2f34830,0x36ce94a,0x29d48b8,0x3b25e2a]
print("\nTestort-Bloecke im Kopfindex?")
for t in TARGET:
    hit=[r for r in recs if r[2]==t or r[4]==t]
    if hit:
        s,k,oA,lA,oB,lB,bb=hit[0]
        role='A' if oA==t else 'B'
        print(f"  @0x{t:07x}  JA  Record @0x{s:x} Feld {role}  "
              f"key {k>>21}/{k&0x1FFFFF}  lon {lon(bb[0]):.4f}..{lon(bb[2]):.4f} "
              f"lat {lat(bb[3]):.4f}..{lat(bb[1]):.4f}")
    else:
        print(f"  @0x{t:07x}  nein")
pickle.dump(recs, open('gw_headidx.pkl','wb'))
