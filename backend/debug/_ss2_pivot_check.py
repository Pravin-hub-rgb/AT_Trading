"""Check why 28 Aug 2nd swing is None with pivot_break config."""
import sys
sys.path.insert(0, ".")
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

# Test with pivot_break config
cfg = {
    "sl": "avg",
    "sl_mult": 1.0,
    "execution": "1min",
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

result = simulate_day(aug28_5, "2026-08-28", cfg, m1_day=aug28_1)
print(f"first_swing_confirmed_idx: {result.get('first_swing_confirmed_idx')}")
print(f"swing2_direction: {result.get('swing2_direction')}")
print(f"swing2_confirmed_idx: {result.get('swing2_confirmed_idx')}")

# Show ALL events
print("\n=== All events ===")
for ev in result.get("events", []):
    print(f"  {ev}")

# Try with swing_mode=none
cfg2 = dict(cfg)
cfg2["swing_mode"] = "none"
result2 = simulate_day(aug28_5, "2026-08-28", cfg2, m1_day=aug28_1)
print(f"\n=== swing_mode=none (no 2nd swing filter) ===")
print(f"trades: {len(result2.get('trades', []))}")
for t in result2.get("trades", []):
    print(f"  {t.get('entry_time')} {t.get('dir')} {t.get('outcome')} {t.get('r_multiple')}R")
