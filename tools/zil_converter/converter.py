"""ZIL to JSON world converter.

Converts extracted ZIL entities into the LLM-IF JSON world format.
"""

from typing import Dict, Any, List, Optional


class LocationConverter:
    """Convert ZIL rooms to JSON locations."""

    def __init__(self):
        self.todos = []

    def convert_room(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert extracted room to JSON location format."""
        location = {
            "id": room_data["id"],
            "name": room_data["name"],
            "attributes": self._build_attributes(room_data),
            "connections": self._convert_exits(room_data["exits"], room_data["id"])
        }

        return location

    def _build_attributes(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build location attributes from ZIL room data."""
        attrs = {}

        # Description hints
        desc_parts = []
        if room_data["long_desc"]:
            desc_parts.append(room_data["long_desc"])
        if room_data["name"]:
            desc_parts.append(room_data["name"])

        attrs["description_hints"] = " - ".join(desc_parts) if desc_parts else room_data["name"]

        # Lighting
        flags = room_data.get("flags", [])
        attrs["lighting"] = self._infer_lighting(flags)

        # Outdoor/indoor
        attrs["is_outdoors"] = "RLANDBIT" not in flags

        # Add any custom ZIL attributes we want to preserve
        attrs.update(self._extract_custom_attributes(room_data))

        return attrs

    def _infer_lighting(self, flags: List[str]) -> str:
        """Infer lighting level from flags.

        LIGHTBIT or ONBIT usually means inherently lit.
        """
        if "LIGHTBIT" in flags or "ONBIT" in flags:
            return "bright"
        else:
            # Let LLM decide based on description
            return "variable"

    def _extract_custom_attributes(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract custom attributes from ZIL properties.

        Preserve interesting ZIL properties as JSON attributes for LLM interpretation.
        """
        custom = {}
        zil_props = room_data.get("_zil_properties", {})

        # Preserve pseudo objects for description
        if room_data.get("pseudo_objects"):
            custom["zil_pseudo_objects"] = room_data["pseudo_objects"]

        # Preserve global objects (scenery, etc.)
        if room_data.get("global_objects"):
            custom["zil_global_objects"] = [
                str(obj).lower().replace("-", "_") for obj in room_data["global_objects"]
            ]

        # Preserve flags as hints
        if room_data.get("flags"):
            custom["zil_flags"] = [f.lower() for f in room_data["flags"]]

        return custom

    def _convert_exits(self, zil_exits: Dict[str, Any], room_id: str) -> Dict[str, str]:
        """Convert ZIL exits to JSON connections.

        For now, only handle direct exits. Conditional exits need puzzle system.
        """
        connections = {}

        for direction, exit_def in zil_exits.items():
            if exit_def["type"] == "direct":
                # Simple exit: just add connection
                connections[direction] = exit_def["destination"]
            else:
                # Conditional exit: add TODO and placeholder
                condition = exit_def.get("condition", "unknown")
                self.todos.append(
                    f"Conditional exit in {room_id}: {direction} -> "
                    f"condition={condition}\n"
                    f"  Consider creating puzzle or adding logic to gate this exit"
                )
                # For now, don't add the connection (blocked until puzzle resolved)

        return connections

    def get_todos(self) -> List[str]:
        """Get all TODO notes."""
        return self.todos


class ItemConverter:
    """Convert ZIL objects to JSON items."""

    def __init__(self):
        self.todos = []

    def convert_object(self, obj_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert extracted object to JSON item format."""
        item = {
            "id": obj_data["id"],
            "name": obj_data["name"],
            "attributes": self._build_attributes(obj_data)
        }

        return item

    def _build_attributes(self, obj_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build item attributes from ZIL object data."""
        attrs = {}

        # Description hints
        if obj_data.get("description"):
            attrs["description_hints"] = obj_data["description"]
        elif obj_data.get("name"):
            attrs["description_hints"] = obj_data["name"]

        # Object type
        attrs["type"] = obj_data.get("type", "generic")

        # Type-specific attributes
        attrs.update(self._convert_type_specific(obj_data))

        # Synonyms and adjectives for parsing
        if obj_data.get("synonyms"):
            attrs["zil_synonyms"] = obj_data["synonyms"]

        if obj_data.get("adjectives"):
            attrs["zil_adjectives"] = obj_data["adjectives"]

        # Size (for inventory management)
        if obj_data.get("size"):
            attrs["size"] = obj_data["size"]

        # Preserve flags
        if obj_data.get("flags"):
            attrs["zil_flags"] = [f.lower() for f in obj_data["flags"]]

        return attrs

    def _convert_type_specific(self, obj_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert type-specific ZIL properties to JSON attributes."""
        attrs = {}
        flags = obj_data.get("flags", [])

        # Container logic
        if "CONTBIT" in flags:
            attrs["container"] = True
            attrs["open"] = "OPENBIT" in flags
            if obj_data.get("capacity"):
                attrs["capacity"] = obj_data["capacity"]

        # Door logic
        if "DOORBIT" in flags:
            attrs["is_door"] = True
            attrs["is_open"] = "OPENBIT" in flags
            attrs["is_locked"] = "LOCKEDBIT" in flags

        # Readable items
        if obj_data.get("text"):
            attrs["text"] = obj_data["text"]
            attrs["type"] = "readable"

        # Takeable items
        if "TAKEBIT" in flags:
            attrs["takeable"] = True
        else:
            attrs["takeable"] = False

        # Light sources
        if "LIGHTBIT" in flags:
            attrs["provides_light"] = True
            attrs["is_lit"] = "ONBIT" in flags

        # Weapons
        if obj_data.get("type") == "weapon":
            # Add placeholder weapon stats for LLM to interpret
            attrs["weapon"] = True
            self.todos.append(
                f"Object {obj_data['id']} is a weapon - add damage/attack stats if needed"
            )

        return attrs

    def get_todos(self) -> List[str]:
        """Get all TODO notes."""
        return self.todos


class NPCConverter:
    """Convert ZIL NPCs to JSON npcs."""

    def __init__(self):
        self.todos = []

    def convert_npc(self, npc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert extracted NPC to JSON npc format."""
        npc = {
            "id": npc_data["id"],
            "name": npc_data["name"],
            "attributes": self._build_attributes(npc_data)
        }

        return npc

    def _build_attributes(self, npc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build NPC attributes from ZIL data."""
        attrs = {}

        # Description hints
        if npc_data.get("description"):
            attrs["description_hints"] = npc_data["description"]
        else:
            attrs["description_hints"] = npc_data["name"]

        # Creature type
        attrs["creature_type"] = "humanoid"  # Default, LLM can interpret

        # Hostility
        hostility = npc_data.get("hostility", "neutral")
        attrs["hostility"] = hostility

        # Personality (LLM will expand)
        attrs["personality"] = f"{npc_data['name']} from Planetfall"

        # Special behavior note
        if npc_data.get("action_routine"):
            attrs["special_behavior"] = (
                f"Complex behavior defined in ZIL routine: {npc_data['action_routine']}"
            )
            self.todos.append(
                f"NPC {npc_data['id']} needs behavior implementation\n"
                f"  Review ZIL routine {npc_data['action_routine']} for dialogue and AI logic"
            )

        # Preserve flags
        if npc_data.get("flags"):
            attrs["zil_flags"] = [f.lower() for f in npc_data["flags"]]

        return attrs

    def get_todos(self) -> List[str]:
        """Get all TODO notes."""
        return self.todos


class WorldConverter:
    """Main converter that coordinates location, item, and NPC conversion."""

    def __init__(self):
        self.location_converter = LocationConverter()
        self.item_converter = ItemConverter()
        self.npc_converter = NPCConverter()

    def convert(self, game_data: Dict[str, Any], smart: bool = True) -> Dict[str, Any]:
        """Convert extracted game data to JSON world format.

        Args:
            game_data: Extracted rooms, objects, NPCs from GameExtractor
            smart: If True, apply smart pattern matching (future feature)

        Returns:
            Complete JSON world structure
        """
        # Convert entities
        locations = {}
        for room in game_data["rooms"]:
            location = self.location_converter.convert_room(room)
            locations[location["id"]] = location

        items = {}
        item_locations = {}
        for obj in game_data["objects"]:
            item = self.item_converter.convert_object(obj)
            items[item["id"]] = item

            # Track initial location
            if obj.get("initial_location"):
                item_locations[item["id"]] = obj["initial_location"]

        npcs = {}
        npc_locations = {}
        for npc_data in game_data["npcs"]:
            npc = self.npc_converter.convert_npc(npc_data)
            npcs[npc["id"]] = npc

            # Track initial location
            if npc_data.get("initial_location"):
                npc_locations[npc["id"]] = npc_data["initial_location"]

        # Determine player start location
        # Look for room with RLANDBIT (usually start room) or just use first room
        player_location = self._find_start_location(game_data["rooms"])

        # Build complete world
        world = {
            "locations": locations,
            "items": items,
            "npcs": npcs,
            "item_locations": item_locations,
            "npc_locations": npc_locations,
            "player_location": player_location,
            "flags": {},
            "puzzles": {}
        }

        return world

    def _find_start_location(self, rooms: List[Dict[str, Any]]) -> str:
        """Find the starting location for the player.

        Heuristics:
        1. Look for room with "START" in name
        2. Look for first room with RLANDBIT
        3. Default to first room
        """
        for room in rooms:
            if "START" in room.get("zil_name", "").upper():
                return room["id"]

        for room in rooms:
            if "RLANDBIT" in room.get("flags", []):
                return room["id"]

        # Default to first room
        if rooms:
            return rooms[0]["id"]

        return "unknown"

    def get_todo_notes(self) -> str:
        """Get all TODO notes as formatted markdown."""
        all_todos = (
            self.location_converter.get_todos() +
            self.item_converter.get_todos() +
            self.npc_converter.get_todos()
        )

        if not all_todos:
            return "# Conversion Notes\n\nNo manual adaptations needed - conversion was clean!"

        notes = "# ZIL Conversion - Adaptation Notes\n\n"
        notes += "## Manual Review Required\n\n"
        notes += "The following items need manual review and possible implementation:\n\n"

        for i, todo in enumerate(all_todos, 1):
            notes += f"{i}. {todo}\n\n"

        return notes
