#!/usr/bin/env python3
"""Test 10: Marker in die ORIGINAL-Blocklaenge hineinkomprimiert.

Test 9 hat die Bisektion entschieden: der Marker war nie das Problem, ein
physisch gewachsener Block ist es. Passend dazu war Test 6 folgenlos -- die
gespeicherte Laenge wird nicht benutzt, das Geraet nimmt offenbar den Abstand
zum naechsten Block. Ein in place gewachsener Block wird damit abgeschnitten
und reisst den Dekoder mit.

Die Parametersuche (fitsearch.py) zeigt: mit lc=2 lp=0 pb=0 statt der
Originalparameter lc=3 lp=0 pb=2 wird jeder Zielblock KLEINER als das
Original. Damit faellt der ganze Zwang weg.

Dieser Bau aendert deshalb KEINEN Indexeintrag, biegt nichts um, opfert
nichts, pflegt kein Format D und laesst die Datei gleich gross -- genau das
Muster des akzeptierten §6-Baus. Der Rest der alten Blockextents wird
genullt.
"""
import struct, lzma, pickle, itertools

BASE='GermanyWest_Basic.patched.psf'; DST='GermanyWest_Basic.t10.psf'
OLD, NEW = b'Testort', b'RELOBAY'
TARGETS=[('B', 0x3392334), ('C', 0x346c45e)]
MF=[lzma.MF_BT4,lzma.MF_BT3,lzma.MF_BT2,lzma.MF_HC4,lzma.MF_HC3]
NICE=[16,32,64,128,192,273]; DEPTH=[0,64,256,512,1024]

def comp(data,ds,lc,lp,pb,mf,nl,dp):
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':lc,'lp':lp,'pb':pb,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':dp}]
    try: return lzma.compress(data,format=lzma.FORMAT_ALONE,filters=f)
    except Exception: return None

def search(data, ds):
    s1=sorted((len(o),lc,lp,pb) for lc,lp in
              [(a,b) for a in range(5) for b in range(5) if a+b<=4] for pb in range(5)
              for o in [comp(data,ds,lc,lp,pb,lzma.MF_BT4,273,0)] if o)
    best=(1<<30,None,None)
    for ln,lc,lp,pb in s1[:3]:
        for mf,nl,dp in itertools.product(MF,NICE,DEPTH):
            o=comp(data,ds,lc,lp,pb,mf,nl,dp)
            if o and len(o)<best[0]: best=(len(o),o,(lc,lp,pb,nl,dp))
    return best

def blk(d,P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

d=open(BASE,'rb').read(); N=len(d); out=bytearray(d); plan=[]
for tag,P in TARGETS:
    raw,orig=blk(d,P); ds=struct.unpack_from('<I',d,P+1)[0]
    occ=raw.count(OLD); assert occ>0
    ln,nb,par=search(raw.replace(OLD,NEW), ds)
    assert ln<=orig, f"{tag}: {ln} > {orig}, passt nicht"
    plan.append((tag,P,orig,nb,occ,par))
    print(f"Ziel {tag} @0x{P:07x}  {occ}x{OLD.decode()}->{NEW.decode()}  "
          f"{orig} -> {ln} ({ln-orig:+d})  lc/lp/pb={par[0]}/{par[1]}/{par[2]} "
          f"nice={par[3]} depth={par[4]}  {orig-ln} B genullt")

for tag,P,orig,nb,occ,par in plan:
    out[P:P+len(nb)]=nb
    out[P+len(nb):P+orig]=b'\0'*(orig-len(nb))     # alten Rest neutralisieren
assert len(out)==N
open(DST,'wb').write(bytes(out))

print("\n--- Verifikation ---")
o=bytes(out)
print(f"Groesse {N} -> {len(o)}   unveraendert: {len(o)==N}")
print(f"geaenderte Bytes: {sum(1 for i in range(N) if d[i]!=o[i])}")
for tag,P,orig,nb,occ,par in plan:
    raw,L=blk(o,P)
    src,_=blk(d,P)
    assert raw==src.replace(OLD,NEW), f"{tag}: Inhalt weicht ab"
    assert L==len(nb) and L<=orig
    q=d.find(struct.pack('<IH',P,orig))
    print(f"Ziel {tag} @0x{P:07x}: Strom {L} <= Extent {orig}, plain {len(raw)}, "
          f"{NEW.decode()}×{raw.count(NEW)} {OLD.decode()}×{raw.count(OLD)}")
    print(f"   Indexeintrag @0x{q:x} unveraendert: "
          f"{struct.unpack_from('<IH',o,q)} == {struct.unpack_from('<IH',d,q)}")
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    try:
        lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1; print(f"   FEHLER @0x{P:07x}")
print(f"Bloecke pruefbar: {ok} ok, {bad} fehlerhaft  (kein Block uebersprungen)")
