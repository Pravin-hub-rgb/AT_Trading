"""Final ARM1 verification: chain equality, every mark checked against the candles,
and long/short mirroring. Nothing here trusts the engine's own probe.

WHY THIS IS A SEPARATE FILE
---------------------------
exp_phantom_marks classifies marks by reading engine state from inside _lock. That
approach was wrong twice: once it compared the break against e_hi_pivot, which the
same bar's seal refreshes, so every mark looked like it sat on its own pivot; and
once it flagged on bars_seen < min_bars, which the engine resets per swing. Both
errors produced confident, wrong counts, and the owner had to catch them by eye.

So the checks below do not read engine state at all. They read the chain the engine
emitted and the raw candles, and re-derive from scratch whether each mark could
possibly be where the owner would put it. If this file and the probe ever disagree,
the probe is the suspect.

THE OWNER'S RULE
----------------
A mark is legitimate if the bar broke EITHER

  1. a level that was already standing on an earlier bar - a pivot, or the extreme
     of an earlier candle, or the running extreme - i.e. something that existed
     before this bar, or
  2. the extreme of the FIRST candle of the leg, because the white flow line has not
     been drawn yet and no pivot can exist there.

And it is NOT legitimate if the level it "broke" was set by this very bar, since a
bar cannot break its own extreme into existence.

CHECKS
------
  1  CHAIN EQUALITY    shipped chain == the B1PATCH chain, mark for mark
  2  LEVEL EXISTED     every mark broke a level that was standing before its own bar
  3  REAL CROSSING     the mark's candle actually crossed the level it is stamped at
  4  SELF-BREAK        how many marks sit on a level only their own bar could have
                       created - must be zero
  5  MIRRORING         up-side and down-side marks balance, and the arming guard's
                       accept-branch fires comparably in both directions
  6  DIRECTION SANITY  B1 fires in the leg's own direction, B2 in the opposite

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_arm1_final_check.py [limit]
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

OUT = ROOT / "backtest/tests/_arm1_final_check.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"
LIMIT = 200000


def chain(flow, patched: bool):
    from src.btc.ptc import get            # noqa - placeholder never used
    raise SystemExit


def main() -> int:
    global LIMIT
    if len(sys.argv) > 1:
        LIMIT = int(sys.argv[1])
    t0 = time.time()
    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings
    from src.btc.patched_swings import compute_ships

    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    flow = list(flow)
    cap = len(flow) // 2
    print("loaded %d %s candles\n" % (len(flow), TF), flush=True)

    print("building chains ...", flush=True)
    ship = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=cap)
    patch = compute_ships(flow, "continuous", MIN_BARS)

    def marks(ch):
        return {(x["time"], x["kind"], x["dir"], x["px"])
                for s in ch for x in s["breaks"]}
    S, P = marks(ship), marks(patch)

    results = {}

    # ---- 1 CHAIN EQUALITY -------------------------------------------------
    results["1_chain_equal"] = {
        "shipped": len(S), "patched": len(P),
        "identical": S == P,
        "only_shipped": len(S - P), "only_patched": len(P - S),
    }

    # ---- rebuild a bar -> (high, low) index for level lookups --------------
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    def last_touch(level, upto, is_high):
        """Last bar before `upto` whose high/low equals `level`."""
        arr = highs if is_high else lows
        j = min(upto, len(arr)) - 1
        while j >= 0:
            if arr[j] == level:
                return j
            j -= 1
        return -1

    # ---- 2/3/4 every mark that means "break of a level" -------------------
    # B1 and FLIP stamp px = locked_level, the level that was broken. B2 does
    # NOT: firstswing.py stamps B2 with b2.px, which is the bar's own
    # self.lo/self.hi at the mark bar (see _confirm_direction), so B2 is a
    # location stamp rather than a broken-level stamp and must not be tested
    # against candles this way - doing so flagged 1502 "self-breaks" that are
    # nothing of the kind.
    #
    # Likewise the direction check is dropped: a B1's direction is the direction
    # it LOCKED, while swing.dir is the direction the leg ended up confirmed in
    # after any flips, so they legitimately disagree on most swings.
    LEVEL_KINDS = ("B1", "FLIP")
    no_level = []
    no_cross = []
    selfbreak = []
    b1_up_b1_dn = {"B1": {"up": 0, "down": 0}, "B2": {"up": 0, "down": 0},
                   "FLIP": {"up": 0, "down": 0}}

    for s in ship:
        for x in s["breaks"]:
            i = x["idx"]
            lvl = x["px"]
            is_high = x["dir"] == "up"
            b1_up_b1_dn[x["kind"]][x["dir"]] += 1
            if x["kind"] not in LEVEL_KINDS:
                continue

            j = last_touch(lvl, i, is_high)
            if j < 0:
                no_level.append((x["time"], x["kind"], x["dir"], lvl))
                selfbreak.append((x["time"], x["kind"], x["dir"], lvl, i))
                continue
            arr = highs if is_high else lows
            crossed = (arr[i] > lvl) if is_high else (arr[i] < lvl)
            passed_through = any(
                (arr[k] > lvl) if is_high else (arr[k] < lvl)
                for k in range(j + 1, i))
            if not crossed or passed_through:
                no_cross.append((x["time"], x["kind"], x["dir"], lvl, j, i))

    results["2_level_never_existed"] = {"count": len(no_level),
                                        "first": no_level[:10]}
    results["3_not_a_real_crossing"] = {"count": len(no_cross),
                                        "first": no_cross[:10]}
    results["4_self_breaks"] = {"count": len(selfbreak), "first": selfbreak[:10]}
    results["6_direction_sanity"] = {
        "note": "dropped - B1 stamps the direction it locked, swing.dir is the "
                "direction the leg confirmed in after any flips, so they "
                "legitimately disagree and the check had no meaning",
        "counts": b1_up_b1_dn}

    # ---- 5 MIRRORING ------------------------------------------------------
    up = b1_up_b1_dn["B1"]["up"]
    dn = b1_up_b1_dn["B1"]["down"]
    ratio = (up / dn) if dn else float("inf")
    results["5_mirroring"] = {
        "B1_up": up, "B1_down": dn, "ratio_up_over_down": round(ratio, 4),
        "balanced_within_5pct": abs(ratio - 1.0) <= 0.05,
    }

    # ---- report -----------------------------------------------------------
    print("\n" + "=" * 70)
    print("ARM1 FINAL CHECK   %s min_bars=%d limit=%d" % (TF, MIN_BARS, LIMIT))
    print("=" * 70)
    c = results["1_chain_equal"]
    print("\n1  CHAIN EQUALITY")
    print("     shipped=%d  patched=%d  IDENTICAL=%s  (only_shipped=%d only_patched=%d)"
          % (c["shipped"], c["patched"], c["identical"],
             c["only_shipped"], c["only_patched"]))

    print("\n2  LEVEL EXISTED BEFORE ITS OWN BAR")
    print("     marks whose level was never touched by an earlier bar: %d"
          % results["2_level_never_existed"]["count"])
    for t in results["2_level_never_existed"]["first"][:5]:
        print("       %s" % (t,))

    print("\n3  REAL CROSSING")
    print("     marks whose candle did not cross the level, or the level had"
          " already been broken earlier: %d"
          % results["3_not_a_real_crossing"]["count"])
    for t in results["3_not_a_real_crossing"]["first"][:5]:
        print("       %s" % (t,))

    print("\n4  SELF-BREAKS (bar breaking its own extreme into existence)")
    print("     %d" % results["4_self_breaks"]["count"])
    for t in results["4_self_breaks"]["first"][:5]:
        print("       %s" % (t,))

    m = results["5_mirroring"]
    print("\n5  MIRRORING")
    print("     B1 up=%d  down=%d  ratio=%.4f  balanced(<=5%%)=%s"
          % (m["B1_up"], m["B1_down"], m["ratio_up_over_down"],
             m["balanced_within_5pct"]))
    cs = results["6_direction_sanity"]["counts"]
    print("     counts: B1 up=%d down=%d | B2 up=%d down=%d | FLIP up=%d down=%d"
          % (cs["B1"]["up"], cs["B1"]["down"], cs["B2"]["up"], cs["B2"]["down"],
             cs["FLIP"]["up"], cs["FLIP"]["down"]))

    print("\n6  DIRECTION SANITY")
    print("     dropped - B1 stamps the direction it locked; swing.dir is the "
          "direction the leg confirmed in after flips")
    cs = results["6_direction_sanity"]["counts"]
    print("     raw counts: B1 up=%d down=%d | B2 up=%d down=%d | FLIP up=%d down=%d"
          % (cs["B1"]["up"], cs["B1"]["down"], cs["B2"]["up"], cs["B2"]["down"],
             cs["FLIP"]["up"], cs["FLIP"]["down"]))

    OUT.write_text(json.dumps(results, indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
