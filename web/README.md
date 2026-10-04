# Retro web terminal

A CRT-styled browser front end for playing the converted Infocom worlds with Claude
as the Dungeon Master. The page shows only the player's commands and the DM's
narration; the deterministic engine (`scripts/if_engine.py`) keeps the state.

```
.venv/bin/python web/server.py --game trinity --world worlds/trinity.json --new   # fresh game
.venv/bin/python web/server.py --game trinity                                     # resume
```

Open http://127.0.0.1:8086. Stdlib only; Claude runs on your normal `claude` login.

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

After converting a game with `tools/zil_converter`, run

```
.venv/bin/python scripts/zil_extras.py worlds/<game>.json resources/zil/<game>
```

with the original source from `github.com/historicalsource/<game>` (kept out of
git). It adds what the converter drops: string constants and object names, the
game clock and its interrupts, the boot queue, the canonical intro, verb syntax,
object point values, conditional exits, missing routines, and late-era flag names.
