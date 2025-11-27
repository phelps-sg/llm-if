# Core Architectural Principles

This document captures the fundamental architectural principles of the Interactive Fiction engine. These principles ensure consistency, maintainability, and immersive gameplay.

## 1. The DM Narrates Everything

**Principle**: All game events must be narrated by the DM (LLM). No game mechanics should print directly to the player without flowing through the DM's narrative generation.

**Why**: This maintains immersion and ensures consistent storytelling. The LLM contextualizes mechanics within narrative, creating a cohesive experience.

**Example Violation**:
```python
# ❌ WRONG: Direct print bypasses DM
print("The wolf attacks! You take 6 damage!")
```

**Correct Pattern**:
```python
# ✅ CORRECT: Flow through DM
combat_result = execute_attack(wolf, player)
game_state.flags["combat_result"] = combat_result
narrative = llm.narrate_combat(combat_result)  # DM narrates
print(narrative)
```

**Implementation**:
- Mechanics store results in `game_state.flags`
- Game loop checks for flags after state updates
- LLM narrates from flags data
- Results displayed: mechanics first, then narrative

## 2. Separation of Mechanics and Narrative

**Principle**: Game mechanics (dice rolls, state updates) are separate from narrative generation.

**Flow**:
```
Player Input → LLM Interprets → Mechanics Execute → Results Stored → LLM Narrates → Player Sees
```

**Why**: Allows mechanical transparency (showing dice rolls) while maintaining immersive narrative. Keeps deterministic game rules separate from creative storytelling.

**Benefits**:
- Mechanics are predictable and testable
- Narrative can be creative and contextual
- Players see both "what happened" (mechanics) and "how it happened" (narrative)

## 3. Mechanical Transparency

**Principle**: D&D mechanics (dice rolls, AC, damage) should be visible to the player alongside narrative.

**Pattern**:
```
[Dice rolls and mechanics displayed]
[DM narrates the outcome...]
[Narrative describing what happened]
```

**Why**: Players need to understand the rules and see fair play. Narrative enhances, not replaces, mechanics.

**Example**:
```
⚔️  COMBAT ROUND
🗡️  YOUR ATTACK:
  🎲 Attack Roll: 15 +5 = 20
  🛡️  Target AC: 14
  ✅ HIT!
  💥 Damage: 1d8+3 ([6]) = 9
  ❤️  Goblin HP: 0/7
  💀 GOBLIN SLAIN!

[DM narrates the outcome...]

Your blade strikes true, cutting through the goblin's defenses!
The creature falls with a final gasp. Victory is yours!
```

## 4. State-Driven Architecture

**Principle**: All game state changes flow through structured state updates, not ad-hoc modifications.

**Pattern**:
```python
# LLM returns structured updates
{"state_updates": [
    {"type": "move_player", "params": {"destination": "hall"}},
    {"type": "add_to_inventory", "params": {"item_id": "sword"}}
]}

# Processor applies them
action_processor.apply_state_updates(updates, game_state)
```

**Why**:
- Ensures consistency - all changes go through same validation
- Enables history tracking and debugging
- Prevents race conditions and invalid states
- Makes state changes explicit and auditable

**Never Do**:
```python
# ❌ WRONG: Direct state modification
game_state.player_location = "hall"  # Bypasses validation
```

## 5. LLM as DM, Not Game Engine

**Principle**: The LLM interprets player intent and narrates outcomes. It does NOT execute mechanics or manage state directly.

**Division of Labor**:
- **LLM (DM)**: Interprets actions, generates narrative, creates drama
- **Rules Engine**: Executes mechanics (combat, dice rolls, state changes)
- **Game State**: Stores truth about world state
- **Action Processor**: Applies structured state updates

**Why**: LLMs can hallucinate. Mechanics and state must be deterministic and reliable.

**Example**:
```python
# Player says: "I attack the goblin with my sword"

# 1. LLM interprets (may be creative)
interpretation = llm.interpret_action("attack goblin", context)
# Returns: {"type": "trigger_combat", "params": {"target_npc_id": "goblin"}}

# 2. Rules engine executes (deterministic)
combat_result = rule_engine.resolve_attack(player, goblin)
# Returns: {"hit": True, "damage": 9, "target_dead": True}

# 3. LLM narrates (creative again)
narrative = llm.narrate_combat(combat_result)
# Returns: "Your blade strikes true, cutting through the goblin's defenses!..."
```

## 6. Flags Pattern for Deferred Narration

**Principle**: When mechanics execute during state updates, store results in `game_state.flags` for later narration.

**Why**: State updates happen synchronously, but we need to show mechanics and generate narrative afterward.

**Pattern**:
```python
# During state update execution:
combat_result = rule_engine.resolve_attack(player, npc)
game_state.flags["last_combat_result"] = combat_result

# After all updates, in game loop:
if "last_combat_result" in game_state.flags:
    combat_result = game_state.flags.pop("last_combat_result")

    # Show mechanics
    display_combat_mechanics(combat_result)

    # Generate narrative
    narrative = llm.narrate_combat(combat_result)
    print(narrative)
```

**Common Flags**:
- `last_combat_result`: Player-initiated combat results
- `npc_actions_result`: NPC unprovoked actions (attacks, chases)
- `item_creation_result`: Dynamically created items
- Custom flags for specific events

## 7. Two-Step LLM Architecture

**Principle**: Separate action interpretation from narrative generation to prevent hallucinations.

**Step 1 - Interpret**: What should happen?
```python
interpretation = llm.interpret_action(player_input, context)
# Returns structured state updates only
```

**Step 2 - Narrate**: Describe what happened
```python
# Apply updates first
action_processor.apply_state_updates(interpretation["state_updates"])

# Then narrate from actual state
narrative = llm.generate_narrative(player_input, updated_context)
```

**Why**: If LLM generates narrative before state updates, it may describe things that don't match reality (hallucinations).

## Summary

These principles work together to create a robust, immersive experience:

1. **DM Narrates Everything**: No raw mechanics output
2. **Separation of Concerns**: Mechanics ≠ Narrative
3. **Mechanical Transparency**: Show the dice rolls
4. **State-Driven Updates**: Structured changes only
5. **LLM as DM**: Interprets and narrates, doesn't execute
6. **Flags Pattern**: Store results for deferred narration
7. **Two-Step LLM**: Prevent hallucinations

Follow these principles to maintain consistency and quality.
