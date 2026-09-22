"""Test mag_ratio>=2 filter — IS + OOS, combined with wage10+wknd baseline."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING
from test_experiments_craze import build_module, stats, show, BASE as CRAZE_BASE
from src.btc.btc_routes import _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

MB15 = SWING["min_bars_15m"]
SHIPPED_BASE = dict(CRAZE_BASE)
EXP_DEFAULTS = dict(exp_partial_r=0.0, exp_wage_h=0, exp_skip_weekend=0, exp_bias_momentum_min=0.0, exp_min_swing_ratio=0.0)
BASE = {**SHIPPED_BASE, **EXP_DEFAULTS}


def run_sim(c1h, sw1h, c15, sw15, fine, **overrides):
    sim = build_module()
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **overrides})
    return r["ltf_trades"] if isinstance(r, dict) else r


def main():
    print("=" * 100)
    print("  MAG RATIO >= 2 — IS + OOS VALIDATION")
    print("=" * 100)

    # IS
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("data loaded (%0.0fs)" % (time.time() - t0))

    # Identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **SHIPPED_BASE)
    t_ship = r_ship["ltf_trades"]
    s_ship = stats(t_ship)
    assert s_ship["n"] == 340 and abs(s_ship["gross"] - 225.3) < 0.1, \
        "ANCHOR MISMATCH: %dt %+.1fR" % (s_ship["n"], s_ship["gross"])
    print("  identity gate: %dt %+.1fR — PASS" % (s_ship["n"], s_ship["gross"]))

    # IS configs
    print("\n  IS RESULTS:")
    print("  %-30s %4s %8s  %5s  %4s  %s" % ("config", "n", "NET", "DD", "N/D", "yearly"))
    print("  " + "-" * 90)

    configs = [
        ("raw base", {}),
        ("wknd skip", dict(exp_skip_weekend=1)),
        ("wknd+wage10", dict(exp_skip_weekend=1, exp_wage_h=10)),
        ("wknd+wage10+bm05", dict(exp_skip_weekend=1, exp_wage_h=10, exp_bias_momentum_min=0.5)),
        ("wknd+wage10+mag2", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=2.0)),
        ("wknd+wage10+mag1.5", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=1.5)),
        ("wknd+wage10+mag2.5", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=2.5)),
        ("wknd+wage10+mag3", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=3.0)),
        ("wknd+wage10+mag5", dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=5.0)),
        ("wknd+wage10+bm05+mag2", dict(exp_skip_weekend=1, exp_wage_h=10, exp_bias_momentum_min=0.5, exp_min_swing_ratio=2.0)),
        ("wknd+wage10+bm08+mag2", dict(exp_skip_weekend=1, exp_wage_h=10, exp_bias_momentum_min=0.8, exp_min_swing_ratio=2.0)),
    ]

    is_results = {}
    for name, flags in configs:
        trades = run_sim(c1h, sw1h, c15, sw15, fine=[], **flags)
        s = stats(trades)
        is_results[name] = s
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-30s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # OOS
    print("\n  Loading OOS data...")
    from test_4_new_concepts import load_unseen, load_fine_1m
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=MB15)
    print("  OOS data loaded")

    print("\n  OOS RESULTS:")
    print("  %-30s %4s %8s  %5s  %5s  %s" % ("config", "n", "NET", "DD", "N/D", "yearly"))
    print("  " + "-" * 90)

    for name, flags in configs:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        s = stats(trades)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        is_s = is_results[name]
        is_ndd = abs(is_s["gross"] / is_s["dd"]) if is_s["dd"] > 0 else 0
        print("  %-30s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # Delta table
    print("\n  IS vs OOS COMPARISON:")
    print("  %-30s  IS NET    OOS NET   DELTA   IS N/D   OOS N/D" % "config")
    print("  " + "-" * 85)
    for name, flags in configs:
        is_s = is_results[name]
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        oos_s = stats(trades)
        is_ndd = abs(is_s["gross"] / is_s["dd"]) if is_s["dd"] > 0 else 0
        oos_ndd = abs(oos_s["gross"] / oos_s["dd"]) if oos_s["dd"] > 0 else 0
        delta = oos_s["gross"] - 55.7  # vs baseline
        print("  %-30s  %+7.1f   %+7.1f   %+6.1f   %5.2f    %5.2f" % (
            name, is_s["gross"], oos_s["gross"], delta, is_ndd, oos_ndd))


if __name__ == "__main__":
    main()
