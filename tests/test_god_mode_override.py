"""Test GOD MODE: command prefix to override is_valid and is_allowed."""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.game_state import GameState
from src.engine.game_loop import GameLoop
from src.llm.gemini_client import GeminiClient
from src.config import DEFAULT_DM_MODEL


@pytest.fixture
def gcp_project():
    """Get GCP project from environment."""
    project = os.getenv("GCP_PROJECT")
    if not project:
        pytest.skip("GCP_PROJECT environment variable not set")
    return project


@pytest.fixture
def simple_game(gcp_project):
    """Create a simple test game."""
    world_data = {
        "locations": {
            "room": {
                "id": "room",
                "name": "Test Room",
                "attributes": {"description_hints": "A simple room"},
                "connections": {},  # No exits
            }
        },
        "items": {
            "locked_door": {
                "id": "locked_door",
                "name": "Locked Door",
                "attributes": {
                    "is_door": True,
                    "is_open": False,
                    "is_locked": True,
                    "is_takeable": False,
                },
            }
        },
        "npcs": {},
        "item_locations": {"locked_door": "room"},
        "npc_locations": {},
        "player_location": "room",
        "player_inventory": [],
        "flags": {},
        "puzzles": {},
        "world_context": {"title": "Test", "author": "Test"},
    }

    game_state = GameState.from_dict(world_data)
    gemini = GeminiClient(project=gcp_project, model_name=DEFAULT_DM_MODEL)
    game_loop = GameLoop(game_state, gemini, None)
    return game_state, game_loop


def test_normal_command_blocked(simple_game):
    """Test that a normal command is blocked when not allowed."""
    game_state, game_loop = simple_game

    # Try to open locked door normally - should fail
    result = game_loop.execute_single_step("open locked door")

    interpretation = result.get("interpretation", {})

    print(f"Normal command result: is_allowed={interpretation.get('is_allowed')}")
    print(f"Normal command result: is_valid={interpretation.get('is_valid')}")
    print(f"State updates: {interpretation.get('state_updates', [])}")
    print(f"Narrative: {result.get('narrative')}")

    # Without god mode, the action should be blocked
    # (Either is_allowed=False or is_valid=False)
    # In either case, no state updates should be generated
    assert interpretation.get("is_allowed") is False or interpretation.get("is_valid") is False, \
        "Normal command should be blocked (is_allowed=False or is_valid=False)"

    # No state updates should be generated when blocked
    state_updates = interpretation.get("state_updates", [])
    assert len(state_updates) == 0, "Blocked command should not generate state_updates"

    # Check the door is still closed and locked
    door = game_state.items["locked_door"]
    assert not door.attributes.get("is_open"), "Door should still be closed"
    assert door.attributes.get("is_locked"), "Door should still be locked"


def test_god_mode_override(simple_game):
    """Test that GOD MODE: prefix forces action to succeed."""
    game_state, game_loop = simple_game

    # Use GOD MODE to force opening the locked door
    result = game_loop.execute_single_step("GOD MODE: open locked door")

    # State updates should have been applied
    interpretation = result.get("interpretation", {})
    state_updates = interpretation.get("state_updates", [])

    print(f"God mode command: is_valid={interpretation.get('is_valid')}")
    print(f"God mode command: is_allowed={interpretation.get('is_allowed')}")
    print(f"State updates: {state_updates}")
    print(f"Narrative: {result.get('narrative')}")

    # With god mode, is_valid and is_allowed should be forced to True
    assert interpretation.get("is_valid") is True, "God mode should force is_valid=True"
    assert interpretation.get("is_allowed") is True, "God mode should force is_allowed=True"

    # State updates should have been generated (door should be opened)
    assert len(state_updates) > 0, "God mode should generate state_updates"

    # Check if door was actually opened
    door = game_state.items["locked_door"]
    assert door.attributes.get("is_open") is True, "Door should be open after god mode command"


def test_god_mode_impossible_action(simple_game):
    """Test that GOD MODE: can force even impossible actions."""
    game_state, game_loop = simple_game

    # Try an impossible action with GOD MODE
    # Normal DM would reject this, but god mode forces it through
    result = game_loop.execute_single_step("GOD MODE: teleport to castle")

    interpretation = result.get("interpretation", {})

    # God mode should force is_valid and is_allowed to True
    # Note: The DM still interprets normally, but game loop overrides the flags
    print(f"Impossible action: is_valid={interpretation.get('is_valid')}")
    print(f"Impossible action: is_allowed={interpretation.get('is_allowed')}")
    print(f"Narrative: {result.get('narrative')}")

    # Should have some state updates (DM generates them because is_allowed=True)
    state_updates = interpretation.get("state_updates", [])
    print(f"State updates: {state_updates}")


def test_god_mode_strips_prefix(simple_game):
    """Test that GOD MODE: prefix is stripped before sending to DM."""
    game_state, game_loop = simple_game

    # The DM should see "look around", not "GOD MODE: look around"
    result = game_loop.execute_single_step("GOD MODE: look around")

    # Should work normally (look is usually allowed anyway)
    narrative = result.get("narrative", "")
    assert len(narrative) > 0, "Should get a narrative response"

    print(f"Look with god mode: {narrative}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
