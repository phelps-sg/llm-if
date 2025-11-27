"""Action processor for handling player actions."""

from typing import Dict, Any, Optional, Tuple, List, Union
from ..models.game_state import GameState
from ..models.npc import NPC
from ..models.item import Item
from ..models.player import Player
from ..rules.rule_engine import RuleEngine, RuleTrigger


class ActionProcessor:
    """Processes player actions and updates game state."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def _resolve_location_id(
        self, location_name_or_id: str, game_state: GameState
    ) -> Optional[str]:
        """Convert location name to ID, or return ID if already an ID.

        Args:
            location_name_or_id: Either a location ID or location name
            game_state: Game state with locations

        Returns:
            Location ID if found, None otherwise
        """
        # Check if it's already a valid ID
        if location_name_or_id in game_state.locations:
            return location_name_or_id

        # Try to find by name
        for loc_id, location in game_state.locations.items():
            if location.name == location_name_or_id:
                return loc_id

        # Not found
        return None

    def apply_state_updates(
        self, updates: List[Dict[str, Any]], game_state: GameState
    ) -> None:
        """Apply LLM-generated state updates to the game state.

        Args:
            updates: List of state update dictionaries
            game_state: Current game state to modify
        """
        for update in updates:
            update_type = update.get("type")
            target = update.get("target")
            params = update.get("params", {})

            if update_type == "move_player":
                destination = params.get("destination")
                if destination:
                    # Resolve location name to ID
                    location_id = self._resolve_location_id(destination, game_state)
                    if location_id:
                        game_state.move_player_to_location(location_id)

                        # Move all pet NPCs with the player
                        for npc_id, npc in game_state.npcs.items():
                            if npc.attributes.get("is_pet", False):
                                # Pet follows player to new location
                                if npc_id in game_state.npc_locations:
                                    game_state.npc_locations[npc_id] = location_id

            elif update_type == "add_to_inventory":
                item_id = params.get("item_id")
                if item_id and item_id in game_state.items:
                    game_state.move_item_to_player(item_id)

            elif update_type == "remove_from_inventory":
                item_id = params.get("item_id")
                if item_id:
                    # Remove from inventory and place at current location
                    game_state.player.remove_item(item_id)
                    # Put the item at the player's current location
                    game_state.item_locations[item_id] = game_state.player_location

            elif update_type == "move_item":
                item_id = params.get("item_id")
                to_location = params.get("to_location")
                if item_id and to_location:
                    # Resolve location name to ID
                    location_id = self._resolve_location_id(to_location, game_state)
                    if location_id:
                        game_state.move_item_to_location(item_id, location_id)

            elif update_type == "modify_attribute":
                entity_id = params.get("entity_id") or target
                attribute_path = params.get("attribute_path", "")
                value = params.get("value")

                if entity_id and attribute_path:
                    # Parse attribute path and set value
                    self._set_nested_attribute(
                        game_state, entity_id, attribute_path, value
                    )

            elif update_type == "set_flag":
                flag_name = params.get("flag_name")
                flag_value = params.get("value", True)
                if flag_name:
                    game_state.flags[flag_name] = flag_value

            elif update_type == "trigger_combat":
                # Execute full combat round (player attacks, then NPC counterattacks)
                target_npc_id = params.get("target_npc_id") or target
                if target_npc_id and target_npc_id in game_state.npcs:
                    combat_result = self._execute_combat_round(
                        game_state, target_npc_id, params.get("attack_type", "melee")
                    )
                    # Store combat result for narrative
                    game_state.flags[f"last_combat_result"] = combat_result

            elif update_type == "consume_item":
                # Consume an item (eat, drink, destroy) - removes from game entirely
                item_id = params.get("item_id") or target
                if item_id:
                    # Remove from player inventory if present
                    game_state.player.remove_item(item_id)

                    # Remove from item_locations (destroys the item)
                    if item_id in game_state.item_locations:
                        del game_state.item_locations[item_id]

                    # TODO: Apply item effects (healing, etc.) based on item attributes
                    # For now, just removing the item

            elif update_type == "remove_npc":
                # Remove an NPC from the current location (for creative player actions)
                npc_id = params.get("npc_id") or target
                if npc_id and npc_id in game_state.npc_locations:
                    del game_state.npc_locations[npc_id]
                    # NPC still exists in game_state.npcs for history/lore

            elif update_type == "move_npc":
                # Move an NPC to a different location
                npc_id = params.get("npc_id") or target
                to_location = params.get("to_location")
                if npc_id and to_location:
                    location_id = self._resolve_location_id(to_location, game_state)
                    if location_id:
                        game_state.move_npc_to_location(npc_id, location_id)

            elif update_type == "create_item":
                # Dynamically create a new item in the game world
                item_id = params.get("item_id")
                name = params.get("name")
                attributes = params.get("attributes", {})
                location = params.get("location")  # None means add to player inventory

                if item_id and name:
                    # Validate item doesn't already exist
                    if item_id in game_state.items:
                        print(f"[WARNING] Item '{item_id}' already exists, skipping create_item")
                        continue

                    # Create new Item object
                    new_item = Item(
                        id=item_id,
                        name=name,
                        attributes=attributes
                    )

                    # Add to game state
                    game_state.items[item_id] = new_item

                    # Set location or add to inventory
                    if location is None:
                        # Add to player inventory
                        game_state.player.add_item(item_id)
                    else:
                        # Resolve location name to ID and place item there
                        location_id = self._resolve_location_id(location, game_state)
                        if location_id:
                            game_state.item_locations[item_id] = location_id
                        else:
                            # Default to player's current location if invalid
                            game_state.item_locations[item_id] = game_state.player_location

            elif update_type == "destroy_item":
                # Permanently remove an item from the game world
                item_id = params.get("item_id") or target
                if item_id:
                    # Remove from player inventory if present
                    if item_id in game_state.player.inventory:
                        game_state.player.remove_item(item_id)

                    # Remove from item_locations
                    if item_id in game_state.item_locations:
                        del game_state.item_locations[item_id]

                    # Remove from items dict (permanent deletion)
                    if item_id in game_state.items:
                        del game_state.items[item_id]

            elif update_type == "create_location":
                # Dynamically create a new location in the game world
                from ..models.location import Location

                location_id = params.get("location_id")
                name = params.get("name")
                attributes = params.get("attributes", {})
                connections = params.get("connections", {})

                # Optional: auto-connect to a location (e.g., "create path south from current location")
                from_location = params.get("from_location")  # Location ID to connect from
                direction = params.get("direction")  # Direction from that location
                reverse_direction = params.get("reverse_direction")  # Optional reverse direction

                if location_id and name:
                    # Validate location doesn't already exist
                    if location_id in game_state.locations:
                        print(f"[WARNING] Location '{location_id}' already exists, skipping create_location")
                        continue

                    # Create new Location object
                    new_location = Location(
                        id=location_id,
                        name=name,
                        attributes=attributes,
                        connections=connections
                    )

                    # Add to game state
                    game_state.locations[location_id] = new_location

                    # Auto-connect to existing location if specified
                    if from_location and direction:
                        from_loc_id = self._resolve_location_id(from_location, game_state)
                        if from_loc_id and from_loc_id in game_state.locations:
                            # Add connection from existing location to new location
                            game_state.locations[from_loc_id].connections[direction] = location_id

                            # Add reverse connection if specified
                            if reverse_direction:
                                new_location.connections[reverse_direction] = from_loc_id

            elif update_type == "create_npc":
                # Dynamically create a new NPC in the game world
                from ..models.npc import NPC

                npc_id = params.get("npc_id")
                name = params.get("name")
                attributes = params.get("attributes", {})
                location = params.get("location")  # Location ID where NPC appears

                if npc_id and name:
                    # Validate NPC doesn't already exist
                    if npc_id in game_state.npcs:
                        print(f"[WARNING] NPC '{npc_id}' already exists, skipping create_npc")
                        continue

                    # Create new NPC object
                    new_npc = NPC(
                        id=npc_id,
                        name=name,
                        attributes=attributes
                    )

                    # Add to game state
                    game_state.npcs[npc_id] = new_npc

                    # Set location (default to player's current location if not specified)
                    if location:
                        location_id = self._resolve_location_id(location, game_state)
                        if location_id:
                            game_state.npc_locations[npc_id] = location_id
                        else:
                            # Default to player's current location if invalid
                            game_state.npc_locations[npc_id] = game_state.player_location
                    else:
                        # No location specified - default to player's current location
                        game_state.npc_locations[npc_id] = game_state.player_location

            elif update_type == "update_dm_state":
                # Update hidden DM state for plot tracking
                path = params.get("path")
                value = params.get("value")
                if path:
                    self._set_nested_dm_state(game_state, path, value)

            elif update_type == "no_change":
                # Narrative-only action, no state change
                pass

    def _execute_combat_round(
        self, game_state: GameState, target_npc_id: str, attack_type: str = "melee"
    ) -> Dict[str, Any]:
        """Execute a full combat round (player attack + NPC counterattack).

        Args:
            game_state: Current game state
            target_npc_id: ID of NPC to attack
            attack_type: Type of attack (melee/ranged)

        Returns:
            Combat result with both player and NPC attack results
        """
        npc = game_state.npcs.get(target_npc_id)
        if not npc:
            return {"success": False, "error": "Target not found"}

        # Execute player's attack
        player_attack = self._execute_single_attack(
            game_state, game_state.player, npc, attack_type
        )

        # If NPC is still alive, it counterattacks
        npc_attack = None
        if player_attack.get("success") and not player_attack.get("target_dead"):
            npc_attack = self._execute_npc_attack(game_state, npc, game_state.player)
        else:
            # NPC is dead - remove it from the location
            if target_npc_id in game_state.npc_locations:
                del game_state.npc_locations[target_npc_id]

        return {
            "success": True,
            "player_attack": player_attack,
            "npc_attack": npc_attack,
            "round_complete": True,
        }

    def _execute_single_attack(
        self,
        game_state: GameState,
        attacker: Union[Player, NPC],
        target: Union[Player, NPC],
        attack_type: str = "melee",
    ) -> Dict[str, Any]:
        """Execute a single attack from attacker to target.

        Args:
            game_state: Current game state
            attacker: The attacking entity (player or NPC)
            target: The target entity (player or NPC)
            attack_type: Type of attack (melee/ranged)

        Returns:
            Combat result with dice rolls, damage, and outcome
        """
        # Get attacker's weapon
        weapon = None
        if isinstance(attacker, Player):
            for item_id in attacker.inventory:
                item = game_state.items.get(item_id)
                if item and item.attributes.get("type") == "weapon":
                    weapon = item
                    break

        # Prepare event data for rule engine
        event_data = {
            "action_type": "attack",
            "attack_range": attack_type,
            "actor": attacker.model_dump(),
            "target": target.model_dump(),
            "weapon": weapon.model_dump()
            if weapon
            else {"damage": "1d4", "damage_type": "bludgeoning"},  # Unarmed
        }

        # Process through rule engine
        results = self.rule_engine.process_event(
            RuleTrigger.ACTION, game_state, event_data
        )

        # Extract combat results
        if results and results[0].get("success"):
            result = results[0]
            damage = result.get("damage_amount", 0)
            new_hp = target.take_damage(damage)

            # Get d20 check details
            d20_check = result.get("d20_check", {})
            damage_result = result.get("damage", {})

            return {
                "success": True,
                "hit": True,
                "attacker_name": attacker.name,
                "attack_roll": d20_check.get("roll", 0),
                "attack_modifier": d20_check.get("modifier", 0),
                "attack_total": d20_check.get("total", 0),
                "target_ac": target.attributes.get("armor_class", 10),
                "target_name": target.name,
                "damage_rolls": damage_result.get("rolls", []),
                "damage_modifier": damage_result.get("modifier", 0),
                "damage_total": damage,
                "damage_notation": f"{damage_result.get('num_dice', 1)}d{damage_result.get('sides', 6)}",
                "target_hp": new_hp,
                "target_max_hp": target.attributes.get("hp_max", 0),
                "target_dead": new_hp <= 0,
                "weapon_name": weapon.name if weapon else "fists",
            }
        else:
            result = results[0] if results else {}
            d20_check = result.get("d20_check", {})

            return {
                "success": True,
                "hit": False,
                "attacker_name": attacker.name,
                "attack_roll": d20_check.get("roll", 0),
                "attack_modifier": d20_check.get("modifier", 0),
                "attack_total": d20_check.get("total", 0),
                "target_ac": target.attributes.get("armor_class", 10),
                "target_name": target.name,
                "weapon_name": weapon.name if weapon else "fists",
            }

    def _execute_npc_attack(
        self, game_state: GameState, npc: NPC, player: Player
    ) -> Dict[str, Any]:
        """Execute NPC's counterattack on the player.

        Args:
            game_state: Current game state
            npc: The NPC counterattacking
            player: The player being attacked

        Returns:
            Combat result for NPC's attack
        """
        return self._execute_single_attack(game_state, npc, player, "melee")

    def _set_nested_attribute(
        self, game_state: GameState, entity_id: str, path: str, value: Any
    ) -> None:
        """Set a nested attribute on an entity.

        Args:
            game_state: Game state containing entities
            entity_id: ID of entity to modify (NPC, item, player)
            path: Dot-separated path like "state.has_been_greeted"
            value: Value to set
        """
        # Find the entity
        entity: Union[NPC, Item, Player, None] = None
        if entity_id in game_state.npcs:
            entity = game_state.npcs[entity_id]
        elif entity_id in game_state.items:
            entity = game_state.items[entity_id]
        elif entity_id == "player":
            entity = game_state.player

        if not entity:
            return

        # Navigate to the nested location
        parts = path.split(".")
        current: Dict[str, Any] = entity.attributes

        # Navigate to parent of final key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        if len(parts) > 0:
            current[parts[-1]] = value

    def _set_nested_dm_state(
        self, game_state: GameState, path: str, value: Any
    ) -> None:
        """Set a nested value in dm_state.

        Args:
            game_state: Game state containing dm_state
            path: Dot-separated path like "npc_states.wolf.status"
            value: Value to set
        """
        parts = path.split(".")
        current: Dict[str, Any] = game_state.dm_state

        # Navigate to parent of final key, creating dicts as needed
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        if len(parts) > 0:
            current[parts[-1]] = value

    def process_action(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process a player action.

        Args:
            action: Structured action from parser
            game_state: Current game state

        Returns:
            (success, result_data) tuple
        """
        action_type = action.get("action_type")

        if action_type == "move":
            return self._handle_move(action, game_state)
        elif action_type == "look":
            return self._handle_look(action, game_state)
        elif action_type == "take":
            return self._handle_take(action, game_state)
        elif action_type == "attack":
            return self._handle_attack(action, game_state)
        elif action_type == "inventory":
            return self._handle_inventory(action, game_state)
        else:
            return False, {"error": f"Unknown action type: {action_type}"}

    def _handle_move(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle movement action."""
        direction = action.get("target", "").lower()
        current_location = game_state.get_player_location()

        if not current_location:
            return False, {"error": "No current location"}

        destination_id = current_location.get_exit(direction)

        if destination_id is None:
            return False, {
                "error": f"Cannot go {direction}",
                "available_exits": current_location.get_available_exits(),
            }

        # Move player
        game_state.move_player_to_location(destination_id)

        new_location = game_state.get_player_location()
        return True, {
            "moved_to": destination_id,
            "new_location": new_location.model_dump() if new_location else None,
        }

    def _handle_look(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle look action."""
        target = action.get("target")

        if not target:
            # Look at current location
            location = game_state.get_player_location()
            items = game_state.get_items_at_location(game_state.player_location)
            npcs = game_state.get_npcs_at_location(game_state.player_location)

            return True, {
                "type": "location",
                "location": location.model_dump() if location else None,
                "items": [item.model_dump() for item in items],
                "npcs": [npc.model_dump() for npc in npcs],
            }

        # Look at specific target
        # For MVP, just return success
        return True, {"type": "target", "target": target}

    def _handle_take(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle take/pick up item action."""
        target = action.get("target", "").lower()

        # Find item at current location
        items = game_state.get_items_at_location(game_state.player_location)
        item = None

        for i in items:
            if target in i.name.lower() or target == i.id:
                item = i
                break

        if not item:
            return False, {
                "error": f"No item '{target}' here",
                "available_items": [i.name for i in items],
            }

        # Move item to player inventory
        game_state.move_item_to_player(item.id)

        return True, {"item_taken": item.model_dump()}

    def _handle_attack(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle attack action."""
        target = action.get("target", "").lower()

        # Find NPC at current location
        npcs = game_state.get_npcs_at_location(game_state.player_location)
        npc = None

        for n in npcs:
            if target in n.name.lower() or target == n.id:
                npc = n
                break

        if not npc:
            return False, {
                "error": f"No target '{target}' here",
                "available_targets": [n.name for n in npcs],
            }

        # Get player weapon
        weapon = None
        for item_id in game_state.player.inventory:
            item = game_state.items.get(item_id)
            if item and item.attributes.get("type") == "weapon":
                weapon = item
                break

        # Prepare event data for rule engine
        event_data = {
            "action_type": "attack",
            "attack_range": "melee",  # For MVP
            "actor": game_state.player.model_dump(),
            "target": npc.model_dump(),
            "weapon": weapon.model_dump()
            if weapon
            else {"damage": "1", "damage_type": "bludgeoning"},
        }

        # Process through rule engine
        results = self.rule_engine.process_event(
            RuleTrigger.ACTION, game_state, event_data
        )

        # Apply damage if hit
        if results and results[0].get("success"):
            damage = results[0].get("damage_amount", 0)
            npc.take_damage(damage)

        return True, {"combat_results": results, "target": npc.model_dump()}

    def _handle_inventory(
        self, action: Dict[str, Any], game_state: GameState
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle inventory display."""
        items = [
            game_state.items[item_id].model_dump()
            for item_id in game_state.player.inventory
            if item_id in game_state.items
        ]

        return True, {"inventory": items}
