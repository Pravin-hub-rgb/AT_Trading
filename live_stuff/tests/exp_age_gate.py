"""P20 - IS THE EXISTING AGE GATE HELPING OR HURTING? (the user's question)

THE QUESTION, which is the sharpest thing asked today
=====================================================
"ya toh dekha age filter hatana se kya hota hai karke toh mtlb yeh age
wageara behter hai"

P19 found that the lanes which ALREADY carry an age gate are the ones
that get worse under my filter:

    age10_dirmatch_swingpause_single   -10.1R IS   (exp_max_swing_age=10)
    age25_dirmatch_multi               -14.3R IS   (exp_max_swing_age=25)
    fullstack_wage10_cd0_single        -12.8R OOS

The obvious alternative explanation to "double filtering is bad" is much
sharper: **the existing age ceiling is itself the problem.**
`exp_max_swing_age` is a CEILING - it refuses entries in windows OLDER
than N hours. My `age > 0.5d` is a FLOOR - it refuses entries in windows
NEWER than 12h. They are not the same rule and they do not obviously
compose. If the ceiling is the wrong shape, removing it and keeping only
the floor should be a straight improvement on those lanes.

THE TEST
========
Four arms, both eras, control reproduced first:

  A  control                    exp_max_swing_age as shipped
  B  ceiling OFF                age gate removed entirely
  C  ceiling OFF + my filter    my nest1h>0.25 AND age>0.5d
  D  ceiling ON  + my filter    the double-filter case P19 showed is
                                worse, re-measured on the same controls
                                so A/B/C/D are all comparable

B is the important one and **it has never been run** - nobody has removed
exp_max_swing_age to see what it costs. It sits in the registry as part
of a lane config, not as an audited decision.

If B > A the age ceiling was a net negative and the whole age-gate family
needs re-examining. If B < A the ceiling is carrying its weight and
P19's result stands as double-filtering rather than as a criticism.

FALSIFIERS, PRE-REGISTERED
==========================
  (a) B does not beat A on any age-gated lane in either era
  (b) C does not beat B on at least one lane -> my floor is not a
      replacement for the ceiling either, and the honest answer is that
      neither shape of age rule adds anything
  (c) the champion (no age ceiling) also improves in the same direction
      -> the effect is about the filter, not about the ceiling
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_crosslane import load, rows_for  # noqa: E402
from exp_smooth_search import evaluate  # noqa: E402

AGE_LANES = [
    "age10_dirmatch_swingpause_single_sw10",
    "age25_dirmatch_multi_sw10",
    "age25_multi_sw10",
]
CONTROL = ["champion_multi_sw10", "dirmatch_multi_sw10"]
MY = lambda r: r["nest1h"] > 0.25 and r["age"] > 0.5


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS
    g = SYMBOL_PARAMS["BTCUSDT"]
    sim = build_module()
    print("=" * 100)
    print("  P20  IS THE EXISTING AGE GATE (ceiling) HELPING OR HURTING?")
    print("=" * 100)
    print("  A control   |  B ceiling OFF  |  C ceiling OFF + my filter")
    print("  |  D ceiling ON + my filter\n")
    for lane in AGE_LANES + CONTROL:
        cfg = EXPERIMENTS[lane]
        p0 = {**BP, **cfg.get("params", {})}
        p_off = {k: v for k, v in p0.items() if k != "exp_max_swing_age"}
        swtag = cfg.get("swing", "sw10")
        print(f"  --- {lane}   (exp_max_swing_age="
              f"{p0.get('exp_max_swing_age', 'none')}) ---")
        for sc in ("is", "oos"):
            args = load(sc, swtag)
            out = []
            for lbl, pp, filt in (
                    ("A control", p0, None),
                    ("B ceiling OFF", p_off, None),
                    ("C OFF + my filter", p_off, MY),
                    ("D ON  + my filter", p0, MY)):
                tr, rr = rows_for(args, pp, sim)
                c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                                     g["entry_slip_pct"],
                                     g["exit_slip_pct"])
                per = c2 / len(tr)
                s = evaluate(rr, per, filt) if filt else evaluate(
                    rr, per, lambda r: True)
                out.append((lbl, s, net_r(tr), len(tr)))
            a = out[0][1]["net"]
            print(f"    [{sc}] control net {out[0][1]['net']:+.1f}R  "
                  f"n={out[0][1]['n']}  (pin net {out[0][2]:+.1f}R "
                  f"n={out[0][3]})")
            for lbl, s, n, cnt in out[1:]:
                # s['net'] is the FILTERED net - net_r(tr) ignores the
                # filter and would silently report the unfiltered book
                print(f"      {lbl:<20} n={s['n']:<4} net={s['net']:+8.1f}R "
                      f"dNet={s['net']-a:>+8.1f}R  R/tr={s['rpt']:+.3f} "
                      f"PF={s['pf']:.2f}  strk={s['streak']}")
        print()
    print("=" * 100)
    print("  B > A on any lane  -> the age CEILING was a net negative")
    print("  B < A              -> the ceiling earns its keep; P19's")
    print("                        double-filter result stands as such")
    print("=" * 100)


if __name__ == "__main__":
    main()
