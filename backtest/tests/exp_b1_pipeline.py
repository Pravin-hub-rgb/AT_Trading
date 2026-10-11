"""The B1 pipeline: check EVERY mark against the candles, print only the ones that fail.

WHY THIS FILE IS BUILT THE WAY IT IS
------------------------------------
Three earlier attempts at this exact tool each produced confident, wrong answers:

  1. exp_phantom_marks read e_hi_pivot at mark time. That field has already been
     overwritten by the mark bar's own seal, so every mark looked like it sat on a
     pivot sealed on its own bar. The owner caught it at 2023-02-04 15:45.
  2. It also flagged bars_seen < min_bars, which the engine resets to 1 at the start
     of every swing and therefore never reaches 50. That alone claimed 7,463 bad
     marks.
  3. exp_missing_b1 read e_hi_pivot_prev without asking whether that pivot still
     belonged to the current leg, so it reported 3,558 "missing" including two the
     owner had explicitly confirmed were correct.

So nothing here reads engine state. The chain is taken as emitted, the candles are
taken raw, and every question is re-derived. If this file and the engine ever
disagree, the engine is right and this file is wrong - and that is the point of
keeping it independent.

WHAT COUNTS AS CORRECT
----------------------
The owner's rule, in full:

  A mark is right when the bar broke something that was already standing:
  a pivot, an earlier candle's extreme, or the running extreme - including the
  extreme of the leg's FIRST candle, because the white flow line does not exist
  there yet and no pivot can.

  A mark is wrong when the level it is stamped at was never standing before its
  own bar, or when the bar did not actually cross it.

  A mark is LATE when an earlier bar already crossed that level. The owner: "if I
  look at each B1 I will come across with something" - a mark one or two candles
  after the real break is that something, and it is invisible on a chart because
  the line still looks right.

KIND COVERAGE
-------------
  B1 and FLIP stamp px = locked_level, the level that was broken. Tested in full.
  B2 is different: _confirm_direction stamps it with b2.px, which is the bar's own
  self.lo / self.hi at the mark bar. B2 is therefore a LOCATION stamp, not a
  broken-level stamp, and testing it against candles produces nothing but noise.
  B2 gets its own check instead: it must follow the B1 of the same leg.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_b1_pipeline.py [limit] [show]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_b1_pipeline.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    t0 = time.time()

    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings
    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    chain = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                               max_swings=len(flow) // 2)

    high = [c["high"] for c in candles]
    low = [c["low"] for c in candles]

    def last_touch(level, upto, arr):
        """Last bar strictly before `upto` whose extreme equals `level`."""
        j = min(upto, len(arr)) - 1
        while j >= 0:
            if arr[j] == level:
                return j
            j -= 1
        return -1

    never_stood = []      # the level did not exist before this bar at all
    no_cross = []         # the bar did not actually cross it
    late = []             # an earlier bar had already crossed it
    b2_orphan = []        # B2 with no B1 in its own swing

    n_b1 = n_b2 = n_flip = 0
    for s in chain:
        s_b1 = [x for x in s["breaks"] if x["kind"] == "B1"]
        for x in s["breaks"]:
            i, lvl, k = x["idx"], x["px"], x["kind"]
            if k == "B2":
                n_b2 += 1
                if not s_b1:
                    b2_orphan.append((x["time"], k, x["dir"], lvl))
                continue
            if k == "B1":
                n_b1 += 1
            else:
                n_flip += 1

            up = x["dir"] == "up"
            arr = high if up else low
            j = last_touch(lvl, i, arr)
            if j < 0:
                never_stood.append({"t": x["time"], "kind": k, "dir": x["dir"],
                                    "lvl": lvl, "idx": i})
                continue
            crossed = (arr[i] > lvl) if up else (arr[i] < lvl)
            if not crossed:
                no_cross.append({"t": x["time"], "kind": k, "dir": x["dir"],
                                 "lvl": lvl, "idx": i, "last_touch": j})
                continue
            for q in range(j + 1, i):
                if (arr[q] > lvl) if up else (arr[q] < lvl):
                    late.append({"t": x["time"], "kind": k, "dir": x["dir"],
                                 "lvl": lvl, "idx": i, "first_cross": q,
                                 "bars_early": i - q})
                    break

    total_bad = len(never_stood) + len(no_cross) + len(late) + len(b2_orphan)
    total = n_b1 + n_b2 + n_flip

    print("\n" + "=" * 74)
    print("B1 PIPELINE   %s  min_bars=%d  limit=%d" % (TF, MIN_BARS, limit))
    print("=" * 74)
    print("\n  swings %d   marks %d   (B1 %d | B2 %d | FLIP %d)"
          % (len(chain), total, n_b1, n_b2, n_flip))
    print("\n  %-52s %6d" % ("FAILURES", total_bad))
    for label, bag in (("level did not exist before the bar", never_stood),
                       ("bar did not actually cross the level", no_cross),
                       ("mark is LATE - an earlier bar crossed first", late),
                       ("B2 with no B1 in its swing", b2_orphan)):
        print("    %-50s %6d" % (label, len(bag)))

    def dump(title, bag, fmt):
        if not bag:
            return
        print("\n--- %s (%d) ---" % (title, len(bag)))
        for r in bag[:show]:
            print("   ", fmt % r)
        if len(bag) > show:
            print("    ... and %d more in the JSON" % (len(bag) - show))

    dump("LEVEL DID NOT EXIST BEFORE THE BAR", never_stood,
         "%(t)-20s %(kind)-5s %(dir)-5s lvl=%(lvl).1f")
    dump("BAR DID NOT CROSS THE LEVEL", no_cross,
         "%(t)-20s %(kind)-5s %(dir)-5s lvl=%(lvl).1f")
    dump("MARK IS LATE - FIRST CROSS WAS EARLIER", late,
         "%(t)-20s %(kind)-5s %(dir)-5s lvl=%(lvl).1f  first_cross=%(first_cross).0f bars early=%(bars_early).0f")
    dump("B2 WITH NO B1 IN ITS SWING", b2_orphan,
         "%(0)-20s %(1)-5s %(2)-5s px=%(3).1f")

    OUT.write_text(json.dumps({
        "tf": TF, "min_bars": MIN_BARS, "limit": limit,
        "swings": len(chain), "marks": total,
        "B1": n_b1, "B2": n_b2, "FLIP": n_flip,
        "never_stood": never_stood, "no_cross": no_cross,
        "late": late, "b2_orphan": b2_orphan,
    }, indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
