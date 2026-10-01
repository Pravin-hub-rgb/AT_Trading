"""Test mag_ratio thresholds WITHOUT wage gate — IS + OOS."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING
from test_experiments_craze import build_module, stats, show, BASE as CRAZE_BASE
from src.btc.btc_routes import _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

MB15 = SWING["min_bars_15m"]
EXP_DEFAULTS = dict(exp_partial_r=0.0, exp_wage_h=0, exp_skip_weekend=0,
                    exp_bias_momentum_min=0.0, exp_min_swing_ratio=0.0)
BASE = {**CRAZE_BASE, **EXP_DEFAULTS}


def run_sim(c1h, sw1h, c15, sw15, fine, **overrides):
    sim = build_module()
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **overrides})
    return r["ltf_trades"] if isinstance(r, dict) else r


def main():
    print("=" * 100)
    print("  MAG RATIO — WITHOUT WAGE GATE — IS + OOS")
    print("=" * 100)

    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("IS data loaded (%0.0fs)" % (time.time() - t0))

    # OOS
    from test_4_new_concepts import load_unseen, load_fine_1m
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=MB15)
    print("OOS data loaded")

    configs = [
        ("raw base", {}),
        ("wknd", dict(exp_skip_weekend=1)),
        ("mag1.5", dict(exp_skip_weekend=1, exp_min_swing_ratio=1.5)),
        ("mag2", dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0)),
        ("mag2.5", dict(exp_skip_weekend=1, exp_min_swing_ratio=2.5)),
        ("mag3", dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0)),
        ("mag4", dict(exp_skip_weekend=1, exp_min_swing_ratio=4.0)),
        ("mag5", dict(exp_skip_weekend=1, exp_min_swing_ratio=5.0)),
        ("mag2+wage10", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=2.0)),
        ("mag3+wage10", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=3.0)),
        ("mag2+bm08", dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0, exp_bias_momentum_min=0.8)),
        ("mag3+bm08", dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.8)),
    ]

    print("\n  IS RESULTS:")
    print("  %-20s %4s %8s  %5s  %5s  %s" % ("config", "n", "NET", "DD", "N/D", "yearly"))
    print("  " + "-" * 85)

    is_results = {}
    for name, flags in configs:
        trades = run_sim(c1h, sw1h, c15, sw15, fine=[], **flags)
        s = stats(trades)
        is_results[name] = s
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-20s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    print("\n  OOS RESULTS:")
    print("  %-20s %4s %8s  %5s  %5s  %s" % ("config", "n", "NET", "DD", "N/D", "yearly"))
    print("  " + "-" * 85)

    for name, flags in configs:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        s = stats(trades)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-20s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # Find winner
    print("\n  WINNER by OOS N/D:")
    best_ndd = 0; best_name = ""
    for name, flags in configs:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        s = stats(trades)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        if ndd > best_ndd:
            best_ndd = ndd; best_name = name
    print("  %s (N/D=%.2f)" % (best_name, best_ndd))


if __name__ == "__main__":
    main()
