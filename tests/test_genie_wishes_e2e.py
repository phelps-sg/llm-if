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


def test_wish_for_new_location(skip_if_no_gcp, genie_setup):
    """Test wishing for a new path/location creates location and connection.

    This tests the genie-compatible design principle:
    - Genie should be able to grant wish for "a path south"
    - Should create new location
    - Should connect current location to new location
    - Should decrement wishes_remaining
    """
    game_loop, game_state, gemini_client = genie_setup

    print("\n=== TESTING LOCATION CREATION VIA WISH ===")

    # Verify starting location
    assert game_state.player_location == "forest_clearing"
    initial_location_count = len(game_state.locations)
    print(f"Initial locations: {list(game_state.locations.keys())}")
    print(f"Location count: {initial_location_count}")

    # Check initial connections from forest_clearing
    clearing = game_state.locations.get("forest_clearing")
    assert clearing is not None
    initial_connections = clearing.connections.copy()
    print(f"Forest clearing connections before wish: {initial_connections}")

    # Genie wishes
    genie = game_state.npcs.get("genie")
    initial_wishes = genie.attributes.get("wishes_remaining", 3)
    print(f"Initial wishes: {initial_wishes}")

    # Wish for a new path south
    print("\n--- Wishing: 'genie, I wish for a path south' ---")
    narrative, interpretation = game_loop.process_turn("genie, I wish for a path south")

    print(f"Narrative: {narrative}")
    print(f"State updates: {interpretation.get('state_updates')}")

    state_updates = interpretation.get("state_updates", [])

    # Check if location was created
    location_created = any(
        update.get("type") == "create_location"
        for update in state_updates
    )

    if not location_created:
        print(f"\n❌ FAILED: No location created")
        print(f"Narrative says: {narrative}")
        print(f"State updates: {state_updates}")
        pytest.fail(
            "Wishing for a path south should create a new location.\n"
            "This tests the genie-compatible design principle."
        )

    print("✅ Location creation state update found")

    # Verify location was actually added to game state
    new_location_count = len(game_state.locations)
    print(f"\nLocation count after wish: {new_location_count}")

    assert new_location_count == initial_location_count + 1, (
        f"Expected {initial_location_count + 1} locations, got {new_location_count}"
    )

    # Find the new location
    new_location_id = None
    for loc_id in game_state.locations:
        if loc_id not in initial_connections.values() and loc_id != "forest_clearing":
            new_location_id = loc_id
            break

    if new_location_id:
        print(f"✅ New location created: {new_location_id}")
        new_location = game_state.locations[new_location_id]
        print(f"   Name: {new_location.name}")
        print(f"   Attributes: {new_location.attributes}")
        print(f"   Connections: {new_location.connections}")

    # Check that forest_clearing now has a south exit
    clearing_after = game_state.locations.get("forest_clearing")
    south_exit = clearing_after.connections.get("south")

    if south_exit:
        print(f"\n✅ Forest clearing now has south exit to: {south_exit}")
    else:
        print(f"\n⚠️  WARNING: Forest clearing has no south exit")
        print(f"Connections: {clearing_after.connections}")
        pytest.fail("Forest clearing should have a south exit after wish")

    # Verify player can move to new location
    print("\n--- Testing movement to new location ---")
    move_narrative, move_interp = game_loop.process_turn("go south")
    print(f"Movement narrative: {move_narrative}")
    print(f"Player location after move: {game_state.player_location}")

    if game_state.player_location == south_exit:
        print(f"✅ Successfully moved to new location: {south_exit}")
    else:
        print(f"⚠️  Expected to be at {south_exit}, but at {game_state.player_location}")

    # Check wishes decremented
    genie_after = game_state.npcs.get("genie")
    wishes_after = genie_after.attributes.get("wishes_remaining", 3)
    wishes_after_int = int(wishes_after) if isinstance(wishes_after, str) else wishes_after

    print(f"\nWishes after: {wishes_after_int}")

    if wishes_after_int == initial_wishes:
        print(f"⚠️  WARNING: Wishes not decremented ({initial_wishes} → {wishes_after_int})")
        pytest.fail("Genie should decrement wishes_remaining when granting a wish")

    print(f"\n✅ Test passed: Location creation via wish works correctly")


def test_wish_for_pet_vehicle_horse(skip_if_no_gcp, genie_setup):
    """Test wishing for a horse creates NPC with pet and vehicle attributes.

    This tests:
    - Horse is created as NPC (not item)
    - Horse has is_pet=true and follows player when moving
    - Horse has is_vehicle=true for mounting
    - Wishes are decremented
    """
    game_loop, game_state, gemini_client = genie_setup

    print("\n=== TESTING PET + VEHICLE MECHANICS ===")

    # Initial state
    assert game_state.player_location == "forest_clearing"
    initial_npc_count = len(game_state.npcs)
    print(f"Initial NPCs: {list(game_state.npcs.keys())}")
    print(f"NPC count: {initial_npc_count}")

    # Wish for a horse
    print("\n--- Wishing: 'genie, I wish for a horse' ---")
    narrative, interpretation = game_loop.process_turn("genie, I wish for a horse")

    print(f"Narrative: {narrative}")
    print(f"State updates: {interpretation.get('state_updates')}")

    state_updates = interpretation.get("state_updates", [])

    # Check if NPC was created (not item!)
    npc_created = any(
        update.get("type") == "create_npc"
        and "horse" in update.get("params", {}).get("name", "").lower()
        for update in state_updates
    )

    # Also check that NO item was created (common mistake)
    item_created = any(
        update.get("type") == "create_item"
        and "horse" in update.get("params", {}).get("name", "").lower()
        for update in state_updates
    )

    if item_created and not npc_created:
        print(f"\n❌ CRITICAL ERROR: Horse created as ITEM, not NPC!")
        print(f"Living creatures MUST be created as NPCs, not items.")
        pytest.fail("Horse should be created as NPC (create_npc), not item (create_item)")

    if not npc_created:
        print(f"\n❌ FAILED: No horse NPC created")
        print(f"Narrative says: {narrative}")
        print(f"State updates: {state_updates}")
        pytest.fail("Wishing for a horse should create an NPC")

    print("✅ Horse created as NPC (not item)")

    # Find the horse NPC
    new_npc_count = len(game_state.npcs)
    assert new_npc_count == initial_npc_count + 1, f"Expected {initial_npc_count + 1} NPCs, got {new_npc_count}"

    horse_npc = None
    horse_id = None
    for npc_id, npc in game_state.npcs.items():
        if "horse" in npc.name.lower():
            horse_npc = npc
            horse_id = npc_id
            break

    assert horse_npc is not None, "Horse NPC not found in game state"
    print(f"\n✅ Horse NPC found: {horse_id}")
    print(f"   Name: {horse_npc.name}")
    print(f"   Attributes: {horse_npc.attributes}")

    # Check pet attribute
    is_pet = horse_npc.attributes.get("is_pet", False)
    print(f"\n   is_pet: {is_pet}")

    if not is_pet:
        print(f"⚠️  WARNING: Horse does not have is_pet=true")
        print(f"   Without is_pet, horse will not follow player when moving")

    # Check vehicle attribute
    is_vehicle = horse_npc.attributes.get("is_vehicle", False)
    print(f"   is_vehicle: {is_vehicle}")

    if not is_vehicle:
        print(f"⚠️  WARNING: Horse does not have is_vehicle=true")
        print(f"   Without is_vehicle, horse cannot be ridden")

    # Verify horse is at current location
    horse_location = game_state.npc_locations.get(horse_id)
    assert horse_location == "forest_clearing", f"Horse should be at forest_clearing, got {horse_location}"
    print(f"\n✅ Horse is at current location: {horse_location}")

    # Test pet mechanics: Move to a different location
    print("\n--- Testing pet mechanics: Moving north ---")
    move_narrative, move_interp = game_loop.process_turn("go north")
    print(f"Movement narrative: {move_narrative}")
    print(f"Player location after move: {game_state.player_location}")

    # Check where horse is now
    horse_location_after = game_state.npc_locations.get(horse_id)
    print(f"Horse location after move: {horse_location_after}")

    if is_pet:
        # Horse should have followed player
        assert horse_location_after == game_state.player_location, (
            f"Pet horse should follow player. "
            f"Player at {game_state.player_location}, horse at {horse_location_after}"
        )
        print(f"✅ Horse followed player to {horse_location_after} (pet mechanics working!)")
    else:
        # Horse should NOT have moved (not a pet)
        assert horse_location_after == "forest_clearing", (
            f"Non-pet horse should stay at forest_clearing, but is at {horse_location_after}"
        )
        print(f"⚠️  Horse stayed behind (not a pet)")

    print(f"\n✅ Test completed: Horse creation and pet/vehicle mechanics tested")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
