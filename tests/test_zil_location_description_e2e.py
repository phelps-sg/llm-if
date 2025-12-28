"""E2E test for location descriptions with ZIL translations.

Tests the describe_location method with actual Zork state to ensure:
1. ZIL translations are properly included in prompts
2. Conditional logic based on global flags works correctly
3. The LLM produces correct descriptions based on flag state
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.llm.zil_translator import ensure_zil_translations


@pytest.fixture
def gemini_client():
    """Create a GeminiClient for testing."""
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set")
    return GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")


@pytest.fixture
def zork_west_of_house():
    """Load actual Zork west_of_house location with ZIL translations."""
    game_state = GameState.from_file("worlds/zork_original.json")
    location = game_state.locations["west_of_house"]
    items = game_state.get_items_at_location("west_of_house")
    npcs = game_state.get_npcs_at_location("west_of_house")

    # Get ZIL translator
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set")
    zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")

    # Ensure ZIL translations
    location_dict, items_dicts, npcs_dicts = ensure_zil_translations(
        zil_translator,
        location=location,
        items=items,
        npcs=npcs
    )

    lighting = game_state.get_effective_lighting("west_of_house")

    return {
        "location_dict": location_dict,
        "items_dicts": items_dicts,
        "npcs_dicts": npcs_dicts,
        "lighting": lighting,
        "world_context": game_state.world_context,
    }


def test_west_of_house_without_won_flag(gemini_client, zork_west_of_house):
    """Test west_of_house description when WON-FLAG is NOT set.

    Expected: Should NOT mention secret path, forest, southwest, or trees.
    Should only describe the field, white house, boarded door, and mailbox.
    """
    player_context = {
        "inventory_ids": [],
        "inventory_items": [],
        "attributes": {"game_time": "09:15"}
    }

    # Empty flags - WON-FLAG not set
    global_flags = {}

    description = gemini_client.describe_location(
        zork_west_of_house["location_dict"],
        zork_west_of_house["items_dicts"],
        zork_west_of_house["npcs_dicts"],
        player_context=player_context,
        world_context=zork_west_of_house["world_context"],
        lighting_info=zork_west_of_house["lighting"],
        cached_descriptions=None,
        global_flags=global_flags
    )

    print(f"\nDescription (WON-FLAG not set):\n{description}\n")

    description_lower = description.lower()

    # Assertions - should NOT contain these forbidden phrases
    # (Note: "paths" for exits is OK, but "secret path" or "path into forest" is not)
    forbidden_phrases = [
        "forest",
        "southwest",
        "secret",
        "path leads",
        "path into",
        "path to the",
        "tree",
        "trees",
        "wood",
        "dense"
    ]

    for phrase in forbidden_phrases:
        assert phrase not in description_lower, (
            f"Description should NOT mention '{phrase}' when WON-FLAG is not set.\n"
            f"Description: {description}"
        )

    # Assertions - should contain these required elements
    required_words = ["field", "house", "white"]
    for word in required_words:
        assert word in description_lower, (
            f"Description should mention '{word}'.\n"
            f"Description: {description}"
        )


def test_west_of_house_with_won_flag(gemini_client, zork_west_of_house):
    """Test west_of_house description when WON-FLAG IS set.

    Expected: SHOULD mention secret path leading southwest into forest.
    """
    player_context = {
        "inventory_ids": [],
        "inventory_items": [],
        "attributes": {"game_time": "09:15"}
    }

    # WON-FLAG is set
    global_flags = {"WON-FLAG": True}

    description = gemini_client.describe_location(
        zork_west_of_house["location_dict"],
        zork_west_of_house["items_dicts"],
        zork_west_of_house["npcs_dicts"],
        player_context=player_context,
        world_context=zork_west_of_house["world_context"],
        lighting_info=zork_west_of_house["lighting"],
        cached_descriptions=None,
        global_flags=global_flags
    )

    print(f"\nDescription (WON-FLAG set):\n{description}\n")

    # When WON-FLAG is set, should mention the secret path
    description_lower = description.lower()

    # Should contain path/forest references
    has_path_mention = any(word in description_lower for word in ["path", "southwest", "forest"])
    assert has_path_mention, (
        f"Description should mention path/southwest/forest when WON-FLAG is set.\n"
        f"Description: {description}"
    )

    # Should still contain base elements
    required_words = ["field", "house", "white"]
    for word in required_words:
        assert word in description_lower, (
            f"Description should mention '{word}'.\n"
            f"Description: {description}"
        )


def test_zil_translation_in_location_dict(zork_west_of_house):
    """Verify that ZIL translation is present in the location dict."""
    location_dict = zork_west_of_house["location_dict"]

    # Should have zil_action_description
    assert "zil_action_description" in location_dict.get("attributes", {}), (
        "Location should have zil_action_description after ensure_zil_translations"
    )

    zil_desc = location_dict["attributes"]["zil_action_description"]

    # Should mention WON-FLAG in the description
    assert "WON-FLAG" in zil_desc, (
        "ZIL translation should mention WON-FLAG for west_of_house"
    )

    # Should have the base description quoted
    assert "You are standing in an open field" in zil_desc, (
        "ZIL translation should contain the base description text"
    )

    # Should mention the conditional path text
    assert "secret path" in zil_desc.lower(), (
        "ZIL translation should mention the secret path in conditional section"
    )

    print(f"\nZIL Description:\n{zil_desc}\n")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
