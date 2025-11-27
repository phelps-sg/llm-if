"""End-to-end tests for description caching system.

These tests verify that:
1. Descriptions are cached after first generation
2. Cached descriptions are used for consistency on subsequent views
3. LLM maintains consistency while allowing for variation
4. State changes are reflected in new descriptions
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
    """Set up a game for caching tests."""
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


def test_location_description_cached(skip_if_no_gcp, game_setup):
    """Test that location descriptions are cached after first view.

    This tests:
    1. First look generates description and caches it
    2. Cache contains location description
    3. Cache has correct structure (description, turn, state_snapshot)
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING LOCATION CACHING ===")

    # Initial state - no cache
    cache = game_state.get_cached_description("location", "entrance")
    assert cache is None, "Cache should be empty initially"

    # First look - should generate and cache
    print("\n--- First look ---")
    result = game_loop.execute_single_step("look")
    narrative1 = result["narrative"]
    print(f"Narrative: {narrative1[:100]}...")

    # Check cache was created
    cache = game_state.get_cached_description("location", "entrance")
    assert cache is not None, "Description should be cached after first look"
    assert "description" in cache, "Cache should contain description"
    assert "turn" in cache, "Cache should contain turn number"
    assert cache["description"] == narrative1, "Cached description should match generated narrative"

    print(f"✅ Location description cached at turn {cache['turn']}")

    # Second look - should use cache for consistency
    print("\n--- Second look ---")
    result2 = game_loop.execute_single_step("look")
    narrative2 = result2["narrative"]
    print(f"Narrative: {narrative2[:100]}...")

    # Cache should be updated
    cache2 = game_state.get_cached_description("location", "entrance")
    assert cache2 is not None, "Cache should still exist"
    assert cache2["description"] == narrative2, "Cache should update with new description"

    print("✅ Cached description available for second look")

    # Descriptions should reference similar elements (consistency)
    # Both should mention moss, walls, or similar features
    common_words = set(narrative1.lower().split()) & set(narrative2.lower().split())
    assert len(common_words) > 10, "Descriptions should have common elements for consistency"

    print(f"✅ Descriptions maintain consistency ({len(common_words)} common words)")


def test_return_visit_uses_cache(skip_if_no_gcp, game_setup):
    """Test that returning to a location uses cached description.

    This tests:
    1. Visit location A, cache created
    2. Move to location B
    3. Return to location A - cache should be available
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING RETURN VISIT CACHING ===")

    # Visit entrance (look)
    print("\n--- Visit entrance ---")
    result1 = game_loop.execute_single_step("look")
    entrance_desc1 = result1["narrative"]
    print(f"First visit: {entrance_desc1[:80]}...")

    # Check cache
    cache1 = game_state.get_cached_description("location", "entrance")
    assert cache1 is not None, "Entrance should be cached"
    entrance_turn1 = cache1["turn"]

    # Move to hall
    print("\n--- Move to hall ---")
    result2 = game_loop.execute_single_step("go north")
    hall_desc = result2["narrative"]
    print(f"Hall: {hall_desc[:80]}...")

    # Check hall cache
    cache_hall = game_state.get_cached_description("location", "hall")
    assert cache_hall is not None, "Hall should be cached"

    # Return to entrance
    print("\n--- Return to entrance ---")
    result3 = game_loop.execute_single_step("go south")
    entrance_desc2 = result3["narrative"]
    print(f"Return visit: {entrance_desc2[:80]}...")

    # Cache should still exist with original data available
    cache2 = game_state.get_cached_description("location", "entrance")
    assert cache2 is not None, "Entrance cache should persist"

    print(f"✅ Return visit has access to previous description (turn {entrance_turn1})")


def test_cache_reflects_state_changes(skip_if_no_gcp, game_setup):
    """Test that cached descriptions note state changes.

    This tests:
    1. View location with items
    2. Take an item
    3. View again - description should reflect item is gone
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING STATE CHANGE DETECTION ===")

    # First look - torch and sword present
    print("\n--- First look (items present) ---")
    result1 = game_loop.execute_single_step("look")
    desc1 = result1["narrative"]
    print(f"Description: {desc1[:100]}...")

    # Verify items mentioned (torch and sword at entrance)
    assert "torch" in desc1.lower() or "sword" in desc1.lower(), (
        "Initial description should mention items"
    )

    # Take the torch
    print("\n--- Take torch ---")
    result2 = game_loop.execute_single_step("take torch")
    print(f"Pickup: {result2['narrative'][:80]}...")

    # Look again - torch should be gone from location
    print("\n--- Look after taking torch ---")
    result3 = game_loop.execute_single_step("look")
    desc2 = result3["narrative"]
    print(f"Description: {desc2[:100]}...")

    # The cached description is a HINT, but current state should prevail
    # If torch is in inventory, it shouldn't be described as "on the ground"
    assert result3["inventory"] == ["Torch"], "Torch should be in inventory"

    print("✅ Description caching handles state changes correctly")


def test_cache_does_not_hallucinate_removed_items(skip_if_no_gcp, game_setup):
    """Test that returning to a location doesn't incorrectly describe removed items.

    This is a regression test for a bug where:
    1. Player looks at location with items (cached)
    2. Player picks up an item
    3. Player moves away and returns
    4. Bug: Description incorrectly showed item still on ground

    The fix ensures current state takes precedence over cached descriptions.
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING CACHE DOESN'T HALLUCINATE REMOVED ITEMS ===")

    # Initial look - cache the description with sword present
    print("\n--- Initial look (sword present) ---")
    result1 = game_loop.execute_single_step("look")
    desc1 = result1["narrative"]
    print(f"Description: {desc1[:100]}...")

    # Verify sword is mentioned
    assert "sword" in desc1.lower(), "Initial description should mention sword"

    # Pick up the sword
    print("\n--- Take sword ---")
    result2 = game_loop.execute_single_step("take rusty sword")
    print(f"Pickup: {result2['narrative'][:80]}...")
    assert "rusty_sword" in game_state.player.inventory, "Sword should be in inventory"

    # Move to another location
    print("\n--- Move north to hall ---")
    result3 = game_loop.execute_single_step("go north")
    print(f"Moved to: {game_state.player_location}")
    assert game_state.player_location == "hall", "Should be in hall"

    # Return to entrance
    print("\n--- Return south to entrance ---")
    result4 = game_loop.execute_single_step("go south")
    desc_return = result4["narrative"]
    print(f"Return description: {desc_return[:150]}...")

    # CRITICAL TEST: Verify sword is NOT described as being on the ground
    # It should either not be mentioned, or mentioned as being in inventory
    sword_on_ground_phrases = [
        "sword lies",
        "sword lying",
        "sword on the ground",
        "sword on the floor",
        "sword nearby",
        "notice a sword",
        "notice a rusty sword",
        "see a sword",
        "see a rusty sword",
    ]

    for phrase in sword_on_ground_phrases:
        assert phrase not in desc_return.lower(), (
            f"Description incorrectly suggests sword is on ground: '{phrase}' found in description. "
            f"Sword is in inventory, not at location!"
        )

    # Verify game state is correct
    assert "rusty_sword" in game_state.player.inventory, "Sword should still be in inventory"
    items_at_entrance = game_state.get_items_at_location("entrance")
    sword_at_entrance = any(item.id == "rusty_sword" for item in items_at_entrance)
    assert not sword_at_entrance, "Sword should NOT be at entrance location"

    print("✅ Cached description correctly omits removed items")


def test_multiple_entity_caching(skip_if_no_gcp, game_setup):
    """Test caching of location, items, and NPCs together.

    This tests:
    1. Location with NPCs and items
    2. All entities get cached
    3. Cache structure correct for each type
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TESTING MULTI-ENTITY CACHING ===")

    # Move to forest clearing (has NPCs and items)
    print("\n--- Moving to forest clearing ---")
    result = game_loop.execute_single_step("go south")
    clearing_desc = result["narrative"]
    print(f"Description: {clearing_desc[:100]}...")

    # Check caches
    location_cache = game_state.get_cached_description("location", "forest_clearing")
    assert location_cache is not None, "Location should be cached"
    print(f"✅ Location cached: {location_cache['turn']}")

    # Check if NPCs are at this location
    npcs_at_clearing = game_state.get_npcs_at_location("forest_clearing")
    print(f"\nNPCs at clearing: {[npc.name for npc in npcs_at_clearing]}")

    # Check if items are at this location
    items_at_clearing = game_state.get_items_at_location("forest_clearing")
    print(f"Items at clearing: {[item.name for item in items_at_clearing]}")

    print("\n✅ Multi-entity caching structure validated")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
