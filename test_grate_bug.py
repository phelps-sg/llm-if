"""Diagnostic script for grate descending bug."""

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

# Make grate visible (simulate "disturb leaves" already done)
game_state.items["grate"].attributes["is_visible"] = True
game_state.flags["GRATE-REVEALED"] = True

# Ensure grate is CLOSED (this is the key!)
game_state.items["grate"].attributes["is_open"] = False
game_state.items["grate"].attributes["is_locked"] = False

print("=== INITIAL STATE ===")
print(f"Player location: {game_state.player_location}")
print(f"Grate visible: {game_state.items['grate'].attributes['is_visible']}")
print(f"Grate open: {game_state.items['grate'].attributes['is_open']}")
print(f"Grate locked: {game_state.items['grate'].attributes['is_locked']}")
print()

# Initialize game loop
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Try to descend through the CLOSED grate
print("=== EXECUTING: descend through grating ===\n")
result = game_loop.execute_single_step("descend through grating")

print("=== RESULT ===")
print(f"Narrative: {result['narrative']}\n")

interpretation = result.get("interpretation", {})
print(f"Intent: {interpretation.get('intent')}")
print(f"Is valid: {interpretation.get('is_valid')}")
print(f"Is allowed: {interpretation.get('is_allowed')}")
print(f"Invalid reason: {interpretation.get('invalid_reason')}")
print(f"Not allowed reason: {interpretation.get('not_allowed_reason')}")
print()

print("=== STATE UPDATES ===")
state_updates = interpretation.get("state_updates", [])
for i, update in enumerate(state_updates, 1):
    print(f"{i}. {update}")
print()

print("=== FINAL STATE ===")
print(f"Player location: {game_state.player_location}")
print(f"Grate open: {game_state.items['grate'].attributes['is_open']}")
print(f"Grate locked: {game_state.items['grate'].attributes.get('is_locked', 'N/A')}")
print()

# The bug is:
# 1. LLM should reject the action (grate is closed)
# 2. LLM should NOT auto-open the grate
# 3. Player should NOT move locations

print("=== BUG ANALYSIS ===")
has_move = any(u.get('type') == 'move_player' for u in state_updates)
has_open = any(
    u.get('type') == 'modify_attribute' and
    u.get('params', {}).get('entity_id') == 'grate' and
    u.get('params', {}).get('attribute_path') == 'open'
    for u in state_updates
)

print(f"Player moved: {has_move}")
print(f"Grate auto-opened: {has_open}")
print()

if has_open:
    print("🐛 BUG CONFIRMED: LLM auto-opened the grate!")
    print("   Expected: Reject action with 'The grating is closed'")
    print("   Actual: Generated state_update to open the grate")

if not has_move and game_state.player_location == "grating_clearing":
    print("🐛 BUG CONFIRMED: Player didn't move!")
    print("   Expected: Player moves to 'grating_room'")
    print(f"   Actual: Player still at '{game_state.player_location}'")
