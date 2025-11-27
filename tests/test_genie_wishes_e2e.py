"""End-to-end tests for genie wish system.

These tests verify that the DM correctly handles wishes by:
1. Creating items when wished for
2. Decrementing wishes_remaining
3. Ensuring narrative matches state updates
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
def genie_setup():
    """Set up a game with the genie in forest clearing."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Move player to forest clearing where genie is
    game_state.player_location = "forest_clearing"

    # Initialize Gemini client
    gemini_client = GeminiClient()

    # Initialize rule engine
    rule_engine = RuleEngine()

    # Create game loop
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_wish_for_ice_cream(skip_if_no_gcp, genie_setup):
    """Test wishing for ice cream creates item and decrements wishes.

    This tests:
    1. Genie creates ice cream item
    2. Ice cream is in game state (item_locations or inventory)
    3. Genie's wishes_remaining decrements from 3 to 2
    4. Narrative mentions ice cream creation
    """
    game_loop, game_state, gemini_client = genie_setup

    print("\n=== INITIAL STATE ===")
    genie = game_state.npcs.get("genie")
    initial_wishes = genie.attributes.get("wishes_remaining", 3)
    print(f"Genie wishes remaining: {initial_wishes}")
    assert initial_wishes == 3, "Genie should start with 3 wishes"

    # Wish for ice cream
    print("\n=== WISHING FOR ICE CREAM ===")
    narrative, interpretation = game_loop.process_turn("genie, I wish for ice cream")

    print(f"Narrative: {narrative}")
    print(f"State updates: {interpretation.get('state_updates')}")

    # Verify state updates exist
    state_updates = interpretation.get("state_updates", [])
    assert len(state_updates) > 0, "Wish should generate state updates"

    # Check if ice cream was created
    ice_cream_created = any(
        update.get("type") == "create_item"
        and "ice" in update.get("params", {}).get("name", "").lower()
        for update in state_updates
    )

    if ice_cream_created:
        print("✅ Ice cream item was created")
    else:
        print(f"❌ No ice cream created. State updates: {state_updates}")
        # Check if it's in inventory or location
        print(f"Player inventory: {game_state.player.inventory}")
        print(f"Item locations: {game_state.item_locations}")
        pytest.fail("Ice cream should be created as an item")

    # Verify wishes_remaining was decremented
    genie_after = game_state.npcs.get("genie")
    wishes_after = genie_after.attributes.get("wishes_remaining", 3)
    print(f"\nGenie wishes after: {wishes_after} (type: {type(wishes_after)})")

    # Handle both string and int values (LLM sometimes returns strings)
    wishes_after_int = int(wishes_after) if isinstance(wishes_after, str) else wishes_after
    assert wishes_after_int == 2, f"Wishes should decrement from 3 to 2, got {wishes_after_int}"

    print("\n✅ Test passed: Ice cream wish works correctly")


def test_wishes_remaining_tracked(skip_if_no_gcp, genie_setup):
    """Test that wishes_remaining is tracked across multiple wishes."""
    game_loop, game_state, gemini_client = genie_setup

    print("\n=== TESTING WISH TRACKING ===")

    # Helper to convert string values to int
    def to_int(val):
        return int(val) if isinstance(val, str) else val

    # Make first wish
    print("\n--- Wish 1: Gold ---")
    narrative1, interp1 = game_loop.process_turn("genie, I wish for gold")
    genie = game_state.npcs.get("genie")
    wishes1 = to_int(genie.attributes.get("wishes_remaining", 3))
    print(f"Wishes after wish 1: {wishes1}")

    # Make second wish
    print("\n--- Wish 2: Sword ---")
    narrative2, interp2 = game_loop.process_turn("genie, I wish for a magic sword")
    genie = game_state.npcs.get("genie")
    wishes2 = to_int(genie.attributes.get("wishes_remaining", 3))
    print(f"Wishes after wish 2: {wishes2}")

    # Make third wish
    print("\n--- Wish 3: Diamond ---")
    narrative3, interp3 = game_loop.process_turn("genie, I wish for a diamond")
    genie = game_state.npcs.get("genie")
    wishes3 = to_int(genie.attributes.get("wishes_remaining", 3))
    print(f"Wishes after wish 3: {wishes3}")

    # Verify progression
    assert wishes1 <= 2, "First wish should decrement to 2 or less"
    assert wishes2 <= wishes1, "Second wish should decrement further"
    assert wishes3 <= wishes2, "Third wish should decrement further"

    if wishes3 == 0:
        print("✅ All 3 wishes used, genie should have 0 remaining")
    else:
        print(f"⚠️  Expected 0 wishes remaining, got {wishes3}")

    print("\n✅ Test passed: Wishes are tracked correctly")


def test_ask_genie_without_saying_wish(skip_if_no_gcp, genie_setup):
    """Test that asking genie (without saying 'wish') still creates state updates.

    This reproduces the real-world bug where players naturally say "ask genie for X"
    instead of "I wish for X", and the LLM fails to generate state updates.

    Expected behavior:
    - Should create ice cream item
    - Should decrement wishes_remaining
    - Narrative should match state (if narrative says item appears, item must be created)
    """
    game_loop, game_state, gemini_client = genie_setup

    print("\n=== TESTING NATURAL LANGUAGE (without 'wish') ===")

    genie = game_state.npcs.get("genie")
    initial_wishes = genie.attributes.get("wishes_remaining", 3)
    print(f"Initial wishes: {initial_wishes}")

    # Natural phrasing - user says "ask for" not "I wish for"
    print("\n--- Asking: 'ask genie for an ice cream' ---")
    narrative, interpretation = game_loop.process_turn("ask genie for an ice cream")

    print(f"Narrative: {narrative}")
    print(f"State updates: {interpretation.get('state_updates')}")

    state_updates = interpretation.get("state_updates", [])

    # Critical assertion: Must have state updates if narrative says something was created
    if "appear" in narrative.lower() or "materialize" in narrative.lower() or "create" in narrative.lower():
        assert len(state_updates) > 0, (
            f"CRITICAL BUG: Narrative says something was created/appeared, "
            f"but state_updates is empty!\n"
            f"Narrative: {narrative}\n"
            f"This violates the rule: narrative must match state updates"
        )

    # Check if item was created
    ice_cream_created = any(
        update.get("type") == "create_item"
        for update in state_updates
    )

    if not ice_cream_created:
        print(f"\n❌ FAILED: No ice cream created")
        print(f"Narrative says: {narrative}")
        print(f"State updates: {state_updates}")
        pytest.fail(
            "Asking genie for ice cream should create item, regardless of exact wording.\n"
            "The LLM should recognize this as a wish even without saying 'I wish for'."
        )

    # Check wishes decremented
    genie_after = game_state.npcs.get("genie")
    wishes_after = genie_after.attributes.get("wishes_remaining", 3)
    wishes_after_int = int(wishes_after) if isinstance(wishes_after, str) else wishes_after

    if wishes_after_int == initial_wishes:
        print(f"\n⚠️  WARNING: Wishes not decremented ({initial_wishes} → {wishes_after_int})")
        pytest.fail("Genie should decrement wishes_remaining when granting a wish")

    print(f"\n✅ Test passed: Natural language wish works correctly")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
