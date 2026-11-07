# `.psf`-Format der VW/Audi MIB2-Navi-SD — Reverse Engineering

**Datenträger:** 8 GB FAT32, `DBInfo.txt`: PartNumber `8V0060866M`, SW `0094`,
SystemName `ECE 2020/21`. HERE/NavTeq, NDS-Format. Build-Zeitstempel im
Dateikopf `0x5DF14EDB` = 12.12.2019. Dateidatum 28.08.2024.
**Frei auf der SD: 43 MiB von 7,5 GiB.**

## Kurzfassung

Die `.psf`-Dateien sind **nicht verschlüsselt**. Gelöst und verifiziert:
Container, Indexlayouts, Kachelkennung, **Georeferenzierung**, Blockrahmen,
Koordinatenauflösung, Polylinien-Deltakodierung — und seit dem 10.09.2026 der
**`_Basic`-Index samt Blockoffsets und -längen im Klartext (§6b)**, seit dem
17.09.2026 die **absolute Platzierung der Polylinien und das Quantum** (§6i,
§6j) und seit dem 18.09.2026 die **Deltageometrie auch geräteseitig** (§6j,
Geometrietest). Blöcke lassen sich im Fahrzeug nachweislich aus dem Index
nehmen, umbiegen (§6d Test 3, §6h Test 7) und beliebig umschreiben, solange die
Länge stimmt (§6h Test 11). Ob sie auch **wachsen** oder **verschoben** werden
dürfen, ist offen — die Tests dazu sind an einem eigenen Skriptfehler gestorben
(Gotcha 1). Offen außerdem: die Feldsemantik der bit-gepackten Nutzrecords und
die Geometrie der `f=0x10`-Records.

---

## Gotchas — erst lesen, dann bauen

**1. `lzma.compress` schreibt einen kaputten 13-Byte-Kopf.** Das hat die
Fahrzeugtests 4, 5, 8, 9 und 10 gekostet (vier Abstürze des MIB, eine
Ablehnung), ohne dass eine davon etwas über ihre eigentliche Frage aussagt.

```
Original:       5d f3 4f 00 00  f3 4f 00 00 00 00 00 00   dict=20467  size=20467
lzma.compress:  5d 00 60 00 00  ff ff ff ff ff ff ff ff   dict=24576  size=2^64-1
```

`dict_size` wird auf die nächste liblzma-Stufe aufgerundet (die Filtervorgabe
steuert nur den Encoder), und die entpackte Größe steht als *unbekannt* drin.
Beide Felder **nach** dem Komprimieren überschreiben:

```python
o=bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
struct.pack_into('<I',o,1,len(data))      # dict_size == entpackte Groesse
struct.pack_into('<Q',o,5,len(data))      # size      == entpackte Groesse
chk=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
assert chk.decompress(bytes(o))==data and len(chk.unused_data)==0
```

**Pflichtprüfung vor jedem Fahrzeugtest:**

```
python3 validate.py GermanyWest_Basic.<bau>.psf     # 0 Fehler = fahrbereit
```

`validate.py` prüft alle hier gelisteten Invarianten über alle 76.003 Blöcke in
Sekunden. Nachgewiesen: `t10` (der Bau, der abstürzte) fällt mit 8 Fehlern
durch, `t11` und `p1` (beide im Fahrzeug bestätigt) bestehen mit 0. Die
Warnungen über tote Bytes in fünf Regionen und Doppeleinträge sind erwartet
(§6g, §6-Bau). Referenz für den Blockbau: `test11.py`, `build()`.

**2. Drei Invarianten, an allen 76.003 Blöcken gemessen** (`blockmap.py`) — wer
eine davon bricht, testet nicht mehr seine eigene Frage:

| Invariante | Messung |
|---|---|
| props-Byte | **93 ausnahmslos** (lc=3, lp=0, pb=2) — kein Ausreißer in der ganzen Datei |
| `dict_size` | **immer == entpackte Größe** |
| Extent − Stromlänge | 0 bei 58.807, exakt 14 bei 17.185 (Format-C-Record, §6b); dazwischen nur **5 Blöcke** |

`pb=0` komprimiert besser, ist aber ein Verstoß gegen die einzige Konstante,
die die Datei ausnahmslos einhält — eingebettete LZMA-Dekoder haben `lc/lp/pb`
oft fest kompiliert. Nicht benutzen.

**3. `gw_anchors.pkl` führt als „Länge" den Ankerabstand, nicht die
Stromlänge.** Bei 17.196 Blöcken weichen sie ab (§6g). Für echte Längen
`gw_blockmap.pkl` benutzen.

**4. AppleDouble-Dateien.** Nach jedem Schreiben auf die Karte
`find "/Volumes/NO NAME" -name '._*' -delete`. macOS legt sie auf FAT32 an,
weil die Quelldatei ein `com.apple.provenance`-xattr trägt; `xattr -c` entfernt
das nicht. Eine `._`-Datei im Kartenverzeichnis macht den Test unauswertbar —
so ist Test 4 einmal verbrannt worden (§6d).

**5. Records nie ohne Längenpräfix in Sektion 16 schieben.** Die
Straßensektion ist eine Kette `u16 L │ Rumpf` mit Gruppenindex davor (§6l).
`e1` hat sie verletzt, danach stürzte das Gerät ab. Immer
`sec16.named()` + `sec16.insert()`/`replace()`; `validate.py` [12] prüft es.

---

## 1. Container

```
0x000    Header (uint32 LE ab Offset 2; erste zwei Felder 0x3c/0xf2 konstant;
         Build-Zeitstempel als Unix-Zeit)
~0x102   Indextabelle, Stride je Content-Typ
danach   Datenblöcke, jeder ein LZMA-alone-Stream
```

### Blockformat: LZMA-alone, 13-Byte-Header

```
Byte  0     0x5D          LZMA properties (lc=3, lp=0, pb=2)
Bytes 1-4   uint32 LE     dictSize
Bytes 5-12  uint64 LE     uncompressedSize
Bytes 13+   LZMA1-Stream
```

`dictSize == uncompressedSize` in allen geprüften Blöcken.

**Verifikation:** `Malta_AdvancedRouting.psf` → **125/125 Blöcke** fehlerfrei mit
`lzma.FORMAT_ALONE`, Ausgabelänge jedes Mal exakt `uncompressedSize`.

`0x5D` + Längenpaar ist ein starker Anker: Blöcke lassen sich auch ohne
Indexkenntnis zuverlässig finden. Die exakte komprimierte Länge liefert
`LZMADecompressor.unused_data`.

### Indexlayouts

| Content-Typ | Tabelle @ | Stride | Layout |
|---|---|---|---|
| `_AdvancedRouting` | 0x102 | 20 | `u32 offset, u32 len, u32 key, 8 B reserved` |
| stride-24 (`MountainPolygons`, `WorldCartographicLayer_Basic`) | 0x10e | 24 | `u32 offset, u16 len, u16 counter, 16 B` |
| `_Basic` | 0x32e | 32 | `key @+4, offset @+8` — **zweistufig** |

stride-24 verifiziert über `offset + len == offset des nächsten Blocks`:
**77/77** (MountainPolygons), **10/10** (WorldCartographicLayer).

`_Basic` ist zweistufig: Maltas erster Datenblock liegt bei Offset 72.670, davor
Platz für höchstens 2.270 Records à 32 B — es gibt aber **5.389 Blöcke**. Der
Kopfindex verweist auf Indexblöcke, die selbst LZMA-komprimiert sind.

---

## 2. Kachelkennung: ein Katalog

```
key = (layer << 21) | (1000 · Regionsnummer + Kachelindex)
```

**Beweis:** die Kachelbasen **aller 52** `_AdvancedRouting`-Regionen sind exakt
Vielfache von 1000 (52/52) — 0, 1000, … 49000, 51000, 52000. Fast jede Region
hat **genau 408 Kacheln**, unabhängig von der Fläche (Ausnahmen: Malta 124,
Island 342, Kaliningrad 362). Unabhängig wiedergefunden in Nutzrecords, wo
`59 c7 80` als u32 `0x0080c759` ergibt = Layer 4, Kachel 51033, also Malta
(Basis 51000) Index 33.

Regionsnummern (HERE-intern, 50000 unbelegt; vollständig via `allbases.py`):

| Nr | Region | Nr | Region |
|---|---|---|---|
| 0 | IrelandGreatBritainNorth | 25000 | Finland |
| 1000 | GreatBritainSouth | 28000 | Portugal |
| 2000 | Norway | 33000 | Albania |
| 4000 | Denmark | 42000 | Turkey |
| 5000 | GermanyNorth | 46000 | Kaliningrad |
| 6000 | GermanyWest | 49000 | RussiaEast |
| 9000 | GermanySouth | 51000 | Malta |
| 15000 | ItalyNorth | 52000 | Iceland |

---

## 3. Georeferenzierung — gelöst

### `_Basic`-Blockkopf = Bounding Box in Mercator-Metern

```
+0   int32 LE   minX      x = R · λ
+4   int32 LE   minY      y = R · ln(tan(π/4 + φ/2))
+8   int32 LE   maxX
+12  int32 LE   maxY
+16  uint16     Blockgröße        (2256/2263 = 99,7 %)
```

### Erdradius, geschlossen bestimmt

Kacheln sind **gradquadratisch**, also `Δλ == Δφ`. Daraus `cos(φ) = Breite/Höhe`
— der Breitengrad **ohne** Kenntnis von R — und `R = y / ln(tan(π/4 + φ/2))`.
Median über **8.830 unabhängige Kachelschätzungen**:

```
R = 6.370.917 m      Erdmittelradius = 6.371.000 m      Abweichung 0,0013 %
```

Also **sphärischer Mercator mit R = 6.371.000 m** (nicht WGS84 6.378.137).

Beweis über Breitengrade hinweg — `Höhe/Breite = 1/cos(φ)`:

| Region | Breite | Höhe | gemessen | 1/cos(φ) |
|---|---|---|---|---|
| Malta (36°) | 4886 | 6048 | 1,238 | 1,235 |
| Portugal (39,5°) | 2442 | 3141 | 1,286 | 1,295 |
| Dänemark (56°) | 2445 | 4390 | 1,795 | 1,789 |
| Island (65°) | 2443 | 5908 | 2,419 | 2,366 |

### Kachelraster

Kachelgrenzen sind exakte Binärbrüche von 360°: Level L → Breite `360/2^L`.
`14,0625 = 40 × 0,3515625`, `35,859375 = 102 × 0,3515625`, auf den Bruchteil
genau. **99,7 % (2586/2595)** der Westkanten liegen innerhalb 2 % einer
Rastergrenze (Zufall: 4 %). `2πR/2^14 = 2443,22 m` trifft die beobachtete
Basisbreite 2442–2445.

Malta: 2.595 Kacheln, **Level 6–15**, Verteilung 5/12/27/92/194/369/489/693/712.

### Unterzellen-Index in groben Kacheln

Grobe Kacheln enthalten ein Array absoluter Mercator-Koordinatenpaare (int32,
Stride 8), Anzahl **exakte Viererpotenz** (1024, 256, 64, 16), in **Z-Order**,
Schrittweite `360/2^14`. Für eine L9-Kachel: 32×32 = 1024 Unterzellen.
Rastertreue **1024/1024**, Z-Order **1024/1024**. Dahinter ein gleich großes
Array aus reinen Nullbytes (leere Referenzen).

Zufallserwartung für die Koordinatenpaare: 0,000018. Gefunden: 1024.

### NDS-kompatibel

`nds_level = L - 1`, Kachelnummer = Morton-Interleave von (col, row) mit col in
den geraden Bits, `packed_id = tileNr + (1 << (16 + nds_level))`.
Gegen die (an Barcelona validierte) Referenz geprüft: **6/6 exakt**.

```
L12 col164 row408 -> nds_level 11, tileNr 181904, packedId 134399632
   eigene BBox  lon[14.4141,14.5020] lat[35.8594,35.9473]
   nds.py-BBox  lon[14.4141,14.5020] lat[35.8594,35.9473]
```

### Inhaltliche Gegenprobe

- südliche Kachel (lat 35,16–35,86) → `Triq Birżebbuġa` (liegt im Süden)
- nördliche Kachel (lat 35,86–36,21) → `Triq Burmarrad` (liegt im Norden)
- POI-Test: Mdina 5/5, Marsaxlokk 5/7, Victoria 5/8 Namenskacheln enthalten den
  Punkt auch geografisch

---

## 4. Blockinneres

### `_AdvancedRouting`

```
Byte 0      N   = Anzahl der Records
Byte 1-2        Deskriptor (Byte 2: 0x00 → 2-Byte-Records, 0x02 → 5-Byte-Records)
Byte 3..        N × uint16 Offset
ab 3+2N         N × Record fester Größe
```

Erster Tabelleneintrag immer genau `3 + 2N`. Verifiziert an 5 Blöcken:

| Block | Kopf | N | Rec | Rechnung = Blockgröße |
|---|---|---|---|---|
| Malta L2 | `08 38 00` | 8 | 2 | 19 + 16 = 35 ✓ |
| Malta L3 | `a3 38 02` | 163 | 5 | 329 + 815 = 1144 ✓ |
| Malta L4 | `ac 38 02` | 172 | 5 | 347 + 860 = 1207 ✓ |
| Albanien L0 | `fc 37 00` | 252 | 2 | 507 + 504 = 1011 ✓ |
| Albanien L2 | `86 37 02` | 134 | 5 | 271 + 670 = 941 ✓ |

### Polylinien in Blattkacheln

Direkt hinter dem Kopf stehen **byte-aligned int8-Deltapaare (dx, dy)**.
Richtungskohärenz `Netto/Weglänge` über viele Läufe: **0,62–0,91**, bei Random
Walk 0,10–0,24. Vier- bis achtfach über dem Zufall.

**Koordinatenfeldbreite: OFFEN.** Frühere Fassungen behaupteten hier 10 Bit —
**das war nicht bewiesen.** Beobachtet ist nur, dass die Ausdehnung *einzelner*
Polylinien in 2074/2075 Läufen unter 1024 bleibt. Das ist mit 10 Bit vereinbar,
aber genauso mit breiteren Feldern und einfach kurzen Straßen. Eine einzelne
Straße muss die Kachel nicht durchqueren, also lässt sich N so nicht bestimmen.

Indiz gegen 10 Bit: bei L11 (19.548 m Kachel) wären das 19 m/Einheit; das Navi
zeigt auf der tiefsten Zoomstufe aber brauchbares Detail aus L11-Daten. Wären
es 14 Bit, ergäbe das 1,19 m, bei 16 Bit 0,30 m.

Zum Bestimmen von N braucht es die absolute Platzierung — die kollektive
Ausdehnung aller Polylinien einer Kachel muss die Kachel ausfüllen.

### Zweiter Blocktyp (angefangen)

Signatur: Byte 1 immer `0x80`/`0x81` (Varint-Fortsetzung), Byte 5-6 `38 00`,
Byte 9-11 `10 16 00`. Enthält Tag-Records:

```
21 00 | a8 a9 | 9e | 59 c7 80      8 Byte, mit Kachelreferenz
20 00 | b8 b9                      4 Byte, ohne
```

Die Paare wandern glatt (168,169) (166,168) (165,164) — **8-Bit-Koordinaten
innerhalb einer Zelle**. `59 c7 80` = Kachelkennung (siehe §2).

In `GermanyWest_Basic.psf` erkennt die Kachelheuristik nur 5.681 von 76.003
Blöcken. **Achtung, häufiger Fehlschluss:** daraus folgt *nicht*, dass die
tiefen Level in diesem zweiten Typ liegen. Über Testort sind alle
namenstragenden Blöcke reguläre L10/L11-Kacheln (siehe §6a). Der zweite Typ
ist noch unbestimmt.

---

## 5. Was heute funktioniert

### Namen pro Kachel mit Koordinaten

`Malta_Basic.psf`: 3,3 MB → 5.389 Blöcke → 7,9 MB entpackt. **4.850
verschiedene maltesische Straßennamen** in **UTF-8**:

```
Triq A. Caligari · Triq Ħaż-Żabbar · Sqaq il-Qaċċawiet · Misraħ Menqa
```

Die Karte führt jeden Namen **doppelt** — mit Diakritika und als
ASCII-Fallback. Ergebnisdateien: `Malta_tiles.geojson` (2.007 Polygone mit
`nds_packed_tile_id`), `Malta_tile_names.csv` (510 Namen mit BBox).

### Ortszuordnung

Namen stehen als UTF-8-Klartext in den Blöcken, damit ist die Regionsdatei
empirisch bestimmbar. Ergebnis für die Zielorte:

| Datei | Testort | Ortbeta (Region) | Niederortbeta | Oberortbeta |
|---|---|---|---|---|
| **GermanyWest_Basic.psf** | 8 Blöcke | 6 | 11 | 9 |
| GermanySouth_Basic.psf | – | – | – | – |
| GermanyNorth / GermanyEast | – | – | – | – |

GermanySouth hat nur grobe Übersichtskacheln (Level 6–8) über den Orten, aber
keinen Namenstreffer. **Detaildaten ausschließlich in GermanyWest.**

### Sonstiges auf der SD

- `vde/common/vde_grammar_plugin/**/*.db`: **reines SQLite**, 47 Länder,
  **916.245 Orte**, **5.379.659 Straßennamen** EU-weit, plus Exonyme
  (Aachen → Aix-la-Chapelle, Cáchy, Ахен), Bundesländer, PLZ. Nur Namen, keine
  Koordinaten, Auflösung nur Land. Direkt abfragbar.
- Phonetik für die Sprachbedienung liegt in eigenen Blöcken, SAMPA-artig:
  `"haUs|baI|6 "Stra:|s@` = „Testorter Straße".
- `map/styles/{1..4}` (Audi/VW/Škoda/SEAT): 5.446 PNGs, 13 TTFs, Zoomparameter.
- `styles/*/resources/strings/*.xml`: POI-Kategorien in 17 Sprachen samt
  Sprachbedienungs-Synonymen.

### Regionsinventar

54 Regionen, 161 Dateien, 6 Content-Typen: `Basic` (41),
`BasicWithPointAddress` (12), `AdvancedRouting` (52), `GlobalPOIIndices` (52),
`ExtZips` (3), `MountainPolygons` (1).

---

## 6. Akzeptanztest — BESTANDEN

**Ergebnis vom 09.09.2026: das Gerät akzeptiert veränderte `.psf`-Dateien.**
Kein Prüfsummen- oder Signaturmechanismus. Der Schreibweg ist offen; die
verbleibenden Hürden sind ausschließlich Formatverständnis.

### Was getestet wurde

Ortsname `Testort` → `TESTBAY` (beide 7 Bytes) in den zwei Blöcken mit
Kompressionsspielraum, Grid-Level 10. Dateigröße byte-genau identisch
(79.319.126 B), Index unberührt, alle 76.003 Blöcke dekomprimierbar. Nur die
eine Datei auf die Original-SD kopiert.

### Beobachtung im Auto

- **2D-Übersicht: `TESTBAY` erscheint.** → Akzeptanz bewiesen.
- Danach **11 weitere Zoomstufen**, auf allen erscheint weiter `Testort`.

Die gepatchten Blöcke bedienen also nur die Übersichtsstufe. Die 11 tieferen
Stufen kommen aus den restlichen Blöcken mit dem Namen.

### Warum die tiefen Stufen nicht patchbar sind

`Testort` steht in **8 Blöcken**. Spielraum = wie viel besser liblzma den
unveränderten Inhalt komprimiert als der Original-Encoder:

| Block | entpackt | komprimiert | Spielraum | Status |
|---|---|---|---|---|
| @0x2f34830 | 23.518 | 16.494 | **+11** | gepatcht → `TESTBA1` |
| @0x2f4009f | 27.823 | 15.490 | **+8** | gepatcht → `TESTBA2` |
| @0x36ce94a | 17.468 | 12.304 | **−2** | gepatcht → `Hausbaz` (Minimalmutation) |
| @0x36ca22e | 25.564 | 18.204 | −10 | nicht möglich |
| @0x3392334 | 20.467 | 13.832 | −21 | nicht möglich |
| @0x346c45e | 21.604 | 15.241 | −23 | nicht möglich |
| @0x29d48b8 | 9.073 | 2.756 | −5 | Phonetikblock, ohnehin unsichtbar |
| @0x3b25e2a | 152 | 104 | −5 | nicht möglich |

**Trick, der ein weiteres Blockpatch ermöglichte:** `Testort` → `Hausbaz` ändert
nur das letzte Byte, der 6-Byte-Präfix bleibt matchbar. Kostete bei @0x36ce94a
exakt 0 Bytes und passte damit in −2 Spielraum. `TESTBAY` ersetzt alle 7 Bytes
und zerstört jeden Match.

**Gleichlängen-Methode ist ausgeschöpft.** Kein Encoder schlägt das Original auf
den restlichen Blöcken:

| Encoder | @0x346c45e (Original 15.241) |
|---|---|
| liblzma, breiter Sweep (5 mf × 6 depth × 6 nice) | 15.257 (−16) |
| xz CLI, preset 9e, getunt | 15.284 (−43) |
| 7-Zip LZMA SDK (mit Container-Overhead) | 15.388 |

→ Die restlichen 5 Blöcke gehen **nur über einen schreibbaren Index**.

### Aktueller Stand von `sdtest/`

Drei Blöcke gepatcht mit **unterscheidbaren Markern**, damit die Anzeige im Auto
verrät, welcher Block welche Zoomstufe bedient:

| Block | Marker | Typ |
|---|---|---|
| @0x2f34830 | `TESTBA1` | Grid-L10-Kachel |
| @0x2f4009f | `TESTBA2` | Grid-L10-Kachel |
| @0x36ce94a | `Hausbaz` | **kein erkannter Kacheltyp** (zweiter Blocktyp) |

Der dritte ist diagnostisch wertvoll: erscheint `Hausbaz` auf einer tiefen
Zoomstufe, ist damit belegt, dass der zweite Blocktyp die tiefen Level bedient.
Dateigröße identisch, alle 76.003 Blöcke dekomprimierbar.

Ein erneuter Kartentest ist optional — er bringt 1 von 6 fehlenden Blöcken. Der
Ertrag kommt, wenn der Index schreibbar ist und alle Vorkommen patchbar sind.

## 6a. Zoomstufen-Zuordnung — im Fahrzeug gemessen (09.09.2026)

Zweiter Kartentest mit **unterscheidbaren Markern pro Block**. Beobachtung von
nah nach weit, 12 Zoomstufen:

| Zoom | Marker | Block | Level | lon-Bereich | Testort drin |
|---|---|---|---|---|---|
| z1–z8 | **`Hausbaz`** | @0x36ce94a | L11 | 7,3–7,5 | **nein** (Nachbar West) |
| z9–z11 | `Testort` | @0x36ca22e / @0x346c45e / @0x3392334 | L11 | – | teils |
| z12 | **`TESTBA2`** | @0x2f4009f | L10 | 7,3–7,7 | ja |

### Was daraus folgt

- **`TESTBA2` gewinnt gegen `TESTBA1`.** Block @0x2f4009f liefert die
  Beschriftung, @0x2f34830 ist ein anderer Layer derselben L10-Kachel und
  liefert keine Labels.
- **Kacheln existieren in Layer-Paaren.** Über Testort: zwei L10-Blöcke mit
  identischer BBox (@0x2f4009f, @0x2f34830) und je zwei L11-Blöcke pro
  L11-Kachel (@0x36ce94a+@0x3392334 West, @0x36ca22e+@0x346c45e Ost).
- **Level 11 ist die tiefste Datenstufe über Testort** — eine 19,5-km-Kachel
  bedient acht Zoomstufen. Malta hat bis L15; hier endet es bei L11.
- **Das Label bei z1–z8 kommt aus der Nachbarkachel westlich von Testort.** Der
  Renderer zeichnet offenbar Ortslabels aus angrenzenden Kacheln mit. Nicht
  weiter geklärt.

### Korrektur eines eigenen Fehlschlusses

Eine frühere Fassung behauptete, @0x36ce94a sei „vom unbekannten Blocktyp" und
dort lägen die tiefen Level. **Falsch.** Der Block hat `u16 @0x10 == Blockgröße`
und eine gültige Mercator-BBox mit 19.548 m Breite — eine reguläre
L11-Kachel. Er fehlte nur in meiner Testort-Liste, weil der Filter Kacheln
verlangt, die den *Punkt* enthalten; diese Kachel liegt 6,8 km westlich davon.

### Konsequenz für die nächste Runde

Für z1–z11 sind drei Blöcke zu patchen: @0x36ca22e (−10 B), @0x3392334 (−21 B),
@0x346c45e (−23 B). **Alle mit negativem Spielraum**, und kein Encoder schlägt
das Original (§6). Der Weg führt zwingend über den schreibbaren
`_Basic`-Index der zweiten Stufe — das ist Priorität 1.

## 6b. `_Basic`-Index gelöst — die Blocklänge ist keine Zwangsbedingung mehr (10.09.2026)

> **Stand 17.09.2026:** der Titel ist zu stark. Dass ein Block verschoben
> oder verlängert werden darf, ist **nicht belegt** — der Test dazu (§6d Test 4)
> ist an Gotcha 1 gestorben. Belegt sind die Recordformate und dass der
> Klartextindex maßgeblich ist.


**Kernergebnis: die `(Offset, Länge)`-Paare stehen im Klartext in der Datei.**
Der bisher als Engpass geführte „komprimierte Index der zweiten Stufe" ist für
die entscheidenden Blöcke gar nicht zuständig. Damit fällt die Bedingung
„gepatchter Block darf nicht länger werden" weg.

### Zwei Recordformate, beide unkomprimiert

**Format A — Kachelrecord, 24 B** (Bereich um 0x74000–0x7c000):

```
+0   int32 LE  minX          Mercator-Meter, R = 6.371.000
+4   int32 LE  maxY
+8   int32 LE  maxX
+12  int32 LE  minY
+16  uint32 LE Blockoffset   absolut in der Datei
+20  uint16 LE Blocklänge    komprimiert
+22  uint16    Flags         0 (95 %), 1, 2, 3
```

Verifikation an **5.558 Records** mit Rasterbreite `2πR/2^L`:
Reihenfolge maxY vor minY **5.557/5.558 (99 %)**; `(Höhe/Breite)/(1/cos φ)`
Median **0,9999**, 98 % innerhalb 2 %. Das ist derselbe Test wie §3, aber am
*Index* statt am Blockkopf — die Kachelgeometrie ist also lesbar, **ohne einen
einzigen Block zu entpacken**. Levelverteilung L5–L15, Schwerpunkt L12–L14.

**Format B — Layerpaar-Record, 32 B** (Bereich ab 0x10e):

```
+0   uint32 LE Kennung       (layer<<21) | (1000·Region + Kachelindex)
+4   uint32 LE Offset A
+8   uint16 LE Länge A
+10  uint32 LE Offset B
+14  uint16 LE Länge B
+16  16 B      BBox wie oben
```

Verifikation: `Offset + Länge == Offset des vorherigen Records` für **794**
aufeinanderfolgende Records in beiden Spalten gleichzeitig (die Tabelle läuft
in absteigender Offsetrichtung). Kennung des ersten Records `0x03001790` =
Layer 24, 6032 = Region GermanyWest (Basis 6000) + Kachel 32, danach
absteigend. Das ist die Registrierung der in §6a beobachteten **Layerpaare**.

**Format C — 14-B-Record zwischen den Datenblöcken:**
`01 00 00 00 00 00 00 03 | uint32 Offset | uint16 Länge`. Steht bei 23 % der
Blöcke direkt hinter dem LZMA-Strom. **Korrektur:** in einer früheren Messung
sah das wie 14 B Füllmaterial aus — es ist keines, dort ist nichts frei.

### Abdeckung

| | |
|---|---|
| Blöcke gesamt | 76.003 |
| mit Klartext-`(Offset, Länge)` | **42.222 (55 %)** |
| davon Fundstelle im Kopfbereich | 38.246 Stellen |
| davon zwischen den Datenblöcken | 17.223 Stellen |
| ohne Eintrag | 33.781, davon 33.179 unter 1 kB |

Die nicht referenzierten Blöcke sind fast alle winzig (bis 19 B komprimiert /
1 B entpackt) und liegen im Dateiende ab ~61,7 MB — ein eigener Abschnitt, der
anders adressiert wird. **Alle acht Testort-Blöcke bis auf einen** (@0x3b25e2a,
104 B) haben einen Eintrag, und zwar **genau einen in der ganzen Datei**.

### Dateikopf

- `@0x04d uint32` = **exakt die Dateigröße** (79.319.126). Wer die Datei
  wachsen lässt, muss dieses Feld mitziehen.
- Am Dateiende hängt eine **verkettete Metadatensektion**, jeweils
  `Offset` im Kopf und `Länge` 4 B dahinter:
  `79.314.569 (+132) → 79.314.701 (+1481) → 79.316.182 (+2682) →
  79.318.864 (+262) → 79.319.126 = EOF`. Vier Glieder, arithmetisch exakt,
  Kopfoffsets 0x096, 0x00a, 0x07a, 0x035, 0x04d.

### Konsequenz: Blockverschiebung statt Größenerhalt

Ein zu langer Block wird ans Dateiende gehängt, sein Indexeintrag umgeschrieben.
Die alten Bytes bleiben stehen (schadet nichts, dient als Rückfallebene).

`relopatch.py` baut `GermanyWest_Basic.reloc.psf`. Marker **`RELOBAY`** nur in
den drei bisher unerreichbaren Blöcken, alles andere Original:

| Block | Vorkommen | alt komp | neu komp | Δ | neu @ |
|---|---|---|---|---|---|
| @0x36ca22e | 1× | 18.204 | 18.222 | +18 | 0x4ba5056 |
| @0x3392334 | 2× | 13.832 | 13.857 | +25 | 0x4ba9784 |
| @0x346c45e | 2× | 15.241 | 15.267 | +26 | 0x4bacda5 |

Datei 79.319.126 → 79.366.472 B (+47.346), Größenfeld nachgezogen. Verifiziert:
alle **76.003** Blöcke des Originalbereichs weiter dekomprimierbar, jeder der
drei Indexeinträge löst auf den neuen Block auf, entpackte Größe unverändert,
`Testort` dort 0×.

### Was der nächste Fahrzeugtest beantwortet

Erscheint auf **z9–z11** `RELOBAY`, ist bewiesen:
Index wird gelesen, Blöcke dürfen verschoben und beliebig lang werden, die
Datei darf wachsen. Damit ist der Schreibweg vollständig offen und das
Restproblem nur noch Recordsemantik (§4).

Bleibt es bei `Testort`, ist zu trennen: Größenfeld @0x04d falsch mitgezogen,
oder Daten jenseits der ursprünglichen Dateilänge werden nicht gelesen. Dann
ist die Gegenprobe, die Blöcke *innerhalb* der alten Dateigrenze
unterzubringen — dafür müssten Blöcke des Endabschnitts weichen.

**Ungetestet ist ausschließlich die Gerätereaktion.** Der Aufbau der Datei ist
verifiziert.

## 6c. Endabschnitt = Namensindex (10.09.2026)

Der in §6b als „ohne Klartext-Indexeintrag" übrig gebliebene Dateiteil ist
identifiziert.

**Grenze:** Block **#54408 @0x4031174 (67,31 MB)**. Ab dort 21.595 Blöcke,
12,0 MB komprimiert / 18,1 MB entpackt, Median 154 B komprimiert — viele
winzig (kleinster: 19 B komprimiert, 1 B entpackt).

**Korrektur zu §6b:** dort stand „ab ~61,7 MB". Das kam aus einer nach Länge
sortierten Laufstatistik, deren Reihenfolge ich verloren hatte. Richtig ist
67,31 MB.

### Aufbau

Zeichenketten liegen im **3-Byte-Raster `<char> <uint16>`**, Großbuchstaben,
Latin-1 (`ß` = 0xdf, `Ö` = 0xd6). Beispiel aus Block #74408:

```
06 00 41 b3 01 45 53 04 49 93 07 4f cb 0a 55 c9 0c d6 02 00
42 02 00 45 02 00 4e 02 00 41 02 00 55 02 00 45 02 00 52 ...
      B        E        N        A        U        E     R
```

Das ergibt gelesen `…BENAUER STRASSE`. Die `uint16` hinter jedem Zeichen ist
mal 2 (lineare Fortsetzung), mal größer (Verzweigung, offenbar Zeiger auf
einen anderen Block des Abschnitts — `41 b3 01` = `A` → 435 → Block #54843).
**Die Kopf-Semantik ist noch nicht bestimmt:** die führende `06 00` passt
weder auf „6 Kinder" noch auf „6 Bytes Rumpf". Ohne sie ist der Trie nicht
sauber traversierbar.

### Was drinsteht — und was nicht

Gezielte Suche nach langen, spezifischen Ketten:

| gesucht | Treffer | Beispiel |
|---|---|---|
| `BOPPARD` | 13 | |
| `KOBLENZ` | 12 | |
| `LIMBURG AN DER LAHN` | 9 | |
| `ORTBETA` | 4 | `ORTBETA  REGION`, `ORTBETAER STRASSE` |
| `NACHBARSTADT` | 1 | |
| `STRASSE` | 139 | |
| **`TESTORT`** | **0** | auch `TESTORTER`, `AUSBAY`, `USBAY`, `SBAY`: 0 |
| `NIEDERORTBETA` / `OBERORTBETA` | 0 / 0 | |

Nachbarorte gegen die vde-SQLite gehalten — dort sind **alle** verzeichnet:

| | vde-DB | Trie | | vde-DB | Trie |
|---|---|---|---|---|---|
| Boppard | 1 | 13 | Testort | 1 | **0** |
| Leiningen | 1 | 8 | Nachbarort | 1 | 0 |
| Nachbardorf B | 1 | 4 | Dörfchen | 1 | 0 |
| Ortsgamma | 1 | 3 | Utzenhain | 1 | 0 |
| Nachbarstadt | 1 | 1 | Dörth | 1 | 0 |

Es ist also **kein reiner Größenfilter** — Ortsgamma (≈1.100 Ew.) steht drin,
Testort (≈450) nicht. Die wahrscheinlichere Lesart: der Trie indiziert
**Straßennamen**, und die Ortstreffer sind Ableitungen daraus
(`BOPPARDER STRASSE` enthält `BOPPARD`). Dazu passt, dass `TESTORTER` fehlt,
obwohl die vde-DB `Testorter Straße` kennt (Street 181336).

**Für Ziel 3 heißt das:** Testort ist in der Sprach-/Zieleingabe-DB vorhanden
(`common_Germany_v1.db`, Area 18833) — der Ort ist eingebbar. Was in der
`.psf` fehlt, ist der Straßenindex. Ob Wege auf dem Campingplatz überhaupt
über diesen Trie erreichbar gemacht werden müssen, hängt am ausstehenden
Fahrzeugtest.

## 6d. Fahrzeugtests 10.09.2026 — zwei Ergebnisse, ein Fehlversuch

> **Stand 17.09.2026:** Test 1 und 4 sind durch Gotcha 1 entwertet, Test 2
> und 3 gelten. Bilanz aller Tests: §6h.


### Test 1: Blockverschiebung ans Dateiende (`RELOBAY`) — ABGEWIESEN

Gerät: „Legen Sie einen Datenträger mit gültigen Navigationsdaten ein."
Die Datei war 79.366.472 B (+47.346), Größenfeld `@0x04d` nachgezogen, drei
Indexeinträge auf ans Ende gehängte Blöcke umgebogen.

**Störfaktor, nicht auflösbar:** beim Zurückbringen war der
Schreibschutzschieber der SD umgelegt. Ob er schon im Fahrzeug zu war, lässt
sich nicht feststellen. Die Ablehnung ist damit *nicht sicher* der Datei
zuzuschreiben.

Ausgeschlossen wurde: eine Prüfsumme im Dateikopf über Kopf-, Index- oder
Datenbereich (7 Bereiche × crc32/adler32/sum32/xor32, dazu die Variante mit
genulltem Prüffeld — kein Treffer). Und die 262 B am Dateiende sind **keine
Signatur**: Entropie 4,2 bit/Byte, in allen 161 `.psf` gleich aufgebaut.

Verbliebener Hauptverdacht: die Blöcke wurden **hinter** die verkettete
Metadatensektion gehängt. Deren Kette endet in jeder Datei exakt an der
Dateigrenze (§6b) — genau diese Invariante war gebrochen.

### Test 2: Indexeinträge des L10-Layerpaares getauscht — AKZEPTIERT, aber blind

Basis der akzeptierte Bau aus §6, dazu 10 geänderte Bytes: in den beiden
Indexeinträgen über Testort wurden nur Offset und Länge getauscht.

**Ergebnis: Karte akzeptiert.** Anzeige unverändert — z1–z8 `Hausbaz`,
z9–z11 `Testort`, z12 `TESTBA2`.

Daraus folgt **eines** sicher: der **Indexbereich ist nicht integritätsgeprüft**.
Eine Änderung dort führt nicht zur Ablehnung. Der Zweig „Index ist geschützt"
ist erledigt, und der Verdacht auf das Dateiwachstum als Ursache von Test 1
wird dadurch stärker.

**Fehler im Versuchsaufbau (eigener):** der Tausch konnte gar nichts über die
Indexnutzung zeigen. Beide Blöcke des Layerpaares tragen einen Ortsnamen, und
welcher das Label liefert, entscheidet offenbar der Blockinhalt, nicht der
Eintrag. Nach dem Tausch werden weiterhin beide Blöcke geladen, derselbe
gewinnt. Ein Nullergebnis war unvermeidlich.

### Test 3: `TESTBA2` aus dem Index entfernen — ENTSCHIEDEN

**Ergebnis: z12 zeigt nur noch Flächenfarben, keine Linien, keine Beschriftung.**
z1–z8 `Hausbaz`, z9–z11 `Testort`, z13+ normal.

**Der Klartextindex ist maßgeblich.** Der Block, der aus dem Index genommen
wurde, wurde nicht mehr geladen und verschwand aus der Anzeige. Blöcke lassen
sich also verschieben; der Fehlschlag aus Test 1 lag nicht am Index.

**Zusatzbefund zum Layerpaar (§6a):** @0x2f34830 zeichnet die **Flächen**,
@0x2f4009f **Linien und Beschriftung**. Vorher war nur bekannt, dass letzterer
„das Label gewinnt".

### Test 3 — Aufbau

`duptest.py` → `GermanyWest_Basic.dup.psf`. **5 geänderte Bytes** gegenüber dem
akzeptierten Bau: beide Einträge des Layerpaares zeigen auf @0x2f34830
(`TESTBA1`). @0x2f4009f (`TESTBA2`) ist danach von keinem Klartexteintrag mehr
referenziert — in der ganzen Datei geprüft (das eine verbliebene rohe
Offsetvorkommen liegt bei 0x3ab10a3 im komprimierten Datenbereich, Zufall).

| z12 zeigt | Bedeutung |
|---|---|
| `TESTBA1` | der Klartextindex bestimmt, was geladen wird → Verschieben ist der Weg |
| `TESTBA2` | er tut es nicht; Blöcke werden anders gefunden → Verschieben ist tot |

### Test 4: korrigierte Verschiebung — ABGEWIESEN (sauber)

`reloc2.py` → `GermanyWest_Basic.reloc2.psf`. Basis unverändertes Original.
Die drei Blöcke wurden **vor** die Metadatenkette eingefügt (@79.314.569), die
Kette rückte um 47.346 B nach hinten, ihre fünf Kopfzeiger (0x096, 0x00a,
0x07a, 0x035, 0x04d) mitgezogen, drei Indexeinträge umgebogen. 27 geänderte
Bytes vor dem Einfügepunkt.

| | |
|---|---|
| Größe | 79.319.126 → 79.366.472 (+47.346) |
| Erster Fahrzeugtest | abgewiesen — **ungültig**, siehe Störfaktor |
| Zweiter Fahrzeugtest | **abgewiesen** |

**Störfaktor beim ersten Durchgang, gefunden und beseitigt:** im Verzeichnis
`markets/eu/map/MapRegions/` lag genau eine Fremddatei,
`._GermanyWest_Basic.psf` (4.096 B), Zeitstempel derselbe Minutenwert wie die
reloc2-Kopie. macOS legt diese AppleDouble-Datei auf FAT32 an, weil die
Quelldatei ein `com.apple.provenance`-xattr trägt — das lässt sich **nicht**
mit `xattr -c` entfernen. Auf der ganzen Karte gab es sonst kein `._`; die
beiden `.DS_Store` stammen von August 2024 und waren bei allen akzeptierten
Tests dabei, Dotfiles an sich stören also nicht.

Nach Löschen der Fremddatei und **ohne ein Byte an der `.psf` zu ändern**
(79.366.472 B, `62b623ae84ab0746`, gegen die Quelldatei verifiziert) wurde
erneut getestet: **wieder abgewiesen.** Damit gehört die Ablehnung der Datei.

**Folge auch für Test 1:** dort war der Schreibschutzschieber der Störfaktor,
plausibel kam dieselbe `._`-Datei hinzu. Beide „Wachstum abgewiesen"-Befunde
sind einzeln entwertet, zeigen aber zusammen in eine Richtung. Verbliebene
Kandidaten für die Ablehnung von Test 4, unentschieden:

1. Das Dateiwachstum selbst wird geprüft (Feld `@0x04d` war mitgezogen, ein
   externes Manifest ist ausgeschlossen — siehe unten).
2. Einer der fünf mitgezogenen Kopfzeiger ist kein Dateioffset, sondern eine
   Länge oder ein Zähler, und ist jetzt falsch.
3. Innerhalb der verschobenen Metadatenkette stehen absolute Offsets, die
   nicht mitgezogen wurden.

**Externes Manifest ausgeschlossen:** in allen Dateien der SD außerhalb von
`MapRegions` (`DBInfo.txt`, `styles/`, `vde/`) kommt weder die Dateigröße
79.319.126 in irgendeiner Kodierung (le32/be32/le64/dezimal/hex) noch die
Zeichenkette `GermanyWest` vor. Die Regionsdateien werden per
Verzeichnisscan gefunden, ihre Größe steht nirgends geschrieben.

### Regel: AppleDouble-Dateien nach jedem Kopieren löschen

`xattr -c` hilft nicht, `com.apple.provenance` ist ein System-xattr. Also
nach **jedem** Schreiben auf die Karte:

```
find "/Volumes/NO NAME" -name '._*' -delete
```

Ein Fahrzeugtest mit einer `._`-Datei im Verzeichnis ist nicht auswertbar.

## 6e. Vierte Recordform: `[u16 Länge][u32 Offset]` (10.09.2026)

Gefunden beim Vollständigkeitscheck vor Test 5, und **von `reloc2.py` und
`duptest.py` systematisch übersehen**: die drei bisher als „Zufallstreffer im
komprimierten Bereich" abgetanen rohen Offsetvorkommen (§6d Test 3 nannte
0x3ab10a3) liegen alle in einem 5-KB-Fenster. Bei 79 MB und drei 4-Byte-Mustern
wären 0,05 Treffer zu erwarten, nicht drei. Es war kein Zufall.

**Format D — 6 B, umgekehrte Feldreihenfolge:**

```
+0   uint16 LE Blocklänge   komprimiert
+2   uint32 LE Blockoffset  absolut in der Datei
```

Beispiel bei 0x3ab1eb1, zwei aufeinanderfolgende Records:

```
fa 3a | e7 ff 46 03   -> Länge 15098, Offset 0x346ffe7   (exakt)
ce 1a | 90 a9 46 03   -> Länge  6862, Offset 0x346a990   (exakt, dessen Layer-Partner)
```

Verwandte Blöcke stehen benachbart, Stride 6, dicht gepackt.

**Die Ankerliste hat hier einen Fehler**, der das verdeckt hat: `gw_anchors.pkl`
führt `@0x3ab05d0` mit Länge 37.519 (dem Abstand zum nächsten Anker), der
LZMA-Strom dort ist aber nur **675 B** lang. Die 36.844 B dahinter gehören zu
keinem Block — dort steht diese Tabelle. Es gibt also unklassifizierte Regionen
im Datenbereich; wie viele, ist noch nicht ausgezählt.

**Konsequenz:** eine Blockverschiebung muss **beide** Formfamilien nachziehen.
Von den acht an Test 5 beteiligten Blöcken haben fünf einen Zweiteintrag:

| Block | `<IH` (Formate A–C) | `<HI` (Format D) |
|---|---|---|
| Ziel A `@0x36ca22e` | 0x7b50c | **keiner** |
| Opfer A `@0x36ce94a` | 0x7b524 | **keiner** |
| Ziel B `@0x3392334` | 0x74b58 | 0x3ab1e57 |
| Ziel C `@0x346c45e` | 0x7550c | 0x3ab1e5d |
| Opfer B `@0x339593c` | 0x74b7c | 0x3ab254d |
| Opfer C `@0x346ffe7` | 0x75524 | 0x3ab1eb1 |
| Partner B `@0x33a5403` | 0x74c0c | 0x3ab2547 |
| Partner C `@0x346a990` | 0x754f4 | 0x3ab1eb7 |

Ob das Gerät Format D überhaupt zum Laden benutzt, ist offen: Test 3 hat
`@0x2f4009f` nur aus dem `<IH`-Index genommen, sein Format-D-Eintrag
(0x3ab10a3) blieb stehen — und der Block verschwand trotzdem aus der Anzeige.
Format D ist also **nicht allein maßgeblich**. Ein stehengelassener
Format-D-Eintrag auf einen *überschriebenen* Block ist damit aber nicht
entschuldigt.

## 6f. Layer-Paare mechanisch bestimmbar, Blöcke wachsen in den Nachbarn

> **Stand 17.09.2026:** die Layer-Paar-Bestimmung über identische BBox gilt.
> Der Wachstums- und Opferblock-Teil ist gegenstandslos — die Blöcke passen mit
> richtigem Encodersweep in ihre Originallänge (§6h).


**Der Blockkopf ist die Bounding Box** (§3), und zwei Blöcke mit **identischer**
BBox sind das Layer-Paar aus §6a. Das 5. int32 im Kopf unterscheidet sie und
läuft innerhalb einer Layer-Gruppe monoton. Damit ist der Partner ohne jede
Heuristik findbar — 20 Byte pro Block entpacken reicht, 76.003 Blöcke in 0,2 s.

Die vier L11-Blöcke über Testort sind zwei Kachelpaare:

| Kachel | BBox x | Layer ~280k | Layer ~1,2M |
|---|---|---|---|
| Ost | 840477–860025 | `@0x36ca22e` 18204 | `@0x346c45e` 15241 |
| West | 820931–840479 | `@0x36ce94a` 12304 | `@0x3392334` 13832 |

**Der entscheidende Befund für den Schreibweg:** alle drei Zielblöcke haben
einen **direkt angrenzenden** Nachfolger, der selbst einen Indexeintrag hat.
`@0x36ca22e` + 18204 = `@0x36ce94a` — exakt, ohne Lücke.

| Ziel | Defizit | Nachfolger | Platz zusammen |
|---|---|---|---|
| `@0x36ca22e` | +18 | `@0x36ce94a` 12304 | 30508 |
| `@0x3392334` | +25 | `@0x339593c` 1995 | 15827 |
| `@0x346c45e` | +26 | `@0x346ffe7` 15098 | 30339 |

Ein Block kann also **an seinem Offset bleiben und in den Nachbarn
hineinwachsen**, wenn der Nachbar Test-3-Stil auf seinen Layer-Partner
umgebogen wird. Dateigröße konstant, kein Kettenumzug, kein Kopfzeiger. Der
Preis ist eine Kachel, die auf einer Zoomstufe ihren zweiten Layer verliert.

**Damit ist das Defizit nie das Problem gewesen.** Die Blöcke fehlen nur 18, 25
und 26 B (mit `RELOBAY` neu gemessen; §6a nannte 10/21/23 für einen anderen
Marker) — die 47.346 B aus Test 4 waren die *vollständigen* Blöcke am neuen
Ort, nicht das Defizit.

### Test 5: Wachstum in den Nachbarn — ABSTURZ des MIB

`test5.py` → `…t5.psf`, `ab1fb6f65fab93bf`. Basis akzeptierter §6-Bau,
Größe identisch, 18.136 geänderte Bytes. Block A @0x36ca22e von 18.204 auf
18.222 B, gleicher Offset, 18 B in den angrenzenden Nachfolger hinein; dessen
Format-A-Record auf den Layer-Partner @0x3392334 umgebogen.

**Ergebnis: kein Ablehnungsdialog, sondern ein vollständiger Absturz.** Das
Audioradio und die im Hintergrund laufende Musik gingen mit, das ganze MIB
startete neu. Das Gerät hat den Index also gelesen und ist beim Verarbeiten
gestorben.

**Eigener Fehler im Versuchsaufbau, zweimal:**

1. Der Test war als „nur von Test 3 belegte Mechanik" begründet. Das war
   falsch. Test 3 änderte einen **Format-B**-Record und bog innerhalb
   benachbarter 5.-Feld-Werte um (2.513.886 → 2.518.191). Test 5 änderte
   **Format-A**-Records und sprang von 279.612 auf 1.200.115. Zwei ungeprüfte
   Variablen in einem Test.
2. Die Ablesung hätte auch bei Erfolg nichts gezeigt: Block A ist die
   **Ost**kachel im Band 280k, und laut Test 6 gewinnt auf z1–z9 die
   **West**kachel das Label. Ein Marker in A wäre unsichtbar geblieben.

Buchhaltung war dagegen sauber: nach der Änderung zeigte **kein einziger**
u32-Verweis in der ganzen Datei mehr auf den überschriebenen Block (Basis 1,
danach 0).

### Test 6: Längenfeld um 18 B übertrieben, ein Byte geändert — AKZEPTIERT

`…t6.psf`, `bebf23195d4c38e5`. Basis akzeptierter §6-Bau. **Ein** geändertes
Byte: im Format-A-Record von Block A steht die Länge 18.222 statt 18.204. Der
Block selbst unangetastet, nichts überschrieben, nichts umgebogen.

**Ergebnis: akzeptiert, Anzeige normal.** z1–z9 `Hausbaz`, ab z10 `Testort`
bis zu klein zum Anzeigen, Linien und Straßen auf allen Stufen.

**Damit ist die Blocklänge im Record nicht tragend** — jedenfalls nicht für
eine Übertreibung um 18 B. Das Gerät läuft die Blöcke **nicht** als harte Kette
`Offset + Länge = nächster Offset` ab, obwohl die Datei diese Invariante
einhält (§6b, 794 Records). Die Kettenhypothese für den Absturz ist erledigt.

**Nebenbefund, Verfeinerung von §6a:** das Label auf z1–z9 kommt aus
`@0x36ce94a`, der Westkachel. Erst ab z10 übernehmen die Blöcke im Band 1,2M.

### Was den Absturz von Test 5 verursacht hat

Nach Test 6 bleiben zwei Kandidaten, und einer fällt ohne Fahrzeugtest:

| Kandidat | Status |
|---|---|
| Längenfeld +18 | **entlastet** durch Test 6 |
| Rekomprimierter LZMA-Strom | **entlastet**: der akzeptierte §6-Bau enthält `@0x36ce94a` als Python-Rekompression und rendert ihn (`Hausbaz`) |
| Umbiegung über Serienbänder | **verbleibender Verdacht** |

Stütze für den Verdacht, aus der Vollvermessung aller 76.003 Blöcke:

| 5. Kopffeld | Blöcke | Byte +20 |
|---|---|---|
| 270.000–300.000 (Opfer A, Ziel A) | 184 | `1`×176, `0`×8 — **nie `2`** |
| 1.190.000–1.280.000 (Ziel B, C) | 655 | `2`×566, `1`×63, `0`×26 |

Im Band des Opfers kommt Byte +20 = `2` in keinem Block vor; genau so einen hat
Test 5 dort eingehängt. **Nicht bewiesen:** dass Byte +20 ein Schema trennt.
Über alle Blöcke nimmt es rund 250 Werte an (0: 9.483, 2: 8.831, 1: 4.930,
14: 3.149 …), es ist **kein globales Typfeld**. Eine frühere Fassung dieses
Abschnitts behauptete das aus sechs Blöcken heraus — Fehlschluss.

### Test 7: Umbiegung im Band, 4 Byte — gebaut, Fahrzeugtest offen

`test7.py` → `…t7.psf`, `51df358a34ca5fe9`. Basis akzeptierter §6-Bau,
Größe identisch, **4 geänderte Bytes**, kein Blockinhalt angetastet.

`@0x36ce94a` (279.612, Byte+20 = 1) → `@0x36ca22e` (287.708, Byte+20 = 1)
statt auf `@0x3392334` (1.200.115, Byte+20 = 2).

| Ablesen | Bedeutung |
|---|---|
| akzeptiert, `Hausbaz` auf z1–z9 verschwunden | Umbiegung **im Band** ist sicher → Test 8 |
| Absturz | Umbiegung in Format-A-Records ist per se unsicher → dann bleibt nur Bearbeitung ohne jedes Opfer |

**Test 8 danach:** Block A auf 18.222 B wachsen lassen **und** das Opfer auf A
umbiegen. Dann rendert der Westkachel-Slot `A'` — und z1–z9 müsste `RELOBAY`
zeigen. Das wäre der erste Bau mit sichtbarem Marker auf einer Stufe, die das
Label auch gewinnt.

## 6g. Vollvermessung aller Blöcke — `gw_anchors.pkl` führt falsche Längen

`blockmap.py` → `gw_blockmap.pkl`: für jeden der 76.003 Blöcke die **echte**
komprimierte Stromlänge, der Ankerabstand, die entpackte Größe, Byte +20, das
5. Kopffeld und die BBox. 0 nicht dekodierbar.

**`gw_anchors.pkl` führt als Länge den Abstand zum nächsten Anker, nicht die
Stromlänge.** Bei 17.196 Blöcken weichen die beiden ab, Summe **3.029.049 B
(2,89 MiB)**. Davon sind 17.185 genau 14 B (der Format-C-Record aus §6b) — der
Rest sind fünf große Brocken:

| Block | Strom | Abstand | unklassifiziert |
|---|---|---|---|
| `@0x4539467` | 466 | 2.421.846 | **2.421.380 B** |
| `@0x45049d6` | 960 | 188.032 | 187.072 B |
| `@0x4b8b131` | 5.886 | 106.277 | 100.391 B |
| `@0x1fe50d5` | 1.608 | 44.137 | 42.529 B |
| `@0x3ab05d0` | 675 | 37.519 | 36.844 B (die Format-D-Tabelle, §6e) |

Das sind **2,79 MiB in fünf Regionen**, die keinem Block gehören. Eine davon
ist nachweislich Index (§6e). Was in den anderen vier steht, ist offen — und
das ist der erste ernsthafte Kandidat für Platz, den wir haben, seit
Dateiwachstum in Test 4 ausgefallen ist.

### Die fünf Regionen sind KEIN freier Platz (18.09.2026)

Der „erste ernsthafte Kandidat für Platz" ist keiner. Alle fünf Regionen tragen
dichte, strukturierte Daten:

| Region | Größe | Nullanteil | Entropie |
|---|---|---|---|
| `@0x4539639` | 2.421.380 B | 20,9 % | 5,98 bit/B |
| `@0x4504d96` | 187.072 B | 47,8 % | 4,80 bit/B |
| `@0x4ba364a` | 6.668 B | 29,7 % | 5,82 bit/B |
| `@0x1fe571d` | 42.529 B | 12,2 % | 4,94 bit/B |
| `@0x3ab0873` | 36.844 B | 18,4 % | 5,98 bit/B (Format-D-Tabelle, §6e) |

Füllmaterial hat Entropie nahe 0. In der größten Region wiederholt sich am
Anfang sichtbar ein Satzmuster im Abstand 20 (`00 00 <xx> 00 12 03 00 01 … 00 00
80 00`) — **aber nur lokal**: über die ganze Region getestet trennen die
Strides 18, 20 und 22 nichts (Bytes +4..5 in 9–10 % `0000`, egal welcher
Stride). Ein globaler fester Satzabstand ist damit **nicht** belegt; die Region
ist strukturiert, ihr Satzformat aber offen.

**Die Datei enthält überhaupt kein Polster.** Längste Nullfolge in allen
79.319.126 B: **6.338 B**, und die liegt *innerhalb* der Format-D-Tabelle. Die
nächstgrößeren sind 31× exakt 1.032 B — eine wiederkehrende Feldgröße, kein
Padding. Alle Nullfolgen ab 256 B zusammen: 48.198 B, verstreut.

**Konsequenz für den Wachstumstest:** ein längerer Block kann *nicht* in eine
dieser Regionen ausweichen. Es bleiben genau zwei Wege, und beide sind
ungeprüft:

1. **In den Nachbarn wachsen** (§6f), dessen Indexeintrag Test-3-Stil
   entfernt oder **im selben Band** umgebogen wird. Dateigröße konstant,
   Metadatenkette unberührt — der konservative Weg. Preis: eine Kachel
   verliert auf einer Stufe ihren zweiten Layer.
2. **Die Datei wachsen lassen** (Test 4, aber mit korrektem LZMA-Kopf). Test 4s
   Ablehnung ist durch Gotcha 1 entwertet, die Frage also offen.

Für *Ziel 3* gibt es daneben einen dritten Weg, der gar keinen Fahrzeugtest
braucht: **innerhalb desselben Blocks umschichten**. Wer im Payload Records
kürzt oder streicht, schafft Platz für neue, und der Block bleibt längenneutral
(§6h Test 11). Das ist der einzige Weg, der heute schon belegt ist.

### Wachstumstest 1 BESTANDEN (20.09.2026) — Blöcke dürfen wachsen

`growtest.py` → `…w1.psf`, `62f175610b7596f8`. **Basis ist das unberührte
Original**, nicht ein früherer Bau — so ist `Testort` überall sonst
unverändert und dient selbst als Gegenprobe.

Der Kniff: **der Payload bleibt bytegleich lang**, es werden nur 7 Zeichen
getauscht. Der Strom wächst allein über die Encoderwahl. Damit hat das Label
dieselbe Gestalt wie Test 11s bewährtes `Manneba` — ein zu langes, nicht mehr
gezeichnetes Label kann das Ergebnis nicht verfälschen. Gemessen wird
ausschließlich: **darf der Strom länger sein als der Extent?**

| Stufe | Block | Sonde | Payload | Strom | gegen Extent |
|---|---|---|---|---|---|
| z1–z9 | `@0x36ce94a` West 280k | `Testort` → `Kontrol` | 17.468 | 12.304 | **±0** |
| z10–z11 | `@0x3392334` West 1,2M | `Testort` → `Wachsba` | 20.467 | 13.896 | **+64** |
| z12 | — | unverändert | | | zeigt weiter `Testort` |

Der Zielblock läuft 64 B in seinen direkten Nachfolger `@0x339593c` (1995 B)
hinein. Dessen **beide** Referenzen sind auf seinen Layer-Partner `@0x33a5403`
umgebogen — Format A @0x74b7c und Format D @0x3ab254d:

| | Opfer `@0x339593c` | Partner `@0x33a5403` |
|---|---|---|
| BBox | 772066/6625281/781832/6640842 | **identisch** |
| 5. Kopffeld | 1.248.557 | 1.271.606 |
| Byte +20 | 2 | **2** |

Gleiches Band, gleiches Byte +20, identische BBox — also genau die Umbiegung,
die **Test 7 einzeln belegt** hat, ohne den Bandwechsel, der seit Test 5 unter
Verdacht steht. Die Länge des Zielblocks ist in **beiden** seiner Referenzen
auf 13.896 nachgezogen (Format A @0x74b58, Format D @0x3ab1e57).

**Referenzbuchhaltung, vollständig:** jeder Block hat genau zwei echte
Einträge, Format A und Format D. Die scheinbaren Zusatztreffer (`<IH>`
@0x3ab1e59, `<HI>` @0x74b56 …) sind **Überlappungsartefakte** — dieselben
Bytes, um zwei Stellen versetzt gelesen. Nach dem Bau zeigt keine Referenz
mehr auf das Opfer.

| | |
|---|---|
| Dateigröße | 79.319.126, **unverändert** |
| geänderte Bytes | 24.949 |
| Metadatenkette am Dateiende | unberührt |
| `validate.py` | **0 Fehler**, 17 Warnungen (alle erwartet) |

**Ergebnis im Fahrzeug: `Kontrol` auf z1–z9 und `Wachsba` auf z10–z11 — beide
da.** Ein Block darf also länger sein als sein Extent.

**Damit ist der Schreibweg vollständig offen.** Was jetzt belegt ist:

| | |
|---|---|
| Blockwachstum | **+64 B über den Extent**, in den geopferten Nachfolger hinein |
| Opfer umbiegen | beide Referenzen (Format A *und* Format D) auf den Layer-Partner, **im selben Band** |
| Längenfeld | auf die **neue** Länge gezogen — wird akzeptiert |
| Dateigröße | konstant, Metadatenkette unberührt |

**Was weiterhin NICHT belegt ist**, und auch nicht gebraucht wird:

- ob die **Datei** wachsen darf (Test 4) — irrelevant, solange Nachbarn
  geopfert werden können;
- **wie weit** ein Block wachsen darf. Getestet sind +64 B; das Opfer bot
  1.995 B. Die Obergrenze ist offen.
- ob ein **Bandwechsel** beim Umbiegen schadet — dieser Bau hat ihn bewusst
  vermieden.

Der Kontrollmarker auf z1–z9 hat getan, wofür er da war: er trennt „Karte
abgewiesen" von „Block nicht geladen" — das war bei Test 4 nicht möglich.

**Folge für Ziel 3:** das Streichen bestehender Records ist **nicht mehr nötig**.
Die `Kelsitstraße` kostet 33 B Payload ≈ 20 B Strom, das Opfer bietet 1.995 B.
Die Frage „dürfen zwei `Moselbrücke`-Segmente weichen" ist damit hinfällig.

### Ziel 3, Bau 1 BESTANDEN (20.09.2026) — OSM-Straßen sind schreibbar

`ziel3.py` → `…z3.psf`, `3442bd9a19942649`, `validate.py` **0 Fehler**. Basis
ist das unberührte Original. Eingefügt ist die **`Kelsitstraße`** in Testort —
der einzige benannte Weg, den OSM im Umkreis von 1 km kennt und der im Block
fehlt.

| | |
|---|---|
| OSM → Record | 4 Stützpunkte, keine Verdichtung nötig, **26 B** |
| eingefügt | @8964 hinter `Nachbarorter Straße`, Rahmung vom Nachbarn (7 B) |
| Payload | 20.467 → **20.500** (+33 B) |
| Strom | 13.832 → **13.856** (+24 B, in den Nachfolger hinein) |
| Startpunkt | 50,1 N / 7,5 E |
| Gegenprobe | der Decoder liest die Straße wieder aus dem gebauten Block, n=3, 4 Punkte |

Sonden: z1–z9 `Testort` → **`Kontro2`** (längenneutral, sagt ob die Karte
geladen ist), z10–z11 `Testort` bleibt `Testort` und die `Kelsitstraße` kommt
dazu.

**Neu an diesem Bau — und der eigentliche Prüfpunkt: der entpackte Payload
wächst.** `w1` hat gezeigt, dass der *Strom* länger sein darf; dort blieb der
Payload bytegleich lang. Hier wird der Block auch **entpackt größer**, und
damit ändern sich `dict_size` und `size` im 13-B-Kopf zwangsläufig.

Das ist kein Verstoß gegen Gotcha 1, sondern deren korrekte Anwendung: die
Invariante ist `dict_size == size == entpackte Größe`, **nicht** Byteidentität
des Kopfes zum Original. `validate.py` prüfte bisher letzteres ([7]) — für
Bauten mit `grow` im Plan ist das jetzt eine Warnung statt eines Fehlers, weil
[3], [4] und [5] die echte Invariante direkt prüfen.

### Label-Stufe ≠ Linien-Stufe (20.09.2026)

Die Zoomtabelle aus §6a/§6h sagt, aus welchem Block das **Ortslabel** kommt.
Sie sagt **nichts** darüber, woher die **Liniengeometrie** kommt — und eine
frühere Fassung dieser Ableseanweisung hat die beiden verwechselt.

Gemessen über alle 13 Blöcke, deren BBox Testort enthält, jeweils mit dem
Sektion-16-Start aus der eigenen Sektionstabelle:

| Block | Level | Band | Linien `f=0x00` | davon <1,5 km um Testort |
|---|---|---|---|---|
| `@0x3392334` | L11 | 1,2M | **41** | **3** (nächste: `Hauptstraße`, 0,10 km) |
| `@0x36ce94a` | L11 | 280k | 0 | 0 |
| `@0x2f34830` | L10 | 2,5M | 15 | 0 (nächste 13,2 km) |
| L10 ×3, L9 ×2, L8 | | | keine Sektion 16 | — |

**`@0x3392334` ist der einzige Block der ganzen Datei, der Straßen in Testort
führt.** Darunter gibt es nichts: die vier Blöcke mit kleinerer BBox
(8.336–18.952 m) passen nicht ins Kachelraster `2πR/2^L` und enthalten **null**
Kartennamen — es sind keine Kartenkacheln. Darüber führen L10 und gröber in
Testort keine Straßen.

**Folge:** was immer das Gerät in Testort an Straßen zeichnet, auf welcher
Zoomstufe auch immer, stammt aus Block B. Eine dort eingefügte Straße kann
beim Hineinzoomen nicht verschwinden — es gibt keinen feineren Block, in den
sie fehlen könnte. Die Richtung, in der Daten tatsächlich fehlen, ist das
**Herauszoomen**: ab L10 sind Dorfstraßen nicht mehr enthalten.

**Ergebnis im Fahrzeug: die `Kelsitstraße` ist zu sehen, sie geht westlich von
den vorhandenen Straßen ab.** Lage und Richtung stimmen.

**Damit ist Ziel 3 end-to-end belegt.** Eine Straße, die es im Navi nicht gab,
steht aus OSM-Daten dort — über `to_units` → `densify` → `record` → Einfügen →
LZMA → Index. Und mit ihr ist die letzte Stufe des Schreibwegs bestätigt: **der
entpackte Payload darf wachsen**, nicht nur der Strom (`w1`).

**Offen geblieben und sofort aufgefallen: die Flurfarbe unter der Straße
stimmt nicht.** Der Ort dehnt sich aus, die Landnutzungsfläche darunter nicht.

### Warum die `Kelsitstraße` fehlte — nicht weil sie neu ist (20.09.2026)

OSM-Historie von Way `25779545`:

```
v1  2008-07-26  highway=residential, name=Kelsitstraße, width=3
v2  2014-07-15  (unveraendert in den Tags)
```

**Sie steht seit 2008 in OSM**, der Kartenstand ist von 12.12.2019. Sie fehlte
also nicht, weil sie neu wäre, sondern weil **HERE sie nicht erfasst hat**: 48 m
lang, 3 m breit, eine Stichstraße unter der Erfassungsschwelle. Passend dazu
führt Block B für Testort nur die beiden Hauptachsen `Hauptstraße` und
`Nachbarorter Straße`.

**Folge für die Flurfarbe:** es ist *kein* Neubaugebiet, dessen Landnutzung
noch fehlt. Die Siedlungsfläche von HERE ist schlicht kleiner geschnitten als
die reale Bebauung.

### Auflösungsgrenze, jetzt empirisch statt gerechnet (20.09.2026)

Die `Kelsitstraße` ist **48 m lang** und wurde zu **3 Deltabytes** — im Fahrzeug
sichtbar und als eigener Stich erkennbar. Damit ist die Untergrenze gemessen,
nicht mehr geschätzt:

| Länge | bei Quantum 18 m | Ergebnis |
|---|---|---|
| < 18 m | < 1 Einheit | verschwindet ganz |
| ~48 m | 2,7 Einheiten | **sichtbar** (belegt) |
| 100–400 m | 6–22 Einheiten | Form grob richtig |

Zwei Wege mit weniger als 18 m Abstand fallen auf dieselbe Linie; Kurven werden
zum Zickzack auf dem Raster.

**Korrektur einer früheren Pauschalaussage:** „Campingplatzwege in ihrer
Feinheit nicht" war zu streng. Die **Hauptwege** eines Campingplatzes
(Ringstraße, Zufahrt, typisch 100–400 m) sind darstellbar; nur die
Parzellenstruktur mit Abständen um 10 m ist es nicht.

### Camping Schinderhannes, Bau c1 — aufgespielt, Fahrzeugtest offen (20.09.2026)

`camping.py` → `…c1.psf`, `7a5cebd589930c18`, `validate.py` **0 Fehler**.

**Der Platz liegt in der OSTkachel.** Er beginnt östlich von 7,5 E, gehört
also in Block C `@0x346c45e` — nicht in Testorts Block B. Ein erster Anlauf
gegen Block B ergab 37 von 37 Wegen „außerhalb der Kachel".

**Vorher war dort nichts.** Geprüft über **alle** Recordtypen, nicht nur
`f=0x00` — Block C führt 64 Records in sechs Flag-Varianten (`f=0x00` 33,
`f=0x10` 25, dazu 0x03/0x20/0x2f/0x54), und **null** davon liegen im
Platzrechteck (X 28..101, Y 12..82). Die einzige Linie in der Nähe ist die
Zufahrt `Testorter Straße` (X 87..103, Y 118..130), die rund 700 m nördlich
des Platzes endet.

| | |
|---|---|
| Wege | 40, zusammen 4.479 m, 168 Deltabytes |
| Payload | 21.604 → **22.647** (+1.043 B) |
| Strom | 15.241 → **15.581** (+340 B, in `@0x346ffe7` hinein) |
| Opfer | `@0x346ffe7` → Partner `@0x346a990`, beide Referenzen |
| ausgelassen | 2 Wege unter 18 m — sie verschwinden im Raster |

**Namenswahl:** die 13 Wege ab 100 m heißen `Country Camping`. `Campingplatz`
wäre falsch gewesen — so heißt bereits eine Straße an der Mosel (17 km weg,
andere Kachel), die im Suchindex doppelt aufgetaucht wäre. `Country Camping`
kommt in keinem der vier Blöcke vor.

**Sonde: 27 Wege haben einen LEEREN Namen** (`00 03 00`). Ob das Format das
zulässt, ist offen — `parse_section` verwirft sie, deshalb sind sie per
Bytevergleich geprüft (40/40 stehen korrekt im Block). Ablesen: erscheint nur
das Gerüst aus 13 Wegen, braucht künftig jeder Weg einen Namen; erscheint das
volle Netz, sind Wegenetze ohne Labelflut möglich.

**Unabhängiger Prüfpunkt vom Nutzer:** ein bekannter Punkt auf dem Platz liegt
bei 50,1 N / 7,5 E = X 52,88 / Y 56,86 in Block C — mitten im
Platzrechteck, die drei nächsten OSM-Wege 9, 12 und 15 m entfernt und alle im
Bau enthalten. **Die 9 m sind zugleich die Grenze:** bei 18 m Quantum wird jeder
Weg auf eine halbe Rasterzelle genau platziert. Für Zufahrt und Ringstruktur
reicht das, für „vor welcher Parzelle stehe ich" nicht.

### Bau c1 im Fahrzeug: nichts zu sehen — und nicht auswertbar (21.09.2026)

**Ergebnis des Nutzers:** „Keine zusätzlichen frisch gezeichneten Wege zwischen
der Sackgasse *Campingplatz* in Testort und dem Dorf Testort erkennbar, auf
keiner Zoomstufe."

**Der Bau beantwortet keine der beiden Fragen, die er stellen sollte.** `c1`
verstößt gegen die eigene Regel aus §6h („mehrere unabhängige Sonden pro Bau"):

| | `z3` (bestanden) | `c1` (Nullresultat) |
|---|---|---|
| geänderte Blöcke | `0x3392334`, **`0x36ce94a`** | **nur** `0x346c45e` |
| Ladeanzeige | `Kontro2`, z1–z9 | **keine** |
| Kachel | West — 6 positive Fahrzeugtests | Ost — **null** positive, ein Null (Test 11) |
| Namen | alle benannt | 13 benannt, **27 leer** |
| Wachstum | +33 B Payload | +1.043 B Payload |

Ohne Ladeanzeige ist „nichts Neues zu sehen" nicht von „die alte Karte ist noch
im Gerät" zu unterscheiden. Und selbst wenn sie geladen war, bleiben drei
Ursachen verknotet: Ostkachel, leere Namen, Blickrichtung.

**Die Blickrichtung ist eine ernstzunehmende Möglichkeit.** Gezeichnet wurde
50,0..50,1 N / 7,5..7,5 E, Schwerpunkt 50,1 / 7,5 —
das ist **780 m südöstlich** der Ortsmitte, auf dem Platz selbst. Der Korridor
Dorf → Platz gehört **nicht** dazu: das Auswahlrechteck verlangte *alle*
Stützpunkte innerhalb X 28..101, und die Zufahrten aus dem Dorf (OSM-Service-
wege ab 7,5 E) fallen damit heraus. Wer zwischen Dorf und Sackgasse schaut,
schaut westlich an allem Gezeichneten vorbei.

**Ausgeschlossen ist dagegen der Strukturverdacht.** Die Sektionstabelle
(`validate.py`, Prüfung 10) führt in beiden Blöcken **Klasse 16 als letzten
Eintrag** — West `[(5,25),(8,6),(9,8),(10,6309),(13,7545),(16,7709)]`, Ost
`[…,(14,11083),(16,11341)]`. Einfügen am Sektionsende verschiebt also nichts,
worauf die Tabelle zeigt. `z3` hat zusätzlich bewiesen, dass sogar **mitten in
die Sektion** eingefügt werden darf (+33 B @8964, alle folgenden Records um
33 B verschoben, im Fahrzeug sichtbar). Es gibt keinen Recordoffsetindex.
Auch die Validatorwarnungen von `c1` sind identisch mit denen des bestandenen
`z3` — kein Unterschied dort.

### Die Ostkachel hat einen dritten Block — die Westkachel nicht (21.09.2026)

Vollzählung aller Blöcke, deren BBox den Platz bzw. Testort enthält:

| Kachel | L11-Blöcke mit identischer BBox |
|---|---|
| West (Testort) `X820931 Y6455973` | `@0x3392334`/1.200.115, `@0x36ce94a`/279.612 |
| Ost (Platz) `X840477 Y6455973` | `@0x346c45e`/1.201.252, **`@0x3473ae1`/1.191.679**, `@0x36ca22e`/287.708 |

`@0x3473ae1` (12.031 B) war bisher unbekannt. Er hat **keine lesbare
Sektionstabelle**, führt 18 Namen (`Am Casino`, `Rheinpromenade`, `Zur
Marksburg`, `Mittelrheintal` …) — also anderer Inhalt als Block C.

Und das ist kein Sonderfall, sondern die **Regel**: über alle 189 L11-Kacheln
der Datei

    Gruppengroesse 1: 90   2: 83   3: 15   4: 1

und die Zweiergruppen bestehen fast immer aus **zwei Blöcken des 1,2M-Bands**
(z. B. 1.200.477 + 1.192.997), nicht aus 1,2M + 280k. Das 5. Kopffeld ist damit
keine Klassenkennung, sondern läuft kontinuierlich von 1.181.244 bis 1.202.708.

**Die Westkachel ist die Ausnahme:** ihr fehlt der ~1,19M-Partner. Alle sechs
bestandenen Fahrzeugtests liegen in dieser Ausnahmekachel. Ob in der Ostkachel
`@0x346c45e` oder `@0x3473ae1` gerendert wird, ist damit **offen** — und genau
das macht Test 11s Nebenbefund („Badenha erschien nirgends") und `c1` zu zwei
Nullresultaten mit *derselben* möglichen Ursache.

**Gegenprobe, die noch fehlt:** ob `Testorter Straße` (nur in `@0x346c45e`,
`@0x2f4009f` und `@0x29d48b8`, **nicht** in Block B) im Gerät überhaupt
beschriftet wird. Steht sie da, wird Block C gelesen.

### Bau d1 — der Diskriminator (21.09.2026)

`disc1.py` → `…d1.psf`, `63dd904f447de2bd`, `validate.py` **0 Fehler**, auf der
Karte. Basis ist das unberührte Original. Sechs unabhängige Sonden, eine Fahrt:

| Sonde | Block | Änderung | Ablesen |
|---|---|---|---|
| P0 | `@0x36ce94a` West 280k | `Testort` → **`Kontro3`** | z1–z9: Karte geladen? |
| P1 | `@0x3392334` West 1,2M | + `Kelsitstraße` (benannt, 26 B) | Einfügen funktioniert (Wiederholung von z3) |
| P2 | `@0x3392334` West 1,2M | + Quadrat 252 m mit **leerem Namen**, X 1051 / Y 104 = 50,1 N / 7,5 E, 330 m westlich der Ortsmitte | **leere Namen zulässig?** |
| P3 | `@0x346c45e` Ost 1,2M | `Testorter Straße` → **`OSTTEST`** | wird Block C gelesen? |
| P4 | `@0x346c45e` Ost 1,2M | `Ortsgammaer Straße` @13729 → Quadrat 252 m (längenneutral, 9 Deltas) | zeichnet die Ostkachel Linien? |
| P5 | `@0x346c45e` Ost 1,2M | die 40 Campingwege aus `c1`, unverändert | erscheinen sie, wenn man **auf dem Platz** schaut? |

Payload West 20.467 → 20.526 (+59), Strom 13.832 → 13.873 (+41).
Payload Ost 21.604 → 22.637 (+1.033), Strom 15.241 → 15.583 (+342).
Zwei Opfer: `0x339593c` → `0x33a5403`, `0x346ffe7` → `0x346a990`.
**Neu an diesem Bau:** zwei gewachsene Blöcke in zwei Bändern gleichzeitig.

Die Wahrheitstabelle:

- **kein `Kontro3`** → die Karte war nicht geladen, alles andere ist wertlos.
- `Kontro3` da, **P1 und P2 beide da** → leere Namen sind zulässig.
- `Kontro3` da, **P1 da, P2 fehlt** → leere Namen werden verworfen; `c1`s
  27 namenlose Wege sind damit erklärt, die 13 benannten aber nicht.
- **P3 oder P4 da** → Block C wird gerendert. Dann liegt es an den Namen (P2)
  oder daran, wo geschaut wurde (P5).
- **P3 und P4 beide weg** → die Ostkachel wird aus `@0x346c45e` nicht
  gezeichnet. Nächster Verdächtiger: `@0x3473ae1`.

**Nebenwirkung, bewusst in Kauf genommen:** P4 macht aus der echten
`Ortsgammaer Straße` östlich von Norath ein Quadrat, P3 nimmt der
`Testorter Straße` ihren Namen. Testkarte.

### d1 im Fahrzeug: Karte geladen, Strassennetz weg (22.09.2026) — ÜBERHOLT, siehe Korrektur unten

**Ergebnis:** P0 `Kontro3` **da**. P1–P5 alle **nicht** da — „kein Straßennetz
bei z10–z11".

Das ist ein viel schärferes Ergebnis als `c1`, weil die Ladeanzeige sitzt:
die Karte ist geladen, der 280k-Westblock (längenneutral umgeschrieben,
Test-11-Mechanik) rendert. Und **P1 ist die `Kelsitstraße`, die in `z3` am
selben Ort mit demselben Code sichtbar war.** Sie fehlt jetzt — zusammen mit
dem Straßennetz, das vorher schon im Block stand.

**Ein Record reisst die ganze Sektion mit.** Der einzige strukturelle
Unterschied zwischen `z3` (sichtbar) und `d1` (alles weg) ist P2: ein
zusätzlicher Record mit **leerem Namen**, eingefügt *hinter* der Kelsitstraße.
Trotzdem fehlt auch die Kelsitstraße, die davor steht — das Gerät verwirft also
nicht ab der Fehlerstelle, sondern die Sektion als Ganzes.

| Bau | Blöcke | leere Namen | Ergebnis |
|---|---|---|---|
| `z3` | B wächst +24 B Strom | 0 | **Kelsitstraße sichtbar** |
| `c1` | C wächst +340 B | **27** | nichts Neues (B unberührt, Dorf normal) |
| `d1` | B +41 B, C +342 B | **1 in B**, 27 in C | **kein Straßennetz mehr** |

**Leere Namen sind im Original nirgends belegt.** Sequentiell gelesen, mit
ausdrücklich zugelassenem leerem Namen: 0 von 41 Records in Block B, 0 von 32
in Block C. Das `00 03 00` war eine Erfindung ohne Vorbild in den Daten.

**Damit ist auch `c1` erklärt** — nicht durch die Ostkachel und nicht durch die
Blickrichtung: dort standen 27 leere Namen in Block C, die Sektion war hin, und
deshalb erschienen selbst die 13 benannten Wege nicht, die *vor* dem ersten
leeren Namen stehen.

**Noch nicht getrennt:** ob statt der leeren Namen das **doppelte Wachstum**
(zwei gewachsene Blöcke, zwei Opfer in einem Bau) schuld ist. `e1` prüft genau
das, weil es die Struktur von `d1` exakt beibehält.

**Korrektur zu §6j, nebenbei gefunden:** `ins = max(r['end'] for r in vor)` ist
**nicht** das Ende der Sektion, sondern nur das Ende des letzten `f=0x00`-
Records. Dahinter stehen in Block B noch 3.902 B, in Block C 3.376 B weitere
Records — `f=0x10`-Records und Randrecords, die `parse_section` nicht
zurückgibt (u. a. `Höhenkammstraße B 1` in Block B). `c1` und `d1` haben also
*mitten* in die Sektion eingefügt, nicht dahinter.

**Blockkopf, Nebenbefund:** Byte 35 (direkt vor der Sektionstabelle) ist die
**Zahl der Sektionen** — Block B 6, Block C 9, jeweils genau die Länge der
Tabelle ab Offset 36.

### Korrektur: d1 war kein Totalausfall — nur z10–z11 abgelesen (22.09.2026)

Nachfrage beim Nutzer: **„Bei z1–9 war das Dorf wie gehabt da, mit
Kelsitstraße."** Die Kelsitstraße gibt es nur, weil `d1` sie in Block B
geschrieben hat, also **las das Gerät Block B und zeichnete ihn**. Das
„kein Straßennetz“ galt nur für z10–z11, und auf dieser Stufe zeichnet das
Gerät Dorfstraßen vermutlich grundsätzlich nicht (z1–z9 ist der Nahzoom). Ob
bei z10–z11 im Originalzustand Testorts Straßen zu sehen sind, ist nie
abgelesen worden. Die Ableseanweisungen für `z3`, `d1` und `e1` nannten
z10–z11 für die Straßen, und das war der eigentliche Fehler.

**Widerlegt ist damit die Aussage oben, ein leerer Name reiße die ganze Sektion
mit.** Reihenfolge in Block B von `d1`:

    @8856 Hauptstraße  @8927 Nachbarorter Straße  @8971 Kelsitstraße
    @9004 Quadrat mit LEEREM Namen
    @10275 Hauptstraße (anderer Ort) … weitere Records

Alles, was der Nutzer im Dorf sah, steht **vor** dem leeren Namen. Das passt zu
zwei Lesarten, die `d1` nicht trennt:

- **(a) leere Namen sind harmlos**, oder
- **(b) das Gerät hört am leeren Namen auf zu lesen** und alles dahinter fehlt.

Ob das Quadrat (P2, 330 m westlich) bei z1–z9 da war, wurde nicht abgelesen.
Die Ostsonden P3–P5 wurden nur bei z10–z11 gesucht und sind damit
**unbeantwortet**, nicht negativ.

**Auch `c1` ist damit wieder offen.** Unter (b) hätten die 13 benannten Wege
vor dem ersten leeren Namen erscheinen müssen. Unter (a) alle 40. Dass keiner
zu sehen war, spricht wieder für Blickrichtung oder Ostkachel, also die
Diagnose vom 21.09.

**Die Regel „nie ein leerer Name“ bleibt als billige Vorsicht bestehen**:
`00 03 00` ist im Original nirgends belegt. Bewiesen schädlich ist er nicht.

### Bau e1 — eine Variable gegenüber d1 (22.09.2026)

`disc2.py` → `…e1.psf`, `e3b10bf924d2e6c1`, `validate.py` **0 Fehler**, auf der
Karte. Struktur identisch zu `d1` — gleiche Blöcke, gleiche Opfer, gleiche
Einfügestellen, gleiches Wachstum — **nur bekommt jeder Record einen Namen**:

| Sonde | Änderung gegenüber `d1` |
|---|---|
| P0 | `Kontro3` → **`Kontro4`** (damit die Anzeige neu ist) |
| P2 | Quadrat heißt jetzt **`QUADRAT`** statt leer |
| P5 | die 27 kurzen Campingwege heißen **`Campingweg`** statt leer |
| P1, P3, P4 | unverändert |

West Payload 20.467 → 20.533, Strom 13.832 → 13.879 (+47).
Ost Payload 21.604 → 22.907, Strom 15.241 → 15.597 (+356).

**Ein längenneutraler Ostblock wäre risikoärmer gewesen, ist aber nicht
baubar:** über 55 Varianten (5 Quadratgrößen × 11 Namen, jeweils voller
Encodersweep) liegt liblzma für Block C **+11 bis +16 B** über dem Extent. Das
bestätigt §6h („C −12") und schließt die Test-11-Mechanik für diesen Block aus.

### e1 im Fahrzeug: ABSTURZ beim Anzeigen der Kacheln (24.09.2026)

Wo und bei welcher Zoomstufe, weiß der Nutzer nicht. Karte geprüft: byteidentisch
`e1`, keine `._`-Dateien, `validate.py` damals 0 Fehler. Der Validator sah das
Innere der Blöcke nicht → §6l.

## 6l. Sektion 16 ist eine längenpräfixierte Kette mit Gruppenindex (24.09.2026)

**Die Straßensektion ist lückenlos als Kette lesbar** — Block B 281 Elemente
von 7988 bis 17547, Block C 211 Elemente von 12059 bis 19168:

```
[n]  n × (Klasse, Flags, x, 00, u16 Offset)      Gruppenindex, Offset ab [n]
Kette:   u16 L │ Rumpf (L−2 B)                     L zählt das Längenfeld mit
benannt: u16 L │ 80 11 │ u16 L−1 │ 01 n f X Y Δ… │ {<Typ> 03 Text 00} │ k
unbenannt u. a.: u16 L │ 00 01 n f X Y Δ…   (Rumpftypen 0001, 8011, 8001, 0000, 8020)
```

- **Gruppenindex:** Block B n=18 bei 7879, Block C n=14 bei 11974. **Alle
  Offsets treffen Elementanfänge (18/18, 14/14)**, der erste zeigt aufs erste
  Element. Einträge sind nach Offset sortiert; `22 80 03` ist die Gruppe von
  Testorts Dorfstraßen. Wer einfügt, muss jeden späteren Offset nachziehen.
- **Namenseinträge:** `00 03 Name 00` (Straßenname), `03 03 B327 00`
  (Nummer); ein Element kann mehrere tragen. Das Schlussbyte `k` ist 1..4,
  beim Einzelnamen immer `01`, Semantik sonst offen.
- **Keine weiteren Zeiger** in die Kette: weder aus der Nachbarsektion 13/14
  noch aus den 2,4–2,9 KB hinter der Kette (Treffer auf Zufallsniveau).
- **Korrektur zu §6j „Offen: der Zähler `<v>`“:** `<v>` ist **kein Attribut,
  sondern die Innenlänge `L−1`** des nächsten Elements, und `01` davor ist das
  Schlussbyte `k` des vorigen. Die zwölf Hypothesen dort maßen gegen die
  falsche Rahmung. 73/73 benannte `f=0`-Records in B und C erfüllen die Regel.

**Was `z3`, `c1`, `d1` und `e1` falsch gemacht haben:**

| Bau | Fehler |
|---|---|
| alle vier | eingefügt **zwischen Name und Schlussbyte** eines Elements, kein Längenpräfix, Gruppenindex nicht nachgezogen (B: 17 von 18 Offsets falsch) |
| `c1`/`d1`/`e1` Ost | Campingwege mit `rawo[SEC_O:SEC_O+7]` = `15 22 26 d7 01 80 01` gerahmt — das ist der Kopf eines **Punktlabels**, kein Straßenrahmen |
| `d1`/`e1` Ost | `OSTTEST` kürzte das Element um 10 B, `L` und `L−1` blieben stehen |

`z3` und `d1` liefen trotzdem, sogar mit sichtbarer `Kelsitstraße`; `e1` mit
anderen Bytes an denselben kaputten Stellen stürzte ab. **Das Gerät liest die
Kette also nicht streng, aber kaputte Rahmung ist Glücksspiel.** Ob genau sie
den Absturz auslöste, ist nicht bewiesen — sie ist der einzige gefundene
Strukturfehler.

**Werkzeug:** `sec16.py` (`find`, `named`, `insert`, `replace`, `check`).
`validate.py` prüft das als **[12]** für jeden geänderten Block mit Sektion 16:
`e1`, `d1`, `c1` und `z3` fallen durch, `w1` und `geo` bestehen,
Stichprobe von 20 Originalblöcken fehlerfrei.

### Bau f1 — dieselben Sonden, korrekt gerahmt (24.09.2026)

`f1.py` → `…f1.psf`, `1f9b09e324561cf3`, `validate.py` **0 Fehler inkl. [12]**.

| Sonde | Block | Änderung | Ablesen bei z1–z9 |
|---|---|---|---|
| P0 | `@0x36ce94a` | `Testort` → **`Kontro5`** | Karte geladen? |
| P1 | `@0x3392334` | `Kelsitstraße` als Element vor `Nachbarorter Straße`, Gruppe `22 80 03`, Index nachgezogen | da? |
| P2 | `@0x3392334` | Quadrat 252 m `QUADRAT`, 330 m westlich der Ortsmitte | da? |
| P3 | `@0x346c45e` | `Testorter Straße` → **`OSTTEST Testorter`**, gleich lang | Ostkachel beschriftet? |
| P4 | `@0x346c45e` | `Ortsgammaer Straße` bei Norath → Quadrat, längenneutral | Ostkachel zeichnet? |

**Keine Campingwege**: Block C ist strukturell unverändert (Payload +0, nur
der Strom +22 B wegen liblzma, Opfer wie in `d1`). **Stürzt `f1` ab, liegt es
am Westblock** — oder am Wachstum von C, das in `d1` aber unauffällig war.

### Ergebnis f1 (25.09.2026)

Im Fahrzeug: **kein Absturz. P0 `Kontro5` und P1 `Kelsitstraße` sichtbar,
P2 `QUADRAT`, P3 `OSTTEST Testorter`, P4 Ostquadrat nicht.**

- **Korrekt gerahmtes Einfügen hält.** Gleiche Sonden wie `e1`, nur mit
  `sec16.insert()` — und kein Absturz. Stützt (beweist nicht) §6l als Ursache.
- **Die Ostkachel `@0x346c45e` rendert nicht — viertes Nullresultat** (Test 11,
  `c1`, P3 Name, P4 Geometrie). Vorsicht bei der Lesart des Geometrietests:
  `geotest.py` hat die `Ortsgammaer Straße` **im Westblock** `@0x3392334`
  (@12474) umgebogen, nicht im Ostblock. P4 hat ihr Duplikat in der Ostkachel
  getroffen, das ist ein anderer Record. Der Westblock trägt die Straße
  weiterhin unverändert.
- **P2 ist offen, und das ist der eigentliche Befund.** `QUADRAT` steht in
  derselben Gruppe `22 80 03`, direkt zwischen `Kelsitstraße` (@8927, sichtbar)
  und `Nachbarorter Straße` (@8993). Das Gerät hat die Kette also darüber
  hinweg gelesen und diesen einen Record nicht gezeichnet. Offline
  ausgeschlossen: räumliches Aussortieren über den Gruppenindex (Gruppe spannt
  X 35–1087, Y 45–1575), Rahmung (validate [12] 0 Fehler), Kachelgrenze
  (X 1051–1065 von 1086).
- **Neuer Strukturbefund: 73/73 `f=0`-Records in B und C enden auf Deltabyte
  `01`.** Als echtes Delta (dx=+1) ist das unmöglich, das Byte ist Teil des
  Formats. `QUADRAT` endet auf `d0`; `Kelsitstraße` endet nur zufällig auf
  `01`. **Gegenbeleg:** der sichtbare `geotest` hatte das `01` durch `20`
  ersetzt. Pflicht ist es also nicht, jedenfalls nicht beim Umbiegen eines
  bestehenden Records.
- **Kandidaten für P2:** (a) Ablesen, P2 lag nicht im Blickfeld; (b) das
  Schlussbyte `01` wird bei neuen Records gebraucht; (c) das Gerät zeichnet
  nur Linien, die ans Netz anschließen — `QUADRAT` ist isoliert, Kelsitstraße
  und `geotest` hingen am Dorfnetz.
- **Nachtrag vom Nutzer:** Hauptstraße und Nachbarorter Straße normal; die
  `Ortsgammaer Straße` bei Norath **in Originalform** da → der Westblock
  zeichnet sie, das Ost-Duplikat nicht. Ob das P2-Feld im Blick war: **unbekannt**.
  Kelsitstraße hängt am Netz (Endpunkt (1082,82) = Stützpunkt der
  Nachbarorter Straße).

### Bau g1 — P2 auflösen (26.09.2026)

`g1.py` → `…g1.psf`, `ffcedf148f647835`, validate 0 Fehler. Nur Westblock und
Ladeanzeige, **Ostkachel unberührt**. Drei Sonden in Gruppe `22 80 03`, Reihenfolge
Kelsitstraße, A, B, C, Nachbarorter Straße:

| Sonde | Form | Ort (SW-Ecke/Start) | isoliert | Schluss |
|---|---|---|---|---|
| P0 | `Kontro6` | Ortslabel | | |
| A `QUADRAT` | Quadrat 252 m, **byteidentisch mit f1-P2 inkl. Rahmung** | 50,1 N / 7,5 E, NW | ja | `d0` |
| B `SONDE B` | Quadrat 252 m + Schwanz 18 m | 50,1 N / 7,5 E, SW | ja | `01` |
| C `SONDE C` | Dreieck 252 m hoch | Anfangspunkt Hauptstraße (1075,95), nach Norden | nein | `97` |

Auswertung: A sichtbar → f1 übersehen. A weg, B da → Schluss `01` nötig.
A weg, C da → Netzanschluss nötig. A, B, C weg → beides falsch.

### §6k. Landnutzungsflächen — offen (20.09.2026)

Der Nutzer im Fahrzeug: „Der Dorfmittelpunkt Testort / `Kontro2` ist Siedlung",
die neue Straße daneben liegt aber auf falscher Flurfarbe. Wer Orte wachsen
lässt, muss die Flächen mitziehen. Stand der Suche im Flächenblock
`@0x36ce94a`:

| | |
|---|---|
| Sektionen | Klasse 9 ist mit **10.106 B (58 %)** die größte — im Straßenblock ist es Klasse 16 |
| Klasse 9 enthält | 91 Records `01 80 01 │ X │ Y │ 00 <n> 00 03 │ Name`, **Ortslabels** |
| `Testort` dort | @4403, in **Klasse 9** |

**Ausgeschlossen:**

- **`<n>` ist nicht die Ortsgröße.** Derselbe Ort kommt mehrfach mit ganz
  verschiedenen Werten vor (Buchholz 77/76/13, Löf 73/6, Brodenbach 10/7/3).
  Die Korrelation zur Einwohnerzahl (r = 0,54) entsteht nur dadurch, dass große
  Orte *mehr* Records haben.
- **`<n>` ist nicht die Länge der Nachbarbytes** — 0 von 90 Lücken passen.
- **Keine Nibbel-Polygone.** Weder die `n` Bytes vor noch nach einem Record
  ergeben einen geschlossenen Zug (0/89 und 0/91, Zufallskontrolle 1/455).
  Auch keine der 557 nullgetrennten Ketten der Sektion schließt sich.

Das deckt sich mit §6j: der Nahzoom-Block hat eine **andere** Geometriekodierung
als die Straßen. Wie die Flächen kodiert sind, ist offen.

- Beide da → **Ziel 3 funktioniert end-to-end**, OSM-Daten sind ins Navi
  schreibbar.
- Nur `Kontro2`, keine `Kelsitstraße` → der entpackte Block darf nicht wachsen,
  obwohl der Strom es darf. Dann bleibt der längenneutrale Weg (oben).

### Stand der Datenträger

| | Inhalt | sha256/16 |
|---|---|---|
| `sdsrc/` | Original, unberührt | `a5c39e28c71c9526` |
| SD + `sdtest/` | Test 4 (`reloc2`), **abgewiesen** (2×, zweites Mal sauber) | `62b623ae84ab0746` |
| `spike/…t5.psf` | Test 5, **Absturz des MIB** | `ab1fb6f65fab93bf` |
| SD + `sdtest/` | Test 6, **akzeptiert** (1 Byte) | `bebf23195d4c38e5` |
| `spike/…t7.psf` | Test 7, akzeptiert | `51df358a34ca5fe9` |
| `spike/…t11.psf` | Test 11, **bestanden** | `15137c5fcaf8d2b2` |
| `spike/…geo.psf` | Geometrietest, **bestanden** | `67d30b41b6bfd408` |
| `spike/…w1.psf` | Wachstumstest 1, **bestanden** 20.09.2026 | `62f175610b7596f8` |
| `spike/…z3.psf` | Ziel 3 Bau 1, **bestanden** 20.09.2026 (`Kelsitstraße` sichtbar) | `3442bd9a19942649` |
| `spike/…c1.psf` | Camping c1, 21.09.2026 **nichts zu sehen — nicht auswertbar** (keine Ladeanzeige) | `7a5cebd589930c18` |
| `spike/…d1.psf` | Diskriminator d1, 22.09.2026: `Kontro3` da, **Straßennetz weg** | `63dd904f447de2bd` |
| `spike/…e1.psf` | e1, 24.09.2026: **Absturz beim Anzeigen** (§6l) | `e3b10bf924d2e6c1` |
| `spike/…f1.psf` | f1, gefahren 25.09.2026: kein Absturz, P0+P1 da, P2–P4 nicht (§6l „Ergebnis f1“) | `1f9b09e324561cf3` |
| **SD + `sdtest/`** | **g1 (Sonden A/B/C zu P2), aufgespielt 26.09.2026, Fahrzeugtest offen** | `ffcedf148f647835` |
| `spike/…dup.psf` | Test 3, entschieden | `906d2f06fe6c0f97` |
| `spike/…patched.psf` | akzeptierter Bau §6 | `e3511640b2148cae` |
| `spike/…reloc.psf` | abgewiesen (Test 1) | `f1e8dc5d7c7bc2f8` |
| `spike/…swap.psf` | akzeptiert, blind (Test 2) | `fa05bb7e7c56d434` |

**Immer prüfen: Schreibschutzschieber offen — und `._*` auf der Karte gelöscht.**

## 6h. Testbilanz nach dem Kopffehler (17.09.2026)

Gotcha 1 hat fünf Fahrzeugtests entwertet. Was davon noch gilt:

| Test | rekomprimiert | Kopf ok | Ergebnis | gilt? |
|---|---|---|---|---|
| §6-Bau | ja | **ja** | akzeptiert | **ja** |
| 1 | ja | nein | abgewiesen | nein |
| 2 | nein | — | akzeptiert | ja |
| 3 | nein | — | entschieden | ja |
| 4 | ja | nein | abgewiesen | **nein** |
| 5 | ja | nein | Absturz | **nein** |
| 6 | nein | — | akzeptiert | **ja** |
| 7 | nein | — | akzeptiert | **ja** |
| 8, 9, 10 | ja | nein | Absturz | **nein** |
| 11 | ja | **ja** | **bestanden** | **ja** |

**Belegt (ohne Rekompression, deshalb unberührt):**

- **Test 2/3:** der Klartextindex ist maßgeblich; ein daraus entfernter Block
  verschwindet aus der Anzeige.
- **Test 6:** eine um 18 B **übertriebene** Länge im Format-A-Record ist
  folgenlos — die gespeicherte Länge wird fürs Laden nicht gebraucht.
- **Test 7:** Umbiegen auf einen anderen Block **funktioniert**, sogar mit
  abweichender BBox. Der Slot rendert dann den fremden Block; sichtbar daran,
  dass z1–z9 nur noch die Osthälfte zeichnete.
- **Zoomzuordnung (Test 6):** z1–z9 Label aus `@0x36ce94a` (Westkachel, Band
  280k), ab z10 aus den Blöcken im Band 1,2M. Verfeinert §6a.

**Wieder offen, weil nur mit kaputtem Kopf getestet:** ob die Datei wachsen
darf, ob ein Block wachsen darf, ob ein Bandwechsel beim Umbiegen schadet, ob
der Markerinhalt eine Rolle spielt.

### Der Encoder-Abstand, richtig gemessen

§6a's **„kein Encoder schlägt das Original" ist widerlegt** — die alte Suche
hatte `lc/lp/pb` festverdrahtet und `BT2` sowie kleine `nice_len` nie probiert.
Voller Sweep bei props 93 über `mf` × `nice_len` × `depth`:

| Block | Extent | alte Suche | voller Sweep | Gewinner |
|---|---|---|---|---|
| `@0x3392334` | 13.832 | 13.859 (+27) | **13.836 (+4)** | `BT2`/16/0 |
| `@0x346c45e` | 15.241 | 15.253 (+12) | 15.253 (+12) | `BT2`/16/0 |

### Rezept: die Stromlänge auf das Byte treffen

Der Marker ist frei wählbar, und **7-Zeichen-Ketten, die im Block schon
vorkommen**, komprimieren besser, weil LZMA sie matcht. Damit stellt man die
Länge gezielt ein. Kandidaten: `re.findall(rb'[A-Z][a-z]{6}', plain)`.

| Block | Extent | Marker | Ergebnis |
|---|---|---|---|
| `@0x3392334` | 13.832 | `Manneba` | **13.832** exakt |
| `@0x346c45e` | 15.241 | `Badenha` | **15.241** exakt |

`fitsearch.py` macht die Suche, `test11.py` den Bau.

### Test 11 — BESTANDEN (17.09.2026)

`test11.py` → `…t11.psf`, `15137c5fcaf8d2b2`, Basis §6-Bau.

**Ergebnis im Fahrzeug: z1–z9 `Hausbaz`, z10–z11 `Manneba`, z12 `TESTBA2`.**

| | |
|---|---|
| 13-Byte-Kopf beider Blöcke | byteidentisch zum Original |
| Stromlänge | exakt == Extent, kein totes Byte |
| Indexeinträge | unverändert |
| Dateigröße | unverändert, 76.003 Blöcke dekodieren |
| geänderte Bytes | 28.260, alle innerhalb der zwei Blockextents |

**Damit ist der Container erledigt.** Ein Block lässt sich beliebig umschreiben,
solange der Payload in die Originallänge komprimiert — und das gelingt mit
vollem Encodersweep plus einem Marker, der im Block schon vorkommt. Kein
Wachstum, kein Opferblock, keine Indexänderung, keine Verschiebung nötig.

**Nebenbefund: die Westkachel gewinnt das Label auf allen Stufen.** `Badenha`
aus Ziel C (`@0x346c45e`, Ostkachel, gleiche Änderung, gleicher Bau) erscheint
nirgends. Patches für sichtbare Ortslabels gehören in die **Westkachel**:
`@0x36ce94a` (Band 280k) für z1–z9, `@0x3392334` (Band 1,2M) für z10–z11.

### Was das für die nächste Phase bedeutet

Das Fahrzeug ist ab jetzt ein **verlässliches Orakel für Blockinhalte**: eine
Änderung im entpackten Payload ist reproduzierbar auf dem Schirm ablesbar. Das
ist das Werkzeug, das für §7.2 (Recordsemantik) fehlte — Feldbedeutungen lassen
sich jetzt durch gezielte Byteänderungen messen statt erraten.

Weil jeder Test eine Fahrt kostet, gehören **mehrere unabhängige Sonden in
einen Bau**: verschiedene Kacheln und Zoomstufen zeigen gleichzeitig
verschiedene Proben. Die Zuordnung Kachel → Zoomstufe steht oben, die
Layer-Paare sind über identische BBox findbar (§6f).

## 6i. Ortsrecords und Koordinatenkodierung — gegen OSM gefittet (17.09.2026)

**Offline gelöst, ohne Fahrzeugtest.** OSM ist die Grundwahrheit: für jeden
Ortsnamen im Block kennt Overpass die echte Lage. Das ergibt ein
überbestimmtes Gleichungssystem statt der Rateversuche aus §7.

### Recordformat (Sektionsklasse 16)

```
ff ff ff ff │ u16 X │ u16 Y │ u16 ? │ 00 01 03 │ Name (UTF-8) 00
```

Beispiel aus Block B @0x3392334, Offset 17776:

```
ff ff ff ff 38 04 58 00 56 00 00 01 03 48 61 75 73 62 61 79 00
            X=1080  Y=88   ?=86        "Testort"
```

- **X, Y sind relativ zur Kachelecke** aus dem Blockkopf (§3). Der
  Achsenabschnitt des Fits ist +13 m bzw. +43 m, also null.
- **Der Maßstab ist isotrop** — in x und y derselbe Meterwert, obwohl die
  Kachel nicht quadratisch ist (19.548 × 30.528 m). Es ist ein metrisches
  Quantum, **keine feste Einheitenzahl pro Kachelseite**.
- Das dritte u16 liegt zwischen 70 und 114, Vielfache von 2. Vermutlich
  Anzeigepriorität oder Ortsklasse — ungeprüft.
- `00 01 03` ist konstant über alle Records aller geprüften Blöcke.

### Maßstab je Block (`osmfit.py`)

| Block | Kachel | Records | mit OSM | Maßstab | RMS | Breite/Maßstab |
|---|---|---|---|---|---|---|
| L11 Band 1,2M West `@0x3392334` | 19.548 m | 57 | 52 | **17,970** | 177 m | 1087,8 |
| L11 Band 1,2M Ost `@0x346c45e` | 19.548 m | 27 | 12 | **17,909** | 109 m | 1091,5 |
| L11 Band 280k West `@0x36ce94a` | 19.548 m | 57 | 52 | **3,9931** | 177 m | 4895,4 |
| L10 Band 2,5M `@0x2f4009f` | 39.102 m | 155 | 85 | **38,183** | 2160 m | 1024,1 |

Die RMS von ~177 m ist der Abstand zwischen OSM-Ortsmittelpunkt und dem
Ankerpunkt des Navis; bei Dörfern von 500–1500 m Ausdehnung zu erwarten.

### Das Quantum ist exakt bestimmt: runde Meterzahlen

Der Fit über Ortsanker ist auf ±0,07 genau — zu grob. **Schärfer geht es über
die OSM-Stützpunkte der Straßen:** alle u16-Paare des entpackten Blocks in eine
Menge legen, dann für jeden Kandidatenmaßstab zählen, wie viele quantisierte
OSM-Punkte darin vorkommen. Der wahre Maßstab erzeugt einen scharfen Peak.

| Block | Maßstab | Treffer | Rauschpegel | Faktor |
|---|---|---|---|---|
| L11 Band 1,2M `@0x3392334` | **18,0000 m** | 557 | 87 | **6,4×** |
| L10 Band 2,5M `@0x2f4009f` | **38,000 m** | 1007 | 93 | **10,8×** |

Beide Peaks sind auf fünf Tausendstel scharf (bei ±0,005 fällt L11 auf 499/479,
L10 auf 927/884). **Damit sind sowohl Breite/2¹⁰ (19,0898 bzw. 38,1855 m) als
auch die aus Ortsankern gefitteten Krummwerte ausgeschlossen.**

Das Quantum ist also eine **runde Meterzahl je Band**, keine Kachelfraktion und
keine Zweierpotenz. 18 und 38 stehen in keinem einfachen Verhältnis (2,111) —
eine rationale Form ist **nicht** erkennbar und sollte nicht weiter gesucht
werden, solange keine weiteren Bänder vermessen sind. Für den 280k-Block liefert
dieselbe Methode **keinen** Peak (bestes 2,6× bei s=4,98): dort stehen
offenbar keine Straßenstützpunkte als absolute u16-Paare, der Ortsanker-Fit
(3,993, verträglich mit 4,0) bleibt der einzige Wert.

### Was damit geht

- **Ein Ortslabel an eine gewünschte Position setzen:** `X = dx/s`, `Y = dy/s`
  mit dx, dy gegenüber der Kachelecke. Genauigkeit rund eine halbe Labelbreite.
- **Offline prüfen statt fahren.** Jede Änderung an Ortsrecords lässt sich
  gegen OSM nachrechnen, bevor die Karte ins Auto geht.

### Datenbestand

`osm/places.pkl` — 625 benannte Orte (node/way/relation mit `place`-Tag) im
Raum 50,05–50,32 N / 7,30–7,62 E, bereits nach Mercator umgerechnet.
`osm/osm_west.json` — 8,4 MB `highway`-Wege der Westkachel, für den nächsten
Schritt: dieselbe Methode auf die **Polyliniengeometrie** anwenden. Dort gibt
es keine Ankerunschärfe, damit lässt sich das Quantum exakt festnageln und
§7.3 (absolute Platzierung) schließen. Abfragen in `osm/*.overpass`.

## 6j. Straßenrecords — Stützpunkte sind absolut, nicht delta (17.09.2026)

**§4 und §7.3 sind überholt.** Die Rahmung „Polylinien sind deltakodiert, der
Startpunkt ist unbekannt" stimmt nicht: der **erste Stützpunkt steht absolut**
da, in genau denselben Kacheleinheiten wie die Ortsrecords aus §6i.

### Nachweis

OSM-Wege der Westkachel nach §6i quantisiert (`X=(x−X0)/s`, `Y=(y−Y0)/s`,
s = 17,9695 m) und ihre Endpunkte als `struct('<HH')` im entpackten Block
gesucht:

| | Block B `@0x3392334` | 280k-Block `@0x36ce94a` |
|---|---|---|
| Endpunkte in der Kachel | 17.762 | 17.771 |
| davon exakt als u16-Paar gefunden | **66** | **0** |
| Zufallsbasis (gleichverteilte Koordinaten im gültigen Bereich) | 18 | 6 |
| Faktor | **4,1×** | — |

> **Korrektur einer früheren Fassung.** Hier stand „1.355 Treffer gegen
> Zufallserwartung 2,1". Beides war falsch: die 1.355 entstanden mit ±2
> Toleranz in beiden Achsen, also 25 Mustern je Endpunkt, und die Erwartung
> 2,1 war über 2³² gerechnet, als wären alle u16-Paare gleich wahrscheinlich.
> Echte Koordinaten liegen nur in einem Bereich von ~1.086 × 1.696. Die
> richtige Nullhypothese misst man, indem man gleichverteilte Koordinaten aus
> genau diesem Bereich im Block sucht. Der Befund bleibt, die Stärke war um
> zwei Größenordnungen überzeichnet. Mit dem exakten Maßstab 18,0 (siehe §6i)
> steigen die Treffer auf 557 bei Rauschpegel 87.

**Gegenprobe über den Namen** — trägt der Record hinter dem Startpunkt den
Namen, den OSM für genau diesen Weg führt?

| | |
|---|---|
| Startpunkt exakt gefunden (ohne Toleranz, benannte Wege) | 11 |
| davon mit dem **eigenen** OSM-Namen innerhalb 160 B dahinter | **5 (45 %)** |
| Kontrolle: zufällige Koordinaten, 2.000 Versuche | **0 (0,0 %)** |

### Recordformat

```
u16 X │ u16 Y │ <gepackte Deltas, variabel> │ 00 03 │ Name (UTF-8) 00
```

Belegte Beispiele aus Block B:

```
@10512  8c 02 f8 03 │ 09 0a │ 01 00 03 │ "Pfarrer-Muster-Straße" 00
        X=652 Y=1016   (OSM quantisiert: 652, 1016)

@10050  51 01 0c 05 │ 22 32 65 21 20 30 31 10 11 13 12 07 04 11 10 2f 10 10 01 01 01 │ 00 03 │ "Bergweg" 00
        X=337 Y=1292

@ 8103  8a 00 80 00 │ 21 32 86 0a 63 83 08 62 32 a8 80 12 2a 00 80 11 29 00 │ 01 05 00 │ …
        X=138 Y=128    (OSM quantisiert: 138, 128)
```

Der 3-Byte-Tag vor dem Namen ist derselbe wie bei den Ortsrecords (§6i), nur
permutiert — dort `00 01 03`, hier `01 00 03` bzw. `00 03`. Die genaue
Feldaufteilung ist **offen**.

### Was als Nächstes zu tun ist

### Die Deltakodierung ist gelöst (17.09.2026)

```
u16 X │ u16 Y │ Deltabytes │ 00 │ 03 │ Name (UTF-8) │ 00
```

**Ein Byte je Stützpunkt: hohes Nibbel = dy, niedriges Nibbel = dx, beide
4-bit Zweierkomplement (−8..+7). `0x00` beendet die Geometrie**, danach leitet
`03` den Namen ein. Die Bytes, die §6j vorher als unverstandenen „Tag" führte,
sind genau dieser Terminator plus Namensmarke.

Maximaler Schritt ±7 Einheiten = ±126 m bei 18 m Quantum.

### Wie es bestimmt wurde

Bewertung geometrisch: alle OSM-`highway`-Segmente der Kachel rastern, dann
messen, welcher Anteil rekonstruierter Stützpunkte auf einer Straßenzelle
landet. Zellengenau, ohne Dilatation. **Erst ab dem dritten Schritt zählen** —
sonst misst man nur, dass der Startpunkt auf einer Straße liegt. Kontrolle sind
**dieselben Bytes, gemischt**, also identische Bytestatistik.

Entscheidend war der Vergleich der Varianten untereinander, nicht gegen Zufall:

| Variante | auf Straße | eigene Kontrolle | Differenz |
|---|---|---|---|
| **Zweierkomplement, dy hoch / dx niedrig** | **32,1 %** | 19,8 % | **+12,4** |
| zigzag, dx hoch | 20,7 % | 19,8 % | +0,9 |
| Zweierkomplement, dx hoch | 17,8 % | 17,2 % | +0,6 |
| offset-8, dy hoch | 14,9 % | 14,3 % | +0,6 |
| zigzag, dy hoch | 21,7 % | 21,6 % | +0,1 |
| offset-8, dx hoch | 14,1 % | 14,8 % | −0,7 |

Fünf Varianten liegen flach auf ihrer eigenen Kontrolle, eine springt heraus.
`0x00` als **Terminator** statt als Nullschritt hebt die Quote weiter von
32,1 % auf **43,3 %** (≤1 Zelle: 62,5 %).

Eine Bitbreitensuche über w = 3..10, Startbitversatz 0..15, Zweierkomplement
und zigzag, beide Achsenreihenfolgen — 512 Konfigurationen — findet dieselbe
Lösung als klaren Spitzenreiter (1,90× gegen 1,57× beim Zweitplatzierten).

### Verifikation

| | |
|---|---|
| Records mit ≥3 Punkten, alle Punkte in der Kachel | 125 |
| davon mit einem Namen, den **OSM auch kennt** | **106 (84 %)** |
| Stützpunkte gesamt, davon auf einer OSM-Straße | 41,1 % |
| **richtig verankerte Einzelrecords** | **85–96 %** |

Beispiele: `Rhein-Mosel-Straße` @12783 → 25 Punkte, **96 %** auf Straße;
@12076 → 25 Punkte, 92 %; `Waldstrecke` @9158 → 26 Punkte, 85 %.

### Recordrahmung — Anker gefunden, Trennschärfe fehlt

Vor **26 von 26** verifizierten Records steht dasselbe Muster:

```
[80 11 <v> 00] │ 01 <n> <f> │ u16 X │ u16 Y │ <n> Deltabytes │ 00 03 │ Name │ 00
```

- Byte −3 ist `0x01` bei **26/26**, Byte −4 `0x00` bei 26/26, Byte −6 `0x11` bei 26/26.
- **`<n>` ist die Zahl der Deltabytes**, also Stützpunkte − 1. Geprüft:
  26 Punkte → `0x19`, 22 → `0x15`, 16 → `0x0f`, 8 → `0x07`. Die Länge steht
  damit im Kopf; der `0x00`-Terminator ist nur ein zweiter Weg.
- Die Gruppe `80 11 <v> 00` fehlt bei manchen Records — das Format ist
  **TLV-artig mit optionalen Feldern**, nicht fest.

Zwei vollständige Records nebeneinander:

```
@10468  80 11 24 00 │ 01 07 00 │ 77 02 df 03 │ 12 22 33 11 31 11 01 │ 00 03 │ "Mittelstraße" 00
@10505  80 11 29 00 │ 01 02 20 │ 8c 02 f8 03 │ 09 0a …
```

**Records liegen lückenlos aneinander** — eine frühere Fassung behauptete das
Gegenteil; das war ein Fehler in meiner Endoffset-Rechnung. Zwischen zwei
Records stehen genau **7 Byte**:

```
<Name> 00 │ 01 <v> 00 │ 80 11 <v−1> 00 │ 01 <n> <f> │ u16 X │ u16 Y │ Deltas │ 00 03 │ <Name> 00
```

`<v>` zählt herunter (`01 2a 00 80 11 29 00`, dann `01 2d 00 80 11 2c 00`). Die
zweite Gruppe ist optional — manche Records haben statt `80 11 <v> 00` nur `00`.

**Sequentiell lesen statt Muster suchen** hebt die Qualität um das Dreifache:

| Verfahren | Records | Stützpunkte auf Straße | Name in OSM |
|---|---|---|---|
| naiver Ankerscan über `01 <n> <f>` | 307 | 31,4 % | 64 % |
| **sequentiell, `n` Deltabytes** | 38 | **89,8 %** | 84 % |
| sequentiell, +1 wenn `f & 0x30` | 57 | 79,5 % | 89 % |

Zehn Records erreichen 100 % (`Gödenrother Straße`, `Schulstraße`, `Höhenweg`,
`Bergweg`, `Mittelstraße`, `Grüntal`, `Bodenheck`, `In der Huhl`, `Grieshof`,
`Höhenkammstraße B 1`).

### Die `f & 0x30`-Regel ist widerlegt — `n` ist immer exakt

Statt einen Zählwert anzunehmen, die **tatsächliche** Zahl der Deltabytes bis
zum `00 03` messen:

| Flag | Records | gemessen − `n` | auf Straße | Name in OSM |
|---|---|---|---|---|
| `0x00` | 38 | **0 bei allen 38** | **89,4 %** | 32/38 |
| `0x10` | 39 | 1, 2, 3, 4, 5 — variabel | 48,9 % | 36/39 |
| `0x20` | 1 | 1 | 33 % | 1/1 |

**`n` ist also immer die exakte Deltazahl.** Bei `f=0x10` stehen hinter den
Deltas 1–5 **Zusatzbytes** vor dem `00 03`, die fast immer auf `01` enden —
offenbar ein TLV-Feld. Die frühere Regel las sie als Deltas mit und erzeugte
Geisterschritte.

**`f=0x10` benutzt eine andere Kodierung — die 48,9 % sind ein Artefakt.**
Die Records sind echt (36 von 39 Namen kennt OSM), aber ihre Deltabytes sind
keine Nibbelschritte. Belege:

**Trefferquote je Schritt** — `f=0x00` bleibt flach, `f=0x10` zerfällt ab dem
dritten:

| Schritt | 1 | 2 | 3 | 5 | 7 | 10 | 12 |
|---|---|---|---|---|---|---|---|
| `f=0x00` | 90 % | 90 % | 94 % | 90 % | 90 % | 100 % | 89 % |
| `f=0x10` | 75 % | 68 % | **39 %** | 45 % | 38 % | 33 % | 43 % |

Der Startpunkt liegt bei `f=0x10` zu **95 %** auf einer Straße (f=0x00: 97 %),
die ersten ein, zwei Schritte bleiben in dessen Nähe — danach läuft der Pfad
weg. Die 48,9 % messen also **Nähe zum Startpunkt, nicht richtige Dekodierung.**

**Bytestatistik bestätigt es:** bei `f=0x00` haben nur **12 %** der Schritte
|d| ≥ 5, bei `f=0x10` sind es **44 %**. Das wären 44 % Sprünge über 90 m — für
eine Straßenpolylinie unsinnig. Die Bytes sind etwas anderes.

**Geprüft und ausgeschlossen** (f=0x10, gegen f=0x00 als Kontrolle):

| Gegenhypothese | f=0x10 | f=0x00 |
|---|---|---|
| Nibbel dy/dx (Standard) | 48,9 % | **89,4 %** |
| i8-Paare dx,dy / dy,dx | 14,2 % / 10,3 % | — |
| Nibbel vertauscht | 11,4 % | — |
| X,Y bei +4 / +5 statt +3 | 0 % / 4 % | 0 % |
| Deltas bei +8 statt +7 | 24,3 % | 33,8 % |
| Schrittmultiplikator ×2 / ×3 / ×4 | 22,4 / 16,7 / 16,5 % | 22,3 % |
| **Fortsetzung: Start = Endpunkt des Vorgängers** | **14,9 %** | — |
| Fortsetzung: Start = Startpunkt des Vorgängers | 19,1 % | — |

Die Fortsetzungs-Hypothese aus einer früheren Fassung dieses Abschnitts ist
damit **widerlegt**.

Implementierung: `roadrec.py`, `parse_section(raw, start, W, H)`.

### Zwei TLV-Tags vor dem Anker

**Zwei TLV-Tags sind identifiziert:** `80 12 <v> 00` und `80 11 <v> 00` stehen
vor dem Anker, beide mit gesetztem höchsten Bit. Beispiel, vollständig lesbar:

```
@8117  80 12 2a 00 │ 80 11 29 00 │ 01 05 00 │ e7 01 2d 00 │ 5e 4e 3f 51 01 │ 00 03 │ "Gödenrother Straße" 00
                                    n=5 f=0    X=487 Y=45    genau 5 Deltas
```

Alle verifizierten Straßenrecords liegen zwischen Offset 8125 und 15358, also
in **Sektion 16** (ab 7709, §6h). Deren Anfang enthält aber auch andere
Recordtypen — bei 7709 steht `… 02 00 03 │ "Friedhof Herschwiesen"`, also ein
POI mit `02` statt `01` vor dem Namensmarker.

### Der Decoder trägt über Kacheln und Level

Dieselbe Funktion, nur mit dem jeweiligen Quantum (§6i) und dem Sektionsstart
aus der Sektionstabelle (§6h):

| Block | Level | Maßstab | Records `f=0x00` | auf Straße | Name in OSM |
|---|---|---|---|---|---|
| B, Westkachel `@0x3392334` | L11 | 18 m | 38 | **89,4 %** | 32/38 |
| C, Ostkachel `@0x346c45e` | L11 | 18 m | 31 | **89,3 %** | 26/31 |
| L10-Straßenblock `@0x2f4009f` | L10 | 38 m | 60 | **85,8 %** | 50/60 |

Zusammen **129 Records bei rund 88 %** über drei Blöcke und zwei Level. Längste
sauber gelesene Linienzüge: `Forstbachstraße` 39 Punkte zu 97 %,
`Goldbachstraße` 24 zu 88 %, `Waldstrecke` 18 zu 89 %.

**Korrektur (18.09.2026): Testort liegt in der WESTkachel, nicht in der
Ostkachel.** Der alte Satz an dieser Stelle war ein Namenstreffer-Fehlschluss —
`Testort` kommt in Block C zweimal vor, aber keines der beiden Vorkommen ist
sein Ortsrecord:

```
Block C @2075   d7 01 80 01 │ X=3 Y=86 │ 00 08 00 03 │ "Testort"
Block C @15815  01 09 00 │ X=87 Y=118 │ 9 Deltas │ 00 03 │ "Testorter Straße"
```

Das erste ist ein **Punktlabel im Format des 280k-Bands** (§6j), am Westrand
der Ostkachel angeklemmt; das zweite die Zufahrtsstraße im Nachbarort, 1,2 km
weiter östlich. Der echte Ortsrecord steht in **Block B**:

| | |
|---|---|
| Ortsrecord Block B | X=1080 Y=88 → **50,1 N / 7,5 E** |
| Kachelgrenze West\|Ost | 840479 m = 7,5 E |
| Abstand zur Grenze | **108 m** |

Gegenprobe an OSM, alle Stützpunkte im Umkreis von ~1,2 km um die Ortsmitte:

| | West | Ost |
|---|---|---|
| alle Stützpunkte | **392 (80,8 %)** | 93 |
| `Hauptstraße` | 12 | 1 |
| `Höhenkammstraße B 1` | 7 | 0 |
| `Kelsitstraße` | 4 | 0 |
| `Nachbarorter Straße` | 23 | 15 |

**Testorts Dorfstraßen gehören also in Block B `@0x3392334`** — ausgerechnet
der Block, der das Label auf allen Zoomstufen gewinnt (§6h Test 11) und in dem
der Geometrietest bestanden wurde (`geotest.py`, `P=0x3392334`). Für Ziel 3 ist
das die bestmögliche Ausgangslage: die Zielkachel ist dreifach im Fahrzeug
bewährt.

**Falle bei der Umrechnung:** §6b nennt die Kopffelder `minX, maxY, maxX,
minY`. Der Ursprung der kachelrelativen Koordinaten ist aber das **2. Feld**
(so macht es `roadrec.py` richtig) — wer das 4. nimmt, landet 19 km zu weit
nördlich.

### Randrecords: die Bereichsprüfung hat Testorts Dorfstraßen verschluckt (18.09.2026)

`roadrec.py` verwarf jeden Record, dessen Stützpunkte nicht **vollständig**
in `0..W × 0..H` lagen. Straßen am Kachelrand ragen aber legitim darüber
hinaus — und Testort liegt **108 m vor der Ostgrenze** seiner Kachel.

Betroffen sind genau die beiden Dorfstraßen, um die es bei Ziel 3 geht:

```
@8872   80 11 23 00 │ 01 07 00 │ X=1075 Y=95 │ c2 f1 e2 01 02 13 01 │ 00 03 │ "Hauptstraße"
@8943   80 11 2b 00 │ 01 07 00 │ X=1085 Y=75 │ 2d 10 2f 21 10 14 01 │ 00 03 │ "Nachbarorter Straße"
```

Beide strukturell einwandfrei, beide 0,1 bzw. 0,2 km von der Ortsmitte. Der
einzige Grund für die Ablehnung: **ein** Stützpunkt läuft auf X=1087, eine
Einheit über die Kachelbreite W=1086 — 18 m.

**Die Toleranz ist nicht frei gewählt, sie sättigt:**

| Toleranz | ±0 | ±1 | ±2 | ±4 | ±8 | ±16 | ±32 |
|---|---|---|---|---|---|---|---|
| B, Westkachel | 38 | **41** | 41 | 41 | 41 | 41 | 41 |
| C, Ostkachel | 31 | **32** | 32 | 32 | 32 | 32 | 32 |
| L10 | 119 | 119 | 119 | 119 | 119 | 119 | 119 |

Ein zu laxes Kriterium sammelt mit wachsender Toleranz immer mehr Falschtreffer
ein. Hier passiert ab ±1 nichts mehr — die vier zusätzlichen Records sind echt.
**Endgültig belegt durch den Selbsttest:** `roadwrite.py` rekonstruiert sie
byteidentisch, 192/192 statt 188/188.

`parse_section(raw, start, W, H, tol=1)`, Vorgabe `tol=1`.

**Einschränkung, die damit sichtbar wird:** die „89,4 % gegen OSM" aus dem
vorigen Abschnitt sind an dieser Stelle ein **Selektionseffekt** — gewertet
wurden nur Records, die vollständig in der Kachel liegen. Randrecords fehlten
in der Stichprobe.

**Für Ziel 3 heißt das:** Testorts Dorfstraßen sind **schon da**, sie waren nur
unsichtbar. Es geht um Verfeinern und Ergänzen, nicht um Aufbauen von null.
Von den drei benannten Wegen, die OSM im Umkreis von 1 km kennt, fehlt genau
einer: **`Kelsitstraße`**.

### Ziel 3 ist längenneutral machbar — durchgerechnet (18.09.2026)

Die fehlende `Kelsitstraße` aus OSM durch `to_units` → `densify` → `record`:

```
01 03 00 │ X=1078 Y=81 │ 11 02 01 │ 00 03 │ "Kelsitstraße" 00      = 26 B
```

4 OSM-Stützpunkte, keine Verdichtung nötig (alle Schritte ≤7 Einheiten). Mit
der 7-B-Rahmung **33 B Payload**. Eingefügt hinter `Nachbarorter Straße`
@8964, Rahmung vom Nachbarn übernommen.

Gemessen am vollen Encodersweep, Block B, Extent 13.832:

| Bau | Payload | bester Strom | gegen Extent |
|---|---|---|---|
| Original | 20.467 | 13.836 | +4 |
| + `Kelsitstraße` | 20.500 (+33) | 13.856 | +24 |
| + `Kelsitstraße` − 1× `Moselbrücke` | 20.460 (−7) | 13.841 | +9 |
| **+ `Kelsitstraße` − 2× `Moselbrücke`** | **20.423 (−44)** | **13.830** | **−2** |

Und der Extent lässt sich **exakt treffen**: der volle Sweep über den letzten
Payload liefert **8 Einstellungen mit genau 13.832 B** (`BT2`/12 die erste).
Also keine toten Bytes, Invariante gewahrt.

**Damit braucht Ziel 3 den Wachstumstest nicht.** Eine neue Straße kostet zwei
gestrichene Duplikate. Faustzahl aus diesen Messungen: **33 B Payload ≈ 20 B
Strom**, gestrichene Records ≈ 40 % ihres Payloads an Strom.

**Der Preis ist eine Nutzerentscheidung, keine technische.** Streichkandidaten
sind mehrfach vorhandene Namen, alle >15 km von Testort:

| Name | Vorkommen | Recordlängen |
|---|---|---|
| `Moselbrücke` | 5× | 30, 33, 24, 27, 26 |
| `Bergweg` | 3× | 24, 38, 22 |
| `Waldstrecke` | 2× | 46, 43 |
| `Rhein-Mosel-Straße` | 2× | 53, 41 |

Ob zwei der fünf `Moselbrücke`-Segmente weichen dürfen, entscheidet der Nutzer
— technisch ist der Bau fertig durchgerechnet. Fällt der Wachstumstest (`w1`)
positiv aus, entfällt das Streichen ganz.

### Ortbeta (Region) gefunden: `@0x34b2003` (18.09.2026)

Der zweite Ort aus Ziel 3, mechanisch über die Block-BBoxen aus
`gw_blockmap.pkl` gesucht und dann per Stringtreffer bestätigt:

| | |
|---|---|
| Block | `@0x34b2003`, Extent 15.510, entpackt 23.254 |
| Kachel | 8,0..8,2 E, Breite 19.548 m — **dasselbe Level wie Block B** |
| 5. Kopffeld | 1.202.902 (Straßenband 1,2M, wie Block B mit 1.200.115) |
| Quantum | 18 m |
| Ortsrecord | @21176, X=857 Y=607 → **50,3 N / 8,2 E**, `Ortbeta (Region)` |
| Sektion 16 | ab **10838** |
| Records `f=0x00` | **16**, davon 2 im Ort |

```
 0,10 km  n= 8  Dauborner Straße
 0,42 km  n= 9  Brunnenstraße
 1,97 km  n= 3  Hof Meistergraben
 2,25 km  n= 6  Mühlstraße
 …
```

`Dauborner Straße` und `Brunnenstraße` sind Ortbeta' Ortsstraßen — das
bestätigt die Verortung inhaltlich, unabhängig von der Referenzkoordinate.
Auch **Ortbeta (Westerwald)** liegt in der Datei (`@0x348de7d` im selben Band),
falls der falsche Ort erwischt wurde.

**Nebenergebnis: der Sektionsstart ist für jeden Block mechanisch bestimmbar.**
`validate.sections(raw)` liefert die Tabelle Klasse → Offset; für Block B ergibt
Klasse 16 den Wert **7709** — exakt den bisher von Hand ermittelten. Damit ist
`parse_section` auf jeden beliebigen Block anwendbar, nicht nur auf die drei
bekannten.

```
Block B          [(5,25) (8,6) (9,8) (10,6309) (13,7545) (16,7709)]
Ortbeta (Region) [(4,29) (5,99) (8,5) (9,1) (10,8643) (13,10204) (16,10838)]
```

**Was für Ortbeta noch fehlt:** OSM-Grundwahrheit. `spike/osm/` deckt nur die
Westkachel um Testort ab; für 8,09..8,26 E müsste eine weitere
Overpass-Abfrage laufen, analog `osm/q.overpass`.

### Rückwärts bewiesen: 192 von 192 Records byteidentisch rekonstruiert

`roadwrite.py` ist die Umkehrung von `roadrec.py`. Der Selbsttest liest jeden
`f=0x00`-Record, kodiert dessen Geometrie und Namen zurück und vergleicht die
Bytes:

| Block | Records | byteidentisch |
|---|---|---|
| B, Westkachel | 41 | **41** |
| C, Ostkachel | 32 | **32** |
| L10-Straßenblock | 119 | **119** |
| **gesamt** | **192** | **192** |

(vorher 188/188 — die vier zusätzlichen sind Randrecords, siehe unten)

**Das ist kein statistisches Argument mehr, sondern exakt.** Jedes Byte jedes
Straßenrecords entsteht wieder aus der dekodierten Geometrie plus Namen — über
drei Blöcke und zwei Level. Das Format ist damit für `f=0x00` vollständig
verstanden.

### Vorwärts: OSM → Recordbytes

```
Nachbarorter Straße, 32 OSM-Punkte
  → densify()          Schrittgrenze ±7 Einheiten = ±126 m bei 18 m Quantum
  → 23 Stützpunkte     (Nullschritte entfallen, 0x00 wäre Terminator)
  → 52 B Record        01 16 00 │ 01 00 5a 00 │ f1 df f0 0f … │ 00 03 │ Name 00
  → zurückgelesen      identische Punkte, identischer Name
  → 50,1 N, 7,5 E — mitten in Testort
```

**Werkzeuge:** `roadwrite.py` — `to_units()`, `densify()`, `encode_deltas()`,
`record()`. Selbsttest mit `python3 roadwrite.py`.

**Fallstrick:** `decode()` aus `roadrec.py` erwartet den Offset der **Koordinate**,
nicht des Recordanfangs — also `decode(rec, 3)`, nach dem 3-B-Kopf `01 <n> <f>`.

### Platzbudget: es gibt keines

Bestes erreichbares liblzma-Ergebnis für den **unveränderten** Payload, voller
Sweep bei props 93 (`mf` × `nice_len` × `depth`):

| Block | Extent | bestes liblzma | Budget |
|---|---|---|---|
| B, Westkachel (**Testort**) | 13.832 | 13.836 | **−4 B** |
| C, Ostkachel | 15.241 | 15.253 | **−12 B** |
| L10-Straßenblock | 15.490 | 15.479 | **+11 B** |

Der Originalencoder ist ein paar Byte besser als liblzma. **Für neue Inhalte ist
kein freier Platz da** — deshalb war bei Test 11 die Markerwahl nötig, um die
Länge überhaupt zu treffen. Ein Straßenrecord kostet 20–50 B unkomprimiert.

Daraus folgen drei Wege, zwei davon mit ausschließlich bewiesener Mechanik:

1. **Ersetzen statt hinzufügen** — einen entbehrlichen Straßenrecord
   überschreiben. Längenneutral, sofort machbar.
2. **Platz schaffen durch Löschen** — mehrere Records raus, mehrere rein. Bei
   18 m Quantum ist ein Campingplatzweg zwei bis drei Stützpunkte, also ~20 B.
3. **Block wachsen lassen** — der saubere Weg, aber **offen**: die Tests, die das
   zu verneinen schienen (§6d Test 4, §6h Tests 5/8/9), sind durch den
   LZMA-Kopf-Fehler entwertet. Ein Fahrzeugtest beantwortet es.

### Offen: der Zähler `<v>` in der Zwischenrecord-Gruppe

`01 <v> 00` steht hinter jedem Record, optional gefolgt von `80 11 <v−1> 00`.
Über 21 aufeinanderfolgende Records geprüft: `<v>` (Werte 22, 27, 42, 36, 16,
15, 100, 22, 39 …) entspricht **nicht** der Deltazahl des folgenden Records
(2/21), **nicht** dessen Punktzahl (1/21) und ist **nicht monoton**.

Zwölf Hypothesen an **183–185 Records** über drei Blöcke geprüft, gegen den
vorigen **und** den folgenden Record:

| Hypothese | Treffer |
|---|---|
| `v` == Namenslänge (±1) | 8/185, 6/185 |
| `v` == Recordlänge (−7) | 4/185, 1/185 |
| `v` == `n` / Punktzahl | 1/185, 0/185 |
| `v` == `n` + Namenslänge (+2) | 4/185, 3/185 |
| `v` == Recordlänge − Namenslänge | 9/185 |
| `v` == `n` / Punktzahl / Namenslänge / Recordlänge des **folgenden** | 2, 2, 3, 2 von 183 |
| `v` == Abstand zum folgenden (−3) | 0/183, 0/183 |
| `v` == Abstand − 7 | 28/183 (15 %) |

Wertebereich 11..100, kein Gerade/Ungerade-Bias (89/94), keine Korrelation mit
irgendeiner Länge, Anzahl oder Position. Auch der beste Kandidat mit 15 % ist
bei stark schwankenden Abständen Zufall.

> **WIDERLEGT (24.09.2026, §6l):** `<v>` ist die Innenlänge `L−1` des folgenden Elements.

**Schlussfolgerung, vorsichtig formuliert: `<v>` ist kein struktureller Zähler.**
Nichts deutet auf eine Nummerierung hin, die beim Einfügen fortzuschreiben wäre
— vermutlich ein Straßenattribut (Klasse, Breite, Tempolimit oder eine
Referenz-ID). **Einfügen ist damit voraussichtlich gefahrlos**, solange ein
plausibler Wert mitgegeben wird. Bewiesen ist das nicht; ein Wachstumstest, der
einen **bestehenden Record verlängert**, umgeht die Frage ganz und sollte
deshalb zuerst kommen.

**Messfalle:** die L10-Kachel ist doppelt so breit wie eine L11-Kachel und
reicht über die Westkachel hinaus. Gegen `osm_west.json` allein ergibt das
31,6 %; nur Records innerhalb des tatsächlich abgedeckten OSM-Fensters gewertet,
sind es 85,8 %. Für Level-übergreifende Auswertungen die Abdeckung prüfen.
`osm/osm_east.json` (12 MB, Ostkachel) liegt jetzt ebenfalls bereit.

### Geometrietest BESTANDEN (18.09.2026) — Geometrie ist schreibbar

`geotest.py` → `…geo.psf`, `67d30b41b6bfd408`. Basis Test 11. Geändert: die
neun Deltabytes von `Ortsgammaer Straße` @12474.

```
alt:  3d 1f 3f 4f 3f 2e 2e 2d 01   realer Verlauf
neu:  07 07 70 70 09 09 90 90 20   geschlossenes Quadrat
```

Kenndaten des Baus:

| | |
|---|---|
| Lage | 50,1 N / 7,5 E, Mitte des Quadrats (1,5 km nördlich Testort) |
| Kantenlänge | 252 m (7 Einheiten je Schritt, 2 Schritte je Kante) |
| Vernier | letztes Deltabyte `0x20` **und** Marker `Manneba` → `Belthei` |
| Strom | exakt 13.832 == Extent, 13-B-Kopf byteidentisch |
| `validate.py` | **0 Fehler** |

**Ergebnis im Fahrzeug: das Quadrat ist sichtbar, genau bei Grünpfad.**

Damit ist die Deltakodierung **auch geräteseitig bestätigt** — vorher war sie
nur gegen OSM belegt. Der Schreibweg für Geometrie ist offen.

**Unabhängige Bestätigung des Koordinatenmodells:** der Nutzer verortete das
Quadrat spontan „genau in Grünpfad". Grünpfads Ortsrecord liegt bei
(1064,2 / 227,5), die Quadratkanten bei X 1066–1080, Y 215–229 — **zwei
Einheiten = 36 m daneben**. Die ganze Kette aus Kachelecke, Quantum 18 m,
absolutem Startpunkt und Deltas stimmt damit end-to-end.

**Kantenlänge:** rechnerisch 14 Einheiten × 18 m = 252 m. Eine erste Schätzung
„ca. 100 × 100 m" wurde zurückgezogen. Sie stand ohnehin gegen eine harte
Messung: `Waldstrecke` überspannt 719 m Luftlinie über 26 Stützpunkte und liegt
noch bei Schritt 10–12 zu ~90 % auf der echten Straße (§6j) — bei 7 m/Einheit
wäre der Zug nur 280 m lang und könnte das nicht.


### Der Nahzoom-Block hat eine ANDERE Geometriekodierung

`@0x36ce94a` (Band 280k, liefert z1–z9, Quantum ~4 m) speichert Straßen
**nicht** als absolute u16-Paare:

| | Block B (18 m) | 280k-Block (4 m) |
|---|---|---|
| Maßstabspeak über OSM-Stützpunkte | **18,000 m, 6,4×** | **keiner** (bestes 2,5× bei 3,79) |
| Ankermuster mit gültigen Koordinaten | 307 | 122 |
| davon mit `00 03` dahinter | **88** | **1** |

Die Ortsrecords dieses Blocks fitten dagegen sauber bei ~4 m (§6i). Straßen
müssen dort also anders kodiert sein.

**Unterzellen-Hypothese widerlegt.** §3 nennt einen Unterzellen-Index in groben
Kacheln; läge einer vor, wären Koordinaten relativ zur Unterzellenecke und eine
absolute Suche müsste fehlschlagen. Getestet über `(x mod G, y mod G)` für
G = 512, 1024, 2048, 4096, 65536 und s = 4; 4,5; 8; 9; 18, mit einer
Nullverteilung aus denselben OSM-Punkten um einen Zufallsversatz verschoben
(fünf Versätze je Zelle):

| Block | bestes Signal | Treffer | Null | Faktor |
|---|---|---|---|---|
| Block B (Kontrolle, s=18 bekannt) | s=18 | 557 | 20–28 | **20–28×** |
| 280k-Block | s=18 | 60 | 11–17 | 3,6–5,5× |

**Das Gitter macht keinen Unterschied** — 2048, 4096 und 65536 liefern im
280k-Block identisch 60 Treffer. Es gibt dort keine Unterzellenstruktur. Und
das schwache Signal liegt bei 18 m, nicht bei den 4 m seiner eigenen
Ortsrecords.

**Entscheidend:** ein Ankerscan über `01 <n> <f>` + gültige Koordinaten +
`00 03` + Name findet im 280k-Block **null** Records — in beiden Rastern (18 m
und 4 m). Das Recordformat aus §6j kommt dort schlicht nicht vor. Die 60
Koordinatentreffer gehören zu etwas anderem.

### Aufgelöst: das 280k-Band ist gar kein Straßenblock

Der Nahzoom-Block hat sehr wohl absolute Koordinaten, nur mit **anderem
Recordkopf**:

```
d7 01 80 01 │ u16 X │ u16 Y │ 00 <n> 00 03 │ Name (UTF-8) 00
```

**104 Records** mit diesem Muster, Medianabweichung **245 m** gegen die
OSM-Ortslagen bei Maßstab 4,0 — verträglich mit der Ankerunschärfe aus §6i.
Zwischen Koordinate und Name stehen **keine Deltabytes**: das sind Punkte, keine
Linien.

Der Inhalt erklärt den Rest: `Mosel` siebenmal mit verschiedenen Koordinaten,
`Park`, `TSV Nachbarstadt`, `Sportplatz Nachbardorf`, dazu Dörfer. Nur **5**
OSM-Straßennamen kommen überhaupt vor (Block B: 88).

### Alle acht `Testort`-Blöcke, systematisch

| Block | Level | 5. Feld | Straßenrecords `01 <n> <f>` | Punkt/Fläche `d7 01 80 01` |
|---|---|---|---|---|
| `@0x2f4009f` | L10 | 2.518.191 | **120** | 0 |
| `@0x2f34830` | L10 | 2.513.886 | 20 | **223** |
| `@0x3392334` | L11 | 1.200.115 | **41** | 77 |
| `@0x346c45e` | L11 | 1.201.252 | **32** | 87 |
| `@0x36ca22e` | L11 | 287.708 | 3 | **118** |
| `@0x36ce94a` | L11 | 279.612 | 2 | **106** |
| `@0x29d48b8` | — | 420.937.729 | 0 | 0 |
| `@0x3b25e2a` | — | 6.457.562 | 0 | 0 |

Die beiden letzten haben unsinnige BBox-Werte und gehören zu einem anderen
Abschnitt. **Der Paarsplit aus §6d Test 3 ist damit systematisch bestätigt:
innerhalb jedes Kachelpaares trägt ein Block die Straßen, der andere Flächen
und Punkte.** Im 280k-Band liegen die Flächen, im 1,2M-Band die Straßen.

### Konsequenz für Ziel 3 (Campingplatzwege)

**18 m ist die feinste verfügbare Straßenauflösung über Testort** — nicht wegen
fehlenden Formatverständnisses, sondern weil L11 die tiefste Datenstufe ist
(§6a) und der Straßenblock dieser Kachel mit 18 m quantisiert. Das 280k-Band ist
zwar viermal feiner, führt aber keine Straßengeometrie.

Damit sind **Dorfstraßen in Testort und Ortbeta schreibbar**, Wege auf dem
Campingplatz in ihrer tatsächlichen Feinheit **nicht**. Ob ein Weg als grobe
Polylinie bei 18 m überhaupt sinnvoll erscheint, wäre ein Fahrzeugtest wert,
bevor Aufwand in feinere Darstellung fließt.

**Für das Ziel ist das der Engpass:** Campingplatzwege sind bei 18 m Quantum
(Block B) nicht darstellbar, sie bräuchten den Nahzoom-Block. Dorfstraßen in
Testort und Ortbeta sind dagegen in Block B schreibbar.

**Werkzeuge:** `roadrec.py` (Decoder, `decode()` und `to_wgs84()`),
`bitfit.py` (Suchgerüst mit Rasterbewertung und Mischkontrolle).

## 7. Offen

1. **Test 11 auswerten** (§6h) — der erste Bau mit byteidentischem
   LZMA-Kopf und exakter Stromlänge. Zeigt z10+ `Manneba`/`Badenha`?
2. **Feldsemantik der bit-gepackten Nutzrecords** (Links, Knoten, Attribute) —
   nötig, um *neue* Geometrie zu erzeugen statt nur Namen zu ersetzen.
5. **Knotensemantik des Namens-Tries** im Endabschnitt (§6c) — die Kette ist
   lesbar, der Kopf jedes Knotens nicht.

**Erledigt, nicht mehr offen:** der „komprimierte Index der zweiten Stufe" war
bis 09.09.2026 als Engpass Nummer 1 geführt. Für die relevanten Blöcke gibt es
ihn nicht — die Einträge stehen im Klartext (§6b).

**Korrektur:** der Satz „der zweite Blocktyp (§4) ist der Schlüssel zu den
tiefen Level" ist überholt. Die tiefen Level liegen in regulären L10/L11-Kacheln
(§6a), und deren Indexeinträge sind gefunden.

### Sauber widerlegte Hypothesen — nicht wiederholen

- **„Kein Encoder schlägt das Original" (§6a):** Selektionseffekt einer Suche,
  die `lc/lp/pb` festverdrahtet und `BT2` sowie kleine `nice_len` nie probiert
  hat. Voller Sweep bei props 93: unveränderter Payload +4 statt +27, und mit
  passend gewähltem Marker **exakt auf den Extent**. Siehe §6h.
- **„Für die tiefen Level ist ein schreibbarer Index nötig":** folgte aus dem
  vorigen Punkt und fällt mit ihm. Die Blöcke passen in ihre Originallänge.
- **Vier Erklärungen für die Abstürze der Tests 5, 8, 9, 10** — Bandwechsel,
  Blockwachstum, Markerinhalt, „Gerät liest bis zum nächsten Block statt die
  Indexlänge". Alle vier waren nur zufällig mit dem echten Defekt korreliert,
  einem kaputten 13-Byte-LZMA-Kopf in den Bauskripten (§6h). Keine dieser vier
  Fragen ist damit beantwortet — sie sind **offen**, nicht widerlegt, und
  dürfen erst nach einem sauberen Bau wieder getestet werden.
- **Blockkennung als NDS packed Tile ID:** alle 25 Level-Bit-Positionen gegen
  6 Regionen gleichzeitig — **0,0 % in jeder Variante**. Die *Kennung* ist ein
  Katalog; die Kachel*geometrie* im Blockkopf ist dagegen NDS-konform.
- **Absolute Koordinaten in Grad:** 13 Skalierungshypothesen (NDS 2³²/360,
  1e-5/1e-6/1e-7, Milliarcsec, 2²³..2³⁰/360), signed und unsigned, mit
  Paarbedingung — 0 Treffer. Es sind **Mercator-Meter**.
- ~~**Startpunkt als uint16-Paar vor dem Deltalauf:** 0 gültige.~~
  **Aufgehoben 17.09.2026:** genau das ist es (§6j). Die alte Prüfung suchte im
  falschen Blocktyp und ohne die Kacheleinheiten aus §6i. `2e 03 ed 03` bleibt
  eine Schemakonstante.
- **Startpunkt als bit-gepacktes 10/11/12-Bit-Paar:** Containment-Test **trennt
  nicht** — bei Raster 4096 und Pfadausdehnung ~35 bleibt fast jeder Startpunkt
  drin. 97 % erreichen ein Dutzend verschiedene Bit-Offsets. Kein Ergebnis.
- **Offsettabelle im zweiten Blocktyp (Big-Endian @0x10):** an drei
  handverlesenen Blöcken passte es exakt, über 827 Blöcke nur **0,6 %**. Das war
  Selektionseffekt — die Integralitätsprüfung trifft zufällig in ~50 % der Fälle.
- **Delta-Diskriminator auf Byte-Läufen im großen Indexblock:** kein Unterschied
  zur gemischten Kontrolle (36,4° gegen 35,5°). Die Läufe dort sind nur
  entropiearme Bereiche. Polylinien stehen in **Blattkacheln** direkt hinter dem
  Kopf.
- **Frühere „Koordinatentreffer" in Blockköpfen:** Artefakte der
  uint16-Offsettabelle, deren gleichmäßige Inkremente zufällig plausible
  Gradwerte erzeugen.
- **Record mit Key = 1:** existiert nicht, war ein Überlese-Artefakt am
  Tabellenende.
- **Namensbestand des Tries durch Rasterscan extrahieren (§6c):** liefert
  **1,4 Mio. Pseudoketten**. Einige Blöcke des Endabschnitts enthalten
  gewöhnlichen JSON-Text; im 3-Byte-Raster gelesen ergibt der beliebig lange
  „Namen". Nur lange, spezifische Suchbegriffe sind belastbar — ein
  vollständiger Bestand geht nur über echte Traversierung ab einer Wurzel.

---

## 8. Referenzen

Das Format ist der **Navigation Data Standard**, gemeinsam entwickelt von
Herstellern und Zulieferern (BMW, Bosch, Harman, HERE). Maßgeblich hier:
**NDS Format Specification 2.5.4**, §7.2.1 Koordinaten, §7.3.1 NDS Tiles.

- NDS Association — <https://nds-association.org/>
- Offene Spezifikationen — <https://www.nds.live/specs>
- GitHub-Organisation — <https://github.com/ndsev>
- Referenzimplementierung Tiling/Koordinaten (MIT) —
  <https://github.com/limingchina/nds_tile>
- Java-Implementierung — <https://github.com/rondiplomatico/nds-tiles>

---

## 9. Für das Spiel

Für einen Routing-Algorithmus braucht es *ein* Straßennetz mit Geometrie, nicht
*dieses*. OpenStreetMap liefert das sofort, dokumentiert und lizenzklar (ODbL) —
osmium/pyrosm, fertige Graphen über GraphHopper oder OSRM. Der `.psf`-Weg trägt
für das, was OSM nicht hat: diesen Datenstand ECE 2020/21, die
HERE-Regionsaufteilung, die georeferenzierte Namensstatistik.

---

## 10. Dateien

**Ergebnisse:**

| Datei | Inhalt |
|---|---|
| `Malta_tiles.geojson` | 2.007 Kachelpolygone mit `nds_packed_tile_id` |
| `Malta_tile_names.csv` | 510 Straßennamen mit Kachel-ID und BBox |
| `render2.svg` | Kachelpyramide + Polylinien für Testort/Niederortbeta |
| `GermanyWest_Basic.patched.psf` | **akzeptierter §6-Bau, Basis aller Tests** — `e3511640b2148cae` |
| `GermanyWest_Basic.t11.psf` | **Test 11, Fahrzeugtest offen** — `15137c5fcaf8d2b2` (§6h) |
| `…reloc.psf` / `…reloc2.psf` / `…t5.psf` / `…t8.psf` / `…t9.psf` / `…t10.psf` | **entwertet, kaputter LZMA-Kopf** (§6h) — nicht wiederverwenden |
| `…swap.psf` / `…dup.psf` / `…t6.psf` / `…t7.psf` | gültige Indextests ohne Rekompression |
| `gw_anchors.pkl` | 76.003 Anker — **Achtung: „Länge" ist der Ankerabstand, nicht die Stromlänge** (§6g) |
| `gw_blockmap.pkl` | 76.003 × (Offset, **echte** Stromlänge, Abstand, entpackte Größe, Byte+20, 5. Kopffeld, BBox) |
| `gw_tiles.pkl` | Kachelblöcke über Testort/Niederortbeta |
| `testort_blocks.pkl` | 8 Blöcke mit `Testort` |
| `patch.pkl` | Patchdaten |

**Übernehmbar:** `nds.py` (NDS-Mathematik, gegen Referenz validiert),
`mkpatch.py` (Blockpatch mit Größenerhalt), `relopatch.py` (**Blockpatch mit
Verschiebung, ohne Längenzwang**), `idxscan.py` (Ankerliste, gecacht),
`export2.py`, `closeloop.py`, `render2.py`. Alles andere ist
Wegwerf-Analysecode.

| Datei | Zweck |
|---|---|
| `entropy.py`, `payload.py`, `repeats.py`, `period.py` | Entropie, Chi², Wiederholungsmetrik gegen Zufall validiert |
| `records.py`, `hdr.py`, `hdr2.py`, `idxdump.py`, `hdrdiff.py` | Indextabelle und Kopf zerlegen |
| `blocks.py`, `lzma_test.py` | **125/125 — der entscheidende Container-Test** |
| `generalize.py` | Blockfund ohne Index, alle Content-Typen |
| `allbases.py` | **Kachelbasis aller 52 Regionen — Katalogbeweis** |
| `blockschema.py` | Blockinneres `_AdvancedRouting`, verifiziert |
| `basic.py`, `basicidx.py`, `solveunit.py`, `solve2.py` | `_Basic`-Index |
| `mercator.py`, `mercgrid.py`, `fitR.py`, `fitR2.py` | **Mercator-Hypothese und Radiusfit** |
| `proof.py` | **Ende-zu-Ende: Raster 99,8 %, POI-Gegenprobe** |
| `geom1-4.py`, `leaf.py`, `poly1.py`, `poly2.py`, `startpt.py` | Unterzellen-Array, Polylinien, 10-Bit-Befund |
| `type2.py`, `type2b.py`, `unknown.py` | Zweiter Blocktyp |
| `findplace.py`, `grab.py`, `pickblock.py`, `ctx.py` | Ortssuche in Regionsdateien |
| `slack.py`, `search.py`, `proto.py`, `mkpatch.py` | **Akzeptanztest** |
| `idxscan.py`, `idxmap.py`, `idxlayout.py`, `idxwalk.py`, `idxfind.py`, `idxhit.py`, `idxrec.py`, `idxdup.py` | **`_Basic`-Index (§6b)** |
| `hdrfields.py`, `slackmeas.py`, `cover.py`, `cover2.py` | Kopffelder, Blockabstände, Indexabdeckung |
| `blockmap.py` | **Vollvermessung aller Blöcke** → `gw_blockmap.pkl` (§6g, §6h) |
| `fitsearch.py` | Parametersuche: passt der Marker in die Originallänge? (§6h) |
| `test11.py` | **kanonischer Blockbau** — `build()` zieht den 13-Byte-Kopf nach (§6h) |
| `test5.py`–`test10.py` | Fahrzeugtests 5–10, **alle durch den Kopffehler entwertet** |
| `tail1.py`–`tail5.py` | **Endabschnitt als Namensindex (§6c)** |
| `osmfit.py` | **Koordinatenkodierung gegen OSM gefittet (§6i)** |
| `roadrec.py` | **Decoder für Straßenrecords (§6j)** — `decode()`, `to_wgs84()` |
| `bitfit.py` | Suchgerüst: Rasterbewertung gegen OSM, Mischkontrolle |
| `deltafit.py` | erster Anlauf, feste Breiten — ausgeschlossen |
| `validate.py` | Bau gegen alle Invarianten prüfen — **Indexteil noch zu langsam, neu schreiben** |
| `osm/` | OSM-Grundwahrheit: 625 Orte, 8,4 MB Straßen der Westkachel, Overpass-Abfragen |
| `crchunt.py`, `swaptest.py`, `duptest.py` | **Fahrzeugtests §6d** |
| `deeppatch.py`, `finalpatch.py`, `relopatch.py` | Patchbau |
| `coords.py`, `morton.py`, `findtiles.py`, `gridfit.py`, `levelbit.py`, `paircheck.py`, `stride24.py` | Negativergebnisse (§7) |
| `names.py`, `streets.py`, `enc.py` | Namensextraktion, UTF-8-Nachweis |
