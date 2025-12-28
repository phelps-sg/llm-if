#!/usr/bin/env python3
"""Debug what prompt the LLM receives for deck_nine description."""

import sys
import logging
sys.path.insert(0, '/Users/Steve.Phelps/vcs/coding/llm-if')

# Set up logging to see the actual prompt
logging.basicConfig(level=logging.DEBUG)

from src.models.game_state import GameState
from src.engine.game_loop import GameLoop
from src.llm.gemini_client import GeminiClient
from src.llm.zil_translator import ensure_zil_translations
from src.rules.rule_engine import RuleEngine

# Load game state
game_state = GameState.from_file("worlds/planetfall.json")

# Ensure player is at deck_nine
game_state.player_location = "deck_nine"

# Set up clients
gemini = GeminiClient(model="gemini-2.0-flash-exp")
rule_engine = RuleEngine()
game_loop = GameLoop(game_state, gemini, rule_engine, zil_translator_client=gemini)

# Get location, items, NPCs
location = game_state.get_player_location()
items_at_location = game_state.get_items_at_location("deck_nine")
npcs_at_location = game_state.get_npcs_at_location("deck_nine")

# Add global objects (same as game loop does)
if location and 'zil_global_objects' in location.attributes:
    global_obj_ids = location.attributes['zil_global_objects']
    for obj_id in global_obj_ids:
        if obj_id in game_state.items and obj_id not in [item.id for item in items_at_location]:
            items_at_location.append(game_state.items[obj_id])

# Apply ZIL translations
location_dict, items_dicts, npcs_dicts = ensure_zil_translations(
    gemini,
    location=location,
    items=items_at_location,
    npcs=npcs_at_location
)

print("=" * 80)
print("ITEMS BEING PASSED TO LLM:")
print("=" * 80)
for item in items_dicts:
    if 'door' in item['id']:
        print(f"\n{item['id']}:")
        print(f"  name: {item['name']}")
        print(f"  is_open: {item.get('attributes', {}).get('is_open')}")
        print(f"  is_visible: {item.get('attributes', {}).get('is_visible')}")
        print(f"  zil_flags: {item.get('attributes', {}).get('zil_flags')}")

print("\n" + "=" * 80)
print("LOCATION ZIL ACTION DESCRIPTION:")
print("=" * 80)
zil_desc = location_dict.get('attributes', {}).get('zil_action_description')
if zil_desc:
    print(zil_desc)
else:
    print("NO ZIL ACTION DESCRIPTION FOUND!")

print("\n" + "=" * 80)
print("Building prompt to see what LLM receives...")
print("=" * 80)

# Build the actual prompt
lighting_info = game_state.get_effective_lighting("deck_nine")
player_context = {
    "game_time": game_state.game_time,
    "inventory_items": [game_state.items[iid].name for iid in game_state.player.inventory if iid in game_state.items],
    "attributes": game_state.player.attributes
}

prompt = gemini._build_location_prompt(
    location_dict,
    items_dicts,
    npcs_dicts,
    player_context,
    game_state.world_context,
    lighting_info,
    cached_descriptions=None,
    global_flags=game_state.flags
)

# Print relevant sections of the prompt
print("\n" + "=" * 80)
print("ITEMS SECTION IN PROMPT:")
print("=" * 80)
lines = prompt.split('\n')
in_items_section = False
for i, line in enumerate(lines):
    if 'ITEMS CURRENTLY AT THIS LOCATION' in line:
        in_items_section = True
    if in_items_section:
        print(line)
        if line.strip() == "" and i > 0 and lines[i-1].strip().startswith("Attributes:"):
            break

print("\n" + "=" * 80)
print("ZIL SPECIAL BEHAVIOR SECTION IN PROMPT:")
print("=" * 80)
in_zil_section = False
for line in lines:
    if 'LOCATION SPECIAL BEHAVIOR' in line or 'Special Behavior' in line:
        in_zil_section = True
    if in_zil_section:
        print(line)
        if line.strip() == "=" * 80:
            break
