# Plan: Single-Step Execution Mode for Game Testing

## Goal
Add a "single-step" mode that allows running the game engine one command at a time, saving state between commands and exiting. This enables systematic testing without interactive sessions.

## Use Cases
1. Test individual commands in isolation
2. Script sequences of commands for automated testing
3. Inspect game state between each command
4. Reproduce specific scenarios/bugs systematically
5. Allow Claude to test the game directly via command line

## Architecture Design

### Current Flow
```
main.py → GameLoop.__init__() → _game_turn() (infinite loop)
  ↓
User types commands interactively
  ↓
Game runs until user types 'quit'
```

### New Flow (Single-Step Mode)
```
main.py --single-step --command "take sword"
  ↓
Load state from file (or init new game)
  ↓
Process ONE command
  ↓
Save state to file
  ↓
Output result
  ↓
Exit cleanly
```

## Implementation Components

### 1. State Persistence (GameState)
**File**: `src/models/game_state.py`

**Add methods:**
- `save_to_file(file_path: str) -> None`
  - Serialize complete game state to JSON
  - Include ALL fields: locations, items, npcs, player, item_locations, npc_locations, player_location, turn_count, history, flags, plot_config, dm_state
  - Use `model_dump()` for Pydantic models
  - Pretty-print JSON for debugging

- `load_from_file(file_path: str) -> GameState` (classmethod)
  - Deserialize JSON to GameState
  - Use existing `from_file()` or `from_dict()` if available
  - Validate state integrity

**Note**: Check if these methods already exist (likely `from_file()` exists)

### 2. Single-Step Execution (GameLoop)
**File**: `src/engine/game_loop.py`

**Add method:**
```python
def execute_single_step(self, command: str) -> dict:
    """Execute a single command and return full result.

    Args:
        command: Player command to execute

    Returns:
        dict containing:
        - command: The command executed
        - narrative: Generated narrative
        - interpretation: LLM interpretation
        - player_location: Current location ID
        - exits: Available exits
        - inventory: Player inventory
        - turn_count: Current turn number
    """
```

**Implementation:**
- Call existing `process_turn(command)`
- Gather current state info
- Return structured result dict
- Handle errors gracefully (return error in result dict)

### 3. CLI Interface (main.py)
**File**: `main.py`

**Add argument parser:**
```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--single-step', action='store_true',
                   help='Execute single command and exit')
parser.add_argument('--command', type=str,
                   help='Command to execute in single-step mode')
parser.add_argument('--state-file', type=str,
                   default='saves/game_state.json',
                   help='Path to save/load game state')
parser.add_argument('--init', type=str,
                   help='Initialize new game from world file')
parser.add_argument('--debug', action='store_true',
                   help='Output full state dump for debugging')
```

**Add single-step mode handler:**
```python
def run_single_step_mode(args):
    """Run game in single-step mode."""

    # 1. Load or initialize game
    if args.init:
        # Initialize new game from world file
        game_state = GameState.from_file(args.init)
        gemini = GeminiClient()
        rules = RuleEngine()
        game_loop = GameLoop(game_state, gemini, rules)
    else:
        # Load existing state
        if not os.path.exists(args.state_file):
            print(f"Error: No saved state at {args.state_file}")
            print(f"Use --init <world_file> to start new game")
            sys.exit(1)

        game_state = GameState.load_from_file(args.state_file)
        gemini = GeminiClient()
        rules = RuleEngine()
        game_loop = GameLoop(game_state, gemini, rules)

    # 2. Execute command
    if not args.command:
        print("Error: --command required in single-step mode")
        sys.exit(1)

    result = game_loop.execute_single_step(args.command)

    # 3. Save state
    os.makedirs(os.path.dirname(args.state_file), exist_ok=True)
    game_state.save_to_file(args.state_file)

    # 4. Output result
    print("\n" + "="*60)
    print(f"Command: {args.command}")
    print("="*60)
    print(f"\n{result['narrative']}\n")
    print(f"Location: {result['player_location']}")
    print(f"Exits: {', '.join(result['exits'])}")
    print(f"Turn: {result['turn_count']}")

    if args.debug:
        print("\n" + "="*60)
        print("DEBUG: Full State")
        print("="*60)
        print(json.dumps(result, indent=2))

    # 5. Exit
    sys.exit(0)
```

**Modify main():**
```python
def main():
    args = parser.parse_args()

    if args.single_step:
        run_single_step_mode(args)
        return  # Never reached (exits above)

    # Normal interactive mode
    # ... existing code ...
```

### 4. Output Format

**Normal Mode Output:**
```
============================================================
Command: take sword
============================================================

You reach down and grasp the rusty sword. It feels heavy in your hand,
but serviceable. The blade shows signs of age but appears sturdy.

Location: entrance
Exits: north, south, west
Turn: 5
```

**Debug Mode Output:**
```
... (normal output above) ...

============================================================
DEBUG: Full State
============================================================
{
  "command": "take sword",
  "narrative": "...",
  "interpretation": {
    "intent": "...",
    "state_updates": [...],
    ...
  },
  "player_location": "entrance",
  "exits": ["north", "south", "west"],
  "inventory": ["torch", "rusty_sword"],
  "turn_count": 5
}
```

## File Structure

```
saves/
  game_state.json          # Default save file
  test_scenario_1.json     # Custom save files
  test_scenario_2.json
```

## Example Usage

```bash
# 1. Initialize new game
python main.py --single-step --init worlds/example_dungeon.json --command "look"

# 2. Execute next command (loads from saves/game_state.json)
python main.py --single-step --command "go north"

# 3. Another command
python main.py --single-step --command "take sword"

# 4. Check inventory
python main.py --single-step --command "inventory"

# 5. Use custom state file
python main.py --single-step --state-file saves/test1.json --command "attack skeleton"

# 6. Debug mode (see full state)
python main.py --single-step --command "go south" --debug

# 7. Initialize and execute in one go
python main.py --single-step --init worlds/example_dungeon.json --command "take torch"
```

## Testing Strategy

### Manual Testing
```bash
# Test sequence: pick up sword and attack
python main.py --single-step --init worlds/example_dungeon.json --command "look"
python main.py --single-step --command "take rusty sword"
python main.py --single-step --command "go north"
python main.py --single-step --command "attack skeleton"
python main.py --single-step --command "inventory"
```

### Automated Testing (future)
```python
# tests/test_single_step_mode.py
def test_single_step_init():
    """Test initializing game in single-step mode."""
    result = subprocess.run([
        "python", "main.py",
        "--single-step",
        "--init", "worlds/example_dungeon.json",
        "--command", "look",
        "--state-file", "saves/test_init.json"
    ], capture_output=True)

    assert result.returncode == 0
    assert os.path.exists("saves/test_init.json")
```

## Implementation Order

1. **Check existing GameState methods** (5 min)
   - Verify if `save_to_file()` / `load_from_file()` exist
   - Check if modifications needed

2. **Add/enhance state persistence** (15 min)
   - Add `save_to_file()` if missing
   - Ensure `load_from_file()` handles all fields
   - Test save/load roundtrip

3. **Add execute_single_step() to GameLoop** (10 min)
   - Implement method
   - Return structured result dict
   - Handle errors

4. **Add CLI arguments to main.py** (20 min)
   - Add argparse
   - Implement run_single_step_mode()
   - Integrate with existing main()
   - Create saves/ directory if needed

5. **Test manually** (15 min)
   - Initialize game
   - Run command sequence
   - Verify state persistence
   - Test error cases

6. **Document usage** (5 min)
   - Add examples to README or docs

## Error Handling

**Case 1: No state file and no --init**
```
Error: No saved state at saves/game_state.json
Use --init <world_file> to start new game
```

**Case 2: No --command in single-step mode**
```
Error: --command required in single-step mode
Usage: python main.py --single-step --command "your command"
```

**Case 3: Invalid command**
```
Command: invalid command xyz
============================================================

I don't understand that command. Try 'help' for available commands.

Location: entrance
Exits: north, south
Turn: 5
(State saved, exit code 0)
```

**Case 4: World file not found**
```
Error: World file not found: worlds/nonexistent.json
```

## Benefits

✅ **For Claude**: Can test game directly without interactive session
✅ **For Developers**: Easy to reproduce bugs with exact command sequence
✅ **For Testing**: Can script automated test scenarios
✅ **For Debugging**: Inspect state between each command
✅ **For CI/CD**: Can run automated game tests in CI pipeline

## Future Enhancements (out of scope)

- Batch mode: Execute multiple commands from file
- State diffing: Show what changed between commands
- Replay mode: Replay saved command history
- Checkpoint system: Named save points
- State inspection: Query specific state fields without executing command
