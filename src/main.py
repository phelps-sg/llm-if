"""Main entry point for the Interactive Fiction Engine."""

import argparse
import json
import os
import sys
from pathlib import Path

from .models.game_state import GameState
from .llm.gemini_client import GeminiClient
from .rules.rule_engine import RuleEngine
from .rules.dnd_rules import get_all_dnd_rules
from .engine.game_loop import GameLoop


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


def initialize_rule_engine() -> RuleEngine:
    """Initialize the rule engine with D&D rules."""
    print("Initializing rule engine...")
    engine = RuleEngine()

    # Load D&D rules
    dnd_rules = get_all_dnd_rules()
    engine.register_rules(dnd_rules)

    print(f"Loaded {len(engine.rules)} rules")
    return engine


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

    return parser


def run_single_step_mode(args, gcp_project: str) -> None:
    """Run game in single-step mode - execute one command and exit."""

    # 1. Load or initialize game state
    if args.no_state:
        # No state mode - must provide --init
        if not args.init:
            print("Error: --no-state requires --init <world_file>")
            print("Example: python -m src.main --single-step --no-state --init worlds/example_dungeon.json --command 'look'")
            sys.exit(1)

        print(f"Initializing fresh game from {args.init} (no state persistence)...")
        if not os.path.exists(args.init):
            print(f"Error: World file not found: {args.init}")
            sys.exit(1)

        game_state = GameState.from_file(args.init)
        print(f"Initialized with {len(game_state.locations)} locations")
    elif args.init:
        # Initialize new game from world file
        print(f"Initializing new game from {args.init}...")
        if not os.path.exists(args.init):
            print(f"Error: World file not found: {args.init}")
            sys.exit(1)

        game_state = GameState.from_file(args.init)
        print(f"Initialized with {len(game_state.locations)} locations")
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
    print(f"Exits: {', '.join(result['exits']) if result['exits'] else 'none'}")

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
    # Get world file
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

    # Load game
    try:
        game_state = load_game(world_file_str)
    except Exception as e:
        print(f"Error loading world: {e}")
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
