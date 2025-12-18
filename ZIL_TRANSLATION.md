# ZIL Translation System

This document explains the on-demand ZIL code translation system that helps the DM (LLM) understand game mechanics from classic Infocom games.

## Overview

The system automatically translates ZIL (Zork Implementation Language) code into natural language descriptions as needed during gameplay. Translations are cached to disk to avoid redundant LLM calls.

## How It Works

### 1. On-Demand Translation
When the game loop encounters an entity (location, item, or NPC) with ZIL code:
1. Check if translation already exists in cache
2. If not cached, translate using LLM and store in cache
3. Translation is immediately available for DM prompts

### 2. Cache System
- **Location**: `.cache/zil_translations/translations.json`
- **Key**: SHA256 hash of ZIL code (identical code = same translation)
- **Value**: Translation + metadata (routine name, context, timestamp)
- **Persistence**: Survives across game sessions
- **Thread-safe**: Uses locking for concurrent access

### 3. Integration Points

#### Game Loop (`src/engine/game_loop.py`)
- **process_turn()**: Translates ZIL before interpreting player actions
- **execute_single_step()**: Translates before generating location descriptions
- **_display_location()**: Translates before describing locations

#### LLM Prompts (`src/llm/gemini_client.py`)
- **_build_zil_interpretation_hints()**: Prefers `zil_action_description` over raw ZIL code
- Provides fallback interpretation guide for untranslated ZIL

## Usage

### Automatic (Default Behavior)
The system works automatically during gameplay. When the player enters a location with ZIL code:

```python
# Game loop automatically calls:
ensure_zil_translations(
    llm_client,
    location=current_location,
    items=items_here,
    npcs=npcs_here
)
```

### Manual Translation (ZIL Converter)
To pre-translate during world conversion:

```bash
poetry run python -m tools.zil_converter \
  ../zork1/ \
  -o worlds/zork.json \
  --translate-zil \
  --model gemini-2.5-flash
```

**Note**: Pre-translation can be very slow for large games. On-demand translation is recommended.

### Programmatic Access

```python
from llm.gemini_client import GeminiClient
from llm.zil_translation_cache import get_cache

client = GeminiClient(model_name="gemini-2.5-flash")

# Translate with caching
description = client.translate_zil_with_cache(
    zil_code='<ROUTINE "TEST-F" ...>',
    routine_name="TEST-F",
    context="location action"
)

# Check cache
cache = get_cache()
if cache.has(zil_code):
    print("Translation cached!")

# Get stats
stats = cache.get_stats()
print(f"Cache has {stats['entries']} translations")
```

## Cache Management

### Inspect Cache
```bash
cat .cache/zil_translations/translations.json | python -m json.tool | less
```

### Clear Cache
```python
from llm.zil_translation_cache import get_cache
get_cache().clear()
```

Or manually:
```bash
rm -rf .cache/zil_translations/
```

### Cache Statistics
```python
from llm.zil_translation_cache import get_cache
stats = get_cache().get_stats()
print(f"Entries: {stats['entries']}")
print(f"Size: {stats['file_size_mb']} MB")
```

## Data Structure

### World JSON (Existing)
```json
{
  "locations": {
    "underwater": {
      "attributes": {
        "zil_action": "UNDERWATER-F",
        "zil_action_code": "<ROUTINE \"UNDERWATER-F\" ...>",
        "zil_action_json": {...}
      }
    }
  }
}
```

### Cache File
```json
{
  "6a0f482f...": {
    "translation": "This routine triggers at the end of each turn...",
    "routine_name": "UNDERWATER-F",
    "context": "location action for 'Underwater'",
    "cached_at": "2025-12-18T13:40:06.953733",
    "zil_length": 234
  }
}
```

### World JSON (After Translation)
```json
{
  "locations": {
    "underwater": {
      "attributes": {
        "zil_action": "UNDERWATER-F",
        "zil_action_code": "<ROUTINE \"UNDERWATER-F\" ...>",
        "zil_action_json": {...},
        "zil_action_description": "This routine triggers at the end of each turn..."
      }
    }
  }
}
```

**Note**: The `zil_action_description` is added to entity attributes in-memory during gameplay, not persisted to world.json.

## Architecture

### Files
- **`src/llm/zil_translation_cache.py`**: Cache manager
- **`src/llm/zil_translator.py`**: Translation utilities
- **`src/llm/gemini_client.py`**: LLM client with translation method
- **`src/engine/game_loop.py`**: Integration point

### Flow
```
Player Action
    ↓
Game Loop builds context
    ↓
ensure_zil_translations()
    ↓
For each entity with ZIL:
    ↓
Check cache → HIT: use cached translation
    ↓         → MISS: translate with LLM → cache result
    ↓
Add translation to entity.attributes["zil_action_description"]
    ↓
LLM receives context with translations
    ↓
LLM prefers natural language over raw ZIL
```

## Example Translation

### Input (ZIL)
```zil
<ROUTINE "UNDERWATER-F" ("RARG")
  ("COND" (("EQUAL?" ".RARG" ",M-END")
           ("SETG" "DROWN" ("+" ",DROWN" 1))
           ("COND" (("G?" ",DROWN" 2)
                    ("JIGS-UP" "A mighty undertow drags you...")))))>
```

### Output (Natural Language)
```
This routine triggers at the end of each turn when the player is in this location.
It increments a DROWN counter each turn. If the DROWN counter exceeds 2, the player
dies with the message "A mighty undertow drags you across some underwater obstructions."
This creates a time pressure - the player must leave the underwater location quickly
or drown.
```

## Benefits

1. **No Pre-Processing Required**: Translate only what's needed during gameplay
2. **Fast**: Cache ensures each ZIL snippet is translated only once
3. **Persistent**: Cache survives across game sessions
4. **Transparent**: Works automatically without code changes
5. **DM-Friendly**: Natural language helps LLM understand game mechanics
6. **Robust**: Separate cache file keeps world.json clean

## Performance

- **First encounter**: ~1-2 seconds per routine (LLM call)
- **Subsequent encounters**: <1ms (cache lookup)
- **Cache size**: ~500-1000 bytes per translation
- **Zork I**: ~200 routines = ~100-200 KB cache

## Testing

Run the test suite:
```bash
python test_zil_cache.py
```

Expected output:
```
✅ All tests passed!
🎉 All ZIL cache tests passed!
```

## Troubleshooting

### Translations Not Working
1. Check LLM client is initialized with Gemini
2. Verify GCP credentials are set up
3. Check cache directory is writable

### Cache Not Persisting
1. Check `.cache/zil_translations/` directory exists
2. Verify write permissions
3. Check for disk space

### Translations Seem Wrong
1. Clear cache and re-translate
2. Try different model (e.g., gemini-2.5-pro for complex ZIL)
3. Check ZIL code is well-formed

## Future Enhancements

- [ ] Batch translation API for bulk processing
- [ ] Cache invalidation based on game version
- [ ] Translation quality metrics
- [ ] Support for other retro IF languages (TADS, Inform, etc.)
