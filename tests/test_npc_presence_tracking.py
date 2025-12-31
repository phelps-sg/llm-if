"""Test that NPCs are not hallucinated in narration when they're not present.

This test reproduces the Blather bug where:
1. Player is with NPC in location A
2. Player moves to location B (NPC stays behind)
3. Narrative should NOT mention NPC from history
4. Narrative should ONLY describe current location

Bug example from Planetfall:
> w
...location description...
Ensign First Class Blather continues to loom over you... [WRONG - Blather not here!]
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
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
def planetfall_reactor_lobby():
    """Load Planetfall at reactor lobby with Blather."""
    game_state = GameState.from_file("worlds/planetfall.json")
    game_state.player_location = "reactor_lobby"

    # Manually place Blather at reactor lobby for testing
    # (In actual game, Blather is spawned by events/scripts)
    if "blather" in game_state.npcs:
        game_state.npc_locations["blather"] = "reactor_lobby"

    return game_state


def test_npc_not_hallucinated_after_movement(planetfall_reactor_lobby, game_components):
    """Test: NPCs should not appear in narrative after player leaves."""
    game_state = planetfall_reactor_lobby
    game_loop = GameLoop(
        game_state,
        game_components["gemini"],
        game_components["rule_engine"],
        zil_translator_client=game_components["zil_translator"]
    )

    print("\n" + "="*70)
    print("TEST: NPC Presence Tracking")
    print("="*70)

    # Step 1: Verify Blather is present at reactor lobby
    print("\n--- Step 1: Initial State ---")
    print(f"Location: {game_state.player_location}")

    blather_id = "blather"  # Assuming this is the NPC ID
    initial_blather_location = game_state.npc_locations.get(blather_id)
    print(f"Blather location: {initial_blather_location}")

    # Look around to establish Blather's presence
    print("\n--- Step 2: Look Around (Blather should be mentioned) ---")
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}")

    npcs_at_reactor = game_state.get_npcs_at_location("reactor_lobby")
    blather_at_reactor = any(npc.id == blather_id for npc in npcs_at_reactor)

    if blather_at_reactor:
        print("✓ Blather is at reactor lobby")
        # Narrative should mention Blather (but we don't assert on exact text)
    else:
        pytest.skip("Blather not at reactor lobby - test setup issue")

    # Step 3: Move west to deck nine
    print("\n--- Step 3: Move West (Leave Blather Behind) ---")
    result = game_loop.execute_single_step("west")
    print(f"New location: {game_state.player_location}")
    print(f"Narrative: {result['narrative']}")

    # Verify player moved
    assert game_state.player_location != "reactor_lobby", "Player should have moved"

    # Verify Blather is NOT at new location
    npcs_at_new_location = game_state.get_npcs_at_location(game_state.player_location)
    blather_at_new_location = any(npc.id == blather_id for npc in npcs_at_new_location)

    print(f"NPCs at new location: {[npc.name for npc in npcs_at_new_location]}")
    assert not blather_at_new_location, f"Blather should NOT be at {game_state.player_location}"

    # CRITICAL ASSERTION: Narrative should NOT mention Blather
    narrative_lower = result['narrative'].lower()
    blather_mentions = [
        "blather",
        "ensign first class",  # His title
    ]

    blather_mentioned = any(mention in narrative_lower for mention in blather_mentions)

    print("\n--- Step 4: Check Narrative for Hallucination ---")
    print(f"Blather mentioned in narrative: {blather_mentioned}")

    assert not blather_mentioned, (
        f"BUG: Narrative mentions Blather when he's not present!\n"
        f"Narrative: {result['narrative']}\n"
        f"NPCs at location: {[npc.name for npc in npcs_at_new_location]}"
    )

    # Step 5: Do another action to verify Blather doesn't reappear
    print("\n--- Step 5: Look Around at New Location ---")
    result = game_loop.execute_single_step("look")
    print(f"Narrative: {result['narrative']}")

    narrative_lower = result['narrative'].lower()
    blather_mentioned = any(mention in narrative_lower for mention in blather_mentions)

    assert not blather_mentioned, (
        f"BUG: Blather STILL mentioned in second narrative!\n"
        f"Narrative: {result['narrative']}\n"
        f"NPCs at location: {[npc.name for npc in npcs_at_new_location]}"
    )

    print("\n" + "="*70)
    print("✅ TEST PASSED - No NPC Hallucination")
    print("="*70)
    print("Summary:")
    print("- Blather was present at reactor lobby")
    print("- Player moved to new location")
    print("- Blather did NOT follow")
    print("- Narrative correctly omits Blather after movement")


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
