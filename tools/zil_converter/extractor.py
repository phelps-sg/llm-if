"""ZIL entity extractor.

Extracts game entities (rooms, objects, NPCs) from parsed ZIL S-expressions
into intermediate Python data structures.
"""

from typing import List, Any, Dict, Optional
from sexpdata import Symbol
from .zil_serializer import extract_raw_zil


class ZILExtractor:
    """Base extractor with common utilities."""

    def __init__(self):
        self.todos = []  # Track items needing manual review
        self.routines = {}  # Map of routine names to their ZIL code

    def _parse_properties(self, sexp_list: List[Any]) -> Dict[str, Any]:
        """Parse ZIL property list into dictionary.

        ZIL properties come in pairs: (PROP value) or standalone symbols.
        Example: (DESC "Room") (FLAGS LIGHTBIT ONBIT)
        """
        props = {}
        i = 0
        while i < len(sexp_list):
            item = sexp_list[i]

            # Handle property pairs
            if isinstance(item, list) and len(item) >= 2:
                prop_name = str(item[0]).upper() if isinstance(item[0], Symbol) else str(item[0])

                # Single value property
                if len(item) == 2:
                    props[prop_name] = self._normalize_value(item[1])
                # Multi-value property (e.g., FLAGS LIGHTBIT ONBIT)
                else:
                    props[prop_name] = [self._normalize_value(v) for v in item[1:]]

            i += 1

        return props

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a ZIL value to Python type."""
        if isinstance(value, Symbol):
            return str(value)
        elif isinstance(value, str):
            return value
        elif isinstance(value, (int, float, bool)):
            return value
        elif isinstance(value, list):
            return [self._normalize_value(v) for v in value]
        else:
            return str(value)

    def _normalize_id(self, zil_id: Any) -> str:
        """Convert ZIL identifier to lowercase snake_case ID.

        Examples:
            MESS-HALL -> mess_hall
            BALCONY -> balcony
            DECK-NINE -> deck_nine
        """
        if zil_id is None:
            return ""

        id_str = str(zil_id) if isinstance(zil_id, Symbol) else str(zil_id)
        return id_str.lower().replace("-", "_")

    def _add_todo(self, message: str):
        """Add a TODO note for manual review."""
        self.todos.append(message)

    def get_todos(self) -> List[str]:
        """Get all TODO notes."""
        return self.todos


class RoomExtractor(ZILExtractor):
    """Extract room data from ZIL ROOM forms."""

    def extract_room(self, room_sexp: List[Any]) -> Dict[str, Any]:
        """Extract room data from ZIL ROOM form.

        Example ZIL:
            <ROOM BALCONY
                (LOC ROOMS)
                (DESC "Balcony")
                (LDESC "balcony overlooking ocean...")
                (NORTH TO WINDING-STAIR)
                (DOWN TO OCEAN-FLOOR IF WATER-LEVEL-F)
                (FLAGS LIGHTBIT RLANDBIT)
                (PSEUDO "PLAQUE" PLAQUE-PSEUDO)
                (GLOBAL PLAQUE)
                (ACTION BALCONY-F)>
        """
        if not isinstance(room_sexp, list) or len(room_sexp) < 2:
            return None

        # First element should be ROOM symbol
        if not isinstance(room_sexp[0], Symbol) or str(room_sexp[0]).upper() != "ROOM":
            return None

        name = room_sexp[1]
        properties = self._parse_properties(room_sexp[2:])

        room_data = {
            "id": self._normalize_id(name),
            "zil_name": str(name),
            "name": properties.get("DESC", str(name)),
            "long_desc": properties.get("LDESC", ""),
            "exits": self._extract_exits(properties, room_sexp[2:]),
            "flags": self._extract_flags(properties),
            "pseudo_objects": properties.get("PSEUDO", []),
            "global_objects": properties.get("GLOBAL", []),
            "action_routine": properties.get("ACTION"),
            "raw_zil": extract_raw_zil(room_sexp),
            "_zil_properties": properties
        }

        # Add routine code if action routine is present and we have it
        if room_data["action_routine"]:
            routine_name = str(room_data["action_routine"]).upper()
            if routine_name in self.routines:
                room_data["action_routine_code"] = self.routines[routine_name]["zil_string"]
                room_data["action_routine_json"] = self.routines[routine_name]["zil_json"]
            else:
                self._add_todo(
                    f"Room {room_data['id']} has action routine: {room_data['action_routine']}\n"
                    f"  WARNING: Routine code not found in ZIL files"
                )

        # Add pseudo object routine codes if present
        # PSEUDO property format: (PSEUDO "NAME1" ROUTINE1 "NAME2" ROUTINE2 ...)
        # We get a list like ["NAME1", ROUTINE1, "NAME2", ROUTINE2, ...]
        if room_data["pseudo_objects"]:
            pseudo_routines = {}
            pseudo_list = room_data["pseudo_objects"]

            # Process in pairs: (name, routine_ref)
            for i in range(0, len(pseudo_list), 2):
                if i + 1 < len(pseudo_list):
                    pseudo_name = str(pseudo_list[i])  # The name players type
                    routine_ref = pseudo_list[i + 1]  # The routine symbol
                    routine_name = str(routine_ref).upper()

                    if routine_name in self.routines:
                        pseudo_routines[pseudo_name] = {
                            "routine_name": routine_name,
                            "zil_string": self.routines[routine_name]["zil_string"],
                            "zil_json": self.routines[routine_name]["zil_json"]
                        }

            if pseudo_routines:
                room_data["pseudo_object_routines"] = pseudo_routines

        return room_data

    def _extract_exits(self, props: Dict[str, Any], raw_props: List[Any]) -> Dict[str, Any]:
        """Extract room connections from direction properties.

        ZIL directions: NORTH, SOUTH, EAST, WEST, NE, NW, SE, SW, UP, DOWN, IN, OUT

        Exit types:
            (NORTH TO OTHER-ROOM)                           - Direct exit
            (DOWN PER DOOR-LOCKED-F)                        - Conditional exit (function check)
            (EAST IF FLAG-NAME)                             - Conditional exit (flag check)
            (DOWN TO STUDIO IF FALSE-FLAG ELSE "message")   - Blocked exit with message (ELSE clause)

        CRITICAL: (IN ROOMS) is NOT an exit - it means the room is IN the ROOMS container.
                  Only (IN TO somewhere) is an exit.
        """
        exits = {}
        directions = [
            "NORTH", "SOUTH", "EAST", "WEST",
            "NE", "NW", "SE", "SW",
            "UP", "DOWN", "IN", "OUT"
        ]

        for direction in directions:
            if direction in props:
                exit_def = props[direction]

                # SPECIAL CASE: (IN ROOMS) is not an exit, it's a container declaration
                # Only process if it's an actual exit like (IN TO somewhere)
                if direction == "IN":
                    # Check the raw property to see if it's (IN TO ...) or just (IN ROOMS)
                    is_exit = False
                    for prop in raw_props:
                        if isinstance(prop, list) and len(prop) >= 2:
                            prop_name = str(prop[0]).upper() if isinstance(prop[0], Symbol) else str(prop[0])
                            if prop_name == "IN" and len(prop) >= 3:
                                second_elem = str(prop[1]).upper() if isinstance(prop[1], Symbol) else str(prop[1])
                                if second_elem == "TO":
                                    is_exit = True
                                    break
                    if not is_exit:
                        # Skip (IN ROOMS) - it's not an exit
                        continue

                # Handle different exit formats
                if isinstance(exit_def, list) and len(exit_def) >= 2:
                    exit_type = str(exit_def[0]).upper() if isinstance(exit_def[0], Symbol) else str(exit_def[0])

                    # Check if this is a conditional exit with format: (TO destination IF condition)
                    # or (TO destination PER function)
                    is_conditional = False
                    condition_keyword = None
                    condition_value = None
                    destination = None

                    has_else_block = False
                    if exit_type == "TO" and len(exit_def) >= 4:
                        # Look for IF or PER later in the list, and check for ELSE clause
                        for i in range(2, len(exit_def)):
                            elem = str(exit_def[i]).upper() if isinstance(exit_def[i], Symbol) else str(exit_def[i])
                            if elem in ["IF", "PER"]:
                                is_conditional = True
                                condition_keyword = elem.lower()
                                destination = self._normalize_id(exit_def[1])

                                # Check if this is "IF OBJECT IS STATE" format
                                # Format: (EAST TO REACTOR-LOBBY IF CORRIDOR-DOOR IS OPEN)
                                is_object_state_format = False
                                if (elem == "IF" and i + 3 < len(exit_def)):
                                    is_keyword = str(exit_def[i + 2]).upper() if isinstance(exit_def[i + 2], Symbol) else str(exit_def[i + 2])
                                    if is_keyword == "IS":
                                        # This is "IF OBJECT IS STATE" format
                                        is_object_state_format = True
                                        object_name = self._normalize_id(exit_def[i + 1])
                                        state = str(exit_def[i + 3]).upper() if isinstance(exit_def[i + 3], Symbol) else str(exit_def[i + 3])
                                        condition_value = f"{object_name} IS {state}"
                                    elif i + 1 < len(exit_def):
                                        # Standard "IF FLAG" format
                                        condition_value = str(exit_def[i + 1])
                                elif i + 1 < len(exit_def):
                                    condition_value = str(exit_def[i + 1])

                                # Check for ELSE clause after condition
                                # Format: (DOWN TO STUDIO IF FALSE-FLAG ELSE "message")
                                # For "IF OBJECT IS STATE" format, ELSE would be at i+4
                                else_offset = 4 if is_object_state_format else 2
                                if i + else_offset < len(exit_def):
                                    else_keyword = str(exit_def[i + else_offset]).upper() if isinstance(exit_def[i + else_offset], Symbol) else None
                                    if else_keyword == "ELSE" and i + else_offset + 1 < len(exit_def):
                                        # ELSE with a message - treat as blocked exit
                                        else_value = exit_def[i + else_offset + 1]
                                        if isinstance(else_value, str):
                                            # This is a permanently blocked exit with a message
                                            exits[direction.lower()] = {
                                                "type": "blocked",
                                                "message": else_value
                                            }
                                            # Mark that we handled this with ELSE block
                                            has_else_block = True
                                break

                    # Skip further processing if we already handled this exit via ELSE block
                    if has_else_block:
                        continue

                    if is_conditional:
                        # Conditional exit (e.g., SW TO STONE-BARROW IF WON-FLAG)
                        exits[direction.lower()] = {
                            "type": "conditional",
                            "condition_type": condition_keyword,
                            "condition": condition_value,
                            "destination": destination
                        }

                        self._add_todo(
                            f"Conditional exit {direction.lower()} -> {destination}: "
                            f"{condition_keyword} {condition_value}\n"
                            f"  LLM will interpret from raw_zil"
                        )
                    elif exit_type == "TO":
                        # Direct exit (simple TO destination)
                        exits[direction.lower()] = {
                            "type": "direct",
                            "destination": self._normalize_id(exit_def[1])
                        }
                    elif exit_type in ["PER", "IF"]:
                        # Conditional exit (old format: PER function or IF flag)
                        exits[direction.lower()] = {
                            "type": "conditional",
                            "condition_type": exit_type.lower(),
                            "condition": str(exit_def[1]),
                            "destination": None  # May need to parse from routine
                        }

                        self._add_todo(
                            f"Conditional exit {direction.lower()} in room: "
                            f"condition={exit_def[1]}\n"
                            f"  Review ZIL to determine destination and create puzzle if needed"
                        )
                elif isinstance(exit_def, str):
                    # String message means blocked exit (e.g., "The windows are all boarded.")
                    # Store as conditional with message
                    exits[direction.lower()] = {
                        "type": "blocked",
                        "message": exit_def
                    }
                else:
                    # Simple destination (older ZIL format)
                    exits[direction.lower()] = {
                        "type": "direct",
                        "destination": self._normalize_id(exit_def)
                    }

        return exits

    def _extract_flags(self, props: Dict[str, Any]) -> List[str]:
        """Extract and normalize FLAGS property."""
        flags = props.get("FLAGS", [])
        if isinstance(flags, list):
            return [str(f).upper() for f in flags]
        else:
            return [str(flags).upper()]


class ObjectExtractor(ZILExtractor):
    """Extract object/item data from ZIL OBJECT forms."""

    def extract_object(self, obj_sexp: List[Any]) -> Dict[str, Any]:
        """Extract object data from ZIL OBJECT form.

        Example ZIL:
            <OBJECT CANTEEN
                (LOC MESS-HALL)
                (DESC "canteen")
                (FDESC "military issue canteen")
                (SYNONYM CANTEEN FLASK)
                (ADJECTIVE OCTAGONAL MILITARY)
                (FLAGS TAKEBIT CONTBIT OPENABLE)
                (CAPACITY 5)
                (SIZE 10)
                (ACTION CANTEEN-F)>
        """
        if not isinstance(obj_sexp, list) or len(obj_sexp) < 2:
            return None

        # First element should be OBJECT symbol
        if not isinstance(obj_sexp[0], Symbol) or str(obj_sexp[0]).upper() != "OBJECT":
            return None

        name = obj_sexp[1]
        properties = self._parse_properties(obj_sexp[2:])

        # Get flags and determine object type
        flags = self._extract_flags(properties)
        obj_type = self._determine_type(flags, properties)

        obj_data = {
            "id": self._normalize_id(name),
            "zil_name": str(name),
            "name": properties.get("DESC", str(name)),
            "description": properties.get("FDESC", ""),
            "synonyms": self._extract_list(properties.get("SYNONYM", [])),
            "adjectives": self._extract_list(properties.get("ADJECTIVE", [])),
            "initial_location": self._normalize_id(properties.get("IN") or properties.get("LOC")),
            "type": obj_type,
            "flags": flags,
            "capacity": properties.get("CAPACITY"),
            "size": properties.get("SIZE"),
            "text": properties.get("TEXT"),
            "action_routine": properties.get("ACTION"),
            "raw_zil": extract_raw_zil(obj_sexp),
            "_zil_properties": properties
        }

        # Add routine code if action routine is present and we have it
        if obj_data["action_routine"]:
            routine_name = str(obj_data["action_routine"]).upper()
            if routine_name in self.routines:
                obj_data["action_routine_code"] = self.routines[routine_name]["zil_string"]
                obj_data["action_routine_json"] = self.routines[routine_name]["zil_json"]
            else:
                self._add_todo(
                    f"Object {obj_data['id']} has action routine: {obj_data['action_routine']}\n"
                    f"  WARNING: Routine code not found in ZIL files"
                )

        return obj_data

    def _extract_flags(self, props: Dict[str, Any]) -> List[str]:
        """Extract and normalize FLAGS property."""
        flags = props.get("FLAGS", [])
        if isinstance(flags, list):
            return [str(f).upper() for f in flags]
        else:
            return [str(flags).upper()]

    def _extract_list(self, value: Any) -> List[str]:
        """Extract list of strings from ZIL value."""
        if isinstance(value, list):
            return [str(v) for v in value]
        elif value:
            return [str(value)]
        else:
            return []

    def extract_object_as_room(self, obj_sexp: List[Any], room_extractor) -> Dict[str, Any]:
        """Extract an OBJECT form that represents a location (Trinity-style).

        Trinity uses <OBJECT> with (LOC ROOMS) and (FLAGS ... LOCATION ...) for rooms.

        Example:
            <OBJECT PAL-GATE
                (LOC ROOMS)
                (DESC "Palace Gate")
                (FLAGS LIGHTED LOCATION WINDY)
                (NORTH TO BROAD-WALK)
                (ACTION PAL-GATE-F)>
        """
        if not isinstance(obj_sexp, list) or len(obj_sexp) < 2:
            return None

        # Use OBJECT as name since it's the symbol name
        name = obj_sexp[1]
        properties = self._parse_properties(obj_sexp[2:])

        # Use room extractor's methods to process exits and flags
        room_data = {
            "id": self._normalize_id(name),
            "zil_name": str(name),
            "name": properties.get("DESC", str(name)),
            "long_desc": properties.get("LDESC", ""),
            "exits": room_extractor._extract_exits(properties, obj_sexp[2:]),
            "flags": room_extractor._extract_flags(properties),
            "pseudo_objects": properties.get("PSEUDO", []),
            "global_objects": properties.get("GLOBAL", []),
            "action_routine": properties.get("ACTION"),
            "raw_zil": extract_raw_zil(obj_sexp),
            "_zil_properties": properties
        }

        # Add routine code if action routine is present and we have it
        if room_data["action_routine"]:
            routine_name = str(room_data["action_routine"]).upper()
            if routine_name in self.routines:
                room_data["action_routine_code"] = self.routines[routine_name]["zil_string"]
                room_data["action_routine_json"] = self.routines[routine_name]["zil_json"]
            else:
                self._add_todo(
                    f"Room {room_data['id']} has action routine: {room_data['action_routine']}\n"
                    f"  WARNING: Routine code not found in ZIL files"
                )

        # Handle pseudo objects if present
        if room_data["pseudo_objects"]:
            pseudo_routines = {}
            pseudo_list = room_data["pseudo_objects"]

            # Process in pairs: (name, routine_ref)
            for i in range(0, len(pseudo_list), 2):
                if i + 1 < len(pseudo_list):
                    pseudo_name = str(pseudo_list[i])
                    routine_ref = pseudo_list[i + 1]
                    routine_name = str(routine_ref).upper()

                    if routine_name in self.routines:
                        pseudo_routines[pseudo_name] = {
                            "routine_name": routine_name,
                            "zil_string": self.routines[routine_name]["zil_string"],
                            "zil_json": self.routines[routine_name]["zil_json"]
                        }

            room_data["pseudo_object_routines"] = pseudo_routines

        return room_data

    def _determine_type(self, flags: List[str], props: Dict[str, Any]) -> str:
        """Infer object type from ZIL flags and properties.

        Common ZIL flags:
            WEAPONBIT, TOOLBIT - weapons/tools
            DOORBIT - doors
            CONTBIT - containers
            READBIT - readable items
            LIGHTBIT - light sources
            FOODBIT, DRINKBIT - consumables
            TREASUREBIT - treasure/collectibles
            ACTORBIT - NPCs (handled separately)
            TAKEBIT - takeable items
        """
        # NPCs
        if "ACTORBIT" in flags:
            return "npc"

        # Weapons and tools
        if "WEAPONBIT" in flags or "TOOLBIT" in flags:
            return "weapon"

        # Doors
        if "DOORBIT" in flags:
            return "entrance"

        # Containers
        if "CONTBIT" in flags or "CONTAINER" in flags:
            return "container"

        # Readable items
        if "READBIT" in flags or props.get("TEXT"):
            return "readable"

        # Light sources
        if "LIGHTBIT" in flags:
            return "light_source"

        # Consumables
        if "FOODBIT" in flags or "DRINKBIT" in flags:
            return "consumable"

        # Treasure
        if "TREASUREBIT" in flags:
            return "treasure"

        # Default to generic
        return "generic"


class NPCExtractor(ZILExtractor):
    """Extract NPC data from ZIL OBJECT forms with ACTORBIT flag."""

    def extract_npc(self, obj_sexp: List[Any]) -> Optional[Dict[str, Any]]:
        """Extract NPC from OBJECT with ACTORBIT flag.

        NPCs in ZIL are objects with ACTORBIT flag.

        Example:
            <OBJECT FLOYD
                (LOC DECK-NINE)
                (DESC "Floyd")
                (FDESC "cheerful robot companion")
                (FLAGS ACTORBIT PERSON)
                (ACTION FLOYD-F)>
        """
        if not isinstance(obj_sexp, list) or len(obj_sexp) < 2:
            return None

        if not isinstance(obj_sexp[0], Symbol) or str(obj_sexp[0]).upper() != "OBJECT":
            return None

        name = obj_sexp[1]
        properties = self._parse_properties(obj_sexp[2:])
        flags = self._extract_flags(properties)

        # Check if this is an NPC (multiple flag patterns supported)
        if not self._is_npc(flags):
            return None

        npc_data = {
            "id": self._normalize_id(name),
            "zil_name": str(name),
            "name": properties.get("DESC", str(name)),
            "description": properties.get("FDESC", ""),
            "initial_location": self._normalize_id(properties.get("IN") or properties.get("LOC")),
            "flags": flags,
            "hostility": self._infer_hostility(flags, properties),
            "action_routine": properties.get("ACTION"),
            "raw_zil": extract_raw_zil(obj_sexp),
            "_zil_properties": properties
        }

        # Add routine code if action routine is present and we have it
        if npc_data["action_routine"]:
            routine_name = str(npc_data["action_routine"]).upper()
            if routine_name in self.routines:
                npc_data["action_routine_code"] = self.routines[routine_name]["zil_string"]
                npc_data["action_routine_json"] = self.routines[routine_name]["zil_json"]
            else:
                self._add_todo(
                    f"NPC {npc_data['id']} has action routine: {npc_data['action_routine']}\n"
                    f"  WARNING: Routine code not found in ZIL files"
                )

        return npc_data

    def _extract_flags(self, props: Dict[str, Any]) -> List[str]:
        """Extract and normalize FLAGS property."""
        flags = props.get("FLAGS", [])
        if isinstance(flags, list):
            return [str(f).upper() for f in flags]
        else:
            return [str(flags).upper()]

    def _infer_hostility(self, flags: List[str], props: Dict[str, Any]) -> str:
        """Infer NPC hostility from flags.

        Common patterns:
            - VILLAINBIT: hostile
            - PERSON + no VILLAINBIT: neutral/friendly
        """
        if "VILLAINBIT" in flags:
            return "hostile"
        elif "PERSON" in flags:
            return "neutral"
        else:
            return "unknown"

    def _is_npc(self, flags: List[str]) -> bool:
        """Detect NPCs using multiple flag patterns.

        Different Infocom games use different conventions:
        - Planetfall: ACTORBIT (modern)
        - Zork/Trinity: PERSON + LIVING (classic)
        """
        # Pattern 1: Modern (Planetfall)
        if "ACTORBIT" in flags:
            return True

        # Pattern 2: Classic (Zork, Trinity)
        # Requires BOTH flags to avoid false positives
        if "PERSON" in flags and "LIVING" in flags:
            return True

        return False


class GameExtractor:
    """Main extractor that coordinates room, object, and NPC extraction."""

    def __init__(self):
        self.room_extractor = RoomExtractor()
        self.object_extractor = ObjectExtractor()
        self.npc_extractor = NPCExtractor()

    def _extract_routines(self, sexps: List[Any]) -> Dict[str, Dict]:
        """Extract all ROUTINE definitions and build name -> code map.

        Args:
            sexps: Parsed S-expressions

        Returns:
            Dict mapping routine names to their ZIL code (both string and JSON)
        """
        from .zil_to_json import format_routine_as_json

        routines = {}
        for sexp in sexps:
            if not isinstance(sexp, list) or len(sexp) < 2:
                continue

            form_type = str(sexp[0]).upper() if isinstance(sexp[0], Symbol) else ""

            if form_type == "ROUTINE":
                # Format: (ROUTINE NAME (...) ...)
                if len(sexp) >= 2:
                    routine_name = str(sexp[1]).upper() if isinstance(sexp[1], Symbol) else str(sexp[1])
                    # Store both string format (for debugging) and JSON (for LLM)
                    routines[routine_name] = {
                        "zil_string": extract_raw_zil(sexp),
                        "zil_json": format_routine_as_json(sexp)
                    }

        return routines

    def extract(self, sexps: List[Any]) -> Dict[str, Any]:
        """Extract all game entities from parsed S-expressions.

        Returns:
            Dictionary with rooms, objects, npcs, and todos
        """
        # First pass: extract all routine definitions
        routines = self._extract_routines(sexps)

        # Pass routines to extractors so they can include function code
        self.room_extractor.routines = routines
        self.object_extractor.routines = routines
        self.npc_extractor.routines = routines

        rooms = []
        objects = []
        npcs = []

        for sexp in sexps:
            if not isinstance(sexp, list) or len(sexp) < 2:
                continue

            form_type = str(sexp[0]).upper() if isinstance(sexp[0], Symbol) else ""

            if form_type == "ROOM":
                room = self.room_extractor.extract_room(sexp)
                if room:
                    rooms.append(room)

            elif form_type == "OBJECT":
                # Check if this is actually a location (Trinity-style)
                # Trinity uses <OBJECT> with (LOC ROOMS) and (FLAGS ... LOCATION ...)
                is_location = False
                if len(sexp) >= 3:
                    props = self.room_extractor._parse_properties(sexp[2:])
                    loc = props.get("LOC")
                    flags = props.get("FLAGS", [])

                    # Check if this is a room/location
                    # Handle both Symbol and string for LOC value
                    loc_str = str(loc).upper() if loc else ""
                    has_loc_rooms = loc_str == "ROOMS"

                    # Check FLAGS for LOCATION
                    has_location_flag = any(
                        str(f).upper() == "LOCATION"
                        for f in (flags if isinstance(flags, list) else [flags] if flags else [])
                    )

                    is_location = has_loc_rooms or has_location_flag

                if is_location:
                    # Extract as room (Trinity-style location)
                    room = self.object_extractor.extract_object_as_room(sexp, self.room_extractor)
                    if room:
                        rooms.append(room)
                else:
                    # Try NPC extraction first
                    npc = self.npc_extractor.extract_npc(sexp)
                    if npc:
                        npcs.append(npc)
                    else:
                        # Regular object
                        obj = self.object_extractor.extract_object(sexp)
                        if obj:
                            objects.append(obj)

        # Collect all TODOs
        all_todos = (
            self.room_extractor.get_todos() +
            self.object_extractor.get_todos() +
            self.npc_extractor.get_todos()
        )

        # Identify global routines (routines not attached to any entity)
        used_routines = set()
        for room in rooms:
            if room.get("action_routine"):
                used_routines.add(room["action_routine"])
            if room.get("pseudo_object_routines"):
                used_routines.update(room["pseudo_object_routines"].keys())
        for obj in objects:
            if obj.get("action_routine"):
                used_routines.add(obj["action_routine"])
        for npc in npcs:
            if npc.get("action_routine"):
                used_routines.add(npc["action_routine"])

        # Global routines are those not used by any entity
        global_routines = {
            name: data for name, data in routines.items()
            if name not in used_routines
        }

        return {
            "rooms": rooms,
            "objects": objects,
            "npcs": npcs,
            "todos": all_todos,
            "global_routines": global_routines  # Add global routines to output
        }
