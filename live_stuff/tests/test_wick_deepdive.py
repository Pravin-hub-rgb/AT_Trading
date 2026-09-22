"""Deep dive: wick_reject combined with other filters — IS + OOS."""
import sys, time
from pathlib import Path
from collections import defaultdict
import statistics

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING
from test_experiments_craze import build_module, stats
from src.btc.btc_routes import _compute_swings
from test_4_new_concepts import load_unseen, load_fine_1m
from test_new_paradigms import compute_indicators, filter_by_indicators
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

MB15 = SWING["min_bars_15m"]
SHIPPED = dict(mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
               sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=0,
               max_consecutive_losses=3, ext_stop_r=3.0, window_end="exit")


def run_sim(c1h, sw1h, c15, sw15, fine, **overrides):
    exp = dict(exp_partial_r=0.0, exp_wage_h=0, exp_skip_weekend=0,
               exp_bias_momentum_min=0.0, exp_min_swing_ratio=0.0)
    params = {**SHIPPED, **exp, **overrides}
    sim = build_module()
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **params)
    return r["ltf_trades"] if isinstance(r, dict) else r


def fmt(s):
    ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
    return "%4dt %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
        s["n"], s["gross"], s["dd"], ndd,
        {k: round(v, 1) for k, v in sorted(s["py"].items())})


def main():
    print("=" * 110)
    print("  WICK REJECT DEEP DIVE — IS + OOS")
    print("=" * 110)

    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("IS loaded (%0.0fs)" % (time.time() - t0))

    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=MB15)
    print("OOS loaded")

    ind_is = compute_indicators(c15)
    ind_oos = compute_indicators(c15o)

    # ================================================================
    # PART 1: Wick reject on different base configs
    # ================================================================
    print("\n  PART 1: wick_reject ON DIFFERENT BASES")
    print("  " + "-" * 100)

    bases = [
        ("raw base", {}),
        ("wknd", dict(exp_skip_weekend=1)),
        ("mag3+wknd", dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0)),
        ("mag3+wknd+bm05", dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5)),
        ("mag2+wknd", dict(exp_skip_weekend=1, exp_min_swing_ratio=2.0)),
        ("mag1.5+wknd", dict(exp_skip_weekend=1, exp_min_swing_ratio=1.5)),
    ]

    print("\n  IS:")
    print("  %-30s  %-20s %s" % ("base", "filter", "n      NET     DD    N/D"))
    print("  " + "-" * 95)
    for bname, bflags in bases:
        trades = run_sim(c1h, sw1h, c15, sw15, fine=[], **bflags)
        base_s = stats(trades)
        filt = filter_by_indicators(trades, c15, ind_is, "wick_rejection")
        filt_s = stats(filt)
        ndd = abs(filt_s["gross"] / filt_s["dd"]) if filt_s["dd"] > 0 else 0
        print("  %-30s  %-20s %s" % (bname, "no filter", fmt(base_s)))
        print("  %-30s  %-20s %s" % ("", "+ wick_reject", fmt(filt_s)))

    print("\n  OOS:")
    print("  %-30s  %-20s %s" % ("base", "filter", "n      NET     DD    N/D"))
    print("  " + "-" * 95)
    for bname, bflags in bases:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **bflags)
        base_s = stats(trades)
        filt = filter_by_indicators(trades, c15o, ind_oos, "wick_rejection")
        filt_s = stats(filt)
        ndd = abs(filt_s["gross"] / filt_s["dd"]) if filt_s["dd"] > 0 else 0
        print("  %-30s  %-20s %s" % (bname, "no filter", fmt(base_s)))
        print("  %-30s  %-20s %s" % ("", "+ wick_reject", fmt(filt_s)))

    # ================================================================
    # PART 2: Wick reject threshold sweep
    # ================================================================
    print("\n  PART 2: wick_reject THRESHOLD SWEEP (on mag3+wknd+bm05)")
    print("  " + "-" * 100)

    base_flags = dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5)
    trades_is = run_sim(c1h, sw1h, c15, sw15, fine=[], **base_flags)
    trades_oos = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **base_flags)

    # Custom wick reject with different thresholds
    date_to_idx_is = {c["date"][:19]: i for i, c in enumerate(c15)}
    date_to_idx_oos = {c["date"][:19]: i for i, c in enumerate(c15o)}

    print("\n  OOS:")
    print("  %-25s %4s %8s  %5s  %5s  %s" % ("threshold", "n", "NET", "DD", "N/D", "yearly"))
    print("  " + "-" * 85)

    for thresh in [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]:
        def custom_wick(trades, candles, ind, idx_map):
            filtered = []
            for t in trades:
                entry_date = t.get("entry_date", "")[:19]
                i = idx_map.get(entry_date, -1)
                if i < 0 or i >= len(candles):
                    filtered.append(t)
                    continue
                rng = ind["highs"][i] - ind["lows"][i]
                if rng > 0:
                    close = ind["closes"][i]
                    high = ind["highs"][i]
                    low = ind["lows"][i]
                    opn = ind["opens"][i]
                    upper_wick = (high - max(opn, close)) / rng
                    lower_wick = (min(opn, close) - low) / rng
                    # Determine trade direction from entry/exit
                    ep = float(t.get("entry_price", 0))
                    xp = float(t.get("exit_price", 0))
                    direction = 1 if xp > ep else -1
                    if direction == 1:
                        reject = lower_wick > thresh
                    else:
                        reject = upper_wick > thresh
                    if not reject:
                        filtered.append(t)
                else:
                    filtered.append(t)
            return filtered

        filt_oos = custom_wick(trades_oos, c15o, ind_oos, date_to_idx_oos)
        s = stats(filt_oos)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  wick>%-20.2f %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            thresh, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # ================================================================
    # PART 3: Combine wick_reject with ema_align and mr
    # ================================================================
    print("\n  PART 3: COMBINED FILTERS (on mag3+wknd+bm05)")
    print("  " + "-" * 100)

    combos = [
        ("baseline", []),
        ("+ wick_reject", ["wick_rejection"]),
        ("+ ema_align", ["ema_alignment"]),
        ("+ mr_1.5", ["mean_reversion_mr_1.5"]),
        ("+ wick + ema", ["wick_rejection", "ema_alignment"]),
        ("+ wick + mr", ["wick_rejection", "mean_reversion_mr_1.5"]),
    ]

    print("\n  IS:")
    print("  %-25s %s" % ("combo", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 90)
    for cname, cfilters in combos:
        trades = run_sim(c1h, sw1h, c15, sw15, fine=[], **base_flags)
        for f in cfilters:
            parts = f.split("_mr_")
            if len(parts) == 2:
                mode = "mean_reversion"
                kw = {"threshold": float(parts[1])}
            else:
                mode = parts[0]
                kw = {}
            trades = filter_by_indicators(trades, c15, ind_is, mode, **kw)
        s = stats(trades)
        print("  %-25s %s" % (cname, fmt(s)))

    print("\n  OOS:")
    print("  %-25s %s" % ("combo", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 90)
    for cname, cfilters in combos:
        trades = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **base_flags)
        for f in cfilters:
            parts = f.split("_mr_")
            if len(parts) == 2:
                mode = "mean_reversion"
                kw = {"threshold": float(parts[1])}
            else:
                mode = parts[0]
                kw = {}
            trades = filter_by_indicators(trades, c15o, ind_oos, mode, **kw)
        s = stats(trades)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-25s %s" % (cname, fmt(s)))

    # ================================================================
    # PART 4: Wick reject on RAW base (no mag3) — does it work standalone?
    # ================================================================
    print("\n  PART 4: wick_reject ON RAW BASE (no mag3)")
    print("  " + "-" * 100)

    raw_is = run_sim(c1h, sw1h, c15, sw15, fine=[])
    raw_oos = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos)

    print("\n  IS:")
    print("  %-25s %s" % ("config", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 90)
    for name, trades, ind, candles in [
        ("raw base", raw_is, ind_is, c15),
        ("raw + wick_reject", filter_by_indicators(raw_is, c15, ind_is, "wick_rejection"), ind_is, c15),
        ("raw + ema_align", filter_by_indicators(raw_is, c15, ind_is, "ema_alignment"), ind_is, c15),
        ("raw + wick + ema", filter_by_indicators(
            filter_by_indicators(raw_is, c15, ind_is, "wick_rejection"), c15, ind_is, "ema_alignment"), ind_is, c15),
    ]:
        s = stats(trades)
        print("  %-25s %s" % (name, fmt(s)))

    print("\n  OOS:")
    print("  %-25s %s" % ("config", "n      NET     DD    N/D    yearly"))
    print("  " + "-" * 90)
    for name, trades, ind, candles in [
        ("raw base", raw_oos, ind_oos, c15o),
        ("raw + wick_reject", filter_by_indicators(raw_oos, c15o, ind_oos, "wick_rejection"), ind_oos, c15o),
        ("raw + ema_align", filter_by_indicators(raw_oos, c15o, ind_oos, "ema_alignment"), ind_oos, c15o),
        ("raw + wick + ema", filter_by_indicators(
            filter_by_indicators(raw_oos, c15o, ind_oos, "wick_rejection"), c15o, ind_oos, "ema_alignment"), ind_oos, c15o),
    ]:
        s = stats(trades)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-25s %s" % (name, fmt(s)))


if __name__ == "__main__":
    main()
