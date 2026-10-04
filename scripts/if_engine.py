#!/usr/bin/env python3
"""Headless engine bridge for the "Claude Code as DM" architecture (Approach B).

This CLI exposes the deterministic core of the Interactive Fiction engine
WITHOUT any LLM in the loop. Claude Code (the DM) drives it:

    look   -> read the ground-truth situation to narrate from
    apply  -> apply structured state updates, run mechanics, persist, re-read
    inspect-> dump raw JSON for one entity (debugging)
    init   -> create a fresh save-state file from a world

The engine (GameState / ActionProcessor / RuleEngine) remains the single
source of truth for state and mechanics; Claude supplies interpretation and
narration. This preserves the CLAUDE.md principles (deterministic state,
mechanical transparency, structured state updates) while swapping Gemini out
for Claude as the DM brain.

All commands read/write a save-state JSON file (the same format as
GameState.to_file) and print a single JSON document to stdout.

No GCP / Vertex credentials are required: gemini_client is never imported.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make `import src...` work when run as `python scripts/if_engine.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.game_state import GameState  # noqa: E402
from src.engine.action_processor import ActionProcessor  # noqa: E402
from src.rules.rule_engine import RuleEngine  # noqa: E402
from src.rules.dnd_rules import get_all_dnd_rules  # noqa: E402

# The state-update vocabulary understood by ActionProcessor.apply_state_updates.
# Kept here so `apply` can validate before mutating and give Claude a helpful
# error (with the full list) instead of silently ignoring an unknown update.
VALID_UPDATE_TYPES = {
    "move_player",
    "add_to_inventory",
    "remove_from_inventory",
    "move_item",
    "modify_attribute",
    "set_flag",
    "trigger_combat",
    "consume_item",
    "remove_npc",
    "move_npc",
    "create_item",
    "transform_item",
    "transform_item_to_npc",
    "transform_npc_to_item",
    "destroy_item",
    "create_location",
    "create_npc",
    "update_dm_state",
    "schedule_event",
    "cancel_event",
    "no_change",
}

# Flags the engine sets during state updates that carry mechanics results the
# DM must narrate (see CLAUDE.md "Flags Pattern for Deferred Narration").
MECHANICS_FLAGS = [
    "last_combat_result",
    "npc_actions_result",
    "item_creation_result",
    "combat_result",
]


# --- ZIL game clock & interrupt queue ---------------------------------------
# Populated by scripts/zil_extras.py (world_context.clock / boot_queue). The
# engine keeps the clock and the QUEUEd-interrupt list in flags so they persist
# in the save; the DM still runs each interrupt's routine, but now sees exactly
# what time it is and when each clock-gated interrupt next checks.
CLOCK_FLAG = "zil_clock"   # seconds since midnight
QUEUE_FLAG = "zil_queue"   # names of QUEUEd interrupt routines
DELAY_FLAG = "zil_queue_delay"   # interrupt -> ticks until it fires (QUEUE I-X n, n>0)
FROZEN_FLAG = "zil_clock_frozen"  # FREEZE?: moves still count, the clock doesn't move
SETG_FLAG = "zil_setg"            # ZIL globals the DM has SETG'd (initial values: zil_globals)
# zil_flags <-> engine attributes kept in sync by --make/--unmake
FLAG_SYNC = {"takeable": "takeable", "container": "container", "surface": "surface",
             "opened": "open", "locked": "locked", "transparent": "transparent",
             "worn": "worn", "doorlike": "is_door"}
SCORE_FLAG = "score"
CLAIMED_FLAG = "value_claimed"        # items whose VALUE has been awarded
NOTIFIED_FLAG = "do_score_notified"   # the one-time NOTIFY note has been shown
# Matches both the converter's quoted form ("D" ",X") and raw ZIL (D ,X).
_REF_RE = re.compile(r'\b(?:D|A|THE|CTHE)"?\s+"?,([A-Z0-9?!\-]+)|,([A-Z0-9?!\-]+)')


def _init_clock(gs: GameState) -> None:
    wc = gs.world_context or {}
    cfg = wc.get("clock")
    if cfg and CLOCK_FLAG not in gs.flags:
        h, m, sec = cfg["start"]
        gs.flags[CLOCK_FLAG] = h * 3600 + m * 60 + sec
    if wc.get("boot_queue") and QUEUE_FLAG not in gs.flags:
        gs.flags[QUEUE_FLAG] = list(wc["boot_queue"])


def _fmt_time(t: int) -> str:
    """As the game's TELL-TIME prints it: 12-hour, h:mm:ss am/pm."""
    h, rem = divmod(t % 86400, 3600)
    m, sec = divmod(rem, 60)
    h12 = h - 12 if h > 12 else (12 if h == 0 else h)
    return f"{h12}:{m:02d}:{sec:02d} {'pm' if h > 11 else 'am'}"


def _parse_time(text: str) -> int:
    h, m, sec = (int(x) for x in text.split(":"))
    return h * 3600 + m * 60 + sec


def _clock_view(gs: GameState) -> Dict[str, Any]:
    """`time` (what the watch reads this move) and `timers` (each QUEUEd
    interrupt: when its clock check next matches, or that it runs every move)."""
    out: Dict[str, Any] = {}
    if (gs.world_context or {}).get("zil_syntax"):
        out["score"] = gs.flags.get(SCORE_FLAG, 0)
    t = gs.flags.get(CLOCK_FLAG)
    cfg = (gs.world_context or {}).get("clock") or {}
    if t is not None:
        out["time"] = _fmt_time(t) + (" (frozen)" if gs.flags.get(FROZEN_FLAG) else "")
    if gs.flags.get(SETG_FLAG):
        out["globals"] = gs.flags[SETG_FLAG]
    queued = gs.flags.get(QUEUE_FLAG) or []
    delays = gs.flags.get(DELAY_FLAG) or {}
    if not queued:
        return out
    tick = cfg.get("tick_seconds") or 0
    triggers = cfg.get("triggers") or {}
    timers: Dict[str, str] = {}
    for name in queued:
        if delays.get(name):
            d = delays[name]
            timers[name] = ("fires at the end of THIS move" if d == 1
                            else f"fires at the end of the move {d - 1} moves from now")
            continue
        pts = triggers.get(name)
        if not pts or t is None or not tick or gs.flags.get(FROZEN_FLAG):
            timers[name] = "runs every move"
            continue
        for n in range(0, 4 * 3600 // tick):
            tt = t + n * tick
            if any((tt // 60) % 60 == pm and (ps is None or tt % 60 == ps) for pm, ps in pts):
                timers[name] = f"clock check matches at {_fmt_time(tt)} ({n} moves from now)"
                break
        else:
            timers[name] = "no clock match within 4h"
    out["timers"] = timers
    return out


def zil_refs(gs: GameState, code: str) -> Dict[str, str]:
    """Resolve the constants and object names a ZIL routine references, so the DM
    never guesses at `,TOS` or `D ,MEMORIAL`."""
    wc = gs.world_context or {}
    globals_ = wc.get("zil_globals") or {}
    descs = wc.get("zil_descs") or {}
    refs: Dict[str, str] = {}
    for m in _REF_RE.finditer(code or ""):
        if m.group(1):
            if m.group(1) in descs:
                refs[m.group(1)] = descs[m.group(1)]
        elif isinstance(globals_.get(m.group(2)), str):
            refs["," + m.group(2)] = globals_[m.group(2)]
    return refs


def _build_engine() -> ActionProcessor:
    rule_engine = RuleEngine()
    rule_engine.register_rules(get_all_dnd_rules())
    return ActionProcessor(rule_engine)


def _item_summary(gs: GameState, item_id: str, depth: int = 1) -> Dict[str, Any]:
    """Compact, DM-facing summary of an item (recurses into containers)."""
    item = gs.items.get(item_id)
    if item is None:
        return {"id": item_id, "name": item_id, "missing": True}
    attrs = item.attributes or {}
    summary: Dict[str, Any] = {
        "id": item.id,
        "name": item.name,
        "hints": attrs.get("description_hints"),
        "type": attrs.get("type"),
        "is_visible": attrs.get("is_visible", True),
        "takeable": attrs.get("takeable"),
    }
    if attrs.get("container"):
        summary["container"] = True
        summary["open"] = attrs.get("open", False)
        if attrs.get("open", False) and depth > 0:
            contents = gs.get_items_in_container(item.id)
            summary["contents"] = [
                _item_summary(gs, c.id, depth - 1) for c in contents
            ]
        elif gs.get_items_in_container(item.id):
            # Note that there IS hidden content without revealing it.
            summary["has_hidden_contents"] = True
    elif depth > 0 and gs.get_items_in_container(item.id):
        # Surfaces and other holders (flower beds, tables): contents are in view.
        summary["contents"] = [
            _item_summary(gs, c.id, depth - 1) for c in gs.get_items_in_container(item.id)
        ]
    if attrs.get("type") == "readable" and attrs.get("text"):
        summary["text"] = attrs["text"]
    if attrs.get("locked"):
        summary["locked"] = True
    # Surface any game-specific ZIL behavior so the DM can honor it.
    if attrs.get("zil_action"):
        summary["zil_action"] = attrs["zil_action"]
    return summary


def _autonomous_events(gs: GameState) -> List[Dict[str, Any]]:
    """Designer-readable summaries of the world's timed / autonomous events.

    These come from the ZIL conversion (world_context.game_scripts.events) and
    describe set-pieces that fire on the game clock rather than in response to
    the player -- e.g. Planetfall's ship_explosion_sequence ("turns 240-330").
    The DM must compare these against the live `turn` and fire them faithfully
    ON TIME, not early. The underlying ZIL is not executed by this engine, so
    the DM is the one honoring the schedule.
    """
    scripts = (gs.world_context or {}).get("game_scripts") or {}
    events = scripts.get("events") or []
    out = []
    for e in events:
        if isinstance(e, dict):
            out.append({
                "name": e.get("name"),
                "trigger": e.get("trigger"),
                "description": e.get("description"),
            })
    return out


def _npc_summary(npc) -> Dict[str, Any]:
    attrs = npc.attributes or {}
    return {
        "id": npc.id,
        "name": npc.name,
        "hostility": attrs.get("hostility"),
        "hp": attrs.get("hp"),
        "hp_max": attrs.get("hp_max"),
        "hints": attrs.get("description_hints"),
        "is_visible": attrs.get("is_visible", True),
    }


def build_situation(gs: GameState, verbose_zil: bool = False) -> Dict[str, Any]:
    """The ground truth a DM needs to narrate the current turn."""
    loc = gs.get_player_location()
    if loc is None:
        return {"error": f"player_location '{gs.player_location}' not found"}

    lighting = gs.get_effective_lighting(loc.id)
    can_see = lighting.get("can_see_clearly", True)

    exits: Dict[str, Any] = {}
    for direction, dest_id in (loc.connections or {}).items():
        dest = gs.locations.get(dest_id)
        exits[direction] = {"to": dest_id, "name": dest.name if dest else None}

    location_block: Dict[str, Any] = {
        "id": loc.id,
        "name": loc.name,
        "hints": loc.attributes.get("description_hints"),
        "is_outdoors": loc.attributes.get("is_outdoors"),
        "lighting": {
            "level": lighting.get("level"),
            "can_see_clearly": can_see,
            "description": lighting.get("description"),
        },
        "exits": exits,
    }
    if verbose_zil and loc.attributes.get("zil_action_code"):
        location_block["zil_action_code"] = loc.attributes["zil_action_code"]
        refs = zil_refs(gs, loc.attributes["zil_action_code"])
        if refs:
            location_block["refs"] = refs

    # Items/NPCs physically here. When it is too dark to see, we still report
    # them but flag can_see_clearly=False; the skill instructs the DM not to
    # reveal them to the player in that case (grue territory).
    items_here = [_item_summary(gs, i.id) for i in gs.get_items_at_location(loc.id)]
    npcs_here = [_npc_summary(n) for n in gs.get_npcs_at_location(loc.id)]
    inventory = [_item_summary(gs, item_id) for item_id in gs.player.inventory]

    return {
        "turn": gs.turn_count,
        **_clock_view(gs),
        "location": location_block,
        "items_here": items_here,
        "npcs_here": npcs_here,
        "inventory": inventory,
        "player": {
            "name": gs.player.name,
            "hp": gs.player.attributes.get("hp"),
            "hp_max": gs.player.attributes.get("hp_max"),
        },
    }


def build_brief(gs: GameState, zil: bool = False) -> Dict[str, Any]:
    """A token-lean situation for routine turns. Same TRUTHS as build_situation
    (location, exits, what's here, container states, inventory, darkness) but
    strips verbose/redundant fields (hints, type flags, per-item ZIL, full
    attribute dumps). Use the full build_situation only when a turn needs the
    extra detail (a set-piece, a door's ZIL, an examine). Gameplay is unaffected:
    the authoritative state still lives in the save file and can be re-`look`ed.
    """
    loc = gs.get_player_location()
    if loc is None:
        return {"error": f"player_location '{gs.player_location}' not found"}
    can_see = gs.get_effective_lighting(loc.id).get("can_see_clearly", True)

    def brief_item(item_id: str) -> Any:
        it = gs.items.get(item_id)
        if it is None:
            return item_id
        attrs = it.attributes or {}
        # NODESC contents (a gnomon in the sundial, a ball lodged in a tree) are
        # not described until the code says so.
        inner = [x for x in gs.get_items_in_container(it.id)
                 if "nodesc" not in ((x.attributes or {}).get("zil_flags") or [])]
        if attrs.get("container"):
            entry: Dict[str, Any] = {"name": it.name}
            if attrs.get("open") or attrs.get("transparent"):
                if inner:
                    entry["contains"] = [x.name for x in inner]
            else:
                entry["closed"] = True
            return entry
        if inner:  # surfaces / holders: what's on or in them is in view
            return {"name": it.name, "holds": [x.name for x in inner]}
        return it.name

    here, scenery = [], []
    for i in gs.get_items_at_location(loc.id):
        # NODESC objects aren't auto-described: mention them only when the room's
        # ZIL (or the player) brings them up — e.g. a white door that the code
        # hasn't revealed yet.
        flags = (i.attributes or {}).get("zil_flags") or []
        (scenery if "nodesc" in flags else here).append(brief_item(i.id))
    out: Dict[str, Any] = {
        "turn": gs.turn_count,
        **_clock_view(gs),
        "loc": {
            "id": loc.id,
            "name": loc.name,
            "exits": {d: dst for d, dst in (loc.connections or {}).items()},
        },
        "here": here,
        "inv": [brief_item(i) for i in gs.player.inventory],
    }
    if scenery:
        out["scenery"] = scenery
    cond = loc.attributes.get("zil_exits")
    if cond:
        out["loc"]["cond_exits"] = cond
    if zil and loc.attributes.get("zil_action_code"):
        # The room's canonical description routine, so a move can be narrated
        # without a second `look --zil` round trip.
        out["loc"]["zil"] = loc.attributes["zil_action_code"]
        refs = zil_refs(gs, loc.attributes["zil_action_code"])
        if refs:
            out["loc"]["refs"] = refs
        per = " ".join(f"<{v.split()[1]}" for v in (cond or {}).values() if v.startswith("PER "))
        helpers = small_helpers(gs, loc.attributes["zil_action_code"] + " " + per)
        if helpers:
            out["loc"]["helpers"] = helpers
    if not can_see:
        out["dark"] = True
    npcs = gs.get_npcs_at_location(loc.id)
    if npcs:
        listed: List[Any] = []
        for n in npcs:
            held = [gs.items[i].name for i, h in gs.item_locations.items() if h == n.id and i in gs.items]
            flags = (n.attributes or {}).get("zil_flags") or []
            entry: Any = n.name
            if held or "nodesc" in flags:
                entry = {"name": n.name}
                if held:
                    entry["holds"] = held
                if "nodesc" in flags:
                    entry["nodesc"] = True
            listed.append(entry)
        out["npcs"] = listed
    return out


def _pop_mechanics(gs: GameState) -> Dict[str, Any]:
    """Pull any pending mechanics results out of flags (deferred narration)."""
    mechanics: Dict[str, Any] = {}
    for flag in MECHANICS_FLAGS:
        if flag in gs.flags:
            mechanics[flag] = gs.flags.pop(flag)
    return mechanics


def _load(state_path: str) -> GameState:
    p = Path(state_path)
    if not p.exists():
        raise FileNotFoundError(
            f"No save-state at '{state_path}'. Run `init --world <world.json> "
            f"--state {state_path}` first."
        )
    gs = GameState.from_file(state_path)
    _init_clock(gs)
    return gs


def cmd_init(args: argparse.Namespace) -> Dict[str, Any]:
    world = Path(args.world)
    if not world.exists():
        return {"ok": False, "error": f"World file not found: {args.world}"}
    state = Path(args.state)
    if state.exists() and not args.force:
        return {
            "ok": False,
            "error": f"Save-state already exists at {args.state}. "
            f"Pass --force to overwrite (starts a new game).",
        }
    state.parent.mkdir(parents=True, exist_ok=True)
    # A world file IS a valid GameState document, so a copy is a fresh save.
    shutil.copyfile(world, state)
    gs = _load(args.state)
    if args.start_location:
        if args.start_location not in gs.locations:
            return {"ok": False, "error": f"Unknown start location '{args.start_location}'"}
        gs.player_location = args.start_location
    gs.to_file(args.state)  # persists the clock/queue seeded by _load
    return {
        "ok": True,
        "action": "init",
        "world": args.world,
        "state": args.state,
        "title": (gs.world_context or {}).get("title"),
        "intro": (gs.world_context or {}).get("intro"),
        "dm_instructions": (gs.world_context or {}).get("dm_instructions"),
        "autonomous_events": _autonomous_events(gs),
        "situation": build_situation(gs, verbose_zil=args.zil),
    }


def cmd_look(args: argparse.Namespace) -> Dict[str, Any]:
    gs = _load(args.state)
    if getattr(args, "brief", False):
        result: Dict[str, Any] = {"ok": True, "action": "look", "situation": build_brief(gs, zil=args.zil)}
        events = _autonomous_events(gs)
        if events:
            result["autonomous_events"] = events
    else:
        result = {
            "ok": True,
            "action": "look",
            "autonomous_events": _autonomous_events(gs),
            "situation": build_situation(gs, verbose_zil=args.zil),
        }
    if args.inspect:
        result["inspect"] = _inspect(gs, args.inspect)
    return result


def _inspect(gs: GameState, entity_id: str) -> Dict[str, Any]:
    res = _inspect_raw(gs, entity_id)
    data = res.get("data") or {}
    code = data.get("zil_code") or (data.get("attributes") or {}).get("zil_action_code")
    if code:
        refs = zil_refs(gs, code)
        if refs:
            res["refs"] = refs
    return res


def _inspect_raw(gs: GameState, entity_id: str) -> Dict[str, Any]:
    if entity_id in gs.items:
        return {"kind": "item", "data": gs.items[entity_id].model_dump()}
    if entity_id in gs.npcs:
        return {"kind": "npc", "data": gs.npcs[entity_id].model_dump()}
    if entity_id in gs.locations:
        return {"kind": "location", "data": gs.locations[entity_id].model_dump()}
    # Named global ZIL routine (timed interrupts, verbs, etc.) — the canonical
    # behavior for set-pieces like I-BLOWUP-FEINSTEIN. Not executed by this
    # engine; returned so the DM can adjudicate faithfully.
    routines = (gs.world_context or {}).get("global_routines") or {}
    if entity_id in routines:
        r = routines[entity_id]
        code = r.get("zil_code") if isinstance(r, dict) else r
        return {"kind": "routine", "data": {"name": entity_id, "zil_code": code}}
    return {"kind": None, "error": f"No item/npc/location/routine with id '{entity_id}'"}


def cmd_inspect(args: argparse.Namespace) -> Dict[str, Any]:
    gs = _load(args.state)
    if len(args.entity) == 1:
        return {"ok": True, "action": "inspect", "entity": args.entity[0],
                "result": _inspect(gs, args.entity[0])}
    # Several ids in one call: one round trip instead of N.
    return {"ok": True, "action": "inspect",
            "results": {e: _inspect(gs, e) for e in args.entity}}


# --- context: one call that front-loads a turn ------------------------------
CODE_CAP = 6000        # chars of ZIL per object/routine before we say "inspect it"
HELPER_CAP = 3000      # only small helper routines are inlined
VERB_ABBREVS = {"X": "EXAMINE", "L": "LOOK", "I": "INVENTORY", "Z": "WAIT", "G": "AGAIN",
                "Q": "QUIT", "GET": "GET"}
DIRECTIONS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "U", "D", "UP", "DOWN", "IN", "OUT",
              "NORTH", "SOUTH", "EAST", "WEST", "NORTHEAST", "NORTHWEST", "SOUTHEAST",
              "SOUTHWEST"}
_CALL_RE = re.compile(r'\("([A-Z][A-Z0-9?\-]+)"|<([A-Z][A-Z0-9?\-]+)')


def _scope_ids(gs: GameState) -> List[str]:
    loc = gs.get_player_location()
    ids: List[str] = []

    def add(item_id: str, depth: int = 2) -> None:
        if item_id in ids:
            return
        ids.append(item_id)
        if depth:
            for c in gs.get_items_in_container(item_id):
                add(c.id, depth - 1)

    if loc is not None:
        for it in gs.get_items_at_location(loc.id):
            add(it.id)
        ids += [n.id for n in gs.get_npcs_at_location(loc.id)]
    for item_id in gs.player.inventory:
        add(item_id)
    # ZIL GLOBAL-OBJECTS are in scope everywhere (PATH, SKY, SUN, the gates...);
    # their routines decide what they mean here (often CANT-SEE-ANY elsewhere).
    for item_id, where in gs.item_locations.items():
        if where == "global_objects" and item_id not in ids:
            ids.append(item_id)
    return ids


def _words_for(entity) -> set:
    attrs = entity.attributes or {}
    words = {w.lower() for w in (attrs.get("zil_synonyms") or [])}
    words |= {w.lower() for w in (attrs.get("zil_adjectives") or [])}
    words |= set(re.findall(r"[a-z]+", (entity.name or "").lower()))
    return words - {"the", "a", "an", "of", "your"}


def small_helpers(gs: GameState, code: str) -> Dict[str, str]:
    """The small routines a piece of ZIL calls (LOOK-IN-BEDS, TELL-TIME...)."""
    routines = (gs.world_context or {}).get("global_routines") or {}
    helpers: Dict[str, str] = {}
    for name in dict.fromkeys(a or b for a, b in _CALL_RE.findall(code or "")):
        r = routines.get(name)
        rc = (r.get("zil_code") if isinstance(r, dict) else r) or ""
        if rc and len(rc) <= HELPER_CAP:
            helpers[name] = rc
    return helpers


def mentioned_objects(gs: GameState, command: str) -> Dict[str, Any]:
    """Objects in scope that the command names, with their ZIL, resolved refs and
    the small helper routines they call — so the DM rarely needs `inspect`."""
    words = set(re.findall(r"[a-z]+", command.lower()))
    routines = (gs.world_context or {}).get("global_routines") or {}
    out: Dict[str, Any] = {}
    for eid in _scope_ids(gs):
        ent = gs.items.get(eid) or gs.npcs.get(eid)
        if ent is None or not (words & _words_for(ent)):
            continue
        out[eid] = _object_entry(gs, eid, ent, routines)
    return out


def ambiguities(gs: GameState, command: str, mentioned: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Nouns that match several objects in scope. The real parser resolves these
    with the objects' GENERIC routine (e.g. "path" at the Flower Walk ->
    GENERIC-WALK-F picks the Flower Walk, not PATH) before any action runs."""
    routines = (gs.world_context or {}).get("global_routines") or {}
    words = re.findall(r"[a-z]+", command.lower())
    found = []
    for w in dict.fromkeys(words):
        cands = [eid for eid in mentioned
                 if w in (_synonyms_of(gs.items.get(eid) or gs.npcs.get(eid)))]
        if len(cands) < 2:
            continue
        entry: Dict[str, Any] = {"word": w, "candidates": cands}
        resolvers: Dict[str, str] = {}
        for eid in cands:
            ent = gs.items.get(eid) or gs.npcs.get(eid)
            g = (ent.attributes or {}).get("zil_generic") if ent else None
            r = routines.get(g) if g else None
            rc = (r.get("zil_code") if isinstance(r, dict) else r) or ""
            if g and rc:
                resolvers[g] = rc[:CODE_CAP]
        if resolvers:
            entry["generic"] = resolvers
        else:
            entry["note"] = "no GENERIC routine: the parser would ask which one you mean"
        found.append(entry)
    return found


def _synonyms_of(ent) -> set:
    """Nouns only (synonyms + name's last word) — adjectives don't make a match."""
    if ent is None:
        return set()
    attrs = ent.attributes or {}
    nouns = {w.lower() for w in (attrs.get("zil_synonyms") or [])}
    name_words = re.findall(r"[a-z]+", (ent.name or "").lower())
    if name_words:
        nouns.add(name_words[-1])
    return nouns


def _object_entry(gs: GameState, eid: str, ent, routines: Dict[str, Any]) -> Dict[str, Any]:
    attrs = ent.attributes or {}
    code = attrs.get("zil_action_code") or ""
    entry: Dict[str, Any] = {"name": ent.name}
    flags = attrs.get("zil_flags")
    if flags:
        entry["flags"] = flags
    if code:
        entry["zil"] = code[:CODE_CAP]
        if len(code) > CODE_CAP:
            entry["zil_truncated"] = f"{len(code)} chars; inspect {eid} for the rest"
        refs = zil_refs(gs, code)
        if refs:
            entry["refs"] = refs
        helpers = small_helpers(gs, code)
        if helpers:
            entry["helpers"] = helpers
    return entry


def verb_routines(gs: GameState, command: str) -> Optional[Dict[str, Any]]:
    """The verb's own routines (action + PRE-action, from the game's SYNTAX table)
    and the helpers they call — these decide the default wording and side effects
    (V-TAKE's "You take X off Y", its scoring...) that object routines don't."""
    syn = (gs.world_context or {}).get("zil_syntax") or {}
    verbs, synonyms = syn.get("verbs") or {}, syn.get("synonyms") or {}
    words = re.findall(r"[a-z?]+", command.lower())
    if not words or not verbs:
        return None
    w = words[0].upper()
    if w in DIRECTIONS or w in ("GO", "WALK", "RUN") and len(words) > 1 and words[1].upper() in DIRECTIONS:
        canon = "WALK"
    else:
        canon = VERB_ABBREVS.get(w, synonyms.get(w, w))
    entries = verbs.get(canon) or []
    if not entries:
        return {"word": w, "verb": canon, "note": "no SYNTAX entry; the parser rejects this verb"}
    cmd_words = {x.upper() for x in words[1:]}
    fit = [e for e in entries
           if (not e.get("prep_first") or (len(words) > 1 and words[1].upper() == e["preps"][0]))
           and all(pp in cmd_words for pp in e.get("preps", []))]
    if fit:
        most = max(len(e.get("preps", [])) for e in fit)
        fit = [e for e in fit if len(e.get("preps", [])) == most]
    else:  # e.g. UNSCREW X — every syntax names an optional tool (FIND TOOL)
        fit = [e for e in entries if not e.get("preps")] or entries
    routines = (gs.world_context or {}).get("global_routines") or {}
    out: Dict[str, Any] = {"word": w, "verb": canon,
                           "syntax": [f"{e['pattern']} = {e['action']}" + (f" {e['pre']}" if e.get("pre") else "")
                                      for e in fit]}
    code: Dict[str, str] = {}
    for e in fit:
        for name in (e.get("pre"), e["action"]):
            r = routines.get(name) if name else None
            rc = (r.get("zil_code") if isinstance(r, dict) else r) or ""
            if rc and name not in code:
                code[name] = rc[:CODE_CAP]
                for h, hc in small_helpers(gs, rc).items():
                    code.setdefault(h, hc)
    out["routines"] = code
    refs: Dict[str, str] = {}
    for rc in code.values():
        refs.update(zil_refs(gs, rc))
    if refs:
        out["refs"] = refs
    return out


_DIR_ALIASES = {"N": "north", "S": "south", "E": "east", "W": "west", "NE": "ne", "NW": "nw",
                "SE": "se", "SW": "sw", "U": "up", "D": "down", "UP": "up", "DOWN": "down",
                "IN": "in", "OUT": "out", "NORTH": "north", "SOUTH": "south", "EAST": "east",
                "WEST": "west", "NORTHEAST": "ne", "NORTHWEST": "nw", "SOUTHEAST": "se",
                "SOUTHWEST": "sw"}


def destination_preview(gs: GameState, command: str) -> Optional[Dict[str, Any]]:
    """For a movement command along a plain exit: the destination room's ZIL, so
    its arrival effects (M-ENTERED: QUEUE I-BLOW 2, MAKE ...) go into the SAME
    apply as the move — before that move's tick, as in the game."""
    words = [w.upper() for w in re.findall(r"[a-z]+", command.lower())]
    if words and words[0] in ("GO", "WALK", "RUN"):
        words = words[1:]
    if not words or words[0] not in _DIR_ALIASES:
        return None
    loc = gs.get_player_location()
    d = _DIR_ALIASES[words[0]]
    dest_id = (loc.connections or {}).get(d) if loc else None
    if not dest_id or dest_id not in gs.locations:
        return None  # blocked or conditional: see loc.cond_exits
    dest = gs.locations[dest_id]
    code = (dest.attributes or {}).get("zil_action_code") or ""
    out: Dict[str, Any] = {"id": dest_id, "name": dest.name}
    if code:
        out["zil"] = code[:CODE_CAP]
        refs = zil_refs(gs, code)
        if refs:
            out["refs"] = refs
        helpers = small_helpers(gs, code)
        if helpers:
            out["helpers"] = helpers
    return out


def cmd_context(args: argparse.Namespace) -> Dict[str, Any]:
    gs = _load(args.state)
    result: Dict[str, Any] = {"ok": True, "action": "context", "situation": build_brief(gs, zil=True)}
    if args.cmd:
        found = mentioned_objects(gs, args.cmd)
        if found:
            result["mentioned"] = found
            amb = ambiguities(gs, args.cmd, found)
            if amb:
                result["ambiguous"] = amb
        verb = verb_routines(gs, args.cmd)
        if verb:
            result["verb"] = verb
        dest = destination_preview(gs, args.cmd)
        if dest:
            result["destination"] = dest
    if args.interrupts:
        routines = (gs.world_context or {}).get("global_routines") or {}
        code = {}
        for name in gs.flags.get(QUEUE_FLAG) or []:
            r = routines.get(name)
            rc = (r.get("zil_code") if isinstance(r, dict) else r) or ""
            if rc:
                code[name] = rc[:CODE_CAP]
                refs = zil_refs(gs, rc)
                if refs:
                    code[name + " refs"] = refs
        if code:
            result["interrupts"] = code
    return result


def _parse_updates(args: argparse.Namespace) -> List[Dict[str, Any]]:
    if args.updates_file:
        raw = Path(args.updates_file).read_text()
    elif args.updates is not None:
        raw = args.updates
    else:
        raise ValueError("apply requires --updates '<json>' or --updates-file <path>")
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("updates must be a JSON list of update objects")
    return data


def cmd_apply(args: argparse.Namespace) -> Dict[str, Any]:
    gs = _load(args.state)
    try:
        updates = _parse_updates(args)
    except (ValueError, json.JSONDecodeError) as e:
        return {"ok": False, "error": f"Could not parse updates: {e}"}

    # Validate update types up front so the DM gets a clear vocabulary error
    # rather than a silently-ignored update.
    bad = [u.get("type") for u in updates if u.get("type") not in VALID_UPDATE_TYPES]
    if bad:
        return {
            "ok": False,
            "error": f"Unknown update type(s): {bad}",
            "valid_types": sorted(VALID_UPDATE_TYPES),
        }

    inv_before = set(gs.player.inventory)
    engine = _build_engine()
    errors: List[str] = []
    try:
        engine.apply_state_updates(updates, gs)
    except Exception as e:  # deterministic engine error — report, don't crash
        errors.append(f"{type(e).__name__}: {e}")
    errors += engine.last_errors

    delays = gs.flags.setdefault(DELAY_FLAG, {})
    for spec in args.queue or []:
        name, _, n = spec.partition(":")
        q = gs.flags.setdefault(QUEUE_FLAG, [])
        if name not in q:
            q.append(name)
        if n and int(n) > 0:
            delays[name] = int(n)   # QUEUE I-X n: fires when n ticks have run
        else:
            delays.pop(name, None)  # -1 / no count: every move
    for name in args.dequeue or []:
        q = gs.flags.get(QUEUE_FLAG) or []
        if name in q:
            q.remove(name)
        delays.pop(name, None)
    initial = (gs.world_context or {}).get("zil_globals") or {}
    for spec, sign in [(x, 1) for x in args.incg or []] + [(x, -1) for x in args.decg or []]:
        name, _, n = spec.partition(":")
        name = name.upper()
        setg = gs.flags.setdefault(SETG_FLAG, {})
        cur = setg.get(name, initial.get(name, 0))
        if not isinstance(cur, int):
            errors.append(f"incg/decg: {name} is not a number ({cur!r})")
            continue
        setg[name] = cur + sign * int(n or 1)
    for spec in args.setg or []:
        name, _, raw = spec.partition("=")
        try:
            val: Any = json.loads(raw)
        except json.JSONDecodeError:
            val = raw
        gs.flags.setdefault(SETG_FLAG, {})[name.upper()] = val
    for spec, on in [(x, True) for x in args.make or []] + [(x, False) for x in args.unmake or []]:
        eid, _, flag = spec.partition(":")
        ent = gs.items.get(eid) or gs.npcs.get(eid) or gs.locations.get(eid)
        if ent is None or not flag:
            errors.append(f"{'make' if on else 'unmake'}: unknown object '{eid}' or missing flag ('OBJ:FLAG')")
            continue
        flags = ent.attributes.setdefault("zil_flags", [])
        flag = flag.lower()
        if on and flag not in flags:
            flags.append(flag)
        elif not on and flag in flags:
            flags.remove(flag)
        if flag in FLAG_SYNC:
            ent.attributes[FLAG_SYNC[flag]] = on
    if args.freeze_clock:
        gs.flags[FROZEN_FLAG] = True
    if args.unfreeze_clock:
        gs.flags.pop(FROZEN_FLAG, None)
    if args.set_clock:
        gs.flags[CLOCK_FLAG] = _parse_time(args.set_clock)

    if args.advance_turn:
        gs.turn_count += args.advance_turn
        # CLOCKER, once per tick: count down delayed interrupts (a one-shot that
        # reaches 0 has fired this tick and leaves the queue), then move the clock
        # unless it is frozen.
        tick = ((gs.world_context or {}).get("clock") or {}).get("tick_seconds") or 0
        for _ in range(args.advance_turn):
            for name in list(delays):
                delays[name] -= 1
                if delays[name] <= 0:
                    delays.pop(name)
                    q = gs.flags.get(QUEUE_FLAG) or []
                    if name in q:
                        q.remove(name)
            if tick and CLOCK_FLAG in gs.flags and not gs.flags.get(FROZEN_FLAG):
                gs.flags[CLOCK_FLAG] += tick

    mechanics = _pop_mechanics(gs)
    # Scoring: V-TAKE awards an object's VALUE the first time it is taken;
    # --score adds points awarded by other routines (UPDATE-SCORE n).
    gained = 0
    claimed = gs.flags.setdefault(CLAIMED_FLAG, [])
    for item_id in set(gs.player.inventory) - inv_before:
        item = gs.items.get(item_id)
        v = ((item.attributes or {}).get("zil_value") if item else 0) or 0
        if v and item_id not in claimed:
            claimed.append(item_id)
            gained += v
    gained += args.score or 0
    if gained:
        gs.flags[SCORE_FLAG] = gs.flags.get(SCORE_FLAG, 0) + gained
        mechanics["score"] = {"gained": gained, "total": gs.flags[SCORE_FLAG],
                              "first_notification": not gs.flags.get(NOTIFIED_FLAG)}
        gs.flags[NOTIFIED_FLAG] = True
    gs.to_file(args.state)

    result: Dict[str, Any] = {
        "ok": not errors,
        "action": "apply",
        "errors": errors,
        "mechanics": mechanics,
    }
    if engine.last_warnings:
        result["warnings"] = engine.last_warnings
    if getattr(args, "brief", False):
        result["situation"] = build_brief(gs, zil=args.zil)
        events = _autonomous_events(gs)
        if events:
            result["autonomous_events"] = events
    else:
        result["applied"] = updates
        result["autonomous_events"] = _autonomous_events(gs)
        result["situation"] = build_situation(gs, verbose_zil=args.zil)
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    def add_zil(sp):
        sp.add_argument("--zil", action="store_true",
                        help="Include raw ZIL routine text (canonical narration/behavior)")

    def add_brief(sp):
        sp.add_argument("--brief", action="store_true",
                        help="Token-lean output for routine turns (same truths, less verbosity)")

    sp = sub.add_parser("init", help="Create a fresh save-state from a world file")
    sp.add_argument("--world", required=True, help="World JSON (e.g. worlds/zork_original.json)")
    sp.add_argument("--state", required=True, help="Save-state file to create")
    sp.add_argument("--start-location", help="Override starting location id")
    sp.add_argument("--force", action="store_true", help="Overwrite an existing save-state")
    add_zil(sp)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("look", help="Report the current situation (ground truth to narrate)")
    sp.add_argument("--state", required=True)
    sp.add_argument("--inspect", help="Also dump raw JSON for this entity id")
    add_zil(sp)
    add_brief(sp)
    sp.set_defaults(func=cmd_look)

    sp = sub.add_parser("apply", help="Apply structured state updates, run mechanics, persist")
    sp.add_argument("--state", required=True)
    sp.add_argument("--updates", help="JSON list of state-update objects")
    sp.add_argument("--updates-file", help="Path to a JSON file with the update list")
    sp.add_argument("--advance-turn", nargs="?", type=int, const=1, default=0, metavar="N",
                    help="End of a move that takes time: advance the turn and tick the "
                         "game clock (N ticks, e.g. WAIT; default 1)")
    sp.add_argument("--queue", action="append", metavar="ROUTINE[:N]",
                    help="QUEUE an interrupt (ZIL QUEUE): ROUTINE runs every move; ROUTINE:N "
                         "fires once when N ticks have run (N=2: end of the next move); repeatable")
    sp.add_argument("--setg", action="append", metavar="NAME=VALUE",
                    help="SETG a ZIL global (JSON value, e.g. IN-PRAM?=true, HCNT=7); repeatable")
    sp.add_argument("--incg", action="append", metavar="NAME[:N]",
                    help="INC a ZIL global by N (default 1), starting from its initial value")
    sp.add_argument("--decg", action="append", metavar="NAME[:N]",
                    help="DEC a ZIL global (e.g. HCNT each tick of I-LONDON-HOLE)")
    sp.add_argument("--make", action="append", metavar="OBJ:FLAG",
                    help="MAKE: set a ZIL flag on an object (e.g. gnomon:boring); repeatable")
    sp.add_argument("--unmake", action="append", metavar="OBJ:FLAG",
                    help="UNMAKE: clear a ZIL flag on an object (e.g. lwdoor:nodesc); repeatable")
    sp.add_argument("--freeze-clock", action="store_true",
                    help="FREEZE?: moves still count but the clock stops (re-base with --set-clock)")
    sp.add_argument("--unfreeze-clock", action="store_true", help="Clear FREEZE?")
    sp.add_argument("--dequeue", action="append", metavar="ROUTINE",
                    help="DEQUEUE an interrupt routine; repeatable")
    sp.add_argument("--score", type=int, metavar="N",
                    help="Add N points (a routine's UPDATE-SCORE); taking a valued item scores itself")
    sp.add_argument("--set-clock", metavar="HH:MM:SS",
                    help="Re-base the game clock, 24h (as the ZIL's SETG HOURS/MINUTES/SECONDS)")
    add_zil(sp)
    add_brief(sp)
    sp.set_defaults(func=cmd_apply)

    sp = sub.add_parser("context", help="Brief situation + ZIL of objects the player's command mentions")
    sp.add_argument("--state", required=True)
    sp.add_argument("--cmd", default="", help="The player's command text")
    sp.add_argument("--interrupts", action="store_true",
                    help="Also include the ZIL of every QUEUEd interrupt")
    sp.set_defaults(func=cmd_context)

    sp = sub.add_parser("inspect", help="Dump raw JSON for one item/npc/location/global-routine")
    sp.add_argument("--state", required=True)
    sp.add_argument("entity", nargs="+", help="Entity id(s) or global ZIL routine name(s) to inspect")
    sp.set_defaults(func=cmd_inspect)

    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = args.func(args)
    except FileNotFoundError as e:
        result = {"ok": False, "error": str(e)}
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("ok", True) else 1)


if __name__ == "__main__":
    main()
