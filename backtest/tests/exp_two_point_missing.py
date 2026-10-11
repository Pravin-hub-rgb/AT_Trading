"""The fourth direction: the two-point rule, tested for MISSING marks.

THE GAP THIS FILLS
------------------
Three tests already cover the rule from three sides and this was the fourth:

  exp_b1_pipeline     a mark that EXISTS is in the right place            0 failures
  exp_false_b1        every B1 breaks the seed extreme or the first pivot 0 failures
  exp_missing_leg_seed the SEED EXTREME was broken and a B1 is there      0 missing

None of them asked the other half of the second question. If the first PIVOT is
broken and no B1 is marked, nothing catches it. The owner asked for exactly this:
"is there no test which is saying that this candle breaks it, but still B1 is not
marked there." There was not.

THE RULE, AS HE STATED IT
-------------------------
"The leg starts [at the previous swing's end]. As this is a green candle, the low of
it would be considered as an extreme low. And the first pivot we see is at 4:00. So
this would be considered as extreme high. So we have two points which are locked,
and whichever breaks, we consider that as B1."

  level 1   the seed candle's extreme - LOW if the seed is green, HIGH if red
  level 2   the first pivot on the opposite side

Whichever of the two is broken first is the B1. A leg has exactly one B1, at the
first crossing of either level, and it must be the first - a later crossing of the
other level is B2's business or a FLIP's, not a new B1.

pidx >= si matters here too: the seed candle's own extreme becomes a real pivot as
soon as the walker confirms it. On 2023-01-14 the leg seeds on the red 06:15 and at
06:45 the walker seals L 20809.5 whose extreme candle IS the seed. That is level 2,
and 06:45 breaking it is the confirmed B1.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_two_point_missing.py [limit] [show]
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

OUT = ROOT / "backtest/tests/_two_point_missing.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"
TOL = 1


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    t0 = time.time()

    p1 = ROOT / "backend" / "src" / "firstswing.py"
    p2 = ROOT / "backend" / "src" / "btc" / "btc_swing.py"
    src = p1.read_text(encoding="utf-8")
    sa = "            if not p.sealed:\n                continue\n"
    assert src.count(sa) == 1
    src = src.replace(sa, sa +
                      "            _T = getattr(self, '_t', None)\n"
                      "            if _T is not None:\n"
                      "                _T.setdefault('seals', {}).setdefault(g_idx, []).append(\n"
                      "                    (p.kind, p.px, p.idx))\n", 1)
    ma = "        if self.armed:\n            self._step(down_break, up_break)\n"
    assert src.count(ma) == 1
    src = src.replace(ma,
                      "        _U = getattr(self, '_t', None)\n"
                      "        if _U is not None and self.break_marks:\n"
                      "            _U.setdefault('marks', []).extend(\n"
                      "                (k.kind, k.dir, k.px, k.idx) for k in self.break_marks)\n"
                      "            self.break_marks = []\n" + ma, 1)

    nm = "src.firstswing_tp"
    m = types.ModuleType(nm)
    m.__file__ = str(p1)
    m.__package__ = "src"
    m.__dict__["__name__"] = nm
    sys.modules[nm] = m
    exec(compile(src, str(p1), "exec"), m.__dict__)
    sw = p2.read_text(encoding="utf-8").replace(
        "from src.firstswing import", "from src.firstswing_tp import")
    nm2 = "src.btc.btc_swing_tp"
    sm = types.ModuleType(nm2)
    sm.__file__ = str(p2)
    sm.__package__ = "src.btc"
    sm.__dict__["__name__"] = nm2
    sys.modules[nm2] = sm
    exec(compile(sw, str(p2), "exec"), sm.__dict__)

    legs = []
    ri = sm.SwingEngine.__init__

    def init(self, *a, **k):
        ri(self, *a, **k)
        c = {}
        c["_t"] = self._t = c
        c["seed"] = None
        legs.append(c)
    sm.SwingEngine.__init__ = init
    rs = sm.SwingEngine.process_bar

    def step(self, c_, g):
        if self._t.get("seed") is None:
            self._t["seed"] = g
            self._t["sc"] = (c_.open, c_.high, c_.low, c_.close)
        return rs(self, c_, g)
    sm.SwingEngine.process_bar = step

    from src.btc.btc_routes import _load_window
    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    sm.compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                          max_swings=len(flow) // 2)

    missing, late, ok, nobody = [], [], 0, 0
    for L in legs:
        sc = L.get("sc")
        if not sc:
            continue
        si = L["seed"]
        o, h, l, cl = sc
        green = cl >= o
        extreme = l if green else h
        piv_dir = "H" if green else "L"
        seals = L.get("seals", {})

        pivot = None
        for g in sorted(seals):
            for k, px, pidx in seals[g]:
                if k == piv_dir and pidx >= si and (pivot is None or g < pivot[0]):
                    pivot = (g, k, px)
                    break
            if pivot:
                break

        b1 = [x for x in L.get("marks", []) if x[0] == "B1"]
        marks = L.get("marks", [])
        last = max([x[3] for x in marks] + [si])

        # first bar crossing EITHER locked level
        hit = None
        for i in range(si + 1, min(last + 1, len(candles))):
            c = candles[i]
            if green and c["low"] < extreme:
                hit = (i, "seed-extreme", extreme)
                break
            if not green and c["high"] > extreme:
                hit = (i, "seed-extreme", extreme)
                break
            if pivot:
                _, pk, ppx = pivot
                if pk == "H" and c["high"] > ppx:
                    hit = (i, "first-pivot", ppx)
                    break
                if pk == "L" and c["low"] < ppx:
                    hit = (i, "first-pivot", ppx)
                    break

        if hit is None:
            if b1:
                ok += 1
            else:
                nobody += 1
            continue

        idx, which, lvl = hit
        near = [x for x in b1 if abs(x[3] - idx) <= TOL]
        rec = {"seed": candles[si]["date"][:16], "green": green,
               "extreme": extreme,
               "pivot": (candles[pivot[0]]["date"][:16], pivot[1], pivot[2])
                        if pivot else None,
               "first_cross": candles[idx]["date"][:16], "which": which,
               "level": lvl,
               "b1": ", ".join("%s@%d" % (x[1], x[3]) for x in b1) or "none"}
        if not b1:
            missing.append(rec)
        elif not near:
            late.append(rec)
        else:
            ok += 1

    OWNER = ["2023-01-03 12:45", "2023-01-14 06:45", "2023-02-04 15:45",
             "2023-02-13 04:30", "2023-02-13 16:45", "2023-02-05 07:30",
             "2023-03-11 08:30", "2026-08-14 22:45"]
    seen = {r["first_cross"][:16] for r in missing} | {r["first_cross"][:16] for r in late}
    clash = [t for t in OWNER if t in seen]

    print("\n" + "=" * 78)
    print("TWO-POINT RULE, MISSING DIRECTION")
    print("%s  min_bars=%d  limit=%d" % (TF, MIN_BARS, limit))
    print("=" * 78)
    print("\n  VALIDATION against the owner's confirmed candles")
    print("    confirmed candles this test calls wrong : %d %s"
          % (len(clash), clash if clash else ""))
    print("    -> USABLE" if not clash else "    -> STILL WRONG")
    print("\n  legs %d" % len(legs))
    print("    first crossing has its B1              : %4d" % ok)
    print("    neither level ever crossed, no B1      : %4d" % nobody)
    print("    level crossed, NO B1        <-- MISSING : %4d" % len(missing))
    print("    level crossed, B1 LATE      <-- WRONG   : %4d" % len(late))
    for title, bag in (("MISSING", missing), ("LATE", late)):
        if not bag:
            continue
        print("\n--- %s (%d) ---" % (title, len(bag)))
        for r in bag[:show]:
            print("    seed %s %-5s extreme %-9.1f  %-13s %s  lvl %-9.1f  b1: %s"
                  % (r["seed"], "green" if r["green"] else "red", r["extreme"],
                     r["which"], r["first_cross"], r["level"], r["b1"]))
        if len(bag) > show:
            print("    ... and %d more" % (len(bag) - show))
    OUT.write_text(json.dumps({"legs": len(legs), "ok": ok, "missing": missing,
                               "late": late}, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
