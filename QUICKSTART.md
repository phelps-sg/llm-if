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
export GCP_LOCATION='us-west1'
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

Try these commands:
- `look` - Examine your surroundings
- `go north` - Move north (or south, east, west)
- `take sword` - Pick up an item
- `inventory` - Check your inventory
- `attack skeleton` - Attack an enemy
- `help` - Show help
- `quit` - Exit

You can also use natural language - the AI will interpret it!

## Example Session

```
> look
You find yourself at the entrance to an ancient dungeon...

> take sword
You pick up the rusty sword...

> go north
You move north into the grand hall...

> attack skeleton
You swing your rusty sword at the skeletal guard...
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
