# ZIL to JSON Converter

A hybrid extraction tool that converts classic Infocom ZIL (Zork Implementation Language) games to the LLM-IF JSON world format.

## Features

✅ **Automated Extraction**
- Parses ZIL S-expressions from `.zil` source files
- Extracts rooms (105 from Planetfall)
- Extracts objects/items (144 from Planetfall)
- Identifies NPCs via ACTORBIT flag (9 from Planetfall)

✅ **Smart Conversion**
- Converts room exits to JSON connections
- **Handles blocked exits with ELSE clauses** (e.g., "Only Santa Claus climbs down chimneys")
- **Detects transparent containers** via `transbit` flag for content visibility
- Infers item types from ZIL flags (doors, containers, weapons, etc.)
- Preserves ZIL attributes for LLM interpretation
- Flags conditional exits for puzzle implementation

✅ **Comprehensive Documentation**
- Generates adaptation notes for manual review
- Documents action routines requiring implementation
- Tracks conditional exits needing puzzle logic
- Lists TODOs with context

## Installation

Dependencies are already in `pyproject.toml`:
```toml
sexpdata = "^1.0.0"  # S-expression parser
click = "^8.1.0"      # CLI framework
```

## Usage

### Basic Conversion
```bash
poetry run python -m tools.zil_converter ../planetfall-invclues/ -o worlds/planetfall.json
```

### Extract Only (No Smart Patterns)
```bash
poetry run python -m tools.zil_converter ../planetfall-invclues/ --extract-only
```

### Verbose Mode
```bash
poetry run python -m tools.zil_converter ../planetfall-invclues/ -v
```

## Output

### Generated Files

**1. `worlds/planetfall.json`** - Complete LLM-IF world:
```json
{
  "locations": {...},     // 105 rooms
  "items": {...},         // 144 objects
  "npcs": {...},          // 9 NPCs
  "item_locations": {...},
  "npc_locations": {...},
  "player_location": "...",
  "flags": {},
  "puzzles": {}
}
```

**2. `worlds/planetfall_NOTES.md`** - Manual adaptation tasks:
- 185 items needing review
- Room action routines
- Conditional exits
- NPC behavior implementations

### Conversion Results

**Planetfall (105 rooms, 144 items, 9 NPCs)**:
- ✅ All room structure extracted
- ✅ All item properties preserved
- ✅ ZIL flags converted to attributes
- ⚠️ 185 action routines need manual review
- ⚠️ Conditional exits flagged for puzzles
- ⚠️ Floyd extracted as smart object (not NPC - correct!)

## Architecture

### Components

1. **parser.py** - ZIL S-expression parser
   - Handles angle bracket `<...>` syntax
   - Removes comments while preserving structure
   - Extracts ROOM, OBJECT, GLOBAL, ROUTINE forms

2. **extractor.py** - Entity extraction
   - `RoomExtractor` - Extracts locations and exits
   - `ObjectExtractor` - Extracts items with type inference
   - `NPCExtractor` - Identifies actors via ACTORBIT

3. **converter.py** - JSON world generator
   - `LocationConverter` - Rooms → JSON locations
   - `ItemConverter` - Objects → JSON items
   - `NPCConverter` - Actors → JSON NPCs

4. **pattern_matcher.py** - Smart puzzle detection
   - Locked door patterns
   - Container puzzles
   - Conditional exit analysis

5. **cli.py** - Command-line interface

## Technical Decisions

### Why General Libraries?

We use `sexpdata` (general Lisp parser) instead of ZIL-specific tools because:
- No maintained Python ZIL parsers exist
- ZIL is essentially Lisp with `<...>` instead of `(...)`
- Simple string replacement `< → (`, `> → )` works perfectly

### Comment Handling

ZIL comments (`;...`) are tricky:
- Removed to clean up parsed forms
- **Critical**: Preserve closing brackets in comment lines
- Example: `;"OUT" 0>)` → comment removed but `>)` preserved

### Floyd as Object, Not NPC

Floyd (the robot companion) is correctly extracted as an **item** because:
- ZIL defines him as `OBJECT` with `CONTBIT` (container)
- No `ACTORBIT` flag (not an actor in ZIL terms)
- Complex behavior in `FLOYD-F` action routine (noted in TODOs)
- This matches the original implementation

## Limitations

### Cannot Auto-Convert

❌ **Complex ZIL routines** - Require manual adaptation
❌ **Conditional logic** - Functions like `WATER-LEVEL-F` need puzzles
❌ **Floyd AI** - Companion behavior needs Python implementation
❌ **Game-specific mechanics** - Drowning, oxygen, etc.

### Manual Work Required

The converter generates TODOs for:
1. Action routines (rooms, objects, NPCs)
2. Conditional exits (puzzle opportunities)
3. Special mechanics (game-specific attributes)

## Example Output

### Location
```json
"balcony": {
  "id": "balcony",
  "name": "Balcony",
  "attributes": {
    "description_hints": "Balcony",
    "lighting": "bright",
    "is_outdoors": false,
    "zil_pseudo_objects": ["PLAQUE", "PLAQUE-PSEUDO"],
    "zil_global_objects": ["cliff", "ocean", "stairs", "window"],
    "zil_flags": ["onbit", "rlandbit"]
  },
  "connections": {
    "up": "winding_stair"
  }
}
```

### Location with Blocked Exit
```json
"kitchen": {
  "id": "kitchen",
  "name": "Kitchen",
  "attributes": {
    "description_hints": "Kitchen of the white house...",
    "lighting": "bright",
    "blocked_exits": {
      "down": "Only Santa Claus climbs down chimneys."
    }
  },
  "connections": {
    "west": "living_room",
    "up": "attic"
  }
}
```

**Note**: Blocked exits with ELSE clauses from ZIL like `(DOWN TO STUDIO IF FALSE-FLAG ELSE "message")` are automatically converted to the `blocked_exits` attribute.

### Item (Door)
```json
"conference_door": {
  "id": "conference_door",
  "name": "door",
  "attributes": {
    "description_hints": "door",
    "type": "entrance",
    "is_door": true,
    "is_open": false,
    "is_locked": false,
    "takeable": false,
    "zil_flags": ["doorbit", "ndescbit"]
  }
}
```

### Item (Transparent Container)
```json
"bottle": {
  "id": "bottle",
  "name": "glass bottle",
  "attributes": {
    "description_hints": "A bottle is sitting on the table.",
    "type": "container",
    "container": true,
    "open": false,
    "capacity": 4,
    "takeable": true,
    "zil_flags": ["takebit", "transbit", "contbit"]
  }
}
```

**Note**: Items with the `transbit` flag are transparent containers. The game engine will show their contents even when closed, allowing players to see water inside a glass bottle, for example.

### NPC
```json
"measle": {
  "id": "measle",
  "name": "mocking sailor",
  "attributes": {
    "description_hints": "mocking sailor",
    "creature_type": "humanoid",
    "hostility": "neutral",
    "personality": "mocking sailor from Planetfall",
    "special_behavior": "Complex behavior defined in ZIL routine: MEASLE-F",
    "zil_flags": ["actorbit", "person"]
  }
}
```

## Success Criteria

✅ **Must Have** (ALL ACHIEVED):
- [x] Parse all Planetfall ZIL files without errors
- [x] Extract all rooms (105 locations)
- [x] Extract all objects (144 items)
- [x] Identify NPCs (9 actors)
- [x] Generate valid JSON matching world schema
- [x] Create comprehensive TODO notes

✅ **Should Have** (ALL ACHIEVED):
- [x] Infer object types from flags
- [x] Generate description hints from LDESC
- [x] Handle Planetfall-specific attributes
- [x] CLI tool with options

⚠️ **Nice to Have** (PARTIALLY ACHIEVED):
- [~] Convert simple puzzles (locked doors detected, not converted)
- [ ] Parse verb syntax
- [ ] Extract dialogue text

## Next Steps

1. **Test in Engine** - Load `planetfall.json` in LLM-IF
2. **Implement Floyd** - Add companion NPC behavior
3. **Add Puzzles** - Convert conditional exits to puzzle system
4. **Iterate** - Refine based on gameplay testing

## Files Modified

**New Files Created**:
- `tools/zil_converter/__init__.py`
- `tools/zil_converter/__main__.py`
- `tools/zil_converter/parser.py`
- `tools/zil_converter/extractor.py`
- `tools/zil_converter/converter.py`
- `tools/zil_converter/pattern_matcher.py`
- `tools/zil_converter/cli.py`

**Dependencies Added** (pyproject.toml):
- `sexpdata = "^1.0.0"`
- `click = "^8.1.0"`

**Output Generated**:
- `worlds/planetfall.json` - Complete world (105 locations, 144 items, 9 NPCs)
- `worlds/planetfall_NOTES.md` - 185 manual adaptation tasks

## Conclusion

The ZIL converter successfully extracts game structure from Planetfall source files, providing a solid foundation for LLM-IF conversion. While 185 items need manual review (action routines, special mechanics), the core world structure is complete and ready for testing.

The hybrid approach (automated extraction + smart conversion + manual adaptation notes) balances automation with quality, ensuring nothing is lost in translation.
