"""D&D 5e specific rule implementations."""

from typing import Dict, Any, List
from .rule import Rule, RuleTrigger, RuleEffect


def get_dnd_combat_rules() -> List[Rule]:
    """Get D&D 5e combat rules."""

    rules = []

    # Melee attack rule
    melee_attack = Rule(
        id="dnd_melee_attack",
        name="Melee Attack",
        description="Standard D&D 5e melee weapon attack",
        trigger=RuleTrigger.ACTION,
        trigger_filter={"action_type": "attack", "attack_range": "melee"},
        conditions=["actor.hp > 0", "target.hp > 0"],
        effects=[
            RuleEffect(
                type="d20_check",
                params={
                    "modifier": "actor.attack_bonus",
                    "dc": "target.armor_class",
                    "on_success": {
                        "type": "damage",
                        "damage_dice": "weapon.damage",
                        "damage_type": "weapon.damage_type",
                    },
                },
            )
        ],
        priority=100,
        can_override=False,
    )
    rules.append(melee_attack)

    # Ranged attack rule
    ranged_attack = Rule(
        id="dnd_ranged_attack",
        name="Ranged Attack",
        description="Standard D&D 5e ranged weapon attack",
        trigger=RuleTrigger.ACTION,
        trigger_filter={"action_type": "attack", "attack_range": "ranged"},
        conditions=["actor.hp > 0", "target.hp > 0"],
        effects=[
            RuleEffect(
                type="d20_check",
                params={
                    "modifier": "actor.attack_bonus",
                    "dc": "target.armor_class",
                    "on_success": {
                        "type": "damage",
                        "damage_dice": "weapon.damage",
                        "damage_type": "weapon.damage_type",
                    },
                },
            )
        ],
        priority=100,
        can_override=False,
    )
    rules.append(ranged_attack)

    # Death rule
    death_rule = Rule(
        id="dnd_death",
        name="Death",
        description="Entity dies when HP reaches 0",
        trigger=RuleTrigger.DAMAGE_TAKEN,
        conditions=["target.hp <= 0"],
        effects=[
            RuleEffect(
                type="set_flag",
                params={"flag": "entity.{entity_id}.is_dead", "value": True},
            )
        ],
        priority=200,
        can_override=False,
    )
    rules.append(death_rule)

    return rules


def get_dnd_skill_check_rules() -> List[Rule]:
    """Get D&D 5e skill check rules."""

    rules = []

    # Generic ability check
    ability_check = Rule(
        id="dnd_ability_check",
        name="Ability Check",
        description="Standard D&D 5e ability check",
        trigger=RuleTrigger.ACTION,
        trigger_filter={"action_type": "ability_check"},
        conditions=[],
        effects=[
            RuleEffect(
                type="d20_check",
                params={"modifier": "actor.ability_modifier", "dc": "check.dc"},
            )
        ],
        priority=50,
        can_override=True,
    )
    rules.append(ability_check)

    # Saving throw
    saving_throw = Rule(
        id="dnd_saving_throw",
        name="Saving Throw",
        description="Standard D&D 5e saving throw",
        trigger=RuleTrigger.ACTION,
        trigger_filter={"action_type": "saving_throw"},
        conditions=[],
        effects=[
            RuleEffect(
                type="d20_check",
                params={"modifier": "actor.save_modifier", "dc": "save.dc"},
            )
        ],
        priority=50,
        can_override=False,
    )
    rules.append(saving_throw)

    return rules


def get_all_dnd_rules() -> List[Rule]:
    """Get all D&D 5e rules."""
    rules = []
    rules.extend(get_dnd_combat_rules())
    rules.extend(get_dnd_skill_check_rules())
    return rules


# Utility functions for D&D 5e mechanics


def calculate_ability_modifier(ability_score: int) -> int:
    """Calculate ability modifier from ability score."""
    return (ability_score - 10) // 2


def calculate_proficiency_bonus(level: int) -> int:
    """Calculate proficiency bonus from level."""
    return 2 + ((level - 1) // 4)


def calculate_attack_bonus(
    ability_modifier: int, proficiency_bonus: int, is_proficient: bool = True
) -> int:
    """Calculate attack bonus."""
    bonus = ability_modifier
    if is_proficient:
        bonus += proficiency_bonus
    return bonus


def calculate_armor_class(
    base_ac: int, dex_modifier: int, armor_type: str = "none"
) -> int:
    """Calculate armor class.

    Args:
        base_ac: Base AC (10 for unarmored, or armor's base AC)
        dex_modifier: Dexterity modifier
        armor_type: Type of armor (none, light, medium, heavy)
    """
    if armor_type == "heavy":
        return base_ac  # Heavy armor doesn't add dex
    elif armor_type == "medium":
        return base_ac + min(dex_modifier, 2)  # Medium armor caps dex at +2
    else:
        return base_ac + dex_modifier  # Light or no armor uses full dex
