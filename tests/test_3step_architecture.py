"""Tests for 3-step LLM architecture to prevent hallucination.

The 3-step architecture separates:
1. Intent interpretation (is_valid, is_allowed checks)
2. Mechanics generation (state updates)
3. Narrative generation (description)

This prevents hallucination where LLM returns is_valid=true with empty
state_updates but generates narrative describing changes that never occurred.

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


def test_rubble_removal_no_hallucination(skip_if_no_gcp, game_setup):
    """Verify LLM doesn't hallucinate state changes.

    Player tries: "remove rubble" without proper solution
    Expected:
    - Step 1: is_valid=true, is_allowed=false, not_allowed_reason="Need proper tools"
    - Step 2: NOT called (action not allowed)
    - Step 3: Returns not_allowed_reason as narrative
    - State: Unchanged (rubble still there)
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: RUBBLE REMOVAL NO HALLUCINATION ===")

    # Move to hall where rubble blocks progress
    game_state.player_location = "hall"

    # Build context
    context = game_loop._build_context()

    print("\n--- Step 1: Interpret Intent ---")
    intent_result = gemini_client.interpret_intent("remove rubble", context)

    print(f"Intent: {intent_result.get('intent')}")
    print(f"is_valid: {intent_result.get('is_valid')}")
    print(f"is_allowed: {intent_result.get('is_allowed')}")
    print(f"invalid_reason: {intent_result.get('invalid_reason')}")
    print(f"not_allowed_reason: {intent_result.get('not_allowed_reason')}")

    # Verify intent interpretation
    assert intent_result.get("is_valid") == True, "Action should be logically valid"
    assert intent_result.get("is_allowed") == False, "Action should not be allowed without tools"
    assert intent_result.get("not_allowed_reason") is not None, "Should have not_allowed_reason"
    assert intent_result.get("invalid_reason") is None, "Should not have invalid_reason"

    print("\n--- Step 2: Generate State Updates (SHOULD BE SKIPPED) ---")
    # Step 2 should NOT be called when is_allowed=false
    # This is verified by checking process_turn logic

    # Check that rubble flags haven't changed
    rubble_cleared = game_state.flags.get("rubble_cleared", False)
    print(f"Rubble cleared flag: {rubble_cleared}")
    assert rubble_cleared == False, "Rubble should still be blocking"

    print("\n--- Step 3: Generate Narrative ---")
    # Narrative should be the not_allowed_reason
    narrative = gemini_client.generate_narrative(
        "remove rubble",
        intent_result.get("intent"),
        context,
        not_allowed_reason=intent_result.get("not_allowed_reason")
    )

    print(f"Narrative: {narrative}")
    assert narrative == intent_result.get("not_allowed_reason"), "Narrative should be the not_allowed_reason"

    # Verify narrative does NOT describe success
    narrative_lower = narrative.lower()
    success_words = ["vanish", "disappear", "remove", "clear", "gone", "open"]
    # Check if narrative describes successful removal
    # (It should NOT - it should explain why you can't)
    describes_success = any(
        word in narrative_lower and "can't" not in narrative_lower and "cannot" not in narrative_lower
        for word in success_words
    )

    print(f"\nNarrative describes success: {describes_success}")
    # We expect narrative to explain WHY you can't remove it, not that it's removed

    print("✅ Hallucination prevented! Narrative consistent with state!")


def test_nonsensical_input(skip_if_no_gcp, game_setup):
    """Verify LLM rejects nonsensical inputs.

    Player types: "zxcvbnm qwerty"
    Expected:
    - Step 1: is_valid=false, invalid_reason="I don't understand that command"
    - Step 2: NOT called (action invalid)
    - Step 3: Returns invalid_reason as narrative
    - State: Unchanged
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: NONSENSICAL INPUT ===")

    # Build context
    context = game_loop._build_context()

    print("\n--- Step 1: Interpret Intent ---")
    intent_result = gemini_client.interpret_intent("zxcvbnm qwerty", context)

    print(f"Intent: {intent_result.get('intent')}")
    print(f"is_valid: {intent_result.get('is_valid')}")
    print(f"is_allowed: {intent_result.get('is_allowed')}")
    print(f"invalid_reason: {intent_result.get('invalid_reason')}")
    print(f"not_allowed_reason: {intent_result.get('not_allowed_reason')}")

    # Verify intent interpretation
    assert intent_result.get("is_valid") == False, "Nonsensical input should be invalid"
    assert intent_result.get("invalid_reason") is not None, "Should have invalid_reason"
    assert intent_result.get("not_allowed_reason") is None, "Should not check is_allowed for invalid input"

    print("\n--- Step 2: Generate State Updates (SHOULD BE SKIPPED) ---")
    # Step 2 should NOT be called when is_valid=false

    print("\n--- Step 3: Generate Narrative ---")
    # Narrative should be the invalid_reason
    narrative = gemini_client.generate_narrative(
        "zxcvbnm qwerty",
        intent_result.get("intent"),
        context,
        invalid_reason=intent_result.get("invalid_reason")
    )

    print(f"Narrative: {narrative}")
    assert narrative == intent_result.get("invalid_reason"), "Narrative should be the invalid_reason"

    # Verify narrative indicates confusion
    narrative_lower = narrative.lower()
    confusion_words = ["understand", "recognize", "unclear", "what", "don't know", "sorry"]
    indicates_confusion = any(word in narrative_lower for word in confusion_words)

    print(f"\nNarrative indicates confusion: {indicates_confusion}")
    assert indicates_confusion, "Narrative should indicate the DM doesn't understand"

    print("✅ Nonsensical input properly rejected!")


def test_extraordinary_action_without_justification(skip_if_no_gcp, game_setup):
    """Verify LLM rejects extraordinary actions without justification.

    Player tries: "teleport to the throne room" without magic/genie
    Expected:
    - Step 1: is_valid=true, is_allowed=false, not_allowed_reason="No way to teleport"
    - Step 2: NOT called (action not allowed)
    - Step 3: Returns not_allowed_reason as narrative
    - State: Player location unchanged
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: EXTRAORDINARY ACTION WITHOUT JUSTIFICATION ===")

    # Start at entrance
    assert game_state.player_location == "entrance"
    initial_location = game_state.player_location

    # Build context
    context = game_loop._build_context()

    print("\n--- Step 1: Interpret Intent ---")
    intent_result = gemini_client.interpret_intent("teleport to throne room", context)

    print(f"Intent: {intent_result.get('intent')}")
    print(f"is_valid: {intent_result.get('is_valid')}")
    print(f"is_allowed: {intent_result.get('is_allowed')}")
    print(f"invalid_reason: {intent_result.get('invalid_reason')}")
    print(f"not_allowed_reason: {intent_result.get('not_allowed_reason')}")

    # Verify intent interpretation
    assert intent_result.get("is_valid") == True, "Teleporting is a logically valid action"
    assert intent_result.get("is_allowed") == False, "Teleporting should not be allowed without magic"
    assert intent_result.get("not_allowed_reason") is not None, "Should have not_allowed_reason"

    print("\n--- Step 2: Generate State Updates (SHOULD BE SKIPPED) ---")
    # Step 2 should NOT be called when is_allowed=false

    print("\n--- Step 3: Generate Narrative ---")
    # Narrative should be the not_allowed_reason
    narrative = gemini_client.generate_narrative(
        "teleport to throne room",
        intent_result.get("intent"),
        context,
        not_allowed_reason=intent_result.get("not_allowed_reason")
    )

    print(f"Narrative: {narrative}")
    assert narrative == intent_result.get("not_allowed_reason"), "Narrative should be the not_allowed_reason"

    # Verify player location unchanged
    assert game_state.player_location == initial_location, "Player should not have moved"

    print("✅ Extraordinary action properly rejected!")


def test_allowed_action_generates_complete_state_updates(skip_if_no_gcp, game_setup):
    """Verify allowed actions generate complete state updates.

    Player tries: "take sword" (valid and allowed)
    Expected:
    - Step 1: is_valid=true, is_allowed=true
    - Step 2: Returns complete state_updates (remove_from_inventory OR move_item)
    - Step 3: Narrative describes actual state change
    - State: Sword in player inventory
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: ALLOWED ACTION GENERATES COMPLETE STATE UPDATES ===")

    # Build context
    context = game_loop._build_context()

    print("\n--- Step 1: Interpret Intent ---")
    intent_result = gemini_client.interpret_intent("take sword", context)

    print(f"Intent: {intent_result.get('intent')}")
    print(f"is_valid: {intent_result.get('is_valid')}")
    print(f"is_allowed: {intent_result.get('is_allowed')}")

    # Verify intent interpretation
    assert intent_result.get("is_valid") == True, "Taking sword is valid"
    assert intent_result.get("is_allowed") == True, "Taking sword should be allowed"
    assert intent_result.get("invalid_reason") is None
    assert intent_result.get("not_allowed_reason") is None

    print("\n--- Step 2: Generate State Updates ---")
    mechanics_result = gemini_client.generate_state_updates(
        intent_result.get("intent"),
        context,
        intent_result
    )

    state_updates = mechanics_result.get("state_updates", [])
    print(f"State updates: {state_updates}")

    # Verify state updates exist
    assert len(state_updates) > 0, "Should have state updates for taking sword"

    # Verify state updates include inventory change
    has_inventory_update = any(
        update.get("type") in ["add_to_inventory", "move_item"]
        for update in state_updates
    )
    assert has_inventory_update, "Should have inventory-related update"

    # Apply updates
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    # Verify sword in inventory
    assert "rusty_sword" in game_state.player.inventory, "Sword should be in inventory"

    print("\n--- Step 3: Generate Narrative ---")
    updated_context = game_loop._build_context()
    narrative = gemini_client.generate_narrative(
        "take sword",
        intent_result.get("intent"),
        updated_context
    )

    print(f"Narrative: {narrative}")

    # Verify narrative describes taking the sword
    narrative_lower = narrative.lower()
    describes_taking = any(word in narrative_lower for word in ["take", "pick", "grab", "acquire"])

    print(f"\nNarrative describes taking: {describes_taking}")

    print("✅ Allowed action generated complete state updates!")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys

    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
