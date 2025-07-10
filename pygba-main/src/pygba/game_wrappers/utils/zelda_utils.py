# Zelda: A Link to the Past (GBA) utility functions


from .area_mapping import get_area_name, is_area_rewardable

TILE_SIZE = 8


ADDRESSES = {
    "PLAYER_HEALTH": 0x0200234D,  # uint8, current health (hearts * 8)
    "SWORD_SWINGS": 0x02002432,  # uint8, number of sword swings
    "ENEMIES_KILLED": 0x0200243A,  # uint8, number of enemies killed
    "RUPEES": 0x02002340,         # uint16, current rupee count
    "SMALL_KEYS": 0x0200234F,     # uint8, current small keys
    "BOMBS": 0x02002323,          # uint8, current bombs
    "MAPS": 0x02002349,           # uint8, current maps
    "BOOMERANG": 0x02002321,      # uint8, boomerang type: 1=Blue, 2=Red
    "MASTER_KEY": 0x02002347,     # uint8, master key (big key)
    "LAMP": 0x0200232C,           # uint8, lamp
    "SWORD": 0x0200233D,          # uint8, sword
    "ZELDA_WITH_LINK": 0x020023FE,  # uint8, 1 if Zelda is with Link, 0 otherwise
    "PLAYER_Y": 0x030038F0,  # 4 bytes, player Y coordinate
    "PLAYER_X": 0x030038F4,  # 4 bytes, player X coordinate
}

def read_memory(gba, addr, size=1):
    """Generic memory reading function"""
    return gba.read_memory(addr, size)

def read_bit(gba, addr, bit: int) -> bool:
    """Read a specific bit from a memory address"""
    value = read_memory(gba, addr)
    return bin(256 + value)[-bit - 1] == "1"

def bit_count(value):
    """Count number of 1 bits in a value"""
    return bin(value).count("1")

def read_player_health(gba):
    """Reads Link's current health (uint8)"""
    return gba.read_u8(ADDRESSES["PLAYER_HEALTH"])

def read_rupees(gba):
    """Reads Link's current rupee count (uint16)"""
    return gba.read_u16(ADDRESSES["RUPEES"])

def read_small_keys(gba):
    """Reads Link's current small keys (uint8)"""
    return gba.read_u8(ADDRESSES["SMALL_KEYS"])

def read_bombs(gba):
    """Reads Link's current bombs (uint8)"""
    return gba.read_u8(ADDRESSES["BOMBS"])

def read_maps(gba):
    """Reads Link's current maps (uint8)"""
    return gba.read_u8(ADDRESSES["MAPS"])

def read_boomerang(gba):
    """Reads Link's boomerang type (uint8): 1=Blue, 2=Red"""
    return gba.read_u8(ADDRESSES["BOOMERANG"])

def read_master_key(gba):
    """Reads Link's master key (big key) (uint8)"""
    return gba.read_u8(ADDRESSES["MASTER_KEY"])

def read_lamp(gba):
    """Reads Link's lamp (uint8)"""
    return gba.read_u8(ADDRESSES["LAMP"])

def read_sword(gba):
    """Reads Link's sword (uint8)"""
    return gba.read_u8(ADDRESSES["SWORD"])

def read_items(gba):
    """Reads Link's inventory (placeholder)"""
    return gba.read_memory(ADDRESSES.get("ITEMS", 0), 16)  # Adjust size as needed

def read_player_y(gba):
    """Reads 4 bytes for player Y coordinate (int)"""
    return int.from_bytes(gba.read_memory(ADDRESSES["PLAYER_Y"], 4), 'little')

def read_player_x(gba):
    """Reads 4 bytes for player X coordinate (int)"""
    return int.from_bytes(gba.read_memory(ADDRESSES["PLAYER_X"], 4), 'little')

def read_player_xy(gba):
    """Returns (x, y) tuple of player coordinates (int, int)"""
    return (read_player_x(gba), read_player_y(gba))

def get_area_description(gba):
    """Get a human-readable description of the current area"""
    x, y = read_player_xy(gba)
    return get_area_name(x, y)

def get_area_rewardable(x, y):
    return is_area_rewardable(x, y)

def read_enemies_killed(gba):
    """Reads the number of enemies killed (uint8)"""
    return gba.read_u8(ADDRESSES["ENEMIES_KILLED"])

def read_zelda_with_link(gba):
    """Reads if Zelda the princess is with Link (uint8: 1=yes, 0=no)"""
    return gba.read_u8(ADDRESSES["ZELDA_WITH_LINK"])