#!/usr/bin/env python3
"""Retro-terminal web front end for the Claude-as-DM interactive fiction harness.

Keeps ONE long-lived headless Claude Code process per game
(`claude -p --input-format stream-json --output-format stream-json`), so each
turn pays no process start-up and the prompt cache stays warm. Claude drives
`scripts/if_engine.py` exactly as the play-if skill does; the browser only ever
sees the player's command and the DM's final narration.

    .venv/bin/python web/server.py --game trinity
    .venv/bin/python web/server.py --game zork --world worlds/zork_original.json --new
    .venv/bin/python web/server.py --game trinity --dm relay   # an interactive session DMs

Two DM backends:
  headless (default)  a dedicated `claude -p` process plays DM.
  relay               an interactive Claude Code session plays DM (the play-if skill,
                      inline): it pulls commands with `web/relay.py wait` and answers
                      with `web/relay.py say`.

Stdlib only. Auth comes from your normal `claude` login (subscription).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import queue
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web"
ENGINE = [str(REPO / ".venv/bin/python"), str(REPO / "scripts/if_engine.py")]

OPENING_PROMPT = (
    "The player has just switched on the terminal. Present the opening screen. "
    "If an [intro] block is given (turn 0), print it verbatim first, then the "
    "room as if the player had typed LOOK — render its M-LOOK text from loc.zil, "
    "resolving every ,CONSTANT from loc.refs (,TON is \" to the north\"). Otherwise just describe where the "
    "player is now, as LOOK would. This is not a move: no --advance-turn."
)


def engine(*args: str) -> Dict[str, Any]:
    out = subprocess.run(ENGINE + list(args), cwd=REPO, capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": out.stderr.strip() or out.stdout.strip()}


_seen_queues: Dict[str, List[str]] = {}


# Turn-context blocks the DM sees, in order (all optional except situation).
CONTEXT_BLOCKS = ["out_of_character", "feelie", "interrupts", "mentioned", "ambiguous", "performs",
                  "verb", "destination", "tests"]


def context(state: Path, cmd: str = "", fresh: bool = False) -> Dict[str, Any]:
    """Fresh brief truth (room ZIL, clock, timers) plus the ZIL of any object the
    command names, the verb's routines, evaluated predicates, ... — handed to the DM
    with every command so a turn rarely needs a lookup round trip. The QUEUEd
    interrupts' code is included on a fresh DM and whenever the queue changes."""
    res = engine("context", "--state", str(state), "--cmd", cmd, "--interrupts")
    out: Dict[str, Any] = {"situation": res.get("situation") or {}}
    out.update({k: res[k] for k in CONTEXT_BLOCKS if res.get(k) and k != "interrupts"})
    queue = sorted((out["situation"].get("timers") or {}).keys())
    if res.get("interrupts") and (fresh or _seen_queues.get(str(state)) != queue):
        out["interrupts"] = res["interrupts"]
    _seen_queues[str(state)] = queue
    return out


def opening_intro(state: Path) -> Optional[str]:
    """The game's own intro text, on a fresh game only."""
    data = json.loads(state.read_text())
    if data.get("turn_count"):
        return None
    return (data.get("world_context") or {}).get("intro")


HOW_TO_ANSWER = (
    "Answer what the player MEANS, as a game master at the table would. The game's logic "
    "(what exists, what's possible, outcomes, timing, score) binds; the 1986 parser and its "
    "wording do not. Never reply with a parser error (\"I don't know the word...\", \"You can't "
    "be serious.\", \"You can't see any...\"). If they're talking to you, answer them in "
    "[brackets]. If the game really refuses something, say so in your own voice, with the reason."
)

# A reply that is just a 1986 parser failure, not an answer.
PARSER_ERROR_RE = re.compile(
    r"^\s*(I don't know the word|You can't see any|You can't be serious|What a ridiculous concept|"
    r"That's impossible|\[Which way do you want|I don't understand|That sentence isn't one|"
    r"You used the word|There was no verb)", re.I)


def turn_message(state: Path, text: str, opening: bool = False, fresh: bool = False,
                 recap: str = "") -> str:
    ctx = context(state, "" if opening else text, fresh)
    msg = ""
    intro = opening_intro(state) if opening else None
    if intro:
        msg += f"[intro]\n{intro}\n\n"
    msg += f"[situation]\n{json.dumps(ctx['situation'])}\n\n"
    for k in CONTEXT_BLOCKS:
        if ctx.get(k):
            msg += f"[{k}]\n{json.dumps(ctx[k])}\n\n"
    if recap:
        msg += f"[recent transcript — you are picking up this game mid-play]\n{recap}\n\n"
    msg += f"[how to answer]\n{HOW_TO_ANSWER}\n\n"
    return msg + f"[player]\n{text}"


def dm_brief(game: str) -> Optional[Path]:
    p = REPO / "worlds" / f"{game}_DM_BRIEF.md"
    return p if p.exists() else None


def world_notes(state: Path) -> Dict[str, str]:
    wc = json.loads(state.read_text()).get("world_context") or {}
    notes = []
    for key in ("title", "author", "setting", "tone"):
        if wc.get(key):
            notes.append(f"{key.capitalize()}: {wc[key]}")
    dm = wc.get("dm_instructions")
    if isinstance(dm, list):
        notes.append("DM notes:\n" + "\n".join(f"- {line}" for line in dm))
    elif dm:
        notes.append(f"DM notes: {dm}")
    return {"title": wc.get("title") or state.stem, "notes": "\n".join(notes)}


class Game:
    """Save/transcript bookkeeping shared by both DM backends."""

    def __init__(self, game: str, state: Path, new: bool):
        self.game, self.state = game, state
        self.meta_path = REPO / "saves" / f"{game}.web.json"
        self.log_path = REPO / "saves" / f"{game}.weblog.jsonl"
        self.lock = threading.Lock()
        if new:
            self.meta_path.unlink(missing_ok=True)
            self.log_path.unlink(missing_ok=True)
        self.title = world_notes(state)["title"]

    def status(self) -> Dict[str, Any]:
        s = engine("look", "--state", str(self.state), "--brief").get("situation") or {}
        return {"title": self.title, "loc": (s.get("loc") or {}).get("name", ""), "turn": s.get("turn", 0)}

    def history(self) -> List[Dict[str, str]]:
        if not self.log_path.exists():
            return []
        return [json.loads(l) for l in self.log_path.read_text().splitlines() if l.strip()]

    def log(self, cmd: Optional[str], out: str) -> None:
        with self.log_path.open("a") as f:
            f.write(json.dumps({"cmd": cmd, "out": out}) + "\n")


class RelayDM(Game):
    """An interactive Claude Code session is the DM. Commands queue here until it
    pulls them (GET /api/relay/next); its narration comes back on /api/relay/reply."""

    def __init__(self, game: str, state: Path, new: bool):
        super().__init__(game, state, new)
        self.pending: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.replies: Dict[str, "queue.Queue[str]"] = {}
        self.inflight: Optional[Dict[str, Any]] = None

    def turn(self, text: str, opening: bool = False) -> Iterator[Dict[str, Any]]:
        tid = uuid.uuid4().hex[:8]
        self.replies[tid] = q = queue.Queue()
        brief = dm_brief(self.game)
        self.pending.put({"id": tid, "opening": opening, "cmd": text,
                          "state": str(self.state.relative_to(REPO)),
                          "brief": str(brief.relative_to(REPO)) if brief else None})
        yield {"t": "busy"}
        try:
            yield {"t": "done", "d": q.get()}
        finally:
            self.replies.pop(tid, None)

    def next(self, timeout: float) -> Optional[Dict[str, Any]]:
        # There is only one DM, so a new `wait` means any earlier waiter is gone:
        # re-deliver a turn it took but never answered rather than strand the player.
        job = self.inflight if self.inflight and self.inflight["id"] in self.replies else None
        if job is None:
            try:
                job = self.pending.get(timeout=timeout)
            except queue.Empty:
                return None
        self.inflight = job
        extra = {"intro": opening_intro(self.state)} if job.get("opening") else {}
        opening = bool(job.get("opening"))
        return {**job, **extra, **context(self.state, "" if opening else job["cmd"], fresh=opening)}

    def reply(self, tid: str, text: str) -> bool:
        q = self.replies.pop(tid, None)  # answered now: never re-deliver it
        if q is None:
            return False
        if self.inflight and self.inflight["id"] == tid:
            self.inflight = None
        q.put(text)
        return True


class HeadlessDM(Game):
    """One persistent Claude Code process; one turn at a time."""

    def __init__(self, game: str, state: Path, model: str, new: bool,
                 brief_game: Optional[str] = None, effort: Optional[str] = None):
        super().__init__(game, state, new)
        self.model, self.effort = model, effort
        self.proc: Optional[subprocess.Popen] = None
        self.events: "queue.Queue[Optional[dict]]" = queue.Queue()
        meta = json.loads(self.meta_path.read_text()) if self.meta_path.exists() else {}
        info = world_notes(state)
        rel_state = str(state.relative_to(REPO))
        notes = info["notes"]
        brief = dm_brief(brief_game or game)
        if brief:
            notes += "\n\n" + brief.read_text()
        self.system_prompt = (
            (WEB / "dm_system.md").read_text()
            .replace("{STATE}", rel_state)
            .replace("{WORLD_NOTES}", notes)
        )
        # A changed prompt gets a fresh DM conversation on the same game: resuming
        # the old one lets its old answers outweigh the new rules.
        self.prompt_hash = hashlib.sha256(self.system_prompt.encode()).hexdigest()[:12]
        if meta.get("session_id") and meta.get("prompt") == self.prompt_hash:
            self.session_id, self.resume = meta["session_id"], True
        else:
            self.session_id, self.resume = str(uuid.uuid4()), False
        self.needs_recap = not self.resume and bool(self.history())

    # -- process management -------------------------------------------------
    def _spawn(self) -> None:
        cmd = [
            "claude", "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--include-partial-messages", "--verbose",
            "--model", self.model,
            *(["--effort", self.effort] if self.effort else []),
            "--system-prompt", self.system_prompt,
            "--tools", "Bash",
            "--allowedTools", "Bash(.venv/bin/python scripts/if_engine.py:*)",
            "--strict-mcp-config",
            "--setting-sources", "project",
        ]
        cmd += ["--resume", self.session_id] if self.resume else ["--session-id", self.session_id]
        self.proc = subprocess.Popen(
            cmd, cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self.events = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc, self.events), daemon=True).start()
        threading.Thread(target=self._drain_stderr, args=(self.proc,), daemon=True).start()
        self.meta_path.write_text(json.dumps({"session_id": self.session_id, "prompt": self.prompt_hash}))
        self.resume = True  # any later respawn resumes this session

    @staticmethod
    def _pump(proc: subprocess.Popen, q: "queue.Queue[Optional[dict]]") -> None:
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.strip()
            if line:
                try:
                    q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        q.put(None)  # process exited

    @staticmethod
    def _drain_stderr(proc: subprocess.Popen) -> None:
        for line in proc.stderr:  # type: ignore[union-attr]
            sys.stderr.write(f"[claude] {line}")

    def _alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    # -- a turn -----------------------------------------------------------------
    def turn(self, text: str, opening: bool = False) -> Iterator[Dict[str, Any]]:
        """Yield UI events: text deltas, retract (drop text being replaced), busy, done."""
        fresh = not self._alive()
        if fresh:
            self._spawn()
        recap = ""
        if self.needs_recap:
            recap = "\n".join(f">{h['cmd']}\n{h['out']}" if h.get("cmd") else h["out"]
                              for h in self.history()[-12:])
            self.needs_recap = False
        final = yield from self._exchange(turn_message(self.state, text, opening, fresh, recap))
        if final is None:
            return
        if not opening and PARSER_ERROR_RE.match(final) and len(final) < 240:
            # Guard: a bare 1986 parser error isn't an answer. Ask once for a real one.
            yield {"t": "retract"}
            again = yield from self._exchange(
                f"[correction]\nYour reply \"{final.strip()}\" is a 1986 parser error, not an "
                f"answer. The player typed: \"{text}\". {HOW_TO_ANSWER} Fix any state you "
                f"changed for the wrong reading, then give your real reply — nothing else.")
            if again is None:
                return
            final = again
        yield {"t": "done", "d": final}

    def _exchange(self, content: str):
        """Send one user message; stream events; return the final text (None on error)."""
        msg = {"type": "user", "message": {"role": "user", "content": content}}
        self.proc.stdin.write(json.dumps(msg) + "\n")  # type: ignore[union-attr]
        self.proc.stdin.flush()  # type: ignore[union-attr]
        streamed = ""
        while True:
            ev = self.events.get()
            if ev is None:
                yield {"t": "error", "d": "The terminal has lost its connection to the DM."}
                return None
            kind = ev.get("type")
            if kind == "stream_event":
                se = ev["event"]
                if se["type"] == "content_block_start" and se["content_block"]["type"] == "tool_use":
                    if streamed:
                        streamed = ""
                        yield {"t": "retract"}
                    yield {"t": "busy"}
                elif se["type"] == "content_block_delta" and se["delta"].get("type") == "text_delta":
                    streamed += se["delta"]["text"]
                    yield {"t": "text", "d": se["delta"]["text"]}
            elif kind == "result":
                final = ev.get("result") or ""
                if ev.get("is_error"):
                    yield {"t": "error", "d": final or "The DM is unavailable."}
                    return None
                return final


class Handler(BaseHTTPRequestHandler):
    dm: Game  # HeadlessDM or RelayDM, set at startup

    def log_message(self, fmt: str, *args: Any) -> None:  # quiet
        pass

    def _json(self, obj: Any, code: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = (WEB / "static" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/state":
            self._json({**self.dm.status(), "history": self.dm.history()})
        elif self.path.startswith("/api/relay/next") and isinstance(self.dm, RelayDM):
            job = self.dm.next(timeout=25)
            self._json(job if job else {"id": None})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/api/relay/reply" and isinstance(self.dm, RelayDM):
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            ok = self.dm.reply(req.get("id", ""), req.get("text", ""))
            return self._json({"ok": ok}, 200 if ok else 404)
        if self.path != "/api/command":
            return self._json({"error": "not found"}, 404)
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        cmd = (req.get("cmd") or "").strip()
        opening = bool(req.get("opening"))
        if not cmd and not opening:
            return self._json({"error": "empty command"}, 400)
        if not self.dm.lock.acquire(blocking=False):
            return self._json({"error": "busy"}, 409)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            final = None
            for ev in self.dm.turn(OPENING_PROMPT if opening else cmd, opening):
                if ev["t"] == "done":
                    final = ev["d"]
                    ev["status"] = self.dm.status()
                self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                self.wfile.flush()
            if final is not None:
                self.dm.log(None if opening else cmd, final)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser went away; the turn still completed server-side
        finally:
            self.dm.lock.release()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", required=True, help="save name: saves/<game>.json")
    ap.add_argument("--world", help="world file to init from (required with --new or if no save exists)")
    ap.add_argument("--new", action="store_true", help="start a fresh game (overwrites the save)")
    ap.add_argument("--dm", choices=["headless", "relay"], default="headless",
                    help="headless: own claude -p process; relay: an interactive session DMs via web/relay.py")
    ap.add_argument("--model", default="opus", help="claude model alias for --dm headless (opus, sonnet, ...)")
    ap.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                    help="DM reasoning effort (default: the model's default); lower is faster")
    ap.add_argument("--port", type=int, default=8086)
    args = ap.parse_args()

    state = REPO / "saves" / f"{args.game}.json"
    if args.new or not state.exists():
        if not args.world:
            sys.exit(f"No save at {state}; pass --world worlds/<X>.json to start one.")
        res = engine("init", "--world", args.world, "--state", str(state), "--force")
        if not res.get("ok"):
            sys.exit(res.get("error"))

    if args.dm == "relay":
        Handler.dm = RelayDM(args.game, state, args.new)
        mode = "relay — DM with: .venv/bin/python web/relay.py wait"
    else:
        Handler.dm = HeadlessDM(args.game, state, args.model, args.new, effort=args.effort)
        mode = f"headless, model {args.model}" + (f", effort {args.effort}" if args.effort else "")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"{Handler.dm.title} — http://127.0.0.1:{args.port}  ({mode}; Ctrl-C to quit)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        proc = getattr(Handler.dm, "proc", None)
        if proc and proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    main()
