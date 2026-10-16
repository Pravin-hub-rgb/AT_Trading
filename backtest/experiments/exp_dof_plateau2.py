"""Plateau sweep part 2 - the two knobs that were skipped in part 1.

`exp_dof_plateau.py` skipped exp_trail_skip_n and exp_bias_momentum_min because
neither is in the BP defaults, so the champion book did not carry them and the
sweep had nothing to vary. Skipping them is not the same as them being safe -
they are the two most-contested knobs in the family, and the whole question is
whether a book fitted one of them to a single value.

So each is swept on a book that actually carries it, on IS only, same rule:
everything else held, one knob moved, and the shape read off the neighbourhood.

exp_bias_momentum_min gets a book that carries it in the registry
(fsent_champ_long_biasmom05, 0.5). exp_trail_skip_n gets the champion plus the
book the registry already uses for it, because trailing-skip behaves differently
on a book that was not built around it.

Output: dof_plateau2.json
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
from exp_dof_plateau import run, GOOD_FRAC  # noqa: E402
from run_experiment import get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402

OUT = HERE / "dof_plateau2.json"

WORK = [
    ("fsent_champ_long_biasmom05", "exp_bias_momentum_min", [0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0]),
    ("fsent_champ_long_htf15_tskip6", "exp_trail_skip_n", [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]),
    ("fsent_champ_long_tskip4", "exp_trail_skip_n", [0, 1, 2, 3, 4, 5, 6, 8]),
]


def main() -> int:
    t0 = time.time()
    print("loading data ...", flush=True)
    data = get_data()
    sim = build_family_module()
    res = {}
    for book, knob, grid in WORK:
        cfg = dict(EXPERIMENTS[book])
        swing = cfg.get("swing") or "sw10"
        bp = {**BP, **(cfg.get("params") or {})}
        cells = []
        print("\n%s  %s = %s (registered %s)" % (book, knob, grid, bp.get(knob)), flush=True)
        for v in grid:
            c = dict(cfg)
            c["params"] = dict(bp)
            c["params"][knob] = v
            r = run(sim, data, c, swing)
            r["value"] = v
            cells.append(r)
            flag = " <- registered" if v == bp.get(knob) else ""
            print("   %4s  n=%4d  net %+9.2f  dd %6.2f  avg_r %+.4f%s"
                  % (v, r["n"], r["net"], r["dd"], r["avg_r"], flag), flush=True)
        best = max(c["net"] for c in cells)
        good = [c for c in cells if best > 0 and c["net"] >= GOOD_FRAC * best]
        spread = (max(c["value"] for c in good) - min(c["value"] for c in good)) if good else 0
        res["%s|%s" % (book, knob)] = {
            "book": book, "knob": knob, "registered": bp.get(knob),
            "cells": cells, "best_net": best, "good_cells": len(good),
            "total_cells": len(cells), "good_spread": spread,
            "shape": "PLATEAU" if len(good) >= 3 and spread > 0 else "SPIKE",
        }
        print("   -> %s (%d/%d hold, spread %s)"
              % (res["%s|%s" % (book, knob)]["shape"], len(good), len(cells), spread), flush=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))
    print("\nwrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())