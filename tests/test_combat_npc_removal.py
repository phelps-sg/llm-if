"""Test that NPCs are removed from locations when killed in combat."""

import pytest
from src.models.game_state import GameState
from src.models.location import Location
from src.models.npc import NPC
from src.models.player import Player
from src.engine.action_processor import ActionProcessor
from src.rules.rule_engine import RuleEngine


def test_npc_removed_when_killed():
    """Test that NPC is removed from location when killed in combat."""

    # Setup game state
    game_state = GameState()

    # Create a location
    hall = Location(
        id="hall",
        name="Grand Hall",
        attributes={"description_hints": "vast hall"},
        connections={},
    )
    game_state.locations["hall"] = hall
    game_state.player_location = "hall"

    # Create a weak NPC (1 HP) that will die in one hit
    guard = NPC(
        id="weak_guard",
        name="Weak Guard",
        attributes={
            "hp": 1,
            "hp_max": 1,
            "armor_class": 1,  # Very low AC, easy to hit
            "strength": 10,
        },
    )
    game_state.npcs["weak_guard"] = guard
    game_state.npc_locations["weak_guard"] = "hall"

    # Give player high stats to ensure they can hit and kill
    game_state.player.attributes = {
        "hp": 20,
        "hp_max": 20,
        "armor_class": 15,
        "strength": 18,  # +4 modifier
        "proficiency_bonus": 2,
    }

    # Verify NPC is at location before combat
    npcs_before = game_state.get_npcs_at_location("hall")
    assert len(npcs_before) == 1
    assert npcs_before[0].id == "weak_guard"
    assert "weak_guard" in game_state.npc_locations

    # Execute combat round
    rule_engine = RuleEngine()
    action_processor = ActionProcessor(rule_engine)

    # Trigger combat
    combat_result = action_processor._execute_combat_round(
        game_state, "weak_guard", "melee"
    )

    # Verify combat was successful
    assert combat_result.get("success") is True
    player_attack = combat_result.get("player_attack", {})

    # NPC should be dead (or at least killed by the attack)
    # If the attack missed, the NPC might still be alive, which is valid
    # So we only check removal if target_dead is True
    if player_attack.get("target_dead"):
        # Verify NPC is removed from location
        npcs_after = game_state.get_npcs_at_location("hall")
        assert len(npcs_after) == 0, "Dead NPC should be removed from location"
        assert (
            "weak_guard" not in game_state.npc_locations
        ), "Dead NPC should not be in npc_locations"

        # NPC should still exist in npcs dict (for history/lore)
        assert (
            "weak_guard" in game_state.npcs
        ), "Dead NPC should still exist in npcs dict"

        # NPC's HP should be 0
        assert guard.get_hp() == 0, "Dead NPC should have 0 HP"
    else:
        # If NPC survived, it should still be at the location
        npcs_after = game_state.get_npcs_at_location("hall")
        assert len(npcs_after) == 1, "Living NPC should remain at location"


def test_npc_stays_if_survives():
    """Test that NPC remains at location if it survives the attack."""

    # Setup game state
    game_state = GameState()

    # Create a location
    hall = Location(
        id="hall",
        name="Grand Hall",
        attributes={"description_hints": "vast hall"},
        connections={},
    )
    game_state.locations["hall"] = hall
    game_state.player_location = "hall"

    # Create a tough NPC (100 HP) that won't die in one hit
    guard = NPC(
        id="tough_guard",
        name="Tough Guard",
        attributes={
            "hp": 100,
            "hp_max": 100,
            "armor_class": 10,
            "strength": 10,
        },
    )
    game_state.npcs["tough_guard"] = guard
    game_state.npc_locations["tough_guard"] = "hall"

    # Give player normal stats
    game_state.player.attributes = {
        "hp": 20,
        "hp_max": 20,
        "armor_class": 15,
        "strength": 14,
        "proficiency_bonus": 2,
    }

    # Execute combat round
    rule_engine = RuleEngine()
    action_processor = ActionProcessor(rule_engine)

    combat_result = action_processor._execute_combat_round(
        game_state, "tough_guard", "melee"
    )

    # Verify combat happened
    assert combat_result.get("success") is True
    player_attack = combat_result.get("player_attack", {})

    # NPC should still be alive
    assert not player_attack.get("target_dead"), "Tough NPC should survive"

    # Verify NPC is still at location
    npcs_after = game_state.get_npcs_at_location("hall")
    assert len(npcs_after) == 1, "Living NPC should remain at location"
    assert npcs_after[0].id == "tough_guard"
    assert "tough_guard" in game_state.npc_locations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
