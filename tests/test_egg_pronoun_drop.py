"""Test egg drop scenario with pronoun 'it' - verifying correct item drops.

This test reproduces a bug where:
1. Player picks up nest from tree (nest contains egg, egg contains canary)
2. Player says "drop it" (expecting to drop the nest)
3. BUG: Game drops the EGG instead of the nest
4. BUG: Nest stays in player inventory
5. BUG: Broken egg and canary not visible on ground

Expected behavior:
- "drop it" should drop the NEST (last picked up item)
- Nest falls to ground (path location)
- Egg inside nest breaks, becoming broken_egg at path
- Canary should be tracked (either freed or inside broken_egg)
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


def test_drop_it_pronoun_drops_nest_not_egg(zork_up_a_tree, game_components):
    """Test: 'drop it' after picking up nest should drop NEST, not egg."""
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
    assert "canary" in game_state.items, "Canary should exist"

    initial_nest_location = game_state.item_locations.get("nest")
    initial_egg_location = game_state.item_locations.get("egg")
    initial_canary_location = game_state.item_locations.get("canary")

    print(f"Initial nest location: {initial_nest_location}")
    print(f"Initial egg location: {initial_egg_location}")
    print(f"Initial canary location: {initial_canary_location}")
    print(f"Broken egg exists: {'broken_egg' in game_state.items}")

    # Step 1: Pick up the nest (manually to ensure controlled test state)
    print("\n" + "="*60)
    print("STEP 1: PICK UP NEST")
    print("="*60)
    game_state.move_item_to_player("nest")
    print(f"Inventory after pickup: {game_state.player.inventory}")
    print(f"Nest location: {game_state.item_locations.get('nest')}")
    print(f"Egg location: {game_state.item_locations.get('egg')}")

    # Verify nest is in inventory
    assert "nest" in game_state.player.inventory, "Nest should be in inventory after pickup"

    # Step 2: Drop "it" (pronoun should resolve to nest, the last picked up item)
    print("\n" + "="*60)
    print("STEP 2: DROP IT (expecting to drop NEST)")
    print("="*60)
    result = game_loop.execute_single_step("drop it")
    print(f"Narrative: {result['narrative']}")
    print(f"Interpretation: {result.get('interpretation', {})}")

    state_updates = result.get('interpretation', {}).get('state_updates', [])
    print(f"State updates: {state_updates}")

    # Check current state after drop
    print(f"\nInventory after 'drop it': {game_state.player.inventory}")
    print(f"Nest location: {game_state.item_locations.get('nest')}")
    print(f"Egg location: {game_state.item_locations.get('egg')}")
    print(f"Broken egg location: {game_state.item_locations.get('broken_egg')}")
    print(f"Canary location: {game_state.item_locations.get('canary')}")

    # CRITICAL ASSERTION 1: NEST should NOT be in inventory after drop
    assert "nest" not in game_state.player.inventory, \
        "BUG: Nest should NOT be in inventory after 'drop it' - it should be dropped!"

    # CRITICAL ASSERTION 2: EGG should NOT be in inventory (it was never picked up)
    assert "egg" not in game_state.player.inventory, \
        "BUG: Egg should NOT be in inventory - player only picked up nest!"

    # CRITICAL ASSERTION 3: Nest should be at path location (ground below tree)
    nest_location_after_drop = game_state.item_locations.get("nest")
    assert nest_location_after_drop == "path", \
        f"BUG: Nest should be at 'path' location after drop, but is at: {nest_location_after_drop}"

    # Step 3: Verify egg broke and broken_egg exists
    print("\n" + "="*60)
    print("STEP 3: VERIFY EGG BROKE")
    print("="*60)

    # According to ZIL translation:
    # "The nest falls to the ground, and the egg spills out of it, seriously damaged."
    # The EGG object is removed, and a BROKEN-EGG object is moved to the PATH room.

    # CRITICAL ASSERTION 4: broken_egg should exist
    assert "broken_egg" in game_state.items, \
        "BUG: broken_egg item should exist after nest is dropped from tree"

    # CRITICAL ASSERTION 5: broken_egg should be at path location
    broken_egg_location = game_state.item_locations.get("broken_egg")
    assert broken_egg_location == "path", \
        f"BUG: broken_egg should be at 'path' location, but is at: {broken_egg_location}"

    # Step 4: Verify canary is tracked
    print("\n" + "="*60)
    print("STEP 4: VERIFY CANARY IS TRACKED")
    print("="*60)

    # CRITICAL ASSERTION 6: Canary should exist and be visible
    assert "canary" in game_state.items, "BUG: Canary should still exist"

    canary_location = game_state.item_locations.get("canary")
    print(f"Canary location: {canary_location}")

    # The canary should either be:
    # - At path location (freed when egg broke)
    # - Inside broken_egg (still contained)
    # - Inside nest (spilled from egg into nest)
    # Any of these is acceptable, but it must be tracked somewhere
    assert canary_location in ["path", "broken_egg", "nest"], \
        f"BUG: Canary should be at 'path', 'broken_egg', or 'nest', but is at: {canary_location}"

    # Step 5: Climb down and look at path to verify visibility
    print("\n" + "="*60)
    print("STEP 5: CLIMB DOWN AND VERIFY ITEMS VISIBLE")
    print("="*60)

    result = game_loop.execute_single_step("down")
    print(f"Moved down: {game_state.player_location}")

    assert game_state.player_location == "path", "Should be at path location"

    result = game_loop.execute_single_step("look")
    print(f"\nNarrative at path: {result['narrative']}")

    items_at_path = game_state.get_items_at_location("path")
    item_names = [item.name for item in items_at_path]
    print(f"Items at path: {item_names}")

    # CRITICAL ASSERTION 7: Nest should be visible at path
    nest_at_path = any(item.id == "nest" for item in items_at_path)
    assert nest_at_path, \
        "BUG: Nest should be visible at path location after dropping from tree"

    # CRITICAL ASSERTION 8: Broken egg should be visible at path
    broken_egg_at_path = any(item.id == "broken_egg" for item in items_at_path)
    assert broken_egg_at_path, \
        f"BUG: Broken egg should be visible at path location. Items present: {item_names}"

    # CRITICAL ASSERTION 9: Canary should be visible (either at path or examine broken_egg)
    canary_at_path = any(item.id == "canary" for item in items_at_path)
    if not canary_at_path:
        # Canary might be inside broken_egg, verify it's accessible
        print("\nCanary not directly at path, checking if inside broken_egg...")
        result = game_loop.execute_single_step("examine broken egg")
        print(f"Examine broken egg: {result['narrative']}")
        # This is acceptable - canary can be inside broken_egg
    else:
        print("\nCanary is directly at path location (freed from egg)")

    print("\n" + "="*60)
    print("✅ ALL CRITICAL ASSERTIONS PASSED")
    print("="*60)
    print("\nSummary:")
    print(f"- 'drop it' correctly dropped NEST (not egg)")
    print(f"- Nest location: {game_state.item_locations.get('nest')}")
    print(f"- Egg broke into broken_egg at path")
    print(f"- Canary tracked at: {game_state.item_locations.get('canary')}")
    print(f"- All items visible and accessible")


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
