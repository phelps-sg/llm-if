"""Player model representing the player character."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class Player(BaseModel):
    """Represents the player character.

    Player has flexible attributes and inventory.
    Location is tracked in GameState.
    """

    name: str = Field(default="Adventurer", description="Player character name")

    # Flexible attributes for stats, conditions, etc.
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible attributes - rule engine determines which are relevant",
    )

    # Inventory
    inventory: List[str] = Field(
        default_factory=list, description="List of item IDs carried by player"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Aldric the Bold",
                "attributes": {
                    "class": "fighter",
                    "level": 1,
                    "hp": 12,
                    "hp_max": 12,
                    "armor_class": 16,
                    "str": 16,
                    "dex": 14,
                    "con": 14,
                    "int": 10,
                    "wis": 12,
                    "cha": 8,
                    "proficiency_bonus": 2,
                },
                "inventory": ["longsword", "shield", "backpack"],
            }
        }

    def has_item(self, item_id: str) -> bool:
        """Check if player has a specific item."""
        return item_id in self.inventory

    def add_item(self, item_id: str) -> None:
        """Add item to player inventory."""
        if item_id not in self.inventory:
            self.inventory.append(item_id)

    def remove_item(self, item_id: str) -> bool:
        """Remove item from player inventory. Returns True if item was present."""
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            return True
        return False

    def get_hp(self) -> int:
        """Get current HP."""
        return int(self.attributes.get("hp", 0))

    def get_max_hp(self) -> int:
        """Get maximum HP."""
        return int(self.attributes.get("hp_max", 0))

    def take_damage(self, damage: int) -> int:
        """Apply damage to player. Returns remaining HP."""
        current_hp = self.get_hp()
        new_hp = max(0, current_hp - damage)
        self.attributes["hp"] = new_hp
        return new_hp

    def heal(self, amount: int) -> int:
        """Heal player. Returns new HP."""
        current_hp = self.get_hp()
        max_hp = self.get_max_hp()
        new_hp = min(max_hp, current_hp + amount)
        self.attributes["hp"] = new_hp
        return new_hp
