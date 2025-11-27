# Genie-Compatible Design Principle

## Overview

**Genie-compatible** is a core design principle that guides the implementation of this LLM-powered interactive fiction engine. It's not a feature, but a constraint that ensures maximum DM creativity and world mutability.

## Definition

> The game world must be flexible and mutable enough that a genie (or similar wish-granting entity) can grant ANY reasonable wish through the available state update mechanisms.

If the DM cannot narrate the effects of a wish because the system lacks the necessary state update types or world representation capabilities, then the system is too rigid.

## Philosophy

Traditional IF engines have fixed worlds:
- Locations are predefined in the game file
- Items are created by the author, not dynamically
- NPCs have fixed behaviors
- The world structure is immutable

**Genie-compatible design challenges this.** If a player wishes for:
- "A path south" → Can the DM create new locations?
- "Wings to fly" → Can the DM modify player capabilities?
- "Turn this staff into a sword" → Can the DM transform items?

If the answer is "no" to any of these, the system lacks creative freedom.

## Why "Genie" as the Test?

Genies are the ultimate stress test for a creative system because:
1. **Unpredictable requests** - Players can wish for anything
2. **Requires full mutation** - Must modify locations, items, NPCs, player
3. **Tests boundaries** - Reveals what the system CAN'T do
4. **Universal metaphor** - Everyone understands wish-granting mechanics

## Current Implementation Status

### ✅ Implemented (Genie-Compatible)

| Capability | State Update | Example Wish |
|------------|-------------|--------------|
| Create items | `create_item` | "I wish for a magic sword" |
| Modify player | `modify_attribute` (player) | "I wish to see in the dark" |
| Modify NPCs | `modify_attribute` (npc) | "I wish the deer was friendly" |
| Destroy items | `destroy_item` | "I wish to erase this cursed ring" |
| Move entities | `move_item`, `move_npc` | "I wish the treasure was here" |

### ❌ Not Yet Implemented

| Capability | State Update | Example Wish |
|------------|-------------|--------------|
| Create locations | `create_location` | "I wish for a path south" |
| Modify location attributes | `modify_attribute` (location) | "I wish this room was brighter" |
| Create NPCs | `create_npc` | "I wish for a companion" |
| Modify game rules | `modify_rule` | "I wish gravity didn't exist" |

## Design Decisions Guided by This Principle

### 1. Dynamic Item Creation
**Decision:** Added `create_item` state update
**Rationale:** Genies must be able to create items on demand
**Benefit:** DM can handle "knock antlers off deer" → creates severed antlers

### 2. General Player Attributes
**Decision:** `player.attributes` is an open dict, not fixed fields
**Rationale:** Genies might grant ANY ability (flying, darkvision, telepathy)
**Benefit:** DM can track blindness, wounds, blessings, curses creatively

### 3. NPC-Specific Behaviors
**Decision:** Put wish-tracking in genie's attributes, not general prompt
**Rationale:** Not every game has genies; mechanics should be per-NPC
**Benefit:** Different games can have different NPCs without changing engine

### 4. Narrative-State Matching
**Decision:** Strengthened rule that narrative MUST match state updates
**Rationale:** If genie creates ice cream in narrative, it must exist in game
**Benefit:** Prevents hallucinations where wishes seem to work but don't

## Testing with Genie-Compatible Scenarios

### Test Case 1: Simple Item Creation
```
Player: "genie, I wish for ice cream"
Expected:
  - create_item (ice cream)
  - modify_attribute (genie.wishes_remaining -= 1)
Status: ✅ WORKS
```

### Test Case 2: Player Modification
```
Player: "genie, I wish to fly"
Expected:
  - modify_attribute (player.can_fly = true)
  - modify_attribute (genie.wishes_remaining -= 1)
Status: ✅ WORKS (system supports this)
```

### Test Case 3: World Modification
```
Player: "genie, I wish for a path south"
Expected:
  - create_location ("hidden_grove")
  - connect forest_clearing → hidden_grove (south)
  - modify_attribute (genie.wishes_remaining -= 1)
Status: ❌ BLOCKED (no create_location state update yet)
```

### Test Case 4: Complex Transformation
```
Player: "genie, turn this oak staff into a flaming sword"
Expected:
  - destroy_item (oak_staff)
  - create_item (flaming_sword with fire damage attributes)
  - modify_attribute (genie.wishes_remaining -= 1)
Status: ✅ WORKS
```

## When to Add New Capabilities

Use this test: **"Could a genie grant this wish?"**

If the answer is "yes" but the system can't handle it, consider adding:
1. New state update type
2. More flexible data structures
3. Better LLM guidance

## Coexistence with Traditional IF

Genie-compatible does NOT mean abandoning traditional IF conventions:

**Invalid moves** (no exit):
- Traditional: "You can't go that way"
- Genie-compatible: "I wish for a path south" → DM creates location

**Fixed puzzles** (locked door):
- Traditional: "You need the ancient key"
- Genie-compatible: "I wish the door was open" → DM modifies door.locked = false

Both approaches coexist. The system supports:
- **Rigid structures** when appropriate (game design choice)
- **Creative mutation** when needed (wish fulfillment)

## Future Directions

### 1. Dynamic Location Creation
Add `create_location` state update for truly dynamic world building.

### 2. NPC Creation
Add `create_npc` to allow wishes like "I wish for a friendly guard".

### 3. Rule Modification
Add capability to modify game physics/rules for wishes like "I wish I could breathe underwater".

### 4. Persistent World Changes
Ensure genie-created content persists across save/load.

## Conclusion

**Genie-compatible design is about asking: "What would break if we added a genie?"**

If the answer is "the genie couldn't grant reasonable wishes," then the system needs more flexibility. The genie is our design compass, ensuring the engine remains creative, mutable, and truly powered by LLM imagination rather than rigid programming.

---

*This principle was discovered during development when testing revealed the LLM couldn't properly handle wish-granting mechanics, exposing limitations in world mutability.*
