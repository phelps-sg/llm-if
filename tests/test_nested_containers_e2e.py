"""End-to-end tests for nested container support.

Tests that items inside containers are properly visible to the LLM
and can be taken/manipulated.
"""

import pytest
from src.models.game_state import GameState
from src.models.location import Location
from src.models.item import Item
from src.engine.game_loop import GameLoop
from src.llm.gemini_client import GeminiClient
from src.rules.rule_engine import RuleEngine


@pytest.fixture
def game_with_container():
    """Create a test game with a container (mailbox) and nested item (leaflet)."""
    game_state = GameState()

    # Create starting location
    location = Location(
        id="west_of_house",
        name="West of House",
        description="You are standing in an open field west of a white house.",
        connections={},
    )
    game_state.locations["west_of_house"] = location
    game_state.player_location = "west_of_house"

    # Create mailbox (container)
    mailbox = Item(
        id="mailbox",
        name="small mailbox",
        attributes={
            "container": True,
            "open": False,
            "description": "A small mailbox",
        },
    )
    game_state.items["mailbox"] = mailbox
    game_state.item_locations["mailbox"] = "west_of_house"

    # Create leaflet (nested inside mailbox)
    leaflet = Item(
        id="advertisement",
        name="leaflet",
        attributes={
            "description": "A small leaflet advertising the Great Underground Empire",
        },
    )
    game_state.items["advertisement"] = leaflet
    game_state.item_locations["advertisement"] = "mailbox"  # Nested!

    # Initialize game loop
    llm = GeminiClient(model_name="gemini-2.0-flash-exp")
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, llm, rule_engine)

    return game_loop, game_state


def test_container_contents_visible_when_opened(game_with_container):
    """Test that opening a container makes its contents visible to the LLM."""
    game_loop, game_state = game_with_container

    # Initially, mailbox is closed and leaflet should not be visible
    assert not game_state.items["mailbox"].attributes.get("open", False)
    assert game_state.item_locations["advertisement"] == "mailbox"

    # Open the mailbox
    narrative, interpretation = game_loop.process_turn("open the mailbox")

    # After opening, mailbox should be open (check both possible attributes)
    mailbox_open = (game_state.items["mailbox"].attributes.get("is_open", False) or
                   game_state.items["mailbox"].attributes.get("open", False))
    assert mailbox_open, "Mailbox should be open after 'open the mailbox' command"

    # Build context to check what LLM sees
    context = game_loop._build_context()
    container_contents = context.get("container_contents", {})

    # If mailbox is open, its contents should be in container_contents
    if mailbox_open:
        assert "mailbox" in container_contents, "Open mailbox should appear in container_contents"
        assert len(container_contents["mailbox"]) == 1
        assert container_contents["mailbox"][0]["id"] == "advertisement"


def test_take_item_from_container(game_with_container):
    """Test that player can take an item from an open container."""
    game_loop, game_state = game_with_container

    # Open the mailbox
    narrative, interpretation = game_loop.process_turn("open the mailbox")

    # Verify mailbox is open (check both possible attributes)
    mailbox_open = (game_state.items["mailbox"].attributes.get("is_open", False) or
                   game_state.items["mailbox"].attributes.get("open", False))
    assert mailbox_open, "Mailbox should be open"

    # Take the leaflet
    narrative, interpretation = game_loop.process_turn("take the leaflet")

    # Check that leaflet is now in inventory
    assert "advertisement" in game_state.player.inventory

    # Check that leaflet is no longer at mailbox location
    assert game_state.item_locations.get("advertisement") is None


def test_cannot_see_contents_when_closed(game_with_container):
    """Test that closed containers don't show their contents."""
    game_loop, game_state = game_with_container

    # Mailbox is closed initially
    assert not game_state.items["mailbox"].attributes.get("open", False)

    # Build context
    context = game_loop._build_context()
    container_contents = context.get("container_contents", {})

    # Closed containers should not appear in container_contents
    assert "mailbox" not in container_contents


def test_zork_mailbox_scenario(game_with_container):
    """Test the actual Zork scenario: open mailbox and take leaflet."""
    game_loop, game_state = game_with_container

    # Step 1: Open mailbox
    narrative, interpretation = game_loop.process_turn("open mailbox")

    # Verify mailbox opened (check both possible attributes)
    mailbox_open = (game_state.items["mailbox"].attributes.get("is_open", False) or
                   game_state.items["mailbox"].attributes.get("open", False))
    assert mailbox_open, "Mailbox should be open after 'open mailbox' command"

    # Step 2: Take leaflet
    narrative, interpretation = game_loop.process_turn("take leaflet")

    # Verify leaflet is in inventory
    assert "advertisement" in game_state.player.inventory, \
        "Leaflet should be in inventory after 'take leaflet' command"

    # Verify state updates include add_to_inventory
    state_updates = interpretation.get("state_updates", [])
    has_add_to_inventory = any(
        u.get("type") == "add_to_inventory" and
        u.get("params", {}).get("item_id") == "advertisement"
        for u in state_updates
    )
    assert has_add_to_inventory, \
        "State updates should include add_to_inventory for leaflet"


def test_container_in_inventory():
    """Test that containers in player inventory also show their contents."""
    game_state = GameState()

    # Create starting location
    location = Location(
        id="room",
        name="Room",
        description="A simple room.",
        connections={},
    )
    game_state.locations["room"] = location
    game_state.player_location = "room"

    # Create bag (container in inventory)
    bag = Item(
        id="bag",
        name="leather bag",
        attributes={
            "container": True,
            "open": True,
        },
    )
    game_state.items["bag"] = bag
    game_state.player.add_item("bag")

    # Create coin (nested inside bag)
    coin = Item(
        id="coin",
        name="gold coin",
        attributes={},
    )
    game_state.items["coin"] = coin
    game_state.item_locations["coin"] = "bag"

    # Initialize game loop
    llm = GeminiClient(model_name="gemini-2.0-flash-exp")
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, llm, rule_engine)

    # Build context
    context = game_loop._build_context()
    container_contents = context.get("container_contents", {})

    # Bag is in inventory and open, so its contents should be visible
    assert "bag" in container_contents
    assert len(container_contents["bag"]) == 1
    assert container_contents["bag"][0]["id"] == "coin"


def test_multiple_containers():
    """Test that multiple open containers all show their contents."""
    game_state = GameState()

    # Create starting location
    location = Location(
        id="room",
        name="Room",
        description="A room with containers.",
        connections={},
    )
    game_state.locations["room"] = location
    game_state.player_location = "room"

    # Create chest (container at location)
    chest = Item(
        id="chest",
        name="wooden chest",
        attributes={
            "container": True,
            "open": True,
        },
    )
    game_state.items["chest"] = chest
    game_state.item_locations["chest"] = "room"

    # Create sword (inside chest)
    sword = Item(
        id="sword",
        name="iron sword",
        attributes={},
    )
    game_state.items["sword"] = sword
    game_state.item_locations["sword"] = "chest"

    # Create box (container at location)
    box = Item(
        id="box",
        name="small box",
        attributes={
            "container": True,
            "open": True,
        },
    )
    game_state.items["box"] = box
    game_state.item_locations["box"] = "room"

    # Create gem (inside box)
    gem = Item(
        id="gem",
        name="ruby gem",
        attributes={},
    )
    game_state.items["gem"] = gem
    game_state.item_locations["gem"] = "box"

    # Initialize game loop
    llm = GeminiClient(model_name="gemini-2.0-flash-exp")
    rule_engine = RuleEngine()
    game_loop = GameLoop(game_state, llm, rule_engine)

    # Build context
    context = game_loop._build_context()
    container_contents = context.get("container_contents", {})

    # Both containers should show contents
    assert "chest" in container_contents
    assert "box" in container_contents
    assert container_contents["chest"][0]["id"] == "sword"
    assert container_contents["box"][0]["id"] == "gem"
