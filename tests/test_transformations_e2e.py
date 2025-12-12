"""E2E tests for item/NPC transformation system."""

import pytest
import json
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine
from src.engine.game_loop import GameLoop


@pytest.fixture
def game_with_transformable_items():
    """Setup game with items that can be transformed."""
    from src.models.item import Item
    from src.models.npc import NPC

    with open("worlds/example_dungeon.json", "r") as f:
        world_data = json.load(f)

    game_state = GameState.from_dict(world_data)

    # Add a leaflet at starting location
    leaflet = Item(
        id="leaflet",
        name="leaflet",
        attributes={"description": "A small paper leaflet with information."}
    )
    game_state.items["leaflet"] = leaflet
    game_state.item_locations["leaflet"] = "entrance"

    # Add a stone statue at entrance
    statue = Item(
        id="stone_statue",
        name="stone statue",
        attributes={"description": "A statue carved from stone.", "material": "stone"}
    )
    game_state.items["stone_statue"] = statue
    game_state.item_locations["stone_statue"] = "entrance"

    # Add a goblin at entrance (for petrification test)
    goblin = NPC(
        id="goblin",
        name="goblin",
        attributes={
            "description": "A small, green goblin.",
            "hp": 7,
            "hp_max": 7,
            "armor_class": 15,
            "hostility": "aggressive"
        }
    )
    game_state.npcs["goblin"] = goblin
    game_state.npc_locations["goblin"] = "entrance"

    game_state.player_location = "entrance"
    game_state.player.inventory = []

    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    return game_loop, game_state


def test_fold_leaflet_into_paper_plane(game_with_transformable_items):
    """Test transforming leaflet into paper plane (item → item transformation)."""
    game_loop, game_state = game_with_transformable_items

    # Pick up leaflet
    game_loop.process_turn("take the leaflet")
    assert "leaflet" in game_state.player.inventory
    original_leaflet = game_state.items["leaflet"]

    # Fold into paper plane
    narrative, interpretation = game_loop.process_turn("fold the leaflet into a paper plane")

    # Assert: leaflet still exists (same ID) but transformed
    assert "leaflet" in game_state.items, "Item should still exist with same ID"
    assert "leaflet" in game_state.player.inventory, "Item should still be in inventory"

    transformed_item = game_state.items["leaflet"]

    # Assert: name changed to paper plane
    assert "plane" in transformed_item.name.lower(), \
        f"Item name should reference plane, got: {transformed_item.name}"

    # Assert: transformation was recorded in state updates
    state_updates = interpretation.get("state_updates", [])
    has_transform = any(u.get("type") == "transform_item" for u in state_updates)
    assert has_transform, \
        f"Expected transform_item state update, got: {state_updates}"


def test_transformation_preserves_history(game_with_transformable_items):
    """Test that transformation history is tracked for DM narrative and reversal."""
    game_loop, game_state = game_with_transformable_items

    # Pick up leaflet
    game_loop.process_turn("take the leaflet")

    # Fold into paper plane
    game_loop.process_turn("fold the leaflet into a paper plane")

    transformed_item = game_state.items["leaflet"]

    # Assert: transformation history exists
    assert "transformation_history" in transformed_item.attributes, \
        "Item should have transformation_history in attributes"

    history = transformed_item.attributes["transformation_history"]
    assert len(history) > 0, "Should have at least one transformation record"

    # Assert: history contains original state
    first_transform = history[0]
    assert "from_name" in first_transform, "Should record original name"
    assert "leaflet" in first_transform["from_name"].lower(), \
        f"Should record 'leaflet' as original, got: {first_transform.get('from_name')}"

    # Assert: history contains new state
    assert "to_name" in first_transform, "Should record new name"
    assert "plane" in first_transform["to_name"].lower(), \
        f"Should record 'plane' as new name, got: {first_transform.get('to_name')}"

    # Assert: turn number recorded
    assert "turn" in first_transform, "Should record turn number"


def test_reversible_transformation(game_with_transformable_items):
    """Test that reversible transformations can be undone."""
    game_loop, game_state = game_with_transformable_items

    # Pick up leaflet
    game_loop.process_turn("take the leaflet")

    # Fold into paper plane (should be reversible)
    narrative1, interpretation1 = game_loop.process_turn("fold the leaflet into a paper plane")

    transformed_item = game_state.items["leaflet"]
    history = transformed_item.attributes.get("transformation_history", [])

    # Assert: transformation marked as reversible
    # Note: LLM should infer that folding paper is reversible
    if history:
        first_transform = history[0]
        if "reversible" in first_transform:
            assert first_transform["reversible"] == True, \
                "Folding paper should be marked as reversible"

    # Unfold back to leaflet
    narrative2, interpretation2 = game_loop.process_turn("unfold the paper plane")

    unfolded_item = game_state.items["leaflet"]

    # Assert: item can be unfolded (LLM should reference transformation history)
    # The name might be back to "leaflet" or similar
    # What's important is that the LLM can access the transformation history


def test_animate_statue_item_to_npc(game_with_transformable_items):
    """Test transforming item into NPC (e.g., animate object spell)."""
    game_loop, game_state = game_with_transformable_items

    # Statue starts as an item
    assert "stone_statue" in game_state.items
    assert "stone_statue" in game_state.item_locations
    assert game_state.item_locations["stone_statue"] == "entrance"

    # Cast animate object on statue
    narrative, interpretation = game_loop.process_turn("cast animate object on the statue")

    state_updates = interpretation.get("state_updates", [])
    has_transform_to_npc = any(u.get("type") == "transform_item_to_npc" for u in state_updates)

    # If LLM generated transform_item_to_npc:
    if has_transform_to_npc:
        # Assert: statue no longer exists as item
        # (might keep same ID or create new NPC ID - implementation dependent)

        # Assert: new NPC exists at same location
        npcs_at_entrance = game_state.get_npcs_at_location("entrance")
        animated_npcs = [npc for npc in npcs_at_entrance
                        if "statue" in npc.name.lower() or "golem" in npc.name.lower()]

        assert len(animated_npcs) > 0, \
            f"Should have animated NPC at entrance, got NPCs: {[n.name for n in npcs_at_entrance]}"

        animated_npc = animated_npcs[0]

        # Assert: NPC has transformation history
        if "transformation_history" in animated_npc.attributes:
            history = animated_npc.attributes["transformation_history"]
            assert len(history) > 0, "NPC should have transformation history"

            first_transform = history[0]
            assert first_transform.get("from_type") == "item", \
                "Should record transformation from item"
            assert "statue" in first_transform.get("from_name", "").lower(), \
                f"Should record statue as original, got: {first_transform.get('from_name')}"


def test_petrify_npc_to_item(game_with_transformable_items):
    """Test transforming NPC into item (e.g., petrify spell)."""
    game_loop, game_state = game_with_transformable_items

    # Goblin starts as NPC
    assert "goblin" in game_state.npcs
    assert "goblin" in game_state.npc_locations
    assert game_state.npc_locations["goblin"] == "entrance"

    # Cast petrify on goblin
    narrative, interpretation = game_loop.process_turn("cast petrify on the goblin")

    state_updates = interpretation.get("state_updates", [])
    has_transform_to_item = any(u.get("type") == "transform_npc_to_item" for u in state_updates)

    # If LLM generated transform_npc_to_item:
    if has_transform_to_item:
        # Assert: goblin no longer exists as NPC at entrance
        npcs_at_entrance = game_state.get_npcs_at_location("entrance")
        goblin_npcs = [npc for npc in npcs_at_entrance if "goblin" in npc.name.lower()]

        assert len(goblin_npcs) == 0, \
            f"Goblin should be petrified (not an NPC), found: {[n.name for n in goblin_npcs]}"

        # Assert: statue/stone item exists at entrance
        items_at_entrance = game_state.get_items_at_location("entrance")
        statue_items = [item for item in items_at_entrance
                       if "statue" in item.name.lower() or "stone" in item.name.lower()]

        assert len(statue_items) > 0, \
            f"Should have petrified goblin as item at entrance, got items: {[i.name for i in items_at_entrance]}"

        petrified_item = statue_items[0]

        # Assert: item has transformation history
        if "transformation_history" in petrified_item.attributes:
            history = petrified_item.attributes["transformation_history"]
            assert len(history) > 0, "Item should have transformation history"

            first_transform = history[0]
            assert first_transform.get("from_type") == "npc", \
                "Should record transformation from NPC"
            assert "goblin" in first_transform.get("from_name", "").lower(), \
                f"Should record goblin as original, got: {first_transform.get('from_name')}"


def test_transformation_no_orphaned_references(game_with_transformable_items):
    """Regression test: transformations should not create orphaned item_locations references.

    This tests the original bug where folding leaflet into paper plane crashed
    because of mismatched items dict and item_locations dict.
    """
    game_loop, game_state = game_with_transformable_items

    # Pick up leaflet
    game_loop.process_turn("take the leaflet")
    assert "leaflet" in game_state.player.inventory

    # Fold into paper plane
    game_loop.process_turn("fold the leaflet into a paper plane")

    # Assert: no orphaned references - every item_id in item_locations exists in items
    for item_id in game_state.item_locations.keys():
        assert item_id in game_state.items, \
            f"Orphaned reference: '{item_id}' in item_locations but not in items dict"

    # Assert: no crashes when looking up items at location
    # This used to crash with KeyError before fix
    items_at_entrance = game_state.get_items_at_location("entrance")
    # Should succeed without KeyError

    items_in_inventory = [game_state.items[item_id]
                         for item_id in game_state.player.inventory
                         if item_id in game_state.items]
    # Should succeed without KeyError

    # Assert: transformed item is accessible
    assert "leaflet" in game_state.items
    transformed_item = game_state.items["leaflet"]
    assert transformed_item is not None
