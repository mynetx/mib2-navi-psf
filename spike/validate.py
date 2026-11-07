#!/usr/bin/env python3
"""Prueft einen gebauten .psf gegen alle an der Originaldatei gemessenen
Invarianten. Wer hier gruen ist, hat keinen Fahrzeugtest an einem Bauschaden
verschwendet.

    python3 validate.py GermanyWest_Basic.p1.psf

Geprueft wird (Herkunft der Invariante in Klammern):
  1  Dateigroesse gegen das Original                                  (§6d T4)
  2  jeder Block dekodiert                                            (§1)
  3  props-Byte == 93 in JEDEM Block                                  (Gotcha 2)
  4  dict_size == entpackte Groesse in JEDEM Block                    (Gotcha 2)
  5  size-Feld == entpackte Groesse in JEDEM Block                    (Gotcha 1)
  6  Stromlaenge == Extent, oder Extent-14 mit Format-C-Record        (Gotcha 2)
  7  13-B-Kopf geaenderter Bloecke byteidentisch zum Original         (Gotcha 1)
  8  Indexrecords <IH>/<HI> zeigen auf Blockanfaenge, nicht mittenrein (§6b,§6e)
  9  kein Indexrecord zeigt auf einen ueberschriebenen Block           (§6d T3)
 10  Sektionstabelle monoton und innerhalb des Blocks                  (§6h)
 12  Strassenkette in Sektion 16 geaenderter Bloecke: Gruppenindex zeigt
     auf Elementanfaenge, Kette lueckenlos, benannte Elemente wohlgeformt (§6l)

Baeue, die absichtlich eine Invariante verletzen (ein Block waechst in seinen
Nachbarn hinein), legen neben die .psf eine `<name>.plan.json`:

    {"grow":       {"0x3392334": 13896},     # Block -> neue Stromlaenge
     "sacrificed": ["0x339593c"],            # Bloecke, die dabei sterben
     "note":       "Wachstumstest 1"}

Der Validator zieht den Plan dann in die Invarianten ein, statt ihn als Fehler
zu melden -- und prueft zusaetzlich (11), dass der gewachsene Block das Opfer
nicht ueberlaeuft und dass auf ein Opfer KEIN Indexeintrag mehr zeigt, weder
<IH> (Formate A-C) noch <HI> (Format D, §6e).
"""
import sys, struct, lzma, pickle, collections, json, os
import sec16

ORIG='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
FMTC=b'\x01\x00\x00\x00\x00\x00\x00\x03'

def stream(d,P,limit):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:P+limit])
    return raw, limit-len(dec.unused_data)

def sections(raw):
    for s in range(20,60):
        p=[]
        for i in range(64):
            o=s+4*i
            if o+4>len(raw): break
            k,v=struct.unpack_from('<HH',raw,o)
            if p and not (k>p[-1][0] and v>p[-1][1]): break
            if v>len(raw): break
            p.append((k,v))
        if len(p)>=6: return s,p
    return None,None

def main(path):
    o=open(ORIG,'rb').read(); n=open(path,'rb').read()
    anc=pickle.load(open('gw_anchors.pkl','rb'))
    offs=[p for p,c,s in anc]
    ext={offs[i]: (offs[i+1]-offs[i]) for i in range(len(offs)-1)}
    ext[offs[-1]]=len(o)-offs[-1]
    err=[]; warn=[]; changed=[]; checked16=[]

    print(f"Pruefe {path}")

    planpath=os.path.splitext(path)[0]+'.plan.json'
    grow={}; sacr=set()
    if os.path.exists(planpath):
        pl=json.load(open(planpath))
        grow={int(k,0): v for k,v in pl.get('grow',{}).items()}
        sacr={int(k,0) for k in pl.get('sacrificed',[])}
        print(f"[0] Bauplan {os.path.basename(planpath)}: "
              f"{pl.get('note','')}"
              f"  waechst: {', '.join(f'0x{k:07x}->{v}' for k,v in grow.items()) or '-'}"
              f"  geopfert: {', '.join(f'0x{k:07x}' for k in sacr) or '-'}")
        for P,L in grow.items():
            if P not in ext: err.append(f"[11] Plan: 0x{P:07x} ist kein Blockanfang"); continue
            # Grenze = Anfang des naechsten Blocks, der NICHT geopfert ist
            j=offs.index(P)+1
            while j<len(offs) and offs[j] in sacr: j+=1
            grenze=offs[j] if j<len(offs) else len(o)
            ende=P+L
            if L<=ext[P]:
                warn.append(f"[11] 0x{P:07x} soll wachsen, neue Laenge {L} <= Extent {ext[P]}")
            if ende>grenze:
                err.append(f"[11] 0x{P:07x} laeuft mit {L} B bis 0x{ende:07x} und damit "
                           f"ueber die geopferten Bloecke hinaus (Grenze 0x{grenze:07x})")
            else:
                tot=grenze-ende
                if tot: warn.append(f"[11] 0x{P:07x}: {tot} B hinter dem Strom sind tot "
                                    f"(Rest des geopferten Blocks) -- erwartet")
            ext[P]=L
        offs=[q for q in offs if q not in sacr]
    if len(n)!=len(o):
        warn.append(f"[1] Dateigroesse {len(n)} != Original {len(o)} ({len(n)-len(o):+d}) "
                    f"-- Dateiwachstum ist im Fahrzeug UNGEPRUEFT (§6h)")
    else:
        print(f"[1] Dateigroesse {len(n)} == Original")

    for P in offs:
        E=ext[P]
        try: raw,comp = stream(n,P,E+64)
        except Exception as e:
            err.append(f"[2] @0x{P:07x} dekodiert nicht: {e}"); continue
        props=n[P]; dic=struct.unpack_from('<I',n,P+1)[0]; siz=struct.unpack_from('<Q',n,P+5)[0]
        if props!=93: err.append(f"[3] @0x{P:07x} props={props} statt 93")
        if dic!=len(raw): err.append(f"[4] @0x{P:07x} dict_size={dic} != entpackt {len(raw)}")
        if siz!=len(raw):
            s='UNBEKANNT (0xFFFF..)' if siz==2**64-1 else str(siz)
            err.append(f"[5] @0x{P:07x} size={s} != entpackt {len(raw)}  <== lzma.compress-Falle")
        if comp!=E:
            if comp==E-14 and n[P+comp:P+comp+8]==FMTC: pass
            else:
                d=E-comp
                (err if d<0 else warn).append(
                    f"[6] @0x{P:07x} Strom {comp}, Extent {E} ({d:+d} tote Bytes, "
                    f"kein Format-C-Record)")
        if n[P:P+E]!=o[P:P+E]:
            changed.append(P)
            if n[P:P+13]!=o[P:P+13]:
                if P in grow and len(raw)!=struct.unpack_from('<I',o,P+1)[0]:
                    # Payload ist gewachsen -> dict_size/size MUESSEN sich aendern.
                    # Die echte Invariante prueft [4]/[5]; Byteidentitaet waere
                    # hier falsch verlangt.
                    warn.append(f"[7] @0x{P:07x} 13-B-Kopf geaendert, weil der Payload "
                                f"waechst ({struct.unpack_from('<I',o,P+1)[0]} -> {len(raw)}) "
                                f"-- laut Plan erwartet")
                else:
                    err.append(f"[7] @0x{P:07x} 13-B-Kopf weicht vom Original ab: "
                               f"{n[P:P+13].hex(' ')} statt {o[P:P+13].hex(' ')}")
            s,p=sections(raw)
            if p is None: warn.append(f"[10] @0x{P:07x} keine Sektionstabelle gefunden")
            elif 16 in dict(p):
                ro,_=stream(o,P,E+64)
                so,po=sections(ro)
                s16=dict(po).get(16,0) if po else 0
                for e in sec16.check(ro,raw,max(0,s16-40)):
                    err.append(f"[12] @0x{P:07x} {e}  (§6l, e1 stuerzte ab)")
                checked16.append(P)

    print(f"[12] Strassenkette in {len(checked16)} geaenderten Bloecken geprueft")
    print(f"[2-7] {len(offs)} Bloecke geprueft, {len(changed)} veraendert: "
          f"{', '.join(f'0x{P:07x}' for P in changed[:8])}"
          f"{' …' if len(changed)>8 else ''}")

    # 8/9: Indexrecords -- EIN numpy-Durchlauf statt 76.003 Volltextsuchen
    import numpy as np
    a=np.frombuffer(n,dtype=np.uint8).astype(np.uint32); N=len(a)
    v32=a[0:N-5]|(a[1:N-4]<<8)|(a[2:N-3]<<16)|(a[3:N-2]<<24)
    v16=a[4:N-1]|(a[5:N]<<8)
    del a
    off=np.array(offs,dtype=np.uint32)
    ln =np.array([ext[P] for P in offs],dtype=np.uint32)
    k=np.clip(np.searchsorted(off,v32),0,len(off)-1)
    isblk=off[k]==v32
    cand=np.nonzero(isblk)[0]
    L=v16[cand]; want=ln[k[cand]]
    okmask=(L==want)|(L==want-14)
    print(f"[8] <IH>: {len(cand)} Stellen mit Blockoffset als u32, "
          f"{int(okmask.sum())} davon mit passender Laenge")
    # <HI>: u16 Laenge vor u32 Offset
    b=np.frombuffer(n,dtype=np.uint8).astype(np.uint32)
    h16=b[0:N-5]|(b[1:N-4]<<8)
    h32=b[2:N-3]|(b[3:N-2]<<8)|(b[4:N-1]<<16)|(b[5:N]<<24)
    del b
    k2=np.clip(np.searchsorted(off,h32),0,len(off)-1)
    c2=np.nonzero(off[k2]==h32)[0]
    L2=h16[c2]; w2=ln[k2[c2]]
    ok2=(L2==w2)|(L2==w2-14)
    print(f"[8] <HI>: {len(c2)} Stellen, {int(ok2.sum())} mit passender Laenge")
    # 11: auf ein Opfer darf KEIN Indexeintrag mehr zeigen (<IH> und <HI>)
    for P in sorted(sacr):
        a=int((v32==P).sum()); b=int((h32==P).sum())
        if a or b:
            err.append(f"[11] geopferter Block 0x{P:07x} wird noch referenziert: "
                       f"{a}x <IH>, {b}x <HI> -- umbiegen oder entfernen")
        else:
            print(f"[11] geopferter Block 0x{P:07x}: keine Referenz mehr, weder <IH> noch <HI>")
    # 11b: die Indexeintraege eines gewachsenen Blocks muessen die NEUE Laenge fuehren
    for P,L in grow.items():
        ih=int(((v32==P)&(v16==L)).sum()); hi=int(((h32==P)&(h16==L)).sum())
        alt_ih=int(((v32==P)&(v16!=L)).sum()); alt_hi=int(((h32==P)&(h16!=L)).sum())
        print(f"[11] gewachsener Block 0x{P:07x}: {ih}x <IH> und {hi}x <HI> mit neuer Laenge {L}")
        if alt_ih or alt_hi:
            warn.append(f"[11] 0x{P:07x}: {alt_ih}x <IH>/{alt_hi}x <HI> fuehren noch eine "
                        f"andere Laenge (nach Test 6 folgenlos, aber unsauber)")

    # 9: zeigt ein Record auf einen ueberschriebenen Block mit falscher Laenge?
    for P in changed:
        E=ext[P]
        hits_ih=int(((v32==P)&(v16!=E)&(v16!=E-14)).sum())
        if hits_ih:
            warn.append(f"[9] @0x{P:07x}: {hits_ih} <IH>-Stellen mit abweichender Laenge")
        co=n.count(struct.pack('<I',P)); cc=o.count(struct.pack('<I',P))
        if co!=cc:
            warn.append(f"[9] @0x{P:07x} rohe u32-Verweise {cc} -> {co}")

    print()
    for w in warn: print("WARN ", w)
    for e in err: print("FEHLER", e)
    print(f"\n{'BESTANDEN' if not err else 'DURCHGEFALLEN'}: "
          f"{len(err)} Fehler, {len(warn)} Warnungen")
    return 1 if err else 0

if __name__=='__main__':
    sys.exit(main(sys.argv[1]))
