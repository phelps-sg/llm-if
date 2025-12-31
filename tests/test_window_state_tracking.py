"""Test how state is tracked when interacting with ZIL-translated objects.

This test investigates the kitchen window to understand:
1. What state updates the LLM generates when player opens the window
2. How the system tracks state (attributes vs flags vs global variables)
3. Whether subsequent interactions reflect the changed state
"""

import pytest
import os
import json
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
def zork_behind_house():
    """Player behind house where kitchen window is visible."""
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "east_of_house"  # Behind house
    return game_state


def test_window_state_tracking_workflow(zork_behind_house, game_components):
    """Test: Opening window and verifying state is tracked correctly."""
    game_state = zork_behind_house
    game_loop = GameLoop(
        game_state,
        game_components["gemini"],
        game_components["rule_engine"],
        zil_translator_client=game_components["zil_translator"]
    )

    print("\n" + "="*60)
    print("INITIAL STATE")
    print("="*60)
    print(f"Location: {game_state.player_location}")
    window = game_state.items.get("kitchen_window")
    assert window is not None, "Kitchen window should exist"
    print(f"Window attributes: {json.dumps(window.attributes, indent=2)}")

    # Verify initial state
    assert window.attributes.get("is_open") == False, "Window should start closed"
    assert game_state.flags == {}, "Should have no global flags initially"

    # Step 1: Look around
    print("\n" + "="*60)
    print("STEP 1: LOOK AROUND")
    print("="*60)
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}\n")

    # Step 2: Examine window
    print("\n" + "="*60)
    print("STEP 2: EXAMINE WINDOW")
    print("="*60)
    result = game_loop.execute_single_step("examine window")
    print(f"Narrative: {result['narrative']}")
    print(f"State updates: {json.dumps(result.get('state_updates', []), indent=2)}")

    # Step 3: Open window
    print("\n" + "="*60)
    print("STEP 3: OPEN WINDOW")
    print("="*60)
    result = game_loop.execute_single_step("open window")
    print(f"Narrative: {result['narrative']}")
    print(f"State updates: {json.dumps(result.get('state_updates', []), indent=2)}")

    # Check window state after opening
    print("\n" + "="*60)
    print("WINDOW STATE AFTER OPENING")
    print("="*60)
    window = game_state.items.get("kitchen_window")
    assert window is not None, "Window should still exist"
    print(f"Window attributes: {json.dumps(window.attributes, indent=2)}")

    # CRITICAL ASSERTION: Window should now be open (single source of truth)
    assert window.attributes.get("is_open") == True, "Window should be open after OPEN command"
    # CRITICAL ASSERTION: No legacy global flags should be created
    assert "KITCHEN-WINDOW-FLAG" not in game_state.flags, "Should not create legacy KITCHEN-WINDOW-FLAG"
    assert "kitchen_window_flag" not in game_state.flags, "Should not create kitchen_window_flag"

    # Step 4: Look around again
    print("\n" + "="*60)
    print("STEP 4: LOOK AROUND AGAIN")
    print("="*60)
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}\n")

    # CRITICAL ASSERTION: Description should reflect window is now open
    narrative_lower = result['narrative'].lower()
    assert "open" in narrative_lower, "Room description should mention window is open"

    # Step 5: Examine window again
    print("\n" + "="*60)
    print("STEP 5: EXAMINE WINDOW AGAIN")
    print("="*60)
    result = game_loop.execute_single_step("examine window")
    print(f"Narrative: {result['narrative']}")

    # Final state check
    print("\n" + "="*60)
    print("FINAL WINDOW STATE")
    print("="*60)
    window = game_state.items.get("kitchen_window")
    assert window is not None, "Window should exist at end"
    print(f"Window attributes: {json.dumps(window.attributes, indent=2)}")

    # CRITICAL ASSERTION: Window should still be open
    assert window.attributes.get("is_open") == True, "Window should remain open"

    # Check for global flags
    print("\n" + "="*60)
    print("CHECK FOR LEGACY FLAGS")
    print("="*60)
    print(f"Flags: {game_state.flags}")
    print(f"DM state keys: {list(game_state.dm_state.keys())}")

    # CRITICAL ASSERTION: No legacy flags should exist
    assert "KITCHEN-WINDOW-FLAG" not in game_state.flags, "Should never create legacy KITCHEN-WINDOW-FLAG"
    assert "kitchen_window_flag" not in game_state.flags, "Should never create kitchen_window_flag"

    print("\n" + "="*60)
    print("✅ ALL ASSERTIONS PASSED")
    print("="*60)
    print("Summary:")
    print("- Window state tracked via is_open attribute (single source of truth)")
    print("- No legacy global flags created")
    print("- Narrative reflects current state correctly")
    print("- State persists across multiple interactions")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
