"""Monkey-patch intraday.simulate_day's entry loop to log per-bar state for 28-Aug."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.config import DATA_DIR
import src.intraday as idm

# Read CSV and load as DataFrames
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts"] = df5["ts"].astype("int64")
df5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)

cfg = {
    "sl_mode": "avg",
    "execution": "1min",
    "trailing": "off",
    "trail_distance_r": 1.0,
    "gap_pct": 0.0027,
    "sl_pivot_buffer": 1.0,
    "ft_fail_enabled": True,
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

ctx = {"gap": "flat", "extreme": None, "avg_range": 50.0}
result = idm.simulate_day(df5, "bearish", cfg, m1_day=df1, ctx=ctx)

# Show ALL events for bars 0-15
print("\n=== ALL EVENTS (bars 0-15) ===")
for ev in result.get("events", []):
    bar = ev.get("bar", -1)
    if bar >= 0 and bar <= 15:
        t = ev.get("type", "")
        time = ev.get("time", "")
        print(f"  [{bar}] {time} | {t} | {ev}")

print("\n=== TRADES ===")
for t in result.get("trades", []):
    print(f"  {t.get('entry_time', 'N/A')} | {t.get('dir')} | outcome={t.get('outcome')} | entry_bar={t.get('entry_bar')}")

print(f"\n1-min FS confirmed_idx_5min: {result.get('fs1_1min_confirmed_idx_5min')}")
print(f"First swing end time: {result.get('first_swing_end_time')}")
print(f"Case: {result.get('case')}")
print(f"Swing direction: {result.get('swing_direction')}")
print(f"First swing confirmed idx: {result.get('first_swing_confirmed_idx')}")