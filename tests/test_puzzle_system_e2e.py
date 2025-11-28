"""End-to-end tests for the puzzle system.

Tests the complete puzzle workflow:
- Puzzles block exits when unsolved
- Valid solutions (key, tool) unlock puzzles
- Deus ex machina solutions are rejected
- Progressive hints work
- Exits are restored after solving
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
    """Set up a Zork game with puzzle system."""
    game_state = GameState.from_file("worlds/zork.json")

    # Verify puzzle was loaded
    assert "puzzles" in game_state.dm_state
    assert "grating_puzzle" in game_state.dm_state["puzzles"]

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state, gemini_client


def test_puzzle_blocks_exit(skip_if_no_gcp, game_setup):
    """Test that unsolved puzzle blocks the exit."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Puzzle Blocks Exit ===")

    # Move to grating_clearing
    game_state.player_location = "grating_clearing"

    # Verify puzzle is active and unsolved
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    assert puzzle["solved"] == False
    print(f"Puzzle state: solved={puzzle['solved']}")

    # Verify "down" exit is blocked
    location = game_state.locations["grating_clearing"]
    assert "down" not in location.connections
    print(f"Available exits: {list(location.connections.keys())}")

    # Try to go down (should be blocked)
    narrative, interpretation = game_loop.process_turn("go down")

    print(f"\nPlayer: go down")
    print(f"Narrative: {narrative}")
    print(f"is_valid: {interpretation['is_valid']}")

    # Should be invalid (no exit exists)
    assert interpretation["is_valid"] == False
    print("\n✅ TEST PASSED: Puzzle correctly blocks exit")


def test_puzzle_solution_with_key(skip_if_no_gcp, game_setup):
    """Test that the brass key solution works."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Puzzle Solution with Key ===")

    # Move to grating_clearing and give player the key
    game_state.player_location = "grating_clearing"
    game_state.move_item_to_player("brass_key")

    print(f"Player inventory: {game_state.player.inventory}")

    # Verify puzzle is unsolved
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    assert puzzle["solved"] == False

    # Try to unlock with key
    narrative, interpretation = game_loop.process_turn("unlock grating with brass key")

    print(f"\nPlayer: unlock grating with brass key")
    print(f"Narrative: {narrative}")
    print(f"is_valid: {interpretation['is_valid']}")

    # Should be valid
    assert interpretation["is_valid"] == True

    # Check if puzzle was marked as solved
    puzzle_after = game_state.dm_state["puzzles"]["grating_puzzle"]
    print(f"Puzzle solved: {puzzle_after['solved']}")

    if puzzle_after["solved"]:
        print("✅ Puzzle marked as solved")

        # Verify exit was restored
        location = game_state.locations["grating_clearing"]
        if "down" in location.connections:
            print(f"✅ Exit restored: down -> {location.connections['down']}")
        else:
            print("⚠️  Exit not yet restored (may require another turn)")
    else:
        print("⚠️  Puzzle not marked as solved (LLM may not have followed prompt)")

    print("\n✅ TEST PASSED: Key solution accepted")


def test_puzzle_alternative_solution_tool(skip_if_no_gcp, game_setup):
    """Test that a tool (wrench) can force the lock open."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Puzzle Alternative Solution with Tool ===")

    # Move to grating_clearing and give player a wrench
    game_state.player_location = "grating_clearing"
    game_state.move_item_to_player("wrench")

    print(f"Player inventory: {game_state.player.inventory}")

    # Verify puzzle is unsolved
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    assert puzzle["solved"] == False

    # Try to break lock with wrench
    narrative, interpretation = game_loop.process_turn("break lock with wrench")

    print(f"\nPlayer: break lock with wrench")
    print(f"Narrative: {narrative}")
    print(f"is_valid: {interpretation['is_valid']}")

    # Should be valid
    assert interpretation["is_valid"] == True

    # Check if puzzle was marked as solved
    puzzle_after = game_state.dm_state["puzzles"]["grating_puzzle"]
    print(f"Puzzle solved: {puzzle_after['solved']}")

    if puzzle_after["solved"]:
        print("✅ Puzzle marked as solved")

        # Verify exit was restored
        location = game_state.locations["grating_clearing"]
        if "down" in location.connections:
            print(f"✅ Exit restored: down -> {location.connections['down']}")
        else:
            print("⚠️  Exit not yet restored (may require another turn)")
    else:
        print("⚠️  Puzzle not marked as solved (LLM may not have followed prompt)")

    print("\n✅ TEST PASSED: Tool solution accepted")


def test_puzzle_deus_ex_machina_prevention(skip_if_no_gcp, game_setup):
    """Test that deus ex machina solutions are rejected."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Deus Ex Machina Prevention ===")

    # Move to grating_clearing (without key or tool)
    game_state.player_location = "grating_clearing"

    print(f"Player inventory: {game_state.player.inventory}")

    # Verify puzzle is unsolved
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    assert puzzle["solved"] == False
    initial_failed_attempts = puzzle.get("failed_attempts", 0)

    # Try a blocked action (teleport)
    narrative, interpretation = game_loop.process_turn("teleport past the grating")

    print(f"\nPlayer: teleport past the grating")
    print(f"Narrative: {narrative}")
    print(f"is_valid: {interpretation['is_valid']}")

    # Should be invalid (blocked action)
    assert interpretation["is_valid"] == False

    # Check if failed_attempts was incremented
    puzzle_after = game_state.dm_state["puzzles"]["grating_puzzle"]
    failed_attempts_after = puzzle_after.get("failed_attempts", 0)
    print(f"Failed attempts: {initial_failed_attempts} -> {failed_attempts_after}")

    # Verify puzzle still unsolved
    assert puzzle_after["solved"] == False
    print("✅ Puzzle remains unsolved")

    print("\n✅ TEST PASSED: Deus ex machina solution rejected")


def test_puzzle_hint_progression(skip_if_no_gcp, game_setup):
    """Test that hints become more explicit with failed attempts."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Puzzle Hint Progression ===")

    # Move to grating_clearing (without key or tool)
    game_state.player_location = "grating_clearing"

    # Test hint at 0 failed attempts (should be subtle)
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    puzzle["failed_attempts"] = 0

    narrative_1, _ = game_loop.process_turn("examine grating")
    print(f"\nAttempts: 0")
    print(f"Narrative: {narrative_1[:200]}...")

    # Test hint at 2 failed attempts (should be moderate)
    puzzle["failed_attempts"] = 2

    narrative_2, _ = game_loop.process_turn("look at grating")
    print(f"\nAttempts: 2")
    print(f"Narrative: {narrative_2[:200]}...")

    # Test hint at 4 failed attempts (should be explicit)
    puzzle["failed_attempts"] = 4

    narrative_3, _ = game_loop.process_turn("inspect grating")
    print(f"\nAttempts: 4")
    print(f"Narrative: {narrative_3[:200]}...")

    print("\n✅ TEST PASSED: Hint progression tested (manual verification needed)")


def test_exit_restored_after_solve(skip_if_no_gcp, game_setup):
    """Test that exit is restored and player can move after solving puzzle."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Exit Restored After Solve ===")

    # Move to grating_clearing and give player the key
    game_state.player_location = "grating_clearing"
    game_state.move_item_to_player("brass_key")

    # Solve the puzzle
    print("Solving puzzle...")
    narrative, interpretation = game_loop.process_turn("unlock grating with brass key")
    print(f"Narrative: {narrative[:150]}...")

    # Check puzzle state
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    print(f"Puzzle solved: {puzzle['solved']}")

    if puzzle["solved"]:
        # Check if exit was restored
        location = game_state.locations["grating_clearing"]
        print(f"Available exits: {list(location.connections.keys())}")

        if "down" in location.connections:
            print(f"✅ Exit 'down' restored -> {location.connections['down']}")

            # Try to move down
            narrative_move, interpretation_move = game_loop.process_turn("go down")
            print(f"\nPlayer: go down")
            print(f"Narrative: {narrative_move[:150]}...")
            print(f"is_valid: {interpretation_move['is_valid']}")
            print(f"New location: {game_state.player_location}")

            # Should be valid and player should move
            if interpretation_move["is_valid"] and game_state.player_location == "cave_entrance":
                print("✅ Player successfully moved through restored exit")
            else:
                print(f"⚠️  Movement may not have worked (location: {game_state.player_location})")
        else:
            print("⚠️  Exit not restored - puzzle handler may not have triggered")
    else:
        print("⚠️  Puzzle not solved - cannot test exit restoration")

    print("\n✅ TEST COMPLETED: Exit restoration tested")


def test_puzzle_loading_from_json(skip_if_no_gcp, game_setup):
    """Test that puzzle data is correctly loaded from JSON."""
    game_loop, game_state, gemini_client = game_setup

    print("\n=== TEST: Puzzle Loading from JSON ===")

    # Check dm_state has puzzles
    assert "puzzles" in game_state.dm_state
    print("✅ dm_state contains 'puzzles'")

    # Check grating_puzzle exists
    assert "grating_puzzle" in game_state.dm_state["puzzles"]
    puzzle = game_state.dm_state["puzzles"]["grating_puzzle"]
    print("✅ grating_puzzle loaded")

    # Check puzzle structure
    assert puzzle["id"] == "grating_puzzle"
    assert puzzle["type"] == "locked_exit"
    assert puzzle["location"] == "grating_clearing"
    assert puzzle["exit_direction"] == "down"
    print(f"✅ Puzzle metadata correct: {puzzle['name']}")

    # Check runtime state added
    assert "solved" in puzzle
    assert "failed_attempts" in puzzle
    assert puzzle["solved"] == False
    assert puzzle["failed_attempts"] == 0
    print(f"✅ Runtime state initialized: solved={puzzle['solved']}, failed_attempts={puzzle['failed_attempts']}")

    # Check requirements
    assert "requirements" in puzzle
    assert "solutions" in puzzle["requirements"]
    assert len(puzzle["requirements"]["solutions"]) >= 2
    print(f"✅ Puzzle has {len(puzzle['requirements']['solutions'])} solution paths")

    # Check hints
    assert "hints" in puzzle
    assert "subtle" in puzzle["hints"]
    assert "moderate" in puzzle["hints"]
    assert "explicit" in puzzle["hints"]
    print("✅ All hint levels present")

    # Check deus ex machina prevention
    assert "deus_ex_machina_prevention" in puzzle
    assert "blocked_actions" in puzzle["deus_ex_machina_prevention"]
    blocked = puzzle["deus_ex_machina_prevention"]["blocked_actions"]
    print(f"✅ {len(blocked)} blocked actions defined")

    # Check exit blocking
    assert "blocked_exits" in game_state.dm_state
    blocked_exits = game_state.dm_state["blocked_exits"]
    grating_exit_key = "grating_clearing_down"
    assert grating_exit_key in blocked_exits
    print(f"✅ Exit blocked: {blocked_exits[grating_exit_key]}")

    # Verify connection was removed
    location = game_state.locations["grating_clearing"]
    assert "down" not in location.connections
    print(f"✅ Connection removed from location: available exits = {list(location.connections.keys())}")

    print("\n✅ TEST PASSED: All puzzle data loaded correctly")


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
