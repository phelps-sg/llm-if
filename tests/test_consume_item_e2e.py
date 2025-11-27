"""E2E tests for consuming/destroying items."""

import pytest
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def game_with_consumables():
    """Setup game with consumable items."""
    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Ensure berries are at forest_clearing and key is at entrance
    game_state.item_locations["wild_berries"] = "forest_clearing"
    game_state.item_locations["ancient_key"] = "entrance"
    game_state.player_location = "forest_clearing"
    game_state.player.inventory = []

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state


def test_eat_berries_removes_from_game(game_with_consumables):
    """Test that eating berries permanently removes them from the game."""
    game_loop, game_state = game_with_consumables

    # Pick up berries
    game_loop.process_turn("take the wild berries")
    assert "wild_berries" in game_state.player.inventory
    assert "wild_berries" not in game_state.item_locations

    # Eat berries
    narrative, interpretation = game_loop.process_turn("eat the berries")

    # Assert: berries are gone from inventory
    assert "wild_berries" not in game_state.player.inventory, \
        f"Berries still in inventory after eating: {game_state.player.inventory}"

    # Assert: berries are NOT at any location (permanently removed)
    assert "wild_berries" not in game_state.item_locations, \
        f"Berries reappeared at location after eating: {game_state.item_locations}"

    # Assert: berries no longer exist in items dict (optional - depends on implementation)
    # Note: consume_item might keep the item in the items dict but remove from locations/inventory

    # Verify state updates used consume_item
    state_updates = interpretation.get("state_updates", [])
    has_consume = any(u.get("type") == "consume_item" for u in state_updates)
    assert has_consume, \
        f"Expected consume_item state update, got: {state_updates}"


def test_swallow_key_removes_from_game(game_with_consumables):
    """Test that swallowing a key permanently removes it from the game."""
    game_loop, game_state = game_with_consumables

    # Move to entrance and pick up key
    game_loop.process_turn("go north")
    assert game_state.player_location == "entrance"

    game_loop.process_turn("take the ancient key")
    assert "ancient_key" in game_state.player.inventory
    assert "ancient_key" not in game_state.item_locations

    # Swallow key
    narrative, interpretation = game_loop.process_turn("swallow the key")

    # Assert: key is gone from inventory
    assert "ancient_key" not in game_state.player.inventory, \
        f"Key still in inventory after swallowing: {game_state.player.inventory}"

    # Assert: key is NOT at any location (permanently removed)
    assert "ancient_key" not in game_state.item_locations, \
        f"Key reappeared at location after swallowing: {game_state.item_locations}"

    # Verify state updates used consume_item (not remove_from_inventory)
    state_updates = interpretation.get("state_updates", [])
    has_consume = any(u.get("type") == "consume_item" for u in state_updates)
    has_remove = any(u.get("type") == "remove_from_inventory" for u in state_updates)

    assert has_consume, \
        f"Expected consume_item for swallowing, got: {state_updates}"
    assert not has_remove, \
        f"Should NOT use remove_from_inventory for swallowing, got: {state_updates}"


def test_drop_vs_consume_difference(game_with_consumables):
    """Test that dropping and consuming are different actions."""
    game_loop, game_state = game_with_consumables

    # Pick up berries
    game_loop.process_turn("take the wild berries")
    assert "wild_berries" in game_state.player.inventory

    # Drop berries (should place on ground)
    narrative, interpretation = game_loop.process_turn("drop the berries")

    # Assert: berries are NOT in inventory
    assert "wild_berries" not in game_state.player.inventory

    # Assert: berries ARE at current location (not permanently removed)
    assert "wild_berries" in game_state.item_locations, \
        "Berries should be at location after dropping"
    assert game_state.item_locations["wild_berries"] == game_state.player_location, \
        f"Berries should be at player location {game_state.player_location}, " \
        f"but are at {game_state.item_locations.get('wild_berries')}"

    # Verify state updates used remove_from_inventory (not consume_item)
    state_updates = interpretation.get("state_updates", [])
    has_remove = any(u.get("type") == "remove_from_inventory" for u in state_updates)
    has_consume = any(u.get("type") == "consume_item" for u in state_updates)

    assert has_remove, \
        f"Expected remove_from_inventory for dropping, got: {state_updates}"
    assert not has_consume, \
        f"Should NOT use consume_item for dropping, got: {state_updates}"

    # Pick up again and eat (should permanently remove)
    game_loop.process_turn("take the berries")
    game_loop.process_turn("eat the berries")

    # Assert: berries are completely gone now
    assert "wild_berries" not in game_state.player.inventory
    assert "wild_berries" not in game_state.item_locations
