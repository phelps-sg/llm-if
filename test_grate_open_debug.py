"""Debug grating opening state updates."""

import os
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.engine.game_loop import GameLoop
from src.main import initialize_rule_engine

gcp_project = os.getenv("GCP_PROJECT")
if not gcp_project:
    print("ERROR: GCP_PROJECT not set")
    exit(1)

# Load game
game_state = GameState.from_file("worlds/zork_original.json")
game_state.player_location = "grating_clearing"
game_state.items["grate"].attributes["is_visible"] = True
game_state.flags["GRATE-REVEALED"] = True
game_state.items["grate"].attributes["is_open"] = False
game_state.items["grate"].attributes["is_locked"] = False

print("=== BEFORE OPEN ===")
print(f"Grate attributes: {json.dumps(game_state.items['grate'].attributes, indent=2)}")
print()

# Initialize
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Open grating
print("=== OPENING GRATING ===")
result = game_loop.execute_single_step("open grating")

print(f"Is allowed: {result['interpretation'].get('is_allowed')}")
print(f"State updates: {json.dumps(result['interpretation'].get('state_updates', []), indent=2)}")
print()

print("=== AFTER OPEN ===")
print(f"Grate attributes: {json.dumps(game_state.items['grate'].attributes, indent=2)}")
