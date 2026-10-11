"""Find concrete ARM1 cases on fsent_champ_long where the guard is a no-op.

We instrument the patched engine to log every bar where:
  - defer_same_bar_arm is on
  - _pending_arm is True (a seal arrived this bar)
  - a same-direction break fires (up_break with pending_leg_dir=up, or down_break with pending_leg_dir=down)

For each such bar we record:
  - g_idx and timestamp
  - e_hi_pivot.idx / e_lo_pivot.idx (the sealed pivot — the correct discriminator)
  - e_hi_prev.idx / e_lo_prev.idx (the running extreme — what the patch tests)
  - whether e_hi_pivot.idx == g_idx (phantom: pivot sealed on THIS bar)
  - whether e_hi_pivot.idx < g_idx (genuine: pivot sealed on an EARLIER bar)

The patch's condition is `e_hi_prev.idx < g_idx` which is ALWAYS true.
The correct condition is `e_hi_pivot.idx < g_idx`.

We want to find bars where these disagree — i.e., where the patch arms but shouldn't.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from exp_signal_metrics import load_era  # noqa: E402

OLD = "        if self.armed:\n            self._step(down_break, up_break)\n"
NEW = (
    "        _g = getattr(self, '_probe', None)\n"
    "        if _g is not None:\n"
    "            _g.append({'g_idx': g_idx, 'armed': self.armed,\n"
    "                       'state': self.state, 'dir': self.dir,\n"
    "                       'up_break': bool(up_break),\n"
    "                       'down_break': bool(down_break),\n"
    "                       'pending_arm': self._pending_arm,\n"
    "                       'pending_dir': self._pending_leg_dir,\n"
    "                       'e_hi_pivot_idx': (self.e_hi_pivot.idx if self.e_hi_pivot else -1),\n"
    "                       'e_lo_pivot_idx': (self.e_lo_pivot.idx if self.e_lo_pivot else -1),\n"
    "                       'e_hi_prev_idx': self.e_hi_prev.idx,\n"
    "                       'e_lo_prev_idx': self.e_lo_prev.idx,\n"
    "                       'bars_seen': self.bars_seen})\n"
    + OLD
)


def patch():
    p = ROOT / "backend" / "src" / "firstswing.py"
    src = p.read_text(encoding="utf-8")
    assert src.count(OLD) == 1
    name = "src.firstswing"
    mod = types.ModuleType(name)
    mod.__file__ = str(p)
    mod.__package__ = "src"
    mod.__dict__["__name__"] = name
    sys.modules[name] = mod
    exec(compile(src.replace(OLD, NEW), str(p), "exec"), mod.__dict__)
    sys.modules.pop("src.btc.btc_swing", None)
    sys.modules[name] = mod
    return mod


def main():
    patch()
    from src.btc.btc_swing import compute_btc_swings
    from src.walker import FlowCandle
    import src.firstswing as fs_mod

    d = load_era("is")
    raw = d["c15"]
    probe = []
    real_process = fs_mod.SwingEngine.process_bar

    def wrapper(self, c, g_idx):
        self._probe = probe
        return real_process(self, c, g_idx)
    fs_mod.SwingEngine.process_bar = wrapper

    candles = [FlowCandle(x["date"], x["open"], x["high"], x["low"], x["close"])
               for x in raw]
    cap = max(1, len(candles) // 2)
    swings = compute_btc_swings(candles, opts={"minBars": 50}, max_swings=cap)
    marks = {b["idx"]: b.get("kind") for s in swings for b in s.get("breaks", [])
             if b.get("idx") is not None}

    def dt(i):
        return raw[i]["date"][:16] if 0 <= i < len(raw) else "-"

    # Find bars where the guard is the DECIDING factor:
    #   - pending_arm=True (a seal arrived this bar)
    #   - armed=False (engine was NOT already armed — otherwise break fires normally)
    #   - state=="watch" (guard only runs in watch state)
    #   - same-direction break
    guard_fires = []
    for r in probe:
        if not r["pending_arm"]:
            continue
        if r["armed"]:
            continue
        if r["state"] != "watch":
            continue
        pd = r["pending_dir"]
        if pd == "up" and r["up_break"]:
            guard_fires.append(r)
        elif pd == "down" and r["down_break"]:
            guard_fires.append(r)

    print()
    print("=" * 100)
    print("ARM1 CHART CASES — fsent_champ_long, IS era, min_bars=50")
    print("=" * 100)
    print("  Total bars probed: %d" % len(probe))
    print("  Bars where guard fires (pending_arm + same-dir break): %d" % len(guard_fires))
    print()

    # Split by phantom vs genuine
    phantom = []
    genuine = []
    for r in guard_fires:
        if r["pending_dir"] == "up":
            pidx = r["e_hi_pivot_idx"]
        else:
            pidx = r["e_lo_pivot_idx"]
        if pidx == r["g_idx"]:
            phantom.append(r)
        elif pidx < r["g_idx"]:
            genuine.append(r)
        else:
            print("  WARNING: pivot idx > g_idx (shouldn't happen): g=%d pidx=%d"
                  % (r["g_idx"], pidx))

    print("  PHANTOM (pivot sealed on THIS bar — patch should NOT arm): %d" % len(phantom))
    print("  GENUINE (pivot sealed on EARLIER bar — patch SHOULD arm): %d" % len(genuine))
    print()

    # Show the phantom cases — these are the ones the buggy guard wrongly arms
    print("  PHANTOM CASES (patch arms these because e_hi_prev.idx < g_idx is always true):")
    print("  %-22s %-8s %-12s %-12s %-10s" % ("time", "dir", "pivot_idx", "g_idx", "bars_apart"))
    for r in phantom[:20]:
        if r["pending_dir"] == "up":
            pidx = r["e_hi_pivot_idx"]
        else:
            pidx = r["e_lo_pivot_idx"]
        print("  %-22s %-8s %-12d %-12d %-10d"
              % (dt(r["g_idx"]), r["pending_dir"], pidx, r["g_idx"], r["g_idx"] - pidx))
    if len(phantom) > 20:
        print("  ... and %d more" % (len(phantom) - 20))
    print()

    # Show genuine cases for contrast
    print("  GENUINE CASES (patch correctly arms these):")
    print("  %-22s %-8s %-12s %-12s %-10s" % ("time", "dir", "pivot_idx", "g_idx", "bars_apart"))
    for r in genuine[:10]:
        if r["pending_dir"] == "up":
            pidx = r["e_hi_pivot_idx"]
        else:
            pidx = r["e_lo_pivot_idx"]
        print("  %-22s %-8s %-12d %-12d %-10d"
              % (dt(r["g_idx"]), r["pending_dir"], pidx, r["g_idx"], r["g_idx"] - pidx))
    if len(genuine) > 10:
        print("  ... and %d more" % (len(genuine) - 10))
    print()

    # Now show the key disagreement: bars where patch arms but shouldn't
    print("  DISAGREEMENT SUMMARY:")
    print("    Patch condition (e_hi_prev.idx < g_idx): always true → arms ALL %d cases"
          % len(guard_fires))
    print("    Correct condition (e_hi_pivot.idx < g_idx): arms %d, suppresses %d"
          % (len(genuine), len(phantom)))
    print("    → Patch wrongly arms %d phantom cases" % len(phantom))
    print()

    # Show a few phantom cases with full detail for the owner to check on chart
    print("  DETAILED PHANTOM CASES (for owner chart check):")
    for r in phantom[:5]:
        g = r["g_idx"]
        print("    Bar %s (idx %d):" % (dt(g), g))
        print("      pending_leg_dir: %s" % r["pending_dir"])
        print("      up_break=%s down_break=%s" % (r["up_break"], r["down_break"]))
        if r["pending_dir"] == "up":
            print("      e_hi_pivot.idx=%d (sealed on this bar → phantom)" % r["e_hi_pivot_idx"])
            print("      e_hi_prev.idx=%d (running extreme — always < g_idx)" % r["e_hi_prev_idx"])
        else:
            print("      e_lo_pivot.idx=%d (sealed on this bar → phantom)" % r["e_lo_pivot_idx"])
            print("      e_lo_prev.idx=%d (running extreme — always < g_idx)" % r["e_lo_prev_idx"])
        print("      bars_seen=%d" % r["bars_seen"])
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
