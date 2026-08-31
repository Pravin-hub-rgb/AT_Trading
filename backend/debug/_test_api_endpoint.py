"""Test the intraday API endpoint for 28 Aug to match what frontend sees."""
import sys
sys.path.insert(0, ".")
import json, hashlib
from src.intraday import simulate_day
from src.config import DATA_DIR
import pandas as pd

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts"] = df5["ts"].astype("int64")
df5 = df5.sort_values("timestamp")
aug28_5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")
aug28_1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

# Test with pivot_break config (same as what user has set)
cfg = {
    "sl": "avg",
    "sl_mult": 1.0,
    "execution": "1min",
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

result = simulate_day(aug28_5, "2026-08-28", cfg, m1_day=aug28_1)

# Print what the API would return
print("=== API Response for 28 Aug ===")
print(f"trades count: {len(result.get('trades', []))}")
print(f"first_swing_confirmed_idx: {result.get('first_swing_confirmed_idx')}")
print(f"swing_direction: {result.get('swing_direction')}")
print(f"swing2_direction: {result.get('swing2_direction')}")
print(f"swing2_confirmed_idx: {result.get('swing2_confirmed_idx')}")

# Find FS-related events
print("\n=== FS-related events ===")
for ev in result.get("events", []):
    t = ev.get("type", "")
    if any(x in t for x in ["swing", "fs_", "FS", "swing_classified", "first_swing"]):
        print(f"  {json.dumps(ev)}")

# Check the algoFirstSwing overlay (what frontend renders as cyan line)
algo_fs = result.get("algoFirstSwing", [])
print(f"\nalgoFirstSwing segments: {len(algo_fs)}")
for seg in algo_fs:
    print(f"  {seg}")

# Also run with pace_break config (original user issue)
print("\n=== With pace_break config ===")
cfg2 = {
    "sl": "avg",
    "sl_mult": 1.0,
    "execution": "1min",
    "entry_method": "pace_break",
    "swing_mode": "opposite_swing_needed",
}
result2 = simulate_day(aug28_5, "2026-08-28", cfg2, m1_day=aug28_1)
print(f"trades count: {len(result2.get('trades', []))}")
for t in result2.get("trades", []):
    print(f"  {t.get('entry_time')} {t.get('dir')} {t.get('outcome')} {t.get('r_multiple')}R")
print(f"first_swing_confirmed_idx: {result2.get('first_swing_confirmed_idx')}")
print(f"swing2_direction: {result2.get('swing2_direction')}")
print(f"swing2_confirmed_idx: {result2.get('swing2_confirmed_idx')}")
