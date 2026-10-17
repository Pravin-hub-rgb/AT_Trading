"""Census the last three untested knobs, with the inverse test.

THE INSTRUCTION BEING FOLLOWED
------------------------------
CORRECTED_MARK_SWEEP_2026_10_14.md closed its hypothesis phase with this rule:

    "The remaining untested knobs (window_floor, cap_days, trail_half) should be
     run as a census with the inverse test, NOT as hypothesis sources - the same
     treatment the decay gate got. That is the only version of 'look for new
     edge' that this data supports."

So this is deliberately NOT a search for something better. It switches each knob
on across a grid on one book, records whether it fires at all, and then runs the
inverse test: does the book get WORSE as the knob gets stronger?

The inverse test is what separates a real control from a fitted one. A knob whose
cost rises monotonically with its strength has a mechanism. A knob that is best
in the middle and worse at both ends has been fitted to a middle value, and the
net at that middle is not evidence.

The decay gate got exactly this treatment and produced 120 cells and 0 wins. This
is the same shape, at a much smaller scale, on the three knobs that inventory
said were never switched on.

BOOK: fsent_champ_long, the base the family is defined from, plus the OOS era
read once at the end for anything that looked alive. Nothing is promoted here.

Output: exp_untouched_census.py -> _untouched_census.json + .md
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

OUT = HERE / "_untouched_census.json"
MD = HERE / "_untouched_census.md"

BOOK = "fsent_champ_long"

GRIDS = {
    # the window floor was described in the doc as "never a knob" and then found
    # to have a 900-second hole in it, so both the size and the mode are swept
    "exp_window_floor_s": [None, 1800, 3600, 7200, 14400],
    "exp_window_floor_mode": [None, "floor", "min", "gate"],
    "exp_cap_days": [1, 4, 8, 16, 32, 999],
    "exp_trail_half": [0, 1],
}


def stats(sim, data, cfg, swing):
    p = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
          if t.get("outcome") != "open"]
    tr.sort(key=lambda t: int(t["entry_ts"]))
    rs = [net_r([t]) for t in tr]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"n": len(rs), "net": round(sum(rs), 2), "dd": round(dd, 2)}


def main() -> int:
    t0 = time.time()
    print("loading IS ...", flush=True)
    IS = get_data()
    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    swing = cfg.get("swing") or "sw10"

    base = stats(sim, IS, cfg, swing)
    print("\nbaseline %s: %s\n" % (BOOK, base), flush=True)

    res = {"book": BOOK, "baseline": base, "knobs": {}}

    for knob, grid in GRIDS.items():
        rows = []
        print("%s" % knob, flush=True)
        for v in grid:
            c = dict(cfg)
            c["params"] = dict(cfg.get("params") or {})
            if v is None:
                c["params"].pop(knob, None)
                label = "off"
            else:
                c["params"][knob] = v
                label = str(v)
            try:
                r = stats(sim, IS, c, swing)
            except Exception as exc:  # noqa: BLE001
                print("   %-8s ERROR %s" % (label, str(exc)[:60]), flush=True)
                continue
            r["value"] = label
            rows.append(r)
            fired = (r["n"], r["net"]) != (base["n"], base["net"])
            print("   %-8s n=%4d  net %+9.2f  dd %6.2f   %s"
                  % (label, r["n"], r["net"], r["dd"],
                     "FIRES" if fired else "inert"), flush=True)
        live = [r for r in rows if (r["n"], r["net"]) != (base["n"], base["net"])]
        res["knobs"][knob] = {"cells": rows, "fires": len(live) > 0,
                              "n_cells": len(rows)}
        print("   -> %s\n" % ("FIRES" if live else "INERT on every cell"), flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))
    print("wrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())