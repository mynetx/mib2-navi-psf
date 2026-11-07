# Vehicle tests

Every modified map file that went into the car, what it changed, what the head
unit did, and what that proved. Details and build hashes are in the journal
[`FINDINGS.md`](../FINDINGS.md) (§6–§6l). The format itself is described in
[`format.md`](format.md).

All tests used `GermanyWest_Basic.psf` from the card described in the
[README](../README.md). Only that one file was replaced; everything else on
the card stayed original.

**Labels used here.** The test area is a small village ("village A") in an
L11 tile of the GermanyWest region, close to the tile's eastern edge. Its
tiles:

| Label | Block(s) | Role |
|---|---|---|
| **W-road** | `@0x3392334` | west L11 tile, road layer, quantum 18 m |
| **W-area** | `@0x36ce94a` | west L11 tile, area/point layer, quantum 4 m |
| **E-road** | `@0x346c45e` | east L11 tile, road layer |
| **E-area** | `@0x36ca22e` | east L11 tile, area/point layer |
| **L10-road** / **L10-area** | `@0x2f4009f` / `@0x2f34830` | the L10 tile above both, one layer pair |

A "marker" is a 7-letter label that replaced the village name in one block, so
the screen shows which block served which zoom level. A **load indicator** is
a marker in W-area (always drawn at z1–z9): if it is visible, the device
really loaded the new file.

Zoom steps are counted from near (z1) to far (z12).

---

## Gotchas: read first

Each of these cost at least one wasted drive.

1. **Python's `lzma.compress` writes a broken 13-byte header.** It rounds
   `dict_size` up and writes the size as "unknown" (`ff ff … ff`). The original
   has `dict_size == size == uncompressed size`. Overwrite both fields after
   compressing and assert the round trip (`spike/test11.py`, `build()`). This
   voided **Tests 1, 4, 5, 8, 9 and 10**: four head-unit crashes and two
   rejections, none of which says anything about the question it was meant to
   answer.
2. **Keep the invariants of the original file.** Properties byte `0x5D` in every
   block, `dict_size == size == uncompressed size`, stream length == extent (or
   extent − 14 when a Format C record follows). Do not use `pb=0`.
3. **`gw_anchors.pkl` stores the distance to the next anchor as "length", not
   the stream length.** They differ for 17,196 blocks. Use `gw_blockmap.pkl`
   (from `spike/blockmap.py`) for real lengths.
4. **AppleDouble files (`._*`) on the FAT32 card.** macOS creates
   `._GermanyWest_Basic.psf` when copying, because the source file carries a
   `com.apple.provenance` extended attribute. `xattr -c` cannot remove that
   attribute. One such file in `MapRegions/` made a test unusable (Test 4,
   first run). After **every** write to the card:
   ```sh
   find "/Volumes/NO NAME" -name '._*' -delete
   ```
   Existing `.DS_Store` files from the original card are harmless: they were
   there in all accepted tests.
5. **Never shift bytes between records in section 16.** The street section is
   a chain `u16 L │ body` behind a group index (format §11). Insert and replace
   only with `spike/sec16.py` (`named()`, `insert()`, `replace()`).
   Build `e1` broke this rule and crashed the head unit.
6. **Never write an empty name** (`00 03 00`). It occurs nowhere in the
   original. It has not been proven harmful, but there is no reason to risk it.
7. **Read village streets at z1–z9**, not at z10–z11. The device apparently
   does not draw village streets at z10–z11. Build `d1` was misread because the
   instructions said z10–z11.
8. **Put a load indicator in every build.** Without one, "nothing new is
   visible" cannot be told apart from "the old map is still loaded" (build
   `c1`).
9. **Check the SD card's write-protect switch** before the test. It was found
   switched on after Test 1, which made that rejection impossible to interpret.
10. **Labels and lines come from different blocks.** The zoom table for place
    labels says nothing about where line geometry comes from (format §8).
11. **When neighbouring tiles compete, put markers in the western one.** In the
    test area, changes to the eastern tile never showed (four null results).
    Which of the eastern tile's three blocks the device draws is unknown.

## Workflow rules

- **Never modify the backup copy** (`sdsrc/`). Read from it only. Builds go to
  `spike/GermanyWest_Basic.<build>.psf` and then to the card or a test copy
  (`sdtest/`). Everything unchanged is copied from the backup.
- **Run the validator before every drive:**
  ```sh
  cd spike && python3 validate.py GermanyWest_Basic.<build>.psf   # 0 errors = ready
  ```
  It checks all invariants over all 76,003 blocks in seconds. The crashed build
  `t10` fails with 8 errors; the accepted builds `t11` and `p1` pass with 0.
  The section 16 framing check [12] was added after `e1`: `e1`, `d1`, `c1` and
  `z3` fail it, `w1` and the geometry test pass. Builds that grow a block on
  purpose need a `<build>.plan.json` next to the `.psf` (see the docstring of
  `validate.py`).
- **Several independent probes per build, one variable per probe.** Each test
  costs a drive. Spread probes over different tiles and zoom levels, and
  write down beforehand what each possible outcome would mean.
- **Change one thing relative to the last accepted build.** Test 5 changed two
  untested things at once and its result could not be attributed.
- **Copy to the card with `dd`** (`/bin/dd bs=4m`) and compare hashes
  afterwards. Then delete `._*` files (gotcha 4).
- **Restore the original** when the car goes back into normal use:
  copy back from the backup and check with `diff -rq`.

---

## Summary

| # | Build | Change | Result | Valid? |
|---|---|---|---|---|
| 0 | §6 acceptance | village name → marker, same length, 3 blocks | **accepted**, marker visible on the overview | yes |
| 0b | §6a zoom mapping | distinct marker per block | zoom map measured | yes |
| 1 | `reloc` | 3 blocks appended at EOF, file +47 KB | rejected | **no** (header, write-protect) |
| 2 | `swap` | offsets/lengths of an L10 layer pair swapped | accepted, no visible change | yes (blind) |
| 3 | `dup` | one block removed from the index | **block disappeared** | yes |
| 4 | `reloc2` | 3 blocks inserted before the metadata chain | rejected (twice) | **no** (header) |
| 5 | `t5` | block grows into neighbour, cross-band redirect | **crash** (full MIB reboot) | **no** (header) |
| 6 | `t6` | one length field +18 B | accepted, normal | yes |
| 7 | `t7` | one index entry redirected within band | accepted, foreign block drawn | yes |
| 8–10 | `t8`–`t10` | growth variants | **crash** | **no** (header) |
| P1 | probe 1 | block header bbox +5 km east | **content moved 5 km** | yes |
| 11 | `t11` | two blocks rewritten to exact original length | **passed**, markers visible | yes |
| G | `geo` | 9 delta bytes → square | **square visible** where predicted | yes |
| w1 | `w1` | stream grows +64 B into sacrificed neighbour | **accepted**, both markers visible | yes |
| z3 | `z3` | new OSM street inserted, payload +33 B | **street visible** | yes (but bad framing) |
| c1 | `c1` | 40 paths in the eastern tile, 27 unnamed | nothing visible | **not evaluable** |
| d1 | `d1` | 6 probes, empty name, two blocks grow | load indicator + new street at z1–z9 | partly |
| e1 | `e1` | `d1` with all names | **crash** when displaying tiles | yes (bad framing) |
| f1 | `f1` | `e1` probes, correctly framed | no crash, 2 of 5 probes visible | yes |
| g1 | `g1` | 3 probes for the invisible record | **built, never driven** | — |

"Header" = the broken 13-byte LZMA header of gotcha 1.

---

## Test details

### 0. Acceptance test (2026-09-09), journal §6

**Change:** the 7-letter village name replaced by a 7-letter marker in the two
blocks that had room to compress (L10 tile), plus a one-letter change in a
third block (W-area). The one-letter change keeps a 6-byte prefix LZMA can
still match, so it cost 0 bytes. File size identical, index untouched.

**Result:** accepted. The marker appeared on the 2D overview; the 11 closer
zoom steps still showed the original name.

**Proved:** the device accepts modified `.psf` files. There is no checksum or
signature.

### 0b. Zoom mapping (2026-09-09), journal §6a

**Change:** a different marker in each block.

**Result and proof** (refined by Test 6): z1–z9 label from W-area, z10–z11
from W-road, z12 from L10-road. The L10 pair: L10-road wins the label over
L10-area. Tiles exist in layer pairs; L11 is the deepest data level over the
village. (The journal concluded here that the renderer draws labels from a
neighbouring tile. That rested on the belief that the village lies in the
eastern tile; it was later found to lie in the western one, 108 m from the
border, so the conclusion does not hold.)

### Test 1: block relocation to EOF (2026-09-10), journal §6d

**Change:** three blocks re-compressed (longer), appended at the end of the
file, after the metadata chain; their index entries and the file-size field
`@0x04d` updated. File +47,346 B.

**Result:** rejected: "Insert a medium with valid navigation data."

**Proved:** nothing. The write-protect switch was found on afterwards, an
AppleDouble file was probably present, and the blocks had the broken header.
Ruled out offline at the time: a checksum over header, index or data ranges.

### Test 2: L10 layer-pair entries swapped (2026-09-10)

**Change:** in the two index entries of the L10 pair, offset and length
swapped (10 bytes).

**Result:** accepted, display unchanged.

**Proved:** the index area is not integrity-checked. The swap itself could
show nothing: both blocks are still loaded, and which one provides the label
depends on block content, not on the index slot.

### Test 3: block removed from the index (2026-09-10)

**Change:** both entries of the L10 pair point to L10-area; L10-road is
referenced by no Format A/B entry (5 bytes changed). Its Format D entry was
left in place.

**Result:** z12 showed only area colours, no lines, no labels. Other zooms
normal.

**Proved:** the plain-text index decides what is loaded. Format D alone does
not. In a layer pair, one block draws areas and the other draws lines and
labels.

### Test 4: relocation before the metadata chain (2026-09-10)

**Change:** three blocks inserted before the metadata chain, the chain moved
back by 47,346 B, its five header pointers and the size field updated, three
index entries redirected.

**Result:** rejected, twice. The first run had a `._GermanyWest_Basic.psf`
AppleDouble file next to the map; the second run was clean (same file,
verified by hash).

**Proved:** at the time it looked as if the file was rejected. Later found to
be void: the re-compressed blocks had the broken header. **Whether the file may
grow is still open.**

### Test 5: growth into the neighbour (2026-09-10)

**Change:** E-area grew by 18 B into the next block (W-area); W-area's
Format A entry was redirected to W-road, a block in a different "band".
18,136 bytes changed.

**Result:** full crash of the MIB: the radio and background music went down
too and the whole unit rebooted.

**Proved:** nothing. Two untested variables at once, a marker in a block that
never wins the label, and the broken header. Bookkeeping was correct (no
reference to the overwritten block remained).

### Test 6: length field overstated (2026-09-10)

**Change:** one byte. A Format A length field says 18,222 instead of 18,204.

**Result:** accepted, display normal on all levels.

**Proved:** the length in the index record is not needed for loading (at least
not for an 18 B overstatement). The device does not walk blocks as a strict
`offset + length` chain. Also refined the zoom table: z1–z9 from W-area.

### Test 7: redirect within the band (2026-09-10)

**Change:** 4 bytes. W-area's index entry redirected to E-area (same band,
different bbox).

**Result:** accepted; at z1–z9 only the eastern half was drawn.

**Proved:** redirecting an entry loads the other block, even with a different
bbox. The block-header bbox, not the slot, decides where content is drawn.

### Tests 8, 9, 10: growth variants

**Result:** head-unit crashes. All three had the broken header and prove
nothing. `t10` fails the validator with 8 errors.

### Probe 1: header bbox shifted (2026-09-17)

**Change:** the bbox in a block header moved 5 km east.

**Result:** at z10–z11 the content moved east by 5 km; a 5 km wide gap stayed
in the west over the full tile height (30 km).

**Proved:** the bbox in the block header anchors the content; the bbox in the
index record is not used for clipping. Confirms the georeferencing (format §5,
§9) in the device.

### Test 11: length-neutral rewrite (2026-09-17), journal §6h

**Change:** W-road and E-road re-compressed with a full encoder sweep and a
marker chosen so that each stream is **exactly** as long as the original. The
13-byte header is byte-identical, index untouched, 28,260 bytes changed, all
inside the two blocks.

**Result:** passed. z1–z9 the earlier one-letter marker, **z10–z11 the new
W-road marker**, z12 the L10 marker. The E-road marker appeared nowhere.

**Proved:** any block can be rewritten as long as the payload compresses into
the original length. From here on the car is a reliable oracle for block
contents.

### Geometry test (2026-09-18), journal §6j

**Change:** on top of Test 11, the nine delta bytes of an existing street in
W-road replaced (`3d 1f 3f 4f 3f 2e 2e 2d 01` → `07 07 70 70 09 09 90 90 20`),
plus a new marker to hit the exact length. Stream exactly the original length.

**Result:** a closed square, 252 m per side, **visible at the predicted spot**.
Joachim placed it spontaneously at a hamlet whose place record is 2 units
(36 m) from the square's edge.

**Proved:** the delta encoding, the 18 m quantum, the absolute start point and
the tile origin are right, end to end, in the device. Geometry is writable.

### w1: growth test (2026-09-20), journal §6g

**Change:** base is the untouched original. W-area: name → load indicator
(same length). W-road: name → marker (same payload length), but compressed so
the stream is **+64 B** longer than its extent, running into the next block
(1,995 B). That next block's **both** references (Format A and Format D) were
redirected to its layer partner (identical bbox, same band, same byte +20),
and W-road's length updated in both of its references. File size unchanged,
24,949 bytes changed, metadata chain untouched, validator 0 errors.

**Result:** load indicator at z1–z9 and the marker at z10–z11, both visible.

**Proved:** a block may be longer than its original extent, if the neighbour
it grows into is sacrificed this way.

### z3: first OSM street (2026-09-20)

**Change:** a 48 m residential street that HERE never captured (in OSM since
2008) converted from OSM and inserted into W-road. Payload +33 B, stream
+24 B into the sacrificed neighbour. Load indicator in W-area.

**Result:** the street was visible, branching off in the right place and
direction. The land-use colour under it was wrong (HERE's settlement polygon
is smaller than the real village).

**Proved:** the uncompressed payload may grow too (with matching header
fields). OSM data can be written into the map end to end. The insertion was
later found to violate the section 16 framing (it still rendered).

### c1: campsite paths (2026-09-20/21)

**Change:** 40 OSM paths (4,479 m) of a campsite in the eastern tile inserted
into E-road (payload +1,043 B, stream +340 B, neighbour sacrificed); 13 named,
27 with an empty name. No load indicator.

**Result:** nothing visible on any zoom.

**Proved:** nothing. No load indicator, eastern tile (no positive test ever),
empty names, and the area looked at was not where the paths were drawn. It
also used a point-label header as the street framing (found later, §6l).

### d1: discriminator (2026-09-21/22)

**Change:** six probes in one build. P0 load indicator. P1 the street from
`z3` again. P2 an isolated 252 m square with an empty name in W-road. P3 a
street name in E-road changed. P4 a street in E-road turned into a square
(length-neutral). P5 the campsite paths from `c1`. Two blocks grew in two
bands at once.

**Result:** load indicator visible. At z1–z9 the village as usual **with the
new street**. At z10–z11 no street network at all. P2–P5 were only looked for
at z10–z11.

**Proved:** the map loaded and W-road was read and drawn. Growing two blocks in
one build works. A first reading ("one empty name kills the whole section")
was **wrong**: everything seen lies before the empty-name record, so either
empty names are harmless or the device stops reading there. P2–P5 are
unanswered, not negative.

### e1: everything named (2026-09-22/24)

**Change:** exactly `d1`'s structure, but every record named (P2 got a name,
the 27 short campsite paths too) and a new load indicator.

**Result:** **crash while displaying tiles**. Zoom and place unknown. Card
verified byte-identical, no `._` files, validator (at that time) 0 errors.

**Proved:** led to the discovery of the section 16 chain (format §11). All
four insertion builds (`z3`, `c1`, `d1`, `e1`) had inserted between a name and
its element's trailer byte, without a length prefix and without updating the
group index; the eastern builds also used a wrong framing and shortened an
element without updating its lengths. `z3` and `d1` survived this by luck.
Bad framing is the only structural error found; it is the likely cause, not a
proven one.

### f1: correctly framed (2026-09-24/25)

**Change:** the `e1` probes, inserted with `sec16.insert()` (length prefix,
group index updated): P0 load indicator; P1 the street as its own element in
the village's group `22 80 03`; P2 a named isolated square, 330 m from the
village centre; P3 a street name in E-road changed (same length); P4 a street
in E-road turned into a square. No campsite paths. Validator 0 errors
including [12].

**Result:** no crash. P0 and P1 visible. P2, P3, P4 not visible. The street
that P4 changed in the eastern tile was still drawn in its original form,
from a duplicate of it in W-road.

**Proved:** correctly framed insertion is stable. The eastern road block
(`@0x346c45e`) is not what the device draws there (fourth null result: Test
11, `c1`, P3, P4). **P2 is the open question:** it sits in the same group
between two visible records, so the chain was read past it, yet it was not
drawn. Candidates: (a) it was not in view (unknown), (b) new records need the
final delta byte `01` that all 73 original records have (P2 ended in `d0`),
(c) only lines connected to the network are drawn (P2 was isolated; P1 shares
an end point with an existing street).

### g1: resolving P2 (built 2026-09-26, never driven)

**Change:** only W-road and the load indicator, eastern tile untouched. Three
probes in group `22 80 03`:

| Probe | Shape | Isolated | Last delta byte |
|---|---|---|---|
| A | square 252 m, byte-identical to `f1` P2 | yes | `d0` |
| B | square 252 m + 18 m tail | yes | `01` |
| C | triangle 252 m from the start point of an existing street | no | `97` |

**Reading:** A visible → `f1` P2 was overlooked. A missing, B visible → new
records need the final `01`. A missing, C visible → network connection is
needed. All missing → both explanations are wrong.

**Status:** never driven. The card was restored to the original on 2026-10-09
(verified with `diff -rq`), because the car is in other use. Rebuild and copy
before the next test (`spike/g1.py`).
