"""How many B1s does the one-bar arming deferral actually cost?

WHAT THE LEDGER SHOWED
---------------------
On the frozen slice every recorded B1 sits on a bar where the engine was already
`armed=True`. Bars where a break was True while `armed=False` produced nothing:

    2026-08-13 11:15 .. 12:15   armed=False   6 bars, all dropped
    2026-08-13 22:45            armed=False   dropped
    2026-08-14 04:15 .. 04:30   armed=False   dropped   <- the owner's 22:45 case
    2026-08-14 22:45            armed=False   dropped   <- the owner's case

The deferral is deliberate. firstswing.py:297-305 suppresses a break on the bar a
seal arrives, because a break of a pivot that was sealed on this very bar is
circular - the pivot was built from this bar, so breaking it here uses the bar to
prove itself. That reasoning is sound.

What is being measured here is the case the deferral does NOT intend to catch: a
break of a pivot that was sealed EARLIER, which merely happens to land on a bar
where a different seal is arriving. The engine cannot tell those two apart from the
flag alone - it drops on `_pending_arm` regardless of which pivot would be broken.

THE QUESTION
------------
How often does a genuine break coincide with a pending arm, and how many B1s does
that cost across the real chain? If it is rare, this is a documented edge. If it is
common, it is a structural hole in how direction gets established, because the FIRST
break after a seal is the one that would set the leg direction.

Everything is IST.
"""
import json
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from exp_signal_metrics import load_era            # noqa: E402

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
    b1_marks = {i for i, k in marks.items() if k == "B1"}

    def dt(i):
        return raw[i]["date"][:16] if 0 <= i < len(raw) else "-"

    # a dropped break: condition True, no mark landed
    dropped = [r for r in probe
               if (r["up_break"] or r["down_break"])
               and r["g_idx"] not in marks]
    pend = [r for r in dropped if r["pending_arm"]]
    not_armed = [r for r in dropped if not r["armed"]]

    # of the not-armed drops, how many break a pivot sealed on an EARLIER bar?
    # that is the case the deferral was never meant to catch
    genuine = []
    for r in not_armed:
        up = r["up_break"]
        pidx = r["e_hi_pivot_idx"] if up else r["e_lo_pivot_idx"]
        if pidx >= 0 and pidx < r["g_idx"]:
            genuine.append((r, pidx))
    # and how many break the pivot sealed on THIS bar - those are the phantoms the
    # deferral exists for, and dropping them is correct
    phantom = [r for r in not_armed if r not in [g[0] for g in genuine]]

    print()
    print("=" * 112)
    print("COST OF THE ONE-BAR ARMING DEFERRAL   (%d swings, %d break bars, IST)"
          % (len(swings), sum(1 for r in probe if r["up_break"] or r["down_break"])))
    print("=" * 112)
    print("  break True but no mark landed        : %d" % len(dropped))
    print("     of those, a seal was pending      : %d" % len(pend))
    print("     of those, engine was not armed    : %d" % len(not_armed))
    print()
    print("  Of the %d dropped while NOT ARMED, split by which pivot was broken:" % len(not_armed))
    print("     breaks a pivot sealed EARLIER bar : %-6d  <- genuine, deferral is collateral"
          % len(genuine))
    print("     breaks a pivot sealed THIS bar    : %-6d  <- phantom, deferral is correct"
          % len(phantom))
    print()
    print("  B1 marks actually recorded           : %d" % len(b1_marks))
    print()
    if genuine:
        pct = 100.0 * len(genuine) / (len(genuine) + len(phantom) or 1)
        print("  Of the drops the deferral caused, %.0f%% are genuine breaks of an older"
              % pct)
        print("  pivot - the collateral case, not the phantom the rule was written for.")
    print()
    print("  First 12 GENUINE drops (a real pivot break lost to the arming gap):")
    for r, pidx in genuine[:12]:
        side = "up  " if r["up_break"] else "down"
        print("     %s  %s  pivot sealed %s (%d bars earlier)"
              % (side, dt(r["g_idx"]), dt(pidx), r["g_idx"] - pidx))
    print()
    print("  First 6 PHANTOM drops (breaking the bar's own seal - correctly suppressed):")
    for r in phantom[:6]:
        side = "up  " if r["up_break"] else "down"
        print("     %s  %s  pending_leg=%s"
              % (side, dt(r["g_idx"]), r["pending_dir"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())