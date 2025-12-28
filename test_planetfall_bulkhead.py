#!/usr/bin/env python3
"""Test to debug bulkhead door state in Planetfall."""

import json
import sys
sys.path.insert(0, '/Users/Steve.Phelps/vcs/coding/llm-if')

from src.models.game_state import GameState

# Load Planetfall
game_state = GameState.from_file("worlds/planetfall.json")

# Move player to deck_nine if not already there
if game_state.player_location != "deck_nine":
    print("Moving player to deck_nine...")
    game_state.player_location = "deck_nine"

# Get items at location like game loop does
location = game_state.get_player_location()
items_at_location = game_state.get_items_at_location(game_state.player_location)

# Add global objects from location's zil_global_objects to items list (same as game loop)
if location and 'zil_global_objects' in location.attributes:
    global_obj_ids = location.attributes['zil_global_objects']
    for obj_id in global_obj_ids:
        if obj_id in game_state.items and obj_id not in [item.id for item in items_at_location]:
            items_at_location.append(game_state.items[obj_id])

print("=" * 80)
print("DECK NINE CONTEXT INSPECTION")
print("=" * 80)

# Check location
print("\n📍 LOCATION:")
print(f"  ID: {location.id}")
print(f"  Name: {location.name}")

# Check if global objects are in the items list
print("\n🔧 GLOBAL OBJECTS IN LOCATION:")
if 'zil_global_objects' in location.attributes:
    global_objs = location.attributes['zil_global_objects']
    print(f"  ZIL global objects: {global_objs}")

# Check items in context
print("\n📦 ITEMS AT LOCATION (after adding global objects):")
for item in items_at_location:
    if 'door' in item.id or 'bulkhead' in item.name.lower():
        print(f"\n  🚪 {item.id}:")
        print(f"     Name: {item.name}")
        print(f"     is_open: {item.attributes.get('is_open', 'NOT SET')}")
        print(f"     is_visible: {item.attributes.get('is_visible', 'NOT SET')}")
        print(f"     is_locked: {item.attributes.get('is_locked', 'NOT SET')}")
        print(f"     zil_flags: {item.attributes.get('zil_flags', [])}")

# Check if corridor_door and gangway_door are in items
item_ids = [item.id for item in items_at_location]
print(f"\n  All item IDs at location: {item_ids}")
print(f"\n  ✓ corridor_door in items: {'corridor_door' in item_ids}")
print(f"  ✓ gangway_door in items: {'gangway_door' in item_ids}")

# Check the actual item objects in game state
print("\n🗃️  ACTUAL ITEM STATE IN GAME:")
if 'corridor_door' in game_state.items:
    door = game_state.items['corridor_door']
    print(f"\n  corridor_door:")
    print(f"    is_open: {door.attributes.get('is_open')}")
    print(f"    is_visible: {door.attributes.get('is_visible')}")
    print(f"    location_id: {door.location_id}")

if 'gangway_door' in game_state.items:
    door = game_state.items['gangway_door']
    print(f"\n  gangway_door:")
    print(f"    is_open: {door.attributes.get('is_open')}")
    print(f"    is_visible: {door.attributes.get('is_visible')}")
    print(f"    location_id: {door.location_id}")

# Check ZIL action code
print("\n📜 ZIL ACTION CODE:")
if 'zil_action_code' in location.attributes:
    action_code = location.attributes['zil_action_code']
    # Extract the relevant part
    if 'FSET?' in action_code and 'GANGWAY-DOOR' in action_code:
        print("  ✓ Found GANGWAY-DOOR OPENBIT check in action code")
        print("\n  Relevant condition:")
        print("    (COND ((FSET? ,GANGWAY-DOOR ,OPENBIT) (TELL \".\"))")
        print("          (T (TELL \", but both of these are blocked by closed bulkheads.\")))")
        print("\n  This means: IF gangway_door has OPENBIT (is_open=true), say '.', ELSE say 'blocked'")

print("\n" + "=" * 80)
print("\n🔍 DIAGNOSIS:")
print("\n  The doors are marked as is_open=true in the JSON file.")
print("  They should be included in the items context sent to the LLM.")
print("  The LLM should interpret the ZIL condition based on the is_open attribute.")
print("\n  If the description still says 'closed bulkheads', the problem is likely:")
print("  1. The LLM is not correctly translating OPENBIT → is_open attribute")
print("  2. The LLM is not seeing the door items in the context")
print("  3. The ZIL translation layer is not working correctly")
print("\n" + "=" * 80)
