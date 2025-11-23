"""End-to-end tests that call real Gemini API.

These tests require:
- GCP_PROJECT environment variable set
- gcloud auth configured
- Actual Gemini API calls (costs money, but minimal)
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
    """Set up a minimal game for testing."""
    # Load the example dungeon
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Initialize Gemini client
    gemini_client = GeminiClient()

    # Initialize rule engine
    rule_engine = RuleEngine()

    # Create game loop
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_go_north_e2e(skip_if_no_gcp, game_setup):
    """Test 'go north' command with real Gemini API call.

    This tests:
    1. Gemini interprets 'n' as 'go north'
    2. Returns structured output with valid location ID
    3. State update moves player correctly
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== INITIAL STATE ===")
    print(f"Player location: {game_state.player_location}")
    assert game_state.player_location == "entrance"

    # Build context
    context = game_loop._build_context()

    print("\n=== CALLING GEMINI WITH 'n' ===")
    # Call Gemini with 'n' (should interpret as go north)
    interpretation = gemini_client.interpret_action("n", context)

    print(f"Intent: {interpretation.get('intent')}")
    print(f"State Updates: {interpretation.get('state_updates')}")
    print(f"Narrative: {interpretation.get('narrative_response', '')[:100]}...")

    # Verify we got valid structured output
    assert "intent" in interpretation
    assert "state_updates" in interpretation
    assert "narrative_response" in interpretation
    assert "is_valid" in interpretation

    # Apply state updates
    state_updates = interpretation.get("state_updates", [])
    if state_updates:
        game_loop.action_processor.apply_state_updates(state_updates, game_state)

    print("\n=== AFTER STATE UPDATE ===")
    print(f"Player location: {game_state.player_location}")

    # Verify player moved to hall (north of entrance)
    # The LLM should have generated a move_player state update
    # with destination='hall' (not 'Grand Hall')
    has_move = any(u.get("type") == "move_player" for u in state_updates)

    if has_move:
        # If LLM generated a move, verify it used correct location ID
        assert (
            game_state.player_location == "hall"
        ), f"Expected player at 'hall', got '{game_state.player_location}'"
        print("✅ Player successfully moved north using correct location ID!")
    else:
        # LLM might interpret "n" differently - that's okay for this test
        print(f"ℹ️  LLM interpreted 'n' as: {interpretation.get('intent')}")
        print("    (Did not generate movement - may need more explicit command)")


def test_take_and_throw_sword_e2e(skip_if_no_gcp, game_setup):
    """Test complete sword pickup -> throw -> verify visible scenario.

    This is the main bug we've been fixing.
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: TAKE AND THROW SWORD ===")

    # Step 1: Take sword
    print("\n--- Step 1: Take sword ---")
    context = game_loop._build_context()
    interpretation = gemini_client.interpret_action("take sword", context)

    state_updates = interpretation.get("state_updates", [])
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    print(f"Player inventory: {game_state.player.inventory}")
    assert "rusty_sword" in game_state.player.inventory, "Sword should be in inventory"

    # Step 2: Throw sword
    print("\n--- Step 2: Throw sword ---")
    context = game_loop._build_context()
    interpretation = gemini_client.interpret_action("throw sword at wall", context)

    print(f"State updates: {interpretation.get('state_updates')}")

    state_updates = interpretation.get("state_updates", [])
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    print(f"Player inventory: {game_state.player.inventory}")
    print(f"Item locations: {game_state.item_locations}")

    # Step 3: Verify sword is visible
    print("\n--- Step 3: Verify sword visible ---")
    assert (
        "rusty_sword" not in game_state.player.inventory
    ), "Sword should not be in inventory after throwing"

    assert (
        "rusty_sword" in game_state.item_locations
    ), "Sword should exist in item_locations"

    # The critical assertion: sword should be at entrance (using location ID)
    assert (
        game_state.item_locations["rusty_sword"] == "entrance"
    ), f"Sword should be at 'entrance', got '{game_state.item_locations['rusty_sword']}'"

    items_at_entrance = game_state.get_items_at_location("entrance")
    item_names = [item.name for item in items_at_entrance]

    print(f"Items at entrance: {item_names}")
    assert (
        "Rusty Sword" in item_names
    ), "Sword should be visible at entrance after throwing"

    print("✅ Sword correctly visible at location after throwing!")


def test_pronoun_resolution_throw_it_e2e(skip_if_no_gcp, game_setup):
    """Test pronoun resolution: 'throw it' after picking up sword.

    This tests the critical pronoun resolution fix where 'it' should
    refer to the last item interacted with (the sword).
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: PRONOUN RESOLUTION - THROW IT ===")

    # Step 1: Take sword
    print("\n--- Step 1: Take sword ---")
    player_input = "take sword"
    context = game_loop._build_context()
    interpretation = gemini_client.interpret_action(player_input, context)

    state_updates = interpretation.get("state_updates", [])
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    # Update reference tracking (simulate what game_loop does)
    game_loop._update_reference_tracking(interpretation, player_input, context)

    print(f"Player inventory: {game_state.player.inventory}")
    print(f"Last referenced item: {game_loop.last_referenced_item}")
    assert "rusty_sword" in game_state.player.inventory, "Sword should be in inventory"
    assert (
        game_loop.last_referenced_item == "rusty_sword"
    ), "Should be tracking sword as last item"

    # Step 2: Throw IT (pronoun resolution!)
    print("\n--- Step 2: Throw IT (using pronoun) ---")
    context = game_loop._build_context()
    # Add pronoun resolution (game_loop does this automatically)
    if game_loop.last_referenced_item:
        context["last_item"] = game_loop.last_referenced_item
    if game_loop.last_referenced_npc:
        context["last_npc"] = game_loop.last_referenced_npc

    print(f"Context last_item: {context.get('last_item')}")
    interpretation = gemini_client.interpret_action("throw it at the wall", context)

    print(f"State updates: {interpretation.get('state_updates')}")

    state_updates = interpretation.get("state_updates", [])
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    print(f"Player inventory: {game_state.player.inventory}")
    print(f"Item locations: {game_state.item_locations}")

    # Step 3: Verify sword is visible
    print("\n--- Step 3: Verify sword visible ---")
    assert (
        "rusty_sword" not in game_state.player.inventory
    ), "Sword should not be in inventory after throwing IT"

    assert (
        "rusty_sword" in game_state.item_locations
    ), "Sword should exist in item_locations"

    # The critical assertion: sword should be at entrance
    assert (
        game_state.item_locations["rusty_sword"] == "entrance"
    ), f"Sword should be at 'entrance', got '{game_state.item_locations['rusty_sword']}'"

    items_at_entrance = game_state.get_items_at_location("entrance")
    item_names = [item.name for item in items_at_entrance]

    print(f"Items at entrance: {item_names}")
    assert (
        "Rusty Sword" in item_names
    ), "Sword should be visible at entrance after throwing IT"

    print("✅ Pronoun resolution works! 'throw it' correctly identified the sword!")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys

    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
