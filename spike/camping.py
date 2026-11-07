#!/usr/bin/env python3
"""Country Camping Schinderhannes: das Wegenetz ins Navi schreiben (Bau c1).

Der Platz liegt OESTLICH von 7,55861 E und damit in der Ostkachel -- Block C
@0x346c45e, nicht in Testorts Block B. In der Navi-Karte ist er komplett leer:
null Stuetzpunkte im Platzrechteck. Nur die Zufahrt `Testorter Straße` gibt es,
und die endet rund 700 m noerdlich davon.

Sonde: die laengsten drei Wege bekommen den Namen `Campingplatz`, alle uebrigen
einen LEEREN Namen (`00 03 00`). Ob ein leerer Name zulaessig ist, ist offen --
erscheinen auch die namenlosen, sind kuenftige Baeue ohne Labelflut moeglich.
"""
import json, lzma, struct, sys, pickle, math
sys.path.insert(0,'.')
from roadrec import parse_section
from roadwrite import to_units, densify, record, encode_deltas

SRC='../sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf'
DST='GermanyWest_Basic.c1.psf'
ZIEL, OPFER, PARTNER = 0x346c45e, 0x346ffe7, 0x346a990
IH_ZIEL,  HI_ZIEL  = 0x7550c, 0x3ab1e5d
IH_OPFER, HI_OPFER = 0x75524, 0x3ab1eb1
S=18.0
# Platzrechteck in Kacheleinheiten (aus der Abgleichsmessung)
BX0,BX1,BY0,BY1 = 28,101,12,82

def blk(d,P):
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw=dec.decompress(d[P:]); return raw, len(d)-P-len(dec.unused_data)

def build(data, mf, nl):
    f=[{'id':lzma.FILTER_LZMA1,'dict_size':len(data),'lc':3,'lp':0,'pb':2,
        'mode':lzma.MODE_NORMAL,'mf':mf,'nice_len':nl,'depth':0}]
    o=bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
    struct.pack_into('<I',o,1,len(data)); struct.pack_into('<Q',o,5,len(data))
    chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert chk.decompress(bytes(o))==data and len(chk.unused_data)==0
    return bytes(o)

MFS=[lzma.MF_BT2,lzma.MF_BT3,lzma.MF_BT4,lzma.MF_HC3,lzma.MF_HC4]
def sweep(data):
    best=(None,None,None)
    for mf in MFS:
        for nl in (5,6,8,10,12,16,24,32,48,64,96,128,192,273):
            try: o=build(data,mf,nl)
            except Exception: continue
            if best[0] is None or len(o)<best[0]: best=(len(o),mf,nl)
    return best

d=open(SRC,'rb').read(); N=len(d); out=bytearray(d)
raw, ext = blk(d, ZIEL)
X0,Y0,X1,Y1=struct.unpack_from('<4i',raw,0)
W,H=int((X1-X0)/S),int((Y1-Y0)/S)

# --- Wege auswaehlen: im Platzrechteck, baubar, nicht schon vorhanden --------
vor=parse_section(raw,11341,W,H)
pkt=[(p[0],p[1]) for r in vor for p in r['points']]
ways=json.load(open('osm/osm_camp.json'))['elements']
kand=[]
for w in sorted(ways,key=lambda w:-w['len']):
    pts=[to_units(p['lat'],p['lon'],X0,Y0,S) for p in w['geometry']]
    if not all(BX0<=a<=BX1 and BY0<=b<=BY1 for a,b in pts): continue
    dn=densify(pts)
    try: dl,_=encode_deltas(dn)
    except ValueError: continue
    if not dl: continue
    gedeckt=sum(1 for a,b in dn if any(abs(a-x)<=1.5 and abs(b-y)<=1.5 for x,y in pkt))
    if gedeckt>=len(dn)*0.6: continue          # liegt schon in der Karte
    kand.append((w,dn,len(dl)))
print(f"{len(kand)} Wege werden eingezeichnet "
      f"(zusammen {sum(w['len'] for w,_,_ in kand):.0f} m, "
      f"{sum(n for _,_,n in kand)} Deltabytes)")

# --- Recordbytes: die drei laengsten benannt, der Rest namenlos --------------
neu=bytearray(); benannt=0
for i,(w,dn,n) in enumerate(kand):
    nm = 'Country Camping' if w['len']>=100 else ''
    if nm: benannt+=1
    r=record(dn, nm)
    neu += raw[11341:11348] + r            # 7 B Rahmung vom Sektionsanfang
print(f"   {benannt} mit Namen 'Country Camping' (>=100 m), "
      f"{len(kand)-benannt} mit leerem Namen (Sonde)")

# einfuegen hinter dem letzten vorhandenen Record der Sektion
ins=max(r['end'] for r in vor)
payload = raw[:ins] + bytes(neu) + raw[ins:]
print(f"   eingefuegt @{ins}, Payload {len(raw)} -> {len(payload)} "
      f"({len(payload)-len(raw):+d} B)")

L,mf,nl = sweep(payload)
nb = build(payload, mf, nl)
assert nb[0]==93 and struct.unpack_from('<I',nb,1)[0]==len(payload)
assert struct.unpack_from('<Q',nb,5)[0]==len(payload)
print(f"   Strom {L}, Extent {ext} ({L-ext:+d})")
_, opferlen = blk(d, OPFER)
assert ext < L <= ext+opferlen, f"passt nicht in den Opferblock ({opferlen} B)"
out[ZIEL:ZIEL+L]=nb

# --- Index ------------------------------------------------------------------
_, partnerlen = blk(d, PARTNER)
assert struct.unpack_from('<IH', d, IH_ZIEL)==(ZIEL, ext)
assert struct.unpack_from('<HI', d, HI_ZIEL)==(ext, ZIEL)
struct.pack_into('<H', out, IH_ZIEL+4, L); struct.pack_into('<H', out, HI_ZIEL, L)
assert struct.unpack_from('<IH', d, IH_OPFER)==(OPFER, opferlen)
assert struct.unpack_from('<HI', d, HI_OPFER)==(opferlen, OPFER)
struct.pack_into('<IH', out, IH_OPFER, PARTNER, partnerlen)
struct.pack_into('<HI', out, HI_OPFER, partnerlen, PARTNER)
print(f"   Index: Laenge {ext}->{L}; Opfer @0x{OPFER:07x} -> @0x{PARTNER:07x} ({partnerlen} B)")

assert len(out)==N
open(DST,'wb').write(bytes(out))
json.dump({'grow':{hex(ZIEL):L}, 'sacrificed':[hex(OPFER)],
           'note':f'Camping Schinderhannes -- {len(kand)} Wege, Block waechst +{L-ext} B'},
          open(DST.replace('.psf','.plan.json'),'w'), indent=1)

print("\n--- Verifikation ---")
o=bytes(out)
r2,L2=blk(o,ZIEL)
n2=parse_section(r2,11341,W,H)
imfeld=[r for r in n2 if all(BX0<=p[0]<=BX1 and BY0<=p[1]<=BY1 for p in r['points'])]
print(f"Dateigroesse unveraendert: {len(o)==N}")
print(f"Block C: Strom {L2}, entpackt {len(r2)}")
print(f"Records im Platzrechteck laut Decoder: vorher 0, jetzt {len(imfeld)} "
      f"(der Decoder verwirft leere Namen -- deshalb Bytevergleich:)")
fehlt=0
for i,(w,dn,n) in enumerate(kand):
    nm='Country Camping' if w['len']>=100 else ''
    if record(dn,nm) not in r2: fehlt+=1
print(f"Recordbytes im gebauten Block wiedergefunden: {len(kand)-fehlt}/{len(kand)}")
assert fehlt==0
ok=bad=0
for P,c,s in pickle.load(open('gw_anchors.pkl','rb')):
    if P==OPFER: continue
    try: lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(o[P:P+c+64],max_length=32); ok+=1
    except Exception: bad+=1
print(f"Bloecke ausser dem Opfer: {ok} dekodieren, {bad} fehlerhaft")
print(f"\ngeschrieben: {DST}")
