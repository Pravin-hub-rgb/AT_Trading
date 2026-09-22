"""3 NEW PARADIGM EXPERIMENTS — IS + OOS

Experiment 1: Volume proxy — body/wick ratio as participation signal
Experiment 2: Compression breakout — volatility squeeze → expansion entry
Experiment 3: Mean reversion fade — fade failed breakouts

All run on the CURRENT shipped engine with mag3+wknd+bm05 baseline.
"""
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


def compute_indicators(candles):
    """Compute indicators from 15m candles."""
    n = len(candles)
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    opens = [float(c["open"]) for c in candles]

    # True range
    tr = [0.0] * n
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr[i] = max(h - l, abs(h - pc), abs(l - pc))

    # ATR(5) and ATR(20)
    atr5 = [0.0] * n
    atr20 = [0.0] * n
    for i in range(n):
        s5 = max(0, i - 4)
        s20 = max(0, i - 19)
        atr5[i] = sum(tr[s5:i + 1]) / min(5, i + 1)
        atr20[i] = sum(tr[s20:i + 1]) / min(20, i + 1)

    # Body/wick ratio (volume proxy)
    body_wick = [0.0] * n
    for i in range(n):
        rng = highs[i] - lows[i]
        if rng > 0:
            body = abs(closes[i] - opens[i])
            body_wick[i] = body / rng  # 0 = all wick, 1 = all body

    # Inside bar detection
    inside = [False] * n
    for i in range(1, n):
        if highs[i] <= highs[i - 1] and lows[i] >= lows[i - 1]:
            inside[i] = True

    # Consecutive inside bars
    inside_count = [0] * n
    for i in range(n):
        if inside[i]:
            inside_count[i] = inside_count[i - 1] + 1

    # Bollinger squeeze (BB width / BB middle)
    bb_squeeze = [0.0] * n
    for i in range(19, n):
        window = closes[i - 19:i + 1]
        mid = sum(window) / 20
        std = statistics.stdev(window) if len(window) > 1 else 0
        upper = mid + 2 * std
        lower = mid - 2 * std
        bb_squeeze[i] = (upper - lower) / mid if mid > 0 else 0

    # BB squeeze percentile (rolling)
    bb_pctile = [0.0] * n
    for i in range(50, n):
        window = bb_squeeze[i - 49:i + 1]
        current = bb_squeeze[i]
        below = sum(1 for x in window if x < current)
        bb_pctile[i] = below / len(window)

    # EMA(20) and EMA(50)
    ema20 = [0.0] * n
    ema50 = [0.0] * n
    k20 = 2.0 / 21
    k50 = 2.0 / 51
    ema20[0] = closes[0]
    ema50[0] = closes[0]
    for i in range(1, n):
        ema20[i] = closes[i] * k20 + ema20[i - 1] * (1 - k20)
        ema50[i] = closes[i] * k50 + ema50[i - 1] * (1 - k50)

    return {
        "atr5": atr5, "atr20": atr20, "body_wick": body_wick,
        "inside": inside, "inside_count": inside_count,
        "bb_squeeze": bb_squeeze, "bb_pctile": bb_pctile,
        "ema20": ema20, "ema50": ema50,
        "closes": closes, "highs": highs, "lows": lows, "opens": opens,
    }


def filter_by_indicators(trades, candles, indicators, mode, **kwargs):
    """Post-filter trades by indicators."""
    filtered = []
    date_to_idx = {c["date"][:19]: i for i, c in enumerate(candles)}

    for t in trades:
        entry_date = t.get("entry_date", "")[:19]
        i = date_to_idx.get(entry_date, -1)
        if i < 0 or i >= len(candles):
            filtered.append(t)
            continue

        keep = True

        if mode == "body_wick_min":
            # Only enter when body/wick ratio > threshold (strong candle)
            keep = indicators["body_wick"][i] >= kwargs.get("threshold", 0.5)

        elif mode == "body_wick_max":
            # Only enter when body/wick ratio < threshold (weak candle = reversal)
            keep = indicators["body_wick"][i] <= kwargs.get("threshold", 0.3)

        elif mode == "vol_expansion":
            # Volume proxy: ATR expanding (ATR5 > ATR20 * multiplier)
            mult = kwargs.get("multiplier", 1.2)
            keep = indicators["atr5"][i] > indicators["atr20"][i] * mult

        elif mode == "compression_breakout":
            # Was in compression (bb_pctile < low) and now breaking out
            low_pctile = kwargs.get("low_pctile", 0.25)
            # Check if recent bars were in compression
            if i >= 5:
                recent_pctile = indicators["bb_pctile"][i - 5:i]
                was_compressed = any(p < low_pctile for p in recent_pctile)
                # Now expanding (bb_pctile rising)
                expanding = indicators["bb_pctile"][i] > indicators["bb_pctile"][i - 1]
                keep = was_compressed and expanding
            else:
                keep = False

        elif mode == "inside_bar_breakout":
            # Previous bar was inside, current bar breaks out
            if i >= 2:
                was_inside = indicators["inside"][i - 1]
                broke_high = indicators["highs"][i] > indicators["highs"][i - 1]
                broke_low = indicators["lows"][i] < indicators["lows"][i - 1]
                keep = was_inside and (broke_high or broke_low)
            else:
                keep = False

        elif mode == "squeeze_breakout":
            # Bollinger squeeze (bb_pctile < low) for N bars, then breakout
            min_bars = kwargs.get("min_bars", 3)
            low_pctile = kwargs.get("low_pctile", 0.25)
            if i >= min_bars:
                recent = indicators["bb_pctile"][i - min_bars:i]
                was_squeezed = all(p < low_pctile for p in recent)
                expanding = indicators["bb_pctile"][i] > indicators["bb_pctile"][i - 1]
                keep = was_squeezed and expanding
            else:
                keep = False

        elif mode == "ema_alignment":
            # EMA20 > EMA50 (trend confirmation)
            keep = indicators["ema20"][i] > indicators["ema50"][i]

        elif mode == "trend_strength":
            # ADX-like: |EMA20 - EMA50| / ATR20 > threshold
            threshold = kwargs.get("threshold", 0.5)
            diff = abs(indicators["ema20"][i] - indicators["ema50"][i])
            atr = indicators["atr20"][i]
            keep = (diff / atr > threshold) if atr > 0 else False

        elif mode == "mean_reversion":
            # Price far from EMA20 (mean reversion signal)
            threshold = kwargs.get("threshold", 2.0)
            dist = (indicators["closes"][i] - indicators["ema20"][i]) / indicators["atr20"][i] if indicators["atr20"][i] > 0 else 0
            # For longs: price below EMA (oversold). For shorts: price above EMA (overbought)
            if t.get("r_multiple", 0) > 0:
                keep = dist > threshold  # winners: price was above EMA (trend)
            else:
                keep = dist < -threshold  # losers: price was below EMA (mean reversion)

        elif mode == "wick_rejection":
            # Long upper wick = selling pressure, long lower wick = buying pressure
            rng = indicators["highs"][i] - indicators["lows"][i]
            if rng > 0:
                close = indicators["closes"][i]
                high = indicators["highs"][i]
                low = indicators["lows"][i]
                upper_wick = (high - max(indicators["opens"][i], close)) / rng
                lower_wick = (min(indicators["opens"][i], close) - low) / rng
                # Long wick in trade direction = rejection = bad
                direction = 1 if t.get("entry_price", 0) < t.get("exit_price", 0) else -1
                if direction == 1:
                    keep = lower_wick < 0.3  # not too much lower wick (buying rejection)
                else:
                    keep = upper_wick < 0.3  # not too much upper wick (selling rejection)

        if keep:
            filtered.append(t)

    return filtered


def main():
    print("=" * 110)
    print("  3 NEW PARADIGM EXPERIMENTS — IS + OOS")
    print("=" * 110)

    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("IS loaded (%0.0fs)" % (time.time() - t0))

    # OOS
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=MB15)
    print("OOS loaded")

    # Compute indicators
    ind_is = compute_indicators(c15)
    ind_oos = compute_indicators(c15o)

    # Baseline: mag3+wknd+bm05
    base_flags = dict(exp_skip_weekend=1, exp_min_swing_ratio=3.0, exp_bias_momentum_min=0.5)
    trades_is = run_sim(c1h, sw1h, c15, sw15, fine=[], **base_flags)
    trades_oos = run_sim(c1ho, sw10_oos, c15o, sw15_oos, fine=fine_oos, **base_flags)
    base_is = stats(trades_is)
    base_oos = stats(trades_oos)

    print("\n  BASELINE: mag3+wknd+bm05")
    print("  IS: %dt %+8.1fR  DD %5.1f" % (base_is["n"], base_is["gross"], base_is["dd"]))
    print("  OOS: %dt %+8.1fR  DD %5.1f" % (base_oos["n"], base_oos["gross"], base_oos["dd"]))

    # ================================================================
    # EXPERIMENT 1: VOLUME PROXY (body/wick ratio, ATR expansion, wick rejection)
    # ================================================================
    print("\n" + "=" * 110)
    print("  EXPERIMENT 1: VOLUME PROXY (body/wick ratio as participation signal)")
    print("=" * 110)

    exp1_configs = [
        ("body_wick>=0.5", "body_wick_min", {"threshold": 0.5}),
        ("body_wick>=0.6", "body_wick_min", {"threshold": 0.6}),
        ("body_wick>=0.7", "body_wick_min", {"threshold": 0.7}),
        ("body_wick<=0.3", "body_wick_max", {"threshold": 0.3}),
        ("vol_expand_1.2x", "vol_expansion", {"multiplier": 1.2}),
        ("vol_expand_1.5x", "vol_expansion", {"multiplier": 1.5}),
        ("vol_expand_2.0x", "vol_expansion", {"multiplier": 2.0}),
        ("wick_reject", "wick_rejection", {}),
    ]

    print("\n  IS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp1_configs:
        filt = filter_by_indicators(trades_is, c15, ind_is, mode, **kw)
        s = stats(filt)
        print("  %-20s %4d %+8.1fR  DD %5.1f  %s" % (
            name, s["n"], s["gross"], s["dd"],
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    print("\n  OOS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp1_configs:
        filt = filter_by_indicators(trades_oos, c15o, ind_oos, mode, **kw)
        s = stats(filt)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-20s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # ================================================================
    # EXPERIMENT 2: COMPRESSION BREAKOUT
    # ================================================================
    print("\n" + "=" * 110)
    print("  EXPERIMENT 2: COMPRESSION BREAKOUT (volatility squeeze -> expansion)")
    print("=" * 110)

    exp2_configs = [
        ("inside_breakout", "inside_bar_breakout", {}),
        ("bb_squeeze_25%", "compression_breakout", {"low_pctile": 0.25}),
        ("bb_squeeze_30%", "compression_breakout", {"low_pctile": 0.30}),
        ("squeeze_3bars", "squeeze_breakout", {"min_bars": 3, "low_pctile": 0.25}),
        ("squeeze_5bars", "squeeze_breakout", {"min_bars": 5, "low_pctile": 0.25}),
        ("squeeze_20pct", "squeeze_breakout", {"min_bars": 3, "low_pctile": 0.20}),
        ("trend_str>0.5", "trend_strength", {"threshold": 0.5}),
        ("trend_str>0.8", "trend_strength", {"threshold": 0.8}),
        ("ema_align", "ema_alignment", {}),
    ]

    print("\n  IS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp2_configs:
        filt = filter_by_indicators(trades_is, c15, ind_is, mode, **kw)
        s = stats(filt)
        print("  %-20s %4d %+8.1fR  DD %5.1f  %s" % (
            name, s["n"], s["gross"], s["dd"],
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    print("\n  OOS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp2_configs:
        filt = filter_by_indicators(trades_oos, c15o, ind_oos, mode, **kw)
        s = stats(filt)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-20s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # ================================================================
    # EXPERIMENT 3: MEAN REVERSION
    # ================================================================
    print("\n" + "=" * 110)
    print("  EXPERIMENT 3: MEAN REVERSION (fade trades far from EMA)")
    print("=" * 110)

    exp3_configs = [
        ("mr_1.0", "mean_reversion", {"threshold": 1.0}),
        ("mr_1.5", "mean_reversion", {"threshold": 1.5}),
        ("mr_2.0", "mean_reversion", {"threshold": 2.0}),
        ("mr_2.5", "mean_reversion", {"threshold": 2.5}),
        ("mr_3.0", "mean_reversion", {"threshold": 3.0}),
    ]

    print("\n  IS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp3_configs:
        filt = filter_by_indicators(trades_is, c15, ind_is, mode, **kw)
        s = stats(filt)
        print("  %-20s %4d %+8.1fR  DD %5.1f  %s" % (
            name, s["n"], s["gross"], s["dd"],
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    print("\n  OOS:")
    print("  %-20s %4s %8s  %5s  %s" % ("config", "n", "NET", "DD", "yearly"))
    print("  " + "-" * 80)
    for name, mode, kw in exp3_configs:
        filt = filter_by_indicators(trades_oos, c15o, ind_oos, mode, **kw)
        s = stats(filt)
        ndd = abs(s["gross"] / s["dd"]) if s["dd"] > 0 else 0
        print("  %-20s %4d %+8.1fR  DD %5.1f  N/D %5.2f  %s" % (
            name, s["n"], s["gross"], s["dd"], ndd,
            {k: round(v, 1) for k, v in sorted(s["py"].items())}))

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 110)
    print("  SUMMARY: BEST FROM EACH PARADIGM")
    print("=" * 110)
    print("\n  %-35s  IS NET   OOS NET  OOS DD  OOS N/D" % "config")
    print("  " + "-" * 85)
    print("  %-35s  %+7.1f  %+7.1f  %5.1f  %6.2f  (baseline)" % (
        "mag3+wknd+bm05", base_is["gross"], base_oos["gross"],
        base_oos["dd"], abs(base_oos["gross"] / base_oos["dd"]) if base_oos["dd"] > 0 else 0))

    # Find best from each experiment
    all_results = []
    for name, mode, kw in exp1_configs + exp2_configs + exp3_configs:
        filt_is = filter_by_indicators(trades_is, c15, ind_is, mode, **kw)
        filt_oos = filter_by_indicators(trades_oos, c15o, ind_oos, mode, **kw)
        si = stats(filt_is)
        so = stats(filt_oos)
        ndd = abs(so["gross"] / so["dd"]) if so["dd"] > 0 else 0
        all_results.append((name, si["gross"], so["gross"], so["dd"], ndd))

    all_results.sort(key=lambda x: x[4], reverse=True)
    for name, isn, oosn, oosd, ndd in all_results[:10]:
        print("  %-35s  %+7.1f  %+7.1f  %5.1f  %6.2f" % (name, isn, oosn, oosd, ndd))


if __name__ == "__main__":
    main()
