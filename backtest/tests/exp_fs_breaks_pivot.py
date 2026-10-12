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
from src.btc.btc_swing import compute_btc_swings, compute_btc_flow

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_fs_breaks_pivot.json"

CONFIRMED_FS = {
    "2024-07-16 19:00": True,
    "2025-07-20 16:15": True,
    "2024-07-16 18:00": False,
    "2025-07-20 15:30": False,
}


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    candles = list(candles)
    flow = list(flow)
    sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(flow) // 2))
    segs = compute_btc_flow(flow, day_mode="continuous")

    # corners of the white line: every segment endpoint
    corners = {}
    for s in segs:
        corners.setdefault(s["endIdx"], []).append(("end", s["endPx"], s["dir"]))
        corners.setdefault(s["startIdx"], []).append(("start", s["startPx"], s["dir"]))

    fs_rows = []
    for s in sw:
        fa = s.get("fs_at_idx")
        if fa is None or fa < 2:
            continue
        fs_rows.append({"swing": s["swing_index"], "idx": fa,
                        "time": candles[fa]["date"][:16], "dir": s["dir"],
                        "start_idx": s["seg"]["start_idx"]})

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
        want_high = (r["dir"] == "up")     # an up leg ends by breaking a high corner
        cc = candles[i]

        # nearest flow-line corner on the right side that this bar breaches
        hit = None
        for j in sorted((k for k in corners if k < i), reverse=True):
            if i - j > 60:
                break
            for kind, lvl, _d in corners[j]:
                if want_high and cc["high"] > lvl:
                    hit = (j, lvl)
                    break
                if (not want_high) and cc["low"] < lvl:
                    hit = (j, lvl)
                    break
            if hit:
                break
        if not hit:
            fails["1_no_corner_broken"].append(r)
            continue
        okc["1"] += 1
        pj, lvl = hit

        # 2. the corner must really turn the line (it is an endpoint of a segment)
        turns = len(corners.get(pj, [])) >= 2
        if not turns:
            fails["2_not_a_corner"].append(dict(r, corner=candles[pj]["date"][:16],
                                               level=round(lvl, 1)))
            continue
        okc["2"] += 1

        # 3. freshness
        already = None
        for k in range(pj + 1, i):
            if want_high and candles[k]["high"] > lvl:
                already = k
                break
            if (not want_high) and candles[k]["low"] < lvl:
                already = k
                break
        if already is not None:
            fails["3_corner_not_fresh"].append(dict(r, corner=candles[pj]["date"][:16],
                                                    level=round(lvl, 1),
                                                    earlier=candles[already]["date"][:16]))
            continue
        okc["3"] += 1

        # 4. the 50-bar window
        if i < r["start_idx"] + MIN_BARS:
            fails["4_inside_window"].append(dict(r, corner=candles[pj]["date"][:16],
                                                  bars_in=i - r["start_idx"]))
            continue
        okc["4"] += 1

    n = len(fs_rows)
    print("CHECK RESULTS")
    print("-" * 86)
    print("   1  FS bar breaks a flow-line corner : %4d ok  %4d FAIL"
          % (okc["1"], len(fails["1_no_corner_broken"])))
    print("   2  that point is a real corner     : %4d ok  %4d FAIL"
          % (okc["2"], len(fails["2_not_a_corner"])))
    print("   3  the corner is FRESH             : %4d ok  %4d FAIL"
          % (okc["3"], len(fails["3_corner_not_fresh"])))
    print("   4  FS outside the 50-bar window    : %4d ok  %4d FAIL"
          % (okc["4"], len(fails["4_inside_window"])))
    print("-" * 86)
    print("   FS checked %d    fully valid %d    with a defect %d"
          % (n, okc["4"], n - okc["4"]))
    print()

    for k in ("1_no_corner_broken", "2_not_a_corner", "3_corner_not_fresh", "4_inside_window"):
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
