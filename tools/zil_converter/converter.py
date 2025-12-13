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

        # Note: All ZIL data now in structured JSON format (no raw_zil string)

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

        # Preserve ACTION routine name and code for LLM context
        if room_data.get("action_routine"):
            custom["zil_action"] = str(room_data["action_routine"])
            # Include actual ZIL code if available (both string and JSON)
            if room_data.get("action_routine_code"):
                custom["zil_action_code"] = room_data["action_routine_code"]
            if room_data.get("action_routine_json"):
                custom["zil_action_json"] = room_data["action_routine_json"]

        # Preserve pseudo object routines for scenery/pseudo items
        if room_data.get("pseudo_object_routines"):
            custom["zil_pseudo_routines"] = room_data["pseudo_object_routines"]

        return custom

    def _convert_exits(self, zil_exits: Dict[str, Any], room_id: str) -> Dict[str, str]:
        """Convert ZIL exits to JSON connections.

        For now, only handle direct exits. Conditional/blocked exits not included.
        """
        connections = {}

        for direction, exit_def in zil_exits.items():
            if exit_def["type"] == "direct":
                # Simple exit: just add connection
                connections[direction] = exit_def["destination"]
            elif exit_def["type"] == "blocked":
                # Blocked exit with message - skip it (not implemented yet)
                pass
            else:
                # Conditional exit: add TODO and skip
                condition = exit_def.get("condition", "unknown")
                self.todos.append(
                    f"Conditional exit in {room_id}: {direction} -> "
                    f"condition={condition}\n"
                    f"  Needs implementation"
                )
                # Don't add the connection

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

        # Note: All ZIL data now in structured JSON format (no raw_zil string)

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

        # Preserve ACTION routine name and code for LLM context
        if obj_data.get("action_routine"):
            attrs["zil_action"] = str(obj_data["action_routine"])
            # Include actual ZIL code if available (both string and JSON)
            if obj_data.get("action_routine_code"):
                attrs["zil_action_code"] = obj_data["action_routine_code"]
            if obj_data.get("action_routine_json"):
                attrs["zil_action_json"] = obj_data["action_routine_json"]

        return attrs

    def _convert_type_specific(self, obj_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert type-specific ZIL properties to JSON attributes."""
        attrs = {}
        flags = obj_data.get("flags", [])

        # Visibility - CRITICAL for gameplay
        # INVISIBLE flag means hidden until revealed (e.g., trap door under carpet)
        if "INVISIBLE" in flags:
            attrs["is_visible"] = False
        else:
            attrs["is_visible"] = True

        # Auto-description control
        # NDESCBIT means "no description bit" - item exists but shouldn't be auto-described
        # (e.g., table with ndescbit - don't describe table, just show contents)
        if "NDESCBIT" in flags:
            attrs["auto_describe"] = False
        else:
            attrs["auto_describe"] = True

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

        # Note: All ZIL data now in structured JSON format (no raw_zil string)

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
            # Include actual ZIL code if available (both string and JSON)
            if npc_data.get("action_routine_code"):
                attrs["zil_action_code"] = npc_data["action_routine_code"]
            if npc_data.get("action_routine_json"):
                attrs["zil_action_json"] = npc_data["action_routine_json"]
            if not npc_data.get("action_routine_code"):
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

        # First pass: Find player/adventurer item and build ALL item_locations
        player_item_id = None
        player_start_location = None
        item_locations = {}

        for obj in game_data["objects"]:
            item = self.item_converter.convert_object(obj)

            # Check if this is the player character item
            # Common indicators: name="player", INVISIBLE flag, specific IDs
            is_player_item = (
                item["name"].lower() in ["player", "adventurer"] or
                item["id"] in ["adventurer", "player", "me"]
            )

            if is_player_item:
                player_item_id = item["id"]
                player_start_location = obj.get("initial_location")
                # Don't track player item location in item_locations
            else:
                # Track initial location for all non-player items
                if obj.get("initial_location"):
                    item_locations[item["id"]] = obj.get("initial_location")

        # Second pass: Extract player inventory (items inside player/adventurer)
        initial_inventory = []
        if player_item_id:
            initial_inventory = [
                item_id for item_id, loc in item_locations.items()
                if loc == player_item_id
            ]
            # Remove these from item_locations since they're in inventory
            for item_id in initial_inventory:
                del item_locations[item_id]

        # Third pass: Build items dict (excluding player item)
        items = {}
        for obj in game_data["objects"]:
            item = self.item_converter.convert_object(obj)
            # Skip the player item itself
            if item["id"] == player_item_id:
                continue
            items[item["id"]] = item

        # Build NPCs
        npcs = {}
        npc_locations = {}
        for npc_data in game_data["npcs"]:
            npc = self.npc_converter.convert_npc(npc_data)
            npcs[npc["id"]] = npc

            # Track initial location
            if npc_data.get("initial_location"):
                npc_locations[npc["id"]] = npc_data["initial_location"]

        # Determine player start location
        if player_start_location:
            player_location = player_start_location
        else:
            # Fallback to heuristics
            player_location = self._find_start_location(game_data["rooms"])

        # Build complete world
        world = {
            "locations": locations,
            "items": items,
            "npcs": npcs,
            "item_locations": item_locations,
            "npc_locations": npc_locations,
            "player_location": player_location,
            "player_inventory": initial_inventory,  # Add initial inventory
            "flags": {},
            "puzzles": {},
            "world_context": self._generate_world_context(game_data, locations, items, npcs)
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

    def _generate_world_context(
        self,
        game_data: Dict[str, Any],
        locations: Dict[str, Any],
        items: Dict[str, Any],
        npcs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate world_context metadata for the game.

        Detects the game (Zork, Planetfall, etc.) and provides appropriate
        setting, tone, and DM instructions for immersive gameplay.
        """
        # Detect which game this is
        game_type = self._detect_game_type(locations, items, npcs)

        if game_type == "planetfall":
            return {
                "title": "Planetfall",
                "author": "Steve Meretzky / Infocom (1983)",
                "intro": "Another routine day of drudgery aboard the Stellar Patrol Ship Feinstein. This morning's assignment for a certain lowly Ensign Seventh Class: scrubbing the filthy metal deck at the port end of Level Nine. With your Patrol-issue self-contained multi-purpose all-weather scrub brush you shine the floor with a diligence born of the knowledge that at any moment dreaded Ensign First Class Blather, the bane of your shipboard existence, could appear.",
                "setting": "You are an Ensign Seventh Class aboard the starship Feinstein. The game begins with routine ship maintenance, but quickly turns into a desperate survival story on an abandoned alien planet. The planet appears to be the remains of an advanced civilization, with a sprawling research complex, strange technology, and signs of a catastrophic plague. Your only companion is Floyd, a childlike maintenance robot. Your goal is to explore the facility, uncover what happened, survive the dangers, and find a way off this dying world.",
                "tone": "Science fiction adventure with moments of humor (especially with Floyd) contrasted with darker themes of abandonment, plague, and survival. Mix wonder at alien technology with creeping dread about what happened here.",
                "dm_instructions": [
                    "This is a classic Infocom sci-fi adventure. Maintain the retro-futuristic aesthetic of 1980s space opera.",
                    "Floyd the robot is a key character - childlike, loyal, playful, but also capable and brave. He should be endearing.",
                    "The world should feel abandoned and eerie. This was once a thriving research complex, now silent and decaying.",
                    "Technology is advanced but alien - describe it with wonder and mystery, not modern tech terminology.",
                    "The plague storyline is tragic - handle it with appropriate gravity when revealed.",
                    "Time pressure exists (days are counting up, tide is rising) but don't rush the player artificially.",
                    "Puzzles involve repairing technology, understanding alien systems, and using tools creatively.",
                    "The game has a famous emotional climax - if reached, handle it with genuine pathos.",
                    "The chronometer displays turn count as time (e.g., 'current time is 4538' means 4538 turns have passed)."
                ],
                "initial_inventory": [
                    "scrub_brush",
                    "patrol_uniform",
                    "id_card",
                    "chronometer"
                ]
            }
        elif game_type == "zork":
            return {
                "title": "Zork I: The Great Underground Empire",
                "author": "Marc Blank and Dave Lebling / Infocom (1980)",
                "setting": "You are a nameless adventurer standing near a white house in a small clearing. A path leads into the forest to the east. Nearby is a small mailbox. This is the entrance to the Great Underground Empire, a vast subterranean realm filled with treasures, puzzles, and deadly dangers. Your goal is to explore the ancient ruins, solve its mysteries, collect the Twenty Treasures of Zork, and survive the perils that lurk in the darkness.",
                "tone": "Classic text adventure with a mix of whimsy, danger, and archaeological mystery. Maintain the iconic Infocom humor ('You are likely to be eaten by a grue') while treating the underground realm with genuine wonder and threat.",
                "dm_instructions": [
                    "This is the original Zork - the quintessential text adventure. Honor its classic status with vivid descriptions.",
                    "The Great Underground Empire should feel ancient, mysterious, and vast. Emphasize the archaeological wonder.",
                    "Puzzles are logical but often require lateral thinking or finding the right tool/item.",
                    "Treasures are the primary goal - each should feel valuable and unique when discovered.",
                    "The Thief is a recurring antagonist who steals treasures - make him cunning and frustrating.",
                    "Grues are deadly in the dark - enforce light management strictly but give fair warning.",
                    "The tone balances humor with genuine danger - deaths are often darkly funny but still consequential.",
                    "Many items have specific, non-obvious uses. Reward experimentation and creative thinking."
                ]
            }
        else:
            # Generic Infocom-style game
            return {
                "title": "Interactive Fiction Adventure",
                "author": "Infocom",
                "setting": "A classic text adventure world filled with puzzles, treasures, and mysteries to uncover.",
                "tone": "Classic Infocom-style interactive fiction with clever puzzles and immersive storytelling.",
                "dm_instructions": [
                    "This is a classic text adventure. Describe the world vividly and maintain consistency.",
                    "Puzzles should be logical and fair. Give subtle hints when players are stuck.",
                    "Respect the player's agency - they control their character's actions.",
                    "Maintain the vintage text adventure aesthetic while being descriptive and engaging."
                ]
            }

    def _detect_game_type(
        self,
        locations: Dict[str, Any],
        items: Dict[str, Any],
        npcs: Dict[str, Any]
    ) -> str:
        """Detect which game this is based on locations, items, and NPCs.

        Returns:
            "planetfall", "zork", or "unknown"
        """
        # Check for Planetfall-specific entities
        planetfall_indicators = [
            "escape_pod", "balcony", "floyd", "robot", "bio_lab",
            "radiation_lab", "computer_room", "crag"
        ]
        if any(key in locations or key in items or key in npcs for key in planetfall_indicators):
            return "planetfall"

        # Check for Zork-specific entities
        zork_indicators = [
            "west_of_house", "kitchen", "living_room", "white_house",
            "troll", "cyclops", "thief", "grue"
        ]
        if any(key in locations or key in items or key in npcs for key in zork_indicators):
            return "zork"

        return "unknown"
