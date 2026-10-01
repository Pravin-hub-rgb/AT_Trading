"""Compare: Bybit perp v18 with spot 1m vs bybit 1m fills."""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

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

# Load Bybit perp 15m + 1h
print("Loading Bybit perp data...")
c1h, f1h = load_window("1h", "BTCUSDT_BYBIT")
c15, f15 = load_window("15m", "BTCUSDT_BYBIT")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)

t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])

# Load 1m from BOTH sources
fine_spot = _load_fine_1m(t0, t1, symbol="BTCUSDT")
fine_bybit = _load_fine_1m(t0, t1, symbol="BTCUSDT_BYBIT")
print(f"Spot 1m candles: {len(fine_spot)}")
print(f"Bybit 1m candles: {len(fine_bybit)}")

# Check date range overlap
if fine_spot and fine_bybit:
    spot_first = fine_spot[0]["date"]
    spot_last = fine_spot[-1]["date"]
    bybit_first = fine_bybit[0]["date"]
    bybit_last = fine_bybit[-1]["date"]
    print(f"\nSpot 1m range:  {spot_first} to {spot_last}")
    print(f"Bybit 1m range: {bybit_first} to {bybit_last}")

    # Check if prices differ
    # Find common timestamps
    spot_ts = {c["ts"]: c for c in fine_spot}
    bybit_ts = {c["ts"]: c for c in fine_bybit}
    common = set(spot_ts.keys()) & set(bybit_ts.keys())
    print(f"\nCommon timestamps: {len(common)}")

    if common:
        diffs = []
        for ts in sorted(common)[:100]:  # check first 100
            s = spot_ts[ts]
            b = bybit_ts[ts]
            diff = abs(s["close"] - b["close"])
            diffs.append(diff)
        avg_diff = sum(diffs) / len(diffs)
        max_diff = max(diffs)
        print(f"Avg close price diff: ${avg_diff:.2f}")
        print(f"Max close price diff: ${max_diff:.2f}")

# Run v18 with SPOT 1m (what backend does now - BUG)
print("\n" + "="*60)
print("Running v18 with SPOT 1m fills (current backend behavior)")
print("="*60)
result_spot = simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15,
    fine_ltf=fine_spot,
    sl_buf_atr=0.20, ext_stop_r=1.5,
    mode="b2_vs_flip_chop",
    chop_thresh=58.0, cooldown_bars=0,
    max_consecutive_losses=5,
)
trades_spot = result_spot["ltf_trades"]
closed_spot = [t for t in trades_spot if t["outcome"] != "open"]
rs_spot = [t["r_multiple"] for t in closed_spot]
wins_spot = [r for r in rs_spot if r > 0]
print(f"Trades: {len(trades_spot)}, Closed: {len(closed_spot)}")
print(f"Gross R: {sum(rs_spot):+.1f}")
print(f"Win rate: {len(wins_spot)}/{len(closed_spot)} = {100*len(wins_spot)/len(closed_spot):.1f}%" if closed_spot else "")

# Run v18 with BYBIT 1m (correct)
print("\n" + "="*60)
print("Running v18 with BYBIT 1m fills (correct)")
print("="*60)
result_bybit = simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15,
    fine_ltf=fine_bybit,
    sl_buf_atr=0.20, ext_stop_r=1.5,
    mode="b2_vs_flip_chop",
    chop_thresh=58.0, cooldown_bars=0,
    max_consecutive_losses=5,
)
trades_bybit = result_bybit["ltf_trades"]
closed_bybit = [t for t in trades_bybit if t["outcome"] != "open"]
rs_bybit = [t["r_multiple"] for t in closed_bybit]
wins_bybit = [r for r in rs_bybit if r > 0]
print(f"Trades: {len(trades_bybit)}, Closed: {len(closed_bybit)}")
print(f"Gross R: {sum(rs_bybit):+.1f}")
print(f"Win rate: {len(wins_bybit)}/{len(closed_bybit)} = {100*len(wins_bybit)/len(closed_bybit):.1f}%" if closed_bybit else "")

# Compare
print("\n" + "="*60)
print("COMPARISON")
print("="*60)
print(f"{'':>20} {'Spot 1m (BUG)':>20} {'Bybit 1m (CORRECT)':>20}")
print(f"{'Trades':>20} {len(trades_spot):>20} {len(trades_bybit):>20}")
print(f"{'Gross R':>20} {sum(rs_spot):>+20.1f} {sum(rs_bybit):>+20.1f}")
if closed_spot and closed_bybit:
    print(f"{'Win rate':>20} {100*len(wins_spot)/len(closed_spot):>19.1f}% {100*len(wins_bybit)/len(closed_bybit):>19.1f}%")
print(f"{'R difference':>20} {sum(rs_bybit) - sum(rs_spot):>+20.1f}")

# Check specific trade diffs
print(f"\nTrade-by-trade diff (first 10):")
print(f"{'#':>3} | {'Spot R':>8} | {'Bybit R':>8} | {'Diff':>8} | {'Spot out':>10} | {'Bybit out':>10}")
print(f"{'-'*3}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}")
for i in range(min(10, len(trades_spot), len(trades_bybit))):
    ts = trades_spot[i]
    tb = trades_bybit[i]
    rs = ts.get("r_multiple", 0)
    rb = tb.get("r_multiple", 0)
    print(f"{i+1:>3} | {rs:>+8.2f} | {rb:>+8.2f} | {rb-rs:>+8.2f} | {ts.get('outcome','?'):>10} | {tb.get('outcome','?'):>10}")
