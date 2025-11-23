"""Rule model for declarative game rules."""

from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from enum import Enum


class RuleTrigger(str, Enum):
    """Types of events that can trigger a rule."""

    ACTION = "action"  # Player performs an action
    TURN_START = "turn_start"  # Start of turn
    TURN_END = "turn_end"  # End of turn
    DAMAGE_TAKEN = "damage_taken"  # Entity takes damage
    ITEM_PICKED_UP = "item_picked_up"  # Item picked up
    NPC_DEATH = "npc_death"  # NPC dies
    LOCATION_ENTERED = "location_entered"  # Player enters location
    CUSTOM = "custom"  # Custom trigger


class RuleEffect(BaseModel):
    """Represents an effect that a rule can apply."""

    type: str = Field(
        ..., description="Type of effect (e.g., 'modify_attribute', 'add_item')"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the effect"
    )


class Rule(BaseModel):
    """Represents a declarative game rule.

    Rules define when and how game mechanics are applied.
    They consist of:
    - A trigger (when the rule applies)
    - Conditions (checks that must pass)
    - Effects (what happens when rule fires)
    """

    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(default="", description="What this rule does")

    # When does this rule apply?
    trigger: RuleTrigger = Field(..., description="Event that triggers this rule")
    trigger_filter: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional filters for trigger (e.g., action_type='attack')",
    )

    # What must be true?
    conditions: List[str] = Field(
        default_factory=list,
        description="Condition expressions that must evaluate to True",
    )

    # What happens?
    effects: List[RuleEffect] = Field(
        default_factory=list, description="Effects to apply when rule fires"
    )

    # Priority (higher priority rules evaluated first)
    priority: int = Field(default=0, description="Priority for rule evaluation")

    # Can this rule be overridden?
    can_override: bool = Field(
        default=False,
        description="Whether LLM can override this rule with DM discretion",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "melee_attack",
                "name": "Melee Attack",
                "description": "Standard melee weapon attack",
                "trigger": "action",
                "trigger_filter": {"action_type": "attack", "attack_type": "melee"},
                "conditions": ["actor.has_weapon", "target.is_hostile"],
                "effects": [
                    {
                        "type": "d20_check",
                        "params": {
                            "modifier": "actor.attack_bonus",
                            "dc": "target.armor_class",
                            "on_success": {
                                "type": "damage",
                                "damage_dice": "weapon.damage",
                                "damage_type": "weapon.damage_type",
                            },
                        },
                    }
                ],
                "priority": 100,
                "can_override": False,
            }
        }
