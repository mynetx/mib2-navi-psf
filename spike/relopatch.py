#!/usr/bin/env python3
"""Blockverschiebung statt Groessenerhalt.

Neu erkannt: jeder der bisher blockierten Testort-Bloecke hat einen
KLARTEXT-Indexeintrag (u32 Offset, u16 Laenge) im Dateikopf, genau einmal.
Damit ist die Blocklaenge keine Zwangsbedingung mehr: der gepatchte Block
wird ans Dateiende gehaengt und der Indexeintrag umgeschrieben.

Marker RELOBAY (7 B wie Testort) nur in den drei bisher unerreichbaren
Bloecken. Alles andere bleibt Original -- erscheint RELOBAY im Auto auf
z9-z11, ist die Verschiebung bewiesen.
"""
import struct, lzma, os, sys
SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='../spike/GermanyWest_Basic.reloc.psf'
OLD=b'Testort'; NEW=b'RELOBAY'
SIZEFIELD=0x04d          # u32 == Dateigroesse
TARGETS=[0x36ca22e, 0x3392334, 0x346c45e]

SET=[{'mf':lzma.MF_BT4,'depth':0,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':128,'nice_len':273},
     {'mf':lzma.MF_BT4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':0,'nice_len':128},
     {'mf':lzma.MF_HC4,'depth':512,'nice_len':273},
     {'mf':lzma.MF_BT3,'depth':0,'nice_len':128}]
def bestc(data,dic):
    ds=max(4096,min(dic,1<<26)); b=None
    for s in SET:
        f=[{'id':lzma.FILTER_LZMA1,'dict_size':ds,'lc':3,'lp':0,'pb':2,
            'mode':lzma.MODE_NORMAL,**s}]
        try: o=lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f)
        except Exception: continue
        if b is None or len(o)<len(b): b=o
    return b

d=bytearray(open(SRC,'rb').read()); N0=len(d)
assert struct.unpack_from('<I',d,SIZEFIELD)[0]==N0, "Groessenfeld passt nicht"
print(f"Original {N0} B, Groessenfeld @0x{SIZEFIELD:x} stimmt\n")

out=bytearray(d)
plan=[]
for P in TARGETS:
    dic=struct.unpack_from('<I',d,P+1)[0]
    siz=struct.unpack_from('<Q',d,P+5)[0]
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(bytes(d[P:])); COMP=N0-P-len(dec.unused_data)
    plain=raw[:siz]; occ=plain.count(OLD)
    # Indexeintrag suchen: genau einmal (Offset,Laenge)
    pat=struct.pack('<IH',P,COMP)
    q=d.find(pat); assert q>=0 and d.find(pat,q+1)<0, f"Indexeintrag nicht eindeutig @0x{P:x}"
    mod=plain.replace(OLD,NEW); assert len(mod)==siz
    new=bestc(mod,dic)
    plan.append((P,COMP,q,occ,new,mod,siz))
    print(f"@0x{P:07x}  {occ}x {OLD.decode()}  alt komp {COMP:6d}  "
          f"neu {len(new):6d} ({len(new)-COMP:+d})  Index @0x{q:x}")

# anhaengen und Index umschreiben
for P,COMP,q,occ,new,mod,siz in plan:
    newoff=len(out)
    assert len(new)<=0xFFFF, "Laenge passt nicht in u16"
    out += new
    struct.pack_into('<IH', out, q, newoff, len(new))
    print(f"@0x{P:07x} -> neu @0x{newoff:x} ({newoff}), Index aktualisiert")
struct.pack_into('<I', out, SIZEFIELD, len(out))
open(DST,'wb').write(bytes(out))
print(f"\n{DST}")
print(f"  {N0} -> {len(out)} B (+{len(out)-N0}), Groessenfeld auf {len(out)} gesetzt")

# --- Verifikation ---
v=open(DST,'rb').read()
print("\nVerifikation")
print(f"  Groessenfeld == Dateigroesse: "
      f"{struct.unpack_from('<I',v,SIZEFIELD)[0]==len(v)}")
for P,COMP,q,occ,new,mod,siz in plan:
    no,nl=struct.unpack_from('<IH',v,q)
    blk=v[no:no+nl]
    r=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(blk)
    print(f"  Index @0x{q:x} -> @0x{no:x} len {nl}: entpackt {len(r)}=={siz} "
          f"{len(r)==siz}, {r.count(NEW)}x {NEW.decode()}, "
          f"{r.count(OLD)}x {OLD.decode()}")
# alle Bloecke des Originalbereichs noch dekomprimierbar?
ok=bad=0; p=0; n0=N0
while p < n0-13:
    p=v.find(b'\x5d',p,n0)
    if p<0: break
    dic=struct.unpack_from('<I',v,p+1)[0]; s=struct.unpack_from('<Q',v,p+5)[0]
    if dic==s and 0<s<=64_000_000:
        try:
            lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(
                v[p:p+4096], max_length=64)
            ok+=1; p+=13; continue
        except Exception: bad+=1
    p+=1
print(f"  Bloecke im Originalbereich: {ok} ok, {bad} fehlerhaft "
      f"(Original hatte 76003)")
tot=v.count(OLD); rel=v.count(NEW)
print(f"  Datei enthaelt {rel}x {NEW.decode()} (roh, komprimiert unsichtbar)")
