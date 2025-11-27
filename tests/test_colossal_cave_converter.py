"""Tests for Colossal Cave converter."""

import pytest
import json
from pathlib import Path
from scripts.convert_colossal_cave import ColossalCaveConverter

# Mock YAML data for testing
MOCK_YAML = """
locations:
  LOC_ROAD:
    description:
      long: "You are standing at the end of a road before a small brick building."
      short: "End of road"
    conditions: {LIT: true}
    travel:
      - verbs: [WEST, W]
        action: [goto, LOC_HILL]
      - verbs: [EAST, E]
        action: [goto, LOC_BUILDING]

  LOC_HILL:
    description:
      long: "You have walked up a hill."
      short: "Hill"
    conditions: {LIT: true}
    travel:
      - verbs: [EAST, E]
        action: [goto, LOC_ROAD]

  LOC_BUILDING:
    description:
      long: "You are inside a building."
      short: "Inside building"
    conditions: {LIT: false}
    travel:
      - verbs: [OUT, WEST, W]
        action: [goto, LOC_ROAD]

objects:
  OBJ_KEYS:
    inventory: "Set of keys"
    words: [KEYS, KEY]
    treasure: false
    locations: [LOC_BUILDING]

  OBJ_LAMP:
    inventory: "Brass lantern"
    words: [LAMP, LANTE]
    treasure: false
    locations: [LOC_BUILDING]

  OBJ_GOLD:
    inventory: "Large gold nugget"
    words: [GOLD, NUGGE]
    treasure: true
    locations: [LOC_HILL]
"""

@pytest.fixture
def mock_yaml_file(tmp_path):
    """Create temporary YAML file for testing."""
    yaml_file = tmp_path / "test_adventure.yaml"
    yaml_file.write_text(MOCK_YAML)
    return str(yaml_file)

def test_yaml_loading(mock_yaml_file):
    """Test that YAML file loads successfully."""
    converter = ColossalCaveConverter(mock_yaml_file)
    converter._load_yaml()

    assert "locations" in converter.yaml_data
    assert "objects" in converter.yaml_data
    assert len(converter.yaml_data["locations"]) == 3
    assert len(converter.yaml_data["objects"]) == 3

def test_location_conversion(mock_yaml_file):
    """Test that locations convert to correct JSON format."""
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    # Check locations exist
    assert "road" in output["locations"]
    assert "hill" in output["locations"]
    assert "building" in output["locations"]

    # Check location structure
    road = output["locations"]["road"]
    assert road["name"] == "End of road"
    assert "description_hints" in road["attributes"]
    assert road["attributes"]["lighting"] == "bright"  # LIT condition

    building = output["locations"]["building"]
    assert building["attributes"]["lighting"] == "dark"  # No LIT

def test_connection_extraction(mock_yaml_file):
    """Test that travel rules become valid connections."""
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    # Check connections
    road = output["locations"]["road"]
    assert "west" in road["connections"]
    assert road["connections"]["west"] == "hill"
    assert "east" in road["connections"]
    assert road["connections"]["east"] == "building"

    # Check reverse connection
    hill = output["locations"]["hill"]
    assert "east" in hill["connections"]
    assert hill["connections"]["east"] == "road"

def test_item_conversion(mock_yaml_file):
    """Test that objects convert to items."""
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    # Check items exist
    assert "keys" in output["items"]
    assert "lamp" in output["items"]
    assert "gold" in output["items"]

    # Check item structure
    keys = output["items"]["keys"]
    assert keys["name"] == "Keys"
    assert keys["attributes"]["type"] == "misc"
    assert keys["attributes"]["treasure"] is False

    gold = output["items"]["gold"]
    assert gold["attributes"]["treasure"] is True

def test_item_placement(mock_yaml_file):
    """Test that items are placed at correct starting locations."""
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    # Check placements
    assert output["item_locations"]["keys"] == "building"
    assert output["item_locations"]["lamp"] == "building"
    assert output["item_locations"]["gold"] == "hill"

def test_output_structure(mock_yaml_file):
    """Test that output has all required fields."""
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    required_fields = [
        "locations", "npcs", "items", "player",
        "npc_locations", "item_locations", "player_location",
        "turn_count", "history", "flags"
    ]

    for field in required_fields:
        assert field in output, f"Missing required field: {field}"

    # Check player structure
    assert "name" in output["player"]
    assert "attributes" in output["player"]
    assert "inventory" in output["player"]

def test_game_state_loading(mock_yaml_file, tmp_path):
    """Test that converted JSON loads as valid GameState."""
    # Convert
    converter = ColossalCaveConverter(mock_yaml_file)
    output = converter.convert()

    # Save to file
    json_file = tmp_path / "test_output.json"
    with open(json_file, 'w') as f:
        json.dump(output, f)

    # Try loading as GameState
    from src.models.game_state import GameState

    game_state = GameState.from_file(str(json_file))

    assert len(game_state.locations) == 3
    assert len(game_state.items) == 3
    assert game_state.player_location in game_state.locations
