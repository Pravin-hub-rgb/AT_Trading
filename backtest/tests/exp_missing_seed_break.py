"""Missing-B1 detector built on the owner's rule, from the chain and candles only.

THE RULE, AS HE STATED IT
-------------------------
"If the swing calculation starts from a green candle, the candle extreme would be
the low of it. Now the next pivot comes, any pivot comes at the high side ... So we
have a pivot and we have the green candle low as a candle extreme. Now any new
candle breaks it, it is considered as a B1. For a selling swing we have to just
symmetrically mirror it."

So a leg has two live levels:

  1. the SEED candle's extreme - its LOW when the seed is green, its HIGH when red
  2. the pivot that forms on the opposite side

and any candle that breaks either one is a B1. He verified this on 2023-02-10,
where the swing starts on the green 21:30, 21:45 takes out the 21:30 low (B1, which
he confirmed correct), 22:45 is the next B1 and 01:00 the FLIP.

WHY THE SEED MATTERS SO MUCH
----------------------------
Because a leg's seed is the FIRST candle, its extreme is the level the leg is
waiting on before any pivot exists - the white flow line has not been drawn yet.
The engine's break test is against the RUNNING extreme (e_hi_prev / e_lo_prev),
which on a young leg is exactly the seed's extreme, so the common case already
works. That is why 2023-02-10 needs no fix and why the owner was surprised there was
anything to fix at all.

The seed is available straight off the chain: each swing carries seg.start_idx, the
window position where that leg's calculation began. No engine internals involved.

WHAT IT REPORTS
---------------
For every leg, the first candle after the seed that breaks the seed's extreme, and
whether a B1 was marked there. A leg where the seed's extreme was never broken is
reported separately: that leg moved to the pivot first, which is a different and
valid shape.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_missing_seed_break.py [limit] [show]
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

OUT = ROOT / "backtest/tests/_missing_seed_break.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"
TOL = 2          # a B1 may land a candle or two off the first crossing


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    t0 = time.time()

    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings
    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    chain = compute_btc_swings(list(flow), opts={"minBars": MIN_BARS},
                               max_swings=len(flow) // 2)

    missing, pivot_first, clean = [], 0, 0
    for si, s in enumerate(chain):
        st = s["seg"]["start_idx"]
        if not (0 <= st < len(candles) - 1):
            continue
        end = min(s["seg"].get("end_idx", st + 1), len(candles) - 1)
        seed = candles[st]
        green = seed["close"] >= seed["open"]
        lvl = seed["low"] if green else seed["high"]
        want_dir = "down" if green else "up"

        # first candle after the seed that breaks the seed's extreme
        hit = None
        for i in range(st + 1, min(end + 1, len(candles))):
            c = candles[i]
            broke = (c["low"] < lvl) if green else (c["high"] > lvl)
            if broke:
                hit = i
                break
        if hit is None:
            pivot_first += 1          # leg resolved on the pivot before the extreme
            continue

        # Only marks inside THIS leg count. A swing's break list can carry marks the
        # same engine emitted before this leg's calculation began, and comparing the
        # seed's first break against those is meaningless - it reported 981 false
        # misses before this filter, every one of them matching a B1 at idx 1, 52,
        # 81 against a seed at idx 60 and up.
        b1 = [x for x in s["breaks"]
              if x["kind"] == "B1" and st <= x["idx"] <= end]
        near = [x for x in b1 if abs(x["idx"] - hit) <= TOL]
        if not near:
            got = ", ".join("%s@%d" % (x["dir"], x["idx"]) for x in b1) or "no B1"
            missing.append({
                "swing": si, "seed": candles[st]["date"][:16],
                "green": green, "extreme": lvl, "want_dir": want_dir,
                "first_break": candles[hit]["date"][:16],
                "first_break_idx": hit,
                "b1_marks": got,
                "pivot_break_first": (b1 and b1[0]["idx"] < hit),
            })
        else:
            clean += 1

    n = len(chain)
    print("\n" + "=" * 76)
    print("MISSING SEED-EXTREME BREAKS   %s  min_bars=%d  limit=%d"
          % (TF, MIN_BARS, limit))
    print("=" * 76)
    print("\n  legs %d" % n)
    print("    seed extreme was never broken (leg went to the pivot first) : %d"
          % pivot_first)
    print("    seed extreme broken and a B1 is there                     : %d" % clean)
    print("    seed extreme broken and NO B1 near it   <-- MISSING       : %d"
          % len(missing))

    if missing:
        print("\n--- MISSING (%d) ---" % len(missing))
        print("  %-6s %-17s %-6s %-10s %-17s %s"
              % ("swing", "seed", "green", "extreme", "first break", "B1 marks"))
        for m in missing[:show]:
            print("  %-6d %-17s %-6s %-10.1f %-17s %s"
                  % (m["swing"], m["seed"], m["green"], m["extreme"],
                     m["first_break"], m["b1_marks"]))
        if len(missing) > show:
            print("  ... and %d more in the JSON" % (len(missing) - show))

    OUT.write_text(json.dumps(
        {"legs": n, "pivot_first": pivot_first, "clean": clean,
         "missing": missing}, indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
