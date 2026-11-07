#!/usr/bin/env python3
"""NDS 2.5.4 Tile-/Koordinatenmathematik, portiert nach der oeffentlichen Referenz
(limingchina/nds_tile, MIT). Nur zur Analyse."""
MAX_LON = 2**31 - 1
MIN_LON = -(2**31)
MAX_LAT = MAX_LON // 2
MIN_LAT = MIN_LON // 2
LON_RANGE = MAX_LON - MIN_LON
LAT_RANGE = MAX_LAT - MIN_LAT
MAX_LEVEL = 15

def morton_to_lonlat(m):
    bit = 1; lon = lat = 0
    for _ in range(31):
        lon |= m & bit
        m >>= 1
        lat |= m & bit
        bit <<= 1
    lon |= m & bit
    if lat >= (1 << 30): lat -= (1 << 31)
    if lon >= (1 << 31): lon -= (1 << 32)
    return lon, lat

def to_wgs84(lon, lat):
    wlon = (lon / MAX_LON) * 180.0 if lon >= 0 else (lon / MIN_LON) * -180.0
    wlat = (lat / MAX_LAT) *  90.0 if lat >= 0 else (lat / MIN_LAT) *  -90.0
    return wlon, wlat

def extract_level(pid):
    for lvl in range(MAX_LEVEL, -1, -1):
        if pid & (1 << (16 + lvl)): return lvl
    return -1

def tile_from_packed(pid):
    lvl = extract_level(pid)
    if lvl < 0: return None
    nr = pid ^ (1 << (16 + lvl))
    if nr > (1 << (2 * lvl + 1)) - 1: return None
    return lvl, nr

def tile_bbox(lvl, nr):
    """-> (west, east, south, north) in WGS84-Grad"""
    if lvl == 0:
        return (0.0, 180.0, -90.0, 90.0) if nr == 0 else (-180.0, 0.0, -90.0, 90.0)
    m = nr << (32 + (MAX_LEVEL - lvl) * 2)
    slon, slat = morton_to_lonlat(m)
    north = slat + LAT_RANGE // (1 << lvl) + (1 if slat < 0 else 0)
    east  = slon + LON_RANGE // (1 << (lvl + 1)) + (1 if slon < 0 else 0)
    w, s = to_wgs84(slon, slat)
    e, n = to_wgs84(min(east, MAX_LON), min(north, MAX_LAT))
    return w, e, s, n

def bbox_of_packed(pid):
    t = tile_from_packed(pid)
    if t is None: return None
    return tile_bbox(*t), t

if __name__ == '__main__':
    print("=== Selbsttest gegen die dokumentierten Referenzbeispiele ===")
    for pid, expect in [(539636700, 'Level 13, Barcelona (~2.2E / 41.4N)'),
                        (65536,     'Level 0, Osthemisphaere'),
                        (65537,     'Level 0, Westhemisphaere'),
                        (262147,    'Level 2, Nordhalbkugel'),
                        (262154,    'Level 2, Suedhalbkugel')]:
        r = bbox_of_packed(pid)
        if r is None:
            print(f"  {pid:>12}  UNGUELTIG   (erwartet: {expect})"); continue
        (w,e,s,n),(lvl,nr) = r
        print(f"  {pid:>12}  level={lvl:2d} nr={nr:<10} "
              f"bbox lon[{w:9.4f}, {e:9.4f}] lat[{s:8.4f}, {n:8.4f}]")
        print(f"                erwartet: {expect}")
