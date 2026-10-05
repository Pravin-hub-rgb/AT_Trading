"""SIGNAL PLANE — the directional FS ladder, and a hunt for a long-side edge.

THE GAP. The multi plane already has the four-arm directional FS experiment
(_fs_directional_leg.json, run by exp_fs_directional_leg.py): control, long,
short, both. On champion_multi_sw10_leg, IS went +239.1 control to +528.9 long
and +571.4 short, and `both` landed between them at +426.4. Two readings there:
both sides work about equally on multi, and mixing them dilutes.

Neither has been run on the signal plane. Thirteen books carry
exp_fs_entry_side and every `long` one is multi except fsent_sig_sw10_long. The
signal plane has exactly one long book, so nobody knows whether the long edge
exists there or is simply untested.

EXPERIMENTS, in order:

  A  the four-arm ladder on fsent_sig_full - the best signal book, currently
     short-only. Answers whether short wins by being better than long (a
     structural difference) or by being long's mirror (a trigger that works on
     whichever side you pick, a sum).

  B  long mirrors of the other two strong signal books. If A shows long is
     mirrored, one of these should confirm it.

  C  exp_fs_small_swing across the ladder. This is the trigger that made the FS
     worth having on multi - +239 to +571 - and it appears in only four books.
     If long needs a different trigger width than short, this is where it shows.

  D  the remaining non-default knobs of fsent_sig_full, each removed, on short
     and on long.

Read-only. Nothing is written to the registry; the numbers are a proposal
until someone pins them.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_signal_fs_ladder.py
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

OUT = ROOT / "backtest/tests/_signal_fs_ladder.json"

from exp_full_metrics import compute  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

BASE = "fsent_sig_full"
MIRRORS = ["fsent_sig_fs_mom", "fsent_sig_wk_pause_short"]

# Pre-registered fixed ladder: the point is the shape across it, not the best
# cell in it.
SMALL_SWINGS = (3.0, 4.5, 6.0, 8.0)

# fsent_sig_full's non-default knobs, each switched off to see what it carries.
EXTRA_KNOBS = {
    "exp_bias_momentum_min": 0.0,
    "exp_trail_skip_n": 0,
    "exp_skip_weekend": 0,
    "exp_fs_small_swing": 0.0,
}


def arms_long():
    return {
        "control": {"exp_fs_entry_side": None},
        "short": {"exp_fs_entry_side": "short"},
        "long": {"exp_fs_entry_side": "long"},
        "both": {"exp_fs_entry_side": "both"},
    }
class Runner:
    """One data load per era, many runs. Loading costs ~20s each time."""

    def __init__(self, era):
        from exp_tf_family import build_family_module
        from run_experiment import BP, net_r, get_swings
        self.BP, self.net_r, self.get_swings = BP, net_r, get_swings
        self.sim = build_family_module()
        self.data = load_era(era)
        self.era = era

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


def line(book, arm, m, ref=None):
    tag = ""
    if ref and m.get("n") and ref.get("n"):
        tag = "  dNet=%+8.1f" % (m["net"] - ref["net"])
    print("  %-28s %-9s n=%4d net=%+8.1f R/t=%+.3f WR=%4.1f%% PF=%4.2f DD=%5.1f%s"
          % (book[:28], arm, m.get("n", 0), m.get("net", 0), m.get("avgR", 0),
             m.get("wr", 0), m.get("pf") or 0, m.get("max_dd", 0), tag),
          flush=True)


def main() -> int:
    t0 = time.time()
    payload = {"stage": "signal_fs_ladder", "configs": {}}

    for era in ("is", "oos"):
        print("\n=== bybit %s ===" % era.upper(), flush=True)
        R = Runner(era)

        print("\n[A] four-arm ladder on %s" % BASE, flush=True)
        res = {}
        ref = None
        for arm, extra in arms_long().items():
            m = R.run(BASE, extra)
            if arm == "control":
                ref = m
            res[arm] = m
            line(BASE, arm, m, ref)
        payload["configs"].setdefault(era, {})["A_ladder"] = \
            {"book": BASE, "arms": res}

        print("\n[B] the same ladder on the other strong signal books",
              flush=True)
        b_res = {}
        for key in MIRRORS:
            b_res[key] = {}
            ref = None
            for arm, extra in arms_long().items():
                m = R.run(key, extra)
                if arm == "control":
                    ref = m
                b_res[key][arm] = m
                line(key, arm, m, ref)
        payload["configs"].setdefault(era, {})["B_mirrors"] = b_res

        print("\n[C] exp_fs_small_swing ladder x side", flush=True)
        c_res = {}
        for side in ("short", "long", "both"):
            for w in SMALL_SWINGS:
                m = R.run(BASE, {"exp_fs_small_swing": w,
                                 "exp_fs_entry_side": side})
                c_res["%s@%.1f" % (side, w)] = m
                line(BASE, "%s@%.1f" % (side, w), m)
        payload["configs"].setdefault(era, {})["C_small_swing"] = \
            {"book": BASE, "ladder": SMALL_SWINGS, "cells": c_res}

        print("\n[D] each non-default knob removed, on short and on long",
              flush=True)
        d_res = {}
        for knob, off in EXTRA_KNOBS.items():
            d_res[knob] = {}
            for side in ("short", "long"):
                m = R.run(BASE, {knob: off, "exp_fs_entry_side": side})
                d_res[knob][side] = m
                line(BASE, "%s-%s" % (side, knob), m)
        payload["configs"].setdefault(era, {})["D_knobs"] = \
            {"book": BASE, "cells": d_res}

    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
