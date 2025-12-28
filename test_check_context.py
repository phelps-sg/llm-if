"""Check what context the LLM actually sees."""

import os
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.engine.game_loop import GameLoop
from src.main import initialize_rule_engine
from unittest.mock import patch

gcp_project = os.getenv("GCP_PROJECT")
if not gcp_project:
    print("ERROR: GCP_PROJECT not set")
    exit(1)

# Load game with GRATE OPEN
game_state = GameState.from_file("worlds/zork_original.json")
game_state.player_location = "grating_clearing"
game_state.items["grate"].attributes["is_visible"] = True
game_state.flags["GRATE-REVEALED"] = True
game_state.items["grate"].attributes["is_open"] = True  # OPEN!
game_state.items["grate"].attributes["is_locked"] = False

print("=== GAME STATE ===")
print(f"Grate is_open: {game_state.items['grate'].attributes['is_open']}")
print()

# Initialize
gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
rule_engine = initialize_rule_engine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=zil_translator)

# Intercept interpret_intent to see what context it receives
captured_context = {}

original_interpret = gemini.interpret_intent
def capture_intent(player_input, context):
    captured_context['context'] = context
    return original_interpret(player_input, context)

with patch.object(gemini, 'interpret_intent', side_effect=capture_intent):
    result = game_loop.execute_single_step("descend through the grating")

print("=== CONTEXT PASSED TO INTERPRET_INTENT ===")
items = captured_context['context'].get('items', [])
for item in items:
    if 'grat' in item.get('name', '').lower():
        print(f"Item: {item.get('name')}")
        print(f"  ID: {item.get('id')}")
        print(f"  is_open: {item.get('attributes', {}).get('is_open')}")
        print(f"  is_locked: {item.get('attributes', {}).get('is_locked')}")
        print(f"  is_door: {item.get('attributes', {}).get('is_door')}")
        print()

print("=== RESULT ===")
print(f"Is allowed: {result['interpretation'].get('is_allowed')}")
print(f"Message: {result['narrative']}")
