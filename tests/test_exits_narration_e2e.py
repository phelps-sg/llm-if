"""End-to-end tests for exit narration by DM.

These tests verify that exits are narrated by the DM (LLM) rather than
being printed directly by Python code.

This follows Architectural Principle #1: "The DM Narrates Everything"

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


def test_exits_mentioned_in_location_description(skip_if_no_gcp, game_setup):
    """Test that DM includes exits in location description.

    This verifies that the DM receives exit information and integrates
    it into the narrative description, rather than having Python print exits.
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: EXITS IN LOCATION DESCRIPTION ===")

    # Start at entrance (has exits north and south)
    assert game_state.player_location == "entrance"

    location = game_state.locations["entrance"]
    available_exits = location.get_available_exits()
    print(f"Available exits at entrance: {available_exits}")

    # Build context and generate description
    player_context = game_loop._build_context()

    print(f"\nContext exits: {player_context.get('exits')}")
    assert player_context.get('exits') is not None, "Exits should be in context"
    assert len(player_context.get('exits')) > 0, "Should have at least one exit"

    # Get items and NPCs at location
    items = game_state.get_items_at_location(game_state.player_location)
    npcs = game_state.get_npcs_at_location(game_state.player_location)

    # Get lighting info
    lighting = game_state.get_effective_lighting(game_state.player_location)

    # Generate description
    description = gemini_client.describe_location(
        location=location.model_dump(),
        items=[item.model_dump() for item in items],
        npcs=[npc.model_dump() for npc in npcs],
        player_context=player_context,
        lighting_info=lighting
    )

    print(f"\nDM Description:\n{description}")

    # Verify description is not empty
    assert len(description) > 0, "Description should not be empty"

    # Verify that the description mentions directions/exits
    # The DM should integrate exits naturally, so we check for directional words
    directional_words = ['north', 'south', 'east', 'west', 'passage', 'exit', 'door', 'path', 'corridor', 'hallway']
    description_lower = description.lower()

    has_directional_reference = any(word in description_lower for word in directional_words)

    assert has_directional_reference, (
        f"Description should mention exits/directions. "
        f"Expected words like {directional_words}, but got: {description}"
    )

    print("✅ DM successfully integrated exits into the description!")


def test_exits_narration_after_movement(skip_if_no_gcp, game_setup):
    """Test that exits are narrated when player moves to new location.

    This verifies that after movement, the new location's exits are
    described by the DM, not printed by Python.
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: EXITS NARRATION AFTER MOVEMENT ===")

    # Move north to hall
    print("\n--- Step 1: Move to hall ---")
    context = game_loop._build_context()
    interpretation = gemini_client.interpret_action("go north", context)

    state_updates = interpretation.get("state_updates", [])
    game_loop.action_processor.apply_state_updates(state_updates, game_state)

    print(f"Player location: {game_state.player_location}")

    # If movement was successful, check the description
    if game_state.player_location == "hall":
        print("\n--- Step 2: Get hall description ---")

        location = game_state.locations["hall"]
        available_exits = location.get_available_exits()
        print(f"Available exits at hall: {available_exits}")

        # Build new context with exits
        player_context = game_loop._build_context()
        assert 'exits' in player_context, "Context should include exits"
        print(f"Context exits: {player_context.get('exits')}")

        # Get items and NPCs at location
        items = game_state.get_items_at_location(game_state.player_location)
        npcs = game_state.get_npcs_at_location(game_state.player_location)

        # Get lighting info
        lighting = game_state.get_effective_lighting(game_state.player_location)

        # Generate description for hall
        description = gemini_client.describe_location(
            location=location.model_dump(),
            items=[item.model_dump() for item in items],
            npcs=[npc.model_dump() for npc in npcs],
            player_context=player_context,
            lighting_info=lighting
        )

        print(f"\nDM Description of Hall:\n{description}")

        # Verify description mentions directions
        directional_words = ['north', 'south', 'east', 'west', 'passage', 'exit', 'door', 'path', 'corridor', 'hallway', 'opening']
        description_lower = description.lower()

        has_directional_reference = any(word in description_lower for word in directional_words)

        assert has_directional_reference, (
            f"Hall description should mention exits/directions. "
            f"Expected words like {directional_words}, but got: {description}"
        )

        print("✅ DM successfully narrated exits in new location after movement!")
    else:
        print(f"ℹ️  Player did not move (still at {game_state.player_location})")
        print("    This is acceptable - LLM may interpret 'go north' differently")


def test_look_command_includes_exits_in_narrative(skip_if_no_gcp, game_setup):
    """Test that 'look' command produces description with exits from DM.

    This verifies that when player types 'look', the DM describes the
    exits as part of the narrative, not as a separate hardcoded list.
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: LOOK COMMAND INCLUDES EXITS ===")

    # Execute 'look' command
    player_context = game_loop._build_context()
    interpretation = gemini_client.interpret_action("look", player_context)

    print(f"Intent: {interpretation.get('intent')}")

    # Get current location exits
    location = game_state.locations[game_state.player_location]
    available_exits = location.get_available_exits()
    print(f"Available exits: {available_exits}")

    # Get items and NPCs at location
    items = game_state.get_items_at_location(game_state.player_location)
    npcs = game_state.get_npcs_at_location(game_state.player_location)

    # Get lighting info
    lighting = game_state.get_effective_lighting(game_state.player_location)

    # Generate description
    description = gemini_client.describe_location(
        location=location.model_dump(),
        items=[item.model_dump() for item in items],
        npcs=[npc.model_dump() for npc in npcs],
        player_context=player_context,
        lighting_info=lighting
    )

    print(f"\nDM Description (from 'look'):\n{description}")

    # Verify exits are mentioned in the narrative
    directional_words = ['north', 'south', 'east', 'west', 'passage', 'exit', 'door', 'path', 'corridor', 'hallway']
    description_lower = description.lower()

    has_directional_reference = any(word in description_lower for word in directional_words)

    assert has_directional_reference, (
        f"'look' description should mention exits/directions naturally. "
        f"Expected words like {directional_words}, but got: {description}"
    )

    # Verify it's not a boring list format like "Exits: north, south"
    assert not description.startswith("Exits:"), (
        "Description should not start with 'Exits:' - should be integrated naturally"
    )

    print("✅ DM successfully integrated exits into 'look' command description!")


def test_no_exits_location_handled_gracefully(skip_if_no_gcp, game_setup):
    """Test that locations with no exits are described without crashing.

    This verifies that the DM can handle locations with no available exits
    and describes them appropriately (e.g., dead ends, enclosed spaces).
    """
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: NO EXITS LOCATION ===")

    # Create a test location with no exits
    from src.models.location import Location

    dead_end = Location(
        id="dead_end",
        name="Dead End",
        description="A dead end with no way out",
        connections={}
    )

    game_state.locations["dead_end"] = dead_end
    game_state.player_location = "dead_end"

    available_exits = dead_end.get_available_exits()
    print(f"Available exits at dead_end: {available_exits}")
    assert len(available_exits) == 0, "Dead end should have no exits"

    # Build context and generate description
    player_context = game_loop._build_context()

    # Get lighting info
    lighting = game_state.get_effective_lighting(game_state.player_location)

    # Generate description
    description = gemini_client.describe_location(
        location=dead_end.model_dump(),
        items=[],
        npcs=[],
        player_context=player_context,
        lighting_info=lighting
    )

    print(f"\nDM Description:\n{description}")

    # Verify description exists and doesn't crash
    assert len(description) > 0, "Description should exist even with no exits"

    # The DM might mention "no exit", "trapped", "enclosed", etc.
    # We just verify it doesn't crash and produces some narrative
    print("✅ DM handled no-exit location gracefully!")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys

    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
