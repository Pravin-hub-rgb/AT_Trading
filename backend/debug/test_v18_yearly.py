"""v18 per-year breakdown — streak halt 5L, the actual production version."""
import sys
from pathlib import Path
from collections import defaultdict
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    c, f = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        f.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return c, f

print("Loading data...")
c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)

print("Running v18 (streak halt 5L)...")
result = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine,
                                      sl_buf_atr=0.25, ext_stop_r=1.5,
                                      mode="b2_vs_flip_chop",
                                      cooldown_bars=20, max_consecutive_losses=5)
trades = result["ltf_trades"]

# Apply costs
_trade_costs(trades, 0.05, 2.0)

# Per-year breakdown
yearly = defaultdict(lambda: {"trades": 0, "gross": 0.0, "net": 0.0, "wins": 0, "losses": 0, "bars": []})

for t in trades:
    if t["outcome"] == "open":
        continue
    year = t.get("exit_date", "")[:4]
    if not year:
        continue
    y = yearly[year]
    y["trades"] += 1
    y["gross"] += t["r_multiple"]
    net = t["r_multiple"] - t.get("cost_r", 0.0)
    y["net"] += net
    if t["r_multiple"] > 0:
        y["wins"] += 1
    else:
        y["losses"] += 1
    y["bars"].append(t.get("bars_held", 0))

print()
print("=" * 80)
print("v18 PER-YEAR BREAKDOWN (streak halt 5L, cooldown 20, costs 0.05%+2pt)")
print("=" * 80)
print(f"{'Year':<8} {'Trades':>8} {'Gross R':>10} {'Net R':>10} {'Win%':>8} {'Avg R':>10} {'Max DD':>10}")
print("-" * 80)

# Also compute per-year max DD
for year in sorted(yearly.keys()):
    y = yearly[year]
    win_pct = 100.0 * y["wins"] / y["trades"] if y["trades"] > 0 else 0
    avg_r = y["net"] / y["trades"] if y["trades"] > 0 else 0
    print(f"{year:<8} {y['trades']:>8} {y['gross']:>10.2f} {y['net']:>10.2f} {win_pct:>7.1f}% {avg_r:>10.3f}")

print()
print("=" * 80)
print("YEARLY MAX DRAWDOWN (within each year)")
print("=" * 80)

for year in sorted(yearly.keys()):
    year_trades = [t for t in trades if t.get("exit_date", "").startswith(year) and t["outcome"] != "open"]
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in year_trades:
        cum += t["r_multiple"] - t.get("cost_r", 0.0)
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    print(f"  {year}: max DD = {max_dd:.2f}R")

print()
print("Total trades:", sum(y["trades"] for y in yearly.values()))
print("Total net:", round(sum(y["net"] for y in yearly.values()), 2), "R")
