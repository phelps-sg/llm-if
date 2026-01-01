"""E2E test for Zork lantern lighting bug.

This test reproduces the bug reported in the playthrough test where:
1. Player gets the lantern from Living Room
2. Player turns on the lantern (narrative confirms it's on)
3. Player goes underground to cellar
4. BUG: Location is pitch black despite lit lantern

Expected: Lit lantern should provide light underground.
"""

import pytest
from src.models.game_state import GameState
from src.engine.game_loop import GameLoop
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine


@pytest.fixture
def zork_game():
    """Initialize Zork game state at Living Room with lantern."""
    game_state = GameState.from_file("worlds/zork_original.json")

    # Start at Living Room
    game_state.player_location = "living_room"

    # Give player the lantern (simulating getting it from trophy case)
    game_state.move_item_to_player("lamp")

    # Initialize game loop
    gemini = GeminiClient(project="test", dry_run=True)
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini, rule_engine)

    return game_state, game_loop


def test_lantern_not_lit_underground_is_dark(zork_game):
    """Test that unlit lantern doesn't provide light underground."""
    game_state, game_loop = zork_game

    # Lantern starts unlit
    lamp = game_state.items["lamp"]
    assert lamp.attributes.get("is_lit") is False

    # Go down to cellar
    game_state.player_location = "cellar"

    # Check lighting - should be pitch black (no lit light source)
    lighting = game_state.get_effective_lighting("cellar")

    assert lighting["level"] == "pitch_black" or lighting["level"] == "dark", \
        "Cellar should be dark without lit lantern"
    assert lighting["can_see_clearly"] is False, \
        "Should not be able to see clearly in dark cellar without lit lantern"


def test_lantern_turned_on_provides_light_underground(zork_game):
    """Test that turning on lantern provides light underground.

    This is the CRITICAL test that reproduces the bug from the playthrough.
    """
    game_state, game_loop = zork_game

    # Turn on the lantern
    lamp = game_state.items["lamp"]
    lamp.attributes["is_lit"] = True

    # Verify lantern attributes are correct
    assert lamp.attributes.get("provides_light") is True, \
        "Lantern should have provides_light=True"
    assert lamp.attributes.get("is_lit") is True, \
        "Lantern should be lit after turning on"
    assert lamp.attributes.get("type") == "light_source", \
        "Lantern should be a light_source type"

    # Go down to cellar
    game_state.player_location = "cellar"

    # Check lighting - BUG: This currently fails because lighting system
    # only checks provides_light but not is_lit
    lighting = game_state.get_effective_lighting("cellar")

    print(f"Lighting level: {lighting['level']}")
    print(f"Artificial light: {lighting['artificial']}")
    print(f"Light sources: {lighting['light_sources']}")
    print(f"Can see clearly: {lighting['can_see_clearly']}")

    # THESE ASSERTIONS SHOULD PASS but currently FAIL due to bug
    assert lighting["level"] != "pitch_black", \
        "Cellar should NOT be pitch black with lit lantern"
    assert lighting["artificial"] != "none", \
        "Lit lantern should provide artificial light"
    assert len(lighting["light_sources"]) > 0, \
        "Lit lantern should be in light_sources list"
    assert lighting["can_see_clearly"] is True, \
        "Should be able to see clearly with lit lantern"

    # Check that lantern is recognized as a light source
    light_source_names = [source for source in lighting["light_sources"]]
    assert any("lantern" in source.lower() or "lamp" in source.lower()
               for source in light_source_names), \
        f"Lantern should be in light sources, got: {light_source_names}"


def test_lantern_lighting_sequence_like_playthrough(zork_game):
    """Test the exact sequence from the playthrough report.

    1. Start at Living Room with lantern
    2. Turn on lantern (set is_lit=True)
    3. Go down to cellar
    4. Verify cellar is visible
    5. Go north to Troll Room
    6. Verify troll room is visible
    """
    game_state, game_loop = zork_game

    # Step 1: At Living Room with lantern
    assert game_state.player_location == "living_room"
    assert "lamp" in game_state.player.inventory

    # Step 2: Turn on lantern
    lamp = game_state.items["lamp"]
    lamp.attributes["is_lit"] = True

    # Step 3: Go down to cellar
    game_state.player_location = "cellar"

    # Step 4: Verify cellar is visible
    cellar_lighting = game_state.get_effective_lighting("cellar")
    assert cellar_lighting["can_see_clearly"] is True, \
        "Cellar should be visible with lit lantern"
    assert cellar_lighting["level"] in ["dim", "bright"], \
        f"Cellar should have dim or bright light, got: {cellar_lighting['level']}"

    # Step 5: Go north to Troll Room
    game_state.player_location = "troll_room"

    # Step 6: Verify troll room is visible
    troll_lighting = game_state.get_effective_lighting("troll_room")
    assert troll_lighting["can_see_clearly"] is True, \
        "Troll Room should be visible with lit lantern"
    assert troll_lighting["level"] in ["dim", "bright"], \
        f"Troll Room should have dim or bright light, got: {troll_lighting['level']}"


def test_lantern_light_level_attribute():
    """Test that lantern has correct light level when lit."""
    game_state = GameState.from_file("worlds/zork_original.json")

    lamp = game_state.items["lamp"]

    # Check if lantern has a light_level attribute
    # If not, it should default to "dim" or "bright"
    light_level = lamp.attributes.get("light_level")

    # Lantern should either have explicit light_level or we assume "dim"
    if light_level:
        assert light_level in ["dim", "bright"], \
            f"Lantern light_level should be dim or bright, got: {light_level}"

    # The important attributes for lighting
    assert lamp.attributes.get("provides_light") is True
    assert lamp.attributes.get("type") == "light_source"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
