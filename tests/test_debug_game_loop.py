"""Debug test to see what the game loop is passing to describe_location."""

import pytest
import os
from src.models.game_state import GameState
from src.llm.gemini_client import GeminiClient
from src.engine.game_loop import GameLoop
from src.main import initialize_rule_engine
from unittest.mock import patch


@pytest.fixture
def zork_game():
    game_state = GameState.from_file("worlds/zork_original.json")
    game_state.player_location = "west_of_house"
    return game_state


@pytest.fixture
def components():
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        pytest.skip("GCP_PROJECT not set")

    gemini = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash-lite")
    zil_translator = GeminiClient(project=gcp_project, model_name="gemini-2.5-flash")
    rule_engine = initialize_rule_engine()

    return gemini, zil_translator, rule_engine


def test_debug_what_game_loop_passes(zork_game, components):
    """Intercept the describe_location call to see what data is passed."""
    gemini, zil_translator, rule_engine = components

    game_loop = GameLoop(zork_game, gemini, rule_engine, zil_translator_client=zil_translator)

    # Track what gets passed to describe_location
    captured_args = {}

    original_describe = game_loop.zil_translator.describe_location

    def spy_describe_location(*args, **kwargs):
        """Capture arguments and call original."""
        captured_args['args'] = args
        captured_args['kwargs'] = kwargs

        # Print what we captured
        if args:
            location_dict = args[0]
            print(f"\n=== LOCATION DICT KEYS ===")
            print(f"Location: {location_dict.get('name')}")
            print(f"Attributes keys: {list(location_dict.get('attributes', {}).keys())}")

            has_zil_desc = 'zil_action_description' in location_dict.get('attributes', {})
            print(f"\nHas zil_action_description? {has_zil_desc}")

            if has_zil_desc:
                zil_desc = location_dict['attributes']['zil_action_description']
                print(f"ZIL description length: {len(zil_desc)}")
                print(f"Contains WON-FLAG? {'WON-FLAG' in zil_desc}")

        global_flags = kwargs.get('global_flags')
        print(f"\n=== GLOBAL FLAGS ===")
        print(f"global_flags: {global_flags}")
        print(f"Type: {type(global_flags)}")

        return original_describe(*args, **kwargs)

    with patch.object(game_loop.zil_translator, 'describe_location', side_effect=spy_describe_location):
        result = game_loop.execute_single_step("look")

    print(f"\n=== RESULT ===")
    print(f"Narrative: {result['narrative'][:200]}...")

    # Verify ZIL description was present
    assert captured_args, "describe_location was not called!"

    location_dict = captured_args['args'][0] if captured_args['args'] else None
    assert location_dict, "No location dict passed"

    has_zil = 'zil_action_description' in location_dict.get('attributes', {})
    assert has_zil, "ZIL action description missing from location dict passed to describe_location!"


def test_compare_direct_vs_game_loop_inputs(zork_game, components):
    """Compare what we pass directly vs what game loop passes."""
    gemini, zil_translator, rule_engine = components

    # Direct test approach (like our passing test)
    from src.llm.zil_translator import ensure_zil_translations

    location = zork_game.locations["west_of_house"]
    items = zork_game.get_items_at_location("west_of_house")
    npcs = zork_game.get_npcs_at_location("west_of_house")

    # Direct translation
    location_dict_direct, items_direct, npcs_direct = ensure_zil_translations(
        zil_translator,
        location=location,
        items=items,
        npcs=npcs
    )

    print("\n=== DIRECT TEST APPROACH ===")
    print(f"Location dict type: {type(location_dict_direct)}")
    print(f"Has zil_action_description? {'zil_action_description' in location_dict_direct.get('attributes', {})}")

    # Now see what game loop produces
    game_loop = GameLoop(zork_game, gemini, rule_engine, zil_translator_client=zil_translator)

    # Capture what game loop passes
    captured = {}

    original_describe = game_loop.zil_translator.describe_location

    def capture_describe(*args, **kwargs):
        captured['location_dict'] = args[0] if args else None
        captured['global_flags'] = kwargs.get('global_flags')
        return original_describe(*args, **kwargs)

    with patch.object(game_loop.zil_translator, 'describe_location', side_effect=capture_describe):
        game_loop.execute_single_step("look")

    location_dict_gameloop = captured.get('location_dict')

    print("\n=== GAME LOOP APPROACH ===")
    print(f"Location dict type: {type(location_dict_gameloop)}")
    print(f"Has zil_action_description? {'zil_action_description' in location_dict_gameloop.get('attributes', {})}")

    # Compare
    print("\n=== COMPARISON ===")

    direct_attrs = set(location_dict_direct.get('attributes', {}).keys())
    gameloop_attrs = set(location_dict_gameloop.get('attributes', {}).keys())

    print(f"Attributes in direct but not game loop: {direct_attrs - gameloop_attrs}")
    print(f"Attributes in game loop but not direct: {gameloop_attrs - direct_attrs}")

    # Check if ZIL descriptions match
    if 'zil_action_description' in location_dict_direct.get('attributes', {}):
        direct_zil = location_dict_direct['attributes']['zil_action_description']
        gameloop_zil = location_dict_gameloop.get('attributes', {}).get('zil_action_description', 'MISSING')

        print(f"\nDirect ZIL desc length: {len(direct_zil)}")
        print(f"Game loop ZIL desc length: {len(gameloop_zil) if gameloop_zil != 'MISSING' else 'MISSING'}")

        if gameloop_zil != 'MISSING':
            print(f"Descriptions match? {direct_zil == gameloop_zil}")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
