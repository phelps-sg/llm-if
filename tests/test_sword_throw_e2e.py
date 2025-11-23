"""End-to-end test for sword throw scenario.

This test reproduces the bug where:
1. Player picks up sword (works)
2. Player throws sword at wall (LLM says it's on the ground)
3. Player looks (sword not visible - BUG!)
4. Player checks inventory (empty - correct)

The sword should be visible at the location after throwing.
"""

import pytest
from typing import Dict, Any
from src.models.game_state import GameState
from src.models.location import Location
from src.models.item import Item
from src.models.player import Player
from src.engine.action_processor import ActionProcessor
from src.rules.rule_engine import RuleEngine


def test_sword_throw_complete_scenario():
    """Test the complete sword pickup -> throw -> look scenario."""

    # Setup minimal game state
    game_state = GameState()

    # Create dungeon entrance
    entrance = Location(
        id="dungeon_entrance",
        name="Dungeon Entrance",
        attributes={"description_hints": "moss-covered stone walls, flickering torch"},
        connections={"north": "grand_hall"},
    )
    game_state.locations["dungeon_entrance"] = entrance
    game_state.player_location = "dungeon_entrance"

    # Create rusty sword
    sword = Item(
        id="rusty_sword",
        name="Rusty Sword",
        attributes={
            "type": "weapon",
            "damage": "1d6",
            "description": "A pitted, poorly maintained blade",
        },
    )
    game_state.items["rusty_sword"] = sword
    game_state.item_locations["rusty_sword"] = "dungeon_entrance"

    # Create action processor
    rule_engine = RuleEngine()
    action_processor = ActionProcessor(rule_engine)

    print("\n=== INITIAL STATE ===")
    print(f"Player location: {game_state.player_location}")
    print(f"Player inventory: {game_state.player.inventory}")
    print(f"Sword location: {game_state.item_locations.get('rusty_sword')}")
    print(
        f"Items at entrance: {[item.name for item in game_state.get_items_at_location('dungeon_entrance')]}"
    )

    # Step 1: Pick up sword
    print("\n=== STEP 1: PICK UP SWORD ===")
    pickup_updates = [
        {
            "type": "add_to_inventory",
            "target": "rusty_sword",
            "params": {"item_id": "rusty_sword"},
        }
    ]
    action_processor.apply_state_updates(pickup_updates, game_state)

    print(f"Player inventory after pickup: {game_state.player.inventory}")
    print(
        f"Sword location after pickup: {game_state.item_locations.get('rusty_sword')}"
    )
    print(
        f"Items at entrance after pickup: {[item.name for item in game_state.get_items_at_location('dungeon_entrance')]}"
    )

    assert "rusty_sword" in game_state.player.inventory, "Sword should be in inventory"
    assert (
        len(game_state.get_items_at_location("dungeon_entrance")) == 0
    ), "No items should be at entrance"

    # Step 2: Throw sword (simulate LLM response)
    print("\n=== STEP 2: THROW SWORD ===")
    throw_updates = [
        {
            "type": "remove_from_inventory",
            "target": None,
            "params": {"item_id": "rusty_sword"},
        }
    ]

    print(f"Applying state updates: {throw_updates}")
    action_processor.apply_state_updates(throw_updates, game_state)

    print(f"Player inventory after throw: {game_state.player.inventory}")
    print(f"Sword location after throw: {game_state.item_locations.get('rusty_sword')}")
    print(
        f"Items at entrance after throw: {[item.name for item in game_state.get_items_at_location('dungeon_entrance')]}"
    )

    # Step 3: Verify sword is visible at location
    print("\n=== STEP 3: VERIFY SWORD IS VISIBLE ===")

    assert (
        "rusty_sword" not in game_state.player.inventory
    ), "Sword should not be in inventory"
    assert (
        "rusty_sword" in game_state.item_locations
    ), "Sword should still exist in item_locations"
    assert (
        game_state.item_locations["rusty_sword"] == "dungeon_entrance"
    ), "Sword should be at dungeon entrance"

    items_at_location = game_state.get_items_at_location("dungeon_entrance")
    print(
        f"Items at location (detailed): {[(item.id, item.name) for item in items_at_location]}"
    )

    assert (
        len(items_at_location) == 1
    ), f"Should have 1 item at entrance, found {len(items_at_location)}"
    assert items_at_location[0].id == "rusty_sword", "Item should be the rusty sword"

    print("\n=== TEST PASSED ===")
    print("Sword is correctly visible at the location after being thrown!")


if __name__ == "__main__":
    test_sword_throw_complete_scenario()
