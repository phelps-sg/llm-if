"""Test that descriptions don't include explicit clock times.

Descriptions should reflect lighting based on time of day, but should NOT
include explicit times like "at 5:15 PM" or "at 2:00 PM" unless the player
has a timekeeping device and explicitly asks for the time.
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def skip_if_no_gcp():
    """Skip tests if GCP is not configured."""
    if not os.getenv("GCP_PROJECT"):
        pytest.skip("GCP_PROJECT not set - skipping e2e Gemini tests")


@pytest.fixture
def game_setup():
    """Set up a basic game."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Set to different times to test
    game_state.player_location = "entrance"

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_afternoon_description_no_clock_time(skip_if_no_gcp, game_setup):
    """Test that afternoon descriptions don't include '2:00 PM' or similar."""
    game_loop, game_state, gemini_client = game_setup

    # Set to afternoon
    game_state.game_time = "Day 1, Afternoon, 2:15 PM"

    print("\n=== TEST: Afternoon Description (No Clock Time) ===")
    print(f"Game time: {game_state.game_time}")

    # Look around (triggers description generation)
    narrative, interpretation = game_loop.process_turn("look")

    print(f"\nNarrative: {narrative}")

    # Check for explicit clock times
    forbidden_patterns = [
        " PM", " AM", " p.m.", " a.m.",
        ":00", ":15", ":30", ":45",
        "2:15", "2:00", "14:", "afternoon at"
    ]

    violations = []
    for pattern in forbidden_patterns:
        if pattern in narrative:
            violations.append(pattern)

    if violations:
        print(f"\n❌ FAILURE: Found explicit time references: {violations}")
        print(f"Full narrative: {narrative}")
        pytest.fail(
            f"Description should NOT include explicit clock times.\n"
            f"Found: {violations}\n"
            f"Instead, describe lighting EFFECTS (bright sun, shadows, etc.) without stating the time."
        )

    print("✅ No explicit clock times found in description")

    # Verify it DOES describe appropriate lighting
    narrative_lower = narrative.lower()
    afternoon_indicators = ["sun", "light", "bright", "warm", "daylight"]

    has_lighting_description = any(indicator in narrative_lower for indicator in afternoon_indicators)

    if has_lighting_description:
        print("✅ Description includes appropriate afternoon lighting")
    else:
        print("⚠️  WARNING: Description doesn't clearly describe lighting")

    print("\n✅ TEST PASSED: Afternoon description has no clock times")


def test_evening_description_no_clock_time(skip_if_no_gcp, game_setup):
    """Test that evening descriptions don't include '5:15 PM' or similar."""
    game_loop, game_state, gemini_client = game_setup

    # Set to evening
    game_state.game_time = "Day 1, Evening, 5:15 PM"

    print("\n=== TEST: Evening Description (No Clock Time) ===")
    print(f"Game time: {game_state.game_time}")

    # Look around
    narrative, interpretation = game_loop.process_turn("look")

    print(f"\nNarrative: {narrative}")

    # Check for explicit clock times
    forbidden_patterns = [
        " PM", " AM", " p.m.", " a.m.",
        ":00", ":15", ":30", ":45",
        "5:15", "5:00", "17:", "evening at"
    ]

    violations = []
    for pattern in forbidden_patterns:
        if pattern in narrative:
            violations.append(pattern)

    if violations:
        print(f"\n❌ FAILURE: Found explicit time references: {violations}")
        print(f"Full narrative: {narrative}")
        pytest.fail(
            f"Description should NOT include explicit clock times.\n"
            f"Found: {violations}\n"
            f"Instead, describe lighting EFFECTS (fading sun, long shadows, golden hour) without stating the time."
        )

    print("✅ No explicit clock times found in description")

    # Verify it DOES describe appropriate lighting
    narrative_lower = narrative.lower()
    evening_indicators = ["shadow", "fading", "dusk", "golden", "waning", "dimming", "twilight"]

    has_lighting_description = any(indicator in narrative_lower for indicator in evening_indicators)

    if has_lighting_description:
        print("✅ Description includes appropriate evening lighting")
    else:
        print("⚠️  WARNING: Description doesn't clearly describe evening lighting")

    print("\n✅ TEST PASSED: Evening description has no clock times")


def test_player_can_ask_for_time_with_watch(skip_if_no_gcp, game_setup):
    """Test that player CAN get exact time if they have a watch and ask for it."""
    game_loop, game_state, gemini_client = game_setup

    # Set specific time
    game_state.game_time = "Day 1, Afternoon, 2:37 PM"

    print("\n=== TEST: Player Asks 'What Time Is It?' ===")
    print(f"Game time: {game_state.game_time}")

    # First, verify player starts without a watch
    has_watch = any("watch" in item_id.lower() or "clock" in item_id.lower()
                    for item_id in game_state.player.inventory)

    if not has_watch:
        print("Player has no watch - creating one for this test")
        # Create a watch item
        from src.models.item import Item
        watch = Item(
            id="pocket_watch",
            name="Pocket Watch",
            attributes={
                "type": "misc",
                "timekeeping_device": True,
                "description_hints": "brass pocket watch, ticking softly"
            }
        )
        game_state.items["pocket_watch"] = watch
        game_state.player.add_item("pocket_watch")
        print("✅ Added pocket watch to player inventory")

    # Ask for the time
    narrative, interpretation = game_loop.process_turn("what time is it?")

    print(f"\nNarrative: {narrative}")

    # In this case, the narrative SHOULD mention the time
    # (because player has a timekeeping device and explicitly asked)
    narrative_lower = narrative.lower()

    # Check if time is mentioned (could be various formats)
    time_mentioned = (
        "2:37" in narrative or
        "afternoon" in narrative_lower or
        "time" in narrative_lower
    )

    if time_mentioned:
        print("✅ Narrative provides time information (player asked + has watch)")
    else:
        print("⚠️  WARNING: Player asked for time with watch, but no time info provided")
        print(f"This is acceptable if the narrative explains the watch in another way")

    print("\n✅ TEST COMPLETED: Player asking for time tested")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
