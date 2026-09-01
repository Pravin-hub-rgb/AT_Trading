"""Test the 1min execution for 27 Aug."""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day, resolve_cfg
from src.config import DATA_DIR
import pandas as pd

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

print(f"=== 5-min bars (27 Aug) ===")
for i, row in day_5m.iterrows():
    if i <= 20:
        print(f"Bar {i}: {str(row['timestamp'])[11:16]} O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")

print(f"\n=== 1-min bars 09:30-10:30 (27 Aug) ===")
for i, row in day_1m.iterrows():
    bar_time = str(row["timestamp"])[11:16]
    if "09:30" <= bar_time <= "10:30":
        print(f"  {bar_time}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")

cfg = resolve_cfg({
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
})

result = simulate_day(
    day_5m, "bearish", cfg, m1_day=day_1m, ctx={"gap": "flat", "extreme": None}
)

print('\n=== Results ===')
print('Date:', result.get('date'))
print('Case:', result.get('case'))
print('Trade mode:', result.get('trade_mode'))
print('Trades:', len(result.get('trades', [])))
for t in result.get('trades', []):
    print(f'  Dir: {t["dir"]}, Entry: {t["entry_time"]} @ {t["entry_price"]}')
    print(f'  SL: {t["sl"]}, mode: {t.get("sl_mode_used")}, pivot_ref: {t.get("pivot_ref")}')
    print(f'  Exit: {t.get("exit_time")} @ {t.get("exit_price")}, outcome: {t.get("outcome")}')

print('\nKey events:')
for ev in result.get("events", []):
    if ev.get('type') in ['pace_break', 'domination', 'day_level_set', 'pending_direct_1m', 'entry', 'exit', 'fs_segment', 'debug_gate', 'first_break_skipped', 'second_swing_armed', 'skipped_same_direction_swing2', 'swing_flip_break', 'skipped_unbiased_1min', 'skipped_end_line']:
        print(f'  {ev}')
