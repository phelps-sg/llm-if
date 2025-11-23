"""E2E tests for DM-controlled plot system.

Tests the MVP implementation of the general-purpose plot system:
- Plot configuration (pure natural language, LLM interprets)
- DM state tracking (completely freeform, LLM creates structure as needed)
- NPC transformation (plot-driven attribute changes)
- Global NPC access for plot management

The plot system is intentionally minimal and flexible - it provides
infrastructure for the LLM to orchestrate any type of plot using
natural language instructions and arbitrary hidden state.
"""

import pytest
from src.models.game_state import GameState
from src.models.location import Location
from src.models.npc import NPC
from src.models.item import Item
from src.models.player import Player
from src.engine.action_processor import ActionProcessor
from src.rules.rule_engine import RuleEngine


@pytest.fixture
def simple_test_plot():
    """Simple plot with explicit DM instructions for e2e testing.

    This has very explicit instructions to the LLM that we can verify,
    allowing us to test that the LLM actually reads plot config and
    uses update_dm_state correctly.
    """
    return {
        "locations": {
            "room": {
                "id": "room",
                "name": "Test Room",
                "attributes": {"lighting": "bright", "is_outdoors": False},
                "connections": {},
            }
        },
        "npcs": {
            "cat": {
                "id": "cat",
                "name": "Orange Cat",
                "attributes": {
                    "creature_type": "beast",
                    "hostility": "passive",
                    "hp": 2,
                    "hp_max": 2,
                },
            }
        },
        "items": {},
        "player": {
            "name": "Tester",
            "attributes": {"hp": 10, "hp_max": 10, "armor_class": 10},
            "inventory": [],
        },
        "npc_locations": {"cat": "room"},
        "item_locations": {},
        "player_location": "room",
        "turn_count": 0,
        "history": [],
        "flags": {},
        "plot_config": {
            "id": "dm_state_test",
            "title": "DM State Test Plot",
            "description": """FOR TESTING ONLY: You MUST follow these instructions exactly.
            On your very first response, use update_dm_state to set the path
            'test_initialized' to true. When the player examines or looks at the cat,
            use update_dm_state to set 'cat_observed' to true."""
        },
        "dm_state": {}
    }


@pytest.fixture
def minimal_plot_world():
    """Minimal world with natural language plot description.

    This uses a zombie infection as an example, but the plot system
    itself is general-purpose - the LLM interprets the natural language
    and creates whatever dm_state structure it needs.
    """
    return {
        "locations": {
            "forest": {
                "id": "forest",
                "name": "Forest Clearing",
                "attributes": {"lighting": "bright", "is_outdoors": True},
                "connections": {"east": "cave"},
            },
            "cave": {
                "id": "cave",
                "name": "Dark Cave",
                "attributes": {"lighting": "dark", "is_outdoors": False},
                "connections": {"west": "forest"},
            },
        },
        "npcs": {
            "deer": {
                "id": "deer",
                "name": "White Deer",
                "attributes": {
                    "creature_type": "beast",
                    "hostility": "passive",
                    "hp": 4,
                    "hp_max": 4,
                },
            },
            "wolf": {
                "id": "wolf",
                "name": "Gray Wolf",
                "attributes": {
                    "creature_type": "beast",
                    "hostility": "aggressive",
                    "hp": 10,
                    "hp_max": 10,
                },
            },
        },
        "items": {},
        "player": {
            "name": "Adventurer",
            "attributes": {"hp": 12, "hp_max": 12, "armor_class": 14},
            "inventory": [],
        },
        "npc_locations": {"deer": "forest", "wolf": "cave"},
        "item_locations": {},
        "player_location": "forest",
        "turn_count": 0,
        "history": [],
        "flags": {},
        # Natural language plot description - LLM interprets this
        "plot_config": {
            "id": "zombie_outbreak",
            "title": "The Creeping Plague",
            "description": """A necromantic infection is spreading through the land.
            The wolf in the cave is patient zero, fully infected and dangerous.
            When creatures are wounded by infected beings, they may contract the plague.
            After several turns, infected creatures begin to transform into aggressive
            undead with rotting flesh and milky eyes. Track infection status and
            progression in dm_state as you see fit."""
        },
        # Freeform dm_state - LLM creates whatever structure it needs
        "dm_state": {}
    }


def test_plot_config_loads_from_world(minimal_plot_world):
    """Test that plot configuration loads into GameState.

    Plot config is pure natural language - just verify it loads as a dict
    with some text fields that the LLM can read.
    """
    game_state = GameState.from_dict(minimal_plot_world)

    # Verify plot config exists and is a dict
    assert hasattr(game_state, "plot_config")
    assert game_state.plot_config is not None
    assert isinstance(game_state.plot_config, dict)

    # Should have basic identifying fields
    assert "id" in game_state.plot_config
    assert "title" in game_state.plot_config
    assert "description" in game_state.plot_config

    # Description should be non-empty text (LLM instructions)
    assert isinstance(game_state.plot_config["description"], str)
    assert len(game_state.plot_config["description"]) > 0


def test_dm_state_exists_and_is_mutable(minimal_plot_world):
    """Test that dm_state exists as a mutable dict.

    dm_state is completely freeform - the LLM creates whatever structure
    it needs. We just verify it exists and can be modified.
    """
    game_state = GameState.from_dict(minimal_plot_world)

    # Verify dm_state exists and is a dict
    assert hasattr(game_state, "dm_state")
    assert isinstance(game_state.dm_state, dict)

    # Can be empty initially (LLM will populate)
    # This is fine - no assertion about content needed


def test_update_dm_state_can_set_arbitrary_paths(minimal_plot_world):
    """Test that update_dm_state can set arbitrary nested paths.

    The LLM can create any structure it needs - infection tracking, political
    relationships, weather state, quest progress, etc. This tests that the
    update_dm_state mechanism works for any path.
    """
    game_state = GameState.from_dict(minimal_plot_world)
    rule_engine = RuleEngine()
    action_processor = ActionProcessor(rule_engine)

    # Test simple path
    state_updates = [
        {
            "type": "update_dm_state",
            "params": {"path": "test_value", "value": 42},
        }
    ]
    action_processor.apply_state_updates(state_updates, game_state)
    assert game_state.dm_state.get("test_value") == 42

    # Test nested path
    state_updates = [
        {
            "type": "update_dm_state",
            "params": {"path": "npc_states.wolf.status", "value": "infected"},
        }
    ]
    action_processor.apply_state_updates(state_updates, game_state)
    assert game_state.dm_state.get("npc_states", {}).get("wolf", {}).get("status") == "infected"

    # Test deeply nested path with complex value
    state_updates = [
        {
            "type": "update_dm_state",
            "params": {
                "path": "world_events.winter.days_remaining",
                "value": 7,
            },
        }
    ]
    action_processor.apply_state_updates(state_updates, game_state)
    assert game_state.dm_state.get("world_events", {}).get("winter", {}).get("days_remaining") == 7


def test_npc_attributes_can_be_modified_by_plot(minimal_plot_world):
    """Test that NPCs can be transformed by plot mechanics.

    Plots can transform NPCs by modifying their attributes. This could be
    infection, curses, possession, loyalty changes, etc. This test verifies
    the modify_attribute mechanism works for NPCs.
    """
    game_state = GameState.from_dict(minimal_plot_world)
    rule_engine = RuleEngine()
    action_processor = ActionProcessor(rule_engine)

    # Get initial NPC state
    npc_id = "deer"
    deer = game_state.npcs[npc_id]
    initial_creature_type = deer.attributes.get("creature_type")
    assert initial_creature_type == "beast"  # Starts as normal beast

    # Transform NPC (example: becomes undead)
    state_updates = [
        {
            "type": "modify_attribute",
            "target": npc_id,
            "params": {
                "attribute_path": "creature_type",
                "value": "undead",
            },
        },
        {
            "type": "modify_attribute",
            "target": npc_id,
            "params": {
                "attribute_path": "hostility",
                "value": "aggressive",
            },
        },
    ]

    action_processor.apply_state_updates(state_updates, game_state)

    # Verify NPC was transformed
    deer = game_state.npcs[npc_id]
    assert deer.attributes["creature_type"] == "undead"
    assert deer.attributes["hostility"] == "aggressive"


def test_context_includes_all_npcs_not_just_current_location(minimal_plot_world):
    """Test that LLM context includes ALL NPCs for plot management.

    The LLM needs to track and orchestrate events involving NPCs in other
    locations (infection spreading, armies marching, political scheming, etc.).
    """
    from src.engine.game_loop import GameLoop
    from src.llm.gemini_client import GeminiClient
    from src.rules.rule_engine import RuleEngine

    game_state = GameState.from_dict(minimal_plot_world)
    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    context = game_loop._build_context()

    # Context should include ALL NPCs (not just at current location)
    assert "all_npcs" in context
    all_npcs = context["all_npcs"]
    assert isinstance(all_npcs, dict)

    # Should have all NPCs in the game
    assert len(all_npcs) == len(game_state.npcs)

    # Each NPC should include location info
    for npc_id, npc_data in all_npcs.items():
        assert "location" in npc_data
        assert isinstance(npc_data["location"], str)


def test_context_includes_plot_information(minimal_plot_world):
    """Test that LLM context includes plot config and dm_state.

    The LLM needs to see the plot description (natural language instructions)
    and dm_state (hidden plot tracking) to orchestrate the plot.
    """
    from src.engine.game_loop import GameLoop
    from src.llm.gemini_client import GeminiClient
    from src.rules.rule_engine import RuleEngine

    game_state = GameState.from_dict(minimal_plot_world)
    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    context = game_loop._build_context()

    # Context should include plot information
    assert "plot" in context
    plot_context = context["plot"]
    assert isinstance(plot_context, dict)

    # Should include the plot config (with natural language description)
    assert "config" in plot_context
    assert isinstance(plot_context["config"], dict)
    assert "description" in plot_context["config"]

    # Should include dm_state (LLM's hidden tracking)
    assert "dm_state" in plot_context
    assert isinstance(plot_context["dm_state"], dict)


@pytest.mark.skipif(
    True, reason="Requires Gemini API - will implement after basic tests pass"
)
def test_llm_follows_plot_instructions_to_create_dm_state(simple_test_plot):
    """E2E test: LLM reads plot description and creates dm_state as instructed.

    This test uses a simple plot with explicit instructions to verify that:
    1. LLM reads the plot description from context
    2. LLM uses update_dm_state to create hidden state
    3. The plot system infrastructure works end-to-end
    """
    from src.engine.game_loop import GameLoop
    from src.llm.gemini_client import GeminiClient
    from src.rules.rule_engine import RuleEngine

    game_state = GameState.from_dict(simple_test_plot)
    gemini_client = GeminiClient()
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, gemini_client, rule_engine)

    # Process first turn (just look around)
    player_input = "look"
    response, _ = game_loop.process_turn(player_input)

    # LLM should have followed plot instructions to set test_initialized
    assert game_state.dm_state.get("test_initialized") is True

    # Process second turn (examine the cat)
    player_input = "examine cat"
    response, _ = game_loop.process_turn(player_input)

    # LLM should have set cat_observed
    assert game_state.dm_state.get("cat_observed") is True
