"""Sweep: count signals where B2/FLIP fires BEFORE previous swing's FS (15m AND 1h).

The issue: in backtesting, _collect_signals() only sees COMPLETED swings.
In live, the open swing's B2/FLIP marks fire before FS (chop cross +
minBars confirmation). These signals can't be reliably traded live
because the swing might FLIP later, invalidating the signal.

This script checks BOTH 15m and 1h timeframes.
"""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")

import argparse
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.btc_engine import _collect_signals, trade_stats
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOLS = {
    "spot": {"symbol": "BTCUSDT", "chop": 61.8, "cd": 20, "slbuf": 0.25, "label": "BTC Spot"},
    "bybit": {"symbol": "BTCUSDT_BYBIT", "chop": 58.0, "cd": 0, "slbuf": 0.20, "label": "Bybit Perp"},
    "binance_perp": {"symbol": "BTCUSDT_PERP", "chop": 61.8, "cd": 5, "slbuf": 0.15, "label": "Binance Perp"},
}


def load_window(tf, symbol):
    df = load_btc_df(tf, symbol)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({
            "date": date, "ts": int(row.ts),
            "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close),
            "volume": 0, "oi": 0,
        })
        flow.append(FlowCandle(
            date=date, open=float(row.open), high=float(row.high),
            low=float(row.low), close=float(row.close),
        ))
    return candles, flow


def analyze_pre_fs(swings, candles, tf_label):
    """Analyze pre-FS signals for a given timeframe."""
    print(f"\n{'='*70}")
    print(f"  ANALYZING {tf_label} SIGNALS")
    print(f"{'='*70}")

    all_signals = _collect_signals(swings, "decisive", skip_first=True,
                                    selection="stream", candles=candles)
    print(f"  Total signals: {len(all_signals)}")

    pre_fs_signals = []
    post_fs_signals = []

    for sig in all_signals:
        sig_bar = sig["bar"]
        sig_swing_no = sig["swing_no"]

        prev_swing = None
        for s in swings:
            if int(s.get("swing_index", -1)) == sig_swing_no - 1:
                prev_swing = s
                break

        if prev_swing is None:
            post_fs_signals.append(sig)
            continue

        prev_fs_idx = int(prev_swing.get("confirmed_at_idx", -1))

        if prev_fs_idx < 0:
            post_fs_signals.append(sig)
            continue

        if sig_bar < prev_fs_idx:
            pre_fs_signals.append({
                **sig,
                "prev_fs_idx": prev_fs_idx,
                "prev_swing_no": prev_swing.get("swing_index", -1),
            })
        else:
            post_fs_signals.append(sig)

    print(f"\n  Signals BEFORE previous swing's FS: {len(pre_fs_signals)}")
    print(f"  Signals AFTER previous swing's FS:  {len(post_fs_signals)}")
    print(f"  Total: {len(pre_fs_signals) + len(post_fs_signals)}")

    if pre_fs_signals:
        print(f"\n  Pre-FS signals (first 10):")
        print(f"  {'Bar':>6} | {'Kind':>5} | {'Dir':>5} | {'Swing':>5} | {'PrevFS':>6} | {'Gap':>4}")
        print(f"  {'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*6}-+-{'-'*4}")
        for s in pre_fs_signals[:10]:
            gap = s["bar"] - s["prev_fs_idx"]
            print(f"  {s['bar']:>6} | {s['kind']:>5} | {s['dir']:>5} | {s['swing_no']:>5} | {s['prev_fs_idx']:>6} | {gap:>+4}")

    return pre_fs_signals, post_fs_signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exchange", default="spot", choices=["spot", "bybit", "binance_perp"])
    args = parser.parse_args()

    cfg = SYMBOLS[args.exchange]
    symbol = cfg["symbol"]

    print("=" * 70)
    print(f"SWEEP: Pre-FS Signal Analysis — {cfg['label']}")
    print(f"Config: chop={cfg['chop']}, cd={cfg['cd']}, slbuf={cfg['slbuf']}")
    print("=" * 70)

    # Load data
    print(f"\n[1] Loading {cfg['label']} data (symbol={symbol})...")
    c1h, f1h = load_window("1h", symbol)
    c15, f15 = load_window("15m", symbol)
    print(f"  1h: {len(c1h)} candles, 15m: {len(c15)} candles")

    # Compute swings
    print("\n[2] Computing swings...")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    print(f"  1h: {len(sw1h)} swings, 15m: {len(sw15)} swings")

    # Load fine 1m data
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=symbol)
    print(f"  1m: {len(fine)} candles")

    # Run v18 backtest (baseline)
    print(f"\n[3] Running v18 backtest (baseline, {cfg['label']})...")
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15,
        fine_ltf=fine,
        sl_buf_atr=cfg["slbuf"], ext_stop_r=1.5,
        mode="b2_vs_flip_chop",
        chop_thresh=cfg["chop"], cooldown_bars=cfg["cd"],
        max_consecutive_losses=5,
    )
    baseline_trades = result["ltf_trades"]
    htf_trades = result.get("htf_trades", [])
    stats_baseline = trade_stats(baseline_trades)
    print(f"  LTF trades: {stats_baseline['trades']}, {stats_baseline['total_r']:+.1f}R, "
          f"PF {stats_baseline.get('profit_factor', 0):.2f}, WR {stats_baseline.get('win_rate', 0):.1f}%")
    print(f"  HTF trades: {len(htf_trades)}")

    # Analyze 15m signals
    pre_fs_15m, post_fs_15m = analyze_pre_fs(sw15, c15, "15m")

    # Analyze 1h signals
    pre_fs_1h, post_fs_1h = analyze_pre_fs(sw1h, c1h, "1h")

    # Match 15m pre-FS signals against LTF trades
    print(f"\n{'='*70}")
    print(f"  IMPACT ON LTF TRADES (15m pre-FS signals)")
    print(f"{'='*70}")

    pre_fs_keys_15m = set()
    for ps in pre_fs_15m:
        pre_fs_keys_15m.add((ps["bar"], ps["kind"], ps["swing_no"]))

    surviving_ltf = []
    removed_ltf = []
    for t in baseline_trades:
        t_bar = t.get("entry_idx", -1)
        t_kind = t.get("break_kind", "")
        t_swing = t.get("swing_no", -1)
        if (t_bar, t_kind, t_swing) in pre_fs_keys_15m:
            removed_ltf.append(t)
        else:
            surviving_ltf.append(t)

    stats_surviving = trade_stats(surviving_ltf)
    stats_removed = trade_stats(removed_ltf) if removed_ltf else None

    print(f"  Baseline:           {len(baseline_trades)} trades, {stats_baseline['total_r']:+.1f}R")
    print(f"  Surviving (post-FS): {len(surviving_ltf)} trades, {stats_surviving['total_r']:+.1f}R")
    if stats_removed:
        print(f"  Removed (pre-FS):    {len(removed_ltf)} trades, {stats_removed['total_r']:+.1f}R")

    # Match 1h pre-FS signals against HTF trades
    print(f"\n{'='*70}")
    print(f"  IMPACT ON HTF TRADES (1h pre-FS signals)")
    print(f"{'='*70}")

    pre_fs_keys_1h = set()
    for ps in pre_fs_1h:
        pre_fs_keys_1h.add((ps["bar"], ps["kind"], ps["swing_no"]))

    if htf_trades:
        surviving_htf = []
        removed_htf = []
        for t in htf_trades:
            t_bar = t.get("entry_idx", -1)
            t_kind = t.get("break_kind", "")
            t_swing = t.get("swing_no", -1)
            if (t_bar, t_kind, t_swing) in pre_fs_keys_1h:
                removed_htf.append(t)
            else:
                surviving_htf.append(t)

        stats_htf_surviving = trade_stats(surviving_htf) if surviving_htf else None
        stats_htf_removed = trade_stats(removed_htf) if removed_htf else None

        print(f"  HTF trades total:   {len(htf_trades)}")
        print(f"  Surviving (post-FS): {len(surviving_htf)}")
        print(f"  Removed (pre-FS):    {len(removed_htf)}")
        if stats_htf_removed:
            print(f"  Removed R: {stats_htf_removed['total_r']:+.1f}")
    else:
        print(f"  No HTF trades to analyze")

    # Summary
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY — {cfg['label']}")
    print(f"{'='*70}")
    print(f"  15m pre-FS signals: {len(pre_fs_15m)} / {len(pre_fs_15m) + len(post_fs_15m)} "
          f"({100*len(pre_fs_15m)/(len(pre_fs_15m) + len(post_fs_15m)):.1f}%)" if (pre_fs_15m or post_fs_15m) else "")
    print(f"  1h pre-FS signals:  {len(pre_fs_1h)} / {len(pre_fs_1h) + len(post_fs_1h)} "
          f"({100*len(pre_fs_1h)/(len(pre_fs_1h) + len(post_fs_1h)):.1f}%)" if (pre_fs_1h or post_fs_1h) else "")
    print(f"  LTF trades removed: {len(removed_ltf)} / {len(baseline_trades)}")
    if stats_removed:
        print(f"  LTF R removed:      {stats_removed['total_r']:+.1f}")
    print(f"  LTF R after filter: {stats_surviving['total_r']:+.1f}")
    print(f"  LTF R improvement:  {stats_surviving['total_r'] - stats_baseline['total_r']:+.1f}")

    print(f"\n{'='*70}")
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
