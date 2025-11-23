"""Main game loop."""

from typing import Optional, Dict, Any
from ..models.game_state import GameState
from ..llm.gemini_client import GeminiClient
from ..rules.rule_engine import RuleEngine
from .action_processor import ActionProcessor


class GameLoop:
    """Main game loop orchestrator."""

    def __init__(
        self,
        game_state: GameState,
        gemini_client: GeminiClient,
        rule_engine: RuleEngine,
    ):
        self.game_state = game_state
        self.gemini = gemini_client
        self.rule_engine = rule_engine
        self.action_processor = ActionProcessor(rule_engine)
        self.running = False
        self.last_referenced_item: Optional[str] = None  # For pronoun resolution
        self.last_referenced_npc: Optional[str] = None

    def start(self) -> None:
        """Start the game loop."""
        self.running = True
        print("=" * 60)
        print("INTERACTIVE FICTION ENGINE - MVP")
        print("=" * 60)
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

        Uses two-step approach:
        1. Interpret action and get state updates
        2. Apply updates, then generate narrative from actual state

        Args:
            player_input: Player's input string

        Returns:
            Tuple of (narrative_response, interpretation)
        """
        # Step 1: Build context and interpret action
        context = self._build_context()

        # Add pronoun resolution hints to context
        if self.last_referenced_item:
            context["last_item"] = self.last_referenced_item
        if self.last_referenced_npc:
            context["last_npc"] = self.last_referenced_npc

        # Interpret action using LLM (gets state updates only)
        interpretation = self.gemini.interpret_action(player_input, context)

        # Track what was referenced for pronoun resolution
        self._update_reference_tracking(interpretation, player_input, context)

        # Step 2: Apply state updates
        state_updates = interpretation.get("state_updates", [])
        if state_updates:
            self.action_processor.apply_state_updates(state_updates, self.game_state)

        # Step 3: Generate narrative based on CURRENT state (after updates)
        updated_context = self._build_context()
        narrative = self.gemini.generate_narrative(
            player_input,
            interpretation.get("intent", ""),
            updated_context
        )

        # Store narrative in interpretation for history
        interpretation["narrative_response"] = narrative

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

        # Step 1: Interpret action using LLM
        print("[DM interprets your action...]")
        context = self._build_context()

        # Add pronoun resolution hints to context
        if self.last_referenced_item:
            context["last_item"] = self.last_referenced_item
        if self.last_referenced_npc:
            context["last_npc"] = self.last_referenced_npc

        interpretation = self.gemini.interpret_action(player_input, context)

        # DEBUG: Log what LLM returned
        print(f"\n[DEBUG] Interpretation:")
        print(f"  Intent: {interpretation.get('intent', 'N/A')}")
        print(f"  State Updates: {interpretation.get('state_updates', [])}")

        # Track what was referenced for pronoun resolution
        self._update_reference_tracking(interpretation, player_input, context)

        # Step 2: Apply state updates
        state_updates = interpretation.get("state_updates", [])
        if state_updates:
            self.action_processor.apply_state_updates(state_updates, self.game_state)
            # DEBUG: Log state after updates
            print(f"\n[DEBUG] State After Updates:")
            print(f"  Player inventory: {self.game_state.player.inventory}")
            print(
                f"  Items at location: {[item.name for item in self.game_state.get_items_at_location(self.game_state.player_location)]}"
            )
            print(f"  Item locations: {self.game_state.item_locations}")

        # Step 3: Generate narrative based on current state
        print("[DM narrates what happened...]")
        updated_context = self._build_context()
        narrative = self.gemini.generate_narrative(
            player_input,
            interpretation.get("intent", ""),
            updated_context
        )

        # Store narrative in interpretation for history
        interpretation["narrative_response"] = narrative

        # Show narrative response
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

        # Increment turn
        self.game_state.add_history_entry(
            {
                "turn": self.game_state.turn_count,
                "input": player_input,
                "interpretation": interpretation,
            }
        )

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
        }

        description = self.gemini.describe_location(
            location.model_dump(),
            [item.model_dump() for item in items],
            [npc.model_dump() for npc in npcs],
            player_context=player_context,
            lighting_info=lighting,
        )

        print(f"\n{description}")

        # Show exits
        exits = location.get_available_exits()
        if exits:
            print(f"\nExits: {', '.join(exits)}")

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
            print(f"  ✅ HIT!")

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
            print(f"  ❌ MISS!")

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

    def _build_context(self) -> dict:
        """Build context for LLM with detailed state information."""
        location = self.game_state.get_player_location()
        items_at_location = self.game_state.get_items_at_location(
            self.game_state.player_location
        )
        npcs_at_location = self.game_state.get_npcs_at_location(
            self.game_state.player_location
        )

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

        # Build detailed context
        context = {
            "location": location.model_dump() if location else None,
            "exits": location.get_available_exits() if location else [],
            "exit_destinations": exit_destinations,  # direction -> location_id map
            "items": [
                {"id": item.id, "name": item.name, "attributes": item.attributes}
                for item in items_at_location
            ],
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
            "all_locations": all_locations,  # Complete map of location IDs
            "all_npcs": all_npcs,  # All NPCs with locations (for plot management)
            "conversation_history": recent_turns,  # For natural pronoun resolution
        }

        # Add plot information if present
        if self.game_state.plot_config:
            context["plot"] = {
                "config": self.game_state.plot_config,
                "dm_state": self.game_state.dm_state,
            }

        return context
