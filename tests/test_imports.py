"""Test that all modules can be imported."""


def test_model_imports():
    """Test model imports."""
    from src.models import Item, Location, NPC, Player, GameState

    assert Item
    assert Location
    assert NPC
    assert Player
    assert GameState


def test_rule_imports():
    """Test rule engine imports."""
    from src.rules.rule import Rule, RuleTrigger, RuleEffect
    from src.rules.rule_engine import RuleEngine, RuleContext
    from src.rules.dnd_rules import get_all_dnd_rules

    assert Rule
    assert RuleTrigger
    assert RuleEffect
    assert RuleEngine
    assert RuleContext
    assert get_all_dnd_rules


def test_utils_imports():
    """Test utility imports."""
    from src.utils.dice import roll_d20, d20_check, roll_from_notation

    assert roll_d20
    assert d20_check
    assert roll_from_notation


def test_engine_imports():
    """Test engine imports."""
    from src.engine.action_processor import ActionProcessor
    from src.engine.game_loop import GameLoop

    assert ActionProcessor
    assert GameLoop


def test_basic_model_creation():
    """Test creating basic models."""
    from src.models import Item, Location, NPC, Player, GameState

    # Create item
    item = Item(id="test_item", name="Test Item")
    assert item.id == "test_item"

    # Create location
    location = Location(
        id="test_loc", name="Test Location", connections={"north": "other_loc"}
    )
    assert location.id == "test_loc"

    # Create NPC
    npc = NPC(id="test_npc", name="Test NPC")
    assert npc.id == "test_npc"

    # Create player
    player = Player(name="Test Hero")
    assert player.name == "Test Hero"

    # Create game state
    state = GameState()
    assert state.turn_count == 0


def test_dice_rolling():
    """Test dice rolling utilities."""
    from src.utils.dice import roll_d20, roll_from_notation, d20_check

    # Test d20
    result = roll_d20()
    assert 1 <= result <= 20

    # Test notation parsing
    result = roll_from_notation("2d6+3")
    assert "rolls" in result
    assert "total" in result
    assert result["num_dice"] == 2
    assert result["sides"] == 6
    assert result["modifier"] == 3

    # Test d20 check
    result = d20_check(modifier=5)
    assert "roll" in result
    assert "total" in result
    assert result["total"] == result["roll"] + 5


def test_rule_creation():
    """Test creating rules."""
    from src.rules.rule import Rule, RuleTrigger, RuleEffect

    rule = Rule(
        id="test_rule",
        name="Test Rule",
        trigger=RuleTrigger.ACTION,
        conditions=["actor.hp > 0"],
        effects=[RuleEffect(type="damage", params={"damage": "1d6"})],
    )
    assert rule.id == "test_rule"
    assert rule.trigger == RuleTrigger.ACTION


def test_game_state_operations():
    """Test game state operations."""
    from src.models import GameState, Item, Location

    state = GameState()

    # Add location
    loc = Location(id="loc1", name="Location 1")
    state.locations["loc1"] = loc

    # Add item
    item = Item(id="item1", name="Item 1")
    state.items["item1"] = item

    # Place item at location
    state.item_locations["item1"] = "loc1"

    # Move player
    state.player_location = "loc1"

    # Query items at location
    items = state.get_items_at_location("loc1")
    assert len(items) == 1
    assert items[0].id == "item1"

    # Move item to player
    state.move_item_to_player("item1")
    assert "item1" in state.player.inventory
    assert "item1" not in state.item_locations
