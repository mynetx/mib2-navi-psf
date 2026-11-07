#!/usr/bin/env python3
"""WEGWERF: Metrik gegen Zufall validieren, dann Wiederholungsmuster im Payload finden."""
import sys, os, collections

def dupstat(b, w=8):
    n=len(b)
    seen=collections.Counter(b[i:i+w] for i in range(0, n-w+1, w))
    dup=sum(v-1 for v in seen.values() if v>1)
    return dup, n//w, seen

# --- Kontrollgruppe: echter Zufall gleicher Groesse
rnd = os.urandom(127256)
d,t,_ = dupstat(rnd)
print(f"KONTROLLE os.urandom(127256): {d} Duplikate von {t} ({d*100/t:.3f} %)")
zl = __import__('zlib').compress(open(sys.argv[1],'rb').read()[:127256], 9)
d2,t2,_ = dupstat(zl)
print(f"KONTROLLE zlib(-9) derselben Daten: {d2} von {t2} ({d2*100/t2:.3f} %)")
print()

data=open(sys.argv[1],'rb').read()
payload=data[int(sys.argv[2],0):]
d,t,seen = dupstat(payload)
print(f"PAYLOAD: {d} Duplikate von {t} ({d*100/t:.3f} %)")
print("\nTop-20 wiederholte 8-Byte-Bloecke:")
for blk,cnt in seen.most_common(20):
    print(f"   {cnt:6d}x  {blk.hex(' ')}   {blk!r}")

# unaligned check: gleitendes Fenster
seen2=collections.Counter(payload[i:i+8] for i in range(len(payload)-7))
d3=sum(v-1 for v in seen2.values() if v>1)
print(f"\nUNALIGNED (gleitend, Schrittweite 1): {d3} Duplikate von {len(payload)-7}"
      f" ({d3*100/(len(payload)-7):.3f} %)")
print("Top-10 unaligned:")
for blk,cnt in seen2.most_common(10):
    print(f"   {cnt:6d}x  {blk.hex(' ')}")

# Wie viele *verschiedene* Bloecke -> Dictionary-Groesse
print(f"\nVerschiedene aligned 8-Byte-Bloecke: {len(seen)} von {t}")
once = sum(1 for v in seen.values() if v==1)
print(f"davon nur einmal vorkommend: {once}")
