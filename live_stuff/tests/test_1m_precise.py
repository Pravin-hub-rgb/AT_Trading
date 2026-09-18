"""Test: 1m-precise HTF intervals + next-bar entry. FIXED version with regime routing.

Two experiments:
  A) 1m-precise breach detection — HTF window starts at exact 1m breach bar
  B) Next-bar entry — enter at open of next 15m bar instead of close of signal bar

Regime routing: chop > 58.0 → b2 intervals, else flip intervals (same as v18).
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


def find_1m_breach(break_ts_1h, break_level, direction, candle_ts_1m, candles_1m):
    """Find exact 1m bar where extreme was breached within the 1h bar."""
    h1_end = break_ts_1h + 3600
    start_k = bisect.bisect_left(candle_ts_1m, break_ts_1h)
    for k in range(start_k, len(candle_ts_1m)):
        if candle_ts_1m[k] >= h1_end:
            break
        hi = float(candles_1m[k]["high"])
        lo = float(candles_1m[k]["low"])
        if direction == 1 and hi >= break_level:
            return candle_ts_1m[k], float(candles_1m[k]["close"])
        if direction == -1 and lo <= break_level:
            return candle_ts_1m[k], float(candles_1m[k]["close"])
    return None, None


def make_intervals(htf_trades, candles_1m, candle_ts_1m, precise=False):
    """Build interval list from HTF trades."""
    out = []
    for t in htf_trades:
        if t["outcome"] == "open":
            continue
        d = 1 if t["dir"] == "long" else -1
        exit_ts = int(t["exit_ts"])
        if precise:
            b_ts, b_close = find_1m_breach(
                int(t["entry_ts"]), float(t["entry_price"]), d, candle_ts_1m, candles_1m)
            if b_ts is not None:
                out.append((b_ts, exit_ts, d, b_close, float(t["sl"])))
            else:
                out.append((int(t["entry_ts"]), exit_ts, d, float(t["entry_price"]), float(t["sl"])))
        else:
            out.append((int(t["entry_ts"]), exit_ts, d, float(t["entry_price"]), float(t["sl"])))
    out.sort(key=lambda x: x[0])
    return out


def walk_v18_style(candles_ltf, swings_ltf, intervals_flip, intervals_b2,
                   candles_htf, atr15, sl_buf_atr, cd, halt_n,
                   chop_thresh, entry_mode):
    """LTF walk with v18's exact regime routing logic."""
    n = len(candles_ltf)
    store = CandleStore(candles_ltf)

    # Regime series (same as v18)
    chop = _chop_series_1h(candles_htf, lb=14)
    candle_ts_ltf = [int(c["ts"]) for c in candles_ltf]
    candle_ts_htf = [int(c["ts"]) for c in candles_htf]
    chop_per_ltf = [50.0] * n
    for i, ts in enumerate(candle_ts_ltf):
        j = bisect.bisect_right(candle_ts_htf, ts) - 1
        if 0 <= j < len(chop):
            chop_per_ltf[i] = chop[j]

    # Signals: decisive (both B2+FLIP) — same as v18
    sigs = _collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)

    # Build interval lookups
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

        # Regime routing (same as v18:163-165)
        ch = chop_per_ltf[i] if i < len(chop_per_ltf) else 50.0
        use = "b2" if ch > chop_thresh else "flip"

        if use == "flip":
            intervals, starts = intervals_flip, starts_flip
        else:
            intervals, starts = intervals_b2, starts_b2

        if not intervals:
            continue

        idx = bisect.bisect_right(starts, bar_ts) - 1
        if idx < 0:
            continue
        s, e, d, pe, psl = intervals[idx]
        if not (s < bar_ts <= e):
            continue
        if direction != d:
            continue

        # Entry
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

        # Trail events
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
        print("  %-35s 0t" % label)
        return 0
    g = sum(t["r_multiple"] for t in trades)
    w = sum(1 for t in trades if t["r_multiple"] > 0)
    wr = 100 * w / len(trades)
    pos = sum(t["r_multiple"] for t in trades if t["r_multiple"] > 0)
    neg = abs(sum(t["r_multiple"] for t in trades if t["r_multiple"] < 0))
    pf = pos / neg if neg else 999
    print("  %-35s %3dt  %+7.1fR  WR %5.1f%%  PF %.2f" % (label, len(trades), g, wr, pf))
    return g


if __name__ == "__main__":
    print("Loading...")
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    c1m, f1m = load_window("1m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    atr15 = _atr_pct_15m(c15)
    candle_ts_1m = [int(c["ts"]) for c in c1m]

    print("1h=%d 15m=%d 1m=%d  sw1h=%d sw15=%d" % (len(c1h), len(c15), len(c1m), len(sw1h), len(sw15)))

    # Baseline via v18
    r = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=[],
        sl_buf_atr=0.01, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        chop_thresh=58.0, cooldown_bars=10, max_consecutive_losses=3)
    htf_flip = r["htf_trades"]
    htf_b2 = r["htf_trades_b2"]
    base_ltf = r["ltf_trades"]

    # Build intervals (retro and precise)
    retro_flip = make_intervals(htf_flip, c1m, candle_ts_1m, precise=False)
    retro_b2 = make_intervals(htf_b2, c1m, candle_ts_1m, precise=False)
    precise_flip = make_intervals(htf_flip, c1m, candle_ts_1m, precise=True)
    precise_b2 = make_intervals(htf_b2, c1m, candle_ts_1m, precise=True)

    print("\nIntervals: retro flip=%d b2=%d | precise flip=%d b2=%d" % (
        len(retro_flip), len(retro_b2), len(precise_flip), len(precise_b2)))

    # Shift stats
    min_len = min(len(retro_flip), len(precise_flip))
    shifts = [precise_flip[k][0] - retro_flip[k][0] for k in range(min_len)]
    if shifts:
        print("1h->1m shift: median=%ds  mean=%ds  max=%ds" % (
            sorted(shifts)[len(shifts)//2], sum(shifts)//len(shifts), max(shifts)))

    CHOP = 58.0

    print("\nRunning walks with regime routing...")
    w_b = walk_v18_style(c15, sw15, retro_flip, retro_b2, c1h, atr15, 0.01, 10, 3, CHOP, "close")
    w_c = walk_v18_style(c15, sw15, precise_flip, precise_b2, c1h, atr15, 0.01, 10, 3, CHOP, "close")
    w_d = walk_v18_style(c15, sw15, retro_flip, retro_b2, c1h, atr15, 0.01, 10, 3, CHOP, "next_open")
    w_e = walk_v18_style(c15, sw15, precise_flip, precise_b2, c1h, atr15, 0.01, 10, 3, CHOP, "next_open")

    print("\n" + "=" * 70)
    print("RESULTS (with regime routing -- chop > 58 -> b2, else flip)")
    print("=" * 70)
    g0 = pr("v18 baseline (retro, close)", base_ltf)
    g1 = pr("retro walk (manual, regime-routed)", w_b)
    g2 = pr("1m-precise, close", w_c)
    g3 = pr("retro, next_open", w_d)
    g4 = pr("1m-precise, next_open", w_e)

    print("\n--- Deltas vs v18 baseline ---")
    print("  retro walk vs v18:        %+.1fR  (%+d trades)" % (g1 - g0, len(w_b) - len(base_ltf)))
    print("  1m-precise vs retro walk: %+.1fR  (%+d trades)" % (g2 - g1, len(w_c) - len(w_b)))
    print("  next_open vs retro walk:  %+.1fR  (%+d trades)" % (g3 - g1, len(w_d) - len(w_b)))
    print("  both vs retro walk:       %+.1fR  (%+d trades)" % (g4 - g1, len(w_e) - len(w_b)))

    # Per-year
    print("\n--- Per-year ---")
    for yr in ["2023", "2024", "2025", "2026"]:
        for lab, tr in [("v18", base_ltf), ("retro-walk", w_b),
                        ("precise", w_c), ("next_open", w_d), ("both", w_e)]:
            yt = [t for t in tr if t["entry_date"][:4] == yr]
            yr_sum = sum(t["r_multiple"] for t in yt)
            print("  %s %-12s %3dt %+7.1fR" % (yr, lab, len(yt), yr_sum))
        print()
