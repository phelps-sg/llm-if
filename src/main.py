"""Main entry point for the Interactive Fiction Engine."""

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


def main() -> None:
    """Main entry point."""
    # Get GCP project (required for Vertex AI)
    gcp_project = os.getenv("GCP_PROJECT")
    if not gcp_project:
        print("Error: GCP_PROJECT environment variable not set")
        print("Please set it with: export GCP_PROJECT='your-project-id'")
        sys.exit(1)

    # Get world file
    world_file_str: str
    if len(sys.argv) > 1:
        world_file_str = sys.argv[1]
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
