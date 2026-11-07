#!/usr/bin/env python3
"""Abdeckung ueber die GANZE Datei (numpy): an jeder Byteposition q pruefen,
ob u32@q ein Ankeroffset ist und u16@q+4 dessen Laenge (oder Laenge-14)."""
import struct, pickle, collections, numpy as np
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
anc=pickle.load(open('gw_anchors.pkl','rb'))
d=np.frombuffer(open(SRC,'rb').read(), dtype=np.uint8)
N=len(d)
off=np.array([p for p,c,s in anc], dtype=np.uint32)
ln =np.array([c for p,c,s in anc], dtype=np.uint32)
# u32 an jeder Position
b=d.astype(np.uint32)
v32 = b[0:N-5] | (b[1:N-4]<<8) | (b[2:N-3]<<16) | (b[3:N-2]<<24)
v16 = b[4:N-1] | (b[5:N]<<8)
del b
idx=np.searchsorted(off, v32)
idx=np.clip(idx,0,len(off)-1)
isanc = off[idx]==v32
cand=np.nonzero(isanc)[0]
print(f"{len(cand)} Positionen mit Ankeroffset als u32")
k=idx[cand]; L=v16[cand].astype(np.uint32); want=ln[k]
good = cand[(L==want) | (L==want-14)]
gk = idx[good]
ref=np.unique(off[gk])
print(f"Bloecke mit Klartext-(Offset,Laenge): {len(ref)} von {len(anc)} "
      f"({len(ref)*100//len(anc)} %)")
FIRST=anc[0][0]
print(f"   Fundstellen: {len(good)}, davon im Kopf (<0x{FIRST:x}): "
      f"{int((good<FIRST).sum())}, im Datenbereich: {int((good>=FIRST).sum())}")
missmask=~np.isin(off, ref)
miss=off[missmask]
print(f"   ohne Eintrag: {len(miss)}")
h=collections.Counter()
for p,c in zip(miss.tolist(), ln[missmask].tolist()): h[min(c//1000,9)]+=1
print("   Groesse der nicht referenzierten (komp):",
      {f'{k}k':v for k,v in sorted(h.items())})
np.save('gw_refblocks.npy', ref)
np.save('gw_idxpos.npy', np.stack([off[gk], good.astype(np.uint32)]))
