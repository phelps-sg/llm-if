"""Final test of grating workflow with fixed prompts."""

import os
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

print("=== INITIAL STATE ===")
print(f"Player location: {game_state.player_location}")
print(f"Grate is_open: {game_state.items['grate'].attributes['is_open']}")
print(f"Grate is_locked: {game_state.items['grate'].attributes['is_locked']}")
print()

# Initialize
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Step 1: Try to descend (should be blocked)
print("=== TEST 1: Descend through closed grating (should fail) ===")
result1 = game_loop.execute_single_step("go down through the grating")
print(f"Allowed: {result1['interpretation'].get('is_allowed')}")
print(f"Message: {result1['narrative']}")
print(f"Player still at: {game_state.player_location}")
print()

# Step 2: Open it
print("=== TEST 2: Open the grating (should succeed) ===")
result2 = game_loop.execute_single_step("open the grating")
print(f"Allowed: {result2['interpretation'].get('is_allowed')}")
print(f"Grate is_open attribute: {game_state.items['grate'].attributes['is_open']}")
print()

#Step 3: Now descend (should work)
print("=== TEST 3: Descend through now-open grating (should succeed) ===")
result3 = game_loop.execute_single_step("go down through the grating")
print(f"Allowed: {result3['interpretation'].get('is_allowed')}")
print(f"Player moved to: {game_state.player_location}")
print()

print("=== SUMMARY ===")
if result1['interpretation'].get('is_allowed') == False:
    print("✅ Test 1 PASSED: Blocked from descending through closed grating")
else:
    print("❌ Test 1 FAILED: Should have been blocked")

if game_state.items['grate'].attributes['is_open'] == True:
    print("✅ Test 2 PASSED: Grating opened successfully")
else:
    print("❌ Test 2 FAILED: Grating should be open")

if game_state.player_location == "grating_room":
    print("✅ Test 3 PASSED: Player moved to grating_room")
else:
    print(f"❌ Test 3 FAILED: Player at {game_state.player_location}, should be at grating_room")
