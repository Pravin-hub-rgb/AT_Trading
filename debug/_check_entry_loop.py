"""Trace what happens at 5-min bar 8 (09:55) and 9 (10:00)"""
import sys
sys.path.insert(0, ".")
import pandas as pd
from src.config import DATA_DIR
from src.intraday import _prep_day, simulate_day, resolve_cfg
from src.walker import WalkerEngine, FlowCandle

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

cfg = resolve_cfg({"entry_method": "pivot_break", "execution": "1min", "sl_mode": "prev_pivot", "sl_pivot_buffer": 1.0})
result = simulate_day(day_5m, "bearish", cfg, m1_day=day_1m, ctx={"gap": "flat", "extreme": None})

# Find all entry-related events with time before 10:10
print("Events with time <= 10:10:")
for ev in result.get("events", []):
    t = ev.get("time", "")
    if t <= "10:10" and ev.get("type") in ("pace_break", "day_level_set", "skipped_end_line", "skipped_already_broken", "second_swing_armed", "fs2_segment", "pending_direct_1m", "entry"):
        print(f"  {ev}")
