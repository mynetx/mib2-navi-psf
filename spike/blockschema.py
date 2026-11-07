#!/usr/bin/env python3
"""WEGWERF: Blockinneres - Offsettabelle validieren, Datenrecords dumpen."""
import struct, lzma, collections
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]

def recs(path):
    d=open(path,'rb').read(); n=len(d); out=[]; o=0x102
    while o+20<=n:
        off,ln,k=u32(d,o),u32(d,o+4),u32(d,o+8)
        if not(0<off<n and 0<ln<=8_000_000 and off+ln<=n): break
        out.append((off,ln,k)); o+=20
    return d, out[:-1]

for region in ('Malta','Albania'):
    path=f'{region}_AdvancedRouting.psf'
    d,rs = recs(path)
    print(f"######## {region}: {len(rs)} Bloecke")
    # ein Block pro Layer
    bylayer=collections.defaultdict(list)
    for r in rs: bylayer[r[2]>>21].append(r)
    for lay in sorted(bylayer):
        off,ln,k = bylayer[lay][0]
        out=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[off:off+ln])
        hdr=out[:3]
        # Offsettabelle lesen bis zum ersten Eintrag
        first=u16(out,3)
        if first<5 or first>len(out): 
            print(f"  Layer {lay}: Tabellenstart 0x{first:x} unplausibel"); continue
        ntab=(first-3)//2
        tab=[u16(out,3+2*i) for i in range(ntab)]
        gaps=[tab[i+1]-tab[i] for i in range(len(tab)-1)]
        gc=collections.Counter(gaps)
        tail=len(out)-tab[-1] if tab else 0
        print(f"  Layer {lay} key=0x{k:x} nr={k&0xFFFF}: {len(out)} B entpackt, "
              f"Kopf={hdr.hex(' ')}")
        print(f"     Tabelle: {ntab} Eintraege, erster=0x{first:x}, letzter=0x{tab[-1]:x}, "
              f"Rest nach letztem = {tail} B")
        print(f"     Luecken-Histogramm: {gc.most_common(6)}  "
              f"(monoton steigend: {all(g>0 for g in gaps)})")
        # Datenrecords dumpen
        sz=gc.most_common(1)[0][0]
        print(f"     erste 8 Datenrecords (Groesse {sz}):")
        for i in range(min(8, len(tab))):
            s=tab[i]; e=tab[i+1] if i+1<len(tab) else len(out)
            rec=out[s:e]
            print(f"        [{i:3d}] @0x{s:04x} {len(rec)}B  {rec.hex(' ')}")
    print()
