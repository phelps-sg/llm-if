"""Simple debug to trace execution."""

import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.engine.game_loop import GameLoop
from src.main import initialize_rule_engine


def test_trace_execution():
    """Just trace what happens."""
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        return

    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "west_of_house"

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
    rule_engine = initialize_rule_engine()

    game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

    print("\n=== First: Calling process_turn('look') ===")
    narrative_from_process, interpretation = game_loop.process_turn("look")

    print(f"\nProcess_turn returned:")
    print(f"  Narrative length: {len(narrative_from_process)}")
    print(f"  Narrative: {narrative_from_process[:150]}...")
    print(f"  State updates: {interpretation.get('state_updates', [])}")
    print(f"  Number of state updates: {len(interpretation.get('state_updates', []))}")

    # Reset for next test
    game_state.player_location = "west_of_house"

    print("\n\n=== Second: Calling execute_single_step('look') ===")
    result = game_loop.execute_single_step("look")

    print(f"\n=== Result ===")
    print(f"Narrative length: {len(result.get('narrative', ''))}")
    print(f"Narrative:\n{result.get('narrative')}\n")

    # Check if the condition for calling describe_location is met
    state_updates = result['interpretation'].get('state_updates', [])
    is_look_condition = (len(state_updates) == 0 and any(word in "look".lower() for word in ["look", "examine", "l "]))
    print(f"\n=== Condition Check ===")
    print(f"State updates count: {len(state_updates)}")
    print(f"Would call describe_location? {is_look_condition}")

    # Check game state flags
    print(f"\n=== Game State ===")
    print(f"Flags: {game_state.flags}")
    print(f"Player location: {game_state.player_location}")


if __name__ == "__main__":
    test_trace_execution()
