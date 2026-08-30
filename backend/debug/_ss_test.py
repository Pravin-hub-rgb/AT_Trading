"""Test second-swing alignment logic — 3 scenarios."""
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

# 1) 5min baseline (unchanged)
print("=== 1) 5min baseline (swing_mode=none) ===")
cfg = dict(DEFAULT_CFG); cfg["execution"] = "5min"; cfg["swing_mode"] = "none"
r = run_backtest(df5, labels, cfg, df_1min=df1); s = r["stats"]
print(f"  Trades: {s['trades']}, WR: {s['win_rate']:.1f}%, Total R: {s['total_r']:+.2f}")
trades_5min = s['trades']
r_5min = s['total_r']

# 2) 1min with no second-swing gate (swing_mode=none)
print()
print("=== 2) 1min, swing_mode=none (current 1min behavior) ===")
cfg = dict(DEFAULT_CFG); cfg["execution"] = "1min"; cfg["swing_mode"] = "none"
r = run_backtest(df5, labels, cfg, df_1min=df1); s = r["stats"]
print(f"  Trades: {s['trades']}, WR: {s['win_rate']:.1f}%, Total R: {s['total_r']:+.2f}")
trades_1min_none = s['trades']
r_1min_none = s['total_r']

# 3) 1min with opposite_swing_needed (NEW)
print()
print("=== 3) 1min, swing_mode=opposite_swing_needed (NEW alignment rule) ===")
cfg = dict(DEFAULT_CFG); cfg["execution"] = "1min"; cfg["swing_mode"] = "opposite_swing_needed"
r = run_backtest(df5, labels, cfg, df_1min=df1); s = r["stats"]
print(f"  Trades: {s['trades']}, WR: {s['win_rate']:.1f}%, Total R: {s['total_r']:+.2f}")
trades_1min_aligned = s['trades']
r_1min_aligned = s['total_r']

# Event counts
print()
print("=== Event counts (1min, opposite_swing_needed) ===")
fs2_seg = 0; fs2_armed = 0; fs2_skip = 0
for d in r["days"]:
    for e in d["events"]:
        if e["type"] == "fs2_segment": fs2_seg += 1
        if e["type"] == "second_swing_armed": fs2_armed += 1
        if e["type"] == "skipped_same_direction_swing2": fs2_skip += 1
print(f"  fs2_segment events:        {fs2_seg}")
print(f"  second_swing_armed events: {fs2_armed}")
print(f"  skipped_same_direction_swing2 events: {fs2_skip}")

# 4) 1min with pivot_break + opposite_swing_needed (NEW entry method)
print()
print("=== 4) 1min, pivot_break + opposite_swing_needed (NEW entry method) ===")
cfg = dict(DEFAULT_CFG); cfg["execution"] = "1min"; cfg["entry_method"] = "pivot_break"; cfg["swing_mode"] = "opposite_swing_needed"
r = run_backtest(df5, labels, cfg, df_1min=df1); s = r["stats"]
print(f"  Trades: {s['trades']}, WR: {s['win_rate']:.1f}%, Total R: {s['total_r']:+.2f}")
trades_1min_pivot = s['trades']
r_1min_pivot = s['total_r']

# Summary
print()
print("=== Summary ===")
print(f"  5min baseline:                     {trades_5min:4d} trades, R={r_5min:+.2f}")
print(f"  1min (no second-swing gate):      {trades_1min_none:4d} trades, R={r_1min_none:+.2f}")
print(f"  1min (opposite swing needed):     {trades_1min_aligned:4d} trades, R={r_1min_aligned:+.2f}")
print(f"  1min (pivot_break+aligned):       {trades_1min_pivot:4d} trades, R={r_1min_pivot:+.2f}")
print(f"  Delta vs 1min baseline: trades {trades_1min_aligned - trades_1min_none:+d}, R {r_1min_aligned - r_1min_none:+.2f}")
