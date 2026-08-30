"""Compare 5min vs 1min precision entry on the full labelled dataset."""
import sys
sys.path.insert(0, '.')

import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1_path = DATA_DIR / "nifty_1min.csv"
df1 = pd.read_csv(df1_path) if df1_path.exists() else None
if df1 is not None:
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])

daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily_df)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]
print(f"Data loaded: {len(df5)} 5-min rows, {len(df1) if df1 is not None else 0} 1-min rows, {len(labels)} bias labels")
print()

# 5min baseline
print("=== Execution: 5min (baseline) ===")
cfg5 = dict(DEFAULT_CFG)
cfg5["execution"] = "5min"
r5 = run_backtest(df5, labels, cfg5, df_1min=df1)
s5 = r5["stats"]
print(f"  Trades: {s5['trades']}, WR: {s5['win_rate']:.1f}%, Total R: {s5['total_r']:+.2f}")
print(f"  Outcomes: {s5['outcomes']}")

# 1min precision
print()
print("=== Execution: 1min (precision entry) ===")
cfg1 = dict(DEFAULT_CFG)
cfg1["execution"] = "1min"
r1 = run_backtest(df5, labels, cfg1, df_1min=df1)
s1 = r1["stats"]
print(f"  Trades: {s1['trades']}, WR: {s1['win_rate']:.1f}%, Total R: {s1['total_r']:+.2f}")
print(f"  Outcomes: {s1['outcomes']}")

# Diff
print()
print("=== Diff ===")
print(f"  Trade count: {s5['trades']} → {s1['trades']} (Δ {s1['trades'] - s5['trades']:+d})")
print(f"  Total R: {s5['total_r']:+.2f} → {s1['total_r']:+.2f} (Δ {s1['total_r'] - s5['total_r']:+.2f})")

# Count pending_direct events (how many 1min entries we resolved)
pending_events_1m = sum(
    1 for d in r1["days"] for e in d["events"] if e["type"] == "pending_direct_1m"
)
print(f"  pending_direct_1m events in 1min run: {pending_events_1m}")

# Sample a few 1-min trades to confirm they have 1-min timing
print()
print("=== Sample 5 trades with m1 timing check ===")
sample = []
for d in r1["days"]:
    for t in d["trades"]:
        sample.append((d["date"], t))
sample.sort(key=lambda x: x[0])
for date, t in sample[:5]:
    print(f"  {date}  entry={t['entry_time']}  dir={t['dir']:5s}  px={t['entry_price']:.2f}  sl={t['sl']:.2f}  outcome={t['outcome']:6s}  R={t['r_multiple']:+.2f}")