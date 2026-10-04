#!/usr/bin/env python3
"""Post-process a converted ZIL world with facts the converter drops.

Reads the original ZIL source (e.g. a historicalsource/<game> checkout) and patches
the world JSON in place with:

  world_context.zil_globals   string/number GLOBALs and CONSTANTs (",TOS" -> " to the south")
  world_context.zil_descs     DESC of every OBJECT/ROOM ("TOURISTS" -> "tourists")
  world_context.clock         start time, tick per move and clock-gated interrupts, when
                              the game has HOURS/MINUTES/SECONDS globals
  world_context.boot_queue    interrupts QUEUEd at game start (GO / BOOT-SCREEN)
  world_context.intro         the game's own opening text, rendered from its TELL
  item attributes             takeable/container/open/surface/... re-derived from
                              zil_flags, for games (Trinity) whose flag names differ
                              from the classic TAKEBIT/CONTBIT/OPENBIT set

Deterministic, no LLM. Safe to re-run.

    .venv/bin/python scripts/zil_extras.py worlds/trinity.json resources/zil/trinity
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Late-era Infocom flag names -> the attribute the engine understands.
FLAG_ATTRS = {
    "takeable": "takeable", "takebit": "takeable",
    "container": "container", "contbit": "container",
    "surface": "surface", "surfacebit": "surface",
    "openable": "openable",
    "doorlike": "is_door", "doorbit": "is_door",
    "readable": "readable", "readbit": "readable",
    "transparent": "transparent", "transbit": "transparent",
    "clothing": "wearable", "wearbit": "wearable",
    "worn": "worn",
}
OPEN_FLAGS = {"opened", "openbit"}
LOCKED_FLAGS = {"locked", "lockedbit"}

_DEF_RE = re.compile(
    r'<(?:GLOBAL|CONSTANT)\s+([A-Z0-9?!\-]+)(?::\w+)?\s+("(?:[^"\\]|\\.)*"|-?\d+)\s*>', re.S)
_OBJ_RE = re.compile(r'^<(?:OBJECT|ROOM)\s+([A-Z0-9?!\-]+)(.*?)(?=^<)', re.S | re.M)
_DESC_RE = re.compile(r'\(DESC\s+"((?:[^"\\]|\\.)*)"\)', re.S)
_VALUE_RE = re.compile(r'\(VALUE\s+(\d+)\)')
_GENERIC_RE = re.compile(r'\(GENERIC\s+([A-Z0-9?!$\-]+)\)')
_SYNTAX_RE = re.compile(r'<SYNTAX\s+([^=>]+?)=\s*([A-Z0-9?!$\-]+)(?:\s+([A-Z0-9?!$\-]+))?\s*>', re.S)
_DIRS = "NORTH|SOUTH|EAST|WEST|NE|NW|SE|SW|UP|DOWN|IN|OUT"
_EXIT_RE = re.compile(r'\((' + _DIRS + r')\s+(PER\s+[A-Z0-9?!\-]+|SORRY\s+"(?:[^"\\]|\\.)*"'
                      r'|TO\s+[A-Z0-9?!\-]+\s+IF\s+[^)]*)\)', re.S)
_VSYN_RE = re.compile(r'<VERB-SYNONYM\s+([A-Z0-9?!$\-]+)\s+([^>]+)>')
_MIN_SEC_RE = re.compile(r'\("AND" \("EQUAL\?" ",MINUTES" (\d+)\) \("EQUAL\?" ",SECONDS" (\d+)\)\)')
_MIN_RE = re.compile(r'\("EQUAL\?" ",MINUTES" (\d+)\)')
_ZERO_MIN_RE = re.compile(r'\("ZERO\?" ",MINUTES"\)')
_TICK_RE = re.compile(r'"SECONDS" \("\+" ",SECONDS" (\d+)\)')


def zil_string(raw: str) -> str:
    """ZIL string literal -> text: '|' is a newline, bare line breaks are spaces."""
    s = raw.replace('\\"', '"').replace("|\r\n", "\0").replace("|\n", "\0")
    s = re.sub(r"\s*\r?\n\s*", " ", s)
    return s.replace("|", "\0").replace("\0", "\n")


def parse_source(src: Path) -> Dict[str, Dict[str, Any]]:
    globals_: Dict[str, Any] = {}
    descs: Dict[str, str] = {}
    values: Dict[str, int] = {}
    generics: Dict[str, str] = {}
    syntax: Dict[str, List[Dict[str, Any]]] = {}
    exits: Dict[str, Dict[str, str]] = {}
    synonyms: Dict[str, str] = {}
    for f in sorted(src.glob("*.zil")):
        text = f.read_text(errors="replace")
        for name, val in _DEF_RE.findall(text):
            globals_[name] = zil_string(val[1:-1]) if val.startswith('"') else int(val)
        for name, body in _OBJ_RE.findall(text + "\n<"):
            m = _DESC_RE.search(body)
            if m:
                descs[name] = zil_string(m.group(1))
            g = _GENERIC_RE.search(body)
            if g:
                generics[name] = g.group(1)
            v = _VALUE_RE.search(body)
            if v and int(v.group(1)):
                values[name] = int(v.group(1))
            if "(LOC ROOMS)" in body:
                body_nc = re.sub(r';\s*\([^()]*\)', ' ', body)  # drop commented-out props
                for d, spec in _EXIT_RE.findall(body_nc):
                    spec = re.sub(r"\s+", " ", spec)
                    if spec.startswith("SORRY"):
                        spec = "SORRY: " + zil_string(spec[len("SORRY "):].strip()[1:-1])
                    exits.setdefault(name, {})[d.lower()] = spec
        for lhs, action, pre in _SYNTAX_RE.findall(text):
            words = re.sub(r"\([^)]*\)", " ", lhs).split()
            if not words:
                continue
            verb, rest = words[0], words[1:]
            # prepositions: any word that isn't the OBJECT slot marker
            entry = {"pattern": " ".join(words), "action": action,
                     "preps": [w for w in rest if w != "OBJECT"],
                     "prep_first": bool(rest) and rest[0] != "OBJECT"}
            if pre:
                entry["pre"] = pre
            syntax.setdefault(verb, []).append(entry)
        for verb, syns in _VSYN_RE.findall(text):
            for w in syns.split():
                synonyms[w] = verb
    return {"globals": globals_, "descs": descs, "values": values, "exits": exits,
            "generics": generics,
            "syntax": syntax, "synonyms": synonyms}


def source_routines(src: Path) -> Dict[str, str]:
    """Raw text of every <ROUTINE ...> in the source, by name (bracket-matched,
    ignoring brackets inside strings)."""
    out: Dict[str, str] = {}
    for f in sorted(src.glob("*.zil")):
        text = f.read_text(errors="replace")
        for m in re.finditer(r"^<ROUTINE\s+([A-Z0-9?!$\-]+)", text, re.M):
            depth, i, in_str = 0, m.start(), False
            while i < len(text):
                c = text[i]
                if in_str:
                    if c == "\\":
                        i += 1
                    elif c == '"':
                        in_str = False
                elif c == '"':
                    in_str = True
                elif c == "<":
                    depth += 1
                elif c == ">":
                    depth -= 1
                    if depth == 0:
                        out[m.group(1)] = text[m.start():i + 1]
                        break
                i += 1
    return out


def render_tell(tokens: List[Any], g: Dict[str, Any], descs: Dict[str, str]) -> str:
    out: List[str] = []
    it = iter(tokens)
    for tok in it:
        if not isinstance(tok, str):
            continue
        if tok in ("CR", "CRLF"):
            out.append("\n")
        elif tok in ("D", "A", "THE", "CTHE"):
            ref = next(it, "")
            name = descs.get(str(ref).lstrip(","), str(ref).lstrip(",").lower())
            out.append({"D": name, "A": f"a {name}", "THE": f"the {name}",
                        "CTHE": f"The {name}"}[tok])
        elif tok.startswith(","):
            val = g.get(tok[1:])
            out.append(val if isinstance(val, str) else "")
        else:
            out.append(zil_string(tok))
    return "".join(out).strip()


def find_tells(node: Any) -> List[List[Any]]:
    found: List[List[Any]] = []
    if isinstance(node, dict):
        if node.get("op") == "TELL" and isinstance(node.get("text"), list):
            found.append(node["text"])
        for v in node.values():
            found += find_tells(v)
    elif isinstance(node, list):
        for v in node:
            found += find_tells(v)
    return found


def clock_info(world: Dict[str, Any], g: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not all(k in g for k in ("HOURS", "MINUTES", "SECONDS")):
        return None
    routines = world.get("global_routines") or {}
    tick = 0
    for name, r in routines.items():
        m = _TICK_RE.search(r.get("zil_code") or "")
        if m:
            tick = int(m.group(1))
            break
    triggers: Dict[str, List[List[Optional[int]]]] = {}
    for name, r in routines.items():
        code = r.get("zil_code") or ""
        if not name.startswith("I-"):
            continue
        pts: List[List[Optional[int]]] = [[int(a), int(b)] for a, b in _MIN_SEC_RE.findall(code)]
        paired = {p[0] for p in pts}
        pts += [[int(a), None] for a in _MIN_RE.findall(code) if int(a) not in paired]
        if _ZERO_MIN_RE.search(code):
            pts.append([0, None])
        if pts:
            triggers[name] = pts
    return {
        "start": [g["HOURS"], g["MINUTES"], g["SECONDS"]],
        "tick_seconds": tick,
        "triggers": triggers,
        "note": "Seconds advance by tick_seconds at the end of every move (not meta verbs). "
                "triggers = minute[/second] values an interrupt's code tests; it only acts "
                "while QUEUEd and its other conditions hold — read the routine.",
    }


def boot_queue(world: Dict[str, Any]) -> List[str]:
    routines = world.get("global_routines") or {}
    queued: List[str] = []
    for name in ("GO", "BOOT-SCREEN", "START", "INIT"):
        code = (routines.get(name) or {}).get("zil_code") or ""
        for q in re.findall(r'\("QUEUE" "([^"]+)" (-?\d+)\)', code):
            if q[0] not in queued:
                queued.append(q[0])
    return queued


def fix_flags(world: Dict[str, Any]) -> int:
    changed = 0
    for item in (world.get("items") or {}).values():
        attrs = item.get("attributes") or {}
        flags = set(attrs.get("zil_flags") or [])
        for f in flags:
            key = FLAG_ATTRS.get(f)
            if key and not attrs.get(key):
                attrs[key] = True
                changed += 1
        if flags & OPEN_FLAGS and (attrs.get("container") or attrs.get("is_door")) and not attrs.get("open"):
            attrs["open"] = True
            changed += 1
        if flags & LOCKED_FLAGS and not attrs.get("locked"):
            attrs["locked"] = True
            changed += 1
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world", type=Path)
    ap.add_argument("src", type=Path, help="directory of the game's original .zil files")
    args = ap.parse_args()

    world = json.loads(args.world.read_text())
    src = parse_source(args.src)
    wc = world.setdefault("world_context", {})
    wc["zil_globals"] = src["globals"]
    wc["zil_descs"] = src["descs"]
    wc["zil_syntax"] = {"verbs": src["syntax"], "synonyms": src["synonyms"]}
    # Exits the converter can't express: PER routines, SORRY refusals, TO ... IF.
    cond = 0
    for name, ex in src["exits"].items():
        loc = (world.get("locations") or {}).get(name.lower().replace("-", "_"))
        if loc is not None:
            loc.setdefault("attributes", {})["zil_exits"] = ex
            cond += len(ex)
    # The parser's tie-breaker when a word matches several objects (GENERIC).
    for name, routine in src["generics"].items():
        ent = ((world.get("items") or {}).get(name.lower().replace("-", "_"))
               or (world.get("npcs") or {}).get(name.lower().replace("-", "_")))
        if ent is not None:
            ent.setdefault("attributes", {})["zil_generic"] = routine
    # Points an object is worth when first taken (V-TAKE awards P?VALUE).
    valued = 0
    for name, v in src["values"].items():
        item = (world.get("items") or {}).get(name.lower().replace("-", "_"))
        if item is not None:
            item.setdefault("attributes", {})["zil_value"] = v
            valued += 1

    clock = clock_info(world, src["globals"])
    if clock:
        wc["clock"] = clock
    wc["boot_queue"] = boot_queue(world)

    for name in ("BOOT-SCREEN", "GO"):
        r = (world.get("global_routines") or {}).get(name)
        tells = [t for t in find_tells((r or {}).get("zil_json")) if sum(len(x) for x in t if isinstance(x, str)) > 200]
        if tells:
            if wc.get("intro") and "intro_packaging" not in wc:
                wc["intro_packaging"] = wc["intro"]
            wc["intro"] = render_tell(tells[0], src["globals"], src["descs"])
            break

    # Routines the converter dropped (Trinity: I-SHADOW, GO-TO-LONG-WATER, ...).
    routines = world.setdefault("global_routines", {})
    added = []
    for name, code in source_routines(args.src).items():
        if name not in routines:
            routines[name] = {"zil_code": code, "source": "zil_extras (raw ZIL)"}
            added.append(name)

    n = fix_flags(world)
    args.world.write_text(json.dumps(world, indent=2))
    print(json.dumps({
        "globals": len(src["globals"]), "descs": len(src["descs"]),
        "clock": {k: clock[k] for k in ("start", "tick_seconds")} if clock else None,
        "clock_triggers": sorted(clock["triggers"]) if clock else [],
        "boot_queue": wc["boot_queue"], "flag_attrs_set": n,
        "routines_added": len(added), "routines_added_sample": added[:12],
        "syntax_verbs": len(src["syntax"]), "valued_items": valued, "conditional_exits": cond,
        "generics": len(src["generics"]),
        "values_unmatched": sorted(set(src["values"]) - {k.upper().replace("_", "-") for k in (world.get("items") or {})}),
        "intro": (wc.get("intro") or "")[:160],
    }, indent=2))


if __name__ == "__main__":
    main()
