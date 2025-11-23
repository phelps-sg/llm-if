"""Location model representing places in the game world."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Represents a location in the game world.

    Locations define the topology and environmental attributes.
    Items and NPCs are tracked separately in GameState maps.
    All descriptions are generated dynamically by the LLM from attributes.
    """

    id: str = Field(..., description="Unique identifier for the location")
    name: str = Field(..., description="Location name")

    # Flexible attributes for LLM rendering
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible attributes used by LLM for description and mechanics",
    )

    # Topology
    connections: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of direction names to location IDs (None = blocked/exit)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "dungeon_entrance",
                "name": "Dungeon Entrance",
                "attributes": {
                    "description_hints": "ancient stone, moss-covered walls, water drips",
                    "lighting": "dim_torchlight",
                    "temperature": "cold",
                    "atmosphere": "foreboding",
                },
                "connections": {
                    "north": "grand_hall",
                    "east": "guard_room",
                    "south": None,
                },
            }
        }

    def get_available_exits(self) -> list[str]:
        """Get list of valid exit directions."""
        return [
            direction
            for direction, dest in self.connections.items()
            if dest is not None
        ]

    def get_exit(self, direction: str) -> Optional[str]:
        """Get destination location ID for a direction."""
        return self.connections.get(direction.lower())
