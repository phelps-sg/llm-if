# AI-Powered Interactive Fiction Engine

An interactive fiction/text adventure game engine powered by Google Gemini LLM, featuring dynamic narrative generation from structured game state.

## Core Philosophy

**Declarative World, Dynamic Narrative**: The game world is defined as structured JSON with attributes and relationships. The LLM acts as a Dungeon Master, rendering all descriptions dynamically from this state. Nothing is hard-coded—everything is generated based on current game state.

## Key Features

### 🎭 Personality-Driven NPC Dialogue
NPCs speak with quoted dialogue that reflects their personality, role, and attributes:
- **Genie**: Mystical, formal dialogue explaining wish mechanics
- **Guards**: Threatening, hostile warnings
- **Creatures**: Behavior-based responses (passive animals, defensive beasts)
- Dialogue teaches game mechanics through character voice

### 🎮 Single-Step Execution Mode
Test and automate gameplay with command-line interface:
- Execute one command at a time with state persistence
- Custom save file locations for parallel test scenarios
- Debug mode for full state inspection
- Perfect for systematic testing and CI/CD integration

### ⚔️ D&D 5e Combat System
Full tactical combat with dice rolls and rule validation:
- Attack rolls, damage calculation, armor class
- Real-time combat narration
- NPC counterattacks based on hostility
- Complete combat logging

### 🧞 Dynamic Wish System
Reality-bending genie mechanics:
- Create items, NPCs, or locations dynamically
- Wish tracking with decremented counter
- Precise fulfillment (grants exactly what is asked)
- State validation to prevent exploits

### 💡 Intelligent Lighting
Context-aware descriptions based on light levels:
- Pitch black: Only sounds, smells, sensations
- Dark: Vague shapes and outlines
- Dim: Limited visibility with shadows
- Bright: Full detailed descriptions

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        GAME LOOP                             │
│                   (Main Orchestrator)                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌─────────────┐
│ Player  │  │  Game    │  │   Action    │
│ Input   │─>│  State   │<─│  Processor  │
│ Parser  │  │ Manager  │  │             │
└─────────┘  └────┬─────┘  └──────┬──────┘
                  │                │
                  │         ┌──────▼──────┐
                  │         │    Rule     │
                  │         │   Engine    │
                  │         └──────┬──────┘
                  │                │
                  ▼                ▼
            ┌──────────────────────────┐
            │   LLM Rendering Engine   │
            │  (Gemini Integration)    │
            └──────────────────────────┘
                       │
                       ▼
                 ┌──────────┐
                 │ Narrative│
                 │  Output  │
                 └──────────┘
```

## Core Components

### 1. Game State Manager

Maintains the complete game state as structured data:

- **Locations**: Map of location IDs to Location objects
  - Attributes (size, lighting, temperature, mood, etc.)
  - Topology (connections between locations)
  - Items present
  - NPCs present

- **NPCs**: Map of NPC IDs to NPC objects
  - Current location
  - Attributes (stats, personality, relationships, knowledge)
  - Inventory
  - Current state/behavior

- **Items**: Map of item IDs to Item objects
  - Current location or owner
  - Attributes (properties, stats, magical effects)
  - State flags

- **Player State**: Current location, inventory, stats, conditions

- **History**: Recent actions and events for context

### 2. LLM Integration Layer (Gemini)

Handles all communication with Google Gemini:

- **Rendering Functions**:
  - `describe_location()`: Location state → narrative description
  - `describe_action_result()`: Action + state changes → narrative
  - `npc_dialogue()`: NPC attributes + context → speech
  - `combat_narration()`: Combat mechanics → play-by-play

- **Prompt Management**: Context-aware prompt templates
- **Response Parsing**: Extract structured data from LLM responses when needed
- **Context Window Management**: Optimize state sent to LLM

### 3. Rule Engine

Declarative rules that constrain the LLM and enforce game mechanics:

**Rule Types**:
- **Physics Rules**: Movement, object interaction, environmental effects
- **Combat Rules**: D&D 5e mechanics (attack rolls, damage, saving throws)
- **Social Rules**: NPC reactions, persuasion checks, relationship changes
- **Magic Rules**: Spell effects and limitations
- **Narrative Rules**: Story progression gates and triggers

**Rule Format** (JSON):
```json
{
  "rule_id": "combat_attack",
  "trigger": "action.type == 'attack'",
  "conditions": [
    "player.has_weapon",
    "target.is_hostile"
  ],
  "mechanics": {
    "type": "d20_check",
    "modifier": "player.attack_bonus",
    "dc": "target.armor_class"
  },
  "effects": {
    "on_success": ["calculate_damage", "apply_damage"],
    "on_failure": ["miss"]
  }
}
```

**Rule Execution**:
- Rules are deterministic and checked before LLM narration
- LLM narrates the outcome but doesn't decide it
- DM has creative discretion within rule boundaries

### 4. Action Processor

Pipeline for handling player input:

```
Player Input → Parse Intent → Check Rules → Update State → Render Output
                    │              │             │             │
                    ▼              ▼             ▼             ▼
              (LLM interprets) (Validate)  (Apply changes) (LLM narrates)
```

**Steps**:
1. **Parse**: LLM interprets natural language input into structured action
2. **Validate**: Rule engine checks if action is allowed
3. **Execute**: Apply deterministic mechanics (dice rolls, stat checks)
4. **Update**: Modify game state based on results
5. **Render**: LLM generates narrative description of outcome

### 5. Game Loop

Main orchestration:
1. Display current location/situation (LLM-rendered)
2. Accept player input
3. Process action through pipeline
4. Update game state
5. Display results (LLM-rendered)
6. Check for victory/defeat conditions
7. Repeat

## Data Models

### Location
```python
{
  "id": "dungeon_entrance",
  "name": "Dungeon Entrance",
  "attributes": {
    "size": "medium",
    "lighting": "dim_torchlight",
    "temperature": "cold",
    "atmosphere": "foreboding",
    "description_hints": "ancient stone, moss-covered walls"
  },
  "connections": {
    "north": "grand_hall",
    "east": "guard_room",
    "south": null  # exit
  },
  "items_here": ["rusty_sword", "torch_1"],
  "npcs_here": ["guard_skeleton"]
}
```

### NPC
```python
{
  "id": "guard_skeleton",
  "name": "Skeletal Guard",
  "location_id": "dungeon_entrance",
  "attributes": {
    "creature_type": "undead",
    "hp": 13,
    "armor_class": 13,
    "personality": "mindless_guardian",
    "hostility": "aggressive_to_living",
    "description_hints": "rusted armor, glowing eye sockets"
  },
  "inventory": ["ancient_key"],
  "state": {
    "aware_of_player": false,
    "current_behavior": "patrolling"
  }
}
```

### Item
```python
{
  "id": "rusty_sword",
  "name": "Rusty Shortsword",
  "location_id": "dungeon_entrance",
  "owner_id": null,
  "attributes": {
    "type": "weapon",
    "damage": "1d6",
    "weight": 2,
    "condition": "poor",
    "description_hints": "pitted blade, worn leather grip",
    "magical": false
  }
}
```

## Key Design Principles

1. **Separation of State and Presentation**
   - Game state is pure structured data
   - All descriptions generated dynamically by LLM
   - Same state can be rendered different ways based on context

2. **LLM as Narrative Layer Only**
   - LLM never stores state
   - LLM doesn't make mechanical decisions (dice rolls, rule outcomes)
   - LLM interprets and narrates, doesn't adjudicate

3. **Rules as Constraints**
   - LLM has creative freedom within rule boundaries
   - Deterministic mechanics (combat, skill checks) are computed
   - LLM narrates the results creatively

4. **Deterministic Core, Creative Surface**
   - Game mechanics are deterministic and testable
   - Narrative is creative and contextual
   - Clear boundary between the two

5. **Context-Aware Rendering**
   - LLM receives relevant state slice (not entire world)
   - Recent history for narrative continuity
   - Player knowledge vs. actual state separation

## Technology Stack

- **Language**: Python 3.11+
- **LLM Provider**: Google Gemini API
- **Dependencies**:
  - `google-generativeai`: Gemini SDK
  - `pydantic`: Data validation and schema
  - `pyyaml`: Rule and world definition files
  - `jsonschema`: Validation
  - Standard library: `json`, `random` (for dice rolls), `typing`

## Project Structure

```
if/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                 # Game loop entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── game_state.py       # GameState class
│   │   ├── location.py         # Location model
│   │   ├── npc.py              # NPC model
│   │   ├── item.py             # Item model
│   │   └── player.py           # Player model
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── game_loop.py        # Main game loop
│   │   ├── action_processor.py # Action handling
│   │   └── state_manager.py    # State management
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gemini_client.py    # Gemini API wrapper
│   │   ├── prompts.py          # Prompt templates
│   │   └── renderer.py         # Rendering functions
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── rule_engine.py      # Rule evaluation
│   │   ├── dnd_rules.py        # D&D 5e mechanics
│   │   └── validators.py       # Action validation
│   └── utils/
│       ├── __init__.py
│       ├── dice.py             # Dice rolling utilities
│       └── logger.py           # Logging
├── worlds/
│   ├── example_dungeon.json    # Example world definition
│   └── rules/
│       ├── base_rules.yaml     # Core game rules
│       ├── combat_rules.yaml   # Combat mechanics
│       └── magic_rules.yaml    # Magic system
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_rules.py
    └── test_game_loop.py
```

## Development Roadmap

### Phase 1: Core Foundation
- [ ] Data models (Location, NPC, Item, GameState)
- [ ] Basic Gemini integration
- [ ] Simple game loop
- [ ] Location rendering

### Phase 2: Action System
- [ ] Action parser
- [ ] Action processor
- [ ] State update mechanisms
- [ ] Basic rule validation

### Phase 3: Rule Engine
- [ ] Rule definition format
- [ ] Rule engine implementation
- [ ] D&D 5e combat rules
- [ ] Skill check system

### Phase 4: Advanced Features
- [x] NPC dialogue system ✅ *Implemented 2025-11-27*
  - Personality-driven dialogue generation
  - NPCs explain game mechanics through character voice
  - Dialogue reflects NPC attributes (hostile, passive, mischievous, etc.)
  - Comprehensive e2e test coverage
- [x] Combat narration ✅
- [x] Magic system (Genie wishes) ✅
- [x] Inventory management ✅
- [x] Save/load game state ✅

### Phase 5: World Building
- [ ] World definition format
- [ ] Example worlds
- [ ] World validation tools
- [ ] World editor (stretch goal)

## Usage Example

```python
from src.engine.game_loop import GameLoop
from src.models.game_state import GameState

# Load world definition
state = GameState.from_file("worlds/example_dungeon.json")

# Initialize game
game = GameLoop(state, gemini_api_key="YOUR_API_KEY")

# Start game
game.run()
```

```
> You find yourself at the entrance to an ancient dungeon. Cold air seeps
> from the darkness ahead. Moss-covered stone walls are lit by flickering
> torchlight. To the north, you can see a grand hallway. To the east, you
> hear the faint sound of scraping metal.

What do you do?
> look around

> You scan your surroundings more carefully. At your feet lies a rusty
> shortsword, its pitted blade reflecting the torchlight. A torch burns
> in a sconce on the wall. In the shadows, you notice something moving—
> a skeletal figure in rusted armor, its eye sockets glowing with an
> eerie green light. It hasn't noticed you yet.

What do you do?
> quietly pick up the sword

> You carefully reach down and grasp the rusty sword's worn leather grip.
> The skeleton guard continues its patrol, oblivious to your presence.

What do you do?
```

## Configuration

Create a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
LOG_LEVEL=INFO
CONTEXT_WINDOW_SIZE=4096
```

## Design Notes & Future Considerations

- **LLM Consistency**: May need to fine-tune prompts to ensure consistent tone and style
- **Context Window**: Strategy for summarizing long game sessions
- **Ambiguity Resolution**: How to handle ambiguous player input
- **State Validation**: Ensure state remains coherent after updates
- **Performance**: Cache LLM responses where appropriate
- **Multiplayer**: Architecture could extend to multi-player scenarios
- **Procedural Generation**: LLM could help generate new locations/NPCs on the fly

## Contributing

This is a living document. As the design evolves, update this README to reflect:
- Architectural changes
- New components
- Lessons learned
- Design decisions and rationale

---

## Recent Updates

### 2025-11-27: NPC Dialogue System
- ✅ Implemented personality-driven NPC dialogue
- ✅ NPCs speak with quoted dialogue reflecting their attributes
- ✅ Game mechanics explained through character voice (genie explains wishes, guards threaten)
- ✅ Comprehensive e2e test suite (5 tests, 100% passing)
- ✅ Single-step mode enhanced with auto-room descriptions

### 2025-11-27: Single-Step Execution Mode
- ✅ Command-line mode for testing and automation
- ✅ State persistence between commands
- ✅ Custom save file locations
- ✅ Debug mode for full state inspection

---

**Version**: 0.2.0 (Playable Alpha)
**Last Updated**: 2025-11-27
**Status**: Feature Complete - Core Experience Polished
