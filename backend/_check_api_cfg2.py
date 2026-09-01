"""Test with the API's actual gap (gap-up)."""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day, resolve_cfg
from src.config import DATA_DIR
import pandas as pd

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-27"].reset_index(drop=True)

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)

cfg = resolve_cfg({
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
})

# Let simulate_day compute the gap naturally
result = simulate_day(day_5m, "bearish", cfg, m1_day=day_1m)

print(f"Case: {result.get('case')}")
print(f"Trade mode: {result.get('trade_mode')}")
print(f"Trades: {len(result.get('trades', []))}")
for t in result.get("trades", []):
    print(f"  Trade: {t['dir']} {t['entry_time']} @ {t['entry_price']} SL={t['sl']} exit={t.get('exit_time')} @{t.get('exit_price')} outcome={t.get('outcome')}")

print()
print("Key events:")
for ev in result.get("events", []):
    t = ev.get("type")
    if t in [
        "pace_break", "day_level_set", "pending_direct_1m", "entry", "exit",
        "skipped_end_line", "skipped_gate", "debug_gate", "gate_check",
        "second_swing_armed", "swing_flip_break", "first_break_skipped",
        "skipped_unbiased_1min", "skipped_same_direction_swing2",
        "skipped_already_broken"
    ]:
        print(f"  {ev}")