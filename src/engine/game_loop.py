"""Main game loop."""

import logging
from typing import List, Optional, Dict, Any, Set
from ..models.game_state import GameState
from ..llm.gemini_client import GeminiClient
from ..llm.zil_translator import ensure_zil_translations
from ..rules.rule_engine import RuleEngine
from .action_processor import ActionProcessor

logger = logging.getLogger(__name__)


class GameLoop:
    """Main game loop orchestrator."""

    def __init__(
        self,
        game_state: GameState,
        gemini_client: GeminiClient,
        rule_engine: RuleEngine,
        zil_translator_client: Optional[GeminiClient] = None,
    ):
        self.game_state = game_state
        self.gemini = gemini_client
        self.rule_engine = rule_engine
        self.action_processor = ActionProcessor(rule_engine)
        self.running = False
        self.last_referenced_item: Optional[str] = None  # For pronoun resolution
        self.last_referenced_npc: Optional[str] = None
        # Use separate client for ZIL translation (more capable model)
        self.zil_translator = zil_translator_client if zil_translator_client else gemini_client

    def execute_single_step(self, command: str) -> dict:
        """Execute a single command and return full result.

        This method is designed for testing and single-step execution mode.
        It executes one turn, gathers the result, and returns all relevant
        information without entering the interactive loop.

        Args:
            command: Player command to execute

        Returns:
            dict containing:
            - command: The command executed
            - narrative: Generated narrative response
            - interpretation: Full LLM interpretation
            - location: Current location info (id, name)
            - player_location: Location ID
            - exits: Available exits list
            - inventory: Player inventory items (names)
            - turn_count: Current turn number
        """
        # Execute the turn
        narrative, interpretation = self.process_turn(command)

        # Check if this was a location-describing action (movement or look)
        state_updates = interpretation.get("state_updates", [])
        is_movement = any(update.get("type") == "move_player" for update in state_updates)

        # Detect "look" or "examine" commands by checking if there are no state updates
        # and the command is about examining the location
        is_look = (len(state_updates) == 0 and
                  any(word in command.lower() for word in ["look", "examine", "l "]))

        if is_movement or is_look:
            # Generate room description for the new location
            location = self.game_state.get_player_location()
            if location:
                items = self.game_state.get_items_at_location(self.game_state.player_location)
                npcs = self.game_state.get_npcs_at_location(self.game_state.player_location)

                # Get lighting information
                lighting = self.game_state.get_effective_lighting(
                    self.game_state.player_location
                )

                # Build player context for description
                player_context = {
                    "inventory_ids": self.game_state.player.inventory,
                    "inventory_items": [
                        self.game_state.items[item_id].name
                        for item_id in self.game_state.player.inventory
                        if item_id in self.game_state.items
                    ],
                    "attributes": self.game_state.player.attributes,
                }

                world_context = self.game_state.world_context

                # Ensure ZIL translations are available and get dictified versions
                location_dict, items_dicts, npcs_dicts = ensure_zil_translations(
                    self.zil_translator,
                    location=location,
                    items=items,
                    npcs=npcs
                )

                # Gather cached descriptions for consistency
                cached_descriptions = self._get_cached_descriptions_for_location(
                    location.id, items, npcs
                )

                # Generate description using translated dicts
                narrative = self.gemini.describe_location(
                    location_dict,
                    items_dicts,
                    npcs_dicts,
                    player_context=player_context,
                    world_context=world_context,
                    lighting_info=lighting,
                    cached_descriptions=cached_descriptions,
                )

                # Add container contents with LLM-generated prose (Zork-style)
                for item in items:
                    if item.attributes.get("container") and item.attributes.get("open"):
                        contents = self.game_state.get_items_in_container(item.id)
                        if contents:
                            # Build context for container description (same as main description)
                            container_context = {
                                "location": location.model_dump(),
                                "lighting_info": lighting,
                                "player": {
                                    "attributes": self.game_state.player.attributes,
                                    "inventory": player_context["inventory_items"]
                                }
                            }
                            # Generate natural prose for container contents (with full context)
                            container_desc = self.gemini.describe_container_contents(
                                item.model_dump(),
                                [c.model_dump() for c in contents],
                                context=container_context
                            )
                            # Only add if there's content (empty if cannot see)
                            if container_desc and container_desc.strip():
                                narrative += f"\n\n{container_desc}"

                # Update conversation history with complete narrative (including containers)
                self.game_state.update_last_narrative(narrative)

                # Cache the generated description with current state
                self.game_state.cache_description(
                    "location",
                    location.id,
                    narrative,
                    state_snapshot={
                        "game_time": self.game_state.game_time,
                        "lighting": lighting.get("level"),
                        "turn": self.game_state.turn_count,
                        "item_ids": [item.id for item in items],
                        "npc_ids": [npc.id for npc in npcs]
                    }
                )

            # Check for dungeon exit (rogue mode only)
            if is_movement and self.game_state.rogue_config and self.game_state.rogue_config.get("enabled"):
                current_location = self.game_state.get_player_location()
                if current_location and current_location.attributes.get("is_dungeon_exit"):
                    # In single-step mode, we can't show the interactive transition
                    # Just append a note to the narrative
                    narrative += "\n\n[You've reached the exit to the next level!]"

        # Gather current state
        location = self.game_state.get_player_location()
        exits = location.get_available_exits() if location else []

        inventory_items = [
            self.game_state.items[item_id].name
            for item_id in self.game_state.player.inventory
            if item_id in self.game_state.items
        ]

        return {
            "command": command,
            "narrative": narrative,
            "interpretation": interpretation,
            "location": {
                "id": location.id if location else "unknown",
                "name": location.name if location else "Unknown",
            },
            "player_location": self.game_state.player_location,
            "exits": exits,
            "inventory": inventory_items,
            "turn_count": self.game_state.turn_count,
        }

    def start(self) -> None:
        """Start the game loop."""
        self.running = True
        print("=" * 60)
        print("INTERACTIVE FICTION ENGINE - MVP")
        print("=" * 60)
        print()

        # Display intro text if present in world_context
        if self.game_state.world_context and "intro" in self.game_state.world_context:
            intro = self.game_state.world_context["intro"]
            print(intro)
            print()

        # Show initial location
        self._show_location()

        # Main loop
        while self.running:
            try:
                self._game_turn()
            except KeyboardInterrupt:
                print("\n\nGame interrupted. Goodbye!")
                self.running = False
            except Exception as e:
                print(f"\nError: {e}")
                import traceback

                traceback.print_exc()

    def process_turn(self, player_input: str) -> tuple[str, Dict[str, Any]]:
        """Process a single turn and return results (for testing).

        Uses three-step approach:
        1. Interpret intent and check permission (is_valid, is_allowed)
        2. Generate state updates (only if allowed)
        3. Apply updates, then generate narrative from actual state

        Args:
            player_input: Player's input string

        Returns:
            Tuple of (narrative_response, interpretation)
        """
        # STEP 1: Build context and interpret intent
        context = self._build_context()

        # Ensure ZIL translations are available (on-demand translation with caching)
        # Update context with translated versions
        location_dict, items_dicts, npcs_dicts = ensure_zil_translations(
            self.zil_translator,
            location=context.get("location"),
            items=context.get("items", []),
            npcs=context.get("npcs", [])
        )

        # Update context with translated dictionaries
        if location_dict:
            context["location"] = location_dict
        if items_dicts:
            context["items"] = items_dicts
        if npcs_dicts:
            context["npcs"] = npcs_dicts

        # Add pronoun resolution hints to context
        if self.last_referenced_item:
            context["last_item"] = self.last_referenced_item
        if self.last_referenced_npc:
            context["last_npc"] = self.last_referenced_npc

        # Interpret intent and check permission
        intent_result = self.gemini.interpret_intent(player_input, context)
        intent = intent_result["intent"]
        is_valid = intent_result["is_valid"]
        is_allowed = intent_result["is_allowed"]
        invalid_reason = intent_result.get("invalid_reason")
        not_allowed_reason = intent_result.get("not_allowed_reason")

        # STEP 2: Generate mechanics (only if valid AND allowed)
        state_updates = []
        mechanics_result = {}
        if is_valid and is_allowed:
            mechanics_result = self.gemini.generate_state_updates(intent, context, intent_result)
            state_updates = mechanics_result.get("state_updates", [])

            # Track what was referenced for pronoun resolution
            # Build temporary interpretation for tracking
            temp_interpretation = {**intent_result, **mechanics_result}
            self._update_reference_tracking(temp_interpretation, player_input, context)

        # Extract metadata about current state BEFORE applying updates
        action_metadata = self._extract_action_metadata(state_updates, context)

        # Track previous location for chase mechanics
        previous_location = self.game_state.player_location

        # Apply state updates
        if state_updates:
            self.action_processor.apply_state_updates(state_updates, self.game_state)

        # Apply time advancement (DM controls time)
        if mechanics_result.get("new_time"):
            self.game_state.game_time = mechanics_result["new_time"]

        # STEP 3: Generate narrative
        is_movement = any(update.get("type") == "move_player" for update in state_updates)

        if is_movement:
            # For movement, skip narrative - location description will show new state
            narrative = ""
        else:
            # For non-movement actions, generate narrative from current state
            updated_context = self._build_context()
            narrative = self.gemini.generate_narrative(
                player_input,
                intent,
                updated_context,
                action_metadata=action_metadata,
                state_updates=state_updates,  # Pass state updates so LLM can narrate what changed
                is_valid=is_valid,
                invalid_reason=invalid_reason,
                not_allowed_reason=not_allowed_reason
            )

        # Combine results for backward compatibility
        interpretation = {**intent_result, **mechanics_result, "narrative_response": narrative}

        # Process NPC turns (aggressive NPCs attack, chase fleeing player)
        npc_actions = self.action_processor.process_npc_turns(
            self.game_state,
            player_moved=is_movement,
            previous_location=previous_location if is_movement else None
        )

        # Store NPC actions in interpretation for testing
        interpretation["npc_actions"] = npc_actions

        # Increment turn
        self.game_state.add_history_entry(
            {
                "turn": self.game_state.turn_count,
                "input": player_input,
                "interpretation": interpretation,
            }
        )

        return narrative, interpretation

    def _game_turn(self) -> None:
        """Execute one turn of the game."""
        # Get player input
        player_input = input("\n> ").strip()

        if not player_input:
            return

        # Handle special commands
        if player_input.lower() in ["quit", "exit", "q"]:
            self.running = False
            print("Thanks for playing!")
            return

        if player_input.lower() in ["help", "?"]:
            self._show_help()
            return

        # Handle "look" specially - use dedicated location description
        if player_input.lower() in ["look", "l"]:
            print()
            self._show_location()
            return

        # Handle "inventory" specially - just show what player has
        if player_input.lower() in ["inventory", "inv", "i"]:
            self._show_inventory()
            return

        # Handle save command
        if player_input.lower().startswith("save"):
            parts = player_input.split()
            if len(parts) == 1:
                # Default save file
                save_path = "saves/quicksave.json"
            else:
                # Custom save file
                filename = parts[1]
                if not filename.endswith('.json'):
                    filename += '.json'
                save_path = f"saves/{filename}"

            # Create saves directory if needed
            import os
            os.makedirs("saves", exist_ok=True)

            # Save game
            self.game_state.to_file(save_path)
            print(f"\nGame saved to {save_path}")
            return

        # Handle load command
        if player_input.lower().startswith("load"):
            parts = player_input.split()
            if len(parts) == 1:
                # Default save file
                load_path = "saves/quicksave.json"
            else:
                # Custom save file
                filename = parts[1]
                if not filename.endswith('.json'):
                    filename += '.json'
                load_path = f"saves/{filename}"

            # Check if file exists
            import os
            if not os.path.exists(load_path):
                print(f"\nError: Save file not found: {load_path}")
                return

            # Load game
            try:
                loaded_state = GameState.from_file(load_path)
                # Replace current game state
                self.game_state = loaded_state
                print(f"\nGame loaded from {load_path}")
                print()
                self._show_location()
            except Exception as e:
                print(f"\nError loading save file: {e}")
            return

        # STEP 1: Interpret intent and check permission
        print("[DM interprets your action...]")
        context = self._build_context()

        # Add pronoun resolution hints to context
        if self.last_referenced_item:
            context["last_item"] = self.last_referenced_item
        if self.last_referenced_npc:
            context["last_npc"] = self.last_referenced_npc

        # Interpret intent and check permission
        intent_result = self.gemini.interpret_intent(player_input, context)
        intent = intent_result["intent"]
        is_valid = intent_result["is_valid"]
        is_allowed = intent_result["is_allowed"]
        invalid_reason = intent_result.get("invalid_reason")
        not_allowed_reason = intent_result.get("not_allowed_reason")

        # Log what LLM returned
        logger.debug("Intent Interpretation:")
        logger.debug(f"  Intent: {intent}")
        logger.debug(f"  is_valid: {is_valid}")
        logger.debug(f"  is_allowed: {is_allowed}")
        if invalid_reason:
            logger.debug(f"  invalid_reason: {invalid_reason}")
        if not_allowed_reason:
            logger.debug(f"  not_allowed_reason: {not_allowed_reason}")

        # STEP 2: Generate mechanics (only if valid AND allowed)
        state_updates = []
        mechanics_result = {}
        if is_valid and is_allowed:
            print("[DM generates mechanics...]")
            mechanics_result = self.gemini.generate_state_updates(intent, context, intent_result)
            state_updates = mechanics_result.get("state_updates", [])

            logger.debug("Mechanics:")
            logger.debug(f"  State Updates: {state_updates}")

            # Track what was referenced for pronoun resolution
            temp_interpretation = {**intent_result, **mechanics_result}
            self._update_reference_tracking(temp_interpretation, player_input, context)

        # Extract metadata about current state BEFORE applying updates
        action_metadata = self._extract_action_metadata(state_updates, context)

        # Track previous location for chase mechanics
        previous_location = self.game_state.player_location

        # Apply state updates
        if state_updates:
            self.action_processor.apply_state_updates(state_updates, self.game_state)

        # Apply time advancement (DM controls time)
        if mechanics_result.get("new_time"):
            self.game_state.game_time = mechanics_result["new_time"]

            # Log state after updates
            logger.debug("State After Updates:")
            logger.debug(f"  Player location: {self.game_state.player_location}")
            logger.debug(f"  Player inventory: {self.game_state.player.inventory}")
            logger.debug(
                f"  Items at location: {[item.name for item in self.game_state.get_items_at_location(self.game_state.player_location)]}"
            )
            logger.debug(f"  Item locations: {self.game_state.item_locations}")
            logger.debug(
                f"  NPCs at location: {[npc.name for npc in self.game_state.get_npcs_at_location(self.game_state.player_location)]}"
            )
            logger.debug(f"  NPC locations: {self.game_state.npc_locations}")

        # STEP 3: Generate narrative (skip for movement - location description handles that)
        is_movement = any(update.get("type") == "move_player" for update in state_updates)

        if is_movement:
            # For movement, skip narrative - location description will show new state
            narrative = ""
        else:
            # For non-movement actions, generate narrative from current state
            print("[DM narrates what happened...]")
            updated_context = self._build_context()
            narrative = self.gemini.generate_narrative(
                player_input,
                intent,
                updated_context,
                action_metadata=action_metadata,
                state_updates=state_updates,  # Pass state updates so LLM can narrate what changed
                is_valid=is_valid,
                invalid_reason=invalid_reason,
                not_allowed_reason=not_allowed_reason
            )

        # Combine results for backward compatibility
        interpretation = {**intent_result, **mechanics_result, "narrative_response": narrative}

        # Show narrative response (if any)
        if narrative:
            print(f"\n{narrative}")

        # Show combat results if combat occurred
        if "last_combat_result" in self.game_state.flags:
            combat_result = self.game_state.flags.pop("last_combat_result")
            self._show_combat_result(combat_result)

            # Get LLM narration of combat outcome
            print("\n[DM narrates the outcome...]")
            combat_narration = self.gemini.narrate_combat_result(combat_result)
            print(f"\n{combat_narration}")

        # If player moved, show new location
        if any(update.get("type") == "move_player" for update in state_updates):
            print()
            self._show_location()

            # Check for dungeon exit (rogue mode only)
            if self.game_state.rogue_config and self.game_state.rogue_config.get("enabled"):
                current_location = self.game_state.get_player_location()
                if current_location and current_location.attributes.get("is_dungeon_exit"):
                    self._handle_level_transition()

        # Process NPC turns (aggressive NPCs attack, chase fleeing player)
        player_moved = any(update.get("type") == "move_player" for update in state_updates)
        npc_actions = self.action_processor.process_npc_turns(
            self.game_state,
            player_moved=player_moved,
            previous_location=previous_location if player_moved else None
        )

        # Show NPC actions (chases, attacks) with LLM narration - immediately after they occur
        if npc_actions["npc_attacks"] or npc_actions["npc_chases"]:
            # Show mechanical details first (dice rolls for transparency)
            print("\n" + "=" * 50)

            # Chase messages
            for chase in npc_actions.get("npc_chases", []):
                npc_name = chase.get("npc_name", "NPC")
                hp_percent = chase.get("hp_percent", 0) * 100
                print(f"⚠️  {npc_name} chases after you! (HP: {hp_percent:.0f}%)")

            # Attack mechanics
            for attack_info in npc_actions.get("npc_attacks", []):
                npc_name = attack_info.get("npc_name", "NPC")
                attack = attack_info.get("attack", {})

                print(f"\n⚔️  {npc_name.upper()} ATTACKS!")
                self._show_single_attack(attack)

            print("=" * 50)

            # Generate LLM narration for all NPC actions with current game context
            print("\n[DM narrates the chaos...]")
            context = self._build_context()
            npc_narrative = self.gemini.narrate_npc_actions(npc_actions, context)
            print(f"\n{npc_narrative}")

        # WORLD TICK: Allow DM to trigger autonomous events after player's action
        self._process_world_tick()

        # Increment turn
        self.game_state.add_history_entry(
            {
                "turn": self.game_state.turn_count,
                "input": player_input,
                "interpretation": interpretation,
            }
        )

    def _process_world_tick(self) -> None:
        """Process autonomous world events independent of player actions.

        This is called after the player's action is complete. The DM can:
        - Move NPCs
        - Trigger scripted events (like Planetfall's ship explosion)
        - Update world state based on time/conditions
        """
        logger.debug(f"World Tick: Turn {self.game_state.turn_count}")

        # Check if world has game_scripts
        if not self.game_state.world_context:
            logger.debug("World Tick: No world_context found")
            return

        if "game_scripts" not in self.game_state.world_context:
            logger.debug("World Tick: No game_scripts in world_context")
            # TODO: In future, allow DM to be creative with autonomous events
            # even without explicit scripts
            return

        game_scripts = self.game_state.world_context["game_scripts"]
        logger.debug("World Tick: game_scripts found, checking events...")

        # Build context for DM
        context = self._build_context()
        context["game_scripts"] = game_scripts
        context["turn_count"] = self.game_state.turn_count
        context["dm_state"] = self.game_state.flags  # Use flags to track event state

        if self.game_state.world_context:
            context["dm_instructions"] = self.game_state.world_context.get("dm_instructions")
            context["author"] = self.game_state.world_context.get("author")
            context["setting"] = self.game_state.world_context.get("setting")
            context["tone"] = self.game_state.world_context.get("tone")

        # Ask DM if any autonomous events should trigger
        logger.debug("World Tick: Calling DM to check events...")
        world_tick_result = self.gemini.check_world_events(context)
        logger.debug(f"World Tick: DM returned: {world_tick_result}")

        if not world_tick_result or not world_tick_result.get("events_triggered"):
            logger.debug("World Tick: No events triggered")
            return

        logger.debug("World Tick: Events triggered!")

        # Apply state updates from autonomous events
        state_updates = world_tick_result.get("state_updates", [])
        if state_updates:
            logger.debug(f"World Tick: Applying {len(state_updates)} autonomous state updates")
            self.action_processor.apply_state_updates(state_updates, self.game_state)

        # Show narrative for autonomous events
        narrative = world_tick_result.get("narrative", "")
        if narrative:
            print(f"\n{narrative}")

    def _show_location(self) -> None:
        """Show current location description."""
        print("[Generating description...]")

        location = self.game_state.get_player_location()
        if not location:
            print("You are nowhere.")
            return

        items = self.game_state.get_items_at_location(self.game_state.player_location)
        npcs = self.game_state.get_npcs_at_location(self.game_state.player_location)

        # Get lighting information (for LLM context, not shown to player)
        lighting = self.game_state.get_effective_lighting(
            self.game_state.player_location
        )

        # Build player context for description
        player_context = {
            "inventory_ids": self.game_state.player.inventory,
            "inventory_items": [
                self.game_state.items[item_id].name
                for item_id in self.game_state.player.inventory
                if item_id in self.game_state.items
            ],
            "attributes": self.game_state.player.attributes,
            "game_time": self.game_state.game_time,  # Current in-game time
        }

        world_context = self.game_state.world_context

        # Ensure ZIL translations are available and get dictified versions
        location_dict, items_dicts, npcs_dicts = ensure_zil_translations(
            self.zil_translator,
            location=location,
            items=items,
            npcs=npcs
        )

        # Gather cached descriptions for consistency
        cached_descriptions = self._get_cached_descriptions_for_location(
            location.id, items, npcs
        )

        description = self.gemini.describe_location(
            location_dict,
            items_dicts,
            npcs_dicts,
            player_context=player_context,
            world_context=world_context,
            lighting_info=lighting,
            cached_descriptions=cached_descriptions,
        )

        # Generate container contents descriptions (for caching in history)
        container_descriptions = []
        for item in items:
            if item.attributes.get("container") and item.attributes.get("open"):
                container_id = item.id
                contents = self.game_state.get_items_in_container(container_id)
                if contents:
                    # Build context for container description (same as main description)
                    container_context = {
                        "location": location.model_dump(),
                        "lighting_info": lighting,
                        "player": {
                            "attributes": self.game_state.player.attributes,
                            "inventory": player_context["inventory_items"]
                        }
                    }
                    # Generate natural prose for container contents (with full context)
                    container_desc = self.gemini.describe_container_contents(
                        item.model_dump(),
                        [c.model_dump() for c in contents],
                        context=container_context
                    )
                    # Only add if there's content (empty if cannot see)
                    if container_desc and container_desc.strip():
                        container_descriptions.append(container_desc)

        # Append container descriptions to main description for caching
        full_description = description
        if container_descriptions:
            full_description += "\n\n" + "\n\n".join(container_descriptions)

        # Display to player
        print(f"\n{full_description}")

        # Update conversation history with complete description (including containers)
        # This ensures the LLM has full context in subsequent prompts
        self.game_state.update_last_narrative(full_description)

        # Cache the FULL description (including container contents) with current state
        self.game_state.cache_description(
            "location",
            location.id,
            full_description,
            state_snapshot={
                "game_time": self.game_state.game_time,
                "lighting": lighting.get("level"),
                "turn": self.game_state.turn_count,
                "item_ids": [item.id for item in items],
                "npc_ids": [npc.id for npc in npcs]
            }
        )

    def _get_cached_descriptions_for_location(
        self, location_id: str, items: list, npcs: list
    ) -> dict:
        """Gather cached descriptions for a location and its contents.

        Args:
            location_id: ID of the location
            items: List of Item objects at the location
            npcs: List of NPC objects at the location

        Returns:
            Dict with cached descriptions for location, items, and npcs
        """
        cached = {}

        # Get current item and NPC IDs for cache validation
        current_item_ids = [item.id for item in items]
        current_npc_ids = [npc.id for npc in npcs]

        # Get cached location description (with validation)
        location_cache = self.game_state.get_cached_description(
            "location",
            location_id,
            current_item_ids=current_item_ids,
            current_npc_ids=current_npc_ids
        )
        if location_cache:
            cached["location"] = location_cache

        # Get cached item descriptions
        items_cache = {}
        for item in items:
            item_cache = self.game_state.get_cached_description("item", item.id)
            if item_cache:
                items_cache[item.id] = {
                    "name": item.name,
                    "description": item_cache["description"],
                    "turn": item_cache["turn"],
                }
        if items_cache:
            cached["items"] = items_cache

        # Get cached NPC descriptions
        npcs_cache = {}
        for npc in npcs:
            npc_cache = self.game_state.get_cached_description("npc", npc.id)
            if npc_cache:
                npcs_cache[npc.id] = {
                    "name": npc.name,
                    "description": npc_cache["description"],
                    "turn": npc_cache["turn"],
                }
        if npcs_cache:
            cached["npcs"] = npcs_cache

        return cached

    def _show_help(self) -> None:
        """Show help text."""
        print(
            """
Available commands:
  - look (l): Examine your surroundings
  - inventory (inv, i): Show your inventory
  - go <direction>: Move in a direction (north, south, east, west)
  - take <item>: Pick up an item
  - attack <target>: Attack an NPC
  - save [filename]: Save game (default: quicksave.json)
  - load [filename]: Load game (default: quicksave.json)
  - help (?): Show this help
  - quit (q): Exit the game

You can also type natural language commands and the AI will interpret them.
"""
        )

    def _show_inventory(self) -> None:
        """Show player inventory."""
        if not self.game_state.player.inventory:
            print("\nYou aren't carrying anything.")
            return

        print("\nYou are carrying:")
        for item_id in self.game_state.player.inventory:
            if item_id in self.game_state.items:
                item = self.game_state.items[item_id]
                print(f"  - {item.name}")

    def _show_combat_result(self, result: Dict[str, Any]) -> None:
        """Display combat results with dice rolls."""
        if not result.get("success"):
            return

        print("\n" + "=" * 50)
        print("⚔️  COMBAT ROUND")
        print("=" * 50)

        # Show player's attack
        player_attack = result.get("player_attack", {})
        if player_attack:
            print("\n🗡️  YOUR ATTACK:")
            self._show_single_attack(player_attack)

        # Show NPC's counterattack
        npc_attack = result.get("npc_attack")
        if npc_attack:
            print("\n🛡️  ENEMY COUNTERATTACK:")
            self._show_single_attack(npc_attack)

        print("=" * 50)

    def _show_single_attack(self, attack: Dict[str, Any]) -> None:
        """Display a single attack's results."""
        attacker = attack.get("attacker_name", "Attacker")
        target = attack.get("target_name", "Target")
        weapon = attack.get("weapon_name", "weapon")

        if attack.get("hit"):
            attack_mod = attack.get("attack_modifier", 0)
            mod_str = f"+{attack_mod}" if attack_mod >= 0 else str(attack_mod)
            print(
                f"  🎲 Attack Roll: {attack.get('attack_roll')} {mod_str} = {attack.get('attack_total')}"
            )
            print(f"  🛡️  Target AC: {attack.get('target_ac')}")
            print("  ✅ HIT!")

            # Format damage roll
            damage_notation = attack.get("damage_notation", "1d6")
            damage_rolls = attack.get("damage_rolls", [])
            damage_mod = attack.get("damage_modifier", 0)
            damage_total = attack.get("damage_total", 0)

            if damage_mod != 0:
                mod_str = f"+{damage_mod}" if damage_mod > 0 else str(damage_mod)
                damage_str = (
                    f"{damage_notation}{mod_str} ({damage_rolls}) = {damage_total}"
                )
            else:
                damage_str = f"{damage_notation} ({damage_rolls}) = {damage_total}"

            print(f"  💥 Damage: {damage_str}")
            print(
                f"  ❤️  {target} HP: {attack.get('target_hp')}/{attack.get('target_max_hp')}"
            )

            if attack.get("target_dead"):
                print(f"  💀 {target.upper()} SLAIN!")
        else:
            attack_mod = attack.get("attack_modifier", 0)
            mod_str = f"+{attack_mod}" if attack_mod >= 0 else str(attack_mod)
            print(
                f"  🎲 Attack Roll: {attack.get('attack_roll')} {mod_str} = {attack.get('attack_total')}"
            )
            print(f"  🛡️  Target AC: {attack.get('target_ac')}")
            print("  ❌ MISS!")

    def _update_reference_tracking(
        self,
        interpretation: Dict[str, Any],
        player_input: str,
        context: Dict[str, Any],
    ) -> None:
        """Update tracking of last referenced items/NPCs for pronoun resolution.

        Checks both state updates AND the player's input to track what entities
        were mentioned, even for narrative-only actions.
        """
        # First, check player input for explicit mentions of NPCs and items
        # This catches cases like "tickle the rat" where there are no state updates
        player_input_lower = player_input.lower()

        # Common words to ignore when matching
        ignore_words = {"the", "a", "an", "some", "my", "your"}

        # Check for NPCs mentioned in player input
        npcs_at_location = context.get("npcs", [])
        for npc in npcs_at_location:
            npc_name = npc.get("name", "").lower()
            npc_id = npc.get("id")
            if npc_name and npc_id:
                # Try exact match first
                if npc_name in player_input_lower:
                    self.last_referenced_npc = npc_id
                else:
                    # Try matching individual significant words
                    npc_words = [
                        w for w in npc_name.split() if w not in ignore_words
                    ]
                    for word in npc_words:
                        if len(word) > 2 and word in player_input_lower:
                            self.last_referenced_npc = npc_id
                            break

        # Check for items mentioned in player input (both at location and in inventory)
        items_at_location = context.get("items", [])
        inventory_items = context.get("player", {}).get("inventory", [])
        all_items = items_at_location + inventory_items

        for item in all_items:
            item_name = item.get("name", "").lower()
            item_id = item.get("id")
            if item_name and item_id:
                # Try exact match first
                if item_name in player_input_lower:
                    self.last_referenced_item = item_id
                else:
                    # Try matching individual significant words
                    item_words = [
                        w for w in item_name.split() if w not in ignore_words
                    ]
                    for word in item_words:
                        if len(word) > 2 and word in player_input_lower:
                            self.last_referenced_item = item_id
                            break

        # Then, also check state updates for references (existing logic)
        state_updates = interpretation.get("state_updates", [])

        for update in state_updates:
            update_type = update.get("type")
            target = update.get("target")
            params = update.get("params", {})

            # Track items
            if update_type in ["add_to_inventory", "remove_from_inventory"]:
                item_id = params.get("item_id")
                if item_id:
                    self.last_referenced_item = item_id
            elif update_type == "move_item":
                item_id = params.get("item_id")
                if item_id:
                    self.last_referenced_item = item_id
            elif target and target in self.game_state.items:
                self.last_referenced_item = target

            # Track NPCs
            if target and target in self.game_state.npcs:
                self.last_referenced_npc = target
            elif update_type == "trigger_combat":
                npc_id = params.get("target_npc_id")
                if npc_id:
                    self.last_referenced_npc = npc_id
            elif update_type in ["remove_npc", "move_npc"]:
                npc_id = params.get("npc_id")
                if npc_id:
                    self.last_referenced_npc = npc_id

    def _extract_action_metadata(self, state_updates: list, context: Dict) -> Dict[str, Any]:
        """Extract metadata about where items/NPCs were before state updates.

        This helps narrative generation understand what changed.
        """
        metadata = {}

        for update in state_updates:
            update_type = update.get("type")
            params = update.get("params", {})

            if update_type == "add_to_inventory":
                item_id = params.get("item_id")
                # Check if item is currently at player location (on ground)
                if item_id in self.game_state.item_locations:
                    loc = self.game_state.item_locations[item_id]
                    if loc == self.game_state.player_location:
                        metadata["item_picked_from_ground"] = item_id
                        metadata["item_was_at_location"] = True
                    else:
                        metadata["item_was_at_location"] = False

            elif update_type == "remove_from_inventory":
                item_id = params.get("item_id")
                if item_id in self.game_state.player.inventory:
                    metadata["item_dropped_from_inventory"] = item_id
                    metadata["item_was_in_inventory"] = True

        return metadata

    def _build_context(self, only_include: Optional[Set[str]] = None) -> dict:
        """Build context for LLM with detailed state information."""
        location = self.game_state.get_player_location()
        items_at_location = self.game_state.get_items_at_location(
            self.game_state.player_location
        )
        npcs_at_location = self.game_state.get_npcs_at_location(
            self.game_state.player_location
        )
        lighting = self.game_state.get_effective_lighting(
            self.game_state.player_location
        )

        # Add global objects from location's zil_global_objects to items list
        if location and 'zil_global_objects' in location.attributes:
            global_obj_ids = location.attributes['zil_global_objects']
            for obj_id in global_obj_ids:
                if obj_id in self.game_state.items and obj_id not in [item.id for item in items_at_location]:
                    items_at_location.append(self.game_state.items[obj_id])

        # Add pseudo objects (scenery) from location's zil_pseudo_routines as virtual items
        if location and 'zil_pseudo_routines' in location.attributes:
            from src.models.game_state import Item
            pseudo_routines = location.attributes['zil_pseudo_routines']
            for pseudo_name, routine_info in pseudo_routines.items():
                # Create a virtual item for this pseudo object
                pseudo_id = f"pseudo_{pseudo_name.lower()}"
                # Check if we haven't already added it
                if pseudo_id not in [item.id for item in items_at_location]:
                    pseudo_item = Item(
                        id=pseudo_id,
                        name=pseudo_name.lower(),
                        attributes={
                            "type": "scenery",
                            "takeable": False,
                            "is_visible": True,
                            "auto_describe": False,
                            "is_pseudo_object": True,
                            "zil_pseudo_routine": routine_info.get("routine_name"),
                            "zil_action_code": routine_info.get("zil_string"),
                            "zil_action_json": routine_info.get("zil_json"),
                            "description_hints": f"{pseudo_name.lower()} (scenery)"
                        }
                    )
                    items_at_location.append(pseudo_item)

        # Get detailed item info for items in inventory
        inventory_items = []
        for item_id in self.game_state.player.inventory:
            if item_id in self.game_state.items:
                item = self.game_state.items[item_id]
                inventory_items.append(
                    {"id": item.id, "name": item.name, "attributes": item.attributes}
                )

        # Build map of ALL location IDs and their exits
        all_locations = {
            loc_id: {
                "id": loc.id,
                "name": loc.name,
                "exits": loc.connections,
            }
            for loc_id, loc in self.game_state.locations.items()
        }

        # Get exit destinations from current location
        exit_destinations = {}
        if location:
            for direction, dest_id in location.connections.items():
                if dest_id:
                    exit_destinations[direction] = dest_id

        # Build map of ALL NPCs with their locations (for plot management)
        all_npcs = {}
        for npc_id, npc in self.game_state.npcs.items():
            npc_location = self.game_state.npc_locations.get(npc_id, "unknown")
            all_npcs[npc_id] = {
                "id": npc.id,
                "name": npc.name,
                "attributes": npc.attributes,
                "location": npc_location,
            }

        # Build recent conversation history for pronoun resolution
        recent_turns = []
        for entry in self.game_state.get_recent_history(count=3):
            interpretation = entry.get("interpretation", {})
            recent_turns.append({
                "player_input": entry.get("input", ""),
                "narrative": interpretation.get("narrative_response", ""),
            })

        # Build container contents map for open containers
        # Check items at location and in inventory for open containers
        # IMPORTANT: Check recursively - containers can be inside other containers!
        container_contents = {}

        def check_container_recursive(item, checked_ids=None):
            """Recursively check if item is an open container and collect its contents."""
            if checked_ids is None:
                checked_ids = set()

            # Avoid infinite loops
            if item.id in checked_ids:
                return
            checked_ids.add(item.id)

            # Check both 'is_container' and 'container' attributes
            is_container = item.attributes.get("is_container", False) or item.attributes.get("container", False)
            # Check multiple variations of 'open' attribute (LLM may use different names)
            is_open = (
                item.attributes.get("is_open", False) or
                item.attributes.get("open", False) or
                item.attributes.get("opened", False) or
                (isinstance(item.attributes.get("state"), dict) and item.attributes["state"].get("opened", False))
            )

            if is_container and is_open:
                contents = self.game_state.get_items_in_container(item.id)
                logger.debug(f"Container {item.id} is open, contains {len(contents)} items: {[c.name for c in contents]}")
                if contents:
                    container_contents[item.id] = [
                        {"id": c.id, "name": c.name, "attributes": c.attributes}
                        for c in contents
                    ]
                    # Recursively check items inside this container
                    for content_item in contents:
                        check_container_recursive(content_item, checked_ids)

        # Check items at current location (and recursively their contents)
        for item in items_at_location:
            check_container_recursive(item)

        # Also check inventory for open containers (and recursively their contents)
        for item_id in self.game_state.player.inventory:
            if item_id in self.game_state.items:
                item = self.game_state.items[item_id]
                check_container_recursive(item)

        # Build detailed context
        context = {
            "location": location.model_dump() if location else None,
            "lighting": lighting, 
            "exits": location.get_available_exits() if location else [],
            "exit_destinations": exit_destinations,  # direction -> location_id map
            "items": [
                {"id": item.id, "name": item.name, "attributes": item.attributes}
                for item in items_at_location
            ],
            "container_contents": container_contents,  # Items inside open containers
            "npcs": [
                {"id": npc.id, "name": npc.name, "attributes": npc.attributes}
                for npc in npcs_at_location
            ],
            "player": {
                "name": self.game_state.player.name,
                "inventory": inventory_items,
                "inventory_ids": self.game_state.player.inventory,
                "attributes": self.game_state.player.attributes,
            },
            "game_time": self.game_state.game_time,  # Current in-game date/time
            "all_locations": all_locations,  # Complete map of location IDs
            "all_npcs": all_npcs,  # All NPCs with locations (for plot management)
            "conversation_history": recent_turns,  # For natural pronoun resolution
            "global_flags": self.game_state.flags,  # For ZIL condition evaluation
        }

        # Add plot information if present
        if self.game_state.plot_config:
            context["plot"] = {
                "config": self.game_state.plot_config,
                "dm_state": self.game_state.dm_state,
            }

        # Add world context if present
        if self.game_state.world_context:
            context["world_context"] = self.game_state.world_context

        if only_include is not None:
            for omit_key in only_include:
                del context[omit_key]

        return context

    def _handle_level_transition(self) -> None:
        """Handle transition to next dungeon level in rogue mode.

        Generates the next level, applies it to game state, and moves player to entry.
        """
        from ..models.location import Location
        from ..models.npc import NPC
        from ..models.item import Item

        current_level = self.game_state.rogue_config["current_level"]
        next_level = current_level + 1

        print("\n" + "=" * 60)
        print(f"🎊 LEVEL {current_level} COMPLETE!")
        print("=" * 60)
        print("\nDescending deeper into the dungeon...")
        print(f"Generating Level {next_level}...")

        # Generate next level
        genre = self.game_state.rogue_config.get("genre", "dark fantasy")
        plot = self.game_state.rogue_config.get("plot")
        specifics = self.game_state.rogue_config.get("specifics")
        num_middle_locations = self.game_state.rogue_config.get("num_middle_locations", 3)
        num_npcs = self.game_state.rogue_config.get("num_npcs", 2)
        num_items = self.game_state.rogue_config.get("num_items", 3)

        # Increase difficulty with each level
        difficulty_modifier = 1.0 + (next_level - 1) * 0.2

        level_data = self.gemini.generate_dungeon_level(
            level_number=next_level,
            genre=genre,
            plot=plot,
            specifics=specifics,
            difficulty_modifier=difficulty_modifier,
            num_middle_locations=num_middle_locations,
            num_npcs=num_npcs,
            num_items=num_items,
        )

        # Apply generated level to game state
        # Add locations
        for loc_data in level_data["locations"]:
            location = Location(
                id=loc_data["id"],
                name=loc_data["name"],
                attributes=loc_data.get("attributes", {}),
                connections=loc_data.get("connections", {}),
            )
            self.game_state.locations[location.id] = location

        # Add NPCs
        for npc_data in level_data.get("npcs", []):
            npc = NPC(
                id=npc_data["id"],
                name=npc_data["name"],
                attributes=npc_data.get("attributes", {}),
            )
            self.game_state.npcs[npc.id] = npc

        # Add items
        for item_data in level_data.get("items", []):
            item = Item(
                id=item_data["id"],
                name=item_data["name"],
                attributes=item_data.get("attributes", {}),
            )
            self.game_state.items[item.id] = item

        # Set locations
        self.game_state.npc_locations.update(level_data.get("npc_locations", {}))
        self.game_state.item_locations.update(level_data.get("item_locations", {}))

        # Track metadata in rogue_config
        if "level_metadata" not in self.game_state.rogue_config:
            self.game_state.rogue_config["level_metadata"] = {}

        self.game_state.rogue_config["level_metadata"][str(next_level)] = {
            "entry_location_id": level_data["entry_location_id"],
            "exit_location_id": level_data["exit_location_id"],
            "generated_locations": [loc["id"] for loc in level_data["locations"]],
            "generated_npcs": [npc["id"] for npc in level_data.get("npcs", [])],
            "generated_items": [item["id"] for item in level_data.get("items", [])],
            "theme": level_data.get("theme", "unknown"),
            "difficulty": next_level,
        }

        # Update current level
        self.game_state.rogue_config["current_level"] = next_level

        # Move player to entry location
        self.game_state.player_location = level_data["entry_location_id"]

        # Show level generation summary
        print(f"\n✓ Level {next_level} generated!")
        print(f"  Theme: {level_data['theme']}")
        print(f"  Locations: {len(level_data['locations'])}")
        print(f"  NPCs: {len(level_data.get('npcs', []))}")
        print(f"  Items: {len(level_data.get('items', []))}")
        print(f"  Difficulty: {difficulty_modifier:.1f}x")
        print("=" * 60)
        print("\nYou find yourself in a new area...")

        # Show the new location
        print()
        self._show_location()
