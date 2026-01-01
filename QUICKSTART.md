# Quick Start Guide

Get the MVP running in 3 steps:

## 1. Install Dependencies

```bash
poetry install
```

Or using pip:
```bash
pip install -r requirements.txt
```

## 2. Authenticate with GCP

This uses your gcloud CLI authentication (no API keys needed!):

```bash
# Authenticate with gcloud (one-time setup)
gcloud auth login
gcloud auth application-default login

# Set environment variables
export GCP_PROJECT='your-gcp-project-id'
export GCP_LOCATION='your-gcp-region'
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and set GCP_PROJECT and GCP_LOCATION
```

## 3. Run the Game

Using Poetry:
```bash
poetry run python -m src.main
```

Or use the convenience script:
```bash
poetry run if-engine
```

Or specify a custom world:
```bash
poetry run python -m src.main worlds/example_dungeon.json
```

Without Poetry:
```bash
python -m src.main
```

## Playing the Game

### Interactive Mode

Try these commands:
- `look` - Examine your surroundings
- `go north` - Move north (or south, east, west)
- `take sword` - Pick up an item
- `inventory` - Check your inventory
- `attack skeleton` - Attack an enemy
- `talk to genie` - Speak with NPCs (they'll respond with dialogue!)
- `greet deer` - Interact with creatures
- `save` - Save your game (default: saves/quicksave.json)
- `load` - Load your saved game
- `help` - Show help
- `quit` - Exit

You can also use natural language - the AI will interpret it!

### Single-Step Mode (Testing & Automation)

Run the game one command at a time with state persistence:

```bash
# Initialize a new game
python -m src.main --single-step --init worlds/example_dungeon.json --command "look"

# Execute subsequent commands (loads from saves/game_state.json)
python -m src.main --single-step --command "go north"
python -m src.main --single-step --command "take sword"

# Use custom save file
python -m src.main --single-step --state-file saves/test1.json --command "inventory"

# Run without state persistence (fresh game each time)
python -m src.main --single-step --no-state --init worlds/example_dungeon.json --command "look"

# Debug mode (show full state)
python -m src.main --single-step --command "look" --debug
```

Perfect for:
- Automated testing and CI/CD
- Systematic bug reproduction
- Scripted game sequences
- State inspection between commands

## Command-Line Options

### Text Width

Control the width of text output for better readability on different terminal sizes:

```bash
# Default width (80 characters)
poetry run if-engine worlds/zork_original.json

# Narrow terminal (60 characters)
poetry run if-engine worlds/zork_original.json --text-width 60

# Wide terminal (120 characters)
poetry run if-engine worlds/zork_original.json --text-width 120

# Works with single-step mode too
python -m src.main --single-step --text-width 100 --command "look"
```

### Other Options

```bash
# Start at specific location (for testing)
poetry run if-engine worlds/zork_original.json --start-location kitchen

# Enable verbose debug logging
poetry run if-engine worlds/zork_original.json --verbose

# Rogue mode (procedural generation)
poetry run if-engine --game-mode rogue --genre "dark fantasy" --plot "escape the depths"
```

## Example Session

```
> look
You peer into the gloom of the dungeon entrance. Moss-covered stone walls rise
around you, meeting in an ancient, arched doorway. A rusty sword and a burning
torch lie discarded on the cold, damp ground nearby.

> take torch
You reach down and grab the torch. The warmth radiates through your hand, a
stark contrast to the dungeon's chill.

> go south
You step out into a peaceful forest clearing. Dappled sunlight filters through
tall ancient trees. A pristine white deer grazes nearby, and an Ancient Genie
shimmers in the air, its blue ethereal form adorned with golden armlets.

> talk to genie
As you approach the Ancient Genie, its shimmering blue form solidifies.
"Greetings, mortal," the genie booms, its voice echoing through the forest
clearing. "I am bound by ancient law to grant three wishes to those who find
me, but heed my words: I grant exactly what is asked, no more, no less.
Choose wisely!"

> wish for a magic sword
The air crackles with arcane energy as the Ancient Genie gestures towards you.
A gleaming blade materializes in your hand, its hilt wrapped in dragonhide,
pulsing with arcane light.
```

## Troubleshooting

**Missing GCP_PROJECT**: Make sure `GCP_PROJECT` is set in your environment

**gcloud not found**: Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install

**Authentication errors**: Run `gcloud auth login` and `gcloud auth application-default login`

**Import Errors**: Make sure you're running from the project root and using `poetry run python -m src.main`

**Model Errors**: The default model is `gemini-2.0-flash-001`. Other options: `gemini-2.5-flash` (latest, Nov 2025). Change in `src/llm/gemini_client.py` if needed

## Next Steps

- Edit `worlds/example_dungeon.json` to customize the world
- Add new rules in `worlds/rules/`
- Modify prompts in `src/llm/gemini_client.py`
- Implement new action types in `src/engine/action_processor.py`
