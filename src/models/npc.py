"""NPC model representing non-player characters."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class NPC(BaseModel):
    """Represents a non-player character in the game world.

    NPCs have flexible attributes that the rule engine interprets.
    Location is tracked separately in GameState.
    All descriptions and dialogue are generated dynamically by the LLM.
    """

    id: str = Field(..., description="Unique identifier for the NPC")
    name: str = Field(..., description="NPC name")

    # Flexible attributes for LLM rendering and mechanics
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible attributes - rule engine determines which are relevant",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "guard_skeleton",
                "name": "Skeletal Guard",
                "attributes": {
                    "description_hints": "rusted armor, glowing green eye sockets",
                    "creature_type": "undead",
                    "hp": 13,
                    "hp_max": 13,
                    "armor_class": 13,
                    "hostility": "aggressive_to_living",
                    "personality": "mindless_guardian",
                },
            }
        }

    def get_hp(self) -> int:
        """Get current HP."""
        return int(self.attributes.get("hp", 0))

    def get_max_hp(self) -> int:
        """Get maximum HP."""
        return int(self.attributes.get("hp_max", self.get_hp()))

    def take_damage(self, damage: int) -> int:
        """Apply damage to NPC. Returns remaining HP."""
        current_hp = self.get_hp()
        new_hp = max(0, current_hp - damage)
        self.attributes["hp"] = new_hp
        return new_hp

    def heal(self, amount: int) -> int:
        """Heal NPC. Returns new HP."""
        current_hp = self.get_hp()
        max_hp = self.get_max_hp()
        new_hp = min(max_hp, current_hp + amount)
        self.attributes["hp"] = new_hp
        return new_hp

    def is_alive(self) -> bool:
        """Check if NPC is alive (has HP > 0)."""
        return self.get_hp() > 0
