#!/usr/bin/env python3
"""Relay client: lets an interactive Claude Code session be the DM behind the web UI.

Start the server with `--dm relay`, then in the session loop:

    .venv/bin/python web/relay.py wait            # blocks until the player types
    ... run the turn with scripts/if_engine.py ...
    .venv/bin/python web/relay.py say <id> <<'EOF'
    <narration, plain text>
    EOF

`wait` prints the turn id, the player's command and the fresh brief situation
(including the room's ZIL as loc.zil), so the turn needs no initial `look`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _url(port: int, path: str) -> str:
    return f"http://127.0.0.1:{port}{path}"


def wait(port: int, timeout: float) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(_url(port, "/api/relay/next"), timeout=40) as r:
                job = json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"relay: server not reachable on port {port} ({e})", file=sys.stderr)
            time.sleep(2)
            continue
        if job.get("id"):
            print(f"TURN {job['id']}  state={job['state']}")
            if job.get("opening"):
                print(f"OPENING: {job['cmd']}")
                if job.get("intro"):
                    print(f"INTRO (print verbatim first): {json.dumps(job['intro'])}")
                if job.get("brief"):
                    print(f"DM BRIEF: read {job['brief']} before narrating (once per session)")
            else:
                print(f"PLAYER: {job['cmd']}")
            print(f"SITUATION: {json.dumps(job['situation'])}")
            for k in ("out_of_character", "feelie", "interrupts", "mentioned", "ambiguous",
                      "performs", "verb", "destination", "tests"):
                if job.get(k):
                    print(f"{k.upper()}: {json.dumps(job[k])}")
            return 0
    print("relay: no command yet (timed out) — run wait again")
    return 2


def say(port: int, tid: str) -> int:
    text = sys.stdin.read().strip()
    req = urllib.request.Request(
        _url(port, "/api/relay/reply"),
        data=json.dumps({"id": tid, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = json.load(r).get("ok")
    except urllib.error.HTTPError:
        ok = False
    print("sent" if ok else f"relay: no pending turn {tid}")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8086)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wait", help="block until the player enters a command")
    w.add_argument("--timeout", type=float, default=540)
    s = sub.add_parser("say", help="send narration (stdin) for a turn")
    s.add_argument("id")
    args = ap.parse_args()
    sys.exit(wait(args.port, args.timeout) if args.cmd == "wait" else say(args.port, args.id))


if __name__ == "__main__":
    main()
