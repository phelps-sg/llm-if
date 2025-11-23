"""Tests for the lighting and time-of-day system."""

import pytest
from src.models.game_state import GameState
from src.models.location import Location
from src.models.item import Item
from src.models.player import Player


def test_time_of_day_cycle():
    """Test that time of day cycles correctly based on turn count."""
    game_state = GameState()

    # Test full cycle (40 turns = 8 periods of 5 turns each)
    expected_times = [
        "dawn",  # turns 0-4
        "morning",  # turns 5-9
        "day",  # turns 10-14
        "afternoon",  # turns 15-19
        "dusk",  # turns 20-24
        "evening",  # turns 25-29
        "night",  # turns 30-34
        "midnight",  # turns 35-39
        "dawn",  # turns 40-44 (cycle repeats)
    ]

    turn_samples = [0, 5, 10, 15, 20, 25, 30, 35, 40]

    for turn, expected_time in zip(turn_samples, expected_times):
        game_state.turn_count = turn
        assert (
            game_state.get_time_of_day() == expected_time
        ), f"Turn {turn} should be {expected_time}"


def test_ambient_light_levels():
    """Test that ambient light changes with time of day."""
    game_state = GameState()

    # Bright times
    for time in ["morning", "day", "afternoon"]:
        game_state.turn_count = {
            "morning": 5,
            "day": 10,
            "afternoon": 15,
        }[time]
        assert game_state.get_ambient_light_level() == "bright"
        assert game_state.is_daytime() is True

    # Dim times
    for time in ["dawn", "dusk", "evening"]:
        game_state.turn_count = {
            "dawn": 0,
            "dusk": 20,
            "evening": 25,
        }[time]
        assert game_state.get_ambient_light_level() == "dim"

    # Dark times
    for time in ["night", "midnight"]:
        game_state.turn_count = {
            "night": 30,
            "midnight": 35,
        }[time]
        assert game_state.get_ambient_light_level() == "dark"
        assert game_state.is_daytime() is False


def test_indoor_location_lighting_without_torch():
    """Test that indoor location is dark without a light source."""
    game_state = GameState()

    # Create dark indoor location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Set time to day (shouldn't matter for indoor without windows)
    game_state.turn_count = 10  # day

    lighting = game_state.get_effective_lighting("dungeon")

    assert lighting["level"] == "pitch_black"
    assert lighting["natural"] == "pitch_black"
    assert lighting["artificial"] == "none"
    assert lighting["can_see_clearly"] is False
    assert lighting["light_sources"] == []
    assert lighting["time_of_day"] == "day"


def test_indoor_location_lighting_with_torch():
    """Test that torch provides light in dark location."""
    game_state = GameState()

    # Create dark indoor location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Create torch item
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "type": "light_source",
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch

    # Give player the torch
    game_state.player.add_item("torch")

    lighting = game_state.get_effective_lighting("dungeon")

    assert lighting["level"] == "dim"  # Torch provides dim light
    assert lighting["natural"] == "pitch_black"
    assert lighting["artificial"] == "dim"
    assert lighting["can_see_clearly"] is True  # dim or better = can see
    assert any("Torch" in source for source in lighting["light_sources"])


def test_outdoor_location_day_vs_night():
    """Test that outdoor locations change lighting with time of day."""
    game_state = GameState()

    # Create outdoor location
    forest = Location(
        id="forest",
        name="Forest Clearing",
        attributes={
            "lighting": "dark",  # Base lighting (used only if not outdoors)
            "is_outdoors": True,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["forest"] = forest
    game_state.player_location = "forest"

    # Test during day (turn 10)
    game_state.turn_count = 10
    lighting_day = game_state.get_effective_lighting("forest")
    assert lighting_day["level"] == "bright"
    assert lighting_day["natural"] == "bright"
    assert lighting_day["time_of_day"] == "day"

    # Test during night (turn 30)
    game_state.turn_count = 30
    lighting_night = game_state.get_effective_lighting("forest")
    assert lighting_night["level"] == "dark"
    assert lighting_night["natural"] == "dark"
    assert lighting_night["time_of_day"] == "night"


def test_location_with_windows():
    """Test that locations with windows get some daylight."""
    game_state = GameState()

    # Create location with windows
    room = Location(
        id="room",
        name="Stone Room",
        attributes={
            "lighting": "dark",
            "is_outdoors": False,
            "has_windows": True,
        },
        connections={},
    )
    game_state.locations["room"] = room
    game_state.player_location = "room"

    # Test during day (ambient bright -> windows provide dim)
    game_state.turn_count = 10  # day
    lighting_day = game_state.get_effective_lighting("room")
    assert lighting_day["level"] == "dim"
    assert lighting_day["natural"] == "dim"

    # Test during night (ambient dark -> windows provide nothing)
    game_state.turn_count = 30  # night
    lighting_night = game_state.get_effective_lighting("room")
    assert lighting_night["level"] == "dark"
    assert lighting_night["natural"] == "dark"


def test_multiple_light_sources():
    """Test that multiple light sources - brightest one wins."""
    game_state = GameState()

    # Create dark location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Create dim torch
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch

    # Create bright lantern
    lantern = Item(
        id="lantern",
        name="Lantern",
        attributes={
            "provides_light": True,
            "light_level": "bright",
        },
    )
    game_state.items["lantern"] = lantern

    # Give player both light sources
    game_state.player.add_item("torch")
    game_state.player.add_item("lantern")

    lighting = game_state.get_effective_lighting("dungeon")

    # Brightest light source should win
    assert lighting["level"] == "bright"
    assert lighting["artificial"] == "bright"
    assert any("Torch" in source for source in lighting["light_sources"])
    assert any("Lantern" in source for source in lighting["light_sources"])
    assert len(lighting["light_sources"]) == 2


def test_light_source_dropped():
    """Test that dropping torch still provides light (it's at the location)."""
    game_state = GameState()

    # Create dark location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Create torch
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch
    game_state.player.add_item("torch")

    # With torch in inventory - should be dim
    lighting_carried = game_state.get_effective_lighting("dungeon")
    assert lighting_carried["level"] == "dim"
    assert lighting_carried["can_see_clearly"] is True
    assert "Torch (carried)" in lighting_carried["light_sources"]

    # Drop torch at location
    game_state.player.remove_item("torch")
    game_state.item_locations["torch"] = "dungeon"

    # Torch still provides light (it's on the ground here)
    lighting_dropped = game_state.get_effective_lighting("dungeon")
    assert lighting_dropped["level"] == "dim"
    assert lighting_dropped["can_see_clearly"] is True
    assert "Torch (here)" in lighting_dropped["light_sources"]


def test_light_source_moved_to_different_location():
    """Test that moving torch to different location makes original location dark."""
    game_state = GameState()

    # Create two dark locations
    room1 = Location(
        id="room1",
        name="Dark Room 1",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={"east": "room2"},
    )
    room2 = Location(
        id="room2",
        name="Dark Room 2",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={"west": "room1"},
    )
    game_state.locations["room1"] = room1
    game_state.locations["room2"] = room2
    game_state.player_location = "room1"

    # Create torch at room1
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch
    game_state.item_locations["torch"] = "room1"

    # Room1 should have light
    lighting_room1_with_torch = game_state.get_effective_lighting("room1")
    assert lighting_room1_with_torch["level"] == "dim"

    # Move torch to room2
    game_state.item_locations["torch"] = "room2"

    # Room1 should now be pitch black
    lighting_room1_without_torch = game_state.get_effective_lighting("room1")
    assert lighting_room1_without_torch["level"] == "pitch_black"
    assert lighting_room1_without_torch["light_sources"] == []

    # Room2 should now have light
    lighting_room2_with_torch = game_state.get_effective_lighting("room2")
    assert lighting_room2_with_torch["level"] == "dim"
    assert "Torch (here)" in lighting_room2_with_torch["light_sources"]


def test_can_see_clearly_threshold():
    """Test that can_see_clearly is True for dim or better."""
    game_state = GameState()

    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # pitch_black - cannot see
    lighting = game_state.get_effective_lighting("dungeon")
    assert lighting["level"] == "pitch_black"
    assert lighting["can_see_clearly"] is False

    # Give player dim torch - can see
    torch = Item(
        id="torch",
        name="Torch",
        attributes={"provides_light": True, "light_level": "dim"},
    )
    game_state.items["torch"] = torch
    game_state.player.add_item("torch")

    lighting = game_state.get_effective_lighting("dungeon")
    assert lighting["level"] == "dim"
    assert lighting["can_see_clearly"] is True


def test_lighting_combined_natural_and_artificial():
    """Test that natural and artificial light combine (max wins)."""
    game_state = GameState()

    # Location with some natural light
    cave_entrance = Location(
        id="cave_entrance",
        name="Cave Entrance",
        attributes={
            "lighting": "dark",
            "is_outdoors": False,
            "has_windows": True,  # Gets some light from outside
        },
        connections={},
    )
    game_state.locations["cave_entrance"] = cave_entrance
    game_state.player_location = "cave_entrance"

    # Daytime with windows = dim natural light
    game_state.turn_count = 10  # day

    # Create bright lantern
    lantern = Item(
        id="lantern",
        name="Lantern",
        attributes={"provides_light": True, "light_level": "bright"},
    )
    game_state.items["lantern"] = lantern
    game_state.player.add_item("lantern")

    lighting = game_state.get_effective_lighting("cave_entrance")

    # Should take max(dim natural, bright artificial) = bright
    assert lighting["level"] == "bright"
    assert lighting["natural"] == "dim"
    assert lighting["artificial"] == "bright"


def test_underground_dungeon_not_affected_by_daylight():
    """Test that underground dungeon stays dark regardless of time of day."""
    game_state = GameState()

    # Create underground dungeon (like the example dungeon)
    dungeon = Location(
        id="dungeon",
        name="Underground Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
            "description_hints": "underground, no natural light",
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Test during bright day (turn 10)
    game_state.turn_count = 10
    lighting_day = game_state.get_effective_lighting("dungeon")
    assert lighting_day["level"] == "pitch_black"
    assert lighting_day["time_of_day"] == "day"
    assert lighting_day["natural"] == "pitch_black"  # Uses base lighting, not daylight

    # Test during night (turn 30)
    game_state.turn_count = 30
    lighting_night = game_state.get_effective_lighting("dungeon")
    assert lighting_night["level"] == "pitch_black"
    assert lighting_night["time_of_day"] == "night"
    assert lighting_night["natural"] == "pitch_black"

    # Underground stays dark both day and night
    assert lighting_day["level"] == lighting_night["level"]


def test_above_ground_vs_underground_lighting():
    """Test that above-ground changes with time but underground doesn't."""
    game_state = GameState()

    # Create above-ground forest
    forest = Location(
        id="forest",
        name="Forest",
        attributes={
            "lighting": "bright",  # Base doesn't matter for outdoors
            "is_outdoors": True,
            "has_windows": False,
        },
        connections={"down": "cave"},
    )

    # Create underground cave below the forest
    cave = Location(
        id="cave",
        name="Dark Cave",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={"up": "forest"},
    )

    game_state.locations["forest"] = forest
    game_state.locations["cave"] = cave

    # Test at noon (turn 10)
    game_state.turn_count = 10

    # Forest should be bright (daytime)
    game_state.player_location = "forest"
    forest_light = game_state.get_effective_lighting("forest")
    assert forest_light["level"] == "bright"
    assert forest_light["is_outdoors"] is True

    # Cave should be pitch black (underground)
    game_state.player_location = "cave"
    cave_light = game_state.get_effective_lighting("cave")
    assert cave_light["level"] == "pitch_black"
    assert cave_light["is_outdoors"] is False

    # Test at midnight (turn 35)
    game_state.turn_count = 35

    # Forest should be dark (nighttime)
    game_state.player_location = "forest"
    forest_night = game_state.get_effective_lighting("forest")
    assert forest_night["level"] == "dark"

    # Cave should STILL be pitch black (unchanged)
    game_state.player_location = "cave"
    cave_night = game_state.get_effective_lighting("cave")
    assert cave_night["level"] == "pitch_black"

    # Cave lighting doesn't change with time
    assert cave_light["level"] == cave_night["level"]


def test_dungeon_entrance_with_torch_day_and_night():
    """Test that dungeon entrance (underground) needs torch both day and night."""
    game_state = GameState()

    # Dungeon entrance - underground, no windows
    entrance = Location(
        id="entrance",
        name="Dungeon Entrance",
        attributes={
            "lighting": "dark",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["entrance"] = entrance
    game_state.player_location = "entrance"

    # Create torch
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch

    # Test at noon WITHOUT torch - still dark (underground)
    game_state.turn_count = 10  # day
    light_without_torch_day = game_state.get_effective_lighting("entrance")
    assert light_without_torch_day["level"] == "dark"
    assert light_without_torch_day["time_of_day"] == "day"

    # Add torch - now has dim light
    game_state.player.add_item("torch")
    light_with_torch_day = game_state.get_effective_lighting("entrance")
    assert light_with_torch_day["level"] == "dim"

    # Test at night WITH torch - still dim (torch works same regardless of time)
    game_state.turn_count = 30  # night
    light_with_torch_night = game_state.get_effective_lighting("entrance")
    assert light_with_torch_night["level"] == "dim"

    # Torch provides same light level day or night in underground location
    assert light_with_torch_day["level"] == light_with_torch_night["level"]


def test_torch_at_location_provides_light():
    """Test that torch on the ground provides light to the location."""
    game_state = GameState()

    # Create dark location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Create torch at location (not in inventory)
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch
    game_state.item_locations["torch"] = "dungeon"

    # Torch on ground should provide light
    lighting = game_state.get_effective_lighting("dungeon")
    assert lighting["level"] == "dim"
    assert lighting["artificial"] == "dim"
    assert "Torch (here)" in lighting["light_sources"]
    assert lighting["can_see_clearly"] is True


def test_torch_picked_up_still_provides_light():
    """Test that torch provides light both on ground and when carried."""
    game_state = GameState()

    # Create dark location
    dungeon = Location(
        id="dungeon",
        name="Dark Dungeon",
        attributes={
            "lighting": "pitch_black",
            "is_outdoors": False,
            "has_windows": False,
        },
        connections={},
    )
    game_state.locations["dungeon"] = dungeon
    game_state.player_location = "dungeon"

    # Create torch at location
    torch = Item(
        id="torch",
        name="Torch",
        attributes={
            "provides_light": True,
            "light_level": "dim",
        },
    )
    game_state.items["torch"] = torch
    game_state.item_locations["torch"] = "dungeon"

    # Before pickup - torch on ground provides light
    lighting_before = game_state.get_effective_lighting("dungeon")
    assert lighting_before["level"] == "dim"
    assert "Torch (here)" in lighting_before["light_sources"]

    # Pick up torch
    game_state.move_item_to_player("torch")

    # After pickup - torch in inventory provides light
    lighting_after = game_state.get_effective_lighting("dungeon")
    assert lighting_after["level"] == "dim"
    assert "Torch (carried)" in lighting_after["light_sources"]

    # Both provide same light level
    assert lighting_before["level"] == lighting_after["level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
