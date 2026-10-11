"""False-B1 detector: every B1 must break ONE OF TWO LEVELS. The owner's rule, exactly.

THE RULE
--------
"If we are looking at the candle from where the calculation of a swing starts ...
For a green candle, low of it would be an extreme. For a red candle, high of it would
be the extreme. So this is candle colour based, and any pivot after it on the opposite
direction would be considered as ... those are the two points we are looking for.
Anyone breaking either is considered as B1. That's it."

So a leg has exactly TWO live levels:

  1. the SEED candle's extreme - its LOW when green, its HIGH when red
  2. the FIRST pivot on the opposite side - the first L seal for a green seed, the
     first H seal for a red seed

and a B1 is the first candle to break either. Nothing else in the leg is a
breakable level. He checked two candles of my "risk" list on 2026-01 and both
exposed the distinction:

  2023-01-16 09:00  CORRECT - the 08:00 red seed's high 21375.5 or the 08:30 low
                    21060.0 was broken, and 09:00 took the 08:30 low. My "risk"
                    framing called this a case where the bar broke a random pivot;
                    he read it back as the 08:30 extreme, which is what it is.

  2023-01-13 10:45  WRONG  - seed 06:45 is red so the levels are its high 18795.0
                    and the 07:00 low 18730.0. The mark is stamped at 18824.5, which
                    is a later random pivot and neither of the two. "I don't see it
                    breaking at any stuff." Correct.

WHAT THE ENGINE ACTUALLY DOES
-----------------------------
B1 fires on `up_break = c.high > e_hi_prev.px` - a NEW SESSION EXTREME. On a young
leg that happens to be the seed's extreme, which is why the common case was already
right. Later in the leg e_hi_prev has walked on to whatever pivot came last, so the
engine keeps marking B1 at levels the rule does not recognise. That is the class of
defect this file counts.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_false_b1.py [limit] [show]
"""
from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_false_b1.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"
TOL = 1


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    t0 = time.time()

    p1 = ROOT / "backend" / "src" / "firstswing.py"
    p2 = ROOT / "backend" / "src" / "btc" / "btc_swing.py"
    src = p1.read_text(encoding="utf-8")

    seal_anchor = "            if not p.sealed:\n                continue\n"
    assert src.count(seal_anchor) == 1
    src = src.replace(seal_anchor, seal_anchor +
                      "            _FB = getattr(self, '_fb', None)\n"
                      "            if _FB is not None:\n"
                      "                _FB.setdefault('seals', {}).setdefault(g_idx, []).append(\n"
                      "                    (p.kind, p.px, p.idx))\n", 1)
    mark_anchor = "        if self.armed:\n            self._step(down_break, up_break)\n"
    assert src.count(mark_anchor) == 1
    src = src.replace(mark_anchor,
                      "        _FM = getattr(self, '_fb', None)\n"
                      "        if _FM is not None and self.break_marks:\n"
                      "            _FM.setdefault('marks', []).extend(\n"
                      "                (k.kind, k.dir, k.px, k.idx) for k in self.break_marks)\n"
                      "            self.break_marks = []\n" + mark_anchor, 1)

    nm = "src.firstswing_fb"
    m = types.ModuleType(nm)
    m.__file__ = str(p1)
    m.__package__ = "src"
    m.__dict__["__name__"] = nm
    sys.modules[nm] = m
    exec(compile(src, str(p1), "exec"), m.__dict__)
    sw = p2.read_text(encoding="utf-8").replace(
        "from src.firstswing import", "from src.firstswing_fb import")
    nm2 = "src.btc.btc_swing_fb"
    sm = types.ModuleType(nm2)
    sm.__file__ = str(p2)
    sm.__package__ = "src.btc"
    sm.__dict__["__name__"] = nm2
    sys.modules[nm2] = sm
    exec(compile(sw, str(p2), "exec"), sm.__dict__)

    legs = []
    cur = {}
    real_init = sm.SwingEngine.__init__

    def init(self, *a, **kw):
        real_init(self, *a, **kw)
        cur = {}
        cur["_fb"] = self._fb = cur
        cur["seed"] = None
        legs.append(cur)
    sm.SwingEngine.__init__ = init

    from src.btc.btc_routes import _load_window
    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    real_step = sm.SwingEngine.process_bar

    def step(self, c, g_idx):
        if self._fb.get("seed") is None:
            self._fb["seed"] = g_idx
            self._fb["seed_c"] = (c.date, c.open, c.high, c.low, c.close)
        return real_step(self, c, g_idx)
    sm.SwingEngine.process_bar = step

    sm.compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                          max_swings=len(flow) // 2)

    bad, ok, nopiv = [], 0, 0
    for L in legs:
        sc = L.get("seed_c")
        if not sc:
            continue
        si = L["seed"]
        _d, o, h, l, cl = sc
        green = cl >= o
        extreme = l if green else h
        ext_dir = "down" if green else "up"
        piv_dir = "H" if green else "L"

        seals = L.get("seals", {})
        pivot = None
        for g in sorted(seals):
            for k, px, pidx in seals[g]:
                # pidx >= si, NOT > si. The seed candle's OWN extreme becomes a real
                # pivot as soon as the walker confirms it, and that pivot is one of
                # the two levels. On 2023-01-14 the leg seeds on the red 06:15
                # (H 21215.5, L 20809.5); at 06:45 the walker seals L 20809.5 whose
                # extreme candle IS the seed. That is the level 06:45 breaks, giving
                # the B1 the owner confirmed. Excluding pidx == si threw that level
                # away and the detector then flagged the confirmed B1 as false.
                if k == piv_dir and pidx >= si and (pivot is None or g < pivot[0]):
                    pivot = (g, k, px)
                    break
            if pivot:
                break

        for kind, dirn, px, idx in L.get("marks", []):
            if kind != "B1":
                continue
            hit_ext = (candles[idx]["low"] < extreme) if green \
                else (candles[idx]["high"] > extreme)
            hit_piv = False
            if pivot:
                _, k, ppx = pivot
                hit_piv = (candles[idx]["high"] > ppx) if k == "H" \
                    else (candles[idx]["low"] < ppx)
            if hit_ext or hit_piv:
                ok += 1
            else:
                bad.append({
                    "seed": candles[si]["date"][:16], "green": green,
                    "extreme": extreme, "extreme_dir": ext_dir,
                    "pivot": (candles[pivot[0]]["date"][:16], pivot[1], pivot[2])
                             if pivot else None,
                    "mark_time": candles[idx]["date"][:16], "mark_px": px,
                    "mark_dir": dirn,
                    "bar_hi": candles[idx]["high"], "bar_lo": candles[idx]["low"],
                })
        if not pivot:
            nopiv += 1

    tot = ok + len(bad)

    # VALIDATION FIRST. Every candle the owner has personally ruled on must come out
    # clean. A detector that flags a confirmed mark is worse than no detector, and
    # five earlier attempts at this exact tool were wrong in ways only the owner
    # caught on a chart - so the run reports its verdict on the owner's candles
    # BEFORE its verdict on the chain.
    OWNER_OK = ["2023-01-03 12:45", "2023-01-14 06:45", "2023-02-04 15:45",
                "2023-02-13 04:30", "2023-02-13 16:45", "2023-02-05 07:30",
                "2023-03-11 08:30", "2026-08-14 22:45"]
    OWNER_NONE = ["2023-02-05 07:00", "2023-03-11 08:00"]
    flagged = {b["mark_time"]: b for b in bad}
    hit = [t for t in OWNER_OK if t in flagged]
    print("\n" + "=" * 78)
    print("VALIDATION AGAINST THE OWNER'S CONFIRMED CANDLES")
    print("=" * 78)
    print("  confirmed-B1 candles the detector calls false : %d  %s"
          % (len(hit), hit if hit else ""))
    n_ok = sum(1 for b in bad if b["mark_time"] in OWNER_OK)
    print("  -> the detector is USABLE on this rule" if not hit else
          "  -> the detector is STILL WRONG. Its own numbers below mean nothing.")

    print("\n" + "=" * 78)
    print("FALSE B1s  -  every B1 must break the seed extreme or the first pivot")
    print("%s  min_bars=%d  limit=%d" % (TF, MIN_BARS, limit))
    print("=" * 78)
    print("\n  legs %d   (legs with no opposite-side pivot at all: %d)"
          % (len(legs), nopiv))
    print("    B1 breaks one of the two levels  : %4d   correct" % ok)
    print("    B1 breaks NEITHER               : %4d   FALSE" % len(bad))
    if bad:
        print("\n--- FIRST %d FALSE B1s ---" % min(show, len(bad)))
        print("  %-17s %-6s %-11s %-22s %-11s %s"
              % ("seed", "green", "extreme", "first pivot", "B1 stamped", "dir"))
        for b in bad[:show]:
            pv = b["pivot"]
            pvs = ("%s %s %.1f" % (pv[0][11:16], pv[1], pv[2])) if pv else "none"
            print("  %-17s %-6s %-11.1f %-22s %-11.1f %s"
                  % (b["seed"], b["green"], b["extreme"], pvs,
                     b["mark_px"], b["mark_dir"]))
        if len(bad) > show:
            print("  ... and %d more in the JSON" % (len(bad) - show))
    OUT.write_text(json.dumps({"legs": len(legs), "ok": ok, "false": len(bad),
                               "false_marks": bad}, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
