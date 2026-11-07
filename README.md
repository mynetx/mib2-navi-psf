# mib2-navi-psf

Reverse engineering of the `.psf` map files on VW/Audi **MIB2** navigation SD
cards: how they are built, how to read them, and how to write changes that
the head unit accepts.

> **No map data is included here, and none may be added.** The `.psf` files
> and everything extracted from them are copyrighted by HERE and Volkswagen.
> To use the scripts you need your own card. Please don't open issues or pull
> requests that contain map files, decompressed blocks or extracts.

The goal is to document **everything** learnt about the format, so others can
build on it: readers, statistics, routing graphs, or adding missing streets
from OpenStreetMap.

## The card

| | |
|---|---|
| Medium | 8 GB SD card, FAT32 |
| Part number | `8V0060866M`, "ECE 2020/21" (map build 2019-12-12) |
| Data | HERE/NavTeq in **NDS 2.5.4** (Navigation Data Standard) |
| Map files | `markets/eu/map/MapRegions/<Region>_<Type>.psf`, 161 files, 54 regions |

Other MIB2 cards and releases very likely use the same format, but only this
one was examined.

## Current state

### Solved and verified in the vehicle

- **No encryption, no signature, no checksum.** Modified files are accepted.
- **Container:** every block is a plain LZMA-alone stream with a 13-byte
  header. Blocks can be rewritten in place; with the right encoder settings
  they hit the original length to the byte.
- **Index:** the `(offset, length)` pairs of the tile blocks are stored as
  plain text. The index decides what is loaded; removing or redirecting an
  entry has a visible effect.
- **Blocks may grow** into a following block, if that block is sacrificed
  (its references redirected to its layer partner).
- **Georeferencing:** tile bounding boxes in spherical Mercator metres
  (R = 6,371,000 m), NDS tile grid. Moving a bbox moves the drawn content.
- **Street geometry:** absolute start point plus one nibble-pair delta byte per
  vertex, on an 18 m grid (L11) or 38 m grid (L10). A rewritten street and a
  street converted from OSM both appeared in the car where predicted.
- **Section 16 framing:** streets are a length-prefixed chain behind a group
  index. Inserting with correct framing is stable; inserting without it crashed
  the head unit once.

### Solved offline (against OpenStreetMap or the whole file)

- Tile key catalogue `(layer << 21) | (1000 · region + tile)`, region numbers.
- Place records, point labels, coordinate quanta per layer.
- Street records with flag `0x00`: 192 of 192 records re-encoded
  byte-identically.

### Open

- Why one newly inserted isolated street was not drawn (a ready-made test build exists).
- The geometry of street records with flag `0x10` (about half of all streets).
- Land-use polygons, the name-index trie, most attribute fields.
- Whether the file itself may grow.

Details: [docs/open-questions.md](docs/open-questions.md).

## How the format works

```
.psf file
├── header            file size, pointers to the metadata chain at EOF
├── index tables      plain-text (offset, length) records, 4 layouts (A–D)
├── data blocks       76,003 LZMA-alone streams in GermanyWest_Basic.psf
│   └── tile block    header: bbox (Mercator m), size, quantum?, section table
│       ├── area/point layer   place labels, areas         (4 m grid at L11)
│       └── road layer         section 16 = street chain   (18 m grid at L11)
│           └── element: u16 L │ 80 11 │ u16 L-1 │ 01 n f │ X │ Y │ n deltas │ 00 03 name 00 │ k
├── end section       name index (trie) in 3-byte character cells
└── metadata chain    4 linked records, ends exactly at EOF
```

A tile exists as a **layer pair**: two blocks with an identical bbox, one for
areas and labels, one for streets. Coordinates inside a tile are u16 offsets
from the tile's south-west corner, in units of a fixed metre quantum. Each
street vertex after the first is one byte: high nibble = dy, low nibble = dx,
both 4-bit two's complement.

| Document | Content |
|---|---|
| [docs/format.md](docs/format.md) | The specification: every structure, with byte layouts, worked examples and a confidence label for each claim |
| [docs/vehicle-tests.md](docs/vehicle-tests.md) | Every in-car test and what it proved; **gotchas to read before building anything** |
| [docs/open-questions.md](docs/open-questions.md) | What is unknown and the most promising next experiments |
| [FINDINGS.md](FINDINGS.md) | The original lab journal (German, chronological; later sections correct earlier ones) |

## Using the scripts

The scripts in [`spike/`](spike/) are the analysis code from the journal:
throwaway code with German comments, many of them hard-coding block offsets of
the one `GermanyWest_Basic.psf` that was studied. They are published as
evidence and as a starting point, not as a library. Python 3 (tested with
3.11), standard library only.

**Layout they expect.** Run them **from inside `spike/`**, with a copy of the
whole SD card next to it:

```
mib2-navi-psf/
├── sdsrc/NO NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf   # your card copy, read-only
├── sdtest/                                                          # optional working copy
└── spike/                                                           # run scripts here
```

```sh
cd spike
python3 idxscan.py ../sdsrc/NO\ NAME/markets/eu/map/MapRegions/GermanyWest_Basic.psf   # block anchors -> gw_anchors.pkl
python3 blockmap.py                       # real length, size, bbox of every block -> gw_blockmap.pkl
python3 roadrec.py                        # decode street records of one block
python3 roadwrite.py                      # self-test: re-encode all f=0 street records byte-identically
python3 validate.py GermanyWest_Basic.<build>.psf   # check a build against all invariants
```

Most useful entry points:

| Script | Purpose |
|---|---|
| `nds.py` | NDS tile and coordinate maths |
| `idxscan.py`, `blockmap.py` | find and measure all blocks |
| `roadrec.py` | street record decoder (`parse_section()`, `decode()`, `to_wgs84()`) |
| `roadwrite.py` | OSM → street record encoder (`to_units()`, `densify()`, `record()`) |
| `sec16.py` | insert/replace elements in the section 16 chain with correct framing |
| `test11.py` | reference block build (`build()` fixes the 13-byte LZMA header) |
| `validate.py` | checks a modified file against every invariant of the original |
| `osmfit.py`, `bitfit.py` | fitting formats against OSM ground truth |

The scripts that use OpenStreetMap expect Overpass results in `spike/osm/`
(queries: `spike/*.overpass`). OSM data is © OpenStreetMap contributors, ODbL.
The list of all scripts and what each one showed is in FINDINGS.md §10.

## Safety

- **Test only on a spare card, or make a full backup of your card first** and
  never modify the backup.
- Broken files **crashed the head unit** in several tests: the whole MIB
  rebooted, including radio and audio. Others were rejected with "insert a
  medium with valid navigation data". Restoring the original files fixed it
  every time, but there is no guarantee.
- Run `spike/validate.py` before putting a modified file into a car, and read
  the [gotchas](docs/vehicle-tests.md#gotchas-read-first) first.
- On macOS, delete `._*` AppleDouble files on the card after every copy
  (`find "/Volumes/NO NAME" -name '._*' -delete`).
- Don't change the map while driving or use a modified map for real
  navigation. You do this at your own risk.

## Disclaimer

This project is not affiliated with, endorsed by or connected to Volkswagen
AG, Audi AG, HERE Global B.V. or the NDS Association. All product names and
trademarks belong to their owners and are used only to identify the hardware
and data formats. The work is based on analysing a legally purchased map card
for interoperability.

## License

- **Code** (`spike/*.py` and other source files): [MIT](LICENSE).
  Exception: `spike/nds.py` is a port of, and `spike/ref_NDS*.py` are copies
  from, [limingchina/nds_tile](https://github.com/limingchina/nds_tile), which
  is MIT-licensed by its own authors.
- **Documentation** (`README.md`, `FINDINGS.md`, `docs/`):
  [CC BY 4.0](docs/LICENSE).
- **Map data:** none included, no license granted.

## Credit

Reverse engineering, vehicle tests and journal by **Joachim Rütter**
([@mynetx](https://github.com/mynetx)).

References: NDS Association (<https://nds-association.org/>), NDS Format
Specification 2.5.4 §7.2.1 (coordinates) and §7.3.1 (tiles),
[limingchina/nds_tile](https://github.com/limingchina/nds_tile),
[rondiplomatico/nds-tiles](https://github.com/rondiplomatico/nds-tiles).
