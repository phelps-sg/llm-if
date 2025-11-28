"""GameState model - central state container for the game."""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field

from .location import Location
from .npc import NPC
from .item import Item
from .player import Player


class GameState(BaseModel):
    """Central game state container.

    Maintains all game entities and their relationships.
    Uses separate maps to track entity locations.
    """

    # Core entities
    locations: Dict[str, Location] = Field(
        default_factory=dict, description="Map of location ID to Location object"
    )
    npcs: Dict[str, NPC] = Field(
        default_factory=dict, description="Map of NPC ID to NPC object"
    )
    items: Dict[str, Item] = Field(
        default_factory=dict, description="Map of item ID to Item object"
    )
    player: Player = Field(default_factory=Player, description="Player character state")

    # Location tracking maps
    npc_locations: Dict[str, str] = Field(
        default_factory=dict, description="Map of NPC ID to location ID"
    )
    item_locations: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of item ID to location ID (excludes carried items)",
    )
    player_location: str = Field(
        default="start", description="Current player location ID"
    )

    # Game metadata
    turn_count: int = Field(default=0, description="Current turn number")
    game_time: str = Field(
        default="Day 1, Morning, 8:00 AM",
        description="Current in-game date and time (natural language format controlled by DM)"
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of actions and events"
    )
    flags: Dict[str, Any] = Field(
        default_factory=dict, description="Global game flags and state"
    )

    # Plot system (optional - for DM-controlled plots)
    plot_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Plot configuration with natural language description for LLM"
    )
    dm_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hidden DM state for plot tracking (not shown to player)"
    )

    # Rogue-like mode configuration
    rogue_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for rogue-like procedural generation mode"
    )

    # Description caching for consistency
    description_cache: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Cache of previously generated descriptions for locations, NPCs, and items"
    )

    # Query methods for locations

    def get_items_at_location(self, location_id: str) -> List[Item]:
        """Get all items at a specific location."""
        return [
            self.items[item_id]
            for item_id, loc_id in self.item_locations.items()
            if loc_id == location_id
        ]

    def get_npcs_at_location(self, location_id: str) -> List[NPC]:
        """Get all NPCs at a specific location."""
        return [
            self.npcs[npc_id]
            for npc_id, loc_id in self.npc_locations.items()
            if loc_id == location_id
        ]

    def get_player_location(self) -> Optional[Location]:
        """Get the player's current location object."""
        return self.locations.get(self.player_location)

    # Mutation methods for items

    def move_item_to_location(self, item_id: str, location_id: str) -> None:
        """Move an item to a location (from inventory or another location)."""
        # Remove from player inventory if present
        self.player.remove_item(item_id)

        # Remove from NPC inventories if present
        for npc in self.npcs.values():
            if hasattr(npc, "inventory") and item_id in getattr(npc, "inventory", []):
                if hasattr(npc, "remove_item"):
                    npc.remove_item(item_id)

        # Set location
        self.item_locations[item_id] = location_id

    def move_item_to_player(self, item_id: str) -> None:
        """Move an item to player inventory."""
        # Remove from location map
        if item_id in self.item_locations:
            del self.item_locations[item_id]

        # Add to player inventory
        self.player.add_item(item_id)

    def move_item_to_npc(self, item_id: str, npc_id: str) -> None:
        """Move an item to NPC inventory."""
        # Remove from location map
        if item_id in self.item_locations:
            del self.item_locations[item_id]

        # Remove from player inventory
        self.player.remove_item(item_id)

        # Add to NPC (if NPC has inventory support)
        npc = self.npcs.get(npc_id)
        if npc and hasattr(npc, "add_item"):
            npc.add_item(item_id)

    # Mutation methods for NPCs

    def move_npc_to_location(self, npc_id: str, location_id: str) -> None:
        """Move an NPC to a location."""
        self.npc_locations[npc_id] = location_id

    # Mutation methods for player

    def move_player_to_location(self, location_id: str) -> bool:
        """Move player to a location. Returns True if successful."""
        if location_id in self.locations:
            self.player_location = location_id
            return True
        return False

    # Time and lighting system

    def get_time_of_day(self) -> str:
        """Get current time of day based on turn count.

        Cycles through: dawn, morning, day, afternoon, dusk, evening, night, midnight
        Each period lasts ~5 turns. Full day/night cycle = 40 turns.
        """
        time_period = (self.turn_count % 40) // 5
        times = [
            "dawn",
            "morning",
            "day",
            "afternoon",
            "dusk",
            "evening",
            "night",
            "midnight",
        ]
        return times[time_period]

    def is_daytime(self) -> bool:
        """Check if it's currently daytime (affects outdoor lighting)."""
        time = self.get_time_of_day()
        return time in ["morning", "day", "afternoon"]

    def get_ambient_light_level(self) -> str:
        """Get ambient light level based on time of day.

        Returns: "bright", "dim", "dark"
        """
        time = self.get_time_of_day()
        if time in ["morning", "day", "afternoon"]:
            return "bright"
        elif time in ["dawn", "dusk", "evening"]:
            return "dim"
        else:  # night, midnight
            return "dark"

    def get_effective_lighting(self, location_id: str) -> Dict[str, Any]:
        """Calculate effective lighting at a location considering time and light sources.

        Returns dictionary with:
        - level: "bright", "dim", "dark", "pitch_black"
        - natural: natural light level (from location/time)
        - artificial: light from items in inventory
        - can_see_clearly: boolean
        - description: text description of lighting
        """
        location = self.locations.get(location_id)
        if not location:
            return {"level": "dark", "can_see_clearly": False}

        # Get base lighting from location
        base_lighting = location.attributes.get("lighting", "dark")
        is_outdoors = location.attributes.get("is_outdoors", False)
        has_windows = location.attributes.get("has_windows", False)

        # Determine natural light
        natural_light = "dark"
        if is_outdoors:
            natural_light = self.get_ambient_light_level()
        elif has_windows:
            ambient = self.get_ambient_light_level()
            # Windows provide some light during day, none at night
            if ambient == "bright":
                natural_light = "dim"
            elif ambient == "dim":
                natural_light = "dark"
        else:
            # Indoor with no windows - use location's base lighting
            natural_light = base_lighting

        # Check for light sources in player inventory AND at current location
        artificial_light = "none"
        light_sources = []

        # Check inventory
        for item_id in self.player.inventory:
            item = self.items.get(item_id)
            if item and item.attributes.get("provides_light", False):
                light_level = item.attributes.get("light_level", "dim")
                light_sources.append(f"{item.name} (carried)")
                # Take the brightest light source
                if light_level == "bright":
                    artificial_light = "bright"
                elif light_level == "dim" and artificial_light != "bright":
                    artificial_light = "dim"

        # Check items at current location
        for item_id, loc_id in self.item_locations.items():
            if loc_id == location_id:
                item = self.items.get(item_id)
                if item and item.attributes.get("provides_light", False):
                    light_level = item.attributes.get("light_level", "dim")
                    light_sources.append(f"{item.name} (here)")
                    # Take the brightest light source
                    if light_level == "bright":
                        artificial_light = "bright"
                    elif light_level == "dim" and artificial_light != "bright":
                        artificial_light = "dim"

        # Combine natural and artificial light
        light_levels = {"pitch_black": 0, "dark": 1, "dim": 2, "bright": 3}

        natural_value = light_levels.get(natural_light, 0)
        artificial_value = light_levels.get(artificial_light, 0)

        # Take the maximum of natural and artificial
        effective_value = max(natural_value, artificial_value)

        # Convert back to level name
        level_names = {0: "pitch_black", 1: "dark", 2: "dim", 3: "bright"}
        effective_level = level_names.get(effective_value, "dark")

        # Generate description
        descriptions = {
            "bright": "The area is well-lit and you can see clearly.",
            "dim": "The lighting is dim, but you can make out shapes and details.",
            "dark": "It's quite dark. You can barely see your surroundings.",
            "pitch_black": "It's pitch black. You can't see anything at all.",
        }

        return {
            "level": effective_level,
            "natural": natural_light,
            "artificial": artificial_light,
            "light_sources": light_sources,
            "can_see_clearly": effective_value >= 2,  # dim or better
            "description": descriptions.get(effective_level, ""),
            "time_of_day": self.get_time_of_day(),
            "is_outdoors": is_outdoors,
        }

    # History tracking

    def add_history_entry(self, entry: Dict[str, Any]) -> None:
        """Add an entry to the game history."""
        self.history.append(entry)
        self.turn_count += 1

    def get_recent_history(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent history entries."""
        return self.history[-count:] if self.history else []

    # Description caching

    def cache_description(
        self,
        entity_type: str,
        entity_id: str,
        description: str,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache a generated description for an entity.

        Args:
            entity_type: Type of entity ("location", "npc", or "item")
            entity_id: Unique identifier for the entity
            description: The generated description text
            state_snapshot: Optional snapshot of relevant state at time of description
        """
        cache_key = f"{entity_type}:{entity_id}"
        self.description_cache[cache_key] = {
            "description": description,
            "turn": self.turn_count,
            "state_snapshot": state_snapshot or {}
        }

    def get_cached_description(
        self,
        entity_type: str,
        entity_id: str,
        current_item_ids: Optional[List[str]] = None,
        current_npc_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached description for an entity if still valid.

        Validates that relevant state hasn't changed before returning cached description.
        For locations, checks if time, items, or NPCs have changed.

        Args:
            entity_type: Type of entity ("location", "npc", or "item")
            entity_id: Unique identifier for the entity
            current_item_ids: Current item IDs at location (for validation)
            current_npc_ids: Current NPC IDs at location (for validation)

        Returns:
            Dict with description, turn, and state_snapshot, or None if not cached/invalid
        """
        cache_key = f"{entity_type}:{entity_id}"
        cached = self.description_cache.get(cache_key)

        if not cached:
            return None

        # For locations, check if significant state has changed
        if entity_type == "location":
            cached_state = cached.get("state_snapshot", {})

            # Check if time has changed
            cached_time = cached_state.get("game_time", "")
            current_time = self.game_time
            if cached_time != current_time:
                return None

            # Check if items at location have changed
            if current_item_ids is not None:
                cached_items = set(cached_state.get("item_ids", []))
                current_items = set(current_item_ids)
                if cached_items != current_items:
                    return None

            # Check if NPCs at location have changed
            if current_npc_ids is not None:
                cached_npcs = set(cached_state.get("npc_ids", []))
                current_npcs = set(current_npc_ids)
                if cached_npcs != current_npcs:
                    return None

        return cached

    # Serialization

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Create from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, filepath: str) -> "GameState":
        """Load game state from JSON file with puzzle system support."""
        import json

        with open(filepath, "r") as f:
            data = json.load(f)

        # Extract puzzles before creating GameState
        puzzles_data = data.pop("puzzles", {})

        # Create GameState from remaining data
        game_state = cls.from_dict(data)

        # Load puzzles into dm_state
        if puzzles_data:
            game_state.dm_state["puzzles"] = {}
            for puzzle_id, puzzle_def in puzzles_data.items():
                game_state.dm_state["puzzles"][puzzle_id] = {
                    **puzzle_def,
                    "solved": False,
                    "failed_attempts": 0,
                    "hints_given": [],
                    "current_state": "locked"
                }

            # Block exits for unsolved puzzles
            game_state.dm_state["blocked_exits"] = {}
            for location_id, location in game_state.locations.items():
                exit_blocked = location.attributes.get("exit_blocked", {})
                for direction, puzzle_id in exit_blocked.items():
                    if direction in location.connections:
                        blocked_key = f"{location_id}_{direction}"
                        game_state.dm_state["blocked_exits"][blocked_key] = {
                            "from_location": location_id,
                            "direction": direction,
                            "to_location": location.connections[direction],
                            "puzzle_id": puzzle_id
                        }
                        # Remove connection (blocks movement)
                        del location.connections[direction]

        return game_state

    def to_file(self, filepath: str) -> None:
        """Save game state to JSON file."""
        import json

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
