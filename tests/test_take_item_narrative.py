"""Test that item pickup/drop narratives are correct."""

import pytest
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop

@pytest.fixture
def game_with_item_on_ground():
    """Setup game with item on ground, not in inventory."""
    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Ensure key is at entrance, not in inventory
    game_state.item_locations["ancient_key"] = "entrance"
    game_state.player_location = "entrance"
    game_state.player.inventory = []

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state

def test_take_from_ground_narrative(game_with_item_on_ground):
    """When taking item from ground, narrative should not say 'from pack'."""
    game_loop, game_state = game_with_item_on_ground

    narrative, interpretation = game_loop.process_turn("take the ancient key")

    # Assert: key is now in inventory
    assert "ancient_key" in game_state.player.inventory
    assert "ancient_key" not in game_state.item_locations

    # Assert: narrative mentions picking up, not from pack
    narrative_lower = narrative.lower()
    assert any(word in narrative_lower for word in ["pick", "grab", "take", "get"]), \
        f"Narrative should mention picking up: {narrative}"

    assert "pack" not in narrative_lower, \
        f"Narrative incorrectly says 'from pack': {narrative}"
    assert "belt" not in narrative_lower, \
        f"Narrative incorrectly says 'from belt': {narrative}"

def test_drop_from_inventory_narrative(game_with_item_on_ground):
    """When dropping item from inventory, narrative should reflect that."""
    game_loop, game_state = game_with_item_on_ground

    # Setup: put key in inventory first
    game_state.player.add_item("ancient_key")
    game_state.item_locations.pop("ancient_key", None)

    narrative, interpretation = game_loop.process_turn("drop the ancient key")

    # Assert: key is on ground, not in inventory
    assert "ancient_key" not in game_state.player.inventory
    assert game_state.item_locations.get("ancient_key") == "entrance"

    # Assert: narrative mentions dropping
    narrative_lower = narrative.lower()
    assert any(word in narrative_lower for word in ["drop", "place", "set", "put"]), \
        f"Narrative should mention dropping: {narrative}"
