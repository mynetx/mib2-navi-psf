#!/usr/bin/env python3
"""Delta-Laeufe testen: sind es Polylinien? Diskriminator = Drehwinkelkohaerenz
gegen gemischte Kontrolle derselben Bytes."""
import struct, lzma, math, random, statistics, collections
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def blocks(path, cap=None):
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
                    if len(r)>=siz:
                        out.append((p,r[:siz])); p+=13
                        if cap and len(out)>=cap: return out
                        continue
                except Exception: pass
        p+=1
    return out

def s8(v): return v-256 if v>127 else v

def path_stats(pairs):
    """Kohaerenz: mittlerer |Drehwinkel| zwischen aufeinanderfolgenden Segmenten.
    Strassen -> klein. Rauschen -> ~90 Grad."""
    segs=[(dx,dy) for dx,dy in pairs if dx or dy]
    if len(segs)<6: return None
    angs=[math.atan2(dy,dx) for dx,dy in segs]
    turns=[]
    for i in range(len(angs)-1):
        t=angs[i+1]-angs[i]
        while t>math.pi: t-=2*math.pi
        while t<-math.pi: t+=2*math.pi
        turns.append(abs(math.degrees(t)))
    # Ausdehnung vs Weglaenge: Strassen sind eher gestreckt
    x=y=0; xs=[0]; ys=[0]; L=0
    for dx,dy in segs:
        x+=dx; y+=dy; xs.append(x); ys.append(y); L+=math.hypot(dx,dy)
    ext=math.hypot(max(xs)-min(xs), max(ys)-min(ys))
    return statistics.median(turns), ext/max(1e-9,L), len(segs)

def runs_of(b, minlen=40):
    out=[]; cur=None
    for i,c in enumerate(b):
        if c<=0x28 or c>=0xd8:
            if cur is None: cur=i
        else:
            if cur is not None and i-cur>=minlen: out.append((cur,i))
            cur=None
    if cur is not None and len(b)-cur>=minlen: out.append((cur,len(b)))
    return out

bs=blocks('Malta_Basic.psf', cap=400)
print(f"{len(bs)} Bloecke geladen\n")

variants={
 'A int8 (dx,dy)':      lambda r: [(s8(r[i]),s8(r[i+1])) for i in range(0,len(r)-1,2)],
 'B int8 (dy,dx)':      lambda r: [(s8(r[i+1]),s8(r[i])) for i in range(0,len(r)-1,2)],
 'A+1 versetzt':        lambda r: [(s8(r[i]),s8(r[i+1])) for i in range(1,len(r)-1,2)],
 'D int16 (dx,dy)':     lambda r: [struct.unpack_from('<hh',r,i) for i in range(0,len(r)-3,4)],
}

agg={k:[] for k in variants}; ctrl={k:[] for k in variants}
nruns=0
rnd=random.Random(1)
for off,b in bs:
    for s,e in runs_of(b):
        raw=b[s:e]
        if len(raw)<40: continue
        nruns+=1
        for name,fn in variants.items():
            st=path_stats(fn(raw))
            if st: agg[name].append(st)
            sh=bytearray(raw); rnd.shuffle(sh)
            st2=path_stats(fn(bytes(sh)))
            if st2: ctrl[name].append(st2)

print(f"{nruns} Delta-Laeufe untersucht\n")
print(f"{'Variante':18s} {'Median Drehwinkel':>18s} {'Kontrolle':>10s} "
      f"{'Streckung':>10s} {'Kontrolle':>10s}")
for name in variants:
    if not agg[name]: continue
    t=statistics.median(x[0] for x in agg[name])
    tc=statistics.median(x[0] for x in ctrl[name])
    r=statistics.median(x[1] for x in agg[name])
    rc=statistics.median(x[1] for x in ctrl[name])
    print(f"{name:18s} {t:15.1f} Grad {tc:9.1f} {r:10.3f} {rc:10.3f}")
print("\n(Strassen: kleiner Drehwinkel und hohe Streckung. Rauschen: ~90 Grad, "
      "Streckung ~0.1-0.3)")
