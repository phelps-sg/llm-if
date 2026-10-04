#!/usr/bin/env python3
"""Rebuild a playable world from the original ZIL source, reproducibly.

    .venv/bin/python scripts/build_world.py trinity            # -> worlds/trinity.json

Steps (all deterministic, no LLM):
  1. tools/zil_converter: ZIL source -> world JSON
  2. merge the curated, hand-written context from worlds/<game>_context.json
     (title, author, tone, DM notes...)
  3. scripts/zil_extras.py: constants, object names, clock/interrupts, boot queue,
     canonical intro, verb syntax, values, conditional exits, GENERIC tie-breakers,
     missing routines, flag repair

Source defaults to resources/zil/<game>/ (github.com/historicalsource/<game>,
kept out of git). Re-running gives the same file.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / ".venv/bin/python")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game")
    ap.add_argument("--src", type=Path, help="ZIL source dir (default resources/zil/<game>)")
    ap.add_argument("--out", type=Path, help="output (default worlds/<game>.json)")
    args = ap.parse_args()

    src = args.src or REPO / "resources" / "zil" / args.game
    out = args.out or REPO / "worlds" / f"{args.game}.json"
    ctx_file = REPO / "worlds" / f"{args.game}_context.json"
    if not src.is_dir():
        sys.exit(f"No ZIL source at {src}. Fetch github.com/historicalsource/{args.game} there.")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / f"{args.game}.json"
        subprocess.run([PY, "-m", "tools.zil_converter", str(src), "-o", str(raw),
                        "-n", str(REPO / "worlds" / f"{args.game}_NOTES.md")],
                       cwd=REPO, check=True, stdout=subprocess.DEVNULL)
        world = json.loads(raw.read_text())
        if ctx_file.exists():
            curated = {k: v for k, v in json.loads(ctx_file.read_text()).items() if not k.startswith("_")}
            world["world_context"] = curated
        raw.write_text(json.dumps(world, indent=2))
        subprocess.run([PY, str(REPO / "scripts" / "zil_extras.py"), str(raw), str(src)],
                       cwd=REPO, check=True, stdout=subprocess.DEVNULL)
        out.write_text(raw.read_text())
    world = json.loads(out.read_text())
    print(f"{out}: {len(world['locations'])} rooms, {len(world['items'])} items, "
          f"{len(world['npcs'])} npcs, {len(world.get('global_routines', {}))} routines")


if __name__ == "__main__":
    main()
