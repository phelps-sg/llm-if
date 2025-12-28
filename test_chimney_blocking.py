"""Test for chimney blocking with "Only Santa Claus" message.

Tests that the kitchen's "down" exit is blocked with the proper message
from the original ZIL: "Only Santa Claus climbs down chimneys."
"""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


def test_chimney_blocking():
    """Test that chimney descent is blocked with Santa Claus message."""
    # Load game state
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "kitchen"

    # Add lamp to inventory and light it
    if "lamp" in game_state.items:
        game_state.player.inventory.append("lamp")
        game_state.items["lamp"].attributes["is_lit"] = True

    # Check that kitchen has blocked_exits
    kitchen = game_state.locations["kitchen"]
    assert "blocked_exits" in kitchen.attributes, "Kitchen should have blocked_exits attribute"
    assert "down" in kitchen.attributes["blocked_exits"], "Kitchen should block 'down' exit"
    assert "Santa" in kitchen.attributes["blocked_exits"]["down"], "Blocking message should mention Santa"

    print(f"\n✅ Kitchen has blocked exit: {kitchen.attributes['blocked_exits']}")

    # Now test with LLM
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT environment variable not set - can't test with LLM")

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    from src.main import initialize_rule_engine
    rule_engine = initialize_rule_engine()

    game_loop = GameLoop(game_state, gemini, rule_engine)

    # Check that blocked_exits is in context
    context = game_loop._build_context()
    print(f"\n✅ Context blocked_exits: {context.get('blocked_exits', {})}")
    assert "blocked_exits" in context, "Context should include blocked_exits"
    assert "down" in context["blocked_exits"], "Context blocked_exits should include 'down'"

    # Try to go down the chimney
    print("\n🧪 Testing: Player tries to go down chimney...")
    result = game_loop.execute_single_step("go down")

    interpretation = result.get("interpretation", {})
    narrative = result.get("narrative", "")

    print(f"\n📝 Interpretation:")
    print(f"   is_allowed: {interpretation.get('is_allowed')}")
    print(f"   not_allowed_reason: {interpretation.get('not_allowed_reason')}")
    print(f"\n📖 Narrative:\n{narrative}")

    # Should be blocked
    assert not interpretation.get("is_allowed", True), "Going down chimney should not be allowed"

    # Should mention Santa or the blocking message
    full_response = (narrative + " " + interpretation.get("not_allowed_reason", "")).lower()
    assert "santa" in full_response or "chimney" in full_response, \
        "Response should mention Santa Claus or chimneys in blocking message"

    print("\n✅ Test passed! Chimney is properly blocked.")


if __name__ == "__main__":
    test_chimney_blocking()
