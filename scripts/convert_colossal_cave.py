#!/usr/bin/env python3
"""Convert Open Adventure (Colossal Cave) YAML to IF engine JSON format.

Usage:
    python scripts/convert_colossal_cave.py --download --output worlds/colossal_cave.json
    python scripts/convert_colossal_cave.py --input data/adventure.yaml --validate
"""

import yaml
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

class ColossalCaveConverter:
    """Converts Open Adventure YAML to our JSON format."""

    GITLAB_URL = "https://gitlab.com/esr/open-adventure/-/raw/master/adventure.yaml"

    def __init__(self, yaml_path: str):
        """Initialize converter with YAML file path."""
        self.yaml_path = Path(yaml_path)
        self.yaml_data: Dict[str, Any] = {}
        self.output: Dict[str, Any] = {
            "locations": {},
            "npcs": {},
            "items": {},
            "player": self._create_default_player(),
            "npc_locations": {},
            "item_locations": {},
            "player_location": "road",  # Will be set correctly
            "turn_count": 0,
            "history": [],
            "flags": {}
        }
        self.location_id_map: Dict[str, str] = {}  # YAML ID -> readable ID
        self.item_id_map: Dict[str, str] = {}

    def _load_yaml(self) -> None:
        """Load YAML data from file."""
        print(f"Loading YAML from {self.yaml_path}...")
        with open(self.yaml_path, 'r') as f:
            self.yaml_data = yaml.safe_load(f)

        # Convert !!omap (list of tuples) to regular dict
        locations = self.yaml_data.get('locations', [])
        if isinstance(locations, list):
            self.yaml_data['locations'] = {key: value for key, value in locations}

        objects = self.yaml_data.get('objects', [])
        if isinstance(objects, list):
            self.yaml_data['objects'] = {key: value for key, value in objects}

        print(f"✓ Loaded {len(self.yaml_data.get('locations', {}))} locations")
        print(f"✓ Loaded {len(self.yaml_data.get('objects', {}))} objects")

    def convert(self) -> Dict[str, Any]:
        """Main conversion orchestrator."""
        self._load_yaml()
        self._convert_locations()
        self._convert_objects_to_items()
        self._convert_travel_rules()
        self._place_items()
        self._handle_special_mechanics()
        self._set_starting_location()
        self._validate_output()
        return self.output

    def _convert_locations(self) -> None:
        """Convert YAML locations to JSON locations."""
        locations_data = self.yaml_data.get("locations", {})
        print(f"\nConverting {len(locations_data)} locations...")

        for loc_id, loc_data in locations_data.items():
            readable_id = self._make_readable_id(loc_id, "LOC_")
            self.location_id_map[loc_id] = readable_id

            desc = loc_data.get("description", {})
            long_desc = desc.get("long", "")
            short_desc = desc.get("short", "")
            conditions = loc_data.get("conditions", {})

            # Infer attributes
            lighting = "bright" if conditions.get("LIT") else "dark"
            is_outdoors = self._infer_outdoors(long_desc)

            # Generate name, handling None values
            name = short_desc or (long_desc[:50] if long_desc else readable_id.replace('_', ' ').title())

            self.output["locations"][readable_id] = {
                "id": readable_id,
                "name": name,
                "attributes": {
                    "description_hints": long_desc or "",
                    "lighting": lighting,
                    "is_outdoors": is_outdoors,
                    "has_windows": False,
                    "original_id": loc_id
                },
                "connections": {}
            }

        print(f"✓ Converted {len(self.output['locations'])} locations")

    def _convert_objects_to_items(self) -> None:
        """Convert YAML objects to JSON items."""
        objects_data = self.yaml_data.get("objects", {})
        print(f"\nConverting {len(objects_data)} objects to items...")

        for obj_id, obj_data in objects_data.items():
            readable_id = self._make_readable_id(obj_id, "OBJ_")
            self.item_id_map[obj_id] = readable_id

            inventory_desc = obj_data.get("inventory") or "unknown item"
            words = obj_data.get("words", [])
            is_treasure = obj_data.get("treasure", False)

            # Use first word as name, capitalize it
            if words:
                name = words[0].capitalize()
            elif inventory_desc:
                name = inventory_desc.split()[0].capitalize() if inventory_desc.split() else readable_id.capitalize()
            else:
                name = readable_id.capitalize()

            # Determine type
            item_type = "treasure" if is_treasure else "misc"

            self.output["items"][readable_id] = {
                "id": readable_id,
                "name": name,
                "attributes": {
                    "description_hints": inventory_desc,
                    "type": item_type,
                    "treasure": is_treasure,
                    "aliases": words,
                    "original_id": obj_id,
                    "weight": 1.0
                }
            }

        print(f"✓ Converted {len(self.output['items'])} items")

    def _convert_travel_rules(self) -> None:
        """Extract simple directional connections from travel rules."""
        print("\nConverting travel rules to connections...")
        locations_data = self.yaml_data.get("locations", {})
        connection_count = 0

        for loc_id, loc_data in locations_data.items():
            readable_id = self.location_id_map.get(loc_id)
            if not readable_id:
                continue

            travel = loc_data.get("travel", [])
            for rule in travel:
                verbs = rule.get("verbs", [])
                action = rule.get("action", [])

                # Only handle simple "goto" actions (no conditions)
                if len(action) >= 2 and action[0] == "goto":
                    dest_yaml_id = action[1]
                    dest_readable_id = self.location_id_map.get(dest_yaml_id)

                    if not dest_readable_id:
                        continue

                    # Map first verb to direction
                    for verb in verbs:
                        direction = self._verb_to_direction(verb)
                        if direction:
                            self.output["locations"][readable_id]["connections"][direction] = dest_readable_id
                            connection_count += 1
                            break  # One direction per rule

        print(f"✓ Created {connection_count} connections")

    def _place_items(self) -> None:
        """Place items at their starting locations."""
        print("\nPlacing items at starting locations...")
        objects_data = self.yaml_data.get("objects", {})
        placed_count = 0

        for obj_id, obj_data in objects_data.items():
            readable_id = self.item_id_map.get(obj_id)
            if not readable_id:
                continue

            locations = obj_data.get("locations", [])
            if locations:
                start_yaml_loc = locations[0]
                start_readable_loc = self.location_id_map.get(start_yaml_loc)

                if start_readable_loc:
                    self.output["item_locations"][readable_id] = start_readable_loc
                    placed_count += 1

        print(f"✓ Placed {placed_count} items")

    def _handle_special_mechanics(self) -> None:
        """Handle Colossal Cave special mechanics."""
        print("\nAdding special mechanics...")

        # Magic words
        magic_words = ["XYZZY", "PLUGH", "PLOVER", "FEE", "FIE", "FOE", "FOO"]
        for word in magic_words:
            self.output["flags"][f"magic_word_{word.lower()}"] = {
                "discovered": False,
                "description": f"Magic word from ancient times"
            }

        print(f"✓ Added {len(magic_words)} magic words")

    def _set_starting_location(self) -> None:
        """Set correct starting location."""
        # In Colossal Cave, game starts at LOC_START (converted to "start")
        if "start" in self.output["locations"]:
            self.output["player_location"] = "start"
        elif "road" in self.output["locations"]:
            self.output["player_location"] = "road"
        else:
            # Fallback: use first non-nowhere location
            for loc_id in self.output["locations"].keys():
                if loc_id != "nowhere":
                    self.output["player_location"] = loc_id
                    break

        print(f"✓ Set starting location: {self.output['player_location']}")

    def _validate_output(self) -> None:
        """Validate output structure."""
        print("\nValidating output...")

        # Check all connections reference valid locations
        invalid_connections = []
        for loc_id, loc in self.output["locations"].items():
            for direction, dest_id in loc["connections"].items():
                if dest_id not in self.output["locations"]:
                    invalid_connections.append(f"{loc_id} -> {direction} -> {dest_id}")

        if invalid_connections:
            print(f"⚠ Warning: {len(invalid_connections)} invalid connections")
            for conn in invalid_connections[:5]:
                print(f"  - {conn}")

        # Check all item locations reference valid locations
        invalid_placements = []
        for item_id, loc_id in self.output["item_locations"].items():
            if loc_id not in self.output["locations"]:
                invalid_placements.append(f"{item_id} at {loc_id}")

        if invalid_placements:
            print(f"⚠ Warning: {len(invalid_placements)} invalid item placements")

        print("✓ Validation complete")

    # Helper methods

    def _make_readable_id(self, yaml_id: str, prefix: str) -> str:
        """Convert YAML ID to readable format.

        LOC_OUTSIDEBUILDING → outside_building
        OBJ_KEYS → keys
        """
        cleaned = yaml_id.replace(prefix, "")
        return cleaned.lower()

    def _verb_to_direction(self, verb: str) -> Optional[str]:
        """Map YAML verb to our direction."""
        mapping = {
            "NORTH": "north", "N": "north",
            "SOUTH": "south", "S": "south",
            "EAST": "east", "E": "east",
            "WEST": "west", "W": "west",
            "UP": "up", "U": "up",
            "DOWN": "down", "D": "down",
            "IN": "in", "INWAR": "in",
            "OUT": "out", "OUTWA": "out",
        }
        return mapping.get(verb)

    def _infer_outdoors(self, description: str) -> bool:
        """Infer if location is outdoors from description."""
        if not description:
            return False

        outdoor_keywords = [
            "forest", "road", "hill", "valley", "stream", "gully",
            "outside", "grove", "clearing", "path", "trail"
        ]
        desc_lower = description.lower()
        return any(kw in desc_lower for kw in outdoor_keywords)

    def _create_default_player(self) -> Dict[str, Any]:
        """Create default player for Colossal Cave."""
        return {
            "name": "Adventurer",
            "attributes": {
                "class": "explorer",
                "level": 1,
                "hp": 10,
                "hp_max": 10,
                "armor_class": 10,
                "attack_bonus": 2,
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 14,
                "wis": 12,
                "cha": 10
            },
            "inventory": []
        }


def download_adventure_yaml(output_path: str) -> None:
    """Download adventure.yaml from GitLab."""
    url = ColossalCaveConverter.GITLAB_URL
    print(f"Downloading from {url}...")

    response = requests.get(url)
    response.raise_for_status()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'wb') as f:
        f.write(response.content)

    print(f"✓ Downloaded to {output_path}")


def validate_output_as_gamestate(json_path: str) -> bool:
    """Validate that output can be loaded as GameState."""
    print(f"\nValidating {json_path} as GameState...")

    try:
        # Import here to avoid circular dependency
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.models.game_state import GameState

        game_state = GameState.from_file(json_path)

        print(f"✓ Valid GameState!")
        print(f"  - {len(game_state.locations)} locations")
        print(f"  - {len(game_state.items)} items")
        print(f"  - {len(game_state.npcs)} NPCs")
        print(f"  - Starting location: {game_state.player_location}")

        return True
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert Colossal Cave Adventure YAML to IF engine JSON"
    )
    parser.add_argument(
        "--input",
        default="data/adventure.yaml",
        help="Input YAML file (default: data/adventure.yaml)"
    )
    parser.add_argument(
        "--output",
        default="worlds/colossal_cave.json",
        help="Output JSON file (default: worlds/colossal_cave.json)"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download YAML from GitLab before converting"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output by loading as GameState"
    )

    args = parser.parse_args()

    # Download if requested
    if args.download:
        download_adventure_yaml(args.input)

    # Convert
    print("\n" + "="*60)
    print("COLOSSAL CAVE ADVENTURE CONVERTER")
    print("="*60)

    converter = ColossalCaveConverter(args.input)
    output = converter.convert()

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Output saved to {args.output}")
    print(f"  - {len(output['locations'])} locations")
    print(f"  - {len(output['items'])} items")
    print(f"  - {len(output.get('npcs', {}))} NPCs")

    # Validate if requested
    if args.validate:
        validate_output_as_gamestate(args.output)

    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
