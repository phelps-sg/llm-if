"""ZIL entity extractor.

Extracts game entities (rooms, objects, NPCs) from parsed ZIL S-expressions
into intermediate Python data structures.
"""

from typing import List, Any, Dict, Optional
from sexpdata import Symbol


class ZILExtractor:
    """Base extractor with common utilities."""

    def __init__(self):
        self.todos = []  # Track items needing manual review

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
            "exits": self._extract_exits(properties),
            "flags": self._extract_flags(properties),
            "pseudo_objects": properties.get("PSEUDO", []),
            "global_objects": properties.get("GLOBAL", []),
            "action_routine": properties.get("ACTION"),
            "_zil_properties": properties
        }

        # Add TODO if room has action routine
        if room_data["action_routine"]:
            self._add_todo(
                f"Room {room_data['id']} has action routine: {room_data['action_routine']}\n"
                f"  Review ZIL routine for special room behavior"
            )

        return room_data

    def _extract_exits(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Extract room connections from direction properties.

        ZIL directions: NORTH, SOUTH, EAST, WEST, NE, NW, SE, SW, UP, DOWN, IN, OUT

        Exit types:
            (NORTH TO OTHER-ROOM)       - Direct exit
            (DOWN PER DOOR-LOCKED-F)    - Conditional exit (function check)
            (EAST IF FLAG-NAME)         - Conditional exit (flag check)
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

                # Handle different exit formats
                if isinstance(exit_def, list) and len(exit_def) >= 2:
                    exit_type = str(exit_def[0]).upper() if isinstance(exit_def[0], Symbol) else str(exit_def[0])

                    if exit_type == "TO":
                        # Direct exit
                        exits[direction.lower()] = {
                            "type": "direct",
                            "destination": self._normalize_id(exit_def[1])
                        }
                    elif exit_type in ["PER", "IF"]:
                        # Conditional exit
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
            "_zil_properties": properties
        }

        # Add TODO if object has custom action
        if obj_data["action_routine"]:
            self._add_todo(
                f"Object {obj_data['id']} has action routine: {obj_data['action_routine']}\n"
                f"  Review ZIL routine for special object behavior"
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
        if "CONTBIT" in flags:
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

        # Check if this is an NPC (has ACTORBIT)
        if "ACTORBIT" not in flags:
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
            "_zil_properties": properties
        }

        # NPCs always need manual review for behavior
        self._add_todo(
            f"NPC {npc_data['id']} has action routine: {npc_data['action_routine']}\n"
            f"  Review ZIL routine to understand NPC behavior, dialogue, and AI"
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


class GameExtractor:
    """Main extractor that coordinates room, object, and NPC extraction."""

    def __init__(self):
        self.room_extractor = RoomExtractor()
        self.object_extractor = ObjectExtractor()
        self.npc_extractor = NPCExtractor()

    def extract(self, sexps: List[Any]) -> Dict[str, Any]:
        """Extract all game entities from parsed S-expressions.

        Returns:
            Dictionary with rooms, objects, npcs, and todos
        """
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

        return {
            "rooms": rooms,
            "objects": objects,
            "npcs": npcs,
            "todos": all_todos
        }
