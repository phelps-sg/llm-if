"""ZIL pattern matcher for smart puzzle conversion.

Recognizes common ZIL patterns and converts them to our puzzle system.
"""

from typing import Dict, Any, List, Optional


class PuzzleMatcher:
    """Match ZIL patterns and generate puzzles."""

    def __init__(self, rooms: List[Dict], objects: List[Dict]):
        """Initialize with extracted game data.

        Args:
            rooms: List of extracted room data
            objects: List of extracted object data
        """
        self.rooms = {r["id"]: r for r in rooms}
        self.objects = {o["id"]: o for o in objects}
        self.puzzles = []
        self.todos = []

    def find_all_puzzles(self) -> List[Dict[str, Any]]:
        """Find and convert all recognizable puzzle patterns.

        Returns:
            List of puzzle definitions
        """
        # Check each room for puzzle patterns
        for room_id, room_data in self.rooms.items():
            # Check for locked door patterns
            for direction, exit_def in room_data.get("exits", {}).items():
                if exit_def["type"] == "conditional":
                    puzzle = self.match_locked_door(room_data, direction, exit_def)
                    if puzzle:
                        self.puzzles.append(puzzle)

        return self.puzzles

    def match_locked_door(
        self,
        room_data: Dict[str, Any],
        exit_dir: str,
        exit_def: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect locked door pattern and create puzzle.

        Pattern: Room with conditional exit + DOORBIT object with LOCKEDBIT

        Example ZIL:
            <ROOM HALL
                (DOWN PER DOOR-LOCKED-F)>
            <OBJECT TRAPDOOR
                (LOC HALL)
                (FLAGS DOORBIT LOCKEDBIT)>

        Args:
            room_data: Room with conditional exit
            exit_dir: Direction of exit (e.g., "down")
            exit_def: Exit definition with condition

        Returns:
            Puzzle definition or None if pattern doesn't match
        """
        condition_fn = exit_def.get("condition", "")

        # Look for door objects in this room or as global objects
        door_candidates = self._find_doors_in_room(room_data)

        for door_obj in door_candidates:
            flags = door_obj.get("flags", [])

            # Check if this is a locked door
            if "DOORBIT" in flags and "LOCKEDBIT" in flags:
                # Try to find the key
                key_id = self._find_key_for_door(door_obj, condition_fn)

                # Create puzzle
                puzzle = {
                    "id": f"{room_data['id']}_{exit_dir}_locked",
                    "type": "locked_exit",
                    "location": room_data["id"],
                    "exit_direction": exit_dir,
                    "description": f"The {door_obj['name']} blocks the way {exit_dir}",
                    "requirements": {
                        "type": "any_of",
                        "solutions": []
                    }
                }

                # Add key solution if we found one
                if key_id and key_id != "UNKNOWN_KEY":
                    puzzle["requirements"]["solutions"].append({
                        "type": "item_in_inventory",
                        "item_id": key_id,
                        "success_message": f"You unlock the {door_obj['name']}",
                        "action_verbs": ["unlock", "open"]
                    })
                else:
                    # Add TODO for manual key identification
                    self.todos.append(
                        f"Puzzle {puzzle['id']}: Could not identify key automatically\n"
                        f"  Review ZIL routine {condition_fn} to find which item unlocks the door\n"
                        f"  Add solution to puzzle requirements"
                    )

                return puzzle

        return None

    def _find_doors_in_room(self, room_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all door objects in a room.

        Checks both:
        - Objects with initial_location set to this room
        - Global objects referenced by the room
        """
        doors = []
        room_id = room_data["id"]

        # Check objects located in this room
        for obj_id, obj_data in self.objects.items():
            if obj_data.get("initial_location") == room_id:
                if "DOORBIT" in obj_data.get("flags", []):
                    doors.append(obj_data)

        # Check global objects
        for global_obj_name in room_data.get("global_objects", []):
            global_obj_id = str(global_obj_name).lower().replace("-", "_")
            if global_obj_id in self.objects:
                obj_data = self.objects[global_obj_id]
                if "DOORBIT" in obj_data.get("flags", []):
                    doors.append(obj_data)

        return doors

    def _find_key_for_door(self, door_obj: Dict[str, Any], condition_fn: str) -> str:
        """Try to infer which item unlocks this door.

        This is complex because it requires parsing ZIL routines.
        For now, use heuristics:
        1. Look for objects with "KEY" in name/synonyms
        2. Look for objects with similar names to the door
        3. Return UNKNOWN_KEY if can't determine

        Args:
            door_obj: The door object
            condition_fn: The ZIL routine name that checks the lock

        Returns:
            Key item ID or "UNKNOWN_KEY"
        """
        # Heuristic 1: Look for objects with "KEY" in name
        for obj_id, obj_data in self.objects.items():
            obj_name = obj_data.get("name", "").upper()
            synonyms = [s.upper() for s in obj_data.get("synonyms", [])]

            if "KEY" in obj_name or "KEY" in synonyms:
                # Check if key name relates to door name
                door_name_parts = door_obj.get("zil_name", "").upper().split("-")
                key_name_parts = obj_data.get("zil_name", "").upper().split("-")

                # If they share a word, probably related
                if set(door_name_parts) & set(key_name_parts):
                    return obj_id

        # Heuristic 2: Look for "CARD", "PASS", "TOKEN" items
        for obj_id, obj_data in self.objects.items():
            obj_name = obj_data.get("name", "").upper()
            synonyms = [s.upper() for s in obj_data.get("synonyms", [])]

            for key_word in ["CARD", "PASS", "TOKEN", "BADGE"]:
                if key_word in obj_name or key_word in synonyms:
                    return obj_id

        # Could not determine - needs manual review
        return "UNKNOWN_KEY"

    def match_container_puzzle(self, obj_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect container puzzle pattern.

        Pattern: Container with CONTBIT + LOCKEDBIT requires key to open

        This is a simpler pattern that could be auto-converted.
        """
        flags = obj_data.get("flags", [])

        if "CONTBIT" in flags and "LOCKEDBIT" in flags:
            # Create puzzle for opening the container
            puzzle = {
                "id": f"{obj_data['id']}_locked_container",
                "type": "locked_container",
                "item_id": obj_data["id"],
                "description": f"The {obj_data['name']} is locked",
                "requirements": {
                    "type": "any_of",
                    "solutions": []
                }
            }

            # Try to find key
            # For now, add TODO
            self.todos.append(
                f"Locked container {obj_data['id']} needs key identification\n"
                f"  Add solution to puzzle requirements"
            )

            return puzzle

        return None

    def get_todos(self) -> List[str]:
        """Get all TODO notes from pattern matching."""
        return self.todos


class SmartConverter:
    """Coordinates smart pattern matching and puzzle generation."""

    def __init__(self):
        self.matcher = None

    def apply_smart_conversions(
        self,
        game_data: Dict[str, Any],
        world_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply smart pattern matching to enhance world JSON.

        Args:
            game_data: Extracted ZIL data (rooms, objects, NPCs)
            world_json: Basic converted world JSON

        Returns:
            Enhanced world JSON with puzzles added
        """
        # Initialize pattern matcher
        self.matcher = PuzzleMatcher(
            game_data["rooms"],
            game_data["objects"]
        )

        # Find all puzzles
        puzzles = self.matcher.find_all_puzzles()

        # Add puzzles to world
        if puzzles:
            world_json["puzzles"] = {}
            for puzzle in puzzles:
                world_json["puzzles"][puzzle["id"]] = puzzle

        return world_json

    def get_todos(self) -> List[str]:
        """Get all TODO notes from smart conversion."""
        if self.matcher:
            return self.matcher.get_todos()
        return []
