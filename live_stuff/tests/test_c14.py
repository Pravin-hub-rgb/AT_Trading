"""Test C14 fix: chop regime gate lookahead.

Current: chop_per_ltf[i] = chop[j]     (1h bar CONTAINING the 15m bar - includes future data)
Fix A:   chop_per_ltf[i] = chop[j-1]   (PREVIOUS completed 1h bar - fully known)
Fix B:   check chop at next bar's time  (user's idea - shift entry time)

Tests regime routing accuracy and impact on R.
"""
import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import (
    simulate_htf_ltf_streak_halt, _chop_series_1h, _atr_pct_15m
)
from src.btc.btc_engine import _collect_signals, CandleStore
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"


def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def build_chop_per_ltf(candles_ltf, candles_htf, mode):
    """Build chop mapped to 15m bars with different strategies.

    mode:
      "current" = chop[j]   (1h bar containing 15m bar - has future data)
      "prev"    = chop[j-1] (previous completed 1h bar - fully causal)
      "next"    = chop[j+1] (next 1h bar - even more future data, user's idea test)
    """
    candle_ts_ltf = [int(c["ts"]) for c in candles_ltf]
    candle_ts_htf = [int(c["ts"]) for c in candles_htf]
    chop = _chop_series_1h(candles_htf, lb=14)
    n_ltf = len(candles_ltf)
    chop_per_ltf = [50.0] * n_ltf

    for i, ts in enumerate(candle_ts_ltf):
        j = bisect.bisect_right(candle_ts_htf, ts) - 1
        if mode == "prev":
            j = j - 1
        elif mode == "next":
            j = j + 1
        if 0 <= j < len(chop):
            chop_per_ltf[i] = chop[j]
    return chop_per_ltf


def walk_with_chop(candles_ltf, swings_ltf, intervals_flip, intervals_b2,
                   chop_per_ltf, atr15, sl_buf_atr, cd, halt_n, entry_mode,
                   ext_stop_r=1.5):
    """LTF walk with given chop assignment."""
    n = len(candles_ltf)
    store = CandleStore(candles_ltf)
    candle_ts_ltf = [int(c["ts"]) for c in candles_ltf]

    sigs = _collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)
    starts_flip = [s for s, _, _, _, _ in intervals_flip]
    starts_b2 = [s for s, _, _, _, _ in intervals_b2]

    trades = []
    busy = ""
    last_loss = -999999
    halt_skip = False

    for sig in sigs:
        bar_time = sig["bar"]
        i = store.pos(bar_time)
        if i < 0 or i >= n - 1:
            continue
        if busy and bar_time <= busy:
            continue
        if cd > 0 and i - last_loss < cd:
            continue
        if halt_skip:
            halt_skip = False
            continue

        bar_ts = candle_ts_ltf[i]
        direction = int(sig["dir"])

        # Regime routing using the provided chop
        ch = chop_per_ltf[i]
        use = "b2" if ch > 58.0 else "flip"

        if use == "flip":
            ivs, sts = intervals_flip, starts_flip
        else:
            ivs, sts = intervals_b2, starts_b2

        if not ivs:
            continue
        idx = bisect.bisect_right(sts, bar_ts) - 1
        if idx < 0:
            continue
        s, e, d, pe, psl = ivs[idx]
        if not (s < bar_ts <= e):
            continue
        if direction != d:
            continue

        # ext_stop_r check (same as v18:184-188: uses HTF risk, not LTF risk)
        if ext_stop_r > 0:
            hrisk = abs(pe - psl)
            if hrisk > 0:
                ext = (float(candles_ltf[i]["close"]) - pe) * d / hrisk
                if ext > ext_stop_r:
                    continue

        if entry_mode == "next_open" and i + 1 < n:
            entry = float(candles_ltf[i + 1]["open"])
        else:
            entry = float(candles_ltf[i]["close"])

        sl_pivot = sig["swing_start_px"]
        if direction == 1:
            sl = sl_pivot - sl_buf_atr * atr15[i] if sl_buf_atr > 0 else sl_pivot
            if sl >= entry:
                continue
            risk = entry - sl
            if risk < 0.0005 * entry:
                continue
        else:
            sl = sl_pivot + sl_buf_atr * atr15[i] if sl_buf_atr > 0 else sl_pivot
            if sl <= entry:
                continue
            risk = sl - entry
            if risk < 0.0005 * entry:
                continue

        sl0 = sl
        sl_cur = sl

        want_dir = "up" if direction == 1 else "down"
        events = []
        for s_w in swings_ltf:
            if s_w.get("dir") != want_dir:
                continue
            ct = s_w.get("confirmed_at_time", "")
            if not ct:
                continue
            cidx = store.pos(ct)
            if cidx >= 0:
                events.append((cidx, float(s_w["seg"]["start_px"])))
        events.sort(key=lambda x: x[0])
        ev_idx = -1

        exit_idx = None
        exit_px = None
        outcome = "open"

        for j in range(i + 1, n):
            c = candles_ltf[j]
            hi = float(c["high"])
            lo = float(c["low"])
            if direction == 1:
                if lo <= sl_cur:
                    fill = min(sl_cur, float(c["open"]))
                    exit_idx, exit_px = j, fill
                    outcome = "sl" if sl_cur <= sl0 else "trail"
                    break
                while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                    ev_idx += 1
                    if events[ev_idx][0] < i:
                        continue
                    cand = events[ev_idx][1]
                    if sl_cur < cand < hi:
                        sl_cur = cand
            else:
                if hi >= sl_cur:
                    fill = max(sl_cur, float(c["open"]))
                    exit_idx, exit_px = j, fill
                    outcome = "sl" if sl_cur >= sl0 else "trail"
                    break
                while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                    ev_idx += 1
                    if events[ev_idx][0] < i:
                        continue
                    cand = events[ev_idx][1]
                    if hi < cand < sl_cur:
                        sl_cur = cand

        if exit_idx is None:
            exit_idx = n - 1
            exit_px = float(candles_ltf[-1]["close"])
            outcome = "open"

        r_multiple = (exit_px - entry) * direction / risk

        trades.append({
            "entry_date": candles_ltf[i]["date"],
            "entry_ts": int(candles_ltf[i]["ts"]),
            "exit_date": candles_ltf[exit_idx]["date"],
            "exit_ts": int(candles_ltf[exit_idx]["ts"]),
            "dir": "long" if direction == 1 else "short",
            "entry_price": round(entry, 2),
            "sl": round(sl0, 2),
            "exit_price": round(float(exit_px), 2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple), 3),
            "bars_held": exit_idx - i,
        })
        busy = candles_ltf[exit_idx]["date"]
        if cd > 0 and r_multiple < 0:
            last_loss = exit_idx

    return trades


def pr(label, trades):
    if not trades:
        print("  %-40s 0t" % label)
        return 0
    g = sum(t["r_multiple"] for t in trades)
    w = sum(1 for t in trades if t["r_multiple"] > 0)
    wr = 100 * w / len(trades)
    pos = sum(t["r_multiple"] for t in trades if t["r_multiple"] > 0)
    neg = abs(sum(t["r_multiple"] for t in trades if t["r_multiple"] < 0))
    pf = pos / neg if neg else 999
    print("  %-40s %3dt  %+7.1fR  WR %5.1f%%  PF %.2f" % (label, len(trades), g, wr, pf))
    return g


if __name__ == "__main__":
    print("Loading...")
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    atr15 = _atr_pct_15m(c15)

    # Baseline via v18
    r = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, c15, fine_ltf=[],
        sl_buf_atr=0.01, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        chop_thresh=58.0, cooldown_bars=10, max_consecutive_losses=3)
    htf_flip = r["htf_trades"]
    htf_b2 = r["htf_trades_b2"]
    base_ltf = r["ltf_trades"]

    # Build intervals
    def make_iv(htf_trades):
        out = []
        for t in htf_trades:
            if t["outcome"] == "open":
                continue
            d = 1 if t["dir"] == "long" else -1
            out.append((int(t["entry_ts"]), int(t["exit_ts"]), d,
                        float(t["entry_price"]), float(t["sl"])))
        out.sort(key=lambda x: x[0])
        return out

    iv_flip = make_iv(htf_flip)
    iv_b2 = make_iv(htf_b2)

    print("Intervals: flip=%d  b2=%d" % (len(iv_flip), len(iv_b2)))

    # Show how many signals get different regime under each chop mode
    chop_current = build_chop_per_ltf(c15, c1h, "current")
    chop_prev = build_chop_per_ltf(c15, c1h, "prev")

    store15 = CandleStore(c15)
    sigs = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
    candle_ts_ltf = [int(c["ts"]) for c in c15]

    changed = 0
    for sig in sigs:
        i = store15.pos(sig["bar"])
        if i < 0 or i >= len(c15):
            continue
        r_c = "b2" if chop_current[i] > 58.0 else "flip"
        r_p = "b2" if chop_prev[i] > 58.0 else "flip"
        if r_c != r_p:
            changed += 1

    print("\nRegime changes (current vs prev): %d signals out of %d" % (changed, len(sigs)))

    # Runs
    print("\nRunning walks...")
    w_current = walk_with_chop(c15, sw15, iv_flip, iv_b2, chop_current, atr15, 0.01, 10, 3, "close")
    w_prev = walk_with_chop(c15, sw15, iv_flip, iv_b2, chop_prev, atr15, 0.01, 10, 3, "close")

    print("\n" + "=" * 70)
    print("C14 TEST: chop regime gate lookahead")
    print("=" * 70)
    g0 = pr("v18 baseline (chop[j], retro)", base_ltf)
    g1 = pr("chop[j] (manual walk, should match v18)", w_current)
    g2 = pr("chop[j-1] (C14 fix - previous completed 1h bar)", w_prev)

    print("\n--- Delta ---")
    print("  C14 fix (j-1 vs j):  %+.1fR  (%+d trades)" % (g2 - g1, len(w_prev) - len(w_current)))

    # Per-year
    print("\n--- Per-year ---")
    for yr in ["2023", "2024", "2025", "2026"]:
        for lab, tr in [("chop[j]", w_current), ("chop[j-1]", w_prev)]:
            yt = [t for t in tr if t["entry_date"][:4] == yr]
            yr_sum = sum(t["r_multiple"] for t in yt)
            print("  %s %-12s %3dt %+7.1fR" % (yr, lab, len(yt), yr_sum))
        print()
