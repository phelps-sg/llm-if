# Retro web terminal

A CRT-styled browser front end for playing the converted Infocom worlds with Claude
as the Dungeon Master. The page shows only the player's commands and the DM's
narration; the deterministic engine (`scripts/if_engine.py`) keeps the state.

```
.venv/bin/python web/server.py --game trinity --world worlds/trinity.json --new   # fresh game
.venv/bin/python web/server.py --game trinity                                     # resume
```

Open http://127.0.0.1:8086. Stdlib only; Claude runs on your normal `claude` login.
The default style is `classic` (the original's economy of prose); add
`--style remastered` for richer, sensory descriptions in the original's mood —
the same facts, a fuller telling.

## DM backends

- **headless** (default) — the server keeps one `claude -p` stream-json session
  alive, with the lean prompt in `dm_system.md` plus the game's DM brief
  (`worlds/<game>_DM_BRIEF.md`) if present. Narration streams to the screen.
- **relay** (`--dm relay`) — an interactive Claude Code session is the DM (the
  `play-if` skill, inline). It pulls commands with `web/relay.py wait` and answers
  with `web/relay.py say <id>`.

Every command reaches the DM with the engine's `context` for that turn: the
situation (room ZIL with resolved constants and helper routines, clock, timers,
score, conditional exits), the code of any object the command names, the verb's
own routines from the game's SYNTAX table, and the queued interrupts when they
change — so most turns need one engine call.

Transcripts are kept in `saves/<game>.weblog.jsonl` (a reload redraws the screen).

## Preparing a world

Worlds are rebuilt from the original source, reproducibly (no LLM):

```
.venv/bin/python scripts/build_world.py trinity        # -> worlds/trinity.json
```

It runs `tools/zil_converter`, merges the hand-written context in
`worlds/<game>_context.json`, then `scripts/zil_extras.py`, which adds what the
converter drops: constants and object names, the clock and its interrupts, the boot
queue, the canonical intro, verb syntax, object values, conditional exits, GENERIC
tie-breakers, missing routines and late-era flag names. Source lives in
`resources/zil/<game>/` (from `github.com/historicalsource/<game>`, kept out of git).

## Testing

- `tests/test_if_engine_zil.py` — deterministic engine regressions (no LLM, seconds).
- `scripts/dm_eval.py evals/trinity_gardens.json --model sonnet [--judge sonnet]` —
  plays a scripted route through the real headless DM and checks game LOGIC after
  every step (location, score, inventory, what happened and when — never exact
  wording); improvised steps are rated for creativity by an LLM judge. Reports go to
  `evals/results/` (git-ignored). Costs real model calls.

The DM is meant to be creative, not a reproduction of the 1986 game: the game's
logic binds, its parser and its exact wording don't.
