"""Every B1 that SHOULD be marked but is not: suppressed breaks that really did cross
a pivot standing before the bar.

THE OWNER FOUND THESE BY HAND. Three of them, and the third one is the tell:

  2023-02-05 07:00   no B1      correct - nothing was broken
  2023-02-13 04:30   no B1      WRONG   - it broke the 04:00 pivot
  2023-02-13 16:45   B1 marked  correct - same shape, one candle after the pivot

Two identical situations one candle apart, one marked and one not. That is not a
chart-reading difference, that is a defect, and it is the same mistake twice: the
arming guard asks whether the CURRENT pivot (e_hi_pivot, which this bar's own seal has
already overwritten by the time the guard runs) is old, when the question is whether
the bar CROSSED something that was standing before it.

So this file is the pipeline the owner asked for. It does not look at the chart. For
every bar in the window it records what the engine knew at that bar and re-derives,
independently, whether a B1 belonged there. What it prints is the missing list, in
chronological order, with enough context to check any single one against the chart.

WHAT COUNTS AS MISSING
----------------------
A bar where all of these hold:

  1. the engine was NOT armed, so no B1 was recorded
  2. a same-direction break fired (it cleared the running extreme)
  3. that bar also cleared the STANDING PIVOT - e_hi_pivot_prev for an up break,
     e_lo_pivot_prev for a down break. _prev is the pivot as it stood at the end of
     the previous bar, i.e. before this bar's own seal had a chance to overwrite it.

Condition 3 is the one the engine's guard gets wrong. It reads e_hi_pivot, which
process_bar has already refreshed from this bar's seal, so it sees the pivot this bar
just made and concludes nothing older was broken.

e_hi_pivot_prev is used here deliberately and it is NOT the tautology it looks like:
the test is not `prev.idx < g_idx` (always true) but whether this bar's high actually
CROSSED prev.px. That is a real crossing question and it can be answered no.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_missing_b1.py [limit] [show]
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_missing_b1.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"

# Inserted immediately before the step call - after the arming guard, after the
# walker, so everything here is what the engine actually knew at this bar.
OLD = "        if self.armed:\n            self._step(down_break, up_break)\n"
NEW = (
    "        _g = getattr(self, '_probe', None)\n"
    "        if _g is not None:\n"
    "            _g.append({\n"
    "                'g_idx': g_idx, 't': self.t, 'armed': self.armed,\n"
    "                'state': self.state, 'dir': self.dir,\n"
    "                'up_break': bool(up_break), 'down_break': bool(down_break),\n"
    "                'pending_arm': self._pending_arm,\n"
    "                'pending_dir': self._pending_leg_dir,\n"
    "                'hi': self.hi, 'lo': self.lo,\n"
    "                'e_hi_prev_px': self.e_hi_prev.px,\n"
    "                'e_lo_prev_px': self.e_lo_prev.px,\n"
    "                'e_hi_piv_px': (self.e_hi_pivot.px if self.e_hi_pivot else None),\n"
    "                'e_lo_piv_px': (self.e_lo_pivot.px if self.e_lo_pivot else None),\n"
    "                'e_hi_pivprev_px': (self.e_hi_pivot_prev.px if self.e_hi_pivot_prev else None),\n"
    "                'e_lo_pivprev_px': (self.e_lo_pivot_prev.px if self.e_lo_pivot_prev else None),\n"
    "                'e_hi_pivprev_idx': (self.e_hi_pivot_prev.idx if self.e_hi_pivot_prev else -1),\n"
    "                'e_lo_pivprev_idx': (self.e_lo_pivot_prev.idx if self.e_lo_pivot_prev else -1),\n"
    "                'seed_idx': self.seed_idx,\n"
    "                'bars_seen': self.bars_seen,\n"
    "                'e_hi_piv_idx': (self.e_hi_pivot.idx if self.e_hi_pivot else -1),\n"
    "                'e_lo_piv_idx': (self.e_lo_pivot.idx if self.e_lo_pivot else -1),\n"
    "            })\n"
    + OLD
)


def build_engine():
    p = ROOT / "backend" / "src" / "firstswing.py"
    src = p.read_text(encoding="utf-8")
    if src.count(OLD) != 1:
        raise RuntimeError("probe anchor matched %d times" % src.count(OLD))
    name = "src.firstswing_probe_missing"
    m = types.ModuleType(name)
    m.__file__ = str(p)
    m.__package__ = "src"
    m.__dict__["__name__"] = name
    sys.modules[name] = m
    exec(compile(src.replace(OLD, NEW), str(p), "exec"), m.__dict__)
    return m


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    build_engine()
    from src.btc.btc_routes import _load_window
    sw_path = ROOT / "backend" / "src" / "btc" / "btc_swing.py"
    sw_src = sw_path.read_text(encoding="utf-8").replace(
        "from src.firstswing import", "from src.firstswing_probe_missing import")
    nm = "src.btc.btc_swing_probe_missing"
    sm = types.ModuleType(nm)
    sm.__file__ = str(sw_path)
    sm.__package__ = "src.btc"
    sm.__dict__["__name__"] = nm
    sys.modules[nm] = sm
    exec(compile(sw_src, str(sw_path), "exec"), sm.__dict__)

    eng_cls = sm.SwingEngine
    probe: list = []
    orig_lock = eng_cls._lock

    def lock(self, d):
        if probe:
            r = probe[-1]
            r["marked"] = True
            r["mark_dir"] = d
        return orig_lock(self, d)
    eng_cls._lock = lock

    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    print("walking %d bars ..." % len(flow), flush=True)
    from src.walker import FlowCandle
    import json as _json
    holder = {"probe": probe}
    # btc_swing builds engines internally; attach the probe list via the class
    real_init = eng_cls.__init__

    def init(self, *a, **kw):
        real_init(self, *a, **kw)
        self._probe = holder["probe"]
    eng_cls.__init__ = init

    chain = sm.compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                  max_swings=len(flow) // 2)
    marks = {(x["time"], x["kind"]) for s in chain for x in s["breaks"]}

    missing = []
    for r in probe:
        if r.get("marked"):
            continue
        if r["armed"]:
            continue
        up, dn = r["up_break"], r["down_break"]
        if not (up or dn):
            continue
        # same-direction-only: a V reversal is handled by the shipped branch
        if (r["pending_dir"] == "up" and not up) or (r["pending_dir"] == "down" and not dn):
            continue
        lvl = r["e_hi_pivprev_px"] if up else r["e_lo_pivprev_px"]
        pidx = r["e_hi_pivprev_idx"] if up else r["e_lo_pivprev_idx"]
        if lvl is None:
            continue
        # THE LEG-MEMBERSHIP TEST. e_hi_pivot_prev can be a pivot that this leg has
        # already killed - "any new H kills old H" - and a dead pivot from before the
        # leg started is not a level anyone was waiting on. The owner gave the two
        # cases that pin this down:
        #
        #   2023-02-05 07:00   swing starts 06:30. Standing pivot 23314.5 belongs to
        #                     an EARLIER leg. The levels actually under the 06:30 leg
        #                     are the 07:00 pivot's high and the 06:30 candle's low.
        #                     Breaking a dead pivot is not a B1, and none is marked.
        #                     "So what is wrong here? I cannot see the issue."
        #
        #   2023-02-13 04:30   swing starts 03:45. Standing pivot 21793.0 was sealed
        #                     AT 04:00, inside this leg, and 04:30 crossed it. That is
        #                     the same shape as 16:45 the owner marked correctly.
        #
        # So a standing pivot only counts if it belongs to the current leg.
        if pidx < r["seed_idx"]:
            continue
        crossed = r["hi"] > lvl if up else r["lo"] < lvl
        if not crossed:
            continue
        r["broken_level"] = lvl
        r["standing_pivot"] = lvl
        r["standing_pivot_idx"] = pidx
        r["seed_idx"] = r["seed_idx"]
        r["current_pivot"] = r["e_hi_piv_px"] if up else r["e_lo_piv_px"]
        r["current_pivot_idx"] = r["e_hi_piv_idx"] if up else r["e_lo_piv_idx"]
        missing.append(r)

    print("\n" + "=" * 78)
    print("MISSING B1s  -  engine not armed, but the bar DID cross a standing pivot")
    print("=" * 78)
    print("  total: %d" % len(missing))
    by_dir = {}
    for r in missing:
        d = "up" if r["up_break"] else "down"
        by_dir[d] = by_dir.get(d, 0) + 1
    print("  direction: %s" % by_dir)
    print()
    print("  %-6s %-20s %-10s %-12s %s" % ("dir", "timestamp", "broke", "standing", "note"))
    for r in missing[:show]:
        d = "up" if r["up_break"] else "down"
        note = ""
        if r["current_pivot_idx"] == r["g_idx"]:
            note = "engine saw a pivot sealed on THIS bar and gave up"
        print("  %-6s %-20s %-10.1f %-12.1f %s"
              % (d, r["t"][:16], r["hi"] if up else r["lo"], r["standing_pivot"], note))

    OUT.write_text(json.dumps(missing, indent=1, default=str) + "\n", encoding="utf-8")
    print("\n  wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
