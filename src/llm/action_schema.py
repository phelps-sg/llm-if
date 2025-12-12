"""Schema for LLM-driven action parsing and state updates."""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class StateUpdate(BaseModel):
    """Represents a single state update to apply to the game world."""

    type: Literal[
        "move_player",
        "move_item",
        "move_npc",
        "remove_npc",
        "modify_attribute",
        "add_to_inventory",
        "remove_from_inventory",
        "consume_item",
        "create_item",
        "destroy_item",
        "transform_item",
        "transform_item_to_npc",
        "transform_npc_to_item",
        "create_location",
        "create_npc",
        "set_flag",
        "trigger_combat",
        "update_dm_state",
        "no_change",
    ] = Field(..., description="Type of state update")

    target: Optional[str] = Field(None, description="Target entity ID")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the update"
    )


class IntentInterpretation(BaseModel):
    """Step 1 output: Intent interpretation and permission check.

    Separates logical validation (is_valid) from contextual permission (is_allowed).
    """

    intent: str = Field(..., description="What the player is trying to do")

    is_valid: bool = Field(
        ...,
        description="Does the action make logical sense? (e.g., 'go north' is valid, 'asdfghjkl' is not)"
    )

    is_allowed: bool = Field(
        ...,
        description="If valid, will the DM allow it given current game state? (e.g., 'go north' allowed only if north exit exists)"
    )

    invalid_reason: Optional[str] = Field(
        None,
        description="If is_valid=false, explanation of why the command doesn't make sense"
    )

    not_allowed_reason: Optional[str] = Field(
        None,
        description="If is_allowed=false, explanation of why the action cannot succeed (becomes the narrative)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "intent": "Player wants to move north",
                "is_valid": True,
                "is_allowed": False,
                "invalid_reason": None,
                "not_allowed_reason": "There is no exit to the north. You can only go south to the hall."
            }
        }


class MechanicsResult(BaseModel):
    """Step 2 output: State update generation.

    Generates only the mechanics (state updates) without narrative.
    """

    state_updates: List[StateUpdate] = Field(
        default_factory=list,
        description="List of state changes to apply to implement the intent"
    )

    requires_dice_roll: bool = Field(
        default=False,
        description="Whether mechanics require a dice roll"
    )

    dice_check: Optional[Dict[str, Any]] = Field(
        None,
        description="Dice check parameters if needed"
    )

    time_advancement: Optional[str] = Field(
        None,
        description="How much in-game time passes (natural language)"
    )

    new_time: Optional[str] = Field(
        None,
        description="The new in-game date/time after this action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state_updates": [
                    {
                        "type": "move_player",
                        "params": {"destination": "hall"}
                    }
                ],
                "requires_dice_roll": False,
                "dice_check": None,
                "time_advancement": "5 minutes",
                "new_time": "Day 1, Afternoon, 3:35 PM"
            }
        }


class ActionInterpretation(BaseModel):
    """DEPRECATED: Use 3-step flow (IntentInterpretation + MechanicsResult + narrative).

    LLM's interpretation of player action with state updates and narrative.
    This class combines all steps and can lead to hallucination issues.
    """

    intent: str = Field(..., description="What the player is trying to do")

    is_valid: bool = Field(
        ..., description="Whether the action is valid in current context"
    )

    state_updates: List[StateUpdate] = Field(
        default_factory=list, description="List of state updates to apply"
    )

    narrative_response: Optional[str] = Field(
        None, description="DM's narrative response to the action (optional - may be generated separately)"
    )

    requires_dice_roll: bool = Field(
        default=False, description="Whether this action requires a dice roll"
    )

    dice_check: Optional[Dict[str, Any]] = Field(
        None, description="Dice check parameters if needed"
    )

    time_advancement: Optional[str] = Field(
        None,
        description="How much in-game time passes (natural language, e.g., '1 hour', '10 minutes', '3 days', 'several weeks'). DM controls creative time progression including fast travel, time skips, etc."
    )

    new_time: Optional[str] = Field(
        None,
        description="The new in-game date/time after this action (natural language format, e.g., 'Day 1, Afternoon, 2:30 PM'). If provided, this overrides the previous time completely."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "intent": "Player wants to greet the skeletal guard",
                "is_valid": True,
                "state_updates": [
                    {
                        "type": "modify_attribute",
                        "target": "guard_skeleton",
                        "params": {
                            "attribute_path": "state.has_been_greeted",
                            "value": True,
                        },
                    }
                ],
                "narrative_response": "You call out a greeting to the skeletal guard. Its hollow eye sockets turn toward you, glowing with an eerie green light. The undead creature doesn't respond verbally, but you sense its awareness of your presence has changed.",
                "requires_dice_roll": False,
                "dice_check": None,
            }
        }
