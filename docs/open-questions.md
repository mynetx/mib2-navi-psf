# Open questions

What is still unknown about the `.psf` format, roughly in order of
usefulness, with the experiments most likely to answer each question. See
[`format.md`](format.md) for what is known and
[`vehicle-tests.md`](vehicle-tests.md) for how the car is used as a test
oracle.

Two kinds of experiment are available:

- **Offline** against OpenStreetMap: fit a hypothesis over many records and
  compare with a control (shuffled bytes, random coordinates). This is cheap
  and settled the coordinates and the street geometry.
- **In the car**: costs a drive each time. Always include a load indicator and
  several independent probes, and run `spike/validate.py` first.

---

## 1. Why is a newly inserted, isolated street not drawn?

In build `f1`, a correctly framed, named square inside the village's street
group was not visible, while a new street in the same group was
(vehicle-tests, `f1`). Three explanations remain:

- it was simply not in view;
- new records need the final delta byte `01` that all 73 original named
  `f = 0x00` records end with;
- the device only draws lines that connect to the existing network.

**Next experiment:** build `g1` is ready (`spike/g1.py`, probes A/B/C). Rebuild
it from the original, copy it to the card, delete `._*` files and read at
z1–z9. It answers all three at once. Until this is answered, every new street
should end on `01` and share an end point with an existing street.

## 2. Geometry of street records with `f = 0x10`

About half of all street records. Header, `n` and absolute start point are
understood; the deltas are not nibble steps, and 1–5 extra bytes (usually
ending in `01`) follow them. Eight alternatives are ruled out (format §12.4).

**Next experiments (offline):**

- Look at the extra bytes first: do they encode a count, a second start point,
  a reference to another record, or a curve/shape parameter? Correlate their
  values with record length and with the OSM shape of the matching street.
- Try variable-length encodings (varint-style deltas, escape codes for long
  steps) with the same scoring as for `f = 0x00` (`spike/bitfit.py`):
  vertices on OSM streets from step 3 on, against a shuffled-byte control.
- Check whether `f = 0x10` records are the ones with OSM steps > 7 units, i.e.
  whether `0x10` flags a different step size.

## 3. Which block does the eastern test tile draw?

Four probes in the eastern L11 road block (`@0x346c45e`) never showed up.
That tile has a third block with the same bbox (`@0x3473ae1`, no readable
section table, different names). In general, L11 tiles often have two
road-layer blocks; what the second one is for is unknown.

**Next experiments:**

- Offline: compare the two road blocks of a few two-block tiles. Same streets
  at different detail? Different street classes? Split by group class?
- In the car: one marker in each of the eastern blocks in the same build.

## 4. Can the file grow?

Both tests that grew the file (Tests 1 and 4) used the broken LZMA header and
are void. Growth into a sacrificed neighbour block works, so this is not
needed for small edits, but it is for larger ones.

**Next experiment:** repeat Test 4 (insert blocks before the metadata chain,
move the chain, update the five header pointers and the size field `@0x04d`)
with correct headers, plus a load indicator. If it is rejected, test the
three remaining explanations separately: file growth checked as such; one of
the five "pointers" is really a length or count; the chain contains absolute
offsets of its own.

## 5. Limits of block growth

Tested: +342 B of stream growth into a sacrificed neighbour, same band. Open:
the upper limit, and whether redirecting the sacrificed neighbour to a block
in a different band is harmful (Test 5 did that and crashed, but with the
broken header).

## 6. Land use (area) polygons

A new street lies on the wrong ground colour, because HERE's settlement area
is smaller than the real village. Areas are drawn from the area/point layer
(quantum 4 m at L11), where section class 9 (58 % of the block) holds point
labels. How the polygons are encoded is unknown; nibble polygons around the
labels and closed byte chains are ruled out (format §10.4).

**Next experiments (offline):** find the section that changes size with the
number of area features across many tiles; look for coordinate pairs at the
4 m quantum that trace OSM `landuse=*` outlines (same peak method as for the
street quantum). In the car: change bytes in one section at a time of a
length-neutral area block and watch which colours move.

## 7. Is the coordinate quantum stored in the block header?

Found while writing these docs: the "band" value (`i32` at header +16) is
`(u16 @+18 << 16) | uncompressed size`, and the high half is 4, 18 and 38 in
exactly the blocks whose measured quanta are ≈4, 18 and 38 m (format §7.1).

**Next experiment (offline):** run the OSM peak search (`spike/osmfit.py`
method) on blocks whose header says 19, 39, 62 or 63 and check the peak
lands on that value. If it does, every block's quantum can be read from its
header.

## 8. The name index (trie) in the end section

The 3-byte character grid is readable, but the node header (e.g. the leading
`06 00`) is not, so the trie cannot be traversed from a root (format §13).
Which names it contains (probably street names) is also not certain.

**Next experiments:** collect the first bytes of all small end-section
blocks and correlate them with the number of children and the length of the
string run that follows; find the root by following the u16 branch pointers
backwards. Check whether a street added to a road block can be found by name
in the car without a trie entry.

## 9. Unknown fields

Smaller items that will come up when writing more complex content:

| Field | What is known | Idea |
|---|---|---|
| Street element trailer `k` (1–4) | always `01` with a single name | correlate with number/type of name entries |
| `80 12 <v>` tag before `80 11` | exists | check if it is also an inner length |
| Group index class/flags/x (e.g. `22 80 03`) | offsets understood | compare with OSM road class of the streets in each group |
| Element body types `00 01`, `80 01`, `00 00`, `80 20` | exist | decode with the same OSM method |
| Other record flags `0x03 0x20 0x2f 0x54` | exist | same |
| Place record third u16 (70–114, even) | — | correlate with OSM `place=` class / population |
| Point label `<n>` | not size, not a length | compare with OSM feature type |
| Header byte +20 | ~250 values, not a type field | — |
| Section classes 4, 5, 8, 10, 13, 14 | — | size vs. feature counts across tiles |
| Format A flags (0–3) | — | compare with level and layer |
| Metadata chain at EOF | 4 links, not a signature | dump and compare across the 161 files |
| Four unclassified data regions | structured, not free | the largest shows a local 20-byte pattern (`00 00 <xx> 00 12 03 00 01 … 00 00 80 00`) |
| Format D table | maps blocks to (length, offset) | whether the device uses it at all |
| `_AdvancedRouting` records | block framing verified | links/nodes/attributes |
| Second block type | tag records with tile keys | purpose |

## 10. Other regions and card versions

Everything here was measured on one card (`8V0060866M`, ECE 2020/21) and
mostly on `GermanyWest_Basic.psf` plus Malta. Running the scripts on other
regions and on other MIB2 map releases would show which constants are
universal. Most scripts hard-code block offsets of this one file and must be
adapted.
