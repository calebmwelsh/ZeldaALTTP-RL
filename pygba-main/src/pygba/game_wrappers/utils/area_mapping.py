from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class Area:
    name: str
    x_range: Tuple[int, int]  # (min_x, max_x)
    y_range: Tuple[int, int]  # (min_y, max_y)
    rewardable: bool = True  # Whether this area should give a reward

    def contains(self, x: int, y: int) -> bool:
        """Check if the given coordinates are within this area"""
        return (self.x_range[0] <= x <= self.x_range[1] and 
                self.y_range[0] <= y <= self.y_range[1])

# Define areas with mapped coordinates
AREAS = {
    "links_house": Area(
        name="Link's House",
        x_range=(2344, 2504),
        y_range=(8528, 8700),
        rewardable=False
    ),
    "links_land": Area(
        name="Link's Land",
        x_range=(1570, 2530),
        y_range=(2440, 3030),
        rewardable=True
    ),
    "castle_bridge": Area(
        name="Hyrule Castle Bridge",
        x_range=(1624, 2480),
        y_range=(2272, 2439),
        rewardable=True
    ),
    "castle_grounds": Area(
        name="Hyrule Castle Grounds",
        x_range=(1570, 2480),
        y_range=(1530, 2272),
        rewardable=True
    ),
    # Hyrule Castle Basement 1
    "hc_b1_room1": Area(
        name="Hyrule Castle B1 Room 1",
        x_range=(2672, 2992),
        y_range=(2620, 2815),
        rewardable=True
    ),
    "hc_b1_room2": Area(
        name="Hyrule Castle B1 Room 2",
        x_range=(2615, 2976),
        y_range=(2815, 3070),
        rewardable=True
    ),
    # Hyrule Castle Floor 1
    "hc_f1_entrance": Area(
        name="Hyrule Castle Entrance",
        x_range=(505, 1016),
        y_range=(3055, 3580),
        rewardable=True
    ),
    "hc_f1_throne_room": Area(
        name="Hyrule Castle Throne Room",
        x_range=(575, 936),
        y_range=(2590, 3055),
        rewardable=True
    ),
    "hc_f1_left_wing": Area(
        name="Hyrule Castle Left Wing",
        x_range=(296, 505),
        y_range=(3055, 3580),
        rewardable=True
    ),
    "hc_f1_right_wing": Area(
        name="Hyrule Castle Right Wing",
        x_range=(1016, 1352),
        y_range=(3055, 3580),
        rewardable=True
    ),
    "hc_f1_upper_left_wing": Area(
        name="Hyrule Castle Upper Left Wing",
        x_range=(343, 510),
        y_range=(2664, 3055),
        rewardable=True
    ),
    "hc_f1_upper_right_wing": Area(
        name="Hyrule Castle Upper Right Wing",
        x_range=(1010, 1288),
        y_range=(2608, 3055),
        rewardable=True
    ),
    "hc_f1_basement_entrance": Area(
        name="Hyrule Castle Basement Entrance",
        x_range=(490, 1025),
        y_range=(30, 150),
        rewardable=True
    ),
    "hc_b1_room3": Area(
        name="Hyrule Castle B1 Room 3",
        x_range=(1224, 1320),
        y_range=(3620, 3776),
        rewardable=True
    ),
    "hc_b1_room4a": Area(
        name="Hyrule Castle B1 Room 4A",
        x_range=(1054, 1370),
        y_range=(3888, 4496),
        rewardable=True
    ),
    "hc_b1_room4b": Area(
        name="Hyrule Castle B1 Room 4B",
        x_range=(608, 996),
        y_range=(4168, 4494),
        rewardable=True
    ),
    "hc_b1_room5": Area(
        name="Hyrule Castle B1 Room 5",
        x_range=(576, 688),
        y_range=(3894, 4008),
        rewardable=True
    ),
    "hc_b1_room6": Area(
        name="Hyrule Castle B1 Room 6",
        x_range=(822, 938),
        y_range=(3934, 4008),
        rewardable=True
    ),
    "hc_b1_room7": Area(
        name="Hyrule Castle B1 Room 7",
        x_range=(606, 668),
        y_range=(3688, 3776),
        rewardable=True
    ),
    # Hyrule Castle Basement 2
    "hc_b2_room": Area(
        name="Hyrule Castle B2 Room",
        x_range=(64, 176),
        y_range=(3632, 3664),
        rewardable=True
    ),
    # Hyrule Castle Basement 3
    "hc_b3_room": Area(
        name="Hyrule Castle B3 Room",
        x_range=(64, 424),
        y_range=(4144, 4288),
        rewardable=True
    )
}

def get_area_by_coords(x: int, y: int) -> Optional[Area]:
    """
    Get the area containing the given coordinates.
    Returns None if no matching area is found.
    """
    for area in AREAS.values():
        if area.contains(x, y):
            return area
    return None

def get_area_name(x: int, y: int) -> str:
    """Get a human-readable name for the area at the given coordinates"""
    area = get_area_by_coords(x, y)
    if area:
        return area.name
    return f"Unknown Area ({x}, {y})"

def is_area_rewardable(x: int, y: int) -> bool:
    area = get_area_by_coords(x, y)
    return area.rewardable if area else False 