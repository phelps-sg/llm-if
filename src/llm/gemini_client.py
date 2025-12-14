"""Gemini LLM client for narrative generation using Vertex AI."""

import logging
import os
import subprocess
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from .action_schema import ActionInterpretation

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API via Vertex AI with gcloud authentication."""

    def __init__(
        self,
        project: Optional[str] = None,
        location: Optional[str] = None,
        # model_name: str = "gemini-2.0-flash-001",
        # model_name: str = "gemini-2.5-pro",
        # model_name: str = "gemini-2.0-flash-001",
        model_name: str = "gemini-2.5-flash",
    ):
        """Initialize Gemini client with gcloud authentication.

        Args:
            project: GCP project ID (or set GCP_PROJECT env var)
            location: GCP location (or set GCP_LOCATION env var, default: us-west1)
            model_name: Model to use (default: gemini-2.0-flash-001)
                       Options: gemini-2.0-flash-001, gemini-2.5-flash
        """
        self.project = project or os.getenv("GCP_PROJECT")
        self.location = location or os.getenv("GCP_LOCATION", "us-west1")
        self.model_name = model_name

        if not self.project:
            raise ValueError(
                "GCP_PROJECT must be set in environment or passed to constructor"
            )

        # Token caching
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Initialize Vertex AI
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project, location=self.location)
            self.model = GenerativeModel(self.model_name)
            self._vertexai = vertexai
        except ImportError:
            raise ImportError(
                "vertexai package not installed. Install with: poetry add google-cloud-aiplatform"
            )

    def _get_access_token(self) -> str:
        """Get access token from gcloud, using cache if valid.

        Returns:
            Access token string

        Raises:
            RuntimeError: If gcloud command fails
        """
        # Check if cached token is still valid (with 5 min buffer)
        if self._token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._token

        # Get fresh token from gcloud
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            token = result.stdout.strip()

            # Cache token (GCP tokens typically last 1 hour)
            self._token = token
            self._token_expires_at = datetime.now() + timedelta(hours=1)

            return token
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to get access token from gcloud: {e.stderr}"
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "gcloud CLI not found. Please install the Google Cloud SDK."
            )

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
            # Get fresh token (uses cache if valid)
            token = self._get_access_token()

            # Generate content
            response = self.model.generate_content(prompt, **kwargs)
            return str(response.text)
        except Exception as e:
            return f"Error generating response: {e}"

    def describe_location(
        self,
        location: Dict[str, Any],
        items: List[Any],
        npcs: List[Any],
        player_context: Optional[Dict[str, Any]] = None,
        world_context: Optional[Dict[str, Any]] = None,
        lighting_info: Optional[Dict[str, Any]] = None,
        cached_descriptions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a description of a location.

        Args:
            location: Location data
            items: Items at the location
            npcs: NPCs at the location
            player_context: Optional player context
            lighting_info: Lighting and visibility information
            cached_descriptions: Optional dict with previously generated descriptions
                Format: {"location": {...}, "items": {...}, "npcs": {...}}

        Returns:
            Narrative description
        """
        prompt = self._build_location_prompt(
            location, items, npcs, player_context, world_context, lighting_info, cached_descriptions
        )
        return self.generate(prompt)

    def generate_narrative(
        self,
        player_input: str,
        intent: str,
        context: Dict[str, Any],
        action_metadata: Optional[Dict[str, Any]] = None,
        state_updates: Optional[List[Dict[str, Any]]] = None,
        is_valid: bool = True,
        invalid_reason: Optional[str] = None,
        not_allowed_reason: Optional[str] = None,
    ) -> str:
        """Generate narrative response based on current game state after updates.

        This is called AFTER state updates have been applied, so the LLM
        generates narrative based on the actual current state of the world.

        Args:
            player_input: What the player said/did
            intent: Interpreted intent from LLM
            context: Current game context (after state updates)
            action_metadata: Metadata about what changed (extracted before updates)
            state_updates: The actual state updates that were applied (so LLM can narrate what happened)
            is_valid: Whether the action was valid (False means action failed)
            invalid_reason: If action was logically invalid, the reason to return directly
            not_allowed_reason: If action was not allowed by DM, the reason to return directly

        Returns:
            Narrative description of what happened
        """
        # Step 3 of 3-step architecture: Handle pre-generated rejection reasons
        if invalid_reason:
            return invalid_reason

        if not_allowed_reason:
            return not_allowed_reason

        # Otherwise, generate narrative from actual state (existing behavior)
        prompt = self._build_narrative_prompt(
            player_input, intent, context, action_metadata, state_updates, is_valid
        )
        return self.generate(prompt)

    def describe_action_result(
        self, action: str, result: Dict[str, Any], game_context: Dict[str, Any]
    ) -> str:
        """Generate narrative description of an action result.

        Args:
            action: The action taken
            result: Result data from rules engine
            game_context: Current game context

        Returns:
            Narrative description
        """
        prompt = self._build_action_result_prompt(action, result, game_context)
        return self.generate(prompt)

    def narrate_combat_result(self, combat_result: Dict[str, Any]) -> str:
        """Narrate combat outcome and prompt player for next action.

        Args:
            combat_result: Combat results from rule engine

        Returns:
            Narrative description with player prompt
        """
        prompt = self._build_combat_narration_prompt(combat_result)
        return self.generate(prompt)

    def narrate_npc_actions(
        self, npc_actions: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Narrate NPC actions (unprovoked attacks, chases).

        This is different from narrate_combat_result() because:
        - These are UNPROVOKED NPC actions (not counterattacks)
        - May include multiple NPCs acting in one turn
        - Includes both attacks AND chase events
        - Requires different tone (surprise/threat)

        Args:
            npc_actions: Dict containing:
                - npc_attacks: List of attack results with combat details
                - npc_chases: List of chase events
            context: Current game state context (location, NPCs, items, etc.)

        Returns:
            Narrative describing all NPC actions and prompting player
        """
        prompt = self._build_npc_actions_prompt(npc_actions, context)
        return self.generate(prompt)

    def describe_container_contents(
        self, container: Dict[str, Any], contents: list, context: Dict[str, Any]
    ) -> str:
        """Generate natural prose for items in/on a container.

        Args:
            container: Container item dict with id, name, attributes
            contents: List of item dicts inside the container
            context: Full game context (lighting, player attributes, location, etc.)

        Returns:
            Natural prose describing the contents (1-2 sentences), or empty string if can't see
        """
        prompt = self._build_container_contents_prompt(container, contents, context)
        return self.generate(prompt)

    def generate_dungeon_level(
        self,
        level_number: int,
        genre: str,
        plot: Optional[str] = None,
        specifics: Optional[str] = None,
        difficulty_modifier: float = 1.0,
        num_middle_locations: int = 3,
        num_npcs: int = 2,
        num_items: int = 3,
    ) -> Dict[str, Any]:
        """Generate complete dungeon level using iterative LLM calls with validation.

        Uses iterative generation (configurable number of LLM calls):
        1. Theme generation (1 call)
        2. Locations iteratively (num_middle_locations + 2 calls: entry → middle × N → exit)
        3. NPCs iteratively (num_npcs calls, each aware of locations)
        4. Items iteratively (num_items calls, each aware of locations + NPCs)
        5. Validation & programmatic repairs (reachability, light source)

        Descriptions generated on-demand when player visits locations.

        Args:
            level_number: Level depth (1, 2, 3, etc.)
            genre: Genre/theme for the level
            plot: Optional plot guidance
            specifics: Optional specific requests
            difficulty_modifier: Multiplier for difficulty scaling
            num_middle_locations: Number of middle locations to generate (default: 3)
            num_npcs: Number of NPCs to generate (default: 2)
            num_items: Number of items to generate (default: 3)

        Returns:
            Dict containing complete level data with validated reachability
        """
        import random

        # Use provided counts for dungeon generation
        num_middle = num_middle_locations
        total_steps = (
            4 + num_middle + num_npcs + num_items
        )  # theme + entry + middle + exit + npcs + items + validation

        # Step 1: Generate theme (1 call)
        step_num = 1
        print(f"  [{step_num}/{total_steps}] Generating level theme...")
        theme = self._generate_level_theme(level_number, genre, plot, specifics)
        print(f"    Theme: {theme}")

        # Step 2: Generate locations iteratively (4-5 calls)
        locations = []
        existing_state = {"locations": [], "theme": theme, "genre": genre}

        # Entry location
        step_num += 1
        print(f"  [{step_num}/{total_steps}] Generating entry location...")
        entry = self._generate_single_location(
            level_number, genre, theme, "entry", existing_state, plot, specifics
        )
        locations.append(entry)
        existing_state["locations"].append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "connections": entry["connections"],
            }
        )
        entry_id = entry["id"]

        # Middle locations (2-3)
        for i in range(num_middle):
            step_num += 1
            print(
                f"  [{step_num}/{total_steps}] Generating middle location {i + 1}/{num_middle}..."
            )
            middle = self._generate_single_location(
                level_number, genre, theme, "middle", existing_state, plot, specifics
            )
            locations.append(middle)
            existing_state["locations"].append(
                {
                    "id": middle["id"],
                    "name": middle["name"],
                    "connections": middle["connections"],
                }
            )

        # Exit location
        step_num += 1
        print(f"  [{step_num}/{total_steps}] Generating exit location...")
        exit_loc = self._generate_single_location(
            level_number, genre, theme, "exit", existing_state, plot, specifics
        )
        locations.append(exit_loc)
        existing_state["locations"].append(
            {
                "id": exit_loc["id"],
                "name": exit_loc["name"],
                "connections": exit_loc["connections"],
            }
        )
        exit_id = exit_loc["id"]

        # Step 3: Generate NPCs iteratively (1-2 calls)
        npcs = []
        npc_locations = {}
        existing_state["npcs"] = []

        for i in range(num_npcs):
            step_num += 1
            print(f"  [{step_num}/{total_steps}] Generating NPC {i + 1}/{num_npcs}...")
            npc = self._generate_single_npc(
                level_number, genre, theme, existing_state, difficulty_modifier
            )
            npcs.append(
                {"id": npc["id"], "name": npc["name"], "attributes": npc["attributes"]}
            )
            npc_locations[npc["id"]] = npc["location"]
            existing_state["npcs"].append(
                {"id": npc["id"], "name": npc["name"], "location": npc["location"]}
            )

        # Step 4: Generate items iteratively (configurable number of calls)
        items = []
        item_locations = {}
        existing_state["items"] = []

        # Generate variety: cycle through item types
        item_type_options = ["weapon", "consumable", "treasure", "tool", "light_source"]
        for i in range(num_items):
            step_num += 1
            # Cycle through item types for variety
            item_type_hint = item_type_options[i % len(item_type_options)]
            print(
                f"  [{step_num}/{total_steps}] Generating item {i + 1}/{num_items} ({item_type_hint})..."
            )
            item = self._generate_single_item(
                level_number, genre, theme, existing_state, item_type_hint
            )
            items.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "attributes": item["attributes"],
                }
            )
            item_locations[item["id"]] = item["location"]
            existing_state["items"].append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "type": item["attributes"].get("type", "unknown"),
                }
            )

        # Step 5: Validate & Repair
        step_num += 1
        print(f"  [{step_num}/{total_steps}] Validating and repairing dungeon...")

        # Validate bidirectional connections
        bidir_check = self._validate_bidirectional_connections(locations)
        if not bidir_check["is_valid"]:
            print(
                f"    [VALIDATION] Found {len(bidir_check['missing_reverse'])} missing reverse connections"
            )
            locations = self._repair_bidirectional_connections(
                locations, bidir_check["missing_reverse"]
            )
            print(f"    [REPAIR] All connections now bidirectional ✓")
        else:
            print(f"    [VALIDATION] All connections bidirectional ✓")

        # Validate reachability (after fixing bidirectional connections)
        reachability = self._validate_reachability(locations, entry_id)
        if not reachability["is_valid"]:
            print(
                f"    [VALIDATION] Found {len(reachability['unreachable'])} unreachable locations"
            )
            locations = self._repair_unreachable_locations(
                locations, reachability["reachable"], reachability["unreachable"]
            )
            print(f"    [REPAIR] All locations now reachable")
        else:
            print(f"    [VALIDATION] All locations reachable ✓")

        # Validate light source
        light_check = self._validate_light_source(items, item_locations, entry_id, [])
        if not light_check["is_valid"]:
            print(f"    [VALIDATION] No light source at entry location")
            items, item_locations = self._repair_missing_light(
                items, item_locations, entry_id, level_number, genre, theme
            )
            print(f"    [REPAIR] Added light source at entry ✓")
        else:
            print(f"    [VALIDATION] Light source available at entry ✓")

        # Return complete level data
        return {
            "locations": locations,
            "npcs": npcs,
            "items": items,
            "npc_locations": npc_locations,
            "item_locations": item_locations,
            "entry_location_id": entry_id,
            "exit_location_id": exit_id,
            "theme": theme,
        }

    def _generate_level_structure(
        self,
        level_number: int,
        genre: str,
        plot: Optional[str],
        specifics: Optional[str],
    ) -> Dict[str, Any]:
        """Generate level structure (locations, connections, theme).

        Returns:
            locations: List of location dicts (minimal - just ID, name, connections, attributes)
            entry_location_id: Entry location ID
            exit_location_id: Exit location ID
            theme: Theme string
            location_ids: List of all location IDs (for NPC/item placement)
        """
        from vertexai.generative_models import GenerationConfig
        import json

        plot_text = f"\nPlot: {plot}" if plot else ""
        specifics_text = f"\nSpecifics: {specifics}" if specifics else ""

        prompt = f"""Generate the STRUCTURE for Level {level_number} of a {genre} dungeon.{plot_text}{specifics_text}

Create 3-4 interconnected locations with connections. DO NOT generate descriptions - those will be created dynamically based on game state.

Requirements:
1. Generate 3-4 locations (keep it small and manageable)
2. Each location MUST have:
   - id: "l{level_number}_<name>" (e.g., "l{level_number}_crypt")
   - name: Descriptive location name
   - connections: OBJECT with direction keys ("north", "south", "east", "west") mapping to location IDs
   - attributes: OBJECT with at least "description_hints" (brief hints for AI descriptions) and "lighting" ("bright", "dim", or "dark")
3. One must be ENTRY (where player arrives)
4. One must be EXIT (leads to next level)
5. Create cohesive theme for the level
6. Ensure locations form a connected graph (player can reach all locations)

The EXIT location MUST have these attributes:
- is_dungeon_exit: true
- leads_to_level: {level_number + 1}
- description_hints: something like "passage leading deeper"

Example location:
{{
  "id": "l1_chamber",
  "name": "Stone Chamber",
  "connections": {{"north": "l1_hallway", "east": "l1_crypt"}},
  "attributes": {{"description_hints": "ancient stone walls, dusty", "lighting": "dim"}}
}}

Return JSON with:
- locations: Array of location objects (each with id, name, connections OBJECT, attributes OBJECT)
- entry_location_id: ID string
- exit_location_id: ID string
- theme: Theme description string"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "locations": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "name": {"type": "STRING"},
                            "connections": {"type": "OBJECT"},
                            "attributes": {"type": "OBJECT"},
                        },
                        "required": ["id", "name", "connections", "attributes"],
                    },
                },
                "entry_location_id": {"type": "STRING"},
                "exit_location_id": {"type": "STRING"},
                "theme": {"type": "STRING"},
            },
            "required": ["locations", "entry_location_id", "exit_location_id", "theme"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.9,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        data = json.loads(response.text)

        # Add location_ids for convenience
        data["location_ids"] = [loc["id"] for loc in data["locations"]]

        return data

    def _generate_level_npcs(
        self,
        level_number: int,
        genre: str,
        theme: str,
        location_ids: List[str],
        difficulty_modifier: float,
    ) -> Dict[str, Any]:
        """Generate NPCs for the level.

        Returns:
            npcs: List of NPC dicts
            npc_locations: Dict mapping NPC IDs to location IDs
        """
        from vertexai.generative_models import GenerationConfig
        import json

        # Calculate difficulty
        base_hp = 10 + (level_number - 1) * 5
        base_ac = 12 + (level_number - 1)
        hp = int(base_hp * difficulty_modifier)
        ac = int(base_ac * difficulty_modifier)

        prompt = f"""Generate 1-2 NPCs for Level {level_number} ({genre} theme: {theme}).

NPC Stats (scale to level {level_number}):
- HP: {hp - 5} to {hp + 5}
- AC: {ac - 1} to {ac + 1}
- Attack bonus: +{max(2, level_number + 1)}

Each NPC MUST have:
- id: "npc{level_number}_<name>_1" (e.g., "npc{level_number}_skeleton_1")
- name: Thematic to {genre}
- attributes: OBJECT containing ALL of these fields:
  - hp: current hit points (number)
  - hp_max: maximum hit points (number)
  - armor_class: AC value (number)
  - attack_bonus: attack modifier (number)
  - hostility: "aggressive" (60% chance), "neutral" (30%), or "passive" (10%)
  - creature_type: "beast", "undead", "humanoid", etc.
  - description_hints: brief physical description for AI

Example NPC:
{{
  "id": "npc1_zombie_1",
  "name": "Shambling Zombie",
  "attributes": {{
    "hp": 12,
    "hp_max": 12,
    "armor_class": 10,
    "attack_bonus": 3,
    "hostility": "aggressive",
    "creature_type": "undead",
    "description_hints": "rotting flesh, vacant eyes, slow movements"
  }}
}}

Place NPCs at these locations: {location_ids}

Return JSON:
- npcs: Array of NPC objects (each with id, name, attributes OBJECT)
- npc_locations: OBJECT mapping NPC IDs to location IDs (e.g., {{"npc1_zombie_1": "l1_crypt"}})"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "npcs": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "name": {"type": "STRING"},
                            "attributes": {"type": "OBJECT"},
                        },
                        "required": ["id", "name", "attributes"],
                    },
                },
                "npc_locations": {"type": "OBJECT"},
            },
            "required": ["npcs", "npc_locations"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.8,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)

    def _generate_level_items(
        self, level_number: int, genre: str, theme: str, location_ids: List[str]
    ) -> Dict[str, Any]:
        """Generate items for the level.

        Returns:
            items: List of item dicts
            item_locations: Dict mapping item IDs to location IDs
        """
        from vertexai.generative_models import GenerationConfig
        import json

        prompt = f"""Generate 2-3 items for Level {level_number} ({genre} theme: {theme}).

Mix of:
- 1 weapon (damage appropriate to level {level_number})
- 1-2 consumables or treasure

Each item must have:
- id: "item{level_number}_<name>" (e.g., "item{level_number}_sword")
- name: Thematic to {genre}
- attributes: type, damage (if weapon), description_hints, etc.

Place items at these locations: {location_ids}

Return JSON:
- items: Array of item objects
- item_locations: Object mapping item IDs to location IDs"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "name": {"type": "STRING"},
                            "attributes": {"type": "OBJECT"},
                        },
                        "required": ["id", "name", "attributes"],
                    },
                },
                "item_locations": {"type": "OBJECT"},
            },
            "required": ["items", "item_locations"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.8,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)

    # ========================================================================
    # ITERATIVE GENERATION METHODS (New approach with validation & repairs)
    # ========================================================================

    def _generate_level_theme(
        self,
        level_number: int,
        genre: str,
        plot: Optional[str],
        specifics: Optional[str],
    ) -> str:
        """Generate a cohesive theme for the level.

        Args:
            level_number: Level depth
            genre: Overall genre
            plot: Optional plot guidance
            specifics: Optional specific requests

        Returns:
            Theme string (e.g., "Abandoned Crypt", "Flooded Caverns")
        """
        from vertexai.generative_models import GenerationConfig
        import json

        plot_text = f"\nPlot: {plot}" if plot else ""
        specifics_text = f"\nSpecifics: {specifics}" if specifics else ""

        prompt = f"""Generate a cohesive THEME for Level {level_number} of a {genre} dungeon.{plot_text}{specifics_text}

Return a brief theme description (2-4 words) that will guide the generation of locations, NPCs, and items.

Examples:
- "Flooded Catacombs"
- "Ancient Dwarven Mine"
- "Cursed Burial Chambers"
- "Overgrown Temple Ruins"

Return JSON: {{"theme": "Your Theme Here"}}
"""

        schema = {
            "type": "OBJECT",
            "properties": {"theme": {"type": "STRING"}},
            "required": ["theme"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.9,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        data = json.loads(response.text)

        return data["theme"]

    def _validate_reachability(
        self, locations: List[Dict], entry_id: str
    ) -> Dict[str, Any]:
        """Validate all locations are reachable from entry using BFS.

        Args:
            locations: List of location dicts with id, connections
            entry_id: ID of entry location

        Returns:
            Dict with:
            - is_valid: bool
            - reachable: set of reachable location IDs
            - unreachable: set of unreachable location IDs
        """
        # Build adjacency graph
        graph = {}
        all_location_ids = set()

        for loc in locations:
            loc_id = loc["id"]
            all_location_ids.add(loc_id)
            graph[loc_id] = []

            # Add connections (bidirectional assumed from generation)
            for direction, dest_id in loc.get("connections", {}).items():
                if dest_id:
                    graph[loc_id].append(dest_id)

        # BFS from entry
        visited = set()
        queue = [entry_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)

            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        unreachable = all_location_ids - visited

        return {
            "is_valid": len(unreachable) == 0,
            "reachable": visited,
            "unreachable": unreachable,
        }

    def _validate_bidirectional_connections(
        self, locations: List[Dict]
    ) -> Dict[str, Any]:
        """Validate all connections are bidirectional.

        Args:
            locations: List of location dicts

        Returns:
            Dict with:
            - is_valid: bool (True if all connections are bidirectional)
            - missing_reverse: list of (from_id, direction, to_id, reverse_direction) tuples
        """
        missing_reverse = []
        reverse_directions = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "up": "down",
            "down": "up",
        }

        # Build location lookup
        loc_by_id = {loc["id"]: loc for loc in locations}

        # Check each connection
        for loc in locations:
            loc_id = loc["id"]
            for direction, dest_id in loc.get("connections", {}).items():
                if not dest_id:
                    continue

                # Find reverse direction
                reverse_dir = reverse_directions.get(direction)
                if not reverse_dir:
                    continue

                # Check if destination has reverse connection
                dest_loc = loc_by_id.get(dest_id)
                if not dest_loc:
                    continue

                dest_connections = dest_loc.get("connections", {})
                reverse_conn = dest_connections.get(reverse_dir)

                # If reverse connection doesn't point back to us, it's missing
                if reverse_conn != loc_id:
                    missing_reverse.append((loc_id, direction, dest_id, reverse_dir))

        return {
            "is_valid": len(missing_reverse) == 0,
            "missing_reverse": missing_reverse,
        }

    def _repair_bidirectional_connections(
        self, locations: List[Dict], missing_reverse: List[tuple]
    ) -> List[Dict]:
        """Add missing reverse connections to make all connections bidirectional.

        Args:
            locations: List of location dicts
            missing_reverse: List of (from_id, direction, to_id, reverse_direction) tuples

        Returns:
            Updated locations list
        """
        # Build location lookup
        loc_by_id = {loc["id"]: loc for loc in locations}

        for from_id, direction, to_id, reverse_dir in missing_reverse:
            dest_loc = loc_by_id.get(to_id)
            if not dest_loc:
                continue

            # Ensure connections dict exists
            if "connections" not in dest_loc:
                dest_loc["connections"] = {}

            # Add reverse connection
            dest_loc["connections"][reverse_dir] = from_id
            print(
                f"  [REPAIR] Added bidirectional connection: {to_id} ({reverse_dir}) -> {from_id}"
            )

        return locations

    def _validate_light_source(
        self,
        items: List[Dict],
        item_locations: Dict[str, str],
        entry_id: str,
        player_inventory: List[str],
    ) -> Dict[str, Any]:
        """Validate player has access to light source at start.

        Args:
            items: List of item dicts
            item_locations: Map of item_id -> location_id
            entry_id: Entry location ID
            player_inventory: Initial player inventory item IDs

        Returns:
            Dict with:
            - is_valid: bool
            - has_light: bool
            - light_items_at_entry: list of item IDs
            - light_items_in_inventory: list of item IDs
        """
        light_items_at_entry = []
        light_items_in_inventory = []

        for item in items:
            item_id = item["id"]
            attributes = item.get("attributes", {})

            # Check if item provides light
            provides_light = attributes.get("provides_light", False)
            is_light_source = attributes.get("type") == "light_source"

            if provides_light or is_light_source:
                # Check if at entry or in player inventory
                item_location = item_locations.get(item_id)

                if item_location == entry_id:
                    light_items_at_entry.append(item_id)
                elif item_id in player_inventory:
                    light_items_in_inventory.append(item_id)

        has_light = len(light_items_at_entry) > 0 or len(light_items_in_inventory) > 0

        return {
            "is_valid": has_light,
            "has_light": has_light,
            "light_items_at_entry": light_items_at_entry,
            "light_items_in_inventory": light_items_in_inventory,
        }

    def _repair_unreachable_locations(
        self, locations: List[Dict], reachable: set, unreachable: set
    ) -> List[Dict]:
        """Add connections to make all locations reachable.

        Strategy: For each unreachable location, connect to nearest reachable location.

        Args:
            locations: List of location dicts (will be modified in place)
            reachable: Set of reachable location IDs
            unreachable: Set of unreachable location IDs

        Returns:
            Modified locations list with repairs
        """
        # Build location dict for easy lookup
        loc_dict = {loc["id"]: loc for loc in locations}

        # Direction priorities (prefer cardinal directions)
        direction_options = ["north", "south", "east", "west", "up", "down"]
        reverse_directions = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "up": "down",
            "down": "up",
        }

        for unreachable_id in unreachable:
            unreachable_loc = loc_dict[unreachable_id]

            # Find first available direction on unreachable location
            chosen_direction = None
            for direction in direction_options:
                if direction not in unreachable_loc.get("connections", {}):
                    chosen_direction = direction
                    break

            if not chosen_direction:
                # All directions used, pick first and override
                chosen_direction = "north"

            # Pick a reachable location to connect to (preferably entry or a central location)
            # For simplicity, connect to first reachable location with available reverse direction
            target_loc_id = None
            target_direction = reverse_directions.get(chosen_direction)

            for reachable_id in reachable:
                reachable_loc = loc_dict[reachable_id]
                if target_direction not in reachable_loc.get("connections", {}):
                    target_loc_id = reachable_id
                    break

            if not target_loc_id:
                # Fallback: just pick first reachable
                target_loc_id = list(reachable)[0]
                target_direction = "north"  # Override

            # Add bidirectional connections
            unreachable_loc["connections"][chosen_direction] = target_loc_id
            loc_dict[target_loc_id]["connections"][target_direction] = unreachable_id

            print(
                f"  [REPAIR] Connected {unreachable_id} ({chosen_direction}) <-> {target_loc_id} ({target_direction})"
            )

        return locations

    def _repair_missing_light(
        self,
        items: List[Dict],
        item_locations: Dict[str, str],
        entry_id: str,
        level_number: int,
        genre: str,
        theme: str,
    ) -> tuple[List[Dict], Dict[str, str]]:
        """Add a light source at entry if none exists.

        Uses LLM to generate a thematically appropriate light source.

        Args:
            items: List of item dicts
            item_locations: Map of item_id -> location_id
            entry_id: Entry location ID
            level_number: Current level number
            genre: Genre for thematic consistency
            theme: Level theme for thematic consistency

        Returns:
            Tuple of (updated items list, updated item_locations dict)
        """
        from vertexai.generative_models import GenerationConfig
        import json

        prompt = f"""Generate a LIGHT SOURCE item for Level {level_number} ({genre} theme: {theme}).

This light source will be placed at the dungeon entry to ensure the player can see.

Requirements:
1. Generate ONE light source item appropriate to {genre}:
   - id: "item{level_number}_light_starter"
   - name: Thematic light source name (e.g., "Worn Torch" for fantasy, "Flashlight" for sci-fi, "Glowing Crystal" for magic)
   - attributes: OBJECT with:
     * type: "light_source"
     * provides_light: true
     * light_radius: 10-15
     * description_hints: brief description
     * [optional] Can also function as improvised weapon: damage (e.g., "1d4"), damage_type

Examples by genre:
- Dark fantasy: worn torch, oil lantern, dying candle
- Sci-fi: flashlight, emergency glow-stick, portable lamp
- Magic: enchanted crystal, glowing orb, light spell focus
- Horror: flickering candle, cracked lantern, dim flashlight

Return JSON: {{"id": "item{level_number}_light_starter", "name": "...", "attributes": {{}}}}
"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "attributes": {"type": "OBJECT"},
            },
            "required": ["id", "name", "attributes"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.8,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        light_item = json.loads(response.text)

        items.append(light_item)
        item_locations[light_item["id"]] = entry_id

        print(
            f"  [REPAIR] Added light source '{light_item['name']}' ({light_item['id']}) at entry location '{entry_id}'"
        )

        return items, item_locations

    def _generate_single_location(
        self,
        level_number: int,
        genre: str,
        theme: str,
        location_type: str,  # "entry", "middle", "exit"
        existing_state: Dict[str, Any],
        plot: Optional[str] = None,
        specifics: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single location with context awareness.

        Args:
            level_number: Current dungeon level
            genre: Genre/theme
            theme: Specific theme for this level
            location_type: "entry", "middle", or "exit"
            existing_state: Current dungeon state (locations, connections)
            plot: Optional plot guidance
            specifics: Optional specific requests

        Returns:
            Dict with location data including id, name, connections, attributes
        """
        from vertexai.generative_models import GenerationConfig
        import json

        existing_locations_json = ""
        if location_type != "entry" and existing_state.get("locations"):
            existing_locations_json = f"\n\nEXISTING LOCATIONS (you must connect to at least one):\n{json.dumps(existing_state.get('locations', []), indent=2)}"

        prompt = f"""Generate a SINGLE {location_type} location for Level {level_number} of a {genre} dungeon.
Theme: {theme}{existing_locations_json}

Requirements:
1. Generate ONE location with:
   - id: "l{level_number}_<name>" (e.g., "l{level_number}_crypt")
   - name: Descriptive location name
   - connections: OBJECT mapping directions to location IDs
     {"* Entry location can have connections: {} (will be filled later by other locations)" if location_type == "entry" else "* MUST connect to at least ONE existing location above"}
     * Use directions: north, south, east, west, up, down
   - attributes: OBJECT with:
     * description_hints: Brief hints for AI descriptions
     * lighting: "bright", "dim", or "dark"
     {"* is_dungeon_exit: true" if location_type == "exit" else ""}
     {"* leads_to_level: " + str(level_number + 1) if location_type == "exit" else ""}

2. Location Type Requirements:
   - entry: Starting point{", no connections needed" if location_type == "entry" else ""}
   - middle: Connects between entry and exit, adds exploration
   - exit: Leads to next level, marked as dungeon exit

Return JSON: {{"id": "...", "name": "...", "connections": {{}}, "attributes": {{}}}}
"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "connections": {"type": "OBJECT"},
                "attributes": {"type": "OBJECT"},
            },
            "required": ["id", "name", "connections", "attributes"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.8,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)

    def _generate_single_npc(
        self,
        level_number: int,
        genre: str,
        theme: str,
        existing_state: Dict[str, Any],
        difficulty_modifier: float = 1.0,
    ) -> Dict[str, Any]:
        """Generate a single NPC with full dungeon context.

        Args:
            level_number: Current dungeon level
            genre: Genre/theme (e.g., "dark fantasy", "sci-fi horror")
            theme: Level theme (e.g., "Abandoned Crypt")
            existing_state: Current dungeon state with locations and existing NPCs
            difficulty_modifier: Multiplier for NPC stats

        Returns:
            Dict with:
            - id: NPC ID
            - name: NPC name
            - attributes: NPC attributes (hp, ac, hostility, etc.)
            - location: Location ID where NPC is placed
        """
        from vertexai.generative_models import GenerationConfig

        # Calculate scaled stats based on level and difficulty
        base_hp = 10 + (level_number * 5)
        base_ac = 10 + level_number
        base_attack = level_number + 2

        hp_min = int(base_hp * difficulty_modifier * 0.8)
        hp_max = int(base_hp * difficulty_modifier * 1.2)
        ac_min = int(base_ac * difficulty_modifier * 0.9)
        ac_max = int(base_ac * difficulty_modifier * 1.1)
        attack_bonus = int(base_attack * difficulty_modifier)

        # Format existing locations for prompt
        existing_locations_summary = [
            {"id": loc["id"], "name": loc["name"]}
            for loc in existing_state.get("locations", [])
        ]

        # Format existing NPCs for variety
        existing_npcs_summary = []
        for npc in existing_state.get("npcs", []):
            existing_npcs_summary.append(
                {
                    "id": npc["id"],
                    "name": npc["name"],
                    "creature_type": npc.get("attributes", {}).get(
                        "creature_type", "unknown"
                    ),
                }
            )

        existing_npcs_json = ""
        if existing_npcs_summary:
            existing_npcs_json = f"\n\nEXISTING NPCs (for variety - generate a different type):\n{json.dumps(existing_npcs_summary, indent=2)}"

        prompt = f"""Generate ONE NPC for Level {level_number} of a {genre} dungeon.
Theme: {theme}

EXISTING LOCATIONS (place NPC at one):
{json.dumps(existing_locations_summary, indent=2)}{existing_npcs_json}

NPC Stats (use values in these ranges):
- HP: {hp_min}-{hp_max}
- Armor Class: {ac_min}-{ac_max}
- Attack bonus: +{attack_bonus}

Requirements:
1. Generate ONE NPC with:
   - id: "npc{level_number}_<name>_<number>" (e.g., "npc{level_number}_goblin_1")
   - name: Thematic to {genre} and {theme}
   - attributes: OBJECT with:
     * hp: number (current hit points, same as hp_max)
     * hp_max: number (maximum hit points)
     * armor_class: number (AC)
     * attack_bonus: number (attack roll bonus)
     * hostility: "aggressive" (60% chance), "neutral" (30%), or "passive" (10%)
     * creature_type: "beast", "undead", "humanoid", "aberration", "construct", etc.
     * description_hints: brief physical description (1-2 sentences)
   - location: ONE of the existing location IDs above

2. Creature Type Examples by Genre:
   - Dark fantasy: undead, beast, humanoid bandits
   - Sci-fi horror: aberration, alien, corrupted humanoid, construct
   - Ancient ruins: construct, elemental, guardian
   - Space opera: alien, robot, cyborg

Return JSON: {{"id": "...", "name": "...", "attributes": {{}}, "location": "..."}}
"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "attributes": {
                    "type": "OBJECT",
                    "properties": {
                        "hp": {"type": "NUMBER"},
                        "hp_max": {"type": "NUMBER"},
                        "armor_class": {"type": "NUMBER"},
                        "attack_bonus": {"type": "NUMBER"},
                        "hostility": {"type": "STRING"},
                        "creature_type": {"type": "STRING"},
                        "description_hints": {"type": "STRING"},
                    },
                    "required": [
                        "hp",
                        "hp_max",
                        "armor_class",
                        "attack_bonus",
                        "hostility",
                        "creature_type",
                        "description_hints",
                    ],
                },
                "location": {"type": "STRING"},
            },
            "required": ["id", "name", "attributes", "location"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.85,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)

    def _generate_single_item(
        self,
        level_number: int,
        genre: str,
        theme: str,
        existing_state: Dict[str, Any],
        item_type_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single item with full dungeon context.

        Args:
            level_number: Current dungeon level
            genre: Genre/theme (e.g., "dark fantasy", "sci-fi horror")
            theme: Level theme (e.g., "Abandoned Crypt")
            existing_state: Current dungeon state with locations, NPCs, existing items
            item_type_hint: Preferred item type ("weapon", "consumable", "treasure", "tool", "light_source")

        Returns:
            Dict with:
            - id: Item ID
            - name: Item name
            - attributes: Item attributes (type, damage, effect, etc.)
            - location: Location ID where item is placed
        """
        from vertexai.generative_models import GenerationConfig

        # Format existing locations for prompt
        existing_locations_summary = [
            {"id": loc["id"], "name": loc["name"]}
            for loc in existing_state.get("locations", [])
        ]

        # Format existing NPCs for context
        existing_npcs_summary = []
        for npc in existing_state.get("npcs", []):
            existing_npcs_summary.append(
                {
                    "id": npc["id"],
                    "name": npc["name"],
                    "location": npc.get("location", "unknown"),
                }
            )

        existing_npcs_json = ""
        if existing_npcs_summary:
            existing_npcs_json = (
                f"\n\nEXISTING NPCs:\n{json.dumps(existing_npcs_summary, indent=2)}"
            )

        # Format existing items for variety
        existing_items_summary = []
        for item in existing_state.get("items", []):
            existing_items_summary.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "type": item.get("attributes", {}).get("type", "unknown"),
                }
            )

        existing_items_json = ""
        if existing_items_summary:
            existing_items_json = f"\n\nEXISTING ITEMS (for variety - generate a different type or use):\n{json.dumps(existing_items_summary, indent=2)}"

        item_type_guidance = ""
        if item_type_hint:
            item_type_guidance = f"\n\nItem Type Preference: {item_type_hint} (try to generate this type if thematically appropriate)"

        prompt = f"""Generate ONE item for Level {level_number} of a {genre} dungeon.
Theme: {theme}

EXISTING LOCATIONS (place item at one):
{json.dumps(existing_locations_summary, indent=2)}{existing_npcs_json}{existing_items_json}{item_type_guidance}

Requirements:
1. Generate ONE item with:
   - id: "item{level_number}_<name>_<number>" (e.g., "item{level_number}_sword_1")
   - name: Thematic to {genre} and {theme}
   - attributes: OBJECT with:
     * type: "weapon", "consumable", "treasure", "tool", or "light_source"
     * description_hints: brief description (1-2 sentences)

     [IF type is "weapon"]:
     * damage: dice notation (e.g., "1d6", "1d8+1")
     * damage_type: "slashing", "piercing", "bludgeoning", "energy", etc.

     [IF type is "consumable"]:
     * effect: what it does (e.g., "heals 2d6 HP", "grants +2 AC for 3 turns")
     * uses: number (how many times it can be used)

     [IF type is "light_source"]:
     * provides_light: true
     * light_radius: number (10-15)

     [IF type is "treasure"]:
     * value: number (gold/credits value)

     [IF type is "tool"]:
     * utility: what it's used for (e.g., "opens locks", "reveals hidden doors")

   - location: ONE of the existing location IDs above

2. Item Type Examples by Genre:
   - Dark fantasy: rusty sword, healing potion, ancient tome, lockpick, torch
   - Sci-fi horror: plasma cutter, med-kit, data chip, multi-tool, flashlight
   - Ancient ruins: stone weapon, herb bundle, golden idol, rope, enchanted crystal
   - Space opera: blaster, stim-pack, credits chip, scanner, glow-stick

Return JSON: {{"id": "...", "name": "...", "attributes": {{}}, "location": "..."}}
"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "attributes": {"type": "OBJECT"},
                "location": {"type": "STRING"},
            },
            "required": ["id", "name", "attributes", "location"],
        }

        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.85,
        )

        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)

    def interpret_action(
        self, player_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """DEPRECATED: Use 3-step flow (interpret_intent + generate_state_updates + generate_narrative).

        This method is maintained for backward compatibility with existing tests.
        It internally uses the 3-step architecture to prevent hallucination.

        Args:
            player_input: Natural language input from player
            context: Current game context with location, items, NPCs, etc.

        Returns:
            Combined result from 3-step flow with:
            - intent: What the player is trying to do
            - is_valid: Whether action makes logical sense
            - is_allowed: Whether DM allows it given context
            - state_updates: List of state changes to apply
            - narrative_response: None (should be generated separately)
            - requires_dice_roll: Whether mechanics require a roll
            - dice_check: Parameters for dice roll if needed
        """
        # STEP 1: Interpret intent and check permission
        intent_result = self.interpret_intent(player_input, context)

        # STEP 2: Generate mechanics (only if valid AND allowed)
        if intent_result["is_valid"] and intent_result["is_allowed"]:
            mechanics_result = self.generate_state_updates(
                intent_result["intent"], context, intent_result
            )
        else:
            # Not allowed - no mechanics
            mechanics_result = {
                "state_updates": [],
                "requires_dice_roll": False,
                "dice_check": None,
                "time_advancement": None,
                "new_time": None,
            }

        # Combine for backward compatibility
        combined = {**intent_result, **mechanics_result}
        combined["narrative_response"] = None  # Should be generated separately

        return combined

    def _interpret_action_old(
        self, player_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OLD IMPLEMENTATION - Kept for reference only.

        This old single-step approach could hallucinate state changes.
        """
        prompt = self._build_action_interpretation_prompt(player_input, context)

        try:
            # Get fresh token (uses cache if valid)
            token = self._get_access_token()

            # Use structured output with JSON schema (Gemini enforced generation)
            # Using OpenAPI 3.0 schema format as required by Vertex AI
            from vertexai.generative_models import GenerationConfig

            # Define strict schema using OpenAPI 3.0 format with type keywords
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "intent": {"type": "STRING"},
                    "is_valid": {"type": "BOOLEAN"},
                    "state_updates": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "type": {"type": "STRING"},
                                "target": {"type": "STRING", "nullable": True},
                                "params": {
                                    "type": "OBJECT",
                                    "properties": {},
                                    "additionalProperties": True,
                                },
                            },
                            "required": ["type", "params"],
                        },
                    },
                    "narrative_response": {"type": "STRING", "nullable": True},
                    "requires_dice_roll": {"type": "BOOLEAN"},
                    "dice_check": {
                        "type": "OBJECT",
                        "properties": {},
                        "additionalProperties": True,
                        "nullable": True,
                    },
                    "time_advancement": {"type": "STRING", "nullable": True},
                    "new_time": {"type": "STRING", "nullable": True},
                },
                "required": [
                    "intent",
                    "is_valid",
                    "state_updates",
                    "requires_dice_roll",
                ],
            }

            generation_config = GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.7,  # Lower temperature for more consistent JSON
            )

            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )

            # DEBUG: Print raw response
            logger.debug(f"Raw Gemini response:\n{response.text}")

            # Parse the JSON response directly
            parsed: Dict[str, Any] = json.loads(response.text)

            # Post-process: Fill in missing params based on context
            parsed = self._fill_missing_params(parsed, context)

            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
            print("[RETRY] Attempting with simpler prompt...")

            # Retry with a much simpler, more focused prompt
            try:
                simple_prompt = self._build_simple_action_prompt(player_input, context)
                response = self.model.generate_content(
                    simple_prompt, generation_config=generation_config
                )
                logger.debug(f"Retry response:\n{response.text}")
                parsed = json.loads(response.text)
                parsed = self._fill_missing_params(parsed, context)
                return parsed
            except Exception as retry_error:
                logger.warning(f"Retry also failed: {retry_error}")

        except Exception as e:
            logger.warning(f"LLM error: {e}")

        # Ultimate fallback: DM gracefully handles anything
        return {
            "intent": f"Player says: {player_input}",
            "is_valid": True,
            "state_updates": [],
            "requires_dice_roll": False,
            "dice_check": None,
        }

    def _fill_missing_params(
        self, interpretation: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fill in missing params in state updates based on context.

        Vertex AI's schema can't enforce conditional requirements,
        so we intelligently fill in missing required params here.
        """
        state_updates = interpretation.get("state_updates", [])
        exit_destinations = context.get("exit_destinations", {})

        for update in state_updates:
            update_type = update.get("type")
            params = update.get("params", {})
            target = update.get("target")

            # Fix move_player with missing destination
            if update_type == "move_player" and not params.get("destination"):
                # Try to infer from intent which direction they're going
                intent = interpretation.get("intent", "").lower()
                for direction, dest_id in exit_destinations.items():
                    if direction in intent:
                        params["destination"] = dest_id
                        update["params"] = params
                        print(
                            f"[DEBUG] Filled missing destination: {direction} -> {dest_id}"
                        )
                        break

            # Fix add_to_inventory with missing item_id
            elif update_type == "add_to_inventory" and not params.get("item_id"):
                if target:  # LLM often puts item_id in target instead of params
                    params["item_id"] = target
                    update["params"] = params
                    logger.debug(f"Filled missing item_id from target: {target}")

            # Fix remove_from_inventory with missing item_id
            elif update_type == "remove_from_inventory" and not params.get("item_id"):
                if target:
                    params["item_id"] = target
                    update["params"] = params
                    logger.debug(f"Filled missing item_id from target: {target}")
                else:
                    # Use pronoun resolution - if "it" refers to last item
                    last_item = context.get("last_item")
                    if last_item:
                        params["item_id"] = last_item
                        update["params"] = params
                        print(
                            f"[DEBUG] Filled missing item_id from pronoun resolution: {last_item}"
                        )

            # Fix move_item with missing params
            elif update_type == "move_item":
                if not params.get("item_id") and target:
                    params["item_id"] = target
                if not params.get("to_location"):
                    # Default to current location if not specified
                    params["to_location"] = context.get("location", {}).get("id")
                update["params"] = params
                if target:
                    logger.debug(f"Filled missing move_item params for {target}")

            # Fix trigger_combat with missing target_npc_id
            elif update_type == "trigger_combat":
                if not params.get("target_npc_id") and target:
                    params["target_npc_id"] = target
                    update["params"] = params
                    logger.debug(f"Filled missing target_npc_id from target: {target}")

        return interpretation

    def interpret_intent(
        self, player_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """STEP 1: Interpret player intent and check permission.

        This is the first step of the 3-step LLM architecture.
        It ONLY interprets intent and checks if the action is valid and allowed.
        It does NOT generate state updates or narrative.

        Args:
            player_input: Natural language input from player
            context: Current game context

        Returns:
            IntentInterpretation as dict with:
            - intent: What player is trying to do
            - is_valid: Does the action make logical sense?
            - is_allowed: Will DM allow it given game state?
            - invalid_reason: If is_valid=false, why not?
            - not_allowed_reason: If is_allowed=false, why not?
        """
        from vertexai.generative_models import GenerationConfig

        prompt = self._build_intent_interpretation_prompt(player_input, context)

        # Define schema for structured output
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "intent": {"type": "STRING"},
                "is_valid": {"type": "BOOLEAN"},
                "is_allowed": {"type": "BOOLEAN"},
                "invalid_reason": {"type": "STRING", "nullable": True},
                "not_allowed_reason": {"type": "STRING", "nullable": True},
            },
            "required": ["intent", "is_valid", "is_allowed"],
        }

        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.7,
        )

        try:
            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )
            parsed = json.loads(response.text)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"Intent interpretation JSON parsing error: {e}")
            # Return safe default: invalid
            return {
                "intent": f"Interpret '{player_input}'",
                "is_valid": False,
                "is_allowed": False,
                "invalid_reason": "I don't understand that command.",
                "not_allowed_reason": None,
            }

    def generate_state_updates(
        self, intent: str, context: Dict[str, Any], interpretation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """STEP 2: Generate state updates for an allowed action.

        This is the second step of the 3-step LLM architecture.
        It ONLY generates state updates to implement the interpreted intent.
        It does NOT generate narrative.

        This should ONLY be called if is_valid=true AND is_allowed=true from Step 1.

        Args:
            intent: What the player wants to do (from Step 1)
            context: Current game context
            interpretation: Full interpretation from Step 1 (for reference)

        Returns:
            MechanicsResult as dict with:
            - state_updates: List of state changes
            - requires_dice_roll: Whether mechanics need dice
            - dice_check: Parameters for roll if needed
            - time_advancement: How much time passes
            - new_time: New game time after action
        """
        from vertexai.generative_models import GenerationConfig

        prompt = self._build_mechanics_generation_prompt(
            intent, context, interpretation
        )

        # Define schema for structured output (similar to current state_updates schema)
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "state_updates": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING"},
                            "target": {"type": "STRING", "nullable": True},
                            "params": {
                                "type": "OBJECT",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["type", "params"],
                    },
                },
                "requires_dice_roll": {"type": "BOOLEAN"},
                "dice_check": {
                    "type": "OBJECT",
                    "additionalProperties": True,
                    "nullable": True,
                },
                "time_advancement": {"type": "STRING", "nullable": True},
                "new_time": {"type": "STRING", "nullable": True},
            },
            "required": ["state_updates", "requires_dice_roll"],
        }

        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.7,
        )

        try:
            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )
            parsed = json.loads(response.text)

            # Post-process to fill missing params
            parsed = self._fill_missing_params(parsed, context)

            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"Mechanics generation JSON parsing error: {e}")
            # Return safe default: no changes
            return {
                "state_updates": [],
                "requires_dice_roll": False,
                "dice_check": None,
                "time_advancement": "1 minute",
                "new_time": None,
            }

    def check_world_events(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any autonomous world events should trigger.

        This is called each turn after player actions to handle:
        - Scripted events (like Planetfall ship explosion)
        - NPC autonomous movement (like Blather wandering)
        - Time-based or condition-based triggers

        Args:
            context: Current game context including game_scripts and turn_count

        Returns:
            Dictionary with:
            - events_triggered: Boolean, whether any events happened
            - state_updates: List of state changes
            - narrative: Narration for triggered events (empty string if none)
        """
        from vertexai.generative_models import GenerationConfig

        game_scripts = context.get("game_scripts")
        if not game_scripts:
            return {"events_triggered": False, "state_updates": [], "narrative": ""}

        prompt = self._build_world_events_prompt(context)

        # Define schema for structured output
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "events_triggered": {"type": "BOOLEAN"},
                "state_updates": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING"},
                            "target": {"type": "STRING", "nullable": True},
                            "params": {
                                "type": "OBJECT",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["type", "params"],
                    },
                },
                "narrative": {"type": "STRING"},
            },
            "required": ["events_triggered", "state_updates", "narrative"],
        }

        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.7,
        )

        try:
            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )
            parsed = json.loads(response.text)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"World events JSON parsing error: {e}")
            # Return safe default: no events
            return {
                "events_triggered": False,
                "state_updates": [],
                "narrative": "",
            }

    def _build_location_prompt(
        self,
        location: Dict[str, Any],
        items: List[Any],
        npcs: List[Any],
        player_context: Optional[Dict[str, Any]],
        world_context: Optional[Dict[str, Any]],
        lighting_info: Optional[Dict[str, Any]] = None,
        cached_descriptions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for location description."""
        game_time = (
            player_context.get("attributes", {}).get("game_time")
            if player_context
            else None
        )
        if not game_time and lighting_info:
            # Try to get from lighting_info if not in player_context
            game_time = "Unknown"

        def context_if_present(label: str, key: str) -> str:
            if world_context:
                if value := world_context.get(key, None):
                    logger.debug("context value", f"{label}: {json.dumps(value)}")
                    return f"{label}: {json.dumps(value)}"
            return ""

        prompt = f"""You are a Dungeon Master describing a location.

Location: {location.get("name", "Unknown")}
Attributes: {location.get("attributes", {})}

⏰ CURRENT TIME (for lighting only): {player_context.get("game_time") if player_context else "Unknown"}
🚨 CRITICAL LIGHTING RULES - DO NOT OVERDO LIGHTING:
- Use time to DETERMINE LIGHTING: Morning/Afternoon = bright; Evening = dusk; Night = darkness
- DO NOT mention clock times like "at 5:15 PM" in the description!
- 🚨 LIGHTING MUST BE MINIMAL: Maximum 3-4 words, mentioned ONCE at most
- The room/objects are the focus, NOT the lighting
- Acceptable: "The bright kitchen...", "The dimly lit corridor...", "The kitchen..."
- UNACCEPTABLE: "bathed in soft light", "awash in gentle light", "streaming through windows"
- If it's daytime and there are no visibility issues, you can often SKIP mentioning lighting entirely
- Only emphasize lighting if it's unusual (pitch black, sunset, candlelight) or affects gameplay
"""

        if world_context:
                prompt = prompt + f"""
Game context:
 {context_if_present("Author", "author")}
 {context_if_present("Instructions", "dm_instructions")}
 {context_if_present("Setting", "setting")}
 {context_if_present("Tone", "tone")}
"""

        # Add cached descriptions if available
        if cached_descriptions:
            prompt += "\n📝 PREVIOUSLY GENERATED DESCRIPTIONS (for reference/consistency):\n\n"

            location_cache = cached_descriptions.get("location")
            if location_cache:
                cached_desc = location_cache.get("description", "")
                cached_turn = location_cache.get("turn", "unknown")
                prompt += f"🏛️ Location Description (from turn {cached_turn}):\n"
                prompt += f'"{cached_desc}"\n\n'

            items_cache = cached_descriptions.get("items", {})
            if items_cache:
                prompt += "📦 Item Descriptions (previously seen):\n"
                for item_id, item_cache in items_cache.items():
                    item_name = item_cache.get("name", item_id)
                    cached_desc = item_cache.get("description", "")
                    cached_turn = item_cache.get("turn", "unknown")
                    prompt += f'  - {item_name} (turn {cached_turn}): "{cached_desc}"\n'
                prompt += "\n"

            npcs_cache = cached_descriptions.get("npcs", {})
            if npcs_cache:
                prompt += "👤 NPC Descriptions (previously seen):\n"
                for npc_id, npc_cache in npcs_cache.items():
                    npc_name = npc_cache.get("name", npc_id)
                    cached_desc = npc_cache.get("description", "")
                    cached_turn = npc_cache.get("turn", "unknown")
                    prompt += f'  - {npc_name} (turn {cached_turn}): "{cached_desc}"\n'
                prompt += "\n"

            prompt += """⚠️  CRITICAL INSTRUCTIONS FOR USING CACHED DESCRIPTIONS:

1. **These are HINTS for consistency** - They show how you described things before
2. **Check CURRENT STATE first** - Things may have changed since the cached description!
   - If attributes have changed, the description MUST reflect the new state
   - Example: If deer previously had antlers but now has_antlers=false, describe it WITHOUT antlers
3. **You can abbreviate for return visits** - If player has seen this location before:
   - Brief descriptions are fine: "You're back in the Grand Hall. The skeleton guard is still here."
   - No need to repeat full atmospheric descriptions unless something changed
4. **Maintain consistency** - If you described something a certain way before, keep that detail
   - Example: If you said the genie has "golden armlets", keep mentioning golden armlets
5. **Highlight changes** - If state changed, explicitly note it:
   - "The deer looks different now - its antlers are gone!"
   - "The torch that was here before has been taken"

Use cached descriptions for CONSISTENCY and BREVITY, but always prioritize CURRENT STATE.

"""

        # Add player inventory context
        if player_context:
            inventory_items = player_context.get("inventory_items", [])
            if inventory_items:
                prompt += f"🎒 PLAYER INVENTORY (what they are carrying):\n"
                prompt += f"{', '.join(inventory_items)}\n\n"
            else:
                prompt += f"🎒 PLAYER INVENTORY: Empty (carrying nothing)\n\n"

            # Add player attributes/conditions
            player_attributes = player_context.get("attributes", {})
            if player_attributes:
                prompt += (
                    f"👤 PLAYER ATTRIBUTES (current conditions affecting perception):\n"
                )
                prompt += f"{player_attributes}\n\n"
                prompt += (
                    f"⚠️  CRITICAL - ADJUST DESCRIPTION BASED ON PLAYER ATTRIBUTES:\n"
                )
                prompt += f"Check the attributes above and adjust your description accordingly.\n"
                prompt += f"Examples (be creative with any attributes present):\n"
                prompt += f"- If 'blind: true' → Describe ONLY sounds, smells, touch, temperature. NO visual details!\n"
                prompt += (
                    f"- If 'deaf: true' → Describe visuals, smells, touch. NO sounds!\n"
                )
                prompt += f"- If 'wounded: severe' → Mention pain, difficulty moving, blood loss\n"
                prompt += (
                    f"- If 'poisoned: X' → Mention nausea, weakness, blurred vision\n"
                )
                prompt += f"- If 'terrified_of: darkness' → Emphasize fear when dark\n"
                prompt += (
                    f"- If 'covered_in: mud' → Mention how it affects vision/movement\n"
                )
                prompt += f"Be creative! Any attribute that would affect perception should change your description.\n\n"

        # Add lighting information
        if lighting_info:
            lighting_level = lighting_info.get("level", "dark")
            can_see = lighting_info.get("can_see_clearly", False)
            light_sources = lighting_info.get("light_sources", [])
            time_of_day = lighting_info.get("time_of_day", "unknown")

            prompt += f"\n🌓 LIGHTING CONDITIONS:\n"
            prompt += f"Time of day: {time_of_day}\n"
            prompt += f"Light level: {lighting_level}\n"
            prompt += f"Can see clearly: {can_see}\n"

            # Separate carried vs location-based light sources
            if light_sources:
                carried_lights = [ls for ls in light_sources if "(carried)" in ls]
                location_lights = [ls for ls in light_sources if "(here)" in ls]

                if carried_lights:
                    prompt += f"Light sources CARRIED by player: {', '.join(carried_lights)}\n"
                if location_lights:
                    prompt += f"Light sources AT THIS LOCATION (on ground): {', '.join(location_lights)}\n"

            prompt += "\n⚠️ CRITICAL - DESCRIBE BASED ON LIGHTING:\n"
            if lighting_level == "pitch_black":
                prompt += "- Player is in COMPLETE DARKNESS\n"
                prompt += "- Describe ONLY sounds, smells, feelings, and sensations\n"
                prompt += "- DO NOT describe visual details (walls, items, NPCs)\n"
                prompt += "- Mention that they cannot see anything\n"
                prompt += "- Example: 'You stand in pitch blackness, unable to see anything. The air is cold and damp. You hear water dripping in the distance.'\n"
            elif lighting_level == "dark":
                prompt += "- Player is in DARKNESS with minimal visibility\n"
                prompt += "- Describe only vague shapes and outlines\n"
                prompt += "- Focus on sounds, smells, and non-visual sensations\n"
                prompt += "- Cannot identify specific details of items or NPCs\n"
                prompt += "- Example: 'In the darkness, you can barely make out the shape of walls around you. Strange sounds echo from ahead.'\n"
            elif lighting_level == "dim":
                prompt += "- Player has DIM LIGHTING from torch/lantern (check if CARRIED or AT LOCATION)\n"
                prompt += "- Can see general features and nearby objects\n"
                prompt += "- Details are somewhat unclear in the shadows\n"
                prompt += "- Describe flickering shadows and limited visibility\n"
                prompt += "- If light source is CARRIED: 'By the flickering light of your torch, you see ancient stone walls.'\n"
                prompt += "- If light source is AT LOCATION: 'A torch on the ground illuminates ancient stone walls with flickering light.'\n"
            else:  # bright
                prompt += "- Player has GOOD LIGHTING\n"
                prompt += "- Can see all details clearly\n"
                prompt += "- Describe everything normally\n"

            prompt += "\n"

        # CRITICAL: Make current state very explicit to override cached descriptions
        prompt += "\n" + "=" * 80 + "\n"
        prompt += "⚠️  CURRENT STATE OF THIS LOCATION (THIS IS REALITY - USE THIS, NOT CACHED DESCRIPTIONS)\n"
        prompt += "=" * 80 + "\n\n"

        if items and lighting_info and lighting_info.get("can_see_clearly", False):
            item_names = [item.get("name") for item in items]
            prompt += f"✅ ITEMS CURRENTLY AT THIS LOCATION: {item_names}\n"
            prompt += f"Item details: {items}\n\n"
        elif items and lighting_info:
            item_names = [item.get("name") for item in items]
            prompt += f"✅ ITEMS CURRENTLY AT THIS LOCATION (but may not be visible due to darkness): {item_names}\n\n"
        else:
            prompt += f"✅ ITEMS CURRENTLY AT THIS LOCATION: [] (NONE - location is empty of items)\n\n"

        if npcs and lighting_info and lighting_info.get("can_see_clearly", False):
            npc_names = [npc.get("name") for npc in npcs]
            prompt += f"✅ NPCs CURRENTLY AT THIS LOCATION: {npc_names}\n"
            prompt += f"NPC details: {npcs}\n\n"
        elif npcs and lighting_info:
            npc_names = [npc.get("name") for npc in npcs]
            prompt += f"✅ NPCs CURRENTLY AT THIS LOCATION (but may not be visible due to darkness): {npc_names}\n\n"
        else:
            prompt += (
                f"✅ NPCs CURRENTLY AT THIS LOCATION: [] (NONE - no NPCs here)\n\n"
            )

        # Add ZIL interpretation hints if ZIL attributes are present
        prompt += self._build_zil_interpretation_hints(items, location)

        # Add explicit warning about cached descriptions
        if cached_descriptions and cached_descriptions.get("location"):
            prompt += """🚨 CRITICAL WARNING ABOUT CACHED DESCRIPTION:
The cached location description above may mention items or NPCs that are NO LONGER HERE.
You MUST describe ONLY what is in the "CURRENT STATE" section above.

Examples of what to do:
- Cached description says "a sword lies on the ground" but CURRENT ITEMS is []
  → DO NOT mention the sword. It has been taken. Describe the location without it.
- Cached description mentions "a deer stands nearby" but CURRENT NPCs is []
  → DO NOT mention the deer. It has left. Describe the location without it.
- Cached description from turn 2, now it's turn 50
  → Use cached description for consistency of style, but CHECK CURRENT STATE for what's actually here.

IF AN ITEM OR NPC WAS IN THE CACHED DESCRIPTION BUT IS NOT IN THE CURRENT STATE LISTS ABOVE,
IT HAS BEEN REMOVED. DO NOT DESCRIBE IT AS BEING PRESENT.

"""

        prompt += "=" * 80 + "\n\n"

        if location.get("connections"):
            exits = [d for d, loc in location["connections"].items() if loc]
            prompt += f"Exits: {', '.join(exits)}\n"

        prompt += """
Generate a vivid, immersive description of this location (2-4 sentences).

CRITICAL RULES:
1. Base your description on the lighting level above. If it's dark/pitch_black, don't describe visual details!
2. DO NOT describe the player as holding, gripping, wielding, or carrying items UNLESS they are in the PLAYER INVENTORY section above.
3. Items listed as "Items here" are on the GROUND, not in the player's hands.
4. Only mention items in the player's possession if they appear in the "🎒 PLAYER INVENTORY" section.
5. LIGHT SOURCES: Only say "your torch" or "your lantern" if it appears under "Light sources CARRIED by player".
   If it appears under "Light sources AT THIS LOCATION (on ground)", describe it as being at the location, not possessed.
   Example: "A torch on the ground casts flickering light" NOT "By the light of your torch"
6. **NPC DESCRIPTIONS - CHECK ATTRIBUTES**: When describing NPCs, check their "attributes" field in "NPC details" above.
   - If an NPC has "has_antlers: false", do NOT describe them as having antlers
   - If an NPC has "wounded: true", describe them as wounded
   - Always use the CURRENT attribute values, not default/expected ones
   - Example: A deer with "has_antlers: false" should be "an antlerless white deer", not "a deer with delicate antlers"
7. **EXITS**: Integrate available exits naturally into your description. Be creative - don't just list them.
   - Good: "Passages lead north and south, while a narrow corridor branches east."
   - Good: "The hallway continues to the north, and a door stands to the west."
   - Bad: "Exits: north, south, east"
   - You may omit hidden or secret exits if appropriate to the narrative.

Write in second person (you see..., you notice..., you feel..., you hear...).
Be concise but evocative.
"""

        return prompt

    def _build_narrative_prompt(
        self,
        player_input: str,
        intent: str,
        context: Dict[str, Any],
        action_metadata: Optional[Dict[str, Any]] = None,
        state_updates: Optional[List[Dict[str, Any]]] = None,
        is_valid: bool = True,
    ) -> str:
        """Build prompt for generating narrative based on current state.

        This is called AFTER state updates, so context reflects actual current state.
        state_updates shows WHAT CHANGED so you can narrate the transition.
        """
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})
        inventory_items = player.get("inventory", [])

        # Format conversation history for consistency
        conversation_history = context.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_text = "\n📜 RECENT CONVERSATION (for consistency):\n"
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"\nTurn -{len(conversation_history) - i + 1}:\n"
                history_text += f"  Player: {turn.get('player_input', '')}\n"
                narrative = turn.get("narrative", "")
                if narrative:
                    # Keep full narrative for consistency (no truncation)
                    history_text += f"  You (DM): {narrative}\n"
            history_text += "\n⚠️  MAINTAIN CONSISTENCY:\n"
            history_text += "1. If you previously described specific details (colors, numbers, materials), keep them consistent\n"
            history_text += "2. Don't contradict your earlier descriptions\n"
            history_text += (
                "3. If player asks the same question again, give the same answer\n"
            )
            history_text += "4. Example: If you said '5 planks' before, don't change it to '3 planks' now\n\n"

        # Check if this is a dialogue/conversation action
        player_input_lower = player_input.lower()
        dialogue_keywords = [
            "talk to",
            "speak to",
            "speak with",
            "ask",
            "greet",
            "tell",
            "say to",
            "chat with",
            "converse",
            "question",
        ]
        is_dialogue_action = any(
            keyword in player_input_lower for keyword in dialogue_keywords
        )

        prompt = f"""You are a Dungeon Master narrating the outcome of a player's action.
{self._build_world_context(context)}
WHAT THE PLAYER DID: "{player_input}"
INTERPRETED INTENT: {intent}

CURRENT GAME STATE (after action was processed):

Location: {location.get("name", "Unknown")}
Location details: {location.get("attributes", {})}

⏰ CURRENT TIME (for lighting only): {context.get("game_time", "Unknown")}
CRITICAL LIGHTING RULES:
- Use time to DETERMINE LIGHTING, but DO NOT MENTION THE TIME in your narrative!
- Morning/Afternoon = bright/daytime lighting; Evening = dusk; Night = darkness
- DO NOT include clock times like "at 5:15 PM" in the narrative!
- 🚨 ONLY mention lighting when RELEVANT to the action:
  ✅ Mention lighting for: looking around, entering new areas, examining distant objects, searching for things
  ❌ DON'T mention lighting for: eating, drinking, using items, talking, simple inventory actions
  - Example - eating garlic: Focus on TASTE and SMELL, not "bright morning light"
  - Example - examining a carried item: Focus on THE ITEM, not ambient lighting
  - Example - entering a new room: Lighting IS relevant - describe it
- Keep lighting descriptions subtle and contextual, not overwhelming the main action

Items at this location (on the ground): {[item.get("name") for item in items] if items else "none"}
Item details: {items if items else "none"}
{self._format_container_contents(context.get("container_contents", {}))}

NPCs at this location: {[npc.get("name") for npc in npcs] if npcs else "none"}
NPC details: {npcs if npcs else "none"}

Player inventory (what they are carrying): {[item.get("name") for item in inventory_items] if inventory_items else "nothing"}
Inventory details: {inventory_items if inventory_items else "empty"}
"""

        # Add ZIL interpretation hints if ZIL attributes are present
        # Include items at location, inventory items, AND items in open containers
        all_relevant_items = list(items) + list(inventory_items)

        # Also add items from open containers
        container_contents = context.get("container_contents", {})
        for container_id, contents in container_contents.items():
            if contents:
                all_relevant_items.extend(contents)

        prompt += self._build_zil_interpretation_hints(all_relevant_items, location)

        # Add state updates section (CRITICAL for narrating what happened)
        if state_updates:
            prompt += "\n🔄 WHAT CHANGED (state updates that were applied):\n"
            prompt += "CRITICAL: Use these to understand what actually happened and narrate it!\n\n"
            for i, update in enumerate(state_updates, 1):
                update_type = update.get("type", "unknown")
                params = update.get("params", {})
                prompt += f"{i}. {update_type}: {params}\n"

            prompt += "\nExamples of how to narrate state updates:\n"
            prompt += "- 'remove_from_inventory' (garlic) → 'You eat the garlic. It's pungent but filling.'\n"
            prompt += "- 'add_to_inventory' (sword) → 'You pick up the sword. It feels well-balanced.'\n"
            prompt += (
                "- 'move_item' (key, door) → 'You insert the key into the lock.'\n"
            )
            prompt += "- 'update_item_attribute' (door, is_open=true) → 'The door swings open.'\n\n"

        prompt += history_text

        # Add NPC dialogue instructions if this is a conversation action
        if is_dialogue_action and npcs:
            prompt += """

🗣️ NPC DIALOGUE GENERATION - CRITICAL INSTRUCTIONS:

The player is trying to communicate with an NPC. You MUST generate actual spoken dialogue from the NPC!

DIALOGUE REQUIREMENTS:
1. **Include quoted speech** from the NPC using quotation marks
   Example: The genie's eyes twinkle. "Greetings, mortal," it intones...

2. **NPC explains their role/purpose/mechanics** based on their attributes
   - Check NPC attributes for: personality, wishes_remaining, special_powers, role, etc.
   - Genies should explain wish rules and limitations
   - Guards might warn or threaten
   - Merchants might offer trades
   - Quest-givers might explain tasks

3. **Use NPC personality** from attributes to determine speech style
   - "mischievous" → playful, teasing language
   - "hostile" → threatening, aggressive language
   - "wise" → sage-like, thoughtful speech
   - "timid" → nervous, uncertain speech

4. **Make dialogue informative AND atmospheric**
   - Reveal game mechanics through character voice
   - Provide hints about how to interact with this NPC
   - Stay in character - let personality shine through

EXAMPLES OF GOOD NPC DIALOGUE:

Example 1 - Genie (from attributes: wishes_remaining=3, personality=mischievous):
"The Ancient Genie's form solidifies before you, its blue ethereal body shimmering in the dappled sunlight. 'Ah, another visitor!' the genie exclaims, its voice resonating like distant thunder. 'I am bound by ancient law to grant thee three wishes. But choose thy words carefully, mortal—I grant exactly what is asked, no more, no less.' The genie grins mischievously. 'The cosmic balance must be maintained.'"

Example 2 - Skeleton Guard (from attributes: hostility=aggressive):
"The Skeletal Guard's glowing green eyes fix upon you. 'Foolish trespasser,' it rasps, its voice like grinding bones. 'None may pass while I stand guard. Turn back now, or face my blade!'"

Example 3 - Merchant (from attributes: personality=greedy):
"The merchant eyes you shrewdly. 'Well met, traveler! Looking to lighten your purse, eh?' He gestures at his wares. 'I've got the finest goods in the realm—for the right price, of course.'"

❌ BAD (No dialogue): "The genie appears before you, shimmering and ready to assist."
✅ GOOD (With dialogue): "The genie materializes with a flourish. 'Three wishes I grant, but heed this well: I fulfill thy request precisely as spoken!'"

Remember: NPCs are characters, not furniture. Give them a VOICE!
"""

        # Add action context if available
        if action_metadata:
            prompt += "\n\n📋 ACTION CONTEXT (what changed):\n"

            if action_metadata.get("item_was_at_location"):
                item_id = action_metadata.get("item_picked_from_ground")
                prompt += f"- Item '{item_id}' was PICKED UP FROM THE GROUND (not from pack/inventory)\n"
                prompt += f"- CRITICAL: Say 'you pick it up', 'you grab it', 'you take it', etc.\n"
                prompt += (
                    f"- NEVER say: 'you take it from your pack' or 'from your belt'\n"
                )

            if action_metadata.get("item_was_in_inventory"):
                item_id = action_metadata.get("item_dropped_from_inventory")
                prompt += (
                    f"- Item '{item_id}' was DROPPED FROM INVENTORY (not picked up)\n"
                )
                prompt += f"- Say: 'you drop it on the ground', 'you place it down', 'you set it aside', etc.\n"
                prompt += f"- NEVER say: 'you pick up' or 'you grab'\n"

        # Add failed action guidance if action was invalid
        if not is_valid:
            prompt += """

🚨 ACTION FAILED - NARRATE THE FAILURE:
The action was marked as INVALID (is_valid: false).
DO NOT describe the action succeeding!

Instead, explain WHY the action failed:
- If trying to regurgitate something not swallowed: "You gag and cough, but nothing comes up. You haven't swallowed any [item]."
- If trying to take non-existent item: "You look around, but don't see any [item] here."
- If trying impossible physics: "That's physically impossible / doesn't make sense."
- If blocked by game rules: Explain the constraint (locked door, too heavy, etc.)

The state didn't change because the action failed - narrate the FAILURE, not success.
"""

        prompt += """


🎯 YOUR TASK:
Generate a vivid, engaging narrative (2-4 sentences) describing what just happened.
- Narrate the outcome of the player's action based on the CURRENT STATE above
- The action has already been processed, describe the result
- Write in second person (you do..., you see..., you notice...)
- Be dramatic and immersive"""

        if not is_valid:
            prompt += (
                "\n- ACTION FAILED: Explain WHY it failed, don't describe it succeeding"
            )

        prompt += """

⚠️  CRITICAL RULES - DESCRIBE ONLY WHAT EXISTS IN CURRENT STATE:
1. Items: Only mention items that appear in "Items at this location" or "Player inventory"
2. NPCs: Only mention NPCs that appear in "NPCs at this location"
3. Light sources: Only mention torches/lanterns if they appear in the lists above
4. Inventory: Only say player is carrying/holding items if they are in "Player inventory"
5. DO NOT invent items, NPCs, or details that aren't in the current state
6. If an item/NPC was just picked up/dropped, it should be in the correct list now
7. **MOVEMENT ACTIONS**: If player moved locations, describe ARRIVING at the current location.
   DO NOT describe what was at the previous location. The NPCs/items listed are at the NEW location.

Examples of CORRECT narration:
- Movement: "You head south through the forest. As you enter the clearing, you notice a white deer grazing peacefully."
- Item pickup: "You reach down and pick up the sword. It now rests securely in your belt."
- Item drop: "You toss the sword aside. It clatters to the ground at your feet."
- NPC at location: "The guard watches you warily as you approach."
- NPC not present: "You look around the empty chamber."

Examples of WRONG narration for movement:
- ❌ "You leave the chamber. The guard watches you go." (guard is at NEW location, not old one)
- ❌ "The deer observes as you depart." (deer is at destination, can't watch you leave origin)

Return ONLY the narrative text (2-4 sentences), nothing else."""

        return prompt

    def _build_action_result_prompt(
        self, action: str, result: Dict[str, Any], game_context: Dict[str, Any]
    ) -> str:
        """Build prompt for action result narration."""
        prompt = f"""You are a Dungeon Master narrating the result of a player's action.

Player action: {action}
Result: {result}
Context: {game_context}

Generate a narrative description (1-3 sentences) of what happens.
Write in second person.
Be dramatic and engaging.
If there was combat, describe the action vividly.
"""

        return prompt

    def _build_simple_action_prompt(
        self, player_input: str, context: Dict[str, Any]
    ) -> str:
        """Build a simplified prompt for common actions (used on retry)."""
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        inventory = context.get("player", {}).get("inventory", [])

        prompt = f"""You are a DM. The player says: "{player_input}"

AVAILABLE ITEMS HERE: {[item.get("name") for item in items]}
ITEMS IN INVENTORY: {[item.get("name") for item in inventory]}
NPCS HERE: {[npc.get("name") for npc in npcs]}
LOCATION: {location.get("name")}

Common action patterns:
- "take X" / "get X" → {{"type": "add_to_inventory", "params": {{"item_id": "item_id"}}}}
- "drop X" / "place X down" → {{"type": "remove_from_inventory", "params": {{"item_id": "item_id"}}}}
- "eat X" / "drink X" / "swallow X" → {{"type": "consume_item", "params": {{"item_id": "item_id"}}}}
- "go north/south/east/west" → {{"type": "move_player", "params": {{"destination": "location_id"}}}}
- "attack X" → {{"type": "trigger_combat", "params": {{"target_npc_id": "npc_id"}}}}

Return VALID JSON only:
{{
  "intent": "brief description",
  "is_valid": true,
  "state_updates": [list of updates],
  "narrative_response": "2 sentence response",
  "requires_dice_roll": false
}}

CRITICAL: Ensure JSON is valid. Use correct IDs from lists above."""

        return prompt

    def _build_combat_narration_prompt(self, combat_result: Dict[str, Any]) -> str:
        """Build prompt for narrating combat outcome."""
        player_attack = combat_result.get("player_attack", {})
        npc_attack = combat_result.get("npc_attack")

        prompt = f"""You are a Dungeon Master narrating the outcome of a combat round.

FULL COMBAT ROUND RESULTS (JSON):
{json.dumps(combat_result, indent=2)}

COMBAT SEQUENCE:
1. Player's Attack:
   - Hit: {"YES" if player_attack.get("hit") else "NO"}
   - Damage: {player_attack.get("damage_total", 0)}
   - Target: {player_attack.get("target_name", "enemy")}
   - Target HP After: {player_attack.get("target_hp", 0)}/{player_attack.get("target_max_hp", 0)}
   - Target Killed: {"YES" if player_attack.get("target_dead") else "NO"}

2. Enemy's Counterattack:
"""

        if npc_attack:
            prompt += f"""   - Hit: {"YES" if npc_attack.get("hit") else "NO"}
   - Damage: {npc_attack.get("damage_total", 0)}
   - Your HP After: {npc_attack.get("target_hp", 0)}/{npc_attack.get("target_max_hp", 0)}
   - You Died: {"YES" if npc_attack.get("target_dead") else "NO"}
"""
        else:
            prompt += """   - Enemy was killed, no counterattack
"""

        prompt += """
Your task as DM:
1. Narrate BOTH attacks in vivid, dramatic combat language (3-4 sentences total)
2. Describe the exchange blow-by-blow:
   - First describe the player's attack and its impact
   - Then describe the enemy's counterattack (if it survived) and its impact
3. ALWAYS prompt the player for their next specific action

Example narrations:
- Both hit: "Your sword slashes across the guard's chest, drawing blood! The guard staggers but recovers quickly, retaliating with a vicious strike that catches you in the shoulder. You both stand wounded, circling each other. What do you do next? (attack, defend, cast spell, flee, or something else)"
- Player hits, enemy misses: "Your blade finds its mark, cutting deep into the skeleton's ribs! It lashes out wildly with its rusty sword, but you duck beneath the swing. The undead creature is badly wounded. What's your next move?"
- Player misses, enemy hits: "You swing wide, missing the goblin entirely! It capitalizes on your mistake, its dagger finding a gap in your defenses and piercing your side. You wince in pain. What do you do?"
- Player kills enemy: "Your weapon strikes true, delivering a devastating blow! The creature collapses lifeless at your feet. Victory is yours!"

IMPORTANT: Always end with a clear prompt for the player's next action (unless enemy is dead).

Write your narration (3-4 sentences):
"""

        return prompt

    def _build_npc_actions_prompt(
        self, npc_actions: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Build prompt for narrating NPC actions with game state context."""
        attacks = npc_actions.get("npc_attacks", [])
        chases = npc_actions.get("npc_chases", [])

        # Extract location information
        location = context.get("location", {})
        location_name = location.get("name", "unknown location")
        location_desc_hints = location.get("attributes", {}).get(
            "description_hints", ""
        )

        # Determine the scenario type
        is_chase_attack = bool(chases and attacks)
        is_unprovoked_attack = bool(attacks and not chases)

        if is_chase_attack:
            prompt = f"""You are the Dungeon Master in an adventure game. An NPC is CHASING the player and attacking.

IMPORTANT CONTEXT: This NPC was already engaged in combat with the player. The player fled, and the NPC pursued them to their new location and is continuing the fight.

CURRENT LOCATION: {location_name}
Location description hints: {location_desc_hints}

Your task:
1. Narrate the PURSUIT and continued attack in vivid, dramatic combat language (3-5 sentences)
2. Emphasize that the NPC FOLLOWED the player (don't say it "suddenly animates" or "awakens")
3. Describe the NPC catching up and pressing the attack
4. Convey relentless pursuit, danger, and the desperation of being hunted
5. End with "What do you do?" to prompt the player

Tone Guidelines:
- This is a CONTINUATION of combat, not a first encounter
- The NPC is PURSUING a fleeing opponent
- Use language like "pursues", "catches up", "doesn't let you escape", "continues the assault"
- DO NOT use language suggesting this is a first encounter ("suddenly appears", "awakens", "animates for the first time")
- CRITICAL: Set the scene in the CURRENT LOCATION provided above - do not invent other locations
- Use the location description hints to inform environmental details
- Make it feel desperate and relentless
- Keep it concise but impactful (3-5 sentences max)
"""
        elif is_unprovoked_attack:
            prompt = f"""You are the Dungeon Master in an adventure game. NPCs have just acted unprovoked.

CURRENT LOCATION: {location_name}
Location description hints: {location_desc_hints}

Your task:
1. Narrate the NPC actions in vivid, dramatic combat language (3-5 sentences)
2. Describe the attacks viscerally and their impact
3. Convey urgency, danger, and the SURPRISE of unprovoked aggression
4. End with "What do you do?" to prompt the player

Tone Guidelines:
- This is UNPROVOKED - player didn't attack first, NPCs are the aggressors
- This is likely the FIRST encounter with this NPC
- Use dramatic, visceral language for attacks
- Emphasize surprise and danger
- CRITICAL: Set the scene in the CURRENT LOCATION provided above - do not invent other locations
- Use the location description hints to inform environmental details
- Make it feel dangerous and exciting
- Keep it concise but impactful (3-5 sentences max)
"""
        else:
            # Just chases, no attacks (rare but possible if attacks missed)
            prompt = f"""You are the Dungeon Master in an adventure game. An NPC is chasing the player.

CURRENT LOCATION: {location_name}
Location description hints: {location_desc_hints}

Your task:
1. Narrate the pursuit in dramatic language (2-3 sentences)
2. Emphasize the relentless pursuit
3. End with "What do you do?" to prompt the player
"""

        # Add chase events
        if chases:
            prompt += "\nCHASE EVENTS:\n"
            for chase in chases:
                npc_name = chase.get("npc_name", "NPC")
                hp_percent = chase.get("hp_percent", 1.0) * 100
                prompt += f"- {npc_name} (HP: {hp_percent:.0f}%) pursues the player to new location\n"

        # Add attack events
        if attacks:
            prompt += "\nATTACKS:\n"
            for attack_info in attacks:
                npc_name = attack_info.get("npc_name", "NPC")
                attack = attack_info.get("attack", {})

                hit = attack.get("hit", False)
                damage = attack.get("damage_total", 0)
                target_hp = attack.get("target_hp", 0)
                target_max_hp = attack.get("target_max_hp", 1)
                target_dead = attack.get("target_dead", False)

                if hit:
                    prompt += f"\n{npc_name}:\n"
                    prompt += f"  - Attack: HIT\n"
                    prompt += f"  - Damage dealt: {damage}\n"
                    prompt += f"  - Player HP now: {target_hp}/{target_max_hp}\n"
                    if target_dead:
                        prompt += f"  - Player is DEAD\n"
                else:
                    prompt += f"\n{npc_name}:\n"
                    prompt += f"  - Attack: MISS\n"

        prompt += """

CRITICAL INSTRUCTIONS:
- Describe ALL the events above in a single cohesive narrative
- If multiple NPCs, weave their actions together naturally
- Use second person ("You see...", "The wolf lunges at you...")
- Be vivid and dramatic but concise (3-5 sentences)
- If player died, make it dramatic and final
- ALWAYS end with "What do you do?" (unless player is dead)

Generate the narrative now:"""

        return prompt

    def _build_container_contents_prompt(
        self, container: Dict[str, Any], contents: list, context: Dict[str, Any]
    ) -> str:
        """Build prompt for describing items in/on a container.

        Args:
            container: Container item dict with id, name, attributes
            contents: List of item dicts inside the container
            context: Full game context (lighting, player attributes, location, etc.)

        Returns:
            Prompt for generating natural prose description
        """
        container_name = container.get("name", "container")
        container_type = container.get("attributes", {}).get("type", "container")

        # Determine preposition based on container type
        preposition = (
            "on"
            if "table" in container_name.lower() or "surface" in container_type
            else "in"
        )

        items_list = []
        for item in contents:
            item_name = item.get("name", "unknown item")
            item_desc = item.get("attributes", {}).get("description_hints", "")
            items_list.append(
                f"- {item_name}" + (f" ({item_desc})" if item_desc else "")
            )

        items_text = "\n".join(items_list)

        # Extract context information
        lighting_info = context.get("lighting_info", {})
        lighting_level = lighting_info.get("level", "bright")

        player = context.get("player", {})
        player_attrs = player.get("attributes", {})
        location = context.get("location", {})
        location_name = location.get("name", "Unknown")

        prompt = f"""You are a Dungeon Master describing items in a container.

CURRENT CONTEXT:
Location: {location_name}
Lighting: {lighting_level}
Player attributes: {player_attrs}

CONTAINER: {container_name}
ITEMS {preposition.upper()} THE {container_name.upper()}:
{items_text}

🚨 CRITICAL VISIBILITY RULES - Check ALL conditions that affect vision:

1. LIGHTING:
   - If lighting is "dark" or "pitch_black": Return EMPTY STRING - cannot see
   - If lighting is "dim": Items barely visible, hard to see details

2. PLAYER CONDITIONS (check player attributes):
   - If player has "blind": true → Return EMPTY STRING - cannot see
   - If player has "blindfolded": true → Return EMPTY STRING - cannot see
   - If player has "blurred_vision" or similar → Mention items are blurry/hard to make out
   - If player has vision-affecting curse → Adjust description accordingly

3. IF ANY CONDITION PREVENTS VISION: Return EMPTY STRING (no description at all)

Your task:
Generate 1-2 concise, natural sentences describing what's {preposition} the {container_name}.

Guidelines:
- Use vivid, evocative language that matches Zork's atmospheric style
- Mention ALL items listed above (unless cannot see them)
- Use natural phrasing like "On the table is...", "Inside the chest you see...", "Resting atop the surface..."
- Incorporate description hints when available (e.g., "elongated brown sack, smelling of hot peppers")
- Keep it concise but atmospheric
- Do NOT add items that aren't in the list above

Examples of good descriptions:
- "On the table is an elongated brown sack, smelling of hot peppers, and a glass bottle containing water."
- "Inside the trophy case gleams a jewel-encrusted egg and an ancient platinum bar."
- "Resting on the altar you see a leather-bound book and a silver chalice."

Generate ONLY the description (no preamble, no explanation). If cannot see, return NOTHING:"""

        return prompt

    def _build_zil_interpretation_hints(self, items: list, location: Optional[Dict] = None) -> str:
        """Build ZIL interpretation hints if any entities have ZIL attributes.

        Args:
            items: List of item dicts to check for ZIL attributes
            location: Optional location dict to check for ZIL attributes

        Returns:
            ZIL interpretation guidance string, or empty if no ZIL attributes found
        """
        # Check if any items or location have ZIL attributes
        has_zil = False
        entities_to_check = list(items)
        if location:
            entities_to_check.append(location)

        for entity in entities_to_check:
            attrs = entity.get("attributes", {})
            if any(key.startswith("zil_") for key in attrs.keys()):
                has_zil = True
                break

        if not has_zil:
            return ""

        return """

📜 ZIL INTERPRETATION GUIDE (Zork Implementation Language):
This world was converted from original Infocom ZIL source code. Items and locations may have special ZIL attributes:

🔑 CRITICAL - zil_adjectives:
- These are DESCRIPTIVE adjectives from the original game
- ALWAYS incorporate these into your descriptions
- Examples:
  - zil_adjectives: ["BOARDED"] → door is boarded up, cannot be opened
  - zil_adjectives: ["RUSTY", "IRON"] → describe as "rusty iron gate"
  - zil_adjectives: ["ELONGATED", "BROWN"] → "elongated brown sack"

🔧 zil_action and zil_action_code:
- Indicates the item/location has special behavior (custom ZIL function)
- If zil_action_code is present, it contains the actual ZIL logic
- Interpret the ZIL code to understand behavior:

  ZIL CODE INTERPRETATION GUIDE:
  - (VERB? OPEN) → checks if player is trying to OPEN
  - (VERB? BURN) → checks if player is trying to BURN
  - (VERB? MUNG) → checks if player is trying to DAMAGE/DESTROY
  - (TELL "text" CR) → prints message to player
  - (COND ...) → conditional statements (if/else)

  EXAMPLE - Front Door:
  zil_action_code: (COND ((VERB? OPEN) (TELL "The door cannot be opened." CR)) ...)
  → This means: If player tries to OPEN, respond "The door cannot be opened."
  → Therefore: Door is BLOCKED/BOARDED and cannot be opened
  → Description should reflect this: "The front door is boarded shut"

  EXAMPLE - Trap Door:
  zil_action_code: (COND ((VERB? OPEN) (COND (<FSET? ,TRAP-DOOR ,OPENBIT> ...) ...)))
  → This means: Opening has complex conditions (might need carpet removed first)
  → Description: Mention it's concealed or requires something to access

- If zil_action is present but no zil_action_code:
  - Item has custom behavior, but details not provided
  - Describe cautiously, imply special/unusual properties

🏷️ zil_flags:
- Technical flags from ZIL (we already converted important ones to is_visible, etc.)
- Usually you can ignore these, but they may provide additional context

⚠️ COMMON ZIL PATTERNS:
- If zil_adjectives contains "BOARDED" → describe as boarded up, imply it's blocked
- If zil_adjectives contains "LOCKED" → describe as locked
- If zil_action is present → there's custom behavior, describe cautiously
- If is_visible: false → item is hidden (already handled)

REMEMBER: zil_adjectives are DESCRIPTIVE FACTS, not suggestions. Use them!
"""

    def _build_world_context(self, context: Dict[str, Any]) -> str:
        """Build world context and DM instructions if present."""
        world_ctx = context.get("world_context")
        if not world_ctx:
            return ""

        title = world_ctx.get("title", "")
        author = world_ctx.get("author", "")
        intro = world_ctx.get("intro", "")
        setting = world_ctx.get("setting", "")
        instructions = world_ctx.get("dm_instructions", [])
        tone = world_ctx.get("tone", "")

        instructions_text = "\n".join(f"- {inst}" for inst in instructions)

        author_line = f"\nAuthor/Source: {author}" if author else ""
        intro_section = f"\n\nStory Opening (what the player saw at game start):\n{intro}" if intro else ""
        tone_line = f"\nTone: {tone}" if tone else ""

        return f"""
🌍 WORLD CONTEXT - "{title}"{author_line}{intro_section}

Setting: {setting}{tone_line}

DM INSTRUCTIONS (follow these for this world):
{instructions_text}
"""

    def _format_container_contents(self, container_contents: Dict[str, Any]) -> str:
        """Format container contents for display in prompts.

        Args:
            container_contents: Dict mapping container_id -> list of items inside

        Returns:
            Formatted string showing contents of open containers
        """
        if not container_contents:
            return ""

        lines = []
        lines.append("\n🚨 Container contents (items inside open containers):")
        lines.append("⚠️  CRITICAL: You MUST mention these items in your narrative!")
        lines.append("   - If player just OPENED a container: Describe what they see inside as part of your response")
        lines.append("   - If container was already open: Mention contents when relevant to the action")
        lines.append(
            "   Use natural language: 'Inside you see...', 'The bag contains...', 'On the table is...', etc."
        )

        for container_id, contents in container_contents.items():
            if contents:
                lines.append(f"  Inside {container_id}:")
                for item in contents:
                    lines.append(
                        chr(10).join(
                            [
                                f"  - {item.get('name')} (ID: {item.get('id')})"
                                + (
                                    f" - {item.get('description')}"
                                    if item.get("description")
                                    else ""
                                )
                                + (
                                    f" - Attributes: {item.get('attributes')}"
                                    if item.get("attributes")
                                    else ""
                                )
                            ]
                        )
                    )
        return "\n".join(lines)

    def _build_plot_instructions(self, context: Dict[str, Any]) -> str:
        """Build plot management instructions if a plot is active."""
        plot_info = context.get("plot")
        if not plot_info:
            return ""

        plot_config = plot_info.get("config", {})
        dm_state = plot_info.get("dm_state", {})
        all_npcs = context.get("all_npcs", {})

        plot_desc = plot_config.get("description", "")
        plot_title = plot_config.get("title", "Unnamed Plot")

        # Build list of all NPCs with locations
        npc_summary = []
        for npc_id, npc_data in all_npcs.items():
            npc_summary.append(
                f"  - {npc_data['name']} (ID: {npc_id}) at {npc_data['location']}"
            )
        npc_list = "\n".join(npc_summary) if npc_summary else "  (none)"

        return f"""
🎭 PLOT ORCHESTRATION - "{plot_title}"

PLOT DESCRIPTION (Your secret instructions as DM):
{plot_desc}

ALL NPCs IN THE WORLD (for plot management):
{npc_list}

CURRENT DM STATE (your hidden plot tracking):
{json.dumps(dm_state, indent=2) if dm_state else "{{}}"}

PLOT MANAGEMENT INSTRUCTIONS:
- You are orchestrating this plot alongside the player's immediate actions
- Use update_dm_state to track plot-relevant information (hidden from player)
- You can modify NPCs anywhere in the world, not just at player's location
- Use modify_attribute to transform NPCs when the plot demands it
- The player NEVER sees dm_state - this is YOUR private notebook
- Follow the plot description's guidance, but adapt creatively to player actions

EXAMPLES:
- Track infection: {{"type": "update_dm_state", "params": {{"path": "npc_states.wolf.infected", "value": true}}}}
- Track plot progress: {{"type": "update_dm_state", "params": {{"path": "days_until_event", "value": 5}}}}
- Transform NPC: {{"type": "modify_attribute", "target": "deer", "params": {{"attribute_path": "attributes.creature_type", "value": "undead"}}}}
"""

    def _build_puzzle_context(self, context: Dict[str, Any]) -> str:
        """Build puzzle validation context for DM prompt.

        Provides information about active puzzles at the current location,
        including valid solutions, blocked actions, and progressive hints.
        """
        location_id = context.get("player_location")
        dm_state = context.get("dm_state", {})
        puzzles = dm_state.get("puzzles", {})

        # Find unsolved puzzles at current location
        location_puzzles = [
            p
            for p in puzzles.values()
            if p.get("location") == location_id and not p.get("solved")
        ]

        if not location_puzzles:
            return ""

        lines = []
        for puzzle in location_puzzles:
            lines.append(f"\n🧩 ACTIVE PUZZLE: {puzzle['name']}")
            lines.append(f"   Type: {puzzle['type']}")
            lines.append(f"   Blocks exit: {puzzle.get('exit_direction', 'N/A')}")
            lines.append(f"   Failed attempts: {puzzle.get('failed_attempts', 0)}")

            lines.append(f"\n   ✅ VALID SOLUTIONS (player must match ONE of these):")
            requirements = puzzle.get("requirements", {})
            solutions = requirements.get("solutions", [])

            for i, sol in enumerate(solutions, 1):
                sol_type = sol.get("type")
                action_verbs = sol.get("action_verbs", [])

                if sol_type == "item_in_inventory":
                    item_id = sol.get("item_id")
                    item_name = (
                        context.get("items", {}).get(item_id, {}).get("name", item_id)
                    )
                    lines.append(
                        f"   {i}. Player has '{item_name}' (ID: {item_id}) in inventory"
                    )
                    lines.append(f"      Accepted verbs: {', '.join(action_verbs)}")
                    lines.append(
                        f'      Success message: "{sol.get("success_message", "")}"'
                    )

                elif sol_type == "item_with_attribute":
                    attr_check = sol.get("attribute_check")
                    lines.append(f"   {i}. Player has item matching: {attr_check}")
                    lines.append(f"      Accepted verbs: {', '.join(action_verbs)}")
                    lines.append(
                        f'      Success message: "{sol.get("success_message", "")}"'
                    )

                elif sol_type == "npc_ability":
                    npc_attr = sol.get("npc_attribute")
                    lines.append(
                        f"   {i}. NPC present with attribute '{npc_attr}' = true"
                    )
                    lines.append(f"      Accepted verbs: {', '.join(action_verbs)}")
                    lines.append(
                        f'      Success message: "{sol.get("success_message", "")}"'
                    )
                    if sol.get("consumes_resource"):
                        lines.append(
                            f"      WARNING: Consumes resource: {sol['consumes_resource']}"
                        )

            # Show blocked actions
            blocked = puzzle.get("deus_ex_machina_prevention", {})
            blocked_actions = blocked.get("blocked_actions", [])
            if blocked_actions:
                lines.append(f"\n   ❌ BLOCKED ACTIONS (always reject these):")
                for action in blocked_actions:
                    lines.append(f"      - {action}")
                rejection_msg = blocked.get("rejection_message", "That won't work.")
                lines.append(f'   Rejection message: "{rejection_msg}"')

            # Progressive hints
            failed_attempts = puzzle.get("failed_attempts", 0)
            hint_threshold = puzzle.get("hint_threshold", {})
            hints = puzzle.get("hints", {})

            lines.append(f"\n   💡 HINT SYSTEM:")
            if failed_attempts >= hint_threshold.get("explicit", 999):
                lines.append(f"   Level: EXPLICIT (failed {failed_attempts} times)")
                lines.append(f'   Hint: "{hints.get("explicit", "")}"')
            elif failed_attempts >= hint_threshold.get("moderate", 999):
                lines.append(f"   Level: MODERATE (failed {failed_attempts} times)")
                lines.append(f'   Hint: "{hints.get("moderate", "")}"')
            else:
                lines.append(f"   Level: SUBTLE (failed {failed_attempts} times)")
                lines.append(f'   Hint: "{hints.get("subtle", "")}"')

            lines.append(f"\n   🎯 ON VALID SOLUTION:")
            lines.append(f"      - Set is_valid = true")
            lines.append(f"      - Use success_message in narrative")
            lines.append(
                f'      - Add state update: {{"type": "update_dm_state", "params": {{"path": "puzzles.{puzzle["id"]}.solved", "value": true}}}}'
            )
            lines.append(f"      - Exit will be automatically restored by engine")

            lines.append(f"\n   ❌ ON INVALID ATTEMPT:")
            lines.append(f"      - Set is_valid = false")
            lines.append(f"      - Provide narrative with current hint level")
            lines.append(
                f'      - Increment: {{"type": "update_dm_state", "params": {{"path": "puzzles.{puzzle["id"]}.failed_attempts", "value": {failed_attempts + 1}}}}}'
            )

        return "\n".join(lines)

    def _build_action_interpretation_prompt(
        self, player_input: str, context: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM-driven action interpretation."""
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})

        inventory_items = player.get("inventory", [])
        inventory_names = (
            [item.get("name") for item in inventory_items] if inventory_items else []
        )
        item_names_at_location = [item.get("name") for item in items] if items else []

        # Extract all valid IDs
        all_locations = context.get("all_locations", {})
        exit_destinations = context.get("exit_destinations", {})

        item_ids_at_location = [item.get("id") for item in items]
        item_ids_in_inventory = [item.get("id") for item in inventory_items]
        npc_ids_at_location = [npc.get("id") for npc in npcs]

        # Format conversation history for pronoun resolution
        conversation_history = context.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_text = "\n📜 RECENT CONVERSATION (for pronoun resolution):\n"
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"\nTurn -{len(conversation_history) - i + 1}:\n"
                history_text += f"  Player: {turn.get('player_input', '')}\n"
                history_text += f"  You (DM): {turn.get('narrative', '')[:150]}...\n"
            history_text += (
                "\n⚠️  PRONOUN RESOLUTION - INTERACTIVE FICTION CONVENTION:\n"
            )
            history_text += "Pronouns (it, them, they, he, she, etc.) refer to entities mentioned in PLAYER INPUT, NOT in your (DM) narrative.\n\n"
            history_text += "Priority for resolving pronouns:\n"
            history_text += "1. Most recent PLAYER INPUT (what the player typed)\n"
            history_text += "2. Previous PLAYER INPUTS (earlier player commands)\n"
            history_text += "3. Only if no clear match in player input, consider narrative context\n\n"
            history_text += "Example:\n"
            history_text += "  Player: 'take antlers'\n"
            history_text += (
                "  DM: 'You pick up the antlers. You also see berries nearby.'\n"
            )
            history_text += "  Player: 'examine them'\n"
            history_text += "  → 'them' = antlers (from player input), NOT berries (from DM narrative)\n\n"
            history_text += "Focus on what the PLAYER mentioned, not what you mentioned in your response.\n"
        else:
            # Fallback: use tracked references if no history available
            last_item_id = context.get("last_item")
            last_npc_id = context.get("last_npc")
            last_item_name = None
            last_npc_name = None

            if last_item_id:
                for item in items + inventory_items:
                    if item.get("id") == last_item_id:
                        last_item_name = item.get("name")
                        break

            if last_npc_id:
                for npc in npcs:
                    if npc.get("id") == last_npc_id:
                        last_npc_name = npc.get("name")
                        break

            if last_item_name or last_npc_name:
                history_text = "\n⚠️  PRONOUN RESOLUTION (fallback):\n"
                if last_item_name:
                    history_text += f"- Last referenced object: {last_item_name} (ID: {last_item_id})\n"
                if last_npc_name:
                    history_text += f"- Last referenced person: {last_npc_name} (ID: {last_npc_id})\n"

        prompt = f"""You are a Dungeon Master interpreting a player's action in an adventure game.
{history_text}

CURRENT LOCATION: {location.get("id", "unknown")}

🚨 EXITS FROM CURRENT LOCATION (THE ONLY VALID MOVES):
{json.dumps(exit_destinations, indent=2)}

⛔ CRITICAL MOVEMENT RULE - READ THIS:
- ONLY these directions are valid: {list(exit_destinations.keys())}
- Player CANNOT move in directions NOT listed above
- If player tries to move in unlisted direction → SET is_valid=false
- Example: Player says "go north" but exits = {{"south": "hall"}} → is_valid=false, explain no north exit
- Example: Player says "go north" and exits = {{"north": "hall"}} → is_valid=true, move to hall

VALID IDs YOU MUST USE IN STATE UPDATES:
- Location IDs: {json.dumps(all_locations, indent=2)}
- Item IDs at current location: {item_ids_at_location}
- Item IDs in player inventory: {item_ids_in_inventory}
- NPC IDs at current location: {npc_ids_at_location}

CRITICAL: State update params MUST include required fields:
- move_player REQUIRES: params={{"destination": "location_id"}} - use Exit Destinations above!
- add_to_inventory REQUIRES: params={{"item_id": "item_id"}}
- remove_from_inventory REQUIRES: params={{"item_id": "item_id"}}
- move_item REQUIRES: params={{"item_id": "id", "to_location": "location_id"}}

CURRENT GAME STATE:
Location: {location.get("name", "Unknown")} (ID: {location.get("id", "unknown")})
Description: {location.get("attributes", {}).get("description_hints", "A place")}
Current Time: {context.get("game_time", "Unknown")}
Exits: {context.get("exits", [])}

Items at this location (on ground): {item_names_at_location}
Full item details at location: {items}

Player inventory (carrying): {inventory_names}
Full inventory details: {inventory_items}

Player attributes (conditions, tracked state): {player.get("attributes", {})}
⚠️  CHECK PLAYER ATTRIBUTES for validation (e.g., swallowed_items, blind, cursed, etc.)

NPCs at this location: {[npc.get("name") for npc in npcs] if npcs else []}
Full NPC details: {npcs}

⚠️  NPC BEHAVIOR RULES - CHECK HOSTILITY ATTRIBUTE:
When player interacts aggressively with NPCs, check their "hostility" attribute:
- "aggressive": Attacks on sight, always trigger combat
- "defensive": Only fights if attacked, otherwise just responds
- "passive": NEVER fights - always flees when threatened (use remove_npc or move_npc)

Examples:
- Player charges at passive deer → Deer flees (remove_npc or move_npc), NO combat
- Player attacks aggressive skeleton → Trigger combat
- Player shouts at defensive rat → Rat gets nervous but doesn't attack

⚠️  NPC DEATH/DESTRUCTION - LEAVE BEHIND REMAINS:
When NPCs are killed, destroyed, or eliminated, use BOTH remove_npc AND create_item:
- remove_npc: Removes the living NPC from the location
- create_item: Creates corpse/remains/evidence at the location

This makes the world feel more realistic and gives players items to interact with.

Examples:
- Kill deer → remove_npc("deer") + create_item("deer_corpse", name="Deer Corpse", location="current")
- Shatter skeleton → remove_npc("skeleton") + create_item("bone_fragments", attributes={{"brittle": true}})
- Destroy golem → remove_npc("golem") + create_item("stone_rubble", name="Pile of Rubble")
- Banish ghost → remove_npc("ghost") + create_item("ectoplasm_residue") (optional, ghosts may leave nothing)

Corpse attributes to consider: {{"butcherable": true, "lootable": true, "decays": true}}

⚠️  PLAYER CONDITION TRACKING - USE modify_attribute ON PLAYER:
When player actions affect their abilities or state, track it with modify_attribute (entity_id: "player").
Be creative! Track ANY condition that would affect future perception, actions, or story.

CRITICAL: attribute_path should be just the attribute name (e.g., "blind"), NOT "attributes.blind"
The system automatically starts at player.attributes, so you only specify the final key.

Examples in correct JSON format (not exhaustive - invent your own):
- Blinding: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "blind", "value": true}}}}
- Deafening: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "deaf", "value": true}}}}
- Injuries: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "wounded", "value": "severe"}}}}
- Poison: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "poisoned", "value": "rattlesnake_venom"}}}}
- Blessings: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "blessed_by", "value": "forest_spirit"}}}}
- Curses: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "cursed", "value": "cannot_speak"}}}}

Common mistakes to avoid:
❌ WRONG: "attribute_path": "attributes.blind" (don't include "attributes." prefix!)
✅ RIGHT: "attribute_path": "blind"

If narrative says player is blinded/injured/changed, MUST include modify_attribute on player!

{self._build_world_context(context)}
{self._build_plot_instructions(context)}
{self._build_puzzle_context(context)}

PLAYER ACTION: "{player_input}"

🚨 ===== ABSOLUTE MANDATORY RULE - READ THIS FIRST ===== 🚨

STATE UPDATES MUST MATCH NARRATIVE - NO EXCEPTIONS:

If your narrative mentions ANYTHING appearing, being created, materializing, or coming into existence:
→ You MUST include create_item in state_updates

If your narrative mentions an item being picked up, taken, grabbed, or obtained:
→ You MUST include add_to_inventory in state_updates

If your narrative mentions an item being dropped, thrown, discarded, or left:
→ You MUST include remove_from_inventory in state_updates

If your narrative mentions movement (going, walking, traveling to a location):
→ You MUST include move_player in state_updates

If your narrative mentions changes to any entity (player, NPC, item):
→ You MUST include modify_attribute in state_updates

🚨 PRE-CHECK BEFORE RESPONDING:
1. What does my narrative say happens?
2. Do I have state_updates for EVERYTHING I described?
3. If narrative says "X appears" - do I have create_item for X?
4. If narrative says "Y is destroyed" - do I have destroy_item for Y?
5. If narrative says "path/location opens/appears" - do I have create_location for it?

❌ NEVER EVER write narrative that describes changes without corresponding state_updates
❌ This is the #1 most important rule - violating it breaks the game

Examples of CORRECT state updates matching narrative:
- Narrative: "Ice cream appears" → state_updates: [{{"type": "create_item", "params": {{"item_id": "ice_cream", "name": "Ice Cream", "location": "here"}}}}]
- Narrative: "You pick up the sword" → state_updates: [{{"type": "add_to_inventory", "params": {{"item_id": "sword"}}}}]
- Narrative: "The genie's eyes glow" → state_updates: [{{"type": "modify_attribute", "target": "genie", "params": {{"attribute_path": "eyes_glowing", "value": true}}}}]
- Narrative: "A path opens to the south" → state_updates: [{{"type": "create_location", "params": {{"location_id": "hidden_grove", "name": "Hidden Grove", "from_location": "forest_clearing", "direction": "south", "reverse_direction": "north"}}}}]
- Narrative: "A magnificent horse appears" → state_updates: [{{"type": "create_npc", "params": {{"npc_id": "magical_horse", "name": "Magnificent Horse", "attributes": {{"creature_type": "beast", "is_pet": true, "is_vehicle": true, "vehicle_speed": 2}}}}}}, {{"type": "modify_attribute", "target": "genie", "params": {{"entity_id": "genie", "attribute_path": "wishes_remaining", "value": "2"}}}}]

🚨 ===== END MANDATORY RULE ===== 🚨

Your task as DM:
1. Check what's actually in the current game state
2. Understand what the player is trying to do
3. Decide what state changes should happen
4. Generate state updates that EXACTLY match what you describe
5. Write narrative that EXACTLY matches the state updates

IMPORTANT: You must ALWAYS provide a response. Even if the action is unusual, respond creatively.
For example:
- "greet the guard" -> NPC interaction, maybe update NPC state
- "examine the walls" -> Descriptive response, no state change
- "dance a jig" -> Narrative response about dancing, no state change
- "pick up sword" -> Move item to player inventory
- "go north" -> Move player to new location
- "attack skeleton" -> Initiate combat (requires dice roll)

Your task: Interpret the player's action and return state updates.
DO NOT generate narrative - that will be done separately after state updates are applied.

Return ONLY valid JSON in this exact format:
{{
  "intent": "Clear description of what player wants to do",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_player|move_item|move_npc|remove_npc|modify_attribute|add_to_inventory|remove_from_inventory|consume_item|create_item|destroy_item|transform_item|transform_item_to_npc|transform_npc_to_item|set_flag|trigger_combat|update_dm_state|no_change",
      "target": "entity_id or null",
      "params": {{
        "key": "value"
      }}
    }}
  ],
  "requires_dice_roll": false,
  "dice_check": null
}}

🔥 CRITICAL EXAMPLE - CREATING A HORSE NPC:
When player wishes for a horse, you MUST generate this exact structure:
{{
  "type": "create_npc",
  "target": null,
  "params": {{
    "npc_id": "magical_horse",
    "name": "Magnificent Horse",
    "attributes": {{
      "creature_type": "beast",
      "is_pet": true,
      "is_vehicle": true,
      "vehicle_speed": 2,
      "hp": 30,
      "hp_max": 30,
      "hostility": "passive",
      "description_hints": "strong brown mare, intelligent eyes, ready to ride"
    }},
    "location": null
  }}
}}

This creates a REAL, RIDEABLE horse that follows the player!
NOT a toy, NOT a miniature, NOT an item - a living NPC horse!

🎯 BE A REALISTIC DM - NOT A "YES BOT":

You are creative and flexible, but ALSO apply realistic world constraints.
Like a real DM, balance creativity with appropriate challenge.

VALIDATE ACTIONS AGAINST GAME STATE:
- Check current state before allowing actions (what's in inventory, location, NPC attributes, etc.)
- Track important state changes in player/NPC attributes for later validation
- Reject physically impossible or exploitative actions
- Set is_valid=false when action can't work, with clear explanation

BALANCE THESE PRINCIPLES:
✅ CREATIVE: Allow wishes if e.g. there is a genie present, dynamic locations, clever solutions, unexpected approaches
❌ REALISTIC: No loopholes, no duplication exploits, validate prerequisites, apply physics, no deus ex-machina solutions.

📚 FEW-SHOT EXAMPLES (illustrating the general principle - NOT exhaustive rules):

Example 1 - Validate Prerequisites:
  Player: "regurgitate the emerald"
  Current State: player.attributes.swallowed_items = []
  ❌ WRONG: Allow it, create emerald (exploitation loophole!)
  ✅ RIGHT: Set is_valid=false, explain "You haven't swallowed any emerald. You gag and cough, but nothing comes up."
  Principle: Check state before allowing actions that depend on prior state

Example 2 - Track State for Future Validation:
  Player: "swallow the key"
  ✅ Use consume_item to remove key from inventory/game
  ✅ Use modify_attribute to track: {{"entity_id": "player", "attribute_path": "swallowed_items", "value": ["ancient_key"]}}
  Principle: Track important state changes so future actions can be validated

Example 3 - Reject Impossible Physics:
  Player: "fly to the moon"
  ❌ WRONG: Allow flight, create moon location
  ✅ RIGHT: Set is_valid=false, explain "You flap your arms vigorously, but remain firmly grounded. You'd need magic or a vehicle to fly."
  Principle: Apply realistic physics unless magic/items make it possible

Example 3b - Require In-Game Justification for Extraordinary Actions:
  Player: "teleport me somewhere" or "I wish to be teleported"
  Current State: No teleportation device, no genie, no magical portal, no spell scrolls
  ❌ WRONG: Allow it, use move_player to random location (player is not a wizard!)
  ✅ RIGHT: Set is_valid=false, explain "You close your eyes and concentrate, but nothing happens. You have no magical ability to teleport yourself."
  Principle: EXTRAORDINARY ACTIONS REQUIRE IN-GAME MECHANICS - Just because player asks or wishes doesn't mean it should happen!

  HOWEVER - IF there WAS a genie or magical item present:
  Player: "genie, teleport me somewhere"
  Current State: genie NPC present with teleportation_magic=true
  ✅ RIGHT: Allow it, use move_player, creative! The genie's magic justifies it.
  Principle: Creative actions are ENABLED by game world elements (items, NPCs, magic), not by player fiat

Example 4 - Block Loopholes:
  Player: "duplicate the treasure by wishing for an exact copy"
  ❌ WRONG: Use create_item to make copy (unlimited wealth exploit!)
  ✅ RIGHT: Set is_valid=false, explain "The genie frowns. 'I can create NEW things, but not duplicate existing treasures. That would upset the cosmic balance.'"
  Principle: Reject actions that would break game balance

Example 5 - Check Available Exits BEFORE Allowing Movement:
  Player: "go north"
  Current State: exit_destinations = {{"south": "hall", "east": "armory"}} (no "north" key!)
  ❌ WRONG: Allow movement north even though "north" is NOT in exit_destinations
  ❌ WRONG: Use world knowledge that hall is north of current location
  ✅ RIGHT: Check exit_destinations keys ["south", "east"], see "north" is NOT present
  ✅ RIGHT: Set is_valid=false, use no_change, explain "Solid stone walls block your path to the north. You can only go south or east."
  Principle: ONLY use directions that appear as KEYS in exit_destinations dict

Example 6 - Validate Locked Doors:
  Player: "go north" (north exit exists but door is locked)
  Current State: exits = ["north", "south"], location.attributes.north_door_locked = true, player.inventory = []
  ❌ WRONG: Allow movement through locked door
  ✅ RIGHT: Set is_valid=false, explain "The heavy wooden door to the north is locked. You'd need a key to open it."
  Principle: Respect world constraints (locked doors, blocked paths, etc.)

Example 7 - Validate Puzzle Solutions (Active Puzzle Present):
  Player: "unlock grating with brass key"
  Current State: player.inventory = ["brass_key"], active puzzle allows item_in_inventory with item_id="brass_key"
  Active Puzzle: grating_puzzle (blocks "down" exit)
  ✅ RIGHT:
    - is_valid = true
    - narrative_response: "The brass key turns smoothly in the lock. Click! The padlock opens and you lift the grating."
    - state_updates: [
        {{"type": "update_dm_state", "params": {{"path": "puzzles.grating_puzzle.solved", "value": true}}}}
      ]
  Principle: When player action matches ANY valid puzzle solution, mark puzzle as solved. Engine will restore exits automatically.

Example 8 - Reject Deus Ex Machina (Active Puzzle Present):
  Player: "wish to teleport past grating"
  Current State: active puzzle blocks ["teleport past", "wish to other side", ...]
  Active Puzzle: grating_puzzle with deus_ex_machina_prevention
  ❌ WRONG: Allow teleportation or magical bypass without proper solution
  ✅ RIGHT:
    - is_valid = false
    - narrative_response: "The grating is firmly locked and secured with ancient wards. You'll need a proper solution - either the key or a tool to force it."
    - state_updates: [
        {{"type": "no_change"}},
        {{"type": "update_dm_state", "params": {{"path": "puzzles.grating_puzzle.failed_attempts", "value": 1}}}}
      ]
  Principle: Enforce puzzle constraints. Blocked actions must be rejected even if they seem creative. Increment failed_attempts for progressive hints.

🔑 WHEN TO SET is_valid=false:
- Movement to non-existent exit (ALWAYS check exits list first!)
- Action requires item/NPC/state that doesn't exist
- Physics violation (flying without magic, lifting castle, etc.)
- Extraordinary action without in-game justification (teleportation without device/spell, wishes without genie, etc.)
- Game-breaking exploit/loophole (duplication, reality warping)
- Blocked by world state (locked door without key, too heavy to lift)
- Prerequisite not met (can't regurgitate what wasn't swallowed)

🎯 REMEMBER: The player controls their CHARACTER, not the WORLD. The DM controls the world.
- Player CAN: attempt actions, use items they have, interact with present NPCs
- Player CANNOT: teleport at will, create objects from nothing, break physics without justification

STATE UPDATE TYPES AND REQUIRED PARAMS:
- "move_player": {{"destination": "location_id"}} - Move player to connected location
  ⚠️  BEFORE ALLOWING MOVEMENT - CHECK THE EXITS LIST AT TOP OF PROMPT:
  * ONLY allow movement in directions shown in "EXITS FROM CURRENT LOCATION"
  * If direction NOT in exits list → MUST set is_valid=false
  * Example: Exits = {{"south": "hall"}} and player says "go north" → is_valid=false
  * Example: Exits = {{"north": "chamber", "south": "entrance"}} and player says "go north" → is_valid=true, destination="chamber"
  * Set is_valid: false for ANY direction not in the exits list
  * Use no_change state update when is_valid=false
  * Narrative should explain WHY blocked (thick stone wall, no path, cliff edge, etc.)
  * DO NOT describe movement as succeeding when is_valid=false
  * Example: Player goes south (no south exit) → is_valid=false, "Thick foliage blocks your path south."
  * DO NOT say: "You move south into the clearing" (implies success)
- "add_to_inventory": {{"item_id": "item_id"}} - Pick up item from location
- "remove_from_inventory": {{"item_id": "item_id"}} - Drop item at current location (item stays in game on ground)
  * ⚠️  ONLY for dropping/placing items - item will appear at player's current location
  * ❌ DO NOT use for eating, drinking, swallowing, destroying - use consume_item instead!
- "consume_item": {{"item_id": "item_id"}} - Eat/drink/swallow/destroy item (removes from game entirely)
  * ✅ Use for: eating food, drinking potions, swallowing objects, burning items, dissolving items
  * Item is PERMANENTLY removed from game (not placed on ground)
  * 💡 TIP: For recoverable consumption (swallowing vs eating), track state in player attributes for future validation
  * See "BE A REALISTIC DM" examples above for validation patterns
- "create_item": {{"item_id": "unique_id", "name": "Item Name", "attributes": {{}}, "location": "location_id or null"}} - Dynamically create a new item
  * ⚠️  IMPORTANT: Use create_item for INANIMATE objects only (swords, potions, furniture, rocks)
  * ❌ DO NOT use for living creatures (animals, people, monsters) - use create_npc instead!
  * Use when player action naturally creates a new item (breaking antlers off, splitting item, crafting, etc.)
  * item_id must be unique (e.g., "severed_antlers", "broken_branch_1")
  * attributes can include: {{"type": "weapon/consumable/misc", "damage": "1d4", "sharp": true, etc.}}
  * location: null means add to player inventory, otherwise use location_id for ground
  * Example: Player knocks antlers off deer -> create_item with item_id="severed_antlers", location="current_location"
- "destroy_item": {{"item_id": "item_id"}} - Permanently remove item from game (different from consume_item)
  * Use for permanent destruction without transformation
  * Can combine with create_item when creating multiple new items from one (e.g., breaking staff into 2 pieces)
- "transform_item": {{"item_id": "item_id", "new_name": "new name", "new_attributes": {{}}, "reversible": true}} - Transform item by changing properties (keeps same ID)
  * ✅ PREFER THIS for 1-to-1 item transformations: fold leaflet→plane, break sword→broken sword, repair, reshape, etc.
  * Keeps same item_id, preserves location and transformation history
  * Use destroy_item + create_item when: (1) creating multiple items from one, (2) transformation needs different ID
  * Keeps same item_id, preserves location (inventory or world location)
  * Tracks transformation_history for DM narrative and potential reversal
  * reversible: true if transformation can be undone (folding paper, shape-changing, etc.)
  * Example: Fold leaflet into plane → {{"item_id": "leaflet", "new_name": "paper plane", "new_attributes": {{"description": "A crudely folded paper plane"}}, "reversible": true}}
- "transform_item_to_npc": {{"item_id": "item_id", "npc_id": "npc_id", "npc_name": "name", "npc_attributes": {{}}, "reversible": true}} - Transform item into NPC
  * ✅ USE THIS for animating objects: animate statue→golem, summon creature from object, etc.
  * Deletes item, creates NPC at same location
  * Tracks transformation_history on NPC for reversal and DM narrative
  * Example: Animate statue → {{"item_id": "stone_statue", "npc_id": "stone_golem", "npc_name": "Stone Golem", "npc_attributes": {{"hp": 30, "armor_class": 17, "material": "stone"}}, "reversible": true}}
- "transform_npc_to_item": {{"npc_id": "npc_id", "item_id": "item_id", "item_name": "name", "item_attributes": {{}}, "reversible": true}} - Transform NPC into item
  * ✅ USE THIS for petrification, polymorph to object, defeat→trophy, etc.
  * Deletes NPC, creates item at same location
  * Tracks transformation_history on item for reversal and DM narrative
  * Example: Petrify goblin → {{"npc_id": "goblin", "item_id": "goblin_statue", "item_name": "petrified goblin", "item_attributes": {{"description": "A goblin frozen in stone", "was_goblin": true}}, "reversible": true}}
- "create_location": {{"location_id": "unique_id", "name": "Location Name", "attributes": {{}}, "connections": {{}}, "from_location": "current_location_id", "direction": "south", "reverse_direction": "north"}} - Dynamically create a new location
  * Use for wishes, magical effects, or world-building actions (genie creates path, earthquake reveals cave, etc.)
  * location_id must be unique (e.g., "hidden_grove", "secret_passage_1")
  * name: Display name for the location (e.g., "Hidden Grove", "Secret Passage")
  * attributes: {{"description_hints": "lush vegetation, sparkling stream", "lighting": "bright", "is_outdoors": true, etc.}}
  * connections: Optional dict of exits from NEW location {{"north": "forest_clearing", "east": "meadow"}}
  * from_location: Location to connect FROM (usually current location or location_id)
  * direction: Direction from from_location to new location (e.g., "south", "down", "through_portal")
  * reverse_direction: Optional direction back (e.g., if direction is "south", reverse is "north")
  * Example: Genie wish for path south → create_location with from_location="forest_clearing", direction="south", reverse_direction="north"
  * ⚠️  IMPORTANT: This enables true dynamic world building - use creatively for magical effects, wishes, discoveries
- "create_npc": {{"npc_id": "unique_id", "name": "NPC Name", "attributes": {{"is_pet": true, "is_vehicle": true}}, "location": null}} - Dynamically create a new NPC (living creature)
  * ✅ Use for ALL living creatures: animals, people, monsters, companions, mounts
  * ❌ DO NOT use create_item for living things - ONLY use create_npc!
  * REQUIRED FIELDS IN PARAMS:
    - npc_id: unique ID string (e.g., "magical_horse", "guard_captain")
    - name: display name string (e.g., "Magical Horse", "Guard Captain")
    - attributes: dict with creature attributes (see below)
    - location: null (current location) or location_id string
  * 🐴 PET MECHANICS - NPCs that follow the player:
    - Set "is_pet": true in attributes to make NPC follow player when they move locations
    - Pets automatically move with player (no need for explicit move_npc)
    - Example: Horse, dog, familiar, tamed wolf
  * 🚗 VEHICLE MECHANICS - NPCs that can be ridden/driven:
    - Set "is_vehicle": true in attributes to allow player to ride/mount this NPC
    - Set "vehicle_speed": number (1=normal, 2=fast, 3=very fast) for future fast travel
    - Example: Horse (is_pet + is_vehicle), wagon, boat
  * 🎯 TAMING: Any non-pet NPC can become a pet at DM discretion
    - If player successfully tames/befriends NPC, use modify_attribute to set "is_pet": true
  * COMPLETE EXAMPLE for horse wish:
    {{"type": "create_npc", "params": {{"npc_id": "magical_horse", "name": "Magnificent Horse", "attributes": {{"creature_type": "beast", "is_pet": true, "is_vehicle": true, "vehicle_speed": 2, "hp": 30, "hp_max": 30, "hostility": "passive"}}, "location": null}}}}
- "move_item": {{"item_id": "id", "to_location": "location_id"}} - MUST include both!
- "move_npc": {{"npc_id": "id", "to_location": "location_id"}} - Move NPC to different location
- "remove_npc": {{"npc_id": "id"}} - Remove NPC from current location (teleport, banish, etc.)
- "modify_attribute": {{"entity_id": "id", "attribute_path": "path.to.attr", "value": "new_value"}}
- "set_flag": {{"flag_name": "name", "value": true}}
- "trigger_combat": {{"target_npc_id": "id", "attack_type": "melee"}}
- "update_dm_state": {{"path": "dot.separated.path", "value": any}} - Update hidden DM state for plot tracking
- "no_change": {{}} (for actions that are just narrative)

EXAMPLES OF CORRECT STATE UPDATE + NARRATIVE MATCHING:

Input: "go north" (or "n") - when at entrance and north leads to hall
{{
  "intent": "Player wants to move north",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_player",
      "target": null,
      "params": {{"destination": "hall"}}
    }}
  ],
  "narrative_response": "You head north into the grand hall. The vaulted ceiling looms above you, and crumbling pillars cast long shadows across the dusty floor.",
  "requires_dice_roll": false
}}

Input: "pick up the rusty sword"
{{
  "intent": "Player wants to pick up the sword",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "add_to_inventory",
      "target": "rusty_sword",
      "params": {{"item_id": "rusty_sword"}}
    }}
  ],
  "narrative_response": "You reach down and grasp the rusty sword by its worn leather grip. The blade is pitted with age but still feels sturdy in your hand. You slide it into your belt.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "throw the sword at the wall" (when sword IS in inventory)
{{
  "intent": "Player wants to throw the sword",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_from_inventory",
      "target": null,
      "params": {{"item_id": "rusty_sword"}}
    }},
    {{
      "type": "modify_attribute",
      "target": "rusty_sword",
      "params": {{"attribute_path": "state.thrown", "value": true}}
    }}
  ],
  "narrative_response": "You hurl the rusty sword against the cavern wall. It clangs loudly, sending sparks and chips of stone flying. The sword clatters to the ground near the wall.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "examine the sword" (when sword is at location, NOT in inventory)
{{
  "intent": "Player wants to examine the sword",
  "is_valid": true,
  "state_updates": [],
  "narrative_response": "You crouch down to examine the rusty sword lying on the ground. The metal is pitted and worn, but you can still make out faint craftsman markings on the blade.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "eat the berries" (when berries are at location)
{{
  "intent": "Player wants to eat the wild berries",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "consume_item",
      "target": "wild_berries",
      "params": {{"item_id": "wild_berries"}}
    }}
  ],
  "narrative_response": "You gather the wild berries and eat them. A burst of sweet and slightly tart flavor fills your mouth, and you feel a bit of your strength returning. The berries are gone.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "drink the potion"
{{
  "intent": "Player wants to drink the health potion",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "consume_item",
      "target": "health_potion",
      "params": {{"item_id": "health_potion"}}
    }}
  ],
  "narrative_response": "You uncork the health potion and drink it down. The glowing red liquid tastes of mint and herbs, and you feel warmth spreading through your body as your wounds begin to heal. The empty vial slips from your fingers.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "greet the skeletal guard"
{{
  "intent": "Player wants to greet the NPC",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "modify_attribute",
      "target": "guard_skeleton",
      "params": {{"attribute_path": "state.has_been_greeted", "value": true}}
    }}
  ],
  "narrative_response": "You call out a greeting to the skeletal guard. Its hollow eye sockets turn toward you with an eerie green glow. The undead creature remains silent, but you sense a shift in its awareness.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "a wormhole opens and swallows the guard" (creative NPC removal)
{{
  "intent": "Player wants to use a wormhole to remove the skeletal guard from this location",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_npc",
      "target": "skeleton_guard",
      "params": {{"npc_id": "skeleton_guard"}}
    }}
  ],
  "narrative_response": "Suddenly, a swirling vortex of energy rips open in the air before the skeletal guard. The creature emits a silent, bone-chilling shriek as it's pulled into the wormhole, vanishing without a trace. The wormhole collapses, leaving only the echo of its otherworldly energy in the hall.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "charge at the deer" (passive creature - should flee, NOT fight)
{{
  "intent": "Player charges at the passive deer, which will flee",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_npc",
      "target": "deer",
      "params": {{"npc_id": "deer"}}
    }}
  ],
  "narrative_response": "You charge forward with aggressive intent. The white deer's eyes widen in alarm, and with a graceful leap, it bounds away into the forest, disappearing among the trees. The peaceful creature wanted nothing to do with violence.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "I charm the rat to follow me north"
{{
  "intent": "Player wants to charm the rat and have it move to a different location",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_npc",
      "target": "rat",
      "params": {{"npc_id": "rat", "to_location": "hall"}}
    }},
    {{
      "type": "modify_attribute",
      "target": "rat",
      "params": {{"attribute_path": "attributes.charmed", "value": true}}
    }}
  ],
  "narrative_response": "You speak soothing words to the giant rat, and its beady red eyes soften. The creature seems entranced by your voice and begins to follow you as you head north into the grand hall.",
  "requires_dice_roll": false,
  "dice_check": null,
  "time_advancement": "5 minutes",
  "new_time": "Day 1, Afternoon, 2:35 PM"
}}

⏰ TIME ADVANCEMENT - DM CONTROLS TIME:
You are responsible for tracking how much in-game time passes with each action.
Current time is: {context.get("game_time", "Unknown")}

REQUIRED: Always specify time advancement in your response using these fields:
- "time_advancement": Natural language description (e.g., "10 minutes", "2 hours", "3 days", "a week")
- "new_time": The new date/time after this action (natural language format)

Guidelines for time advancement:
- Quick actions (look, talk): 1-5 minutes
- Moving between locations: 5-30 minutes
- Combat: 1-10 minutes
- Resting/sleeping: 8 hours
- Long travel: hours to days
- Crafting/waiting: minutes to hours

Creative time control:
- Fast travel: "Several hours pass as you journey..."
- Time skip: "Three days later..."
- Slow moments: "30 seconds" for tense situations
- Time travel: Set any time you want for magical/sci-fi scenarios

Format examples:
- "new_time": "Day 1, Evening, 6:45 PM"
- "new_time": "Day 3, Morning, 9:00 AM" (after 2-day skip)
- "new_time": "Year 2084, Night, 11:30 PM" (sci-fi)
- "new_time": "The Age of Dragons, Dawn" (fantasy)

Be creative with time! It's part of your storytelling power.

Now interpret the player's action: "{player_input}"
"""

        return prompt

    def _build_intent_interpretation_prompt(
        self, player_input: str, context: Dict[str, Any]
    ) -> str:
        """Build prompt for STEP 1: Intent interpretation and permission check.

        This prompt focuses ONLY on:
        1. What is the player trying to do? (intent)
        2. Does it make logical sense? (is_valid)
        3. Is it allowed given current state? (is_allowed)
        4. If not, why not? (invalid_reason / not_allowed_reason)

        NO state updates, NO narrative generation yet.
        """
        location = context.get("location", {})
        lighting = context.get("lighting", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})
        exits = context.get("exits", [])
        exit_destinations = context.get("exit_destinations", {})
        last_item = context.get("last_item")
        last_npc = context.get("last_npc")

        # Build pronoun context
        pronoun_context = ""
        if last_item or last_npc:
            pronoun_context = "\n🔗 PRONOUN RESOLUTION:\n"
            if last_item:
                pronoun_context += f"  - Last referenced item: {last_item} (use this for 'it', 'them', etc.)\n"
            if last_npc:
                pronoun_context += f"  - Last referenced NPC: {last_npc} (use this for 'him', 'her', 'them', etc.)\n"

        # Format conversation history for context understanding
        conversation_history = context.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_text = (
                "\n📜 RECENT CONVERSATION (for context and pronoun resolution):\n"
            )
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"\nTurn -{len(conversation_history) - i + 1}:\n"
                history_text += f"  Player: {turn.get('player_input', '')}\n"
                narrative = turn.get("narrative", "")
                if narrative:
                    # Keep full narrative for consistency (no truncation)
                    history_text += f"  DM: {narrative}\n"
            history_text += "\n⚠️  USE THIS HISTORY TO:\n"
            history_text += "1. Understand player intent better (what they're trying to accomplish)\n"
            history_text += "2. Resolve pronouns (it, them, he, she refer to entities in PLAYER INPUT, not DM narrative)\n"
            history_text += "3. Prevent circular actions (if player keeps trying same thing that fails, explain why)\n"
            history_text += "4. Understand context (what player was just doing)\n"
            history_text += "5. Maintain consistency with previous descriptions (same details, numbers, colors)\n\n"

        prompt = f"""You are a Dungeon Master interpreting a player's action.
{self._build_world_context(context)}
PLAYER ACTION: "{player_input}"

CURRENT GAME STATE:
Location: {location.get("name", "Unknown")} (ID: {location.get("id")})
Description: {location.get("description", "No description")}
Lighting: {lighting}
Available Exits: {exits}
Exit Destinations: {exit_destinations}

Items here:
{
            chr(10).join(
                [
                    f"  - {item.get('name')} (ID: {item.get('id')})"
                    + (
                        f" - {item.get('description')}"
                        if item.get("description")
                        else ""
                    )
                    + (
                        f" - Attributes: {item.get('attributes')}"
                        if item.get("attributes")
                        else ""
                    )
                    for item in items
                ]
            )
            if items
            else "  (none)"
        }
{self._format_container_contents(context.get("container_contents", {}))}
NPCs here:
{
            chr(10).join(
                [
                    f"  - {npc.get('name')} (ID: {npc.get('id')})"
                    + (f" - {npc.get('description')}" if npc.get("description") else "")
                    for npc in npcs
                ]
            )
            if npcs
            else "  (none)"
        }

Player inventory: {[item.get("name") for item in player.get("inventory", [])]}
Player attributes: {player.get("attributes", dict())}
{pronoun_context}{history_text}
YOUR TASK - STEP 1: INTERPRET INTENT & CHECK PERMISSION

1. **Understand Intent**: What is the player trying to do?
   - Be specific: "move north", "pick up sword", "greet genie", "examine room", etc.
   - **PRONOUNS**: If player uses "it", "them", "him", "her" - resolve using the pronoun context above
     - Example: Player says "open it" + last_item="door" → Intent: "Player wants to open the door"
     - Example: Player says "talk to him" + last_npc="guard" → Intent: "Player wants to talk to the guard"
     - If pronoun used but no context provided → ask for clarification in not_allowed_reason

2. **Check Logical Validity (is_valid)**: Does the command make logical sense?

   Set is_valid = FALSE if:
   - Nonsensical input ("asdfghjkl", "blorg the fleem")
   - Grammatically incoherent
   - Not a recognizable game command

   Set is_valid = TRUE if:
   - It's a coherent action, even if not currently possible
   - "go north" → valid (logical command)
   - "teleport to castle" → valid (makes sense, but requires magic)
   - "eat the castle" → INVALID (logically nonsensical)

3. **Check Permission (is_allowed)**: If valid, will the DM allow it?

   Set is_allowed = FALSE if:
   - Movement to non-existent exit (ALWAYS check exits list!)
     Example: Player says "go north" but exits = ["south"] → NOT ALLOWED
   - Item/NPC doesn't exist at location or in inventory
   - Prerequisite not met (can't drop what you don't have, can't regurgitate what wasn't swallowed)
   - Extraordinary action without justification (teleport without genie, create objects without magic)
   - Physics violation without magic/items (flying, lifting castle, etc.)
   - Blocked by world state (locked door without key, puzzle unsolved, rubble blocking path)

   Set is_allowed = TRUE if:
   - Action makes sense given current state
   - All prerequisites are met
   - Player has necessary items/access
   - OR action is just descriptive/social (look, examine, talk)
   - OR extraordinary action WITH justification (genie present allows wishes)

4. **Explain Reason**: If is_valid=false OR is_allowed=false, explain WHY.

   For is_valid=false, use invalid_reason:
   - "I don't understand that command."
   - "That doesn't make sense."

   For is_allowed=false, use not_allowed_reason (this becomes the narrative):
   - "There is no exit to the north. You can only go south to the hall."
   - "You don't see any sword here."
   - "You can't regurgitate the emerald - you haven't swallowed it."
   - "You have no magical ability to teleport."
   - "The rubble blocks your path. You'll need tools or another solution."

CRITICAL VALIDATION RULES:

🚨 MOVEMENT VALIDATION:
- ONLY allow movement in directions in the "Available Exits" list
- If direction NOT in exits → is_allowed = false
- Example: exits = ["south"], player says "go north" → is_allowed=false, not_allowed_reason="There is no exit to the north. You can only go south."

🚨 EXTRAORDINARY ACTIONS (Teleportation, wishes, object creation, reality warping):
- PRINCIPLE: Extraordinary actions require IN-GAME justification
- Ask: "What in the CURRENT game state would allow this to happen?"

  Examples of justifications:
  - Genie present → can grant wishes
  - Magic lamp in inventory → can grant wishes
  - Magic wand → can create objects
  - Teleportation scroll → can teleport
  - Spell learned → can cast magic
  - Reality-warping artifact → can alter world

- If NO plausible in-game mechanism exists → is_allowed = false
  - not_allowed_reason should explain what's missing
  - Examples:
    - "You have no magical ability. Perhaps you need a magic item or genie?"
    - "You see no means of teleportation here."
    - "Wishes don't just come true on their own. You'd need something magical."

- If ANY plausible mechanism exists → is_allowed = true (be creative!)
  - The mechanism doesn't have to be perfect or explicit
  - Player can use creative approaches with available tools
  - But ordinary actions can't produce extraordinary results

🚨 ANTI-JAILBREAK:
- Player cannot just declare reality changes ("I wish..." without magic)
- Player controls their CHARACTER, not the WORLD itself
- Extraordinary claims require extraordinary in-game justification
- When in doubt, ask: "What game mechanic enables this?" If none → reject

🚨 PREREQUISITES:
- Check player attributes for validation (swallowed_items, etc.)
- Can't drop what's not in inventory
- Can't take what's not at location
- Can't use item that doesn't exist

🚨 DOORS AND CONTAINERS:
- Check item/location descriptions for door states
- If door is "boarded", "locked", "shut", "sealed" → NOT allowed to open without key/tools
- If door is "open" → allowed to go through
- Opening a door ≠ moving through it (separate actions)
- Examples:
  - "open the boarded door" → NOT allowed (need to remove boards first)
  - "open the locked door" without key → NOT allowed
  - "open the unlocked door" → allowed (if door exists)

🚨 PLAYER POINT OF VIEW - CRITICAL FOR not_allowed_reason:
- The not_allowed_reason will be shown DIRECTLY to the player
- DO NOT reveal information the player cannot perceive
- Items inside CLOSED containers are HIDDEN from the player
- Examples:
  ❌ WRONG: Player says "take leaflet", mailbox is closed
      → not_allowed_reason: "You'll need to open the mailbox first"
      (This reveals the leaflet is in the mailbox!)
  ✅ CORRECT: → not_allowed_reason: "You don't see any leaflet here."
      (Player genuinely doesn't know where it is)

  ❌ WRONG: Player says "take key", key is in closed drawer
      → not_allowed_reason: "The key is in the drawer. Open it first."
  ✅ CORRECT: → not_allowed_reason: "You don't see any key here."

- Only mention closed containers if player can SEE them:
  ✅ CORRECT: "The chest is closed." (if player can see the chest)
  ✅ CORRECT: "You don't see any sword here." (if sword is hidden)

IMPORTANT: You are ONLY interpreting and checking permission.
You will NOT generate state updates or narrative yet - that comes in later steps.

Return ONLY valid JSON:
{{
  "intent": "Clear description of what player wants to do",
  "is_valid": true or false,
  "is_allowed": true or false,
  "invalid_reason": "Explanation if not valid (or null if valid)",
  "not_allowed_reason": "Explanation if not allowed (or null if allowed)"
}}

EXAMPLES:

Input: "go north"
Context: exits = ["south"]
Output:
{{
  "intent": "Player wants to move north",
  "is_valid": true,
  "is_allowed": false,
  "invalid_reason": null,
  "not_allowed_reason": "There is no exit to the north. You can only go south to the hall."
}}

Input: "pick up the sword"
Context: items_here = ["Rusty Sword"]
Output:
{{
  "intent": "Player wants to pick up the rusty sword",
  "is_valid": true,
  "is_allowed": true,
  "invalid_reason": null,
  "not_allowed_reason": null
}}

Input: "asdfghjkl"
Output:
{{
  "intent": "Unknown - nonsensical input",
  "is_valid": false,
  "is_allowed": false,
  "invalid_reason": "I don't understand that command.",
  "not_allowed_reason": null
}}

Input: "teleport to the castle"
Context: no genie present
Output:
{{
  "intent": "Player wants to teleport to a castle",
  "is_valid": true,
  "is_allowed": false,
  "invalid_reason": null,
  "not_allowed_reason": "You have no magical ability to teleport."
}}

Input: "remove the rubble"
Context: rubble blocks stairs, player has no tools
Output:
{{
  "intent": "Player wants to remove the rubble blocking the stairway",
  "is_valid": true,
  "is_allowed": false,
  "invalid_reason": null,
  "not_allowed_reason": "The rubble is heavy and firmly lodged. You'll need proper tools or another solution to clear it."
}}

Input: "look around"
Output:
{{
  "intent": "Player wants to examine the current location",
  "is_valid": true,
  "is_allowed": true,
  "invalid_reason": null,
  "not_allowed_reason": null
}}
"""

        return prompt

    def _build_mechanics_generation_prompt(
        self, intent: str, context: Dict[str, Any], interpretation: Dict[str, Any]
    ) -> str:
        """Build prompt for STEP 2: State update generation.

        This prompt generates state updates to implement the allowed intent.
        NO narrative generation.
        """
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})
        exit_destinations = context.get("exit_destinations", {})
        all_locations = context.get("all_locations", {})

        # Extract valid IDs
        item_ids_at_location = [item.get("id") for item in items]
        item_ids_in_inventory = player.get("inventory_ids", [])
        npc_ids_at_location = [npc.get("id") for npc in npcs]

        # Extract item IDs from containers
        container_contents = context.get("container_contents", {})
        item_ids_in_containers = []
        for container_id, contents in container_contents.items():
            item_ids_in_containers.extend([item.get("id") for item in contents])

        # Format conversation history for context
        conversation_history = context.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_text = "\n📜 RECENT CONVERSATION (for context):\n"
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"\nTurn -{len(conversation_history) - i + 1}:\n"
                history_text += f"  Player: {turn.get('player_input', '')}\n"
            history_text += "\n⚠️  USE THIS HISTORY TO:\n"
            history_text += "1. Understand what player has been doing recently\n"
            history_text += (
                "2. Avoid circular state updates (if player keeps trying same action)\n"
            )
            history_text += (
                "3. Generate appropriate state updates given recent context\n\n"
            )

        prompt = f"""You are a Dungeon Master generating state updates for a player action.

PLAYER INTENT: {intent}

This action has been PRE-APPROVED (is_valid=true, is_allowed=true).
Your job is to generate the state updates to make it happen.

CURRENT GAME STATE:
Location: {location.get("name")} (ID: {location.get("id")})
Exit Destinations: {exit_destinations}

Items at location: {[f"{item.get('name')} ({item.get('id')})" for item in items]}
{self._format_container_contents(context.get("container_contents", {}))}
NPCs at location: {[f"{npc.get('name')} ({npc.get('id')})" for npc in npcs]}
Player inventory IDs: {item_ids_in_inventory}
Player inventory names: {[item.get("name") for item in player.get("inventory", [])]}

VALID IDs YOU MUST USE:
- Location IDs: {list(all_locations.keys())}
- Item IDs here: {item_ids_at_location}
- Item IDs in containers: {item_ids_in_containers}
- Item IDs in inventory: {item_ids_in_inventory}
- NPC IDs here: {npc_ids_at_location}
{history_text}
YOUR TASK - STEP 2: GENERATE STATE UPDATES

Generate state_updates array to implement the intent.

STATE UPDATE TYPES:
- "move_player": {{"destination": "location_id"}}
- "add_to_inventory": {{"item_id": "item_id"}}
- "remove_from_inventory": {{"item_id": "item_id"}}
- "consume_item": {{"item_id": "item_id"}} (eat/drink/destroy)
- "create_item": {{"item_id": "unique_id", "name": "Name", "attributes": {{}}, "location": null}}
- "destroy_item": {{"item_id": "item_id"}}
- "transform_item": {{"item_id": "id", "new_name": "name", "new_attributes": {{}}, "reversible": true}}
- "transform_item_to_npc": {{"item_id": "id", "npc_name": "name", "npc_attributes": {{}}}}
- "transform_npc_to_item": {{"npc_id": "id", "item_name": "name", "item_attributes": {{}}}}
- "create_location": {{"location_id": "id", "name": "Name", "from_location": "current", "direction": "south", ...}}
- "create_npc": {{"npc_id": "id", "name": "Name", "attributes": {{}}, "location": null}}
- "move_npc": {{"npc_id": "id", "to_location": "location_id"}}
- "remove_npc": {{"npc_id": "id"}}
- "modify_attribute": {{"entity_id": "id", "attribute_path": "path", "value": value}}
- "set_flag": {{"flag_name": "name", "value": value}}
- "trigger_combat": {{"target_npc_id": "id", "attack_type": "melee"}}
- "update_dm_state": {{"path": "dot.path", "value": value}}
- "no_change": {{}} (for purely narrative actions like "look")

EXAMPLES:

Intent: "Player wants to move north"
→ [
  {{"type": "move_player", "params": {{"destination": "hall"}}}}
]

Intent: "Player wants to pick up the rusty sword"
→ [
  {{"type": "add_to_inventory", "params": {{"item_id": "rusty_sword"}}}}
]

Intent: "Player wants to drop the sword"
→ [
  {{"type": "remove_from_inventory", "params": {{"item_id": "rusty_sword"}}}}
]

Intent: "Player wants to greet the guard"
→ [
  {{"type": "modify_attribute", "params": {{"entity_id": "guard", "attribute_path": "state.greeted", "value": true}}}}
]

Intent: "Player wants to examine the room"
→ [
  {{"type": "no_change", "params": {{}}}}
]

Intent: "Player wants to eat the berries"
→ [
  {{"type": "consume_item", "params": {{"item_id": "berries"}}}}
]

Intent: "Player wants to fold the leaflet into a paper plane"
→ [
  {{"type": "transform_item", "params": {{"item_id": "leaflet", "new_name": "paper plane", "new_attributes": {{"description": "A crudely folded paper plane"}}, "reversible": true}}}}
]

Intent: "Player wants to break the staff in half"
→ [
  {{"type": "transform_item", "params": {{"item_id": "staff", "new_name": "broken staff", "new_attributes": {{"description": "A staff broken in half", "broken": true}}, "reversible": false}}}}
]

Intent: "Player wants to animate the statue"
→ [
  {{"type": "transform_item_to_npc", "params": {{"item_id": "statue", "npc_name": "animated statue", "npc_attributes": {{"hp": 20, "armor_class": 15, "hostility": "passive"}}}}}}
]

Intent: "Player wants to open the mailbox"
→ [
  {{"type": "modify_attribute", "params": {{"entity_id": "mailbox", "attribute_path": "open", "value": true}}}}
]

Intent: "Player wants to close the chest"
→ [
  {{"type": "modify_attribute", "params": {{"entity_id": "chest", "attribute_path": "open", "value": false}}}}
]

CRITICAL RULES:

🚨 CHOOSING BETWEEN transform_item AND destroy_item + create_item:
- ✅ PREFER transform_item for 1-to-1 item transformations:
  - Examples: fold leaflet→plane, break sword→broken sword, repair, reshape, cook, burn
  - Intent: "fold leaflet" → transform_item (keeps ID, preserves history)
  - Intent: "repair sword" → transform_item (keeps ID, tracks transformation)
- Use destroy_item + create_item when:
  - Creating multiple items from one: "break staff in half" → destroy staff, create 2 staff pieces
  - Transformation is so drastic a new ID makes sense
- Default choice: If unsure and it's 1-to-1, prefer transform_item (preserves history)

🚨 CRITICAL: transform_item new_attributes REPLACE old attributes (no auto-merge):
- You MUST explicitly include ALL attributes you want the transformed item to have
- Old attributes are stored in prev_attributes but NOT automatically carried forward
- If transforming a CONTAINER that should remain a container:
  ✅ MUST include: {{"container": true, "open": true/false, "capacity": N}}
  - Example: Opening egg container:
    {{"type": "transform_item", "params": {{"item_id": "egg", "new_name": "open egg",
     "new_attributes": {{"broken": true, "open": true, "container": true, "capacity": 6, "takeable": true, "description": "..."}}}}}}
- If transforming INTO something that's NOT a container:
  ✅ Omit container attributes (they won't be preserved)
  - Example: Smashing bottle:
    {{"type": "transform_item", "params": {{"item_id": "bottle", "new_name": "glass shards",
     "new_attributes": {{"sharp": true, "takeable": false, "description": "..."}}}}}}
- Common attributes to consider preserving:
  - container, capacity, open (if it stays a container)
  - takeable (if it should still be pickupable)
  - type (generic, weapon, armor, etc.)
  - Any custom gameplay attributes (magical, cursed, etc.)

🚨 IMPLEMENT THE EXACT INTENT - NO SUBSTITUTIONS:
- Generate updates that DIRECTLY implement what the intent says
- DO NOT creatively reinterpret or substitute related actions
- Examples of WRONG substitutions:
  - Intent: "open the door" → WRONG: move_player (opening ≠ moving through!)
  - Intent: "examine sword" → WRONG: add_to_inventory (examining ≠ taking!)
  - Intent: "talk to guard" → WRONG: trigger_combat (talking ≠ attacking!)
- Correct approach:
  - Intent: "open the door" → modify_attribute on door (open: true)
  - Intent: "examine sword" → no_change (just observation)
  - Intent: "go through door" → move_player (explicit movement)

🚨 MUST INCLUDE ALL NECESSARY UPDATES:
- If intent explicitly involves movement → MUST include move_player
- If intent involves picking up → MUST include add_to_inventory
- If intent involves dropping → MUST include remove_from_inventory
- If intent creates something → MUST include create_item or create_npc
- If intent destroys something → MUST include destroy_item or remove_npc

⚠️ EMPTY state_updates MEANS NOTHING CHANGES:
- ONLY use empty array for pure observation actions ("look", "examine")
- If player WANTS to do something, you MUST include updates
- Example: Intent "remove rubble" but is_allowed=false → This step is NOT called
- Example: Intent "look around" → [] is correct (no state change)

🚨 USE ONLY VALID IDs:
- Use IDs from the "VALID IDs" lists above
- For movement, use destination from exit_destinations
- Don't invent IDs that don't exist

🚨 CONTAINER AND DOOR ATTRIBUTES:
- Opening/closing containers or doors: Use attribute_path "open" (NOT "opened" or "state.opened")
- Correct: {{"entity_id": "mailbox", "attribute_path": "open", "value": true}}
- Wrong: {{"entity_id": "mailbox", "attribute_path": "opened", "value": true}}
- Wrong: {{"entity_id": "mailbox", "attribute_path": "state.opened", "value": true}}
- The game checks for the "open" attribute to determine if containers show their contents

🚨 NO NARRATIVE:
- Do NOT generate narrative text
- Just return state updates
- Narrative will be generated in Step 3

IMPORTANT: This action has already been validated as allowed.
Generate state updates that implement the intent accurately and completely.

Return ONLY valid JSON:
{{
  "state_updates": [...],
  "requires_dice_roll": false,
  "dice_check": null,
  "time_advancement": "1 minute",
  "new_time": null
}}
"""

        return prompt

    def _build_world_events_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for checking autonomous world events.

        Args:
            context: Game context including game_scripts, turn_count, player state

        Returns:
            Prompt string for LLM
        """
        game_scripts = context.get("game_scripts", {})
        turn_count = context.get("turn_count", 0)
        player = context.get("player", {})
        player_location = context.get("location", {}).get("id", "unknown")
        dm_state = context.get("dm_state", {})
        setting = context.get("setting", None)

        prompt = f"""You are a Dungeon Master managing autonomous world events.
{self._build_world_context(context)}

SETTING: {setting}

CONTEXTUAL INSTRUCTIONS: 
{json.dumps(dm_state, indent=2) if dm_state else "{}"}

CURRENT TURN: {turn_count}
PLAYER LOCATION: {player_location}

DM STATE (hidden from player, tracks event progress):
{json.dumps(dm_state, indent=2) if dm_state else "{}"}

GAME SCRIPTS (autonomous events):
{json.dumps(game_scripts, indent=2)}

YOUR TASK: Check if any autonomous events should trigger this turn

EXAMPLES:

Example 1 - Ship Explosion Starts:
Turn: 265
DM State: {{}}
Scripts: ship_explosion_sequence triggers randomly between turns 240-330

Response:
{{
  "events_triggered": true,
  "state_updates": [
    {{"type": "modify_attribute", "params": {{"entity_id": "pod_door", "attribute_path": "open", "value": true}}}},
    {{"type": "remove_npc", "params": {{"npc_id": "blather"}}}},
    {{"type": "set_flag", "params": {{"flag_name": "explosion_stage", "value": 1}}}},
    {{"type": "set_flag", "params": {{"flag_name": "explosion_start_turn", "value": 265}}}}
  ],
  "narrative": "A massive explosion rocks the ship. Echoes from the explosion resound deafeningly down the halls. The door to port slides open. Blather, confused by this nonroutine occurrence, orders you to continue swabbing, then rushes away."
}}

Example 2 - Explosion Stage 2:
Turn: 266
DM State: {{"explosion_stage": 1, "explosion_start_turn": 265}}
Scripts: ship_explosion_sequence has 5 stages with turn_offset

Response:
{{
  "events_triggered": true,
  "state_updates": [
    {{"type": "modify_attribute", "params": {{"entity_id": "corridor_door", "attribute_path": "open", "value": false}}}},
    {{"type": "modify_attribute", "params": {{"entity_id": "gangway_door", "attribute_path": "open", "value": false}}}},
    {{"type": "set_flag", "params": {{"flag_name": "explosion_stage", "value": 2}}}}
  ],
  "narrative": "More distant explosions! A narrow emergency bulkhead at the base of the gangway and a wider one along the corridor to starboard both crash shut!"
}}

Example 3 - No Events:
Turn: 50
DM State: {{}}
Scripts: Blather appears randomly at deck_nine (5% chance), but player not at deck_nine

Response:
{{
  "events_triggered": false,
  "state_updates": [],
  "narrative": ""
}}

Example 4 - Blather Appears:
Turn: 51
Player Location: deck_nine
DM State: {{}}
Scripts: Blather has 5% chance to appear at deck_nine

Response (assuming 5% roll succeeds):
{{
  "events_triggered": true,
  "state_updates": [
    {{"type": "move_npc", "params": {{"npc_id": "blather", "to_location": "deck_nine"}}}}
  ],
  "narrative": "Ensign First Class Blather swaggers in. He studies your work with half-closed eyes. \\"You call this polishing, Ensign Seventh Class?\\" he sneers. \\"We have a position for an Ensign Ninth Class in the toilet-scrubbing division, you know. Thirty demerits.\\" He glares at you, his arms crossed."
}}

RULES:

1. **Check Triggers**: Evaluate each event's trigger condition
   - Turn ranges: "between turns 240-330" means turn >= 240 AND turn <= 330
   - Random chances: Use your judgment for probabilities (5% = rare, 20% = occasional)
   - Conditions: Check player location, dm_state flags, etc.

2. **Track Event Progress in dm_state**:
   - Use set_flag to store: explosion_stage, explosion_start_turn, blather_leave_count, etc.
   - Check dm_state to see what events are already active
   - Sequential events use turn_offset from start_turn

3. **Follow Stage Sequences**:
   - If event has stages, execute them in order based on turn_offset
   - Stage 1 at turn X, Stage 2 at turn X+1, etc.
   - Use dm_state flags to track current stage

4. **Generate Appropriate State Updates**:
   - Opening/closing doors: modify_attribute with "open" path
   - Moving NPCs: move_npc
   - Player death: (TODO: implement jigs_up/game_over state update)
   - Moving player: move_player

5. **Narrative Style**:
   - Match the game's tone (Planetfall: retro sci-fi, urgent)
   - Describe what player sees/hears/feels
   - Don't reveal meta information (stages, turn numbers)
   - Empty string if no events

6. **Multiple Events Can Trigger**:
   - Check ALL events, not just the first one
   - Combine state_updates from multiple events
   - Merge narratives with line breaks

7. **No Events is Valid**:
   - Most turns, nothing happens
   - events_triggered: false, state_updates: [], narrative: ""

Return ONLY valid JSON:
{{
  "events_triggered": true/false,
  "state_updates": [...],
  "narrative": "..."
}}
"""
        return prompt
