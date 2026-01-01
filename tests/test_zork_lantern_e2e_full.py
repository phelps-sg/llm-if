"""E2E test for Zork lantern turn on command.

This test checks if the 'turn on lantern' command actually sets is_lit=True.
"""

import pytest
import os
from src.models.game_state import GameState
from src.engine.game_loop import GameLoop
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine


@pytest.fixture
def gcp_project():
    """Get GCP project from environment."""
    project = os.getenv("GCP_PROJECT")
    if not project:
        pytest.skip("GCP_PROJECT environment variable not set")
    return project


@pytest.fixture
def zork_with_lantern(gcp_project):
    """Initialize Zork at Living Room with lantern."""
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "living_room"

    # Give player the lantern
    game_state.move_item_to_player("lamp")

    # Verify initial state
    lamp = game_state.items["lamp"]
    assert lamp.attributes.get("is_lit") is False, "Lantern should start unlit"

    # Initialize game loop
    gemini = GeminiClient(project=gcp_project)
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini, rule_engine)

    return game_state, game_loop


def test_turn_on_lantern_sets_is_lit(zork_with_lantern):
    """Test that 'turn on lantern' command sets is_lit=True.

    This is the CRITICAL test that reveals the bug.
    """
    game_state, game_loop = zork_with_lantern

    # Execute turn on command
    narrative, interpretation = game_loop.process_turn("turn on lantern")

    print(f"\nNarrative: {narrative}")
    print(f"Interpretation: {interpretation}")

    # Check if state updates were generated
    state_updates = interpretation.get("state_updates", [])
    print(f"State updates: {state_updates}")

    # Check current state of lantern
    lamp = game_state.items["lamp"]
    is_lit = lamp.attributes.get("is_lit")
    is_on = lamp.attributes.get("is_on")
    print(f"Lantern is_lit after 'turn on': {is_lit}")
    print(f"Lantern is_on after 'turn on': {is_on}")

    # CRITICAL ASSERTION - Check that EITHER is_lit or is_on is True
    # (DM may use either attribute name)
    assert is_lit is True or is_on is True, \
        f"Lantern should be lit/on after 'turn on lantern' command, but is_lit={is_lit}, is_on={is_on}"

    # Verify state updates included setting a light attribute
    has_light_update = any(
        update.get("type") == "modify_attribute" and
        update.get("params", {}).get("attribute_path") in ["is_lit", "is_on"] and
        update.get("params", {}).get("value") is True
        for update in state_updates
    )
    assert has_light_update, \
        f"State updates should include setting is_lit or is_on to True, got: {state_updates}"


def test_turn_on_lantern_then_go_underground(zork_with_lantern):
    """Test full sequence: turn on lantern, then go underground.

    This reproduces the exact bug from the playthrough.
    """
    game_state, game_loop = zork_with_lantern

    # Turn on lantern
    narrative1, interpretation1 = game_loop.process_turn("turn on lantern")

    # Verify lantern is lit (check both is_lit and is_on)
    lamp = game_state.items["lamp"]
    assert lamp.attributes.get("is_lit") is True or lamp.attributes.get("is_on") is True, \
        f"Lantern should be lit/on after turn on command, but is_lit={lamp.attributes.get('is_lit')}, is_on={lamp.attributes.get('is_on')}"

    # Move to cellar (simulating going down through trap door)
    # Note: In actual game, would need to open trap door first
    game_state.player_location = "cellar"

    # Check lighting in cellar
    lighting = game_state.get_effective_lighting("cellar")

    print(f"\nCellar lighting: {lighting}")

    # CRITICAL: Cellar should be visible with lit lantern
    assert lighting["can_see_clearly"] is True, \
        "Should be able to see in cellar with lit lantern"
    assert lighting["level"] != "pitch_black", \
        f"Cellar should not be pitch black with lit lantern, got: {lighting['level']}"
    assert len(lighting["light_sources"]) > 0, \
        "Lantern should be in light sources"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
