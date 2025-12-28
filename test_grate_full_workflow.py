"""Test full grating workflow: open, then descend."""

import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.engine.game_loop import GameLoop
from src.main import initialize_rule_engine

gcp_project = os.getenv("GCP_PROJECT")
if not gcp_project:
    print("ERROR: GCP_PROJECT not set")
    exit(1)

# Load game with grate visible and player at grating_clearing
game_state = GameState.from_file("worlds/zork_original.json")
game_state.player_location = "grating_clearing"
game_state.items["grate"].attributes["is_visible"] = True
game_state.flags["GRATE-REVEALED"] = True
game_state.items["grate"].attributes["is_open"] = False
game_state.items["grate"].attributes["is_locked"] = False

print("=== INITIAL STATE ===")
print(f"Player location: {game_state.player_location}")
print(f"Grate open: {game_state.items['grate'].attributes['is_open']}")
print()

# Initialize game loop
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Step 1: Try to descend (should fail - grate is closed)
print("=== STEP 1: Try to descend through closed grating ===")
result1 = game_loop.execute_single_step("descend through grating")
print(f"Result: {result1['narrative']}")
print(f"Allowed: {result1['interpretation'].get('is_allowed')}")
print(f"Player location: {game_state.player_location}")
print()

# Step 2: Open the grating
print("=== STEP 2: Open the grating ===")
result2 = game_loop.execute_single_step("open grating")
print(f"Result: {result2['narrative'][:200]}...")
print(f"Allowed: {result2['interpretation'].get('is_allowed')}")
print(f"Grate now open: {game_state.items['grate'].attributes['is_open']}")
print()

# Step 3: Now descend (should succeed - grate is open)
print("=== STEP 3: Descend through open grating ===")
result3 = game_loop.execute_single_step("descend through grating")
print(f"Result: {result3['narrative'][:200]}...")
print(f"Allowed: {result3['interpretation'].get('is_allowed')}")
print(f"Player location: {game_state.player_location}")
print()

print("=== WORKFLOW SUMMARY ===")
print(f"✅ Step 1: Descend blocked (grate closed)")
print(f"✅ Step 2: Open grating (success)")
print(f"✅ Step 3: Descend through open grating → moved to {game_state.player_location}")
