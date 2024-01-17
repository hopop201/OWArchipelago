import os
import pkgutil
from typing import Callable, Dict, List, NamedTuple, Optional

from worlds.generic.Rules import set_rule
from BaseClasses import Location, MultiWorld, Region

from . import jsonc
from .Items import OuterWildsItem
from .RuleEval import eval_rule


class OuterWildsLocation(Location):
    game = "Outer Wilds"


class OuterWildsLocationData(NamedTuple):
    region: str
    address: Optional[int] = None
    can_create: Callable[[MultiWorld, int], bool] = lambda multiworld, player: True
    locked_item: Optional[str] = None


class OuterWildsRegionData(NamedTuple):
    connecting_regions: List[str] = []


jsonc_locations_data = pkgutil.get_data(__name__, 'shared_static_logic/locations.jsonc')
locations_data = jsonc.loads(jsonc_locations_data.decode('utf-8'))

jsonc_connections_data = pkgutil.get_data(__name__, 'shared_static_logic/connections.jsonc')
connections_data = jsonc.loads(jsonc_connections_data.decode('utf-8'))


location_data_table: Dict[str, OuterWildsLocationData] = {}
for location_datum in locations_data:
    location_data_table[location_datum["name"]] = OuterWildsLocationData(
        address=location_datum["address"],
        region=(location_datum["region"] if "region" in location_datum else None),
        locked_item=(location_datum["locked_item"] if "locked_item" in location_datum else None)
    )

location_table = {name: data.address for name, data in location_data_table.items() if data.address is not None}

location_name_groups = {
    "Frequencies": {
        "Distress Beacon Frequency",
        "Quantum Fluctuations Frequency",
        "Hide & Seek Frequency",
    },
    "Signals": {
        "ET: Drum Signal",
        "AR: Whistling Signal",
        "BH: Banjo Signal",
        "GD: Flute Signal",
        "DB: Harmonica Signal",
        "TH: Museum Shard Signal",
        "TH: Grove Shard Signal",
        "ET: Cave Shard Signal",
        "BH: Tower Shard Signal",
        "GD: Island Shard Signal",
        "Quantum Moon Signal",
        "BH: Escape Pod 1 Signal",
        "ET: Escape Pod 2 Signal",
        "DB: Escape Pod 3 Signal",
        "TH: Galena's Radio Signal",
        "TH: Tephra's Radio Signal",
    },
    "Hourglass Twins": {
        "ET: High Energy Lab (Upper Text Wall)",
        "ET: Sunless City Shrine (Entrance Text Wall)",
        "ET: Quantum Moon Locator (2nd Scroll)",
        "ET: Fossil (Children's Text)",
        "ET: Lakebed Cave (Floor Text)",
        "ET: Coleus' Cave (Text Wall)",
        "Enter the Ash Twin Project",
        "ET: Drum Signal",
        "ET: Cave Shard Signal",
        "ET: Escape Pod 2 Signal",
    },
    "Timber Hearth": {
        "TH: Ghost Matter Plaque",
        "TH: Zero-G Repairs",
        "TH: Get the Translator from Hal",
        "TH: Talk to Hornfels",
        "TH: Talk to Tektite about Bramble Seed",
        "TH: Mines (Text Wall)",
        "Hide & Seek Frequency",
        "TH: Museum Shard Signal",
        "TH: Grove Shard Signal",
    },
    "Brittle Hollow": {
        "BH: Southern Observatory (Tornado Text Wall)",
        "BH: Old Settlement Murals",
        "BH: Forge (2nd Scroll)",
        "BH: Tower (Top Floor Text Wall)",
        "BH: Banjo Signal",
        "BH: Tower Shard Signal",
        "BH: Escape Pod 1 Signal",
    },
    "Giant's Deep": {
        "GD: Enter the Orbital Probe Cannon",
        "GD: Control Module Logs (Text Wheels)",
        "GD: Bramble Island (Tape Recorder)",
        "GD: Construction Yard (Text Wall)",
        "GD: Statue Island Workshop (Text Wheel)",
        "GD: Tower Rule (Pedestal Text)",
        "GD: Complete the Tower (Text Wall)",
        "GD: Enter the Ocean Depths",
        "GD: Enter the Core",
        "GD: See the Coordinates",
    },
    "Quantum Moon": {
        "QM: Land",
        "QM: Explore the Sixth Location",
    },
    "Dark Bramble": {
        "DB: Feldspar's Note",
        "DB: Nomai Grave (Text Wheel)",
        "DB: Find The Vessel",
    },
}

region_data_table: Dict[str, OuterWildsRegionData] = {}


def create_regions(mw: MultiWorld, p: int, create_item: Callable[[str], OuterWildsItem]) -> None:
    # start by ensuring every region is a key in region_data_table
    for ld in locations_data:
        region_name = ld["region"]
        if region_name not in region_data_table:
            region_data_table[region_name] = OuterWildsRegionData()

    for cd in connections_data:
        if cd["from"] not in region_data_table:
            region_data_table[cd["from"]] = OuterWildsRegionData()
        if cd["to"] not in region_data_table:
            region_data_table[cd["to"]] = OuterWildsRegionData()

    # actually create the Regions, initially all empty
    for region_name in region_data_table.keys():
        mw.regions.append(Region(region_name, p, mw))

    # add locations and connections to each region
    for region_name, region_data in region_data_table.items():
        region = mw.get_region(region_name, p)
        region.add_locations({
            location_name: location_data.address for location_name, location_data in location_data_table.items()
            if location_data.region == region_name
        }, OuterWildsLocation)

        exit_connections = [cd for cd in connections_data if cd["from"] == region_name]
        exit_names = []
        rules = {}
        for exit_connection in exit_connections:
            exit_name = exit_connection["to"]
            exit_names.append(exit_name)
            rules[exit_name] = lambda state, rule=exit_connection["requires"]: eval_rule(state, p, rule)
        region.add_exits(exit_names, rules)

    # add access rules to the locations
    for ld in locations_data:
        set_rule(mw.get_location(ld["name"], p),
                 lambda state, rule=ld["requires"]: eval_rule(state, p, rule))

    # place locked locations
    for name, data in location_data_table.items():
        if data.locked_item:
            mw.get_location(name, p).place_locked_item(create_item(data.locked_item))