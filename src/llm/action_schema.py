"""Schema for LLM-driven action parsing and state updates."""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class StateUpdate(BaseModel):
    """Represents a single state update to apply to the game world."""

    type: Literal[
        "move_player",
        "move_item",
        "move_npc",
        "modify_attribute",
        "add_to_inventory",
        "remove_from_inventory",
        "set_flag",
        "trigger_combat",
        "no_change",
    ] = Field(..., description="Type of state update")

    target: Optional[str] = Field(None, description="Target entity ID")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the update"
    )


class ActionInterpretation(BaseModel):
    """LLM's interpretation of player action with state updates and narrative."""

    intent: str = Field(..., description="What the player is trying to do")

    is_valid: bool = Field(
        ..., description="Whether the action is valid in current context"
    )

    state_updates: List[StateUpdate] = Field(
        default_factory=list, description="List of state updates to apply"
    )

    narrative_response: str = Field(
        ..., description="DM's narrative response to the action"
    )

    requires_dice_roll: bool = Field(
        default=False, description="Whether this action requires a dice roll"
    )

    dice_check: Optional[Dict[str, Any]] = Field(
        None, description="Dice check parameters if needed"
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
