"""SIGNAL PLANE — can the both-side lane be rescued, and can long add to short?

Two questions, run as one harness so the data loads once.

QUESTION 1 — the both-side lane. 37 signal books trade both sides and the best
of them reaches +48.5R out of sample, against +190.5R for the best short-only
book. 22 of the 37 are positive in sample and negative out of it. Is that a
configuration problem or the lane itself? wage20_swingpause_sig_sw10 is the best
both-side book, so if any book can be swept it is that one. Its distinctive
knobs are exp_wage_h (a waiting gate, 20h), exp_swingpause and
exp_skip_weekend. The sweep is a fixed pre-registered ladder; the shape across it
is the answer, not the best cell.

QUESTION 2 — long on top of short. The directional ladder found something the
rankings could not: removing exp_skip_weekend lifted LONG out of sample from
+49.8R to +75.6R, a 52% gain, while costing short only +190.5R to +182.0R. So
the weekend gate helps short and hurts long. Two books cannot share one slot, but
they can be measured separately and the split judged from the numbers. This
measures the four combinations of (side) x (weekend gate) on the same book, plus
the trade count each implies, because on one slot a long trade occupies the slot
a short would have used.

Nothing is written to the registry.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_signal_both_long.py
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

OUT = ROOT / "backtest/tests/_signal_both_long.json"

from exp_full_metrics import compute  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

BOTH_BASE = "wage20_swingpause_sig_sw10"

# Pre-registered fixed ladders. exp_wage_h is the waiting gate; the others are
# the filters this family carries.
WAGE_H = (8, 10, 14, 20, 28, 40)

FS_BASE = "fsent_sig_full"
class Runner:
    """One data load per era, many runs."""

    def __init__(self, era):
        from exp_tf_family import build_family_module
        from run_experiment import BP, net_r, get_swings
        self.BP, self.net_r, self.get_swings = BP, net_r, get_swings
        self.sim = build_family_module()
        self.data = load_era(era)

    def run(self, key, extra):
        from experiment_registry import EXPERIMENTS
        cfg = EXPERIMENTS[key]
        p = {**self.BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        for k, v in extra.items():
            if v is None:
                p.pop(k, None)
            else:
                p[k] = v
        sw = self.get_swings(self.data, cfg.get("swing") or "sw10")
        d = self.data
        out = self.sim(d["c1h"], sw, d["c15"], d["sw15"],
                       fine_ltf=d["fine"], **p)
        tr = out["ltf_trades"] if isinstance(out, dict) else out
        rs = [self.net_r([t]) for t in tr]
        ds = [t.get("entry_date", "") for t in tr]
        return compute(rs, ds)


def line(tag, m):
    print("  %-30s n=%4d net=%+8.1f R/t=%+.3f WR=%4.1f%% PF=%4.2f DD=%5.1f"
          % (tag[:30], m.get("n", 0), m.get("net", 0), m.get("avgR", 0),
             m.get("wr", 0), m.get("pf") or 0, m.get("max_dd", 0)), flush=True)


def main() -> int:
    t0 = time.time()
    payload = {"stage": "signal_both_long", "configs": {}}

    for era in ("is", "oos"):
        print("\n=== bybit %s ===" % era.upper(), flush=True)
        R = Runner(era)

        print("\n[1] %s - exp_wage_h ladder" % BOTH_BASE, flush=True)
        w_res = {}
        for h in WAGE_H:
            m = R.run(BOTH_BASE, {"exp_wage_h": h})
            w_res["wage_h=%d" % h] = m
            line("wage_h=%d" % h, m)

        print("\n[1b] %s - filters on and off" % BOTH_BASE, flush=True)
        f_res = {}
        for tag, extra in (("as-is", {}),
                           ("-swingpause", {"exp_swingpause": 0}),
                           ("-skip_weekend", {"exp_skip_weekend": 0}),
                           ("-wage_h", {"exp_wage_h": 0}),
                           ("-swingpause -skip_weekend",
                            {"exp_swingpause": 0, "exp_skip_weekend": 0}),
                           ("all three off",
                            {"exp_swingpause": 0, "exp_skip_weekend": 0,
                             "exp_wage_h": 0})):
            m = R.run(BOTH_BASE, extra)
            f_res[tag] = m
            line(tag, m)
        payload["configs"].setdefault(era, {})["1_both_sweep"] = \
            {"book": BOTH_BASE, "wage_h": w_res, "filters": f_res}

        print("\n[2] %s - side x weekend gate" % FS_BASE, flush=True)
        c_res = {}
        for side in ("short", "long", "both"):
            for wk, wt in (("wk_on", 1), ("wk_off", 0)):
                m = R.run(FS_BASE, {"exp_fs_entry_side": side,
                                    "exp_skip_weekend": wt})
                c_res["%s|%s" % (side, wk)] = m
                line("%s | %s" % (side, wk), m)
        payload["configs"].setdefault(era, {})["2_side_weekend"] = \
            {"book": FS_BASE, "cells": c_res}

    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())