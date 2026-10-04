---
name: play-if
description: Run an Infocom-style interactive fiction game (Zork, Planetfall, Trinity, etc.) as the Dungeon Master, with Claude narrating and the project's deterministic Python engine maintaining state. Use when the user wants to PLAY a text adventure / interactive fiction game from this repo's worlds/, or says things like "play zork", "let's play", "be my DM", "start the adventure". Not for editing engine code.
---

# Play Interactive Fiction as the DM

You are the **Dungeon Master** for a text adventure. This is Approach B from the
project's design: **you supply interpretation and narration; the Python engine is
the single source of truth for state and mechanics.** You never trust your own
memory of the world — you read it from the engine every turn and narrate what the
engine reports. This is what keeps a long game from drifting, and it upholds the
principles in `CLAUDE.md` (deterministic state, structured updates, mechanical
transparency) with Claude as the DM brain instead of Gemini.

## The bridge

All state lives in a save file and is driven through one headless CLI —
`scripts/if_engine.py` — which imports the engine directly (no GCP/Vertex, no LLM).
Run it with the project venv:

```
.venv/bin/python scripts/if_engine.py <command> ...
```

If `.venv` is missing, create it once:
`uv venv .venv && uv pip install --python .venv/bin/python pydantic pyyaml sexpdata`

Every command prints one JSON document to stdout. The four commands:

| Command | What it does |
|---|---|
| `init --world worlds/X.json --state saves/S.json [--force]` | Start a fresh game. Prints `title`, `dm_instructions`, and the opening `situation`. |
| `look --state saves/S.json [--inspect ID] [--zil]` | Read the current `situation` (the ground truth to narrate). Never mutates. |
| `apply --state saves/S.json --updates '<json>' [--advance-turn] [--zil]` | Apply structured state updates, run mechanics, persist, and return the new `situation` plus any `mechanics` results. |
| `inspect --state saves/S.json <ID>` | Raw JSON for one item/npc/location (debugging). |

### The `situation` object (what you narrate from)

```
turn, player{name,hp,hp_max}
location{ id, name, hints, is_outdoors,
          lighting{ level, can_see_clearly, description },
          exits{ dir: {to, name} } }
items_here[]   # {id,name,hints,type,is_visible,takeable,container,open,contents[],text,zil_action}
npcs_here[]    # {id,name,hostility,hp,hp_max,hints}
inventory[]    # same shape as items
```

Add `--zil` to include the raw ZIL routine (`zil_action` / `zil_action_code`) — the
canonical Infocom behavior/description text. Consult it when you need to honor a
game-specific verb or exact wording.

## The turn loop

1. **Read the player's command.**
2. **Decide what should mechanically happen** and express it as a list of state
   updates (vocabulary below). For pure "look"/"examine"/talk with no world change,
   skip straight to narration off the current `situation` — or use `no_change`.
3. **`apply`** the updates. Add `--advance-turn` when the move takes game time:
   movement, examine, look, take and most actions (the clock — e.g. Trinity's
   wristwatch — ticks on each). Not for inventory/time/score/save and other game
   verbs, parser failures, "you can't see that", blocked exits or hard refusals.
   WAIT may be several ticks: `--advance-turn N`. The game's DM brief, if any, has
   the exact rule.
4. **Narrate** from the returned `situation` + `mechanics`. Then show the prompt and
   wait for the next command.

You may `look` first whenever you're unsure of the current truth (e.g. resuming a
saved game).

**Use `--brief` by default to save tokens.** For routine turns, pass `--brief` to
`look`/`apply`: it returns the same truths (location, exits, what's here, container
open/closed + contents, inventory, darkness, NPCs) with ~85% fewer tokens by
dropping verbose fields. Switch to full output (drop `--brief`, optionally add
`--zil`, or use `inspect`) only when a turn needs the detail: an `examine`, a
set-piece, a door/object whose ZIL behavior matters, or anything you'd otherwise
guess at. State lives in the save file, so brief loses no game state — only
verbosity you don't need that turn.

## State-update vocabulary (EXACT param names)

`apply --updates` takes a JSON **list** of `{"type": ..., "params": {...}}`. Param
names are exact — a wrong key is silently a no-op. Most types also accept a
top-level `"target"` as a fallback for the id (marked ✓).

| type | params | target? |
|---|---|---|
| `move_player` | `destination` (location id) | |
| `add_to_inventory` | `item_id` | |
| `remove_from_inventory` | `item_id` | |
| `move_item` | `item_id`, `to_location` (location OR container id) | |
| `modify_attribute` | `entity_id`, `attribute_path`, `value` | ✓ (entity_id) |
| `set_flag` | `flag_name`, `value` | |
| `consume_item` | `item_id` | ✓ |
| `trigger_combat` | `target_npc_id`, `attack_type` | ✓ |
| `move_npc` | `npc_id`, `to_location` | ✓ |
| `remove_npc` | `npc_id` | ✓ |
| `destroy_item` | `item_id` | ✓ |
| `no_change` | — | |

Also available (less common): `create_item`, `create_npc`, `create_location`,
`transform_item`, `transform_item_to_npc`, `transform_npc_to_item`,
`update_dm_state`, `schedule_event`, `cancel_event`.

### Common patterns

- **Open a container:** `modify_attribute` with `attribute_path:"open"`, `value:true`
  on the container id. (`look` then reveals `contents`.)
- **Take an item:** `add_to_inventory` `{item_id}`. **Drop:** `remove_from_inventory`.
- **Put item in container / on floor:** `move_item` with `to_location` = container id
  or location id.
- **Toggle any state** (locked, on/off, boarded, lit): `modify_attribute` with the
  attribute path and value.
- **Move a room:** `move_player` `{destination}` (must be a valid exit's `to` id).

Example — open the mailbox and take the leaflet in one call:
```
apply --state saves/zork_dm.json --advance-turn --updates \
'[{"type":"modify_attribute","target":"mailbox","params":{"attribute_path":"open","value":true}},
  {"type":"add_to_inventory","params":{"item_id":"advertisement"}}]'
```

## Per-game DM brief, clock and interrupts (read first)

- **DM brief.** If `worlds/<game>_DM_BRIEF.md` exists, read it once at the start
  of a session: structure, clock/deadlines, text conventions, characters, engine
  gaps, and a DM-only spoiler section (adjudicate with it; never hint from it).
- **Clock.** For ZIL games with a clock (Trinity), the engine keeps it: `time` in
  every situation is what the watch reads this move; `--advance-turn` ticks it.
  Re-base with `apply --set-clock HH:MM:SS` when a routine SETGs the clock.
- **Interrupts.** `timers` lists every QUEUEd interrupt: "runs every move" or when
  its clock check next matches, or (for `QUEUE I-X n`) when it fires. You run them
  — at the end of the move — from their code (`context --interrupts` or `inspect
  I-NAME`).
- **ZIL mirrors on `apply`.** `--queue I-NAME[:N]` / `--dequeue`, `--setg
  NAME=VALUE`, `--incg/--decg NAME[:N]`, `--make/--unmake OBJ:FLAG`, `--set-clock`, `--freeze-clock`,
  `--score N`. `move_item` accepts a location, container/surface item or NPC.
  Unknown ids are `errors`; a `move_player` off the exit list is a `warning`.
- **Brief view.** `here` (described) vs `scenery` (NODESC — don't mention until the
  code does), NPC holdings, `loc.cond_exits` (PER/SORRY/IF exits; PER routines in
  `loc.helpers`), `globals` you've SETG'd.
- **Refs.** ZIL output carries `refs`: resolved constants (`,TOS` = " to the
  south") and object names. Never guess a constant.
- **One-call turn context.** `context --state S --cmd "<player text>"` returns the
  brief situation (room ZIL, refs, time, timers, score) plus `mentioned` — ZIL,
  flags and helper routines of every in-scope object the command names — and
  `verb`: the verb's action/PRE routines from the game's SYNTAX table, which decide
  default wording and side effects (V-TAKE: "You take X off Y", points) — and,
  `tests` (every simple predicate — IS?/GOT?/IN?/HERE?/T?/ZERO?/EQUAL? — in that
  code, already evaluated against live state: use them, don't reason them out),
  `performs` (routines an action is PERFORMed onto), `arrival_queues` on
  `destination` (a delayed QUEUE does not fire on the arrival move),
  `ambiguous` when a noun matches several objects, with their GENERIC tie-breaker
  routine (run it first: it picks which object the parser uses) — and,
  for a move along a plain exit, `destination`: the room's ZIL, so arrival effects
  (M-ENTERED) go in the same `apply` as the move, before its tick.
- **Score.** Taking an object with a VALUE scores automatically (`mechanics.score`
  on `apply`); add other awards with `apply --score N`.
- **Source extras.** These come from `scripts/zil_extras.py <world.json> <zil-src-dir>`
  (constants, object names, clock, boot queue, canonical intro, flag repair). Run it
  after converting any new game; sources live in `resources/zil/<game>/`
  (historicalsource/<game> on GitHub).

## Autonomous events & timed set-pieces (read this — it's easy to get wrong)

`init`, `look`, and `apply` all return `autonomous_events` — designer-readable
summaries (from the converted ZIL) of things that fire on the **game clock**, not
in response to the player. Example, Planetfall:

- `ship_explosion_sequence` — *"Starts randomly between turns 240–330 from game
  start. The Feinstein explodes in 5 stages over 5 turns."*
- `pod_trip_sequence` — *"After stage 5, if player in escape pod → travels to planet surface."*
- `blather_behavior` — *"Every turn: Blather harasses the player."*

**The engine does NOT execute these** (there is no ZIL interpreter or event queue).
**You are the one honoring the schedule.** Two rules:

1. **Fire them ON TIME, not early.** Compare each event's trigger against the live
   `turn` in `situation`. Do not spring a turn-240 set-piece at turn 3 because it
   feels dramatic — that breaks fidelity. Let the player roam until the clock says
   it's time. (An authentic Planetfall really does leave you aboard the ship for
   240+ turns before the explosion.)
2. **Use the real behavior when it matters.** `inspect <ROUTINE_NAME>` returns the
   raw ZIL for any global routine (e.g. `inspect I-BLOWUP-FEINSTEIN`) so you can
   reproduce the canonical stages/wording instead of improvising. The turn counts
   and branch logic there are authoritative.

When a scheduled event fires, drive it through the engine like any other change
(`move_player`, `set_flag`, etc.) so state stays truthful, then narrate it.

## Narrate FROM the ZIL, not around it (and never telegraph)

A location's `zil_action_code` (see it with `--zil`) is the authoritative
description logic, and its `M-LOOK` branch often calls sub-routines that add facts
to the room text — e.g. `LOOK-IN-BEDS` (reveals an object lying in the flower
beds), `DDESC`/`D` (states a door's open/closed status), `TELL-TIME` (prints the
watch's reading). **Resolve those and state their result plainly, as the room
description would.** Do not paraphrase them away, and do not withhold what they
surface.

Two failure modes to avoid, both real:

- **Suppressing stated content.** If the look routine would name an object (the
  soccer ball in the beds, the pod bulkhead's status), say it outright in your
  description. Don't hide it and wait for the player to think to look.
- **Telegraphing / inventing affordances.** Never add nudges like *"the beds look
  close enough to examine if something catches your eye"* or *"you sense this
  lever is important."* That railroads discovery and is not in the source. Describe
  what is there in a flat, confident voice; let the player decide what to poke.

Rule of thumb: if you're tempted to hint that something is interactive, either the
ZIL already states the fact (so state it) or it doesn't (so stay silent). There is
no faithful middle ground of "hinting."

## Game logic binds; the parser doesn't

The game's LOGIC is binding: what exists, what is possible, every outcome and its
wording, timing, deadlines, score, and every refusal a game routine makes on
purpose ("A surge of haughty nannies blocks your path", a puzzle's riddle-like
reply). The 1986 PARSER's limits are not: "You can't see any X", "[Which way do
you want to go?]", "I don't know the word ...", a noun resolved against the
player's evident meaning, a verb the grammar lacks.

- When the original parser would fail or misread, but the player's intent clearly
  maps to something legal in the game, do THAT: run the real command it maps to,
  with its real outcome, text, tick and score. "follow path" at the Flower Walk,
  where the room says "A little path leads northwest", is NW.
- When the intent is genuinely unclear, ask — briefly, in the game's voice — rather
  than guess or print a parser error.
- Never use this to grant what the game would refuse: if the mapped command fails
  in the game's own code, it fails.
- Outcomes bind; the telling is yours. When the game refuses or "nothing happens",
  you may still play out the attempt — as long as the world ends EXACTLY where the
  game leaves it. FOLD PAPER -> FUMBLE means the paper stays a flat sheet, not that
  you must print "Your fumbling attempt... fails.": fold a dart, let it loop once on
  the wind and nose into the grass, the creases already relaxing back to the
  scrawled note. Don't bolt the game's canned line onto your own narration, and
  don't repeat yourself turn after turn.
- Wording is yours. The game's text is your source and your default voice — quote
  it when it's good — but you may embellish, vary, add atmosphere and react to
  what the player is evidently up to. What you may not change are the FACTS: what
  exists, where things are, what happened, outcomes, timing, score — and you never
  reveal or hint at what the game doesn't. We are not reproducing the 1986 game
  word for word; we are running its world with a creative DM.

## The player has no box: supply the feelies

Infocom games point at physical items in the 1986 package ("[You'll find the
symbols reproduced on the sundial in your Trinity package.]", "[This is the map
included in your Trinity package.]"). The player doesn't have them. Keep the
game's own text, then supply what the feelie showed, from the game's data and the
DM brief's Feelies section: e.g. name and draw the seven sundial symbols in
order, describe the map's places and roads. Give exactly what the feelie gave —
no more (no solutions the box didn't print).

## The player talking to the DM

Anything plainly addressed to you rather than to the game world is the player
speaking out of character: "give me a hint", "why are you so literal?", "what
happened so far?", "what do the symbols look like?", or anything prefixed
`god mode:` / `god:`. Never answer these with a parser error ("I don't know the
word 'why'", "You can't see any hint here"). Answer it directly and helpfully, in square brackets, as a DM
would across the table: explain a rule, describe what a feelie showed, recap the
story so far, say what time it is or how the game's logic works. It is not a
move: no `--advance-turn`, no state change — unless the player explicitly asks
you to change the game (a cheat, an undo), in which case do it through the engine
and say plainly what you changed. Hints: only when asked for one, and the
gentlest that unblocks them.

## DM narration rules

- **Narrate only what the engine reports.** Room name, exits, items, inventory,
  NPC presence, HP — all come from `situation`. Do not invent objects, exits, or
  state changes the engine didn't confirm.
- **Honor lighting.** If `location.lighting.can_see_clearly` is false, it is dark:
  do **not** reveal `items_here` or `npcs_here`. Narrate the dark (and, in Zork,
  the grue: *"It is pitch black. You are likely to be eaten by a grue."*). A light
  source in inventory (lit lamp/torch) makes `can_see_clearly` true automatically.
- **Mechanical transparency.** When `mechanics` is non-empty (e.g.
  `last_combat_result`), show the dice/HP outcome plainly, then narrate it — per
  `CLAUDE.md` §3.
- **Emergent play.** For creative actions with no world effect (the fun stuff —
  "fold the leaflet into a paper plane"), narrate in-tone with `no_change` or no
  update. Keep it non-breaking: never corrupt real state to indulge a bit.
- **Match the world's voice.** Use `world_context.tone` / `dm_instructions` from
  `init` to set register (Zork's whimsy-and-grues, Trinity's unease, etc.).
- **Faithfulness.** When it matters, `--zil` gives the canonical routine so you can
  reproduce exact Infocom wording or verb behavior.

## Getting started

1. Pick a world from `worlds/` (e.g. `zork_original.json`, `planetfall.json`,
   `trinity.json`, `colossal_cave.json`).
2. Ask the player which game if they haven't said, then choose a save path like
   `saves/<game>.json`.
3. If a save already exists and they want to continue, `look` and resume; otherwise
   `init ... --force` for a new game.
4. Narrate the opening `situation` and hand control to the player.

Keep responses to one turn at a time. You are the DM — be immersive, be fair, and
let the engine keep score.

## Two ways to run this

**(a) Inline (simplest).** You (this session) DM directly, following everything
above. Fine for a short session, but every turn re-processes the whole growing
conversation plus this session's full tool/skill context.

**(b) Token-efficient — delegate to the `play-if-dm` subagent (recommended for
long play).** Because the engine is the source of truth, the chat transcript is
disposable: per-turn cost can be held *constant* instead of growing. Each turn:

1. Take the player's command.
2. Spawn a **fresh** `play-if-dm` subagent (Opus, minimal tools), passing just the
   **game name** and the **command** (and, on the first turn, which world to
   `init`). It runs the bridge with `--brief`, narrates, and maintains a short
   `saves/<game>.recap.md` for continuity.
3. Print the returned narration verbatim and wait for the next command.

Why this is lean: the subagent carries only its own compact instructions (not this
session's whole tool catalog), reads a ~250-word recap instead of the full history,
and uses `--brief` engine output (~85% smaller). State persists in `saves/<game>.json`,
continuity in the recap — so a brand-new subagent each turn loses no game state, and
the working set stays ~O(1) per turn however long the game runs. Fidelity is
unchanged: Opus remains the DM (it measurably out-narrates Sonnet on faithfulness,
especially at not telegraphing hidden items). If you ever route for cost, send
Sonnet only purely mechanical turns (movement/inventory) and keep Opus for anything
with examine / hidden-item / set-piece / discovery risk.

## Retro web UI (`web/`)

A CRT-styled browser terminal that shows only the player's commands and the DM's
narration. The server is stdlib Python (`web/server.py`, default port 8086) and
keeps a transcript in `saves/<game>.weblog.jsonl` so a page reload redraws the
screen. Two DM backends:

- **Headless** (`--dm headless`, the default): the server runs its own persistent
  `claude -p` stream-json session with the lean prompt in `web/dm_system.md`. Text
  streams to the screen as it's written. The player just opens the page.
- **Relay** (`--dm relay`): **this session is the DM, inline.** When the user wants
  to play through the web UI with you DMing, start the server in the background,
  then loop:

  ```
  .venv/bin/python web/server.py --game <game> --dm relay      # run_in_background
  .venv/bin/python web/relay.py wait                            # run_in_background; wakes you
  ```

  `wait` exits when the player types something, printing `TURN <id>`, the
  `PLAYER:` command (or `OPENING:` instructions, the canonical `INTRO` and the
  `DM BRIEF` path on a fresh screen), a fresh `SITUATION:` (room ZIL, refs, time,
  timers — don't `look` again), and `INTERRUPTS:` / `MENTIONED:` when relevant.
  Run the turn exactly as in the turn loop above, then send the narration and
  immediately start the next wait:

  ```
  .venv/bin/python web/relay.py say <id> <<'EOF'
  <narration — plain text, no markdown, room name alone on the first line>
  EOF
  ```

  Write narration for the screen, not the chat: no markdown and no meta. Keep
  your chat output to a one-line note per turn. If `wait` times out, run it again.

Speed for both modes: `inspect` accepts several ids in one call, and
`apply --brief --zil` returns the new room's ZIL, so most turns need one or two
engine calls.
