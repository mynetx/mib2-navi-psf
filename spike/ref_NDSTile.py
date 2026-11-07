# Reference copy from nds_tile (MIT License, see README "Credits"); unchanged apart from this header.
from NDSCoordinate import NDSCoordinate
from WGS84Coordinate import WGS84Coordinate
from NDSBBox import NDSBBox
from PrintBinary import print_binary_representation
import argparse
import logging

class NDSTile:
    """
    Implementation of the NDS Tile scheme.
    It follows the NDS Format Specification, Version 2.5.4, §7.3.1.
    
    No warranties for correctness, use at own risk.
    """
    MAX_LEVEL = 15

    def __init__(self, *args):
        self.level = -1
        self.tile_number = None
        self.center = None

        if len(args) == 1:  # Packed ID constructor
            packed_id = args[0]
            print_binary_representation(packed_id, "Packed ID binary")
            self.level = self.extract_level(packed_id)
            if self.level < 0:
                raise ValueError(f"Invalid packed Tile ID {packed_id}: No Level bit present.")
            level_bit = 1 << (16 + self.level)
            self.tile_number = packed_id ^ level_bit

        elif len(args) == 2:  # Level and tile number or coordinate constructor
            if isinstance(args[1], int):  # Level and tile number
                level, nr = args
                if level < 0 or level > self.MAX_LEVEL:
                    raise ValueError(f"The Tile level {level} exceeds the range [0, {self.MAX_LEVEL}].")
                if nr < 0:
                    raise ValueError(f"The Tile id {nr} must be positive (Max length is 31 bits).")
                if nr > (1 << (2 * level + 1)) - 1:
                    raise ValueError(f"Invalid Tile number for level {level}, numbers 0 .. {(1 << (2 * level + 1)) - 1} are allowed.")
                self.level = level
                self.tile_number = nr

            elif isinstance(args[1], NDSCoordinate):  # Level and NDSCoordinate
                level, coord = args
                self.level = level
                self.tile_number = int(coord.get_morton_code() >> (32 + (self.MAX_LEVEL - level) * 2))

            elif isinstance(args[1], WGS84Coordinate):  # Level and WGS84Coordinate
                level, coord = args
                nds_coord = NDSCoordinate(coord.longitude, coord.latitude)
                self.level = level
                self.tile_number = int(nds_coord.get_morton_code() >> (32 + (self.MAX_LEVEL - level) * 2))

    def contains(self, c):
        """
        Checks if the current Tile contains a certain coordinate.
        """
        return self.tile_number == int(c.get_morton_code() >> (32 + (self.MAX_LEVEL - self.level) * 2))

    def packed_id(self):
        """
        Returns the packed Tile ID for this tile.
        """
        return self.tile_number + (1 << (16 + self.level))

    def get_center(self):
        """
        Returns the center of this tile as NDSCoordinate.
        """
        if self.center is None:
            if self.level == 0:
                if self.tile_number == 0:
                    return NDSCoordinate(NDSCoordinate.MAX_LONGITUDE // 2, 0)
                else:
                    return NDSCoordinate(NDSCoordinate.MIN_LONGITUDE // 2, 0)

            print_binary_representation(self.south_west_as_morton(), "South west morton code binary")
            
            sw = NDSCoordinate(self.south_west_as_morton())
            clat = int(sw.latitude + (NDSCoordinate.LATITUDE_RANGE // (1 << (self.level + 1)))) + (1 if sw.latitude < 0 else 0)
            clon = int(sw.longitude + (NDSCoordinate.LONGITUDE_RANGE // (1 << (self.level + 2)))) + (1 if sw.longitude < 0 else 0)
            self.center = NDSCoordinate(clon, clat)
        return self.center

    def get_bbox(self):
        """
        Creates a bounding box for the current tile.
        """
        if self.level == 0:
            return NDSBBox.EAST_HEMISPHERE if self.tile_number == 0 else NDSBBox.WEST_HEMISPHERE

        south_west_corner_morton = self.south_west_as_morton()
        sw = NDSCoordinate(south_west_corner_morton)
        north = int(sw.latitude + (NDSCoordinate.LATITUDE_RANGE // (1 << self.level))) + (1 if sw.latitude < 0 else 0)
        east = int(sw.longitude + (NDSCoordinate.LONGITUDE_RANGE // (1 << (self.level + 1)))) + (1 if sw.longitude < 0 else 0)
        return NDSBBox(north, east, sw.latitude, sw.longitude)

    def get_tile_grid_coordinates(self):
        """
        Computes the tile grid coordinates for the current tile by decoding the tile number's morton code.
        
        For example:
        * For level 1, the tile's grid coordinates look like this for the whole world:
        [-2,  0] [-1,  0] [0,  0] [1,  0] 
        [-2, -1] [-1, -1] [0, -1] [1, -1]

        Their corresponding tile numbers are:
        '1-00', '1-01', '0-00', '0-01',
        '1-10', '1-11', '0-10', '0-11'

        In decimal form, they are:
        4, 5, 0, 1,
        6, 7, 2, 3
        
        * For level 2, the tile's grid coordinates look like the following:
        [-4,  1] [-3,  1] [-2,  1] [-1,  1] [0,  1] [1,  1] [2,  1] [3,  1]
        [-4,  0] [-3,  0] [-2,  0] [-1,  0] [0,  0] [1,  0] [2,  0] [3,  0]
        [-4, -1] [-3, -1] [-2, -1] [-1, -1] [0, -1] [1, -1] [2, -1] [3, -1]
        [-4, -2] [-3, -2] [-2, -2] [-1, -2] [0, -2] [1, -2] [2, -2] [3, -2]
       
        Their corresponding tile numbers are:
        '1-00-10', '1-00-11', '1-01-10', '1-01-11', '0-00-10', '0-00-11', '0-01-10', '0-01-11',
        '1-00-00', '1-00-01', '1-01-00', '1-01-01', '0-00-00', '0-00-01', '0-01-00', '0-01-01',
        '1-10-10', '1-10-11', '1-11-10', '1-11-11', '0-10-10', '0-10-11', '0-11-10', '0-11-11',
        '1-10-00', '1-10-01', '1-11-00', '1-11-01', '0-10-00', '0-10-01', '0-11-00', '0-11-01'
        
        In decimal form, they are:
        18,  19,  22,  23,   2,   3,   6,   7,
        16,  17,  20,  21,   0,   1,   4,   5,
        26,  27,  30,  31,  10,  11,  14,  15,
        24,  25,  28,  29,   8,   9,  12,  13
        """
        if self.level == 0:
            return [0, 0] if self.tile_number == 0 else [-1, 0]
        col, row = 0, 0
        mask, col_mask = 1, 1

        for _ in range(self.level + 1):
            if self.tile_number & mask:
                col |= col_mask
            mask <<= 1

            if self.tile_number & mask:
                row |= col_mask
            mask <<= 1
            
            col_mask <<= 1

        return [col if col < (1 << self.level) else col - (1 << (self.level + 1)), 
                row if row < (1 << self.level - 1) else row - (1 << self.level)]
    
    def to_geojson(self):
        """
        Computes a GeoJSON representation of the NDS Tile as GeoJSON "Polygon" feature.
        """
        return self.get_bbox().to_wgs84().to_geojson()

    def south_west_as_morton(self):
        """
        Computes the Morton code of the south-west corner of the tile.
        """
        shift = 32 + (self.MAX_LEVEL - self.level) * 2
        morton = self.tile_number << shift
        return morton

    def extract_level(self, packed_id):
        """
        Extracts the level from a packed Tile ID.
        """
        for lvl in range(self.MAX_LEVEL, -1, -1):
            lvl_bit = 1 << (16 + lvl)
            if packed_id & lvl_bit:
                return lvl
            if packed_id < 0 and lvl == self.MAX_LEVEL:
                return self.MAX_LEVEL
        return -1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Show information about NDS Tiles.')
    parser.add_argument('--log_level', type=str, default='info', 
                        help='Set the logging level (debug, info, warning, error, critical)')
    parser.add_argument("packed_ids", type=int, nargs='*', help='The list packed IDs of tiles to process')
    args = parser.parse_args()
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')
    logging.basicConfig(level=numeric_level)

    # if packed_ids are specified, use them, otherwise use the default values
    if len(args.packed_ids) > 0:
        packed_ids = args.packed_ids
    else:
        print("No packed IDs specified, using default values.\n")
        #packed_ids = [262147, 262150] # Level 2 in northern hemisphere
        packed_ids = [262154] # Level 2 in southern hemisphere
        #packed_ids = [65536, 65537] # level 0, only 2 tiles.
        #packed_ids = [131076, 131077, 131078, 131079] # level 1 [-180, 0]
        #packed_ids = [131072, 131073, 131074, 131075] # level 1 [0, 180]
        #packed_ids = [539636700] # level 13 in Barcelona
        #packed_ids = [1049046] # Level 4 in southern hemisphere
    for id in packed_ids:
        tile = NDSTile(id)
        
        print(f"Tile ID: {tile.packed_id()}, Level: {tile.level}, Tile Number: {tile.tile_number}")
        print(f"Tile Grid Coordinates: {tile.get_tile_grid_coordinates()}")
        print(f"Center in NDSCoordinates: {tile.get_center().longitude}, {tile.get_center().latitude}")
        print(f"Center: {tile.get_center().to_geojson()}")
        print(f"Bounding Box: {tile.get_bbox().to_geojson()}\n")

