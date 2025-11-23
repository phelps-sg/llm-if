"""Item model representing objects in the game world."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class Item(BaseModel):
    """Represents an item in the game world.

    Items have flexible attributes that the rule engine interprets.
    Location and ownership are tracked separately in GameState.
    All descriptions are generated dynamically by the LLM from attributes.
    """

    id: str = Field(..., description="Unique identifier for the item")
    name: str = Field(..., description="Item name")

    # Flexible attributes for LLM rendering and mechanics
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible attributes - rule engine determines which are relevant",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rusty_sword",
                "name": "Rusty Shortsword",
                "attributes": {
                    "description_hints": "pitted blade, worn leather grip",
                    "type": "weapon",
                    "damage": "1d6",
                    "damage_type": "slashing",
                    "weight": 2,
                },
            }
        }
