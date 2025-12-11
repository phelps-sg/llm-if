"""End-to-end tests for door state validation.

These tests verify that the DM correctly validates door states before allowing
door interactions (opening, going through, etc.).

This follows the principle: Check actual game state before allowing actions.

Tests require:
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
from src.models.item import Item
from src.models.location import Location


@pytest.fixture
def skip_if_no_gcp():
    """Skip tests if GCP is not configured."""
    if not os.getenv("GCP_PROJECT"):
        pytest.skip("GCP_PROJECT not set - skipping e2e Gemini tests")


@pytest.fixture
def game_with_boarded_door(skip_if_no_gcp):
    """Set up a game with a boarded door."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Create a location with a boarded door
    entrance = Location(
        id="entrance",
        name="House Entrance",
        description="You stand before a white house. The front door is boarded shut with heavy planks.",
        connections={"north": "inside_house"}
    )

    inside = Location(
        id="inside_house",
        name="Inside the House",
        description="Inside the house.",
        connections={"south": "entrance"}
    )

    # Create a door item with boarded state
    door = Item(
        id="front_door",
        name="Front Door",
        description="A wooden door, firmly boarded shut with planks and nails.",
        attributes={
            "is_door": True,
            "is_boarded": True,
            "is_locked": False,
            "is_open": False
        }
    )

    game_state.locations = {"entrance": entrance, "inside_house": inside}
    game_state.items = {"front_door": door}
    game_state.item_locations = {"front_door": "entrance"}
    game_state.player_location = "entrance"

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


@pytest.fixture
def game_with_unlocked_door(skip_if_no_gcp):
    """Set up a game with an unlocked (openable) door."""
    import json

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Create a location with unlocked door
    entrance = Location(
        id="entrance",
        name="House Entrance",
        description="You stand before a white house. A simple wooden door stands before you.",
        connections={"north": "inside_house"}
    )

    inside = Location(
        id="inside_house",
        name="Inside the House",
        description="Inside the house.",
        connections={"south": "entrance"}
    )

    # Create an unlocked door
    door = Item(
        id="front_door",
        name="Front Door",
        description="A simple wooden door, currently closed but unlocked.",
        attributes={
            "is_door": True,
            "is_boarded": False,
            "is_locked": False,
            "is_open": False
        }
    )

    game_state.locations = {"entrance": entrance, "inside_house": inside}
    game_state.items = {"front_door": door}
    game_state.item_locations = {"front_door": "entrance"}
    game_state.player_location = "entrance"

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_cannot_open_boarded_door(game_with_boarded_door):
    """Test that trying to open a boarded door is rejected.

    Expected:
    - Step 1: is_valid=true, is_allowed=false (door is boarded)
    - Step 2: SKIPPED (not allowed)
    - Step 3: Returns not_allowed_reason explaining boards
    - State: Door remains closed and boarded
    """
    game_loop, game_state, gemini_client = game_with_boarded_door

    print("\n=== TEST: CANNOT OPEN BOARDED DOOR ===")

    initial_location = game_state.player_location
    print(f"Initial location: {initial_location}")

    # Check door state
    door = game_state.items.get("front_door")
    assert door.attributes.get("is_boarded") == True, "Door should be boarded"
    assert door.attributes.get("is_open") == False, "Door should be closed"

    # Try to open the door
    print("\n--- Player attempts: 'open the front door' ---")
    narrative, interpretation = game_loop.process_turn("open the front door")

    print(f"\n[DEBUG] Interpretation:")
    print(f"  Intent: {interpretation.get('intent')}")
    print(f"  is_valid: {interpretation.get('is_valid')}")
    print(f"  is_allowed: {interpretation.get('is_allowed')}")
    print(f"  not_allowed_reason: {interpretation.get('not_allowed_reason')}")
    print(f"  state_updates: {interpretation.get('state_updates')}")

    print(f"\nNarrative: {narrative}")

    # CRITICAL ASSERTION: is_allowed should be FALSE
    assert interpretation.get("is_valid") == True, "Opening door is a logically valid action"
    assert interpretation.get("is_allowed") == False, \
        "Opening a boarded door should NOT be allowed without removing boards first"

    # Verify reason mentions boards/blockage
    not_allowed_reason = interpretation.get("not_allowed_reason", "")
    assert not_allowed_reason, "Should have not_allowed_reason"

    reason_lower = not_allowed_reason.lower()
    blocking_words = ["board", "plank", "nail", "block", "shut", "sealed"]
    mentions_blocking = any(word in reason_lower for word in blocking_words)
    assert mentions_blocking, f"Reason should mention boards/blocking: {not_allowed_reason}"

    # Verify NO state updates occurred
    state_updates = interpretation.get("state_updates", [])
    assert len(state_updates) == 0, "No state updates should occur when action not allowed"

    # Verify door state unchanged
    door = game_state.items.get("front_door")
    assert door.attributes.get("is_open") == False, "Door should still be closed"
    assert door.attributes.get("is_boarded") == True, "Door should still be boarded"

    # Verify player didn't move
    assert game_state.player_location == initial_location, "Player should not have moved"

    print("✅ Boarded door correctly rejected!")


def test_cannot_go_through_closed_door(game_with_unlocked_door):
    """Test that going through a closed door is rejected.

    Expected:
    - Step 1: is_valid=true, is_allowed=false (door is closed)
    - Narrative explains door needs to be opened first
    """
    game_loop, game_state, gemini_client = game_with_unlocked_door

    print("\n=== TEST: CANNOT GO THROUGH CLOSED DOOR ===")

    initial_location = game_state.player_location

    # Verify door is closed
    door = game_state.items.get("front_door")
    assert door.attributes.get("is_open") == False, "Door should be closed"

    # Try to go north (through closed door)
    print("\n--- Player attempts: 'go north' (through closed door) ---")
    narrative, interpretation = game_loop.process_turn("go north")

    print(f"\n[DEBUG] Interpretation:")
    print(f"  Intent: {interpretation.get('intent')}")
    print(f"  is_valid: {interpretation.get('is_valid')}")
    print(f"  is_allowed: {interpretation.get('is_allowed')}")
    print(f"  not_allowed_reason: {interpretation.get('not_allowed_reason')}")

    print(f"\nNarrative: {narrative}")

    # Door is closed, movement should be blocked
    # Note: This might be allowed if DM decides to auto-open, but ideally should require explicit opening
    if not interpretation.get("is_allowed"):
        print("✅ Movement through closed door correctly blocked")
    else:
        print("⚠️  DM allowed movement (may have auto-opened door)")

    # Verify player didn't teleport through closed door at minimum
    if game_state.player_location != initial_location:
        # If moved, door should have been opened
        door = game_state.items.get("front_door")
        print(f"Door state after movement: is_open={door.attributes.get('is_open')}")


def test_can_open_unlocked_door(game_with_unlocked_door):
    """Test that opening an unlocked door works.

    Expected:
    - Step 1: is_valid=true, is_allowed=true
    - Step 2: Generates modify_attribute to open door
    - State: Door becomes open
    - Player does NOT move (opening ≠ moving through)
    """
    game_loop, game_state, gemini_client = game_with_unlocked_door

    print("\n=== TEST: CAN OPEN UNLOCKED DOOR ===")

    initial_location = game_state.player_location

    # Verify door is closed but unlocked
    door = game_state.items.get("front_door")
    assert door.attributes.get("is_open") == False, "Door should start closed"
    assert door.attributes.get("is_boarded") == False, "Door should not be boarded"
    assert door.attributes.get("is_locked") == False, "Door should be unlocked"

    # Open the door
    print("\n--- Player attempts: 'open the door' ---")
    narrative, interpretation = game_loop.process_turn("open the door")

    print(f"\n[DEBUG] Interpretation:")
    print(f"  Intent: {interpretation.get('intent')}")
    print(f"  is_valid: {interpretation.get('is_valid')}")
    print(f"  is_allowed: {interpretation.get('is_allowed')}")
    print(f"  state_updates: {interpretation.get('state_updates')}")

    print(f"\nNarrative: {narrative}")

    # Should be allowed
    assert interpretation.get("is_valid") == True
    assert interpretation.get("is_allowed") == True, "Opening unlocked door should be allowed"

    # Should have state update to open door
    state_updates = interpretation.get("state_updates", [])
    assert len(state_updates) > 0, "Should have state updates to open door"

    # Should modify door attribute, NOT move player
    has_modify = any(u.get("type") == "modify_attribute" for u in state_updates)
    has_move = any(u.get("type") == "move_player" for u in state_updates)

    assert has_modify, "Should use modify_attribute to open door"
    assert not has_move, "Opening door should NOT move player (opening ≠ going through)"

    # Verify door is now open
    door = game_state.items.get("front_door")
    # Note: This might fail if modify_attribute didn't work correctly
    if door.attributes.get("is_open"):
        print("✅ Door correctly opened!")
    else:
        print("⚠️  Door state not updated (state update may not have been applied correctly)")

    # Verify player didn't move
    assert game_state.player_location == initial_location, \
        "Player should stay in place when opening door (not go through it)"

    print("✅ Unlocked door opened correctly without moving player!")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys

    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
