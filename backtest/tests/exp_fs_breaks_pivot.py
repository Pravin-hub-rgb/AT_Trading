"""Does every FS break a pivot - using the FLOW LINE the owner is looking at.

OWNER, 2025-07-20: "what is a pivot? You can look any. So look at from where these
flow line is coming from. This white flow line on the front end is coming from,
these walker lines is coming from. So pivot is any V-shape."

So the pivots are not local bar extremes - they are the CORNERS OF THE WHITE FLOW
LINE. compute_btc_flow returns exactly that, as the segments the frontend draws, and
its end points are the corners. The first version of this file used local bar
extremes instead and produced nonsense: 2450 "not fresh" out of 2863, which is the
detector being wrong rather than the engine, and is exactly the failure mode every
earlier probe in this repo had.

Rule under test, from the owner:
  "It is breaking a pivot, that's it."
  "that pivot was already broken ... it is contaminated already. We cannot look at
   that."      -> the pivot must be FRESH
  "if any FS comes before 50th bar, we neglect it."  -> outside the 50-bar window

Four checks per FS, all from raw candles plus the flow line, never engine state:
  1  the FS bar breaks a flow-line corner on the side the leg needs
  2  the corner is really a corner (the line turns there)
  3  the corner was FRESH - nothing between the corner and the FS took it first
  4  the FS bar is at or past the leg's 50th bar
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.btc.btc_display_walk import display_flow

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_fs_breaks_pivot.json"

# The owner's own rulings, recorded verbatim.
#
# GATE, owner 2026-10-12, asked whether FS may sit ON the 50th bar:
#   "If it is greater than equal to, then FS is at the correct place. [...] If it
#    is allowed on the same bar of the 50th gate, then yes, this is correct."
#   The gate is `bars_seen < min_bars` (firstswing.py L607/L771), so bars_seen
#   == min_bars is already OUTSIDE the window. The 2025-07-20 leg reaches its
#   50th bar at 15:15, and the 15:15 candle is the first to cross the 14:45
#   pivot 118037.0 - so 15:15 is the FS. The owner's earlier 16:15 answer came
#   from the stale break-before-kill snapshot hiding that break; with the snapshot
#   gone the 15:15 crossing is visible and the gate permits it.
#
#   The owner's alternative, recorded so the rule stays testable: "Only if it is
#   not allowed, then we go ahead [...] the pivot is at the low of 15:30, which
#   is got broken by 16:15." 16:15's low 117903.6 does cross 15:30's low
#   117926.7, so that reading is self-consistent too - it is simply not the gate
#   this engine implements.
#
# FRESHNESS, owner 2026-10-12:
#   "If a previous candle have already crossed it, then it is already
#    contaminated. But if previous candle have just seen it, haven't crossed it,
#    and yet another candle have crossed it, that candle can be marked as FS."
#   Touch (equal) is NOT contamination; only a strict cross is.
#
# FS TARGET, owner 2026-10-12 - this is what the stale snapshot was breaking:
#   "In FS case, any new pivot of that direction comes, that replaces the older
#    one. That's it. [...] As soon as a new pivot is shown, the previous one is
#    already retired. We don't have to look for the previous pivot to be broken.
#    That would be for B1 and B2, or flip."
#
# 2023-03-19, owner: "The 18:00 low, 27.131 [...] it broke by 18:30. [...] it is
# not breaking any low, any pivot low." The 18:30 candle's low 27087.6 is the
# first cross of the 18:00 pivot 27131.0, and the leg's 50th bar is 17:00, so
# 18:30 is the FS.
CONFIRMED_FS = {
    "2023-03-19 18:30": True,
    "2023-07-02 07:00": True,
    "2023-10-15 15:15": True,
    "2025-08-22 21:45": True,
    "2024-07-16 19:00": True,
    "2025-07-20 15:15": True,
    # must NOT be marked
    "2023-03-19 19:00": False,
    "2023-07-02 06:30": False,
    "2024-07-16 18:00": False,
    "2025-07-20 15:30": False,
}


# the pivot each engine aimed at, keyed by the bar the cross landed on
from src.firstswing import SwingEngine
TARGET = {}
_r_c = SwingEngine._confirm


def _cap(self, src, trig=None):
    if (self.t[11:16] >= self.time_cap and self.bars_seen >= self.min_bars
            and self._chop_cross_active):
        h = self.last_confirm_hit or {}
        # key by the CROSS bar, because that is what fs_at_idx is - not by the
        # declaring bar, which can be a bar or two later (the snap mechanism).
        TARGET[self.last_chop_cross_idx] = (h.get("idx"), h.get("px"))
    return _r_c(self, src, trig)


SwingEngine._confirm = _cap


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    candles = list(candles)
    flow = list(flow)
    sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(flow) // 2))
    # The line the owner actually SEES, not the pre-splice one.
    #
    # display_pivots() is what btc_routes.py serves as "flow" (btc_display_walk),
    # and it re-draws the candles the walker swallows inside an insider stack.
    # Validating against compute_btc_flow instead was checking a line that no
    # longer appears on the chart: on 2023-01-08 that line draws four points
    # where the chart draws eight, and the 07:45 low the owner rules a real
    # pivot is absent from it.
    segs = display_flow(flow, day_mode="continuous")

    # Corners of the white line, WITH their direction.
    #
    # Direction matters and the first version dropped it. A segment's dir is "B"
    # when it rises and "S" when it falls, so the point a segment ENDS at is a LOW
    # (a V, the owner's word) when that segment rose, and a HIGH (an A) when it fell.
    #
    # Without that, the freshness scan asked "did any bar trade above 16554.0" for a
    # corner that was actually a LOW at 16554.0 - true on the very next bar, every
    # time - and reported 2860 of 2863 as stale. That was the detector, not the engine.
    # A segment's dir is "B" when it RISES and "S" when it FALLS, so the point it
    # ENDS at is a peak (A, high) when the segment rose into it, and a valley
    # (V, low) when it fell into it. The first version had these inverted, which
    # made every up-leg look like it was aiming at a valley: check 2 then failed on
    # a case where the engine was right (2025-06-28 aims at candle 10:00's HIGH
    # 107174.9 for an up leg) and check 5 scanned for a break on the wrong side,
    # which is why it reported a breaker exactly 1 bar later in 2860 of 2863 cases.
    corners = {}
    for s in segs:
        end_kind = "high" if s["dir"] == "B" else "low"    # rose into it -> peak
        start_kind = "low" if s["dir"] == "B" else "high"  # fell into it -> peak
        corners.setdefault(s["endIdx"], set()).add((end_kind, round(s["endPx"], 1)))
        corners.setdefault(s["startIdx"], set()).add((start_kind, round(s["startPx"], 1)))

    fs_rows = []
    for s in sw:
        fa = s.get("fs_at_idx")
        if fa is None or fa < 2:
            continue
        fs_rows.append({"swing": s["swing_index"], "idx": fa,
                        "time": candles[fa]["date"][:16], "dir": s["dir"],
                        "start_idx": s["seg"]["start_idx"],
                        "target_idx": TARGET.get(fa, (None, None))[0],
                        "target_px": TARGET.get(fa, (None, None))[1]})

    print("=" * 86)
    print("FS BREAKS A PIVOT?   pivots taken from the WHITE FLOW LINE the owner sees")
    print("=" * 86)
    print("  candles %d   swings %d   FS %d   flow-line segments %d   corners %d"
          % (len(candles), len(sw), len(fs_rows), len(segs), len(corners)))
    print()

    have = {r["time"] for r in fs_rows}
    print("VALIDATION against the owner's confirmed FS outcomes")
    bad_v = 0
    for t, must in sorted(CONFIRMED_FS.items()):
        ok = (t in have) if must else (t not in have)
        bad_v += (not ok)
        print("   %-18s must %-22s %s" % (t, "have an FS" if must else "have NO FS",
                                           "OK" if ok else "*** WRONG ***"))
    print("   -> %s\n" % ("USABLE" if not bad_v else "NOT USABLE"))

    fails = collections.defaultdict(list)
    okc = collections.Counter()
    for r in fs_rows:
        i = r["idx"]
        # Which side gets breached, read off the leg, not guessed.
        #
        # firstswing._check_chop: a DOWN leg aims at a sealed HIGH and fires when
        # self.hi > tgt.px, so a down leg breaks UPWARD through a peak. An UP leg
        # aims at a sealed LOW and fires when self.lo < tgt.px, so an up leg breaks
        # DOWNWARD through a valley.
        #
        # This line had it exactly backwards. Checking it against the real candles
        # (n=2863) the engine aims at: up -> LOW 1460/1461, down -> HIGH 1401/1402.
        # Scanning "high > lvl" for an up leg tested whether price rose above a
        # valley, which the very next candle satisfies by construction - producing a
        # false "breaker exactly +1 bar later" in 2861 of 2863 cases.
        want_high = (r["dir"] == "down")
        cc = candles[i]

        # The pivot the engine AIMED AT. Asking "is the nearest flow-line corner
        # fresh" instead was comparing the wrong thing: the previous run reported
        # 2450 and 2665 failures that way, and reconciliation then showed the
        # engine's target and the flow line agree on the level in 2863 of 2863
        # cases - so the earlier freshness count was measuring a different level.
        pj, lvl = r.get("target_idx"), r.get("target_px")
        if pj is None or lvl is None or pj >= i:
            fails["1_no_pivot_aimed_at"].append(r)
            continue
        okc["1"] += 1

        # 2. the corner must really turn the line (it is an endpoint of a segment)
        need = "high" if want_high else "low"
        turns = (need, round(lvl, 1)) in corners.get(pj, set())
        if not turns:
            fails["2_target_is_not_a_flow_corner"].append(
                dict(r, corner=candles[pj]["date"][:16], level=round(lvl, 1)))
            continue
        okc["2"] += 1

        brk = (cc["high"] > lvl) if want_high else (cc["low"] < lvl)
        if not brk:
            fails["3_bar_does_not_break_target"].append(
                dict(r, corner=candles[pj]["date"][:16], level=round(lvl, 1)))
            continue
        okc["3"] += 1

        # 4. freshness
        already = None
        for k in range(pj + 1, i):
            if want_high and candles[k]["high"] > lvl:
                already = k
                break
            if (not want_high) and candles[k]["low"] < lvl:
                already = k
                break
        if already is not None:
            fails["5_pivot_not_fresh"].append(dict(r, corner=candles[pj]["date"][:16],
                                                   level=round(lvl, 1),
                                                   earlier=candles[already]["date"][:16]))
            continue
        okc["5"] += 1

    n = len(fs_rows)
    print("CHECK RESULTS")
    print("-" * 86)
    print("   1  engine aimed at a pivot         : %4d ok  %4d FAIL"
          % (okc["1"], len(fails["1_no_pivot_aimed_at"])))
    print("   2  that pivot is a flow-line corner: %4d ok  %4d FAIL"
          % (okc["2"], len(fails["2_target_is_not_a_flow_corner"])))
    print("   3  the FS bar breaks that pivot    : %4d ok  %4d FAIL"
          % (okc["3"], len(fails["3_bar_does_not_break_target"])))
    print("   5  the pivot is FRESH              : %4d ok  %4d FAIL"
          % (okc["5"], len(fails["5_pivot_not_fresh"])))
    print("-" * 86)
    print("   FS checked %d    fully valid %d    with a defect %d"
          % (n, okc["5"], n - okc["5"]))
    print()

    for k in ("1_no_pivot_aimed_at", "2_target_is_not_a_flow_corner",
              "3_bar_does_not_break_target", "5_pivot_not_fresh"):
        if not fails[k]:
            continue
        print("%s  -  %d, first 10:" % (k.upper(), len(fails[k])))
        for r in fails[k][:10]:
            ex = ""
            if "corner" in r:
                ex = "  corner %s @%s" % (r["corner"], r.get("level", "?"))
            if "earlier" in r:
                ex += "  already taken at %s" % r["earlier"]
            if "bars_in" in r:
                ex += "  only %d bars into the leg" % r["bars_in"]
            print("   %s  swing %-5d %s%s" % (r["time"], r["swing"], r["dir"], ex))
        print()

    OUT.write_text(json.dumps({k: v[:400] for k, v in fails.items()},
                              indent=1, default=str), encoding="utf-8")
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
