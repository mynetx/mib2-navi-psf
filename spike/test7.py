#!/usr/bin/env python3
"""Test 7: Umbiegung innerhalb desselben Serienbands -- 6 Byte, kein Wachstum.

Stand nach den Tests 4-6:
  Test 4  Datei wuchs +47.346 B                      -> ABGEWIESEN (sauber)
  Test 5  Block A +18 B in place  UND  Umbiegung
          @0x36ce94a -> @0x3392334 (Band 280k -> 1,2M) -> ABSTURZ des MIB
  Test 6  nur Laengenfeld +18, Block unangetastet    -> AKZEPTIERT, Anzeige normal

Test 6 entlastet das Laengenfeld. Der rekomprimierte Strom ist durch den
akzeptierten §6-Bau entlastet (dort ist @0x36ce94a eine Python-Rekompression
und wird gerendert). Bleibt die Umbiegung.

Test 7 macht *nur* die Umbiegung, und zwar innerhalb desselben Serienbands:
@0x36ce94a (5. Feld 279.612, Byte+20 = 1) zeigt auf @0x36ca22e (287.708,
Byte+20 = 1) statt auf @0x3392334 (1.200.115, Byte+20 = 2). Im Band 270k-300k
kommt Byte+20 = 2 in keinem der 184 Bloecke vor.

Ablesen: z1-z9 zeigt heute `Hausbaz` aus dem Opferblock. Danach rendert der
Westkachel-Slot den Ostkachel-Block -- `Hausbaz` muss verschwinden.
  akzeptiert -> Umbiegung im Band ist sicher; dann Test 8 (unten)
  Absturz    -> Umbiegung in Format-A-Records ist per se unsicher; dann bleibt
                nur Bearbeitung ohne jedes Opfer

Test 8 danach: Block A auf 18.222 B wachsen lassen UND das Opfer auf A
umbiegen. Dann rendert der Westkachel-Slot A' -- und z1-z9 muesste `RELOBAY`
zeigen. Das ist der erste Bau mit sichtbarem Marker auf einer Stufe, die das
Label auch gewinnt.
"""
import struct
BASE='GermanyWest_Basic.patched.psf'; DST='GermanyWest_Basic.t7.psf'
QVIC=0x7b524              # Format-A-Record des Opfers, Offsetfeld
VIC,VLEN=0x36ce94a,12304
NEW,NLEN=0x36ca22e,18204  # Ziel A, unveraendert, gleiches Serienband

b=bytearray(open(BASE,'rb').read()); a=bytes(b)
assert struct.unpack_from('<IH',b,QVIC)==(VIC,VLEN)
assert struct.unpack_from('<IH',b,0x7b50c)==(NEW,NLEN), "Ziel A nicht im Originalzustand"
struct.pack_into('<IH',b,QVIC,NEW,NLEN)
open(DST,'wb').write(bytes(b))
o=bytes(b)
print(f"Record @0x{QVIC-16:x}: @0x{VIC:07x}/{VLEN} -> @0x{NEW:07x}/{NLEN}")
print(f"Groesse {len(o)} (unveraendert: {len(o)==len(a)})")
print(f"geaenderte Bytes: {sum(1 for i in range(len(a)) if a[i]!=o[i])}")
print(f"Blockinhalte: unangetastet. Nichts ueberschrieben. Datei waechst nicht.")
print(f"Verweise auf @0x{VIC:07x} nach der Aenderung: {o.count(struct.pack('<I',VIC))}")
