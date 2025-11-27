"""Test that invalid movement (to non-existent exits) is properly rejected."""

import pytest
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def game_at_chamber():
    """Setup game at chamber which only has south exit."""
    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)
    game_state.player_location = "chamber"
    game_state.player.inventory = []

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state


def test_invalid_movement_north_from_chamber(game_at_chamber):
    """Test that trying to go north from chamber (only has south) is rejected."""
    game_loop, game_state = game_at_chamber

    # Verify chamber only has south exit
    chamber = game_state.locations["chamber"]
    assert list(chamber.connections.keys()) == ["south"], \
        f"Chamber should only have south exit, but has: {list(chamber.connections.keys())}"

    # Try to go north (invalid)
    narrative, interpretation = game_loop.process_turn("go north")

    # Assert: is_valid should be false
    assert interpretation.get("is_valid") is False, \
        f"Going north from chamber should be invalid. Interpretation: {interpretation}"

    # Assert: should use no_change state update
    state_updates = interpretation.get("state_updates", [])
    assert len(state_updates) == 1, f"Should have exactly 1 state update: {state_updates}"
    assert state_updates[0].get("type") == "no_change", \
        f"Should use no_change for invalid movement: {state_updates}"

    # Assert: player should still be at chamber
    assert game_state.player_location == "chamber", \
        f"Player should still be at chamber after invalid movement, but is at: {game_state.player_location}"

    # Assert: narrative should explain why blocked
    narrative_lower = narrative.lower()
    assert any(word in narrative_lower for word in ["no", "can't", "cannot", "blocked", "wall", "path"]), \
        f"Narrative should explain why movement is blocked: {narrative}"


def test_valid_movement_south_from_chamber(game_at_chamber):
    """Test that valid movement (south from chamber) works correctly."""
    game_loop, game_state = game_at_chamber

    # Go south (valid)
    narrative, interpretation = game_loop.process_turn("go south")

    # Assert: is_valid should be true
    assert interpretation.get("is_valid") is not False, \
        f"Going south from chamber should be valid. Interpretation: {interpretation}"

    # Assert: should use move_player state update
    state_updates = interpretation.get("state_updates", [])
    has_move = any(u.get("type") == "move_player" for u in state_updates)
    assert has_move, f"Should have move_player state update: {state_updates}"

    # Assert: player should now be at hall
    assert game_state.player_location == "hall", \
        f"Player should be at hall after moving south, but is at: {game_state.player_location}"


def test_invalid_movement_multiple_directions(game_at_chamber):
    """Test that multiple invalid directions are all rejected."""
    game_loop, game_state = game_at_chamber

    invalid_directions = ["north", "east", "west"]

    for direction in invalid_directions:
        # Reset to chamber
        game_state.player_location = "chamber"

        narrative, interpretation = game_loop.process_turn(f"go {direction}")

        # Assert: should be invalid
        assert interpretation.get("is_valid") is False, \
            f"Going {direction} from chamber should be invalid. Interpretation: {interpretation}"

        # Assert: player still at chamber
        assert game_state.player_location == "chamber", \
            f"Player should still be at chamber after trying to go {direction}"
