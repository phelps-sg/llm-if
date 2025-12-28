"""Test for transparent bottle visibility bug.

The Zork kitchen has a glass bottle with water inside. The bottle has the ZIL
'transbit' flag, indicating it's transparent. The water should be visible even
when the bottle is closed.

Bug: Currently, water is only visible when bottle is opened.
Expected: Water should be visible through transparent glass even when closed.
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def game_components():
    """Create game engine components."""
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set")

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")

    from src.main import initialize_rule_engine
    rule_engine = initialize_rule_engine()

    return {
        "gemini": gemini,
        "zil_translator": zil_translator,
        "rule_engine": rule_engine
    }


def test_zork_bottle_shows_water_without_opening():
    """Test that water is visible in closed bottle due to transbit (transparent) flag.

    In the original Zork data (zork_original.json):
    - Bottle has 'transbit' flag (transparent)
    - Water is inside bottle
    - Bottle is closed by default

    Expected behavior:
    - Player should see water through the transparent bottle without opening it
    - Looking at the bottle should mention the water inside

    Current bug:
    - Water only visible after opening bottle
    - Transparent flag ('transbit') is not being used by the engine
    """
    # Load the original Zork game state (no modifications)
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "kitchen"

    # Add lamp to see (kitchen is lit, but this ensures we can see)
    if "lamp" in game_state.items:
        game_state.player.inventory.append("lamp")
        game_state.items["lamp"].attributes["is_lit"] = True

    # Verify test preconditions from the actual data
    assert "bottle" in game_state.items, "Bottle should exist in Zork data"
    assert "water" in game_state.items, "Water should exist in Zork data"

    bottle = game_state.items["bottle"]

    # Check bottle has transbit flag (transparent)
    zil_flags = bottle.attributes.get("zil_flags", [])
    assert "transbit" in zil_flags, "Bottle should have 'transbit' flag indicating transparency"

    # Check bottle is closed
    is_open = bottle.attributes.get("open", False) or bottle.attributes.get("is_open", False)
    assert not is_open, "Bottle should be closed by default"

    # Check water is inside bottle
    water_location = game_state.item_locations.get("water")
    assert water_location == "bottle", f"Water should be in bottle, but is in: {water_location}"

    print("\n=== Test Preconditions ===")
    print(f"Bottle ZIL flags: {zil_flags}")
    print(f"Bottle open: {is_open}")
    print(f"Water location: {water_location}")
    print(f"Bottle has 'transbit': {'transbit' in zil_flags}")

    # Now test visibility
    # First, check what items the game engine considers visible in the bottle
    contents = game_state.get_items_in_container("bottle")
    print(f"\n=== Items in bottle container ===")
    print(f"Contents: {[item.name for item in contents]}")

    # The critical test: Are these contents visible to the player?
    # Check what context the game loop would build
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set - can't test with LLM")

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    from src.main import initialize_rule_engine
    rule_engine = initialize_rule_engine()

    game_loop = GameLoop(game_state, gemini, rule_engine)

    # Build context to see what container_contents includes
    context = game_loop._build_context()

    print(f"\n=== Container Contents in Context ===")
    if "container_contents" in context:
        print(f"Container contents: {context['container_contents']}")
    else:
        print("No container_contents in context!")

    # THE BUG: Bottle should be in container_contents because it's transparent
    # Currently it won't be because code only checks is_open, not transparent

    # Check if bottle contents are visible
    bottle_in_container_contents = "bottle" in context.get("container_contents", {})

    print(f"\n=== Visibility Test Result ===")
    print(f"Is bottle listed in container_contents? {bottle_in_container_contents}")

    if bottle_in_container_contents:
        print("✅ SUCCESS: Transparent bottle contents are visible!")
        bottle_contents = context["container_contents"]["bottle"]
        water_visible = any(item["id"] == "water" for item in bottle_contents)
        assert water_visible, "Water should be visible in transparent bottle contents"
    else:
        print("❌ FAILED: Transparent bottle contents are NOT visible!")
        print("This is the bug: transbit flag is not being used to show contents")

        # This assertion will fail, demonstrating the bug
        assert False, (
            "BUG CONFIRMED: Bottle has 'transbit' flag but contents not visible. "
            "The game engine only shows container contents when is_open=True, "
            "but should also show contents when transparent=True or transbit flag is present."
        )


if __name__ == "__main__":
    # Can run directly for debugging
    test_zork_bottle_shows_water_without_opening()
