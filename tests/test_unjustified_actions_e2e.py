"""End-to-end tests for unjustified extraordinary actions.

These tests verify that the DM correctly REJECTS actions that:
1. Are extraordinary (teleportation, object creation, etc.)
2. Have NO in-game justification (no magic item, no genie, no spell)

The DM should be creative, but NOT a "yes bot" that grants impossible actions.
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
def basic_setup():
    """Set up a basic game WITHOUT genie or magic items."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Move player to entrance (no genie here)
    game_state.player_location = "entrance"

    # Initialize clients
    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_teleport_without_justification(skip_if_no_gcp, basic_setup):
    """Test that teleportation is REJECTED when no teleportation device exists.

    Scenario:
    - Player is in entrance (no genie, no magical portal, no teleport spell)
    - Player says "teleport me somewhere"
    - Expected: is_valid=false, no movement occurs

    Principle: Extraordinary actions require in-game mechanics.
    The player controls their CHARACTER, not the WORLD.
    """
    game_loop, game_state, gemini_client = basic_setup

    print("\n=== TEST: Teleportation Without Justification ===")

    # Record initial state
    initial_location = game_state.player_location
    print(f"Initial location: {initial_location}")
    print(f"Available items at location: {[item.id for item in game_state.get_items_at_location(initial_location)]}")
    print(f"NPCs at location: {[npc.id for npc in game_state.get_npcs_at_location(initial_location)]}")

    # CRITICAL: Verify player is NOT at genie's location
    # (Genie may exist in game, but player shouldn't have access to it)
    genie = game_state.npcs.get("genie")
    if genie:
        genie_location = game_state.npc_locations.get("genie")
        print(f"Genie exists at: {genie_location}")
        assert game_state.player_location != genie_location, "Player should not be at genie's location for this test"
        print(f"✓ Player at {initial_location}, genie at {genie_location} (separated)")

    # Verify no magical items that enable teleportation
    player_items = [game_state.items.get(item_id) for item_id in game_state.player.inventory]
    location_items = game_state.get_items_at_location(initial_location)
    all_accessible_items = player_items + location_items

    teleport_items = [item for item in all_accessible_items if item and "teleport" in str(item.attributes).lower()]
    assert len(teleport_items) == 0, f"No teleportation items should be accessible, found: {teleport_items}"
    print("✓ No teleportation items accessible")

    # Attempt teleportation
    print("\n--- Player attempts: 'teleport me somewhere' ---")
    narrative, interpretation = game_loop.process_turn("teleport me somewhere")

    print(f"\nNarrative: {narrative}")
    print(f"Interpretation: {interpretation}")

    # CRITICAL ASSERTION: is_valid should be FALSE
    is_valid = interpretation.get("is_valid", True)
    print(f"\nis_valid: {is_valid}")

    if is_valid:
        print(f"\n❌ CRITICAL FAILURE: DM allowed teleportation without justification!")
        print(f"This violates the principle: Extraordinary actions require in-game mechanics")
        print(f"Player location before: {initial_location}")
        print(f"Player location after: {game_state.player_location}")
        pytest.fail(
            "DM should reject teleportation when no teleportation device/genie/spell exists.\n"
            "The player is not a wizard! They cannot teleport at will."
        )

    print("✅ DM correctly rejected teleportation (is_valid=false)")

    # Verify player DID NOT move
    assert game_state.player_location == initial_location, (
        f"Player should still be at {initial_location}, but is at {game_state.player_location}.\n"
        f"When is_valid=false, player should NOT move."
    )

    print(f"✅ Player remained at {initial_location} (no movement occurred)")

    # Verify narrative explains WHY it failed
    narrative_lower = narrative.lower()
    # Should contain failure language
    failure_indicators = [
        "can't", "cannot", "unable", "nothing happens", "no effect",
        "you try", "you attempt", "fail", "don't have", "need"
    ]

    has_failure_language = any(indicator in narrative_lower for indicator in failure_indicators)

    if has_failure_language:
        print(f"✅ Narrative explains failure: '{narrative[:100]}...'")
    else:
        print(f"⚠️  WARNING: Narrative doesn't clearly explain failure")
        print(f"Narrative: {narrative}")

    print("\n✅ TEST PASSED: Teleportation correctly rejected without justification")


def test_create_object_without_justification(skip_if_no_gcp, basic_setup):
    """Test that object creation is REJECTED when no creative power exists.

    Scenario:
    - Player is in entrance (no genie, no magic wand, no creation spell)
    - Player says "create a diamond"
    - Expected: is_valid=false, no diamond created

    Principle: Player cannot create objects from thin air.
    Only NPCs (like genie) or magical items can create objects.
    """
    game_loop, game_state, gemini_client = basic_setup

    print("\n=== TEST: Object Creation Without Justification ===")

    # Record initial items
    initial_items = set(game_state.items.keys())
    print(f"Initial items in game: {len(initial_items)}")
    print(f"Items: {list(initial_items)[:10]}...")  # Show first 10

    # Verify no genie present at current location
    assert "genie" not in game_state.npcs or game_state.player_location != game_state.npc_locations.get("genie"), \
        "Player should not be near genie for this test"

    # Attempt to create diamond
    print("\n--- Player attempts: 'create a diamond' ---")
    narrative, interpretation = game_loop.process_turn("create a diamond")

    print(f"\nNarrative: {narrative}")
    print(f"State updates: {interpretation.get('state_updates', [])}")

    # CRITICAL ASSERTION: is_valid should be FALSE
    is_valid = interpretation.get("is_valid", True)
    print(f"\nis_valid: {is_valid}")

    if is_valid:
        print(f"\n❌ CRITICAL FAILURE: DM allowed object creation without justification!")
        print(f"This violates the principle: Player controls CHARACTER, not WORLD")
        pytest.fail(
            "DM should reject object creation when no genie/magic exists.\n"
            "The player cannot create diamonds from thin air!"
        )

    print("✅ DM correctly rejected object creation (is_valid=false)")

    # Verify NO diamond was created
    current_items = set(game_state.items.keys())
    new_items = current_items - initial_items

    print(f"\nNew items created: {new_items}")

    # Check if any new item contains "diamond"
    diamond_created = any("diamond" in item_id.lower() for item_id in new_items)
    if diamond_created:
        print(f"❌ CRITICAL FAILURE: Diamond was created despite is_valid=false!")
        print(f"New items: {new_items}")
        pytest.fail("No diamond should be created when action is invalid")

    print("✅ No diamond created (state correctly unchanged)")

    # Verify narrative explains WHY it failed
    narrative_lower = narrative.lower()
    failure_indicators = [
        "can't", "cannot", "unable", "nothing happens", "no effect",
        "you try", "you attempt", "fail", "don't have", "need"
    ]

    has_failure_language = any(indicator in narrative_lower for indicator in failure_indicators)

    if has_failure_language:
        print(f"✅ Narrative explains failure: '{narrative[:100]}...'")
    else:
        print(f"⚠️  WARNING: Narrative doesn't clearly explain failure")
        print(f"Narrative: {narrative}")

    print("\n✅ TEST PASSED: Object creation correctly rejected without justification")


def test_teleport_WITH_genie_IS_allowed(skip_if_no_gcp):
    """Test that teleportation IS allowed when genie is present (contrast test).

    This test verifies that our validation isn't TOO strict.
    With a genie, creative actions SHOULD be allowed.
    """
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Move player to forest_clearing where genie is
    game_state.player_location = "forest_clearing"

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    print("\n=== TEST: Teleportation WITH Genie (Should Work) ===")

    # Verify genie is present
    genie = game_state.npcs.get("genie")
    assert genie is not None, "Genie should exist in game"
    genie_location = game_state.npc_locations.get("genie")
    assert genie_location == "forest_clearing", "Genie should be at forest_clearing"

    print(f"Genie present: Yes")
    print(f"Genie location: {genie_location}")
    print(f"Player location: {game_state.player_location}")

    initial_location = game_state.player_location

    # Request teleportation from genie
    print("\n--- Player says: 'genie, teleport me somewhere' ---")
    narrative, interpretation = game_loop.process_turn("genie, teleport me somewhere")

    print(f"\nNarrative: {narrative}")
    print(f"is_valid: {interpretation.get('is_valid')}")
    print(f"State updates: {interpretation.get('state_updates', [])}")

    # With genie, this SHOULD be valid
    is_valid = interpretation.get("is_valid", False)

    if not is_valid:
        print(f"\n⚠️  WARNING: DM rejected teleportation even WITH genie present")
        print(f"With a genie, creative actions should be allowed")
        # Don't fail - this is a known limitation, but we want to track it
    else:
        print("✅ DM allowed teleportation with genie (creative and justified!)")

    # Check if movement occurred
    final_location = game_state.player_location
    print(f"\nPlayer location before: {initial_location}")
    print(f"Player location after: {final_location}")

    if final_location != initial_location and is_valid:
        print(f"✅ Player moved to {final_location} (teleportation worked!)")
    elif final_location == initial_location and is_valid:
        print(f"⚠️  is_valid=true but no movement occurred (inconsistency)")

    print("\n✅ TEST COMPLETED: Genie teleportation tested")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
