"""Run v18 backtest on Bybit BTCUSDT perp data (data/bybit/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
BYBIT_DIR = Path(__file__).resolve().parents[2] / "data" / "bybit"


def load_bybit(tf: str):
    path = BYBIT_DIR / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    print(f"  {tf}: {len(df)} rows, {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}")
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


print("Loading Bybit data...")
c1h, f1h = load_bybit("1h")
c15, f15 = load_bybit("15m")

print("\nComputing swings...")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
print(f"  1h swings: {len(sw1h)}")
print(f"  15m swings: {len(sw15)}")

# Bybit doesn't have 1m data — run without fine fills
print("\nRunning v18 simulation (no 1m fine fills — Bybit has no 1m data)...")
trades = simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15, fine_ltf=None,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5
)["ltf_trades"]

# Analysis
rs = [t["r_multiple"] for t in trades]
n = len(trades)
tot = sum(rs)
wins = [r for r in rs if r > 0]
losses = [r for r in rs if r <= 0]
wr = 100 * len(wins) / n if n else 0
pf = sum(wins) / abs(sum(losses)) if losses else float("inf")

eq = peak = dd = 0.0
for r in rs:
    eq += r
    peak = max(peak, eq)
    dd = max(dd, peak - eq)

years = {}
for t in trades:
    y = t["entry_date"][:4]
    years.setdefault(y, [0, 0.0])
    years[y][0] += 1
    years[y][1] += t["r_multiple"]

print("\n" + "=" * 72)
print("BYBIT BTCUSDT PERP — v18 BACKTEST RESULTS")
print("=" * 72)
print(f"  trades: {n}")
print(f"  total R: {tot:+.1f}")
print(f"  win rate: {wr:.1f}% ({len(wins)}W/{len(losses)}L)")
print(f"  PF: {pf:.2f}")
print(f"  max DD: {dd:.1f}R  net/DD: {tot/dd:.1f}" if dd else "  max DD: 0R")
print()
print("Yearly breakdown:")
for y, v in sorted(years.items()):
    print(f"  {y}: {v[0]}t {v[1]:+.1f}R")
print()
all_pos = all(v[1] > 0 for v in years.values())
print(f"All years positive: {'YES' if all_pos else 'NO'}")

# Cost-adjusted (0.05%/side fee + 2pts slippage)
fee_pct = 0.05
slippage_pts = 2
costs = []
for t in trades:
    risk = abs(t["entry_price"] - t["sl"])
    fee_r = (t["entry_price"] * fee_pct / 100 * 2) / risk if risk > 0 else 0
    slip_r = (slippage_pts * 2) / risk if risk > 0 else 0
    costs.append(fee_r + slip_r)
net_r = tot - sum(costs)
print(f"\nGross R:  {tot:+.1f}")
print(f"Costs R:  {sum(costs):.1f}")
print(f"Net R:    {net_r:+.1f}")
print()
print("Comparison:")
print(f"  Binance Spot:   331t +286R net")
print(f"  Binance Perp:   320t +218R net")
print(f"  Bybit Perp:     {n}t {net_r:+.1f}R net")
