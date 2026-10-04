"""Deterministic regression tests for the Claude-as-DM engine CLI on Trinity.

No LLM involved: each test drives scripts/if_engine.py the way a DM would and
checks the engine hands over the right facts. Every test pins a bug found in
play-testing (see git history for the story).
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import if_engine  # noqa: E402
from tools.zil_converter.parser import strip_zil_comments  # noqa: E402

WORLD = REPO / "worlds" / "trinity.json"
pytestmark = pytest.mark.skipif(not WORLD.exists(), reason="worlds/trinity.json not built")


def run(*argv):
    args = if_engine.build_parser().parse_args([str(a) for a in argv])
    return args.func(args)


@pytest.fixture
def save(tmp_path):
    state = tmp_path / "t.json"
    res = run("init", "--world", WORLD, "--state", state, "--force")
    assert res["ok"]
    return state


def apply(state, updates, *flags):
    return run("apply", "--state", state, "--brief", *flags, "--updates", json.dumps(updates))


def go(state, room, *flags):
    return apply(state, [{"type": "move_player", "params": {"destination": room}}], *flags)


def context(state, cmd=""):
    return run("context", "--state", state, "--cmd", cmd)


# --- converter / world -----------------------------------------------------------

def test_zil_comment_strips_one_form_not_the_line():
    assert strip_zil_comments("(FLAGS LIGHTED ; SHADOWY)") == "(FLAGS LIGHTED )"
    assert strip_zil_comments("(GLOBAL A\n ; SBUBBLE CHILDREN)>") == "(GLOBAL A\n  CHILDREN)>"
    assert strip_zil_comments('; (ODOR 0) (X "a;b")') == ' (X "a;b")'


def test_rooms_and_items_once_dropped_by_the_parser_exist():
    world = json.loads(WORLD.read_text())
    for room in ("in_meadow", "at_terrace", "prom", "nbog", "on_beach", "on_bird"):
        assert room in world["locations"]
    assert "axe" in world["items"]


def test_late_era_flags_become_engine_attributes():
    world = json.loads(WORLD.read_text())
    assert world["items"]["ball"]["attributes"]["takeable"] is True
    assert world["items"]["pocket"]["attributes"]["container"] is True


# --- clock, timers, intro --------------------------------------------------------

def test_clock_starts_at_330_and_air_raid_is_due_at_35745(save):
    s = run("look", "--state", save, "--brief")["situation"]
    assert s["time"] == "3:30:00 pm"
    assert "3:57:45 pm (111 moves from now)" in s["timers"]["I-AIR-RAID"]


def test_ticks_and_multi_tick_wait(save):
    s = apply(save, [{"type": "no_change"}], "--advance-turn", "4")["situation"]
    assert s["time"] == "3:31:00 pm" and s["turn"] == 4


def test_canonical_intro_not_the_packaging_paraphrase(save):
    intro = json.loads(save.read_text())["world_context"]["intro"]
    assert "escaped to Hyde Park" in intro and "Tussaud" not in intro


def test_delayed_queue_fires_at_end_of_next_move(save):
    s = apply(save, [{"type": "no_change"}], "--advance-turn", "--queue", "I-BLOW:2")["situation"]
    assert s["timers"]["I-BLOW"] == "fires at the end of THIS move"
    s = apply(save, [{"type": "no_change"}], "--advance-turn")["situation"]
    assert "I-BLOW" not in s["timers"]


def test_frozen_clock_holds(save):
    s = apply(save, [{"type": "no_change"}], "--advance-turn", "3",
              "--set-clock", "15:59:45", "--freeze-clock")["situation"]
    assert s["time"] == "3:59:45 pm (frozen)"


# --- scope, refs, verbs, ambiguity -----------------------------------------------

def test_room_refs_resolve_constants(save):
    loc = context(save)["situation"]["loc"]
    assert loc["refs"][",TON"] == " to the north"


def test_ball_is_visible_in_the_beds_and_scores_once(save):
    s = go(save, "flower_walk")["situation"]
    assert {"name": "flower beds", "holds": ["soccer ball"]} in s["scenery"] + s["here"]
    r = apply(save, [{"type": "add_to_inventory", "params": {"item_id": "ball"}}])
    assert r["mechanics"]["score"] == {"gained": 1, "total": 1, "first_notification": True}
    apply(save, [{"type": "remove_from_inventory", "params": {"item_id": "ball"}}])
    r = apply(save, [{"type": "add_to_inventory", "params": {"item_id": "ball"}}])
    assert "score" not in r["mechanics"]


def test_take_brings_in_the_verb_routines(save):
    go(save, "flower_walk")
    verb = context(save, "take the ball")["verb"]
    assert "V-TAKE" in verb["routines"] and "ITAKE" in verb["routines"]


def test_global_objects_are_in_scope_and_ambiguity_carries_generic(save):
    go(save, "flower_walk")
    ctx = context(save, "follow path")
    assert {"path", "flwalk"} <= set(ctx["mentioned"])
    amb = ctx["ambiguous"][0]
    assert amb["word"] == "path" and "GENERIC-WALK-F" in amb["generic"]


def test_buying_crumbs_has_everything_evaluated(save):
    go(save, "broad_walk")
    ctx = context(save, "buy a bag of crumbs")
    assert "gbag" in ctx["mentioned"]           # held by the bird woman: in scope
    assert ctx["tests"]["GOT? COIN"] is True     # the coin in the pocket counts
    assert "bwoman" in ctx["performs"]           # TRY-BUY -> PERFORM GIVE ... BWOMAN


def test_arrival_at_lancaster_gate_delays_the_gust_and_wind_is_east(save):
    go(save, "lan_walk")
    ctx = context(save, "n")
    assert ctx["destination"]["id"] == "lan_gate"
    assert ctx["destination"]["arrival_queues"][0].startswith("I-BLOW:2")
    assert ctx["tests"]["IS? EWIND SEEN"] is True
    assert ctx["tests"]["IS? JWOMAN SEEN"] is False


def test_room_global_held_elsewhere_is_not_here(save):
    s = go(save, "broad_walk")["situation"]
    listed = json.dumps(s.get("here", []) + s.get("scenery", []))
    assert '"bag"' not in listed                  # GBAG is in the bird woman's hands
    assert any(isinstance(n, dict) and "bag" in n.get("holds", []) for n in s["npcs"])


# --- update validation -------------------------------------------------------------

def test_unknown_ids_are_errors_not_silent_noops(save):
    r = apply(save, [{"type": "move_player", "params": {"destination": "nowhere"}}])
    assert not r["ok"] and "unknown location" in r["errors"][0]
    r = apply(save, [{"type": "move_item", "params": {"item_id": "ball", "to_location": "bogus"}}])
    assert not r["ok"]


def test_items_can_go_into_containers_and_npcs(save):
    r = apply(save, [{"type": "move_item", "params": {"item_id": "parasol", "to_location": "tree"}},
                     {"type": "move_npc", "params": {"npc_id": "meep", "to_location": "ts6"}}])
    assert r["ok"], r["errors"]
    data = json.loads(save.read_text())
    assert data["item_locations"]["parasol"] == "tree"


def test_objects_that_dont_exist_yet_cant_be_taken(save):
    go(save, "broad_walk")
    r = apply(save, [{"type": "add_to_inventory", "params": {"item_id": "bag"}}])
    assert not r["ok"] and "isn't anywhere in the world yet" in r["error"]
    r = apply(save, [{"type": "move_item", "params": {"item_id": "bag", "to_location": "bwoman"}},
                     {"type": "add_to_inventory", "params": {"item_id": "bag"}}])
    assert r["ok"]
