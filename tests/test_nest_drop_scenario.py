"""Test nest drop scenario from tree - item should move to ground, not stay in tree.

This test reproduces a bug where:
1. Player picks up nest from tree
2. Player drops nest (falls to ground, egg breaks)
3. Player looks - nest STILL appears in tree (incorrect)

Expected: Nest should be on ground below, not still in tree.
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop
from src.config import DEFAULT_DM_MODEL, DEFAULT_ZIL_TRANSLATOR_MODEL


@pytest.fixture
def game_components():
    """Create game engine components."""
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set")

    gemini = GeminiClient(project=gcp_project, model_name=DEFAULT_DM_MODEL)
    zil_translator = GeminiClient(project=gcp_project, model_name=DEFAULT_ZIL_TRANSLATOR_MODEL)

    from src.main import initialize_rule_engine
    rule_engine = initialize_rule_engine()

    return {
        "gemini": gemini,
        "zil_translator": zil_translator,
        "rule_engine": rule_engine
    }


@pytest.fixture
def zork_up_a_tree():
    """Player in tree with nest and egg."""
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "up_a_tree"
    return game_state


def test_nest_drop_from_tree_moves_to_ground(zork_up_a_tree, game_components):
    """Test: Dropping nest from tree should move it to ground, not leave it in tree."""
    game_state = zork_up_a_tree
    game_loop = GameLoop(
        game_state,
        game_components["gemini"],
        game_components["rule_engine"],
        zil_translator_client=game_components["zil_translator"]
    )

    print("\n" + "="*60)
    print("INITIAL STATE: UP A TREE")
    print("="*60)

    # Verify initial state
    assert game_state.player_location == "up_a_tree"
    assert "nest" in game_state.items, "Nest should exist"
    assert "egg" in game_state.items, "Jeweled egg should exist"

    initial_nest_location = game_state.item_locations.get("nest")
    print(f"Initial nest location: {initial_nest_location}")
    print(f"Initial egg location: {game_state.item_locations.get('egg')}")

    # Step 1: Look at initial state
    print("\n" + "="*60)
    print("STEP 1: LOOK AT TREE")
    print("="*60)
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}")

    # Nest should be visible in tree
    assert "nest" in result['narrative'].lower(), "Should see nest in tree initially"

    # Step 2: Pick up the nest (manually for test - bypass LLM restrictions)
    print("\n" + "="*60)
    print("STEP 2: PICK UP NEST (simulated)")
    print("="*60)
    # Manually move nest to inventory to test the drop behavior
    game_state.move_item_to_player("nest")
    print(f"Nest manually added to inventory: {game_state.player.inventory}")

    # Verify nest is now in inventory
    assert "nest" in game_state.player.inventory, "Nest should be in inventory"

    # Step 3: Drop the nest
    print("\n" + "="*60)
    print("STEP 3: DROP NEST")
    print("="*60)
    result = game_loop.execute_single_step("drop the nest")
    print(f"Narrative: {result['narrative']}")
    print(f"Interpretation: {result.get('interpretation', {})}")
    state_updates = result.get('interpretation', {}).get('state_updates', [])
    print(f"State updates: {state_updates}")

    # Verify nest is no longer in inventory
    assert "nest" not in game_state.player.inventory, "Nest should not be in inventory after drop"

    # Check where nest ended up
    nest_location_after_drop = game_state.item_locations.get("nest")
    print(f"Nest location after drop: {nest_location_after_drop}")

    # Step 4: Look around again
    print("\n" + "="*60)
    print("STEP 4: LOOK AT TREE AGAIN")
    print("="*60)
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}")

    # Get items currently at tree location and path location
    items_at_tree = game_state.get_items_at_location("up_a_tree")
    items_at_path = game_state.get_items_at_location("path")  # PATH is the ground below tree

    print(f"\nItems at tree: {[item.name for item in items_at_tree]}")
    print(f"Items at path (ground below): {[item.name for item in items_at_path]}")

    # CRITICAL ASSERTION: Nest should NOT be in tree anymore
    nest_in_tree = any(item.id == "nest" for item in items_at_tree)
    assert not nest_in_tree, "Nest should NOT be in tree after dropping - it fell to ground"

    # CRITICAL ASSERTION: Nest SHOULD be at path location (ground below)
    nest_at_path = any(item.id == "nest" for item in items_at_path)
    assert nest_at_path, "Nest SHOULD be at path location (the ground below the tree)"

    # CRITICAL ASSERTION: Nest item should NOT appear in description
    # (checking for "bird's nest" or "nest" as standalone word, not "nestled")
    narrative_lower = result['narrative'].lower()
    # Check if actual nest item is mentioned, not just word "nest" in "nestled"
    has_nest_item = ("bird's nest" in narrative_lower or
                     "the nest" in narrative_lower or
                     "a nest" in narrative_lower)
    assert not has_nest_item, "Should NOT see bird's nest item in tree after dropping it"

    # CRITICAL ASSERTION: Verify exact location per ZIL behavior
    # ZIL says: Items dropped from tree are moved to PATH room (the ground below)
    assert nest_location_after_drop == "path", f"Nest should be at 'path' location (was: {nest_location_after_drop})"

    print("\n" + "="*60)
    print("✅ TEST PASSED")
    print("="*60)


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
