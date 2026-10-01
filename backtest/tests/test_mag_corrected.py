"""CORRECTED mag_ratio test — using the SAME engine params as 4-concepts baseline."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING
from test_experiments_craze import build_module, stats
from src.btc.btc_routes import _compute_swings
from test_4_new_concepts import load_unseen, load_fine_1m
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

MB15 = SWING["min_bars_15m"]

# THE ACTUAL SHIPPED V18 PARAMS — same as 4-concepts test
SHIPPED = dict(mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
               sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=0,
               max_consecutive_losses=3, ext_stop_r=3.0, window_end="exit")

# Experiment defaults (all off)
EXP_OFF = dict(exp_partial_r=0.0, exp_wage_h=0, exp_skip_weekend=0,
               exp_bias_momentum_min=0.0, exp_min_swing_ratio=0.0)

BASE = {**SHIPPED, **EXP_OFF}


def run_sim(c1h, sw1h, c15, sw15, fine, **overrides):
    sim = build_module()
    params = {**BASE, **overrides}
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **params)
    return r["ltf_trades"] if isinstance(r, dict) else r


def fmt(s):
    ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
    return "%4dt %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
        s["n"], s["gross"], s["dd"], ndd,
        {k: round(v, 1) for k, v in sorted(s["py"].items())})


def main():
    print("=" * 110)
    print("  CORRECTED: mag_ratio vs BASELINE on SHIPPED V18 PARAMS")
    print("=" * 110)

    # ---- IS ----
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("IS loaded (%0.0fs)" % (time.time() - t0))

    # Identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **SHIPPED)
    s_ship = stats(r_ship["ltf_trades"])
    assert s_ship["n"] == 375 and abs(s_ship["gross"] - 217.9) < 0.1, \
        "ANCHOR: %dt %+.1fR" % (s_ship["n"], s_ship["gross"])
    print("identity: %dt %+.1fR PASS" % (s_ship["n"], s_ship["gross"]))

    # ---- OOS ----
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=MB15)
    print("OOS loaded")

    configs = [
        ("raw base",                      {}),
        ("wknd",                          dict(exp_skip_weekend=1)),
        ("wage10",                        dict(exp_wage_h=10)),
        ("wage10+wknd",                   dict(exp_wage_h=10, exp_skip_weekend=1)),
        ("mag1.5+wknd",                   dict(exp_skip_weekend=1, exp_min_swing_ratio=1.5)),
        ("mag2+wknd",                     dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0)),
        ("mag2.5+wknd",                   dict(exp_skip_weekend=1, exp_min_swing_ratio=2.5)),
        ("mag3+wknd",                     dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0)),
        ("mag4+wknd",                     dict(exp_skip_weekend=1, exp_min_swing_ratio=4.0)),
        ("mag5+wknd",                     dict(exp_skip_weekend=1, exp_min_swing_ratio=5.0)),
        ("mag2+wage10+wknd",              dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=2.0)),
        ("mag3+wage10+wknd",              dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=3.0)),
        ("mag2+wknd+bm05",                dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0, exp_bias_momentum_min=0.5)),
        ("mag3+wknd+bm05",                dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5)),
        ("mag3+wknd+bm08",                dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.8)),
        ("mag2+wknd+swingpause",          dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0, exp_swingpause=1)),
        ("mag3+wknd+swingpause",          dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_swingpause=1)),
        ("mag3+wage10+wknd+bm05",         dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5)),
        ("mag3+wage10+wknd+bm08",         dict(exp_skip_weekend=1, exp_wage_h=10, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.8)),
    ]

    print("\n  IS RESULTS:")
    print("  %-35s %s" % ("config", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 100)
    is_res = {}
    for name, flags in configs:
        trades = run_sim(c1h, sw1h, c15, sw15, fine=[], **flags)
        s = stats(trades)
        is_res[name] = s
        print("  %-35s %s" % (name, fmt(s)))

    print("\n  OOS RESULTS:")
    print("  %-35s %s" % ("config", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 100)
    for name, flags in configs:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        s = stats(trades)
        print("  %-35s %s" % (name, fmt(s)))

    print("\n  HEAD-TO-HEAD: IS vs OOS (vs raw base +19.4R OOS):")
    print("  %-35s  IS NET   OOS NET  oos_delta  IS N/D  OOS N/D  is/oos" % "config")
    print("  " + "-" * 100)
    for name, flags in configs:
        is_s = is_res[name]
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **flags)
        oos_s = stats(trades)
        is_ndd = abs(is_s["gross"] / is_s["dd"]) if is_s["dd"] > 0 else 0
        oos_ndd = abs(oos_s["gross"] / oos_s["dd"]) if oos_s["dd"] > 0 else 0
        ratio = is_s["gross"] / oos_s["gross"] if oos_s["gross"] > 0 else 999
        print("  %-35s  %+7.1f  %+7.1f   %+6.1f   %5.2f   %5.2f   %4.1fx" % (
            name, is_s["gross"], oos_s["gross"], oos_s["gross"] - 19.4,
            is_ndd, oos_ndd, ratio))


if __name__ == "__main__":
    main()
