"""Plateau or spike: the test that decides whether a knob counts as a trial.

THE IDEA
--------
The deflated study charged 464 trials, most of them numeric knob sweeps. The
defence of those sweeps was that a threshold nudged by 0.05 is not a different
strategy - it is the same strategy measured twice.

That defence is only worth anything if the knob sits on a plateau. If moving
`chop_thresh` from 58 to 50 destroys the result, then 58 was fitted to the
sweep point and every value along that line really is a separate trial. If the
book survives the whole neighbourhood, the sweep was measuring one strategy and
its trial count is close to honest.

So this sweeps each varying numeric knob across a wide grid, one knob at a time,
holding everything else at the champion's settings, and reports the shape.

  PLATEAU   performance holds across a wide band. One strategy. Few trials.
  SPIKE     performance collapses either side of a single value. Fitted.

Read on IS only. OOS is read once at the end, at whatever the IS plateau picks,
because reading OOS at every grid point is how the 2021-22 era gets turned into
another selection surface - which is the thing this whole file exists to avoid.

Output: dof_plateau.json + dof_plateau.md
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402

OUT = HERE / "dof_plateau.json"
MD = HERE / "dof_plateau.md"
BOOK = "fsent_champ_long"

# A wide grid per knob, deliberately wider than the 2-5 values the registry
# actually used. The question is not which values were chosen, it is how far
# the book can be pushed before it breaks - so the grid has to extend past the
# registered values in both directions.
GRIDS = {
    "chop_thresh":           [42, 46, 50, 54, 58, 62, 66, 70, 76],
    "exp_trail_skip_n":      [0, 1, 2, 3, 4, 6, 8, 12],
    "cooldown_bars":         [0, 2, 4, 6, 8, 12, 16, 24],
    "max_consecutive_losses": [0, 1, 2, 3, 4, 6],
    "ext_stop_r":            [0, 0.75, 1.5, 2.25, 3.0, 4.0, 6.0],
    "sl_buf_atr":            [0.0, 0.005, 0.01, 0.05, 0.15, 0.25],
    "exp_partial_r":         [0.0, 1.5, 3.0, 5.0, 7.5, 10.0],
    "exp_bias_momentum_min": [0.0, 0.3, 0.5, 0.7, 0.9, 1.0],
}
# Fraction of the swept range that must stay within reach of the best cell for
# the knob to count as a plateau rather than a spike.
GOOD_FRAC = 0.60


def run(sim, data, cfg, swing):
    params = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **params)
    tr = o["ltf_trades"] if isinstance(o, dict) else o
    tr = [t for t in tr if t.get("outcome") != "open"]
    rs = [net_r([t]) for t in tr]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"n": len(rs), "net": round(sum(rs), 2), "dd": round(dd, 2),
            "avg_r": round(sum(rs) / len(rs), 4) if rs else 0.0}


def main() -> int:
    t0 = time.time()
    print("loading data ...", flush=True)
    data = get_data()
    sim = build_family_module()
    cfg = dict(EXPERIMENTS[BOOK])
    swing = cfg.get("swing") or "sw10"
    base_params = {**BP, **(cfg.get("params") or {})}

    res = {"book": BOOK, "knobs": {}}
    print("baseline ...", flush=True)
    b = run(sim, data, cfg, swing)
    print("  %s" % b, flush=True)
    res["baseline"] = b

    for knob, grid in GRIDS.items():
        if knob not in base_params:
            continue
        cells = []
        print("\n%s = %s (registered %s)" % (knob, grid, base_params[knob]), flush=True)
        for v in grid:
            c = dict(cfg)
            c["params"] = dict(base_params)
            c["params"][knob] = v
            r = run(sim, data, c, swing)
            r["value"] = v
            cells.append(r)
            flag = " <- registered" if v == base_params[knob] else ""
            print("   %6s  n=%4d  net %+9.2f  dd %6.2f  avg_r %+.4f%s"
                  % (v, r["n"], r["net"], r["dd"], r["avg_r"], flag), flush=True)
        best = max(c["net"] for c in cells)
        # A cell counts as "holding up" if it keeps at least 60% of the best
        # net. Stricter than sign, looser than demanding the peak.
        good = [c for c in cells if best > 0 and c["net"] >= GOOD_FRAC * best]
        spread = (max(c["value"] for c in good) - min(c["value"] for c in good)) if good else 0
        res["knobs"][knob] = {
            "registered": base_params[knob], "grid": grid, "cells": cells,
            "best_net": best,
            "good_frac": GOOD_FRAC,
            "good_cells": len(good), "total_cells": len(cells),
            "coverage": round(len(good) / len(cells), 3),
            "good_spread": spread,
            "shape": "PLATEAU" if len(good) >= 3 and spread > 0 else "SPIKE",
        }
        print("   -> %s  (%d/%d cells hold, spread %s)"
              % (res["knobs"][knob]["shape"], len(good), len(cells), spread), flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))

    # ---------------- report ----------------
    L = ["# Plateau or spike", "",
         "Book swept: `%s`. IS only, one knob at a time, everything else held." % BOOK,
         "A knob counts as ONE trial, not as a trial per grid point, only if the",
         "book survives its neighbourhood. A knob that only works at one value was",
         "fitted to that value and every point along the line is a real trial.", "",
         "| knob | registered | good cells | spread | shape |", "|---|---:|---:|---:|---|"]
    for k, v in res["knobs"].items():
        L.append("| `%s` | %s | %d/%d | %s | **%s** |"
                 % (k, v["registered"], v["good_cells"], v["total_cells"],
                    v["good_spread"], v["shape"]))
    L.append("")
    L.append("## The numbers behind the shapes")
    L.append("")
    for k, v in res["knobs"].items():
        L.append("### `%s`" % k)
        L.append("")
        L.append("| value | n | net | dd | avg_r |")
        L.append("|---:|---:|---:|---:|---:|")
        for c in v["cells"]:
            mark = " **<- registered**" if c["value"] == v["registered"] else ""
            L.append("| %s%s | %d | %+.2f | %.2f | %+.4f |"
                     % (c["value"], mark, c["n"], c["net"], c["dd"], c["avg_r"]))
        L.append("")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())