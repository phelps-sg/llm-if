#!/usr/bin/env python3
"""Scripted evaluation of an LLM Dungeon Master against a game.

Plays a spec of commands through the real headless DM (web/server.py's
HeadlessDM: same prompt, brief and turn context as the web UI) on a fresh save,
and after every step checks deterministic expectations against the engine state
and the narration. Improvised ("adhoc") steps can also be rated by an LLM judge.

    .venv/bin/python scripts/dm_eval.py evals/trinity_gardens.json --model sonnet
    .venv/bin/python scripts/dm_eval.py evals/trinity_gardens.json --model opus --judge sonnet

Spec (JSON): {"game", "world", "steps": [{"cmd", "expect": {...}, "adhoc", "repeat_until"}]}
  expect: loc (location id) · score / score_min · contains / not_contains (regexes,
          case-insensitive) · inv_has / inv_lacks (item ids)
  repeat_until: {"contains": regex, "max": n}  — re-send cmd (e.g. "wait") until seen
"cmd": "__open" asks for the opening screen.

Writes evals/results/<spec>-<model>-<timestamp>.{json,md}. Costs real model calls.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("dm_server", REPO / "web" / "server.py")
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)  # type: ignore[union-attr]


def run_turn(dm, cmd: str) -> Dict[str, Any]:
    t0, tools, text = time.time(), 0, None
    opening = cmd == "__open"
    for ev in dm.turn(server.OPENING_PROMPT if opening else cmd, opening):
        if ev["t"] == "busy":
            tools += 1
        elif ev["t"] in ("done", "error"):
            text = ev["d"] if ev["t"] == "done" else "ERROR: " + ev["d"]
    dm.log(None if opening else cmd, text or "")
    return {"text": text or "", "seconds": round(time.time() - t0, 1), "tools": tools}


def state_of(state: Path) -> Dict[str, Any]:
    data = json.loads(state.read_text())
    flags = data.get("flags") or {}
    return {"loc": data.get("player_location"), "score": flags.get("score", 0),
            "inv": (data.get("player") or {}).get("inventory") or [],
            "turn": data.get("turn_count")}


def check(expect: Dict[str, Any], text: str, st: Dict[str, Any]) -> List[str]:
    fails = []
    if "loc" in expect and st["loc"] != expect["loc"]:
        fails.append(f"loc {st['loc']!r} != {expect['loc']!r}")
    if "score" in expect and st["score"] != expect["score"]:
        fails.append(f"score {st['score']} != {expect['score']}")
    if "score_min" in expect and st["score"] < expect["score_min"]:
        fails.append(f"score {st['score']} < {expect['score_min']}")
    for rx in expect.get("contains", []):
        if not re.search(rx, text, re.I | re.M):
            fails.append(f"missing /{rx}/")
    for rx in expect.get("not_contains", []):
        if re.search(rx, text, re.I | re.M):
            fails.append(f"forbidden /{rx}/")
    for item in expect.get("inv_has", []):
        if item not in st["inv"]:
            fails.append(f"inventory lacks {item}")
    for item in expect.get("inv_lacks", []):
        if item in st["inv"]:
            fails.append(f"inventory has {item}")
    return fails


JUDGE_PROMPT = """You are judging an AI Dungeon Master running the 1986 Infocom game {game}.
The DM must keep the game's LOGIC exact (what exists, what's possible, outcomes,
timing, score) but should not be slavish to the 1986 parser: improvised or
playful commands deserve a creative, in-tone response that changes nothing the
game wouldn't, invents no objects/exits/facts, and never hints at solutions.

Below is the whole session in order, so you know the game state at each point (what
the player holds, where they are, what already happened). Rate ONLY the exchanges
marked [RATE]; the rest are context. Reply with ONLY a JSON list, one object per
[RATE] exchange:
{{"cmd": ..., "creativity": 1-5, "fidelity": 1-5, "invented": [facts the DM made up that matter],
  "note": "one sentence"}}

{exchanges}"""


def judge(model: str, game: str, rows: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    ex = "\n\n".join(("[RATE] " if r["adhoc"] else "") + f">{r['cmd']}\n{r['text']}" for r in rows)
    res = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--strict-mcp-config",
                          JUDGE_PROMPT.format(game=game, exchanges=ex)],
                         capture_output=True, text=True, cwd=REPO)
    m = re.search(r"\[.*\]", res.stdout, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--style", choices=["classic", "remastered"], default="classic")
    ap.add_argument("--judge", metavar="MODEL", help="rate adhoc steps with this model")
    ap.add_argument("--stop-on-fail", action="store_true")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    game = f"eval-{args.spec.stem}-{args.model}-{args.style}"
    state = REPO / "saves" / f"{game}.json"
    res = server.engine("init", "--world", spec["world"], "--state", str(state), "--force")
    if not res.get("ok"):
        sys.exit(res.get("error"))
    dm = server.HeadlessDM(game, state, args.model, True, brief_game=spec["game"], effort=args.effort,
                           style=args.style)

    rows: List[Dict[str, Any]] = []
    try:
        for i, step in enumerate(spec["steps"], 1):
            cmd, expect = step["cmd"], step.get("expect", {})
            until = step.get("repeat_until")
            text, secs, tools, sends = "", 0.0, 0, 0
            while True:
                r = run_turn(dm, cmd)
                text += ("\n" if text else "") + r["text"]
                secs += r["seconds"]; tools += r["tools"]; sends += 1
                if not until or re.search(until["contains"], r["text"], re.I) or sends >= until.get("max", 4):
                    break
            st = state_of(state)
            fails = check(expect, text, st)
            row = {"step": i, "cmd": cmd, "adhoc": bool(step.get("adhoc")), "text": text,
                   "seconds": round(secs, 1), "tools": tools, "sends": sends, **st, "fails": fails}
            rows.append(row)
            mark = "PASS" if not fails else "FAIL"
            print(f"{i:>2} {mark} >{cmd}  [{secs:.1f}s, {tools} tools, {st['loc']}, score {st['score']}]"
                  + ("" if not fails else "  " + "; ".join(fails)), flush=True)
            if fails and args.stop_on_fail:
                break
    finally:
        if dm.proc and dm.proc.poll() is None:
            dm.proc.terminate()

    verdicts = judge(args.judge, spec["game"], rows) if args.judge else None
    checked = [r for r in rows if spec["steps"][r["step"] - 1].get("expect")]
    summary = {"spec": str(args.spec), "model": args.model, "steps": len(rows),
               "checked": len(checked), "passed": sum(1 for r in checked if not r["fails"]),
               "final": {k: rows[-1][k] for k in ("loc", "score", "turn")} if rows else {},
               "seconds_total": round(sum(r["seconds"] for r in rows), 1),
               "seconds_median": sorted(r["seconds"] for r in rows)[len(rows) // 2] if rows else 0}
    out_dir = REPO / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = out_dir / f"{args.spec.stem}-{args.model}-{stamp}"
    base.with_suffix(".json").write_text(json.dumps({"summary": summary, "rows": rows, "judge": verdicts}, indent=2))
    md = [f"# {args.spec.stem} — {args.model} — {stamp}", "",
          f"**{summary['passed']}/{summary['checked']} checks passed** · final {summary['final']} · "
          f"median turn {summary['seconds_median']}s · total {summary['seconds_total']}s", ""]
    for r in rows:
        md.append(f"## {r['step']}. `>{r['cmd']}` — {'adhoc' if r['adhoc'] else ''} "
                  f"{'✅' if not r['fails'] else '❌ ' + '; '.join(r['fails'])}")
        md.append("")
        md.append("```")
        md.append(r["text"])
        md.append("```")
        md.append("")
    if verdicts:
        md.append("## Judge (adhoc steps)")
        md.append("")
        for v in verdicts:
            md.append(f"- `>{v.get('cmd')}` creativity {v.get('creativity')}, fidelity {v.get('fidelity')}"
                      f" — {v.get('note')}" + (f" Invented: {v.get('invented')}" if v.get("invented") else ""))
    base.with_suffix(".md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"report: {base.with_suffix('.md').relative_to(REPO)}")


if __name__ == "__main__":
    main()
