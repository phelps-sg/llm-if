"""E2E test for game loop with ZIL translations.

Tests that the full game loop correctly uses ZIL translations in all stages.
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def zork_game_at_west_of_house():
    """Load Zork and position player at west_of_house."""
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "west_of_house"
    return game_state


@pytest.fixture
def game_components():
    """Create game engine components."""
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set")

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")

    # Initialize rule engine same as main.py
    from src.main import initialize_rule_engine
    rule_engine = initialize_rule_engine()

    return {
        "gemini": gemini,
        "zil_translator": zil_translator,
        "rule_engine": rule_engine
    }


def test_look_command_without_won_flag(zork_game_at_west_of_house, game_components):
    """Test that 'look' command at west_of_house doesn't mention secret path when WON-FLAG not set."""
    game_state = zork_game_at_west_of_house
    game_loop = GameLoop(
        game_state,
        game_components["gemini"],
        game_components["rule_engine"],
        zil_translator_client=game_components["zil_translator"]
    )

    # Execute single step
    result = game_loop.execute_single_step("look")

    narrative = result["narrative"]
    print(f"\nNarrative from game loop:\n{narrative}\n")

    narrative_lower = narrative.lower()

    # Should NOT mention forest/secret/southwest when WON-FLAG not set
    forbidden_phrases = [
        "forest",
        "southwest",
        "secret",
        "path leads",
        "path into",
        "tree",
        "trees",
        "wood",
        "dense"
    ]

    for phrase in forbidden_phrases:
        assert phrase not in narrative_lower, (
            f"Game loop narrative should NOT mention '{phrase}' when WON-FLAG not set.\n"
            f"Narrative: {narrative}"
        )

    # Should mention basic elements
    assert "field" in narrative_lower, "Should mention field"
    assert "house" in narrative_lower, "Should mention house"


def test_look_command_with_won_flag(zork_game_at_west_of_house, game_components):
    """Test that 'look' command at west_of_house DOES mention secret path when WON-FLAG is set."""
    game_state = zork_game_at_west_of_house

    # Set the WON-FLAG
    game_state.flags["WON-FLAG"] = True

    game_loop = GameLoop(
        game_state,
        game_components["gemini"],
        game_components["rule_engine"],
        zil_translator_client=game_components["zil_translator"]
    )

    # Execute single step
    result = game_loop.execute_single_step("look")

    narrative = result["narrative"]
    print(f"\nNarrative with WON-FLAG:\n{narrative}\n")

    narrative_lower = narrative.lower()

    # SHOULD mention path/forest/southwest when WON-FLAG is set
    has_path_reference = any(word in narrative_lower for word in ["path", "southwest", "forest"])

    assert has_path_reference, (
        f"Game loop narrative should mention path/southwest/forest when WON-FLAG is set.\n"
        f"Narrative: {narrative}"
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
