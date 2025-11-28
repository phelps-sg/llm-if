"""E2E test for time tracking and advancement system."""

import pytest
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def game_with_time_tracking():
    """Setup game with fresh time tracking."""
    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Set initial time explicitly
    game_state.game_time = "Day 1, Morning, 8:00 AM"
    game_state.player_location = "entrance"
    game_state.turn_count = 0

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state


def test_time_advances_after_action(game_with_time_tracking):
    """Test that time advances when player takes an action."""
    game_loop, game_state = game_with_time_tracking

    initial_time = game_state.game_time
    print(f"\nInitial time: {initial_time}")

    # Take a simple action
    narrative, interpretation = game_loop.process_turn("look around")

    # Time should have changed
    new_time = game_state.game_time
    print(f"Time after action: {new_time}")

    assert new_time != initial_time, \
        f"Time should have advanced but stayed at: {initial_time}"

    # The interpretation should include time information
    assert "new_time" in interpretation or interpretation.get("new_time") is not None, \
        "LLM should provide new_time in interpretation"


def test_time_advances_on_movement(game_with_time_tracking):
    """Test that time advances when player moves between locations."""
    game_loop, game_state = game_with_time_tracking

    initial_time = game_state.game_time

    # Move to a connected location
    narrative, interpretation = game_loop.process_turn("go north")

    new_time = game_state.game_time

    assert new_time != initial_time, \
        f"Time should advance during movement. Was: {initial_time}, Now: {new_time}"


def test_time_format_is_natural_language(game_with_time_tracking):
    """Test that time is stored in natural language format."""
    game_loop, game_state = game_with_time_tracking

    # Execute an action
    narrative, interpretation = game_loop.process_turn("examine the walls")

    # Time should be a string (natural language)
    assert isinstance(game_state.game_time, str), \
        f"Time should be string, got: {type(game_state.game_time)}"

    # Should contain some time-related words
    time_lower = game_state.game_time.lower()
    has_time_keywords = any(keyword in time_lower for keyword in [
        "day", "morning", "afternoon", "evening", "night",
        "am", "pm", "hour", "minute"
    ])

    assert has_time_keywords, \
        f"Time should contain time-related keywords: {game_state.game_time}"


def test_multiple_actions_advance_time(game_with_time_tracking):
    """Test that time continues to advance over multiple actions."""
    game_loop, game_state = game_with_time_tracking

    times = [game_state.game_time]

    # Execute several actions
    actions = [
        "look around",
        "examine the floor",
        "check inventory"
    ]

    for action in actions:
        game_loop.process_turn(action)
        times.append(game_state.game_time)

    print("\nTime progression:")
    for i, time in enumerate(times):
        print(f"  Step {i}: {time}")

    # At least some times should be different (time is advancing)
    unique_times = set(times)
    assert len(unique_times) > 1, \
        f"Time should advance across actions, but got same time {len(times)} times: {times[0]}"


def test_time_context_passed_to_llm(game_with_time_tracking):
    """Test that current time is available to the LLM for decision making."""
    game_loop, game_state = game_with_time_tracking

    # Set a specific time
    game_state.game_time = "Day 1, Midnight, 12:00 AM"

    # The LLM should receive current time and make time-aware decisions
    narrative, interpretation = game_loop.process_turn("wait for dawn")

    # After waiting for dawn, time should reflect morning/dawn
    new_time = game_state.game_time.lower()

    # Should have advanced significantly (if LLM understood the context)
    assert new_time != "day 1, midnight, 12:00 am", \
        "Time should have advanced after waiting"
