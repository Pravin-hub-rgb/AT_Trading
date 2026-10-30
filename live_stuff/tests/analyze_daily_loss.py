"""Quick analysis: how many days in book 107 produce >=5R daily loss?

Runs the full backtest chain (IS + OOS) with book 107 params, groups
closed trades by exit day, sums R per day, and counts days
exceeding the 5R daily loss limit.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backtest" / "tests"))

from src.btc.btc_config import IST_OFFSET_SEC, BTC_BYBIT_DATA_DIR, BTC_BYBIT_OOS_DATA_DIR
from src.btc.btc_routes import _load_fine_1m, _trade_costs, _compute_swings
from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle
from engine.v18_params import SWING
import pandas as pd

IST = timezone(__import__("datetime").timedelta(hours=5, minutes=30))


def load_csv(path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({
            "date": date, "ts": int(row.ts),
            "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close),
            "volume": float(getattr(row, "volume", 0.0) or 0.0),
        })
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def main():
    INSTRUMENT = "BTCUSDT_BYBIT"
    is_15m = BTC_BYBIT_DATA_DIR / "BTCUSDT_15m.csv"
    is_1h = BTC_BYBIT_DATA_DIR / "BTCUSDT_1h.csv"
    oos_15m = BTC_BYBIT_OOS_DATA_DIR / "BTCUSDT_15m.csv"
    oos_1h = BTC_BYBIT_OOS_DATA_DIR / "BTCUSDT_1h.csv"

    c15_oos, f15_oos = load_csv(oos_15m)
    c1h_oos, f1h_oos = load_csv(oos_1h)
    c15_is, f15_is = load_csv(is_15m)
    c1h_is, f1h_is = load_csv(is_1h)

    # OOS first chronologically
    c15 = c15_oos + c15_is
    f15 = f15_oos + f15_is
    c1h = c1h_oos + c1h_is
    f1h = f1h_oos + f1h_is

    print(f"Loaded: OOS 15m={len(c15_oos)} 1h={len(c1h_oos)}, IS 15m={len(c15_is)} 1h={len(c1h_is)}")
    print(f"Total: 15m={len(c15)}, 1h={len(c1h)}")
    print(f"  1h range: {c1h[0]['date']} -> {c1h[-1]['date']}")

    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    htf15 = _compute_swings(f1h, "continuous", min_bars=15)
    print(f"Swings: 15m={len(sw15)}, 1h(htf15)={len(htf15)}")

    fine = _load_fine_1m(
        min(c1h[0]["ts"], c15[0]["ts"]),
        max(c1h[-1]["ts"], c15[-1]["ts"]),
        symbol=INSTRUMENT,
    )
    print(f"Fine 1m: {len(fine)} candles")

    # Book 107 params from registry (experiment_registry.py:fsent_champ_long_mcloff_htf15)
    params = {
        "sl_buf_atr": 0.01,
        "atr_high_thresh": 0.65,
        "atr_low_thresh": 0.35,
        "chop_thresh": 58.0,
        "cooldown_bars": 8,
        "max_consecutive_losses": 0,
        "max_positions": 0,
        "ext_stop_r": 3.0,
        "exp_partial_r": 0.0,
        "exp_persist": 7,
        "pivot_rule": "leg",
        "exp_fs_entry_side": "long",
        "mode": "atr_high",
        "htf_rr": 3.0,
        "window_end": "exit",
    }

    print("\nRunning simulate_htf_ltf_streak_halt on full chain (OOS + IS)...")
    r = simulate_htf_ltf_streak_halt(c1h, htf15, c15, sw15, fine_ltf=fine, **params)
    trades = r["ltf_trades"]
    closed = [t for t in trades if t.get("outcome") != "open"]
    print(f"Total trades: {len(trades)}, closed: {len(closed)}")

    # Gross R per day (what the daily loss gate sees — _check_daily_loss_limit uses
    # r_multiple BEFORE cost adjustment, signals.py:568)
    daily_gross = defaultdict(float)
    daily_count = defaultdict(int)
    for t in closed:
        exit_ts = int(t["exit_ts"])
        day = datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        daily_gross[day] += float(t["r_multiple"])
        daily_count[day] += 1

    sorted_days = sorted(daily_gross.keys())
    total_gross = sum(daily_gross.values())
    print(f"\nTotal gross R: {total_gross:+.2f}R across {len(closed)} trades")
    print(f"Total days with closed trades: {len(sorted_days)}")
    print(f"  Range: {sorted_days[0]} -> {sorted_days[-1]}")

    breach_days = [(d, v) for d, v in sorted(daily_gross.items()) if v <= -5.0]
    print(f"\n*** Days with >=5R daily loss: {len(breach_days)} ***")
    if breach_days:
        print("  (worst 20):")
        for d, v in sorted(breach_days, key=lambda x: x[1])[:20]:
            print(f"    {d}: {v:+.2f}R ({daily_count[d]} trades)")

    losses_only = [v for v in daily_gross.values() if v < 0]
    wins_only = [v for v in daily_gross.values() if v > 0]
    if losses_only:
        print(f"\n  Worst day: {min(losses_only):+.2f}R")
        print(f"  Mean loss day: {sum(losses_only)/len(losses_only):+.2f}R")
        print(f"  Total loss days: {len(losses_only)} / {len(sorted_days)}")
    if wins_only:
        print(f"  Best day: {max(wins_only):+.2f}R")
        print(f"  Total win days: {len(wins_only)}")
    print(f"  Avg trades/day: {len(closed)/len(sorted_days):.1f}")

    # Also show distribution near the threshold
    print("\n  Days worse than -2R:")
    for d, v in sorted(daily_gross.items()):
        if -5.0 < v < -2.0:
            print(f"    {d}: {v:+.2f}R ({daily_count[d]} trades)")


if __name__ == "__main__":
    main()
