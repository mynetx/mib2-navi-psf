# The MIB2 `.psf` map format

This is the consolidated specification of everything learnt about the `.psf`
map files on a VW/Audi MIB2 navigation SD card. It is distilled from the
German lab journal [`FINDINGS.md`](../FINDINGS.md). The journal is
chronological and often corrects itself; this document states only the latest
result. References like "(journal §6j)" point to the journal section with the
evidence, the measurements and the dead ends.

All multi-byte integers are **little-endian** unless stated otherwise.
Offsets written `@0x…` are absolute file offsets in `GermanyWest_Basic.psf`
of the card described below. Offsets written `@1234` (decimal) are offsets
inside a **decompressed** block.

## Confidence labels

Every claim carries one of these labels:

| Label | Meaning |
|---|---|
| **[vehicle]** | Verified in the car: a modified file was loaded by the head unit and the predicted effect appeared on screen. |
| **[OSM]** | Verified offline against OpenStreetMap ground truth, with a control (shuffled bytes or random coordinates). |
| **[data]** | Verified mechanically over the whole file or a large sample (counts given), with no vehicle test. |
| **[hypothesis]** | Consistent with the data, not proven. |
| **[disproven]** | Tested and ruled out. Do not repeat. |

## Contents

1. [The card](#1-the-card)
2. [File container](#2-file-container)
3. [Blocks: LZMA-alone streams](#3-blocks-lzma-alone-streams)
4. [Tile identification](#4-tile-identification)
5. [Georeferencing](#5-georeferencing)
6. [The `_Basic` block index](#6-the-_basic-block-index)
7. [Inside a `_Basic` tile block](#7-inside-a-_basic-tile-block)
8. [Layer pairs, bands and zoom levels](#8-layer-pairs-bands-and-zoom-levels)
9. [Coordinates inside a tile: units and quantum](#9-coordinates-inside-a-tile-units-and-quantum)
10. [Place and point records](#10-place-and-point-records)
11. [Section 16: the street chain](#11-section-16-the-street-chain)
12. [Street records and delta geometry](#12-street-records-and-delta-geometry)
13. [The end section: name index (trie)](#13-the-end-section-name-index-trie)
14. [Other content types and files](#14-other-content-types-and-files)
15. [Field semantics: known vs. unknown](#15-field-semantics-known-vs-unknown)
16. [Disproven hypotheses](#16-disproven-hypotheses)

---

## 1. The card

| | |
|---|---|
| Medium | 8 GB SD card, FAT32, volume label `NO NAME` |
| `DBInfo.txt` | PartNumber `8V0060866M`, SW `0094`, SystemName `ECE 2020/21` |
| Data | HERE (NavTeq) in the **Navigation Data Standard (NDS) 2.5.4** |
| Build timestamp in file header | `0x5DF14EDB` = 2019-12-12 |
| Free space | about 40 MiB of 7.5 GiB. You can replace data, but there is little room to add any. |
| Map files | `markets/eu/map/MapRegions/*.psf` |

**Inventory** (journal §5): 54 regions, 161 `.psf` files, 6 content types:
`Basic` (41), `BasicWithPointAddress` (12), `AdvancedRouting` (52),
`GlobalPOIIndices` (52), `ExtZips` (3), `MountainPolygons` (1). File names are
`<Region>_<ContentType>.psf`, e.g. `GermanyWest_Basic.psf` (79,319,126 B,
76,003 blocks) or `Malta_Basic.psf` (3.3 MB, 5,389 blocks).

**The files are not encrypted and not signed.** [vehicle] Modified files are
accepted (journal §6). A search for a checksum in the file header over 7
ranges × crc32/adler32/sum32/xor32 found nothing [data] (journal §6d Test 1).
No external manifest stores the file size or region names: the region files
are found by directory scan [data] (journal §6d Test 4).

---

## 2. File container

```
0x000    file header      u32 LE fields from offset 2; first two fields 0x3c / 0xf2 constant;
                          build timestamp as Unix time
~0x102   index table(s)   stride depends on content type (§6)
...      data blocks      each one an LZMA-alone stream (§3)
...      end section      name index (§13), from ~67 MB in GermanyWest_Basic
EOF-n    metadata chain   four linked records, ends exactly at EOF
```

### File header fields known so far

| Offset | Type | Meaning | Confidence |
|---|---|---|---|
| `0x04d` | u32 | **exact file size** (79,319,126) | [data] |
| `0x096`, `0x00a`, `0x07a`, `0x035`, `0x04d` | u32 | pointers into the metadata chain at the end of the file (see below) | [data] |
| timestamp field | u32 | build time, Unix seconds | [data] |

### Metadata chain at the end of the file (journal §6b)

Each link is an offset in the header plus a 4-byte length after it. In
`GermanyWest_Basic.psf`:

```
79,314,569 (+132) -> 79,314,701 (+1481) -> 79,316,182 (+2682) -> 79,318,864 (+262) -> 79,319,126 = EOF
```

Four links, arithmetically exact. The chain ends **exactly at EOF in every one
of the 161 files** [data]. The last 262 B are **not a signature**: entropy
4.2 bit/byte, same structure in all files [data]. The contents are unknown.

### No padding anywhere (journal §6g)

The file contains no filler. The longest run of zero bytes in all 79 MB is
6,338 B, and it lies inside an index table (Format D, §6.3). All zero runs
≥ 256 B add up to 48 KB, scattered [data].

There are **five regions in the data area that belong to no block**
(2.79 MiB together). One is the Format D table; the other four are dense,
structured data (entropy 4.8–6.0 bit/byte) with an unknown record format
[data]. They are **not free space**.

| Region | Size | Zero bytes | Entropy |
|---|---|---|---|
| `@0x4539639` | 2,421,380 B | 20.9 % | 5.98 bit/B |
| `@0x4504d96` | 187,072 B | 47.8 % | 4.80 bit/B |
| `@0x4ba364a` | 6,668 B | 29.7 % | 5.82 bit/B |
| `@0x1fe571d` | 42,529 B | 12.2 % | 4.94 bit/B |
| `@0x3ab0873` | 36,844 B | 18.4 % | 5.98 bit/B (Format D table) |

---

## 3. Blocks: LZMA-alone streams

Every data block is a raw **LZMA-alone** (`.lzma`, "LZMA1") stream with the
classic 13-byte header (journal §1):

```
Byte  0      0x5D         LZMA properties byte = 93 -> lc=3, lp=0, pb=2
Bytes 1-4    u32 LE       dict_size
Bytes 5-12   u64 LE       uncompressed size
Bytes 13+    LZMA1 range-coded stream
```

Python's `lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)` decodes them. The
exact compressed length is the input length minus `len(dec.unused_data)`.
Verified on `Malta_AdvancedRouting.psf` (125/125 blocks) and on all 76,003
blocks of `GermanyWest_Basic.psf` [data].

### Invariants (journal Gotcha 2, §6g)

Measured on all 76,003 blocks of `GermanyWest_Basic.psf` [data]. A build that
breaks one of them is no longer testing its own question:

| Invariant | Measurement |
|---|---|
| properties byte | **0x5D (93) without exception** (lc=3, lp=0, pb=2) |
| `dict_size` | **always == uncompressed size** |
| uncompressed-size field | always == uncompressed size (never "unknown") |
| extent − stream length | 0 for 58,807 blocks; exactly 14 for 17,185 blocks (a Format C record follows, §6.3); only 5 exceptions (the unclassified regions above) |

`0x5D` followed by `dict_size == size` is a strong anchor: blocks can be found
without any index (`spike/idxscan.py`).

### The 13-byte header gotcha

**Python's `lzma.compress(..., format=FORMAT_ALONE)` writes a header that the
head unit does not accept** (journal Gotcha 1). It rounds `dict_size` up to the
next liblzma step and writes the uncompressed size as "unknown":

```
original:        5d f3 4f 00 00  f3 4f 00 00 00 00 00 00   dict=20467  size=20467
lzma.compress:   5d 00 60 00 00  ff ff ff ff ff ff ff ff   dict=24576  size=2^64-1
```

Five vehicle tests (four head-unit crashes, one rejection) were lost to this
before it was found. Fix: compress, then **overwrite both fields** and check
the round trip (see `spike/test11.py`, `build()`):

```python
f = [{'id': lzma.FILTER_LZMA1, 'dict_size': len(data), 'lc': 3, 'lp': 0, 'pb': 2,
      'mode': lzma.MODE_NORMAL, 'mf': mf, 'nice_len': nl, 'depth': dp}]
o = bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=f))
struct.pack_into('<I', o, 1, len(data))   # dict_size == uncompressed size
struct.pack_into('<Q', o, 5, len(data))   # size      == uncompressed size
chk = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
assert chk.decompress(bytes(o)) == data and len(chk.unused_data) == 0
```

With this header a re-compressed block is loaded and rendered [vehicle]
(journal §6h Test 11).

Do not use `pb=0`, although it compresses better: it breaks the one constant
the file keeps without exception, and embedded decoders often have
`lc/lp/pb` compiled in [hypothesis].

### Hitting the original length to the byte (journal §6h)

liblzma is **4–12 B worse** than HERE's encoder on unchanged payloads
(full sweep at props 93 over `mf` × `nice_len` × `depth`) [data]:

| Block | Extent | best liblzma | Budget |
|---|---|---|---|
| `@0x3392334` (L11 road layer) | 13,832 | 13,836 (`BT2`/16/0) | −4 B |
| `@0x346c45e` (L11 road layer) | 15,241 | 15,253 | −12 B |
| `@0x2f4009f` (L10 road layer) | 15,490 | 15,479 | +11 B |

A narrow sweep that fixes `lc/lp/pb` and never tries `BT2` or small
`nice_len` misses these optima. That is why an early claim that "no encoder
beats the original" was wrong [disproven].

To make a modified block exactly as long as the original stream: sweep the
encoder settings **and** choose replacement text that already occurs in the
block (LZMA matches it cheaply), e.g. candidates from
`re.findall(rb'[A-Z][a-z]{6}', plain)`. With this, two blocks were rebuilt to
exactly their original length, with a byte-identical 13-byte header
[vehicle] (journal §6h, `spike/fitsearch.py`, `spike/test11.py`).

Rule of thumb from measurements: 33 B of new payload ≈ 20–24 B of stream.

Blocks may also **grow** (stream and uncompressed payload), see §6.5.

---

## 4. Tile identification

### Block key: a catalogue, not an NDS packed tile ID (journal §2)

```
key = (layer << 21) | (1000 · region_number + tile_index)
```

[data] The tile bases of **all 52** `_AdvancedRouting` regions are exact
multiples of 1000 (52/52). Almost every region has **exactly 408 tiles**,
independent of its area (exceptions: Malta 124, Iceland 342, Kaliningrad 362).
Found independently in payload records: `59 c7 80` read as u32 `0x0080c759` =
layer 4, tile 51033 = Malta (base 51000), index 33.

The key is **not** an NDS packed tile ID: all 25 level-bit positions tested
against 6 regions, 0.0 % hits [disproven]. The tile *geometry* is NDS
conformant though (§5).

Region numbers (HERE-internal; 50000 unused; full list via
`spike/allbases.py`):

| No. | Region | No. | Region |
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

## 5. Georeferencing

### Spherical Mercator with R = 6,371,000 m (journal §3)

Tile bounding boxes are stored as **Mercator metres**:

```
x = R · λ
y = R · ln(tan(π/4 + φ/2))          λ, φ in radians, R = 6,371,000 m
```

Derivation [data]: tiles are square in degrees (Δλ == Δφ), so
`cos φ = width / height` gives the latitude without knowing R, and then
`R = y / ln(tan(π/4 + φ/2))`. Median over **8,830 tile estimates**:
R = 6,370,917 m, 0.0013 % from the mean Earth radius. It is **not** WGS84's
6,378,137 m. Cross-check of `height/width = 1/cos φ`:

| Region | Width | Height | measured | 1/cos φ |
|---|---|---|---|---|
| Malta (36°) | 4886 | 6048 | 1.238 | 1.235 |
| Portugal (39.5°) | 2442 | 3141 | 1.286 | 1.295 |
| Denmark (56°) | 2445 | 4390 | 1.795 | 1.789 |
| Iceland (65°) | 2443 | 5908 | 2.419 | 2.366 |

Absolute coordinates in degrees (NDS 2³²/360, 1e-5/1e-6/1e-7,
milliarcseconds, 2²³…2³⁰/360, signed and unsigned) were tested and give 0 hits
[disproven].

### Tile grid

A level-L tile is **360/2^L degrees** wide, i.e. `2πR / 2^L` metres in
Mercator x. Tile edges are exact binary fractions of 360°
(e.g. 14.0625 = 40 × 0.3515625). 99.7 % (2586/2595) of west edges lie within
2 % of a grid line; random would be 4 % [data].

| Level | Width in Mercator metres | Example |
|---|---|---|
| L10 | 39,102 m | |
| L11 | 19,548 m | a GermanyWest tile is 19,548 × 30,528 m at 50° N |
| L14 | 2,443 m | `2πR/2^14 = 2443.22`, matches the observed base width 2442–2445 |

Malta has 2,595 tiles on **levels 6–15**. Over the GermanyWest test area the
deepest data level is **L11** [vehicle].

### NDS compatibility (journal §3)

`nds_level = L − 1`. The NDS tile number is the Morton interleave of
(col, row) with col in the even bits, and
`packed_id = tileNr + (1 << (16 + nds_level))`. Checked against the public
reference implementation (limingchina/nds_tile): 6/6 exact [data]. Example:

```
L12 col 164 row 408 -> nds_level 11, tileNr 181904, packedId 134399632
   own bbox   lon[14.4141, 14.5020] lat[35.8594, 35.9473]
   nds.py     lon[14.4141, 14.5020] lat[35.8594, 35.9473]
```

`spike/nds.py` contains the NDS tile maths.

### Sub-cell index in coarse tiles (journal §3)

Coarse tiles contain an array of absolute Mercator coordinate pairs (int32,
stride 8), with an **exact power-of-four count** (1024, 256, 64, 16), in
**Z-order**, step `360/2^14`. For an L9 tile that is 32 × 32 = 1024 sub-cells;
grid fit 1024/1024, Z-order 1024/1024 (random expectation 0.000018) [data].
An equally long array of zero bytes follows (empty references). What the
sub-cells point to is unknown. They do **not** make tile-relative coordinates
sub-cell-relative (tested for grids 512…65536, journal §6j) [disproven].

### Content cross-check

Names found in a tile are located in that tile (Malta: southern tile → a
southern street, northern tile → a northern street; place test 5/5, 5/7, 5/8)
[data].

---

## 6. The `_Basic` block index

### 6.1 Top-level index tables per content type (journal §1)

| Content type | Table at | Stride | Layout | Confidence |
|---|---|---|---|---|
| `_AdvancedRouting` | `0x102` | 20 | `u32 offset, u32 len, u32 key, 8 B reserved` | [data] |
| stride-24 (`MountainPolygons`, `WorldCartographicLayer_Basic`) | `0x10e` | 24 | `u32 offset, u16 len, u16 counter, 16 B` | [data] 77/77 and 10/10 via `offset + len == next offset` |
| `_Basic` | `0x32e` | 32 | `key @+4, offset @+8`, two-level | [data] |

`_Basic` cannot fit a record per block before the first data block (Malta:
room for ≤ 2,270 records, but 5,389 blocks). Some index levels are themselves
LZMA blocks. **But for the tile blocks that matter, the (offset, length) pairs
are stored as plain text** in the formats below (journal §6b).

### 6.2 Plain-text record formats

**Format A: tile record, 24 B** (region around `0x74000–0x7c000` in
GermanyWest_Basic):

```
+0   i32  minX         Mercator metres, R = 6,371,000
+4   i32  maxY
+8   i32  maxX
+12  i32  minY
+16  u32  block offset  absolute in the file
+20  u16  block length  compressed
+22  u16  flags         0 (95 %), 1, 2, 3 -- meaning unknown
```

Note the bbox order **minX, maxY, maxX, minY**, which differs from the block
header (§7.1). Verified on 5,558 records [data]: maxY-before-minY order
5,557/5,558; `(height/width)/(1/cos φ)` median 0.9999. So tile geometry can be
read **without decompressing a block**. Levels L5–L15, mostly L12–L14.

**Format B: layer-pair record, 32 B** (from `0x10e`):

```
+0   u32  key           (layer << 21) | (1000 · region + tile_index)
+4   u32  offset A
+8   u16  length A
+10  u32  offset B
+14  u16  length B
+16  16 B bbox          as in Format A
```

Verified: `offset + length == offset of the previous record` for **794**
consecutive records in both columns (the table runs in descending offset
order) [data]. First record's key `0x03001790` = layer 24, tile 6032 =
GermanyWest (base 6000) + 32. It registers the layer pairs of §8.

**Format C: 14 B record between data blocks:**

```
01 00 00 00 00 00 00 03 | u32 offset | u16 length
```

Directly after the LZMA stream of 23 % of the blocks (17,185 in
GermanyWest_Basic). This explains the "extent = stream + 14" invariant. It is
not padding [data].

**Format D: 6 B, reversed field order** (journal §6e):

```
+0   u16  block length  compressed
+2   u32  block offset  absolute
```

Lives in an unclassified region (`@0x3ab0873`, 36,844 B). Related blocks sit
next to each other, stride 6, densely packed. Example at `@0x3ab1eb1`:

```
fa 3a | e7 ff 46 03   -> length 15098, offset 0x346ffe7
ce 1a | 90 a9 46 03   -> length  6862, offset 0x346a990   (its layer partner)
```

### 6.3 Coverage (journal §6b, §6c)

| | |
|---|---|
| Blocks total (GermanyWest_Basic) | 76,003 |
| with a plain-text (offset, length) entry | 42,222 (55 %) |
| without an entry | 33,781, of which 33,179 are < 1 kB |

The blocks without an entry are almost all in the end section (name index,
§13), which is addressed differently.

Most tile blocks examined have **one** Format A/B entry and **one** Format D
entry. Some have no Format D entry (two of the eight blocks in the journal's
table). Byte patterns that look like extra hits when read at an offset of two
bytes are **overlap artefacts** of these two formats (journal §6g "w1").

### 6.4 What the head unit actually uses

| Fact | Confidence |
|---|---|
| The plain-text index (Formats A/B) decides what is loaded. A block removed from it disappears from the screen; a redirected entry loads the other block, even with a different bbox. | [vehicle] Tests 3, 7 |
| The **length** in a Format A record is not needed for loading: overstating it by 18 B changed nothing. The device does not walk blocks as a strict `offset + length` chain. | [vehicle] Test 6 |
| The **bbox in the block header** places the content, not the bbox in the index record. Shifting the header bbox 5 km east moved the drawn content 5 km and left a 5 km gap over the full tile height. | [vehicle] Probe 1 |
| The index area is not integrity-checked. | [vehicle] Test 2 |
| Format D alone does not decide loading: Test 3 left the Format D entry in place and the block still disappeared. Whether Format D is used at all is unknown. | [vehicle] / open |

### 6.5 Rewriting, growing and moving blocks

| Operation | Status |
|---|---|
| Rewrite a block at the **same compressed length** (correct 13-byte header, exact stream length) | works [vehicle] Test 11 |
| **Grow** a block's stream past its extent into the immediately following block, after redirecting **both** of that neighbour's references (Format A **and** D) to its layer partner **in the same band**, and updating the grown block's length in both of its references | works [vehicle] `w1`, +64 B stream |
| Grow the **uncompressed payload** too (new `dict_size`/`size` in the header, still equal to the real size) | works [vehicle] `z3`, +33 B payload; largest accepted growth +342 B stream (`d1`, `f1`) |
| Grow two blocks in two bands in one build | works [vehicle] `d1`, `f1` |
| Grow the **file** (append or move blocks, update size field `@0x04d` and the metadata chain pointers) | **open**. Both tests were rejected but are void because of the broken 13-byte header (§3) |
| How far a block may grow | open (tested up to +342 B; the largest neighbour available offered 15,098 B) |
| Redirect a neighbour across bands (e.g. 280k → 1.2M) | open (the test that did this crashed, but also had the broken header) |

---

## 7. Inside a `_Basic` tile block

### 7.1 Block header (decompressed payload, journal §3, §6a, §6f, §6l)

```
+0    i32   minX      Mercator metres
+4    i32   minY
+8    i32   maxX
+12   i32   maxY
+16   u16   uncompressed block size        (2256/2263 Malta tile blocks = 99.7 %)
+18   u16   "band" value, see below
+20   u8    unknown, about 250 distinct values -- NOT a global type field
+21…  variable-length fields, then  88 0a <count>
c     u8    number of sections n           (c = 35 in road blocks, 34 in area blocks seen)
c+1   n × (u16 class, u16 offset)          section table, both ascending
```

Header bytes from +20 in two blocks of the same tile:

```
road layer  (+20 = 2):  02 00 00 31 04 23 00 c7 1e 8b 44 ef 4e 88 0a | 06 | 05 00 19 00 …
area layer  (+20 = 1):  01 00 00 04 22 00 e6 38 f1 3a 38 40 88 0a    | 06 | 05 00 19 00 …
```

| Field | Confidence |
|---|---|
| bbox `minX, minY, maxX, maxY` = SW and NE corners | [data] all tile blocks; [vehicle] Probe 1 |
| **origin of tile-relative coordinates = (minX, minY)**, the first two fields | [OSM] [vehicle] |
| +16 = uncompressed size | [data] |
| section count directly after `88 0a`, table right after it | [data] 6 blocks (6, 9, 6, 10, 9, 7 sections); the journal says "byte 35", which is true for road blocks only |
| section offsets are **relative to the count byte**: in all 6 tables the first offset is exactly `1 + 4n` (the byte after the table) | [data], found while writing this document |
| the L10 road block examined has **no section table**: the street group index (§11) starts in the header (`15 22 80 02 00 7f 00` = 21 groups, first offset 127 = 1 + 6 · 21) | [data] |

`validate.sections()` finds the table by scanning bytes 20–60. The journal
and scripts use the section offsets as absolute block offsets (e.g. class 16
"at 7709"). If they are relative to the count byte, the real start is about
35 B later. That is harmless for the scripts, which scan forward from there.

Careful: the journal once said the first four fields are
`minX, maxY, maxX, minY`. That is the order in the **Format A index record**
(§6.2), not in the block header. In the header, taking the 4th field as the Y
origin places everything one tile height too far north.

**The "5th header field" / band.** The journal reads `i32 @+16` as one
number and calls its value range a "band": ~280k, ~1.2M, ~2.5M. Read as two
u16, it is `(value_at_18 << 16) | uncompressed_size`. In all eight blocks the
journal lists, the high half is **4, 18 or 38**, and these are exactly the
measured coordinate quanta of those blocks (≈ 3.99 m, 18.000 m, 38.000 m,
§9):

| "band" (i32 @+16) | = high u16 · 65536 + size | measured quantum |
|---|---|---|
| 279,612 | 4 · 65536 + 17,468 | 3.993 m (place anchors) |
| 1,200,115 | 18 · 65536 + 20,467 | **18.000 m** |
| 2,518,191 | 38 · 65536 + 27,823 | **38.000 m** |

**[hypothesis]** u16 @+18 is the coordinate quantum in metres. Over all
tile blocks whose low half equals the uncompressed size, the high half takes
values like 4, 18, 19, 38, 39, 62, 63, 228–240, 456–483 and varies with level.
This was found while writing this document (not in the journal) and has not
been checked against a third quantum. It would explain why the "band" value
"runs continuously" inside a layer group (journal §6, 21.09): only the size
part varies.

### 7.2 Section classes

| Class | Seen in | Content | Confidence |
|---|---|---|---|
| 9 | area/point layer (quantum 4) | place labels, 58 % of the block in one example | [data] |
| 16 | road layer (quantum 18/38) | the street chain (§11); area blocks have a class 16 too, holding point records | [data] [vehicle] |
| 4, 5, 8, 10, 13, 14 | various | unknown | — |

Example section tables (class, offset):

```
road block A   [(5,25) (8,658) (9,801) (10,6309) (13,7545) (16,7709)]
road block B   [(4,29) (5,99) (8,575) (9,1065) (10,8643) (13,10204) (16,10838)]
```

Class 16 is the last entry in all road blocks examined, so appending to it
moves nothing the table points to [data]. There is no per-record offset
index besides the group index of §11 [vehicle] (`z3` inserted mid-section and
rendered).

### 7.3 `_AdvancedRouting` blocks (journal §4)

```
Byte 0       N = number of records
Bytes 1-2    descriptor (byte 2: 0x00 -> 2-byte records, 0x02 -> 5-byte records)
Bytes 3..    N × u16 offset (first entry always 3 + 2N)
from 3+2N    N × fixed-size record
```

Verified on 5 blocks [data]:

| Block | Header | N | Rec. size | 3 + 2N + N · size = block size |
|---|---|---|---|---|
| Malta L2 | `08 38 00` | 8 | 2 | 19 + 16 = 35 |
| Malta L3 | `a3 38 02` | 163 | 5 | 329 + 815 = 1144 |
| Malta L4 | `ac 38 02` | 172 | 5 | 347 + 860 = 1207 |
| Albania L0 | `fc 37 00` | 252 | 2 | 507 + 504 = 1011 |
| Albania L2 | `86 37 02` | 134 | 5 | 271 + 670 = 941 |

Record semantics (links, nodes, attributes) are unknown.

### 7.4 Second block type (journal §4, started)

Byte 1 is always `0x80`/`0x81` (varint continuation), bytes 5–6 `38 00`,
bytes 9–11 `10 16 00`. Contains tag records:

```
21 00 | a8 a9 | 9e | 59 c7 80      8 B, with a tile reference (key, §4)
20 00 | b8 b9                      4 B, without
```

The pairs move smoothly ((168,169), (166,168), (165,164)), i.e. 8-bit
coordinates inside a cell [hypothesis]. Purpose unknown. It does **not** hold
the deep zoom levels: those are regular L10/L11 tiles [vehicle].

### 7.5 Polylines in leaf tiles (early result, journal §4)

Directly after the header of leaf tiles stand byte-aligned int8 delta pairs
(dx, dy). Direction coherence (net distance / path length) 0.62–0.91 versus
0.10–0.24 for a random walk [data]. This predates the street-record decoding
of §12. The claim "the coordinate field is 10 bits wide" was never proven
[disproven as a conclusion]; the quantum is a metre value (§9).

---

## 8. Layer pairs, bands and zoom levels

### Layer pairs (journal §6a, §6f, §6j)

Tiles come in **groups of blocks with an identical header bbox**. These can be
found mechanically: decompress the first 20 B of every block (76,003 blocks in
0.2 s) and group by bbox [data].

Within a pair, the roles are split [vehicle] (Test 3) [data] (all 8 blocks
around the test village):

| Layer | quantum ("band") | Content | Records `01 n f` (streets) | Records `d7 01 80 01` (points/areas) |
|---|---|---|---|---|
| area/point layer | 4 m at L11 ("~280k") | areas, point labels, place labels | 2–3 | 106–118 |
| road layer | 18 m at L11 ("~1.2M"), 38 m at L10 ("~2.5M") | street lines + their labels | 32–120 | 0–87 |

At L10 the area layer also has a 38 m quantum ("~2.5M"); there the split was
seen in the car: one block drew the area colours, its partner the lines and
labels (Test 3).

Over all 189 L11 tiles of GermanyWest_Basic, group sizes are
1: 90, 2: 83, 3: 15, 4: 1. Groups of two usually hold **two road-layer
blocks**, not road + area [data]. What the second road block is for is
unknown. In one tile next to the test tile, a third block (`@0x3473ae1`, no
readable section table, other names) exists; it is unknown which of the
tile's blocks the device draws (§ open questions).

### Which block serves which zoom level (journal §6a, Test 6, Test 11, §6j)

Measured in the car over the test village (12 zoom steps from near to far,
"z1" = closest) [vehicle]:

| Zoom | **Place label** comes from | Level |
|---|---|---|
| z1–z9 | area/point layer, quantum 4 (`@0x36ce94a`) | L11 |
| z10–z11 | road layer, quantum 18 (`@0x3392334`) | L11 |
| z12 | road layer of the L10 tile (`@0x2f4009f`) | L10 |

- This table is for the **place label only**, not for line geometry. In the
  test tile, street lines exist only in the L11 road block. Coarser levels do
  not carry village streets at all, and there is no finer level [data].
  **Village streets are drawn at z1–z9**; at z10–z11 the device apparently
  does not draw them [vehicle] (`d1`, `f1`).
- With two neighbouring tiles, the label of the **western** tile won on all
  levels; the same change in the eastern tile was never visible
  [vehicle] (Test 11). In general, which of several candidate blocks
  provides the label depends on block content, not on the index entry
  [vehicle] (Test 2).
- The journal's §6a claim that the renderer draws labels from a
  *neighbouring* tile is void: it assumed the village was in the eastern tile,
  which was later corrected (journal §6j).

---

## 9. Coordinates inside a tile: units and quantum

All in-tile records use **u16 X, u16 Y relative to the tile's SW corner**
`(minX, minY)` from the block header, in units of a fixed **metric quantum s**
per block (journal §6i):

```
x_merc = minX + X · s            lon = degrees(x_merc / R)
y_merc = minY + Y · s            lat = degrees(2 · atan(exp(y_merc / R)) − π/2)
```

Inverse (OSM → units), as in `spike/roadwrite.py` `to_units()`:

```
X = (R · radians(lon) − minX) / s
Y = (R · ln(tan(π/4 + radians(lat)/2)) − minY) / s
```

The scale is **isotropic**: the same metre value in x and y, although the tile
is not square (19,548 × 30,528 m). So it is a metric quantum, not "N units per
tile side". An L11 tile at 18 m is about 1,086 × 1,696 units.

### Measured quanta [OSM]

Method: put all u16 pairs of the decompressed block in a set, quantise all OSM
street vertices of the tile with a candidate scale, count hits. The true scale
gives a sharp peak.

| Block | Quantum | Hits | Noise | Factor | Confidence |
|---|---|---|---|---|---|
| L11 road layer | **18.000 m** | 557 | 87 | 6.4× | [OSM], sharp to ±0.005 |
| L10 road layer | **38.000 m** | 1007 | 93 | 10.8× | [OSM], sharp to ±0.005 |
| L11 area/point layer | ≈ 3.99 m (4?) | from place anchors only | | | [OSM], weak |

`width / 2^10` (19.09 and 38.19 m) is excluded [disproven]. 18 and 38 have no
simple ratio; do not look for a rational formula until more levels are
measured. See §7.1 for the hypothesis that the quantum is stored at header
+18.

The whole chain (tile corner, 18 m quantum, absolute start point, deltas) was
confirmed in the car: a square written at computed coordinates appeared
where predicted, within 2 units (36 m) of the nearest place record
[vehicle] (geometry test, journal §6j).

### Resolution limits [vehicle]

| Length | at 18 m quantum | Result |
|---|---|---|
| < 18 m | < 1 unit | disappears |
| ~48 m | 2.7 units, 3 delta bytes | **visible** as its own spur |
| 100–400 m | 6–22 units | shape roughly right |

Two paths closer than 18 m merge; curves become zigzags on the grid. Street
records may extend **1 unit beyond the tile** (e.g. X = 1087 with width
1086): a parser that rejects anything outside `0..W × 0..H` loses real border
streets. A tolerance of ±1 saturates immediately (more tolerance finds
nothing more) [data] (journal §6j "Randrecords").

---

## 10. Place and point records

### 10.1 Place record in road blocks (journal §6i)

```
ff ff ff ff │ u16 X │ u16 Y │ u16 ? │ 00 01 03 │ name (UTF-8) 00
```

Example (place name replaced by `<7-byte place name>`):

```
ff ff ff ff 38 04 58 00 56 00 00 01 03 <7-byte place name> 00
            X=1080 Y=88 ?=86
```

- X, Y as in §9 [OSM]: the fit intercept is +13 m / +43 m, i.e. zero; RMS
  ~177 m is the distance between the OSM village centre and HERE's anchor
  point.
- The third u16 lies between 70 and 114, always even. Display priority or
  place class? [hypothesis, untested]
- `00 01 03` is constant over all records of all blocks checked [data].
- In the road block examined, these records lie after the end of the street
  chain (the journal files them under "section class 16").

### 10.2 Point/area label in area/point layers (journal §6j, §6k)

```
d7 01 80 01 │ u16 X │ u16 Y │ 00 <n> 00 03 │ name (UTF-8) 00
```

In section class 9 of the area/point layer: 91 records of the form
`01 80 01 │ X │ Y │ 00 <n> 00 03 │ name`. There are **no delta bytes**
between coordinate and name: these are points, not lines. Content: place
labels, rivers (the same river name 7× at different positions), parks, sports
grounds. 104 records match within a median 245 m of OSM positions at scale 4.0
[OSM].

`<n>` is unknown. It is **not** the place size (the same place appears with
very different values, e.g. 77/76/13; the correlation r = 0.54 with population
comes only from big places having more records), and not the length of
neighbouring bytes (0/90) [disproven].

The same record type appears in road-layer blocks too (77–87 per block).
One such record had been mistaken for a village's place record; the real
place record is the `ff ff ff ff` form of §10.1 [data].

### 10.3 POI in section 16

At the start of section 16 a different record type occurs, e.g.
`… 02 00 03 │ "<cemetery name>"`, a POI with `02` instead of `01` before the
name marker [data, single example].

### 10.4 Areas (land use)

How land-use polygons are encoded is **unknown** (journal §6k). Ruled out in
the area/point layer: nibble polygons in the `n` bytes before or after a
label (0/89, 0/91, random 1/455), and closed rings among the 557 zero-separated
byte chains of section 9 [disproven]. Visible consequence: a newly written
street lies on the wrong land-use colour; HERE's settlement polygon is simply
smaller than the real built-up area [vehicle].

---

## 11. Section 16: the street chain

Section 16 of a road block is a **gap-free chain of length-prefixed elements
behind a group index** (journal §6l). Fully readable in both road blocks
examined (281 elements from 7988 to 17547; 211 elements from 12059 to 19168)
[data].

```
[n]   n × (class, flags, x, 00, u16 offset)     group index; offsets relative to the [n] byte
chain:  u16 L │ body (L − 2 bytes)              L includes the length field itself
```

### Group index

- `n` = number of groups (18 and 14 in the two blocks).
- Each 6-byte entry: `class (u8), flags (u8), x (u8), 00, u16 offset`.
  The first offset is `1 + 6n` (the first element right after the index).
- **All offsets hit element starts** (18/18, 14/14), sorted ascending [data].
- Example: the group `22 80 03` (class 0x22, flags 0x80, x = 3) holds the
  streets of the test village. The meaning of class/flags/x is unknown;
  spatial sorting by group was ruled out (one group spans X 35–1087,
  Y 45–1575) [data].
- **Inserting or resizing an element requires adding the size difference to
  every later group offset.** `spike/sec16.py` `insert()` / `replace()` do
  this.

### Element bodies

Body types seen as the 2 bytes after `L`: `80 11`, `00 01`, `80 01`, `00 00`,
`80 20`. The named street element:

```
u16 L │ 80 11 │ u16 L−1 │ 01 n f │ u16 X │ u16 Y │ n delta bytes │ {<type> 03 text 00}… │ k
```

| Field | Meaning | Confidence |
|---|---|---|
| `L` | element length including itself | [data] all elements |
| `80 11` + `u16 L−1` | TLV-like tag; the value is the inner length `L − 1` | [data] 73/73 named `f=0` records |
| `01 n f` | street record header (§12) | [data] |
| name entries | `<type> 03 text 00`; type `00` = street name, `03` = road number (e.g. `03 03 B327 00`); one element can carry several | [data] |
| `k` | trailer byte, 1…4; always `01` with a single name; meaning otherwise unknown | [data] / open |

Another TLV tag, `80 12 <v> 00`, can precede `80 11` [data]. Unnamed and other
elements: `u16 L │ 00 01 n f X Y Δ…` and the other body types; not decoded.

So between two consecutive named records there are exactly **7 bytes**:

```
<name> 00 │ 01 │ <L lo> <L hi> │ 80 11 │ <L−1 lo> <L−1 hi> │ 01 n f │ X │ Y │ …
           k    next element's L         next element's inner length
```

e.g. `01 2a 00 80 11 29 00`. (The journal long treated `<v>` as an unknown
"counter" and tested twelve hypotheses against it; all failed because the
framing was wrong. It is the length [data], journal §6l.)

There are **no other pointers** into the chain: neither from the neighbouring
sections 13/14 nor from the 2.4–2.9 KB after the chain (hits at random level)
[data].

### Why framing matters [vehicle]

Four builds inserted records between the name and the trailer byte of an
existing element, without a length prefix and without updating the group
index. Two of them still rendered, one (`e1`) **crashed the head unit** when
displaying tiles. The same probes inserted with correct framing
(`sec16.insert()`) did not crash (`f1`). The broken framing is the only
structural error found in `e1`, so it is the most likely cause, though not
proven. `spike/validate.py` check [12] tests the framing of every changed
block.

### Worked example: building an element

`sec16.named(rec)` turns record bytes `01 n f X Y Δ… 00 03 name 00` into an
element:

```python
L = 2 + 2 + 2 + len(rec) + 1          # L field, 80 11, L-1 field, record, trailer
elem = pack('<H', L) + b'\x80\x11' + pack('<H', L - 1) + rec + bytes([1])
```

A record with 7 deltas and a 12-byte UTF-8 name has
`len(rec) = 3 + 4 + 7 + 2 + 12 + 1 = 29`, so `L = 36` and the element starts
`24 00 80 11 23 00 01 07 00 …`.

---

## 12. Street records and delta geometry

### Record layout (journal §6j)

```
01 │ n │ f │ u16 X │ u16 Y │ n delta bytes │ 00 03 name (UTF-8) 00
```

| Field | Meaning | Confidence |
|---|---|---|
| `01` | record marker | [data] 26/26, then all |
| `n` | **number of delta bytes = vertices − 1, always exact** for `f = 0x00` (38/38 measured) | [data] [OSM] |
| `f` | flags; `0x00` (fully decoded), `0x10` (different geometry, §12.4), also `0x03`, `0x20`, `0x2f`, `0x54` | partly open |
| `X, Y` | **absolute** first vertex in tile units (§9) | [OSM] [vehicle] |
| deltas | one byte per further vertex | [OSM] [vehicle] |
| `00 03 name 00` | first name entry (type `00` = street name, see §11) | [data] |

The first vertex is absolute. Earlier ideas that polylines were pure delta
runs with an unknown start point, or that a record continues from the
previous record's end point, are wrong [disproven].

### Delta byte

```
bit 7..4 = dy, bit 3..0 = dx, each a 4-bit two's complement (−8 … +7)
```

- **High nibble = dy, low nibble = dx.**
- The maximum step is ±7 units (±126 m at 18 m). Longer segments must be
  densified (`roadwrite.densify()`).
- Byte `0x00` (a zero step) never occurs as a delta. Older decoders treat it
  as the geometry terminator; strictly it is the type byte of the first name
  entry, and `n` gives the length. Encoders must skip zero steps
  (`roadwrite.py` does).
- In 73/73 original named `f = 0x00` records of two road blocks, the **last
  delta byte is `01`** (dx = +1). That cannot be a coincidence, so the byte
  probably belongs to the format [hypothesis]. But a visible test record
  ended with `20` (geometry test), so it is not required when an existing
  record is rewritten [vehicle]. Whether a **new** record needs it is open
  (probe B of the unrun build `g1`).

Found by comparing six encodings against their own shuffled-byte controls:
only "two's complement, dy high" stands out (+12.4 points; the others
−0.7…+0.9). A brute-force search over 512 bit-width/offset/sign
configurations found the same winner [OSM] (journal §6j).

### Worked example 1: decoding

A village main street (name replaced):

```
80 11 23 00 │ 01 07 00 │ 33 04 5f 00 │ c2 f1 e2 01 02 13 01 │ 00 03 <name> 00
             n=7 f=0    X=1075 Y=95
```

| Byte | dy | dx | Vertex |
|---|---|---|---|
| start | | | (1075, 95) |
| `c2` | −4 | +2 | (1077, 91) |
| `f1` | −1 | +1 | (1078, 90) |
| `e2` | −2 | +2 | (1080, 88) |
| `01` | 0 | +1 | (1081, 88) |
| `02` | 0 | +2 | (1083, 88) |
| `13` | +1 | +3 | (1086, 89) |
| `01` | 0 | +1 | (1087, 89) |

The last vertex is 1 unit beyond the tile width (1086), the border case of §9.

### Worked example 2: a square written in the car

The geometry test replaced the 9 delta bytes of an existing record
(same length, so the block stayed length-neutral) [vehicle]:

```
old:  3d 1f 3f 4f 3f 2e 2e 2d 01      real course of the street
new:  07 07 70 70 09 09 90 90 20      closed square
      +7x +7x +7y +7y −7x −7x −7y −7y +2y
```

Side 14 units × 18 m = 252 m. It appeared on screen at the computed place.

### Worked example 3: OSM → record (journal §6j "Vorwärts")

A short residential street of 4 OSM vertices, 48 m long:

```
01 03 00 │ 36 04 51 00 │ 11 02 01 │ 00 03 <name> 00        = 26 B record
n=3 f=0    X=1078 Y=81
```

Pipeline in `spike/roadwrite.py`: `to_units()` → `densify(maxstep=7)` →
drop zero steps → `encode_deltas()` → `record()`; then `sec16.named()` and
`sec16.insert()`. This street was inserted and was **visible in the car,
in the right place and direction** [vehicle] (`z3`, `f1`).

### Verification

| Test | Result | Confidence |
|---|---|---|
| Round trip: read every `f = 0x00` record, re-encode geometry + name, compare bytes | **192/192 byte-identical** over 3 blocks and 2 levels | [data] |
| Vertices on real OSM streets (sequential parsing, `f = 0x00`) | L11 tile A 89.4 %, L11 tile B 89.3 %, L10 85.8 %; 129 records at ~88 % (border records excluded) | [OSM] |
| Names OSM also knows | 84 % | [OSM] |
| Start points found as exact u16 pairs | 557 vs. noise 87 | [OSM] |
| Own OSM name after a found start point | 5/11 (random coordinates: 0/2000) | [OSM] |

Parse **sequentially** from the section start, not by pattern search: a naive
anchor scan over `01 n f` gives 31 % of vertices on streets, sequential
reading 89.8 % [OSM]. `spike/roadrec.py` `parse_section(raw, start, W, H,
tol=1)`. Note: `decode(raw, o)` expects the offset of the **coordinate**
(`record start + 3`).

### 12.4 Records with `f = 0x10` (unsolved)

About half of all street records. 36 of 39 names are known to OSM, so the
records are real, but their geometry is **not** decoded by the nibble rule
[OSM]:

- `n` is still exact, but 1–5 **extra bytes** follow the deltas before
  `00 03`, almost always ending in `01` (a TLV field?) [data].
- The start point is on a street 95 % of the time, but the hit rate decays
  from step 3 on (75 %, 68 %, **39 %**, … vs. a flat ~90 % for `f = 0x00`).
- 44 % of nibble steps would be ≥ 5 units (> 90 m), against 12 % for
  `f = 0x00`.

Ruled out [disproven], journal §6j:

| Hypothesis | `f=0x10` | `f=0x00` control |
|---|---|---|
| nibbles dy/dx (standard) | 48.9 % | 89.4 % |
| int8 pairs dx,dy / dy,dx | 14.2 % / 10.3 % | — |
| nibbles swapped | 11.4 % | — |
| X,Y at +4 / +5 instead of +3 | 0 % / 4 % | 0 % |
| deltas at +8 instead of +7 | 24.3 % | 33.8 % |
| step multiplier ×2 / ×3 / ×4 | 22.4 / 16.7 / 16.5 % | 22.3 % |
| start = end point of previous record | 14.9 % | — |
| start = start point of previous record | 19.1 % | — |

### Area/point layers carry no street geometry

In the 4 m layer, an anchor scan for `01 n f` + valid coordinates + `00 03` +
name finds **zero** records, and there is no quantum peak over OSM street
vertices [OSM]. That layer holds points and areas (§10.2). So the finest
street resolution available over the test area is 18 m: village streets and
the main paths of a campsite (100–400 m) can be written, pitch-level detail
(~10 m) cannot.

---

## 13. The end section: name index (trie)

From **block #54408 at `@0x4031174` (67.31 MB)** to the end of
GermanyWest_Basic: 21,595 blocks, 12.0 MB compressed / 18.1 MB
decompressed, median 154 B compressed, many tiny (smallest: 19 B compressed,
1 B decompressed). These blocks have no plain-text index entry
(journal §6c).

Strings are stored in a **3-byte grid `<char> <u16>`**, uppercase,
**Latin-1** (`ß` = 0xdf, `Ö` = 0xd6):

```
06 00 41 b3 01 45 53 04 49 93 07 4f cb 0a 55 c9 0c d6 02 00
42 02 00 45 02 00 4e 02 00 41 02 00 55 02 00 45 02 00 52 ...
B        E        N        A        U        E        R          -> "...BENAUER STRASSE"
```

The u16 after each character is `2` for a linear continuation, or larger for a
branch, apparently a pointer to another block of the section
(`41 b3 01` = `A` → 435 → block #54843) [hypothesis]. The node header (the
leading `06 00`) is **not understood**: it fits neither "6 children" nor "6
bytes of body". Without it the trie cannot be traversed from a root.

What it contains [data]: long specific strings like big-town names (13, 12, 9
hits), `STRASSE` 139 hits. Several small villages that are in the voice
database are **absent**, while a slightly bigger neighbour is present. So it
is not a simple size filter. Most likely the trie indexes **street names**,
and town hits come from street names derived from them
(`<TOWN>ER STRASSE`) [hypothesis].

Pitfall: scanning the whole section in the 3-byte grid yields 1.4 million
pseudo-strings, because some blocks hold plain JSON text. Only long, specific
search terms are reliable; a complete inventory needs real traversal
[disproven as a method].

---

## 14. Other content types and files

- **`vde/common/vde_grammar_plugin/**/*.db`** are plain **SQLite**: 47
  countries, 916,245 places, 5,379,659 street names EU-wide, plus exonyms
  (Aachen → Aix-la-Chapelle, Cáchy, Ахен), states, postcodes. Names only, no
  coordinates; resolution is country level. Directly queryable [data]. A
  village missing from the `.psf` name trie can still be present here (so it
  is enterable as a destination).
- **Phonetics** for voice control live in separate blocks, SAMPA-like, e.g.
  `"haUs|baI|6 "Stra:|s@` for a "…er Straße" [data].
- **`map/styles/{1..4}`** (Audi/VW/Škoda/SEAT): 5,446 PNGs, 13 TTFs, zoom
  parameters.
- **`styles/*/resources/strings/*.xml`**: POI categories in 17 languages with
  voice-control synonyms.
- **Text encoding**: names in `_Basic` blocks are **UTF-8**; Malta has
  4,850 distinct street names, each stored twice, with diacritics and as an
  ASCII fallback [data]. The end-section trie uses Latin-1 uppercase.
- **Region of a place**: detail data for a place exists in exactly one
  region file; neighbouring region files only have coarse overview tiles
  (L6–L8) there [data].

---

## 15. Field semantics: known vs. unknown

| Structure | Known | Unknown |
|---|---|---|
| File header | size @`0x04d`, metadata chain pointers, build timestamp | all other fields |
| Metadata chain | 4 links, ends at EOF, not a signature | content |
| LZMA block | fully | — |
| Block key | `(layer << 21) \| (1000·region + tile)` | meaning of layer numbers |
| Format A | bbox, offset, length | flags @+22 (0–3) |
| Format B | key, two (offset, length) pairs, bbox | which layer is A vs B |
| Format C | offset, length | the constant `01 … 03` prefix |
| Format D | length, offset | whether the device uses it |
| 4 unclassified regions | structured, not free | record format |
| Block header | bbox, size @+16, section count after `88 0a`, section table | +18 (quantum? §7.1), byte +20, the variable bytes before `88 0a` |
| Section classes | 9 = labels, 16 = streets | 4, 5, 8, 10, 13, 14 |
| Group index | offsets | class / flags / x bytes |
| Street element | `L`, `80 11 L−1`, record, name entries, number entries | trailer `k` (1–4), `80 12` value, other body types (`00 01`, `80 01`, `00 00`, `80 20`) |
| Street record `f=0x00` | everything (192/192 round trip) | why the last delta is always `01` |
| Street record `f=0x10` | header, `n`, start point | delta encoding, extra bytes |
| Other flags `0x03 0x20 0x2f 0x54` | exist | everything |
| Place record `ff ff ff ff` | X, Y, name | third u16 (70–114, even) |
| Point label `d7 01 80 01` | X, Y, name | `<n>` |
| Areas / land use | — | encoding |
| Name trie | 3-byte char grid, Latin-1 | node header, root, traversal |
| `_AdvancedRouting` | block framing | record semantics |
| Second block type | tag records with tile key | purpose |
| Sub-cell array | Z-order grid of coarse tiles | what it references |

---

## 16. Disproven hypotheses

Do not repeat these (journal §7):

- **"No encoder beats the original"**: artefact of a narrow parameter sweep
  (§3). Not true.
- **"Deep zoom levels need a writable second-level index"**: followed from the
  previous point. Blocks fit their original length.
- **"Tests 5, 8, 9, 10 crashed because of band change / block growth / marker
  content / reading up to the next block"**: all four builds had the broken
  13-byte header. These questions are **open, not answered**.
- **Block key as NDS packed tile ID**: 0.0 % in every variant.
- **Absolute coordinates in degrees**: 13 scale hypotheses, 0 hits. They are
  Mercator metres.
- **Start point as a bit-packed 10/11/12-bit pair**: the containment test
  does not discriminate.
- **Big-endian offset table at @0x10 in the second block type**: fitted 3
  hand-picked blocks, 0.6 % over 827.
- **Delta discriminator on byte runs in the big index block**: no difference
  from the shuffled control.
- **"Coordinate hits" in block headers**: artefacts of the u16 offset table.
- **Record with key = 1**: an over-read at the end of a table.
- **Quantum = tile width / 2^10**: excluded by the OSM peak (§9).
- **Sub-cell-relative coordinates** in the 4 m layer: no grid makes a
  difference.
- **`f & 0x30` adds a delta byte**: `n` is always exact.
- **`<v>` between records is an attribute or counter**: it is the next
  element's length (§11).
- **An empty name kills the whole street section**: disproven, the streets
  before it were drawn (journal "Korrektur: d1").
- **The 14 B after some blocks / the five unclassified regions are padding**:
  they are Format C records and structured data.
