"""Debug Test 3 - why is descent blocked when grating is open?"""

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

# Load game with GRATE ALREADY OPEN
game_state = GameState.from_file("worlds/zork_original.json")
game_state.player_location = "grating_clearing"
game_state.items["grate"].attributes["is_visible"] = True
game_state.flags["GRATE-REVEALED"] = True
game_state.items["grate"].attributes["is_open"] = True  # OPEN!
game_state.items["grate"].attributes["is_locked"] = False

print("=== BEFORE DESCENT ===")
print(f"Player location: {game_state.player_location}")
print(f"Grate is_open: {game_state.items['grate'].attributes['is_open']}")
print()

# Initialize
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Try to descend
print("=== DESCENDING THROUGH OPEN GRATING ===")
result = game_loop.execute_single_step("descend through the grating")

print(f"Is allowed: {result['interpretation'].get('is_allowed')}")
print(f"Is valid: {result['interpretation'].get('is_valid')}")
print(f"Not allowed reason: {result['interpretation'].get('not_allowed_reason')}")
print(f"Invalid reason: {result['interpretation'].get('invalid_reason')}")
print(f"Narrative: {result['narrative']}")
print()

print("=== AFTER DESCENT ===")
print(f"Player location: {game_state.player_location}")
print(f"Expected: grating_room")
print()

if game_state.player_location == "grating_room":
    print("✅ SUCCESS: Player descended")
else:
    print(f"❌ FAIL: Player at {game_state.player_location}")
    print(f"State updates: {json.dumps(result['interpretation'].get('state_updates', []), indent=2)}")
