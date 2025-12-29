# AI-Powered Interactive Fiction Engine

**Remaster classic Infocom games with genuine AI narration, or create entirely new worlds**—all while maintaining perfect consistency through retrieval-augmented generation.

## The Problem with Pure LLM Interactive Fiction

Modern LLMs can simulate text adventure games entirely in conversation:

```
You: "Let's play a text adventure. I'm in a dungeon."
LLM: "You stand in a dark dungeon. There's a sword on the ground."
You: "I take the sword and go north."
LLM: "You pick up the sword and head north into a grand hall."
You: "I go back south."
LLM: "You return to the dungeon. There's a shield on the ground."  ← HALLUCINATION
```

**Problems:**
1. **Hallucination**: The sword disappeared, a shield appeared from nowhere
2. **Context Loss**: Conversations exceed context windows, losing critical state
3. **Inconsistency**: Same location described differently each visit
4. **No Mechanics**: Can't enforce rules like combat, puzzles, or inventory limits

## Our Solution: Retrieval-Augmented Generation (RAG)

This engine treats the LLM as a **Dungeon Master**, not a game engine. The LLM narrates, but doesn't store state:

```
┌─────────────────────────────────────────────────┐
│  STRUCTURED GAME STATE (Source of Truth)       │
│  ┌──────────────────────────────────────────┐  │
│  │ Locations: {"dungeon": {...}, "hall": {..}} │
│  │ Items: {"sword": {location: "dungeon"}}  │  │
│  │ Player: {location: "dungeon", inventory: []} │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  LLM (Dungeon Master)   │
         │  Narrates from state    │
         └─────────────────────────┘
                      │
                      ▼
         "You stand in a dark dungeon.
          A rusty sword lies at your feet."
```

**Benefits:**
- **Perfect Consistency**: Same state = same world, always
- **No Hallucination**: LLM only describes what exists in state
- **Unlimited History**: State persists across any number of turns
- **Enforced Mechanics**: Rules engine handles combat, puzzles, inventory
- **Reproducibility**: Same actions = same outcomes

## The Killer Feature: ZIL Import & AI Remastering

We go beyond static JSON worlds. The engine **imports original Infocom game source code** (ZIL - Zork Implementation Language) and **translates procedural logic into natural language** on-demand:

### How It Works

1. **Import Original ZIL**: Load authentic Infocom game source (Zork, Planetfall, Trinity, etc.)
2. **Convert to Structured State**: Extract locations, items, NPCs, relationships
3. **On-Demand Translation**: When LLM needs logic, translate ZIL routines to natural language
4. **Caching**: Translations cached for performance
5. **Manual Overrides**: Enhance specific behaviors without touching base data

**Example - Trinity Coin Description:**

```zil
; Original ZIL Code (things.zil:298)
<ROUTINE COIN-F ()
  <COND (<VERB? EXAMINE>
         <TELL "It's standard British currency, worth fifty pence">)>>
```

↓ **Automatic Translation** ↓

```
examine_text: "It's standard British currency, worth fifty pence"
```

↓ **LLM Receives** ↓

The LLM narrates naturally while staying true to the original:
```
> examine coin
You withdraw the curious seven-sided coin from your pocket.
It's standard British currency, worth fifty pence.
```

### Why This Matters

- **Authentic Experience**: Original Infocom game logic preserved
- **AI Enhancement**: Modern LLM narration brings classics to life
- **Best of Both Worlds**: Classic game design + contemporary AI storytelling
- **Extensible**: Override specific behaviors without breaking imports

## Core Features

### 🎮 ZIL Converter & Import System
Convert original Infocom game source code to playable JSON:
- **Automatic extraction**: Locations, items, NPCs, relationships
- **Smart pattern matching**: Recognizes common ZIL patterns
- **Multi-game support**: Zork, Planetfall, Trinity, and more
- **Preservation**: ZIL code embedded for reference and translation
- **Manual enhancement**: Override system for custom improvements

**Example Usage:**
```bash
python -m tools.zil_converter ~/zork1 --output worlds/zork.json
```

### 🔧 Override System (Source-Agnostic)
Manually enhance imported games without modifying base data:
- **Persistent overrides**: Survives re-imports from ZIL
- **Merge at runtime**: `trinity.json` + `trinity_overrides.json` = final world
- **Any game source**: Works for ZIL imports, manual JSON, or procedural generation
- **Structured enhancements**: Add examine text, NPC dialog, triggers, purchasables

**Example - Trinity Override:**
```json
{
  "items": {
    "coin": {
      "examine_text": "It's standard British currency, worth fifty pence."
    },
    "crumbs": {
      "purchasable": {
        "price": 30,
        "seller_npc": "bwoman",
        "dialog": {
          "ask_price": "Thirty p! Thirty p a bag!"
        }
      }
    }
  },
  "npcs": {
    "bwoman": {
      "ambient_phrases": [
        "Thirty p! Thirty p a bag!",
        "Feed the hungry birds!"
      ]
    }
  }
}
```

### ⚡ God Mode (Developer Debugging)
Powerful introspection and debugging tools:
- **Inspection commands**: `/inspect <entity>`, `/inventory`, `/state`, `/context`
- **DM debug questions**: `DM: why isn't the coin visible?` → AI analyzes game state
- **Works everywhere**: Interactive mode and single-step mode
- **State transparency**: See exactly what the LLM sees

**Example Session:**
```bash
poetry run python -m src.main worlds/trinity.json --god-mode

> /inspect coin
=== ITEM: coin (seven-sided coin) ===
Location: pocket
{
  "examine_text": "It's standard British currency, worth fifty pence.",
  "zil_action": "COIN-F",
  ...
}

> DM: why does the coin have a custom examine text?
[God Mode Debug Response]
The examine_text field is from trinity_overrides.json, which takes
precedence over the base trinity.json. This override was added to
provide the authentic Infocom description from COIN-F routine...
```

### 🔄 On-Demand ZIL Translation
Translate ZIL routines to natural language only when needed:
- **Lazy translation**: Only translate referenced code
- **Persistent caching**: Translations saved to `.cache/zil_translations/`
- **LLM-powered**: Gemini translates ZIL logic to readable descriptions
- **Performance**: Cached translations reused across sessions

### 🎭 Personality-Driven NPC Dialogue
NPCs speak with quoted dialogue that reflects their personality:
- **Genie**: Mystical, formal dialogue explaining wish mechanics
- **Guards**: Threatening, hostile warnings
- **Creatures**: Behavior-based responses (passive animals, defensive beasts)
- **Dialogue teaches mechanics**: Game rules explained through character voice

### ⚔️ D&D 5e Combat System
Full tactical combat with transparent mechanics:
- Attack rolls, damage calculation, armor class
- Real-time combat narration
- NPC counterattacks based on hostility
- Complete combat logging with dice rolls visible

### 🧞 Dynamic Wish System
Reality-bending genie mechanics:
- Create items, NPCs, or locations dynamically
- Wish tracking with decremented counter
- Precise fulfillment (grants exactly what is asked)
- State validation to prevent exploits

### 💡 Intelligent Lighting System
Context-aware descriptions based on light levels:
- **Pitch black**: Only sounds, smells, sensations
- **Dark**: Vague shapes and outlines
- **Dim**: Limited visibility with shadows
- **Bright**: Full detailed descriptions
- **Dynamic**: Outdoor lighting changes with time of day

### 🔍 Container Visibility System
Sophisticated container and inventory handling:
- **Open containers**: Contents visible when opened
- **Transparent containers**: Glass bottles show contents even when closed
- **Nested containers**: Pocket → coin, credit card (Trinity-style)
- **ZIL flag support**: Auto-detects `opened`, `transbit`, `container` flags

### 🚫 Blocked Exit System
Permanent blocked exits with narrative explanations:
- Custom blocking messages ("Only Santa Claus climbs down chimneys")
- Imported from ZIL conditional exits
- Maintains immersion with contextual feedback

### 🎲 Procedural Rogue Mode
Generate entire dungeons on-the-fly:
- **Genre-driven**: Dark fantasy, sci-fi horror, ancient ruins
- **Plot guidance**: "escape the depths", "find the artifact"
- **Configurable**: Control location count, NPC density, item distribution
- **Coherent generation**: LLM creates interconnected levels

### 🧪 Single-Step Testing Mode
Command-line mode for systematic testing:
- Execute one command at a time
- State persistence between commands
- Custom save file locations
- Perfect for CI/CD integration

### 📊 Token Optimization & Dry Run
Performance monitoring and cost analysis:
- **Token tracking**: Monitor API usage per call
- **Dry run mode**: Estimate costs without API calls
- **Implicit caching**: Optimized prompts for Gemini context caching
- **Compact topology**: Efficient state representation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   WORLD SOURCES                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ZIL Import   │  │ Manual JSON  │  │  Procedural  │      │
│  │  (Trinity)   │  │   (Custom)   │  │  (Rogue LLM) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┼──────────────────┘               │
│                           ▼                                  │
│                  ┌─────────────────┐                         │
│                  │  Override Merge │                         │
│                  └────────┬────────┘                         │
└───────────────────────────┼──────────────────────────────────┘
                            ▼
              ┌──────────────────────────┐
              │   GAME STATE (RAG Core)  │
              │  Structured JSON World   │
              └──────────┬───────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌─────────────┐
    │ Player  │   │  Action  │   │    Rule     │
    │  Input  │──>│Processor │──>│   Engine    │
    └─────────┘   └─────┬────┘   └──────┬──────┘
                        │                │
                        └────────┬───────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  LLM (Dungeon Master)   │
                    │   Context: Relevant     │
                    │   state slice only      │
                    └────────┬────────────────┘
                             ▼
                       ┌──────────┐
                       │Narrative │
                       │ Output   │
                       └──────────┘
```

## Key Design Principles

### 1. Separation of State and Presentation
- Game state is pure structured data
- All descriptions generated dynamically by LLM
- Same state can be rendered different ways based on context

### 2. LLM as Narrative Layer Only
- LLM never stores state
- LLM doesn't make mechanical decisions (dice rolls, outcomes)
- LLM interprets and narrates, doesn't adjudicate

### 3. Retrieval-Augmented Generation
- LLM receives **relevant state slice** (not entire world)
- Recent history for narrative continuity
- Context window optimized for Gemini caching
- No hallucination - everything grounded in state

### 4. Deterministic Core, Creative Surface
- Game mechanics are deterministic and testable
- Narrative is creative and contextual
- Clear boundary between the two

### 5. Source-Agnostic World Model
- Works with ZIL imports, manual JSON, procedural generation
- Override system preserves enhancements across re-imports
- Unified model for all game sources

## Technology Stack

- **Language**: Python 3.11+
- **LLM Provider**: Google Gemini (Vertex AI)
- **ZIL Parser**: Custom S-expression parser
- **Dependencies**:
  - `google-cloud-aiplatform`: Vertex AI SDK
  - `pydantic`: Data validation and schema
  - `click`: CLI framework
  - Standard library: `json`, `random`, `typing`, `textwrap`

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/llm-if
cd llm-if

# Install dependencies
poetry install

# Set up Google Cloud credentials
export GCP_PROJECT=your-project-id
gcloud auth application-default login
```

### Play an Imported Classic

```bash
# Play Trinity (imported from original ZIL)
poetry run python -m src.main worlds/trinity.json

# Or Zork
poetry run python -m src.main worlds/zork_original.json

# With god mode for debugging
poetry run python -m src.main worlds/trinity.json --god-mode
```

### Import Your Own ZIL Game

```bash
# Convert ZIL source to playable JSON
python -m tools.zil_converter ~/path/to/zil_source --output worlds/mygame.json

# Play it
poetry run python -m src.main worlds/mygame.json
```

### Create Manual Overrides

```bash
# Create override file
cp worlds/trinity_overrides.json worlds/mygame_overrides.json

# Edit with your enhancements
vim worlds/mygame_overrides.json

# Overrides auto-merge at runtime
poetry run python -m src.main worlds/mygame.json
```

### Generate a Procedural Dungeon

```bash
# Rogue mode - generate on the fly
poetry run python -m src.main \
  --game-mode rogue \
  --genre "dark fantasy" \
  --plot "escape the ancient catacombs" \
  --num-locations 5
```

## Usage Examples

### Interactive Gameplay

```
$ poetry run python -m src.main worlds/trinity.json

Sharp words between the superpowers. Tanks in East Berlin...

A tide of people surges north along the crowded Broad Walk.
Shaded glades stretch away to the northeast...

> inventory
You are carrying:
  - your pocket
  - wristwatch

> look in pocket
You reach into your pocket. Inside, you find a seven-sided coin
and your credit card.

> examine coin
It's standard British currency, worth fifty pence.
```

### God Mode Debugging

```
$ poetry run python -m src.main worlds/trinity.json --god-mode

⚡ GOD MODE ACTIVE ⚡
Special commands: /inspect, /inventory, /state, DM: <question>

> /inspect coin

=== ITEM: coin (seven-sided coin) ===
Location: pocket
{
  "examine_text": "It's standard British currency, worth fifty pence.",
  "zil_action": "COIN-F",
  "zil_flags": ["takeable"]
}

> DM: why is the coin in a nested container?

[God Mode Debug Response]
The coin's location is "pocket" in item_locations, which means it's
inside the pocket container. Trinity uses nested containers for
realistic inventory - items don't float in abstract inventory space.
The pocket is marked with "container" and "opened" in zil_flags...
```

### Single-Step Testing

```bash
# Initialize new game
poetry run python -m src.main worlds/zork.json \
  --single-step \
  --init worlds/zork.json \
  --command "look"

# Execute commands sequentially
poetry run python -m src.main worlds/zork.json \
  --single-step \
  --command "go north"

poetry run python -m src.main worlds/zork.json \
  --single-step \
  --command "take sword"
```

## Project Structure

```
llm-if/
├── README.md
├── pyproject.toml
├── src/
│   ├── main.py                    # Entry point
│   ├── models/
│   │   ├── game_state.py          # RAG core - state management
│   │   ├── location.py            # Location model
│   │   ├── npc.py                 # NPC model
│   │   ├── item.py                # Item model
│   │   └── player.py              # Player model
│   ├── engine/
│   │   ├── game_loop.py           # Main orchestration
│   │   ├── action_processor.py    # Action pipeline
│   │   └── god_mode.py            # Debug/inspection tools
│   ├── llm/
│   │   └── gemini_client.py       # Vertex AI integration
│   ├── rules/
│   │   ├── rule_engine.py         # Rule evaluation
│   │   └── dnd_rules.py           # D&D 5e mechanics
│   └── utils/
│       ├── text_formatter.py      # Output formatting
│       └── logging_config.py      # Logging setup
├── tools/
│   └── zil_converter/
│       ├── cli.py                 # Converter CLI
│       ├── parser.py              # S-expression parser
│       ├── extractor.py           # Entity extraction
│       └── converter.py           # ZIL → JSON conversion
├── worlds/
│   ├── trinity.json               # Trinity (imported from ZIL)
│   ├── trinity_overrides.json     # Manual enhancements
│   ├── zork_original.json         # Zork I (imported from ZIL)
│   └── planetfall.json            # Planetfall (imported from ZIL)
└── .cache/
    └── zil_translations/
        └── translations.json      # Cached ZIL translations
```

## Development Status

### Completed Features ✅

**Core Engine:**
- [x] Structured game state (RAG foundation)
- [x] Gemini LLM integration
- [x] Action interpretation pipeline
- [x] State update mechanism
- [x] Narrative generation from state
- [x] Game loop orchestration

**World Sources:**
- [x] ZIL import & conversion
- [x] Manual JSON worlds
- [x] Procedural generation (rogue mode)
- [x] Override system

**ZIL Integration:**
- [x] S-expression parser
- [x] Entity extraction (locations, items, NPCs)
- [x] Relationship mapping
- [x] On-demand ZIL translation
- [x] Translation caching
- [x] Multi-game support (Zork, Planetfall, Trinity)

**Game Systems:**
- [x] D&D 5e combat with dice rolls
- [x] Inventory management
- [x] Container system (open/transparent/nested)
- [x] Lighting system
- [x] Blocked exits
- [x] NPC personality-driven dialogue
- [x] Dynamic wish mechanics (genie)

**Developer Tools:**
- [x] God mode inspection commands
- [x] DM debug questions
- [x] Single-step testing mode
- [x] Token usage tracking
- [x] Dry run mode
- [x] State persistence (save/load)

**Performance:**
- [x] Implicit context caching
- [x] Compact state representation
- [x] ZIL translation caching
- [x] Configurable text width

### In Progress 🔄

- [ ] Generic behavior extraction from ZIL (examine_text, triggers, etc.)
- [ ] Auto-generate override suggestions from ZIL analysis
- [ ] God mode on-the-fly state editing

### Future Enhancements 💡

- [ ] Inform 7 import support
- [ ] Web UI for easier gameplay
- [ ] Multiplayer support
- [ ] Voice narration output
- [ ] Fine-tuned models for specific game types

## Performance & Cost

**Token Optimization:**
- Implicit caching reduces repeated context costs by ~70%
- Compact topology representation saves ~40% vs full world
- ZIL translation caching eliminates repeat translation costs
- Average game session: ~50K-100K tokens

**Dry Run Mode:**
```bash
# Estimate costs without API calls
poetry run python -m src.main worlds/zork.json --dry-run

Token usage stats:
  Total tokens: 89,234
  Cached tokens: 62,156 (70%)
  New tokens: 27,078
  Estimated cost: $0.08
```

## Contributing

Contributions welcome! Key areas:

1. **New ZIL Game Support**: Test importer with more Infocom titles
2. **Behavior Extraction**: Auto-extract more ZIL patterns
3. **Override Enhancements**: Add more override types (dialog trees, quests)
4. **Performance**: Further optimize token usage
5. **Documentation**: Improve game creation guides

## License

MIT License - See LICENSE file

---

## Recent Updates

### 2025-12-29: God Mode & Override System
- ✅ God mode debugging (`/inspect`, `/state`, `/context`, `DM: <question>`)
- ✅ Override system for manual enhancements (survives re-imports)
- ✅ God mode works in interactive and single-step modes
- ✅ Container nesting fixes (Trinity pocket → coin, credit_card)
- ✅ ZIL flag detection improvements (`opened`, `container`, `transbit`)

### 2025-12-18: ZIL Import Optimization
- ✅ On-demand ZIL translation with persistent caching
- ✅ Configurable ZIL field filtering (reduce token usage by 60%)
- ✅ Trinity game type with proper intro and DM instructions
- ✅ Start location filtering (skip pseudo-locations)

### 2025-12-11: ZIL Converter
- ✅ Full S-expression parser for ZIL
- ✅ Entity extraction (rooms, items, NPCs, relationships)
- ✅ Pattern matching for common ZIL structures
- ✅ Multi-game support (Zork, Planetfall, Trinity)

### 2025-11-27: Core Features
- ✅ NPC personality-driven dialogue
- ✅ Single-step testing mode
- ✅ Token tracking and dry run mode
- ✅ Implicit context caching optimization

---

**Version**: 0.4.0 (Beta - ZIL Remastering Ready)
**Last Updated**: 2025-12-29
**Status**: Production Ready - Classic Game Import & Enhancement
