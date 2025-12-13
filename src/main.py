"""Main entry point for the Interactive Fiction Engine."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from .models.game_state import GameState
from .llm.gemini_client import GeminiClient
from .rules.rule_engine import RuleEngine
from .rules.dnd_rules import get_all_dnd_rules
from .engine.game_loop import GameLoop
from .utils.logging_config import setup_logging


def load_game(world_file: str) -> GameState:
    """Load a game from a world file."""
    print(f"Loading world from {world_file}...")
    game_state = GameState.from_file(world_file)
    print(
        f"Loaded {len(game_state.locations)} locations, "
        f"{len(game_state.npcs)} NPCs, "
        f"{len(game_state.items)} items"
    )
    return game_state


def apply_start_location_override(game_state: GameState, start_location: str) -> None:
    """Override the player's starting location if specified.

    Args:
        game_state: Game state to modify
        start_location: Location ID to start at

    Raises:
        ValueError: If the location doesn't exist
    """
    if start_location not in game_state.locations:
        available_locations = list(game_state.locations.keys())[:10]  # Show first 10
        error_msg = f"Error: Location '{start_location}' not found in world.\n"
        error_msg += f"Available locations (showing first 10): {', '.join(available_locations)}"
        if len(game_state.locations) > 10:
            error_msg += f"... and {len(game_state.locations) - 10} more"
        raise ValueError(error_msg)

    game_state.player_location = start_location
    print(f"Starting location overridden to: {start_location}")


def initialize_rule_engine() -> RuleEngine:
    """Initialize the rule engine with D&D rules."""
    print("Initializing rule engine...")
    engine = RuleEngine()

    # Load D&D rules
    dnd_rules = get_all_dnd_rules()
    engine.register_rules(dnd_rules)

    print(f"Loaded {len(engine.rules)} rules")
    return engine


def apply_generated_level(
    game_state: GameState, level_data: Dict[str, Any], level_number: int
) -> None:
    """Apply generated level data to game state.

    Args:
        game_state: Game state to modify
        level_data: Generated level data from LLM
        level_number: Level number for metadata tracking
    """
    from .models.location import Location
    from .models.npc import NPC
    from .models.item import Item

    # Add locations
    for loc_data in level_data["locations"]:
        location = Location(
            id=loc_data["id"],
            name=loc_data["name"],
            attributes=loc_data.get("attributes", {}),
            connections=loc_data.get("connections", {}),
        )
        game_state.locations[location.id] = location

    # Add NPCs
    for npc_data in level_data.get("npcs", []):
        npc = NPC(
            id=npc_data["id"],
            name=npc_data["name"],
            attributes=npc_data.get("attributes", {}),
        )
        game_state.npcs[npc.id] = npc

    # Add items
    for item_data in level_data.get("items", []):
        item = Item(
            id=item_data["id"],
            name=item_data["name"],
            attributes=item_data.get("attributes", {}),
        )
        game_state.items[item.id] = item

    # Set locations
    game_state.npc_locations.update(level_data.get("npc_locations", {}))
    game_state.item_locations.update(level_data.get("item_locations", {}))

    # Track metadata in rogue_config
    if game_state.rogue_config:
        game_state.rogue_config["level_metadata"][str(level_number)] = {
            "entry_location_id": level_data["entry_location_id"],
            "exit_location_id": level_data["exit_location_id"],
            "generated_locations": [loc["id"] for loc in level_data["locations"]],
            "generated_npcs": [npc["id"] for npc in level_data.get("npcs", [])],
            "generated_items": [item["id"] for item in level_data.get("items", [])],
            "theme": level_data.get("theme", "unknown"),
            "difficulty": level_number,
        }


def initialize_rogue_mode(args, gcp_project: str) -> GameState:
    """Initialize fresh game in rogue mode with procedurally generated Level 1.

    Args:
        args: CLI arguments containing genre, plot, specifics
        gcp_project: GCP project ID for LLM

    Returns:
        GameState with generated level 1
    """
    from .llm.gemini_client import GeminiClient
    from .models.player import Player

    # Prompt for genre if not provided
    if not args.genre:
        print("\n" + "=" * 60)
        print("ROGUE MODE - PROCEDURAL DUNGEON GENERATION")
        print("=" * 60)
        print("\nExamples: dark fantasy, sci-fi horror, ancient ruins, space opera")
        genre = input("\nGenre/Theme: ").strip() or "dark fantasy"

        plot = input("Optional plot/goal (press Enter to skip): ").strip() or None
        specifics = input("Specific requests (press Enter to skip): ").strip() or None

        args.genre = genre
        args.plot = plot if plot else None
        args.specifics = specifics if specifics else None

    print("\n" + "=" * 60)
    print(f"GENERATING LEVEL 1 - {args.genre.upper()}")
    print("=" * 60)

    # Initialize LLM client
    gemini = GeminiClient(project=gcp_project)

    # Generate first level
    level_data = gemini.generate_dungeon_level(
        level_number=1,
        genre=args.genre,
        plot=args.plot,
        specifics=args.specifics,
        difficulty_modifier=1.0,
        num_middle_locations=args.num_locations,
        num_npcs=args.num_npcs,
        num_items=args.num_items,
    )

    # Create minimal GameState with player
    game_state = GameState(
        locations={},
        npcs={},
        items={},
        player=Player(
            name="Adventurer",
            attributes={
                "class": "fighter",
                "level": 1,
                "hp": 20,
                "hp_max": 20,
                "armor_class": 14,
                "attack_bonus": 5,
                "str": 16,
                "dex": 12,
                "con": 14,
                "int": 10,
                "wis": 11,
                "cha": 9,
            },
            inventory=[],
        ),
        rogue_config={
            "enabled": True,
            "genre": args.genre,
            "plot": args.plot,
            "specifics": args.specifics,
            "current_level": 1,
            "level_metadata": {},
            "max_level": None,
            "num_middle_locations": args.num_locations,
            "num_npcs": args.num_npcs,
            "num_items": args.num_items,
        },
        npc_locations={},
        item_locations={},
        player_location="",
    )

    # Apply generated level
    apply_generated_level(game_state, level_data, level_number=1)

    # Set player at entry
    game_state.player_location = level_data["entry_location_id"]

    print(f"\n✓ Level 1 generated!")
    print(f"  Theme: {level_data['theme']}")
    print(f"  Locations: {len(level_data['locations'])}")
    print(f"  NPCs: {len(level_data.get('npcs', []))}")
    print(f"  Items: {len(level_data.get('items', []))}")
    print("=" * 60 + "\n")

    return game_state


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Interactive Fiction Engine - LLM-powered text adventure"
    )

    parser.add_argument(
        "world_file",
        nargs="?",
        help="World file to load (JSON format)",
    )

    parser.add_argument(
        "--single-step",
        action="store_true",
        help="Execute single command and exit (for testing)",
    )

    parser.add_argument(
        "--command",
        type=str,
        help="Command to execute in single-step mode",
    )

    parser.add_argument(
        "--state-file",
        type=str,
        default="saves/game_state.json",
        help="Path to save/load game state (default: saves/game_state.json)",
    )

    parser.add_argument(
        "--no-state",
        action="store_true",
        help="Run without state persistence (single-step mode only)",
    )

    parser.add_argument(
        "--init",
        type=str,
        help="Initialize new game from world file (single-step mode only)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Output full state dump for debugging",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging output",
    )

    # Rogue mode arguments
    parser.add_argument(
        "--game-mode",
        type=str,
        choices=["standard", "rogue"],
        default="standard",
        help="Game mode: standard (load world file) or rogue (procedural generation)",
    )

    parser.add_argument(
        "--genre",
        type=str,
        help="Genre for rogue mode (e.g., 'dark fantasy', 'sci-fi horror')",
    )

    parser.add_argument(
        "--plot",
        type=str,
        help="Plot guidance for rogue mode (e.g., 'escape the depths')",
    )

    parser.add_argument(
        "--specifics",
        type=str,
        help="Specific requests for rogue mode (e.g., 'undead enemies', 'puzzle-focused')",
    )

    # Rogue mode dungeon size configuration
    parser.add_argument(
        "--num-locations",
        type=int,
        default=3,
        help="Number of middle locations to generate (default: 3, total will be +2 for entry/exit)",
    )

    parser.add_argument(
        "--num-npcs",
        type=int,
        default=2,
        help="Number of NPCs to generate per level (default: 2)",
    )

    parser.add_argument(
        "--num-items",
        type=int,
        default=3,
        help="Number of items to generate per level (default: 3)",
    )

    parser.add_argument(
        "--start-location",
        type=str,
        help="Override starting location (location ID) - useful for testing specific areas",
    )

    return parser


def run_single_step_mode(args, gcp_project: str) -> None:
    """Run game in single-step mode - execute one command and exit."""

    # 1. Load or initialize game state
    if args.no_state:
        # No state mode - must provide --init or use rogue mode
        if args.game_mode == "rogue":
            print("Initializing rogue mode (no state persistence)...")
            game_state = initialize_rogue_mode(args, gcp_project)
        elif args.init:
            print(f"Initializing fresh game from {args.init} (no state persistence)...")
            if not os.path.exists(args.init):
                print(f"Error: World file not found: {args.init}")
                sys.exit(1)
            game_state = GameState.from_file(args.init)
            print(f"Initialized with {len(game_state.locations)} locations")

            # Apply start location override if specified
            if args.start_location:
                try:
                    apply_start_location_override(game_state, args.start_location)
                except ValueError as e:
                    print(str(e))
                    sys.exit(1)
        else:
            print("Error: --no-state requires --init <world_file> or --game-mode rogue")
            print("Example: python -m src.main --single-step --no-state --init worlds/example_dungeon.json --command 'look'")
            sys.exit(1)
    elif args.init:
        # Initialize new game from world file
        print(f"Initializing new game from {args.init}...")
        if not os.path.exists(args.init):
            print(f"Error: World file not found: {args.init}")
            sys.exit(1)

        game_state = GameState.from_file(args.init)
        print(f"Initialized with {len(game_state.locations)} locations")

        # Apply start location override if specified
        if args.start_location:
            try:
                apply_start_location_override(game_state, args.start_location)
            except ValueError as e:
                print(str(e))
                sys.exit(1)
    elif args.game_mode == "rogue":
        # Rogue mode: try to load existing state, otherwise initialize
        if os.path.exists(args.state_file):
            print(f"Loading saved rogue game from {args.state_file}...")
            game_state = GameState.from_file(args.state_file)
        else:
            print("Initializing new rogue mode game...")
            game_state = initialize_rogue_mode(args, gcp_project)
    else:
        # Load existing state
        if not os.path.exists(args.state_file):
            print(f"Error: No saved state at {args.state_file}")
            print(f"Use --init <world_file> to start new game")
            print(f"Example: python -m src.main --single-step --init worlds/example_dungeon.json --command 'look'")
            sys.exit(1)

        print(f"Loading saved state from {args.state_file}...")
        game_state = GameState.from_file(args.state_file)

    # 2. Validate command
    if not args.command:
        print("Error: --command required in single-step mode")
        print("Example: python -m src.main --single-step --command 'take sword'")
        sys.exit(1)

    # 3. Initialize game components
    print("Initializing game engine...")
    gemini = GeminiClient(project=gcp_project)
    rule_engine = initialize_rule_engine()
    game_loop = GameLoop(game_state, gemini, rule_engine)

    # 4. Execute single command
    print(f"Executing command: {args.command}")
    try:
        result = game_loop.execute_single_step(args.command)
    except Exception as e:
        print(f"Error executing command: {e}")
        import traceback
        traceback.print_exc()

        # Save state anyway (even on error)
        os.makedirs(os.path.dirname(args.state_file) or ".", exist_ok=True)
        game_state.to_file(args.state_file)
        print(f"State saved to {args.state_file}")
        sys.exit(1)

    # 5. Save state (unless --no-state)
    if not args.no_state:
        os.makedirs(os.path.dirname(args.state_file) or ".", exist_ok=True)
        game_state.to_file(args.state_file)

    # 6. Output result
    print("\n" + "=" * 60)
    print(f"Command: {args.command}")
    print("=" * 60)
    print(f"\n{result['narrative']}\n")

    location = result['location']
    print(f"Location: {location['name']} ({location['id']})")

    if result['inventory']:
        print(f"Inventory: {', '.join(result['inventory'])}")
    else:
        print("Inventory: empty")

    print(f"Turn: {result['turn_count']}")

    if not args.no_state:
        print(f"\nState saved to: {args.state_file}")
    else:
        print("\n(No state saved - running in no-state mode)")

    # 7. Debug output (optional)
    if args.debug:
        print("\n" + "=" * 60)
        print("DEBUG: Full State")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))

    # 8. Exit successfully
    sys.exit(0)


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()

    # Initialize logging based on verbose flag
    setup_logging(verbose=args.verbose)

    # Get GCP project (required for Vertex AI)
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        print("Error: GCP_PROJECT environment variable not set")
        print("Please set it with: export GCP_PROJECT='your-project-id'")
        sys.exit(1)

    # Single-step mode
    if args.single_step:
        run_single_step_mode(args, gcp_project)
        return  # Never reached (exits in function)

    # Normal interactive mode
    # Load game based on mode
    try:
        if args.game_mode == "rogue":
            # Rogue mode - procedural generation
            game_state = initialize_rogue_mode(args, gcp_project)
        else:
            # Standard mode - load world file
            world_file_str: str
            if args.world_file:
                world_file_str = args.world_file
            else:
                # Default to example dungeon
                world_file_path = (
                    Path(__file__).parent.parent / "worlds" / "example_dungeon.json"
                )
                world_file_str = str(world_file_path)

            if not os.path.exists(world_file_str):
                print(f"Error: World file not found: {world_file_str}")
                sys.exit(1)

            game_state = load_game(world_file_str)

            # Apply start location override if specified
            if args.start_location:
                apply_start_location_override(game_state, args.start_location)
    except Exception as e:
        print(f"Error initializing game: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Initialize components
    try:
        print("Initializing Gemini client...")
        gemini = GeminiClient(project=gcp_project)

        rule_engine = initialize_rule_engine()

        # Create game loop
        game = GameLoop(game_state, gemini, rule_engine)

        # Start game
        game.start()

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
