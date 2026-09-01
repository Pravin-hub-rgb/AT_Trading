"""Debug FS2 detection on 27 Aug"""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day, resolve_cfg
import pandas as pd
from src.config import DATA_DIR

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

print("=== All fs2 / second_swing / swing2 events ===")
for ev in result.get("events", []):
    t = ev.get("type", "")
    if "fs2" in t or "second_swing" in t or "swing2" in t:
        print(f"  {ev}")

print()
print(f'swing2_direction: {result.get("swing2_direction")}')
print(f'swing2_confirmed_idx: {result.get("swing2_confirmed_idx")}')
print(f"case: {result.get('case')}")
print(f"trade_mode: {result.get('trade_mode')}")
print(f"# trades: {len(result.get('trades', []))}")

print()
print("=== All pace_break / day_level_set / entry events ===")
for ev in result.get("events", []):
    t = ev.get("type", "")
    if t in ("pace_break", "day_level_set", "entry", "skipped_end_line", "skipped_already_broken"):
        print(f"  {ev}")
