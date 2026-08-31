"""Debug trace: show ALL pending_direct events and what happens to each."""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day, resolve_cfg
from src.config import DATA_DIR
import pandas as pd

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

cfg = resolve_cfg({
    "swing_mode": "opposite_swing_needed",
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
})

result = simulate_day(
    day_5m, "bearish", cfg, m1_day=day_1m, ctx={"gap": "flat", "extreme": None}
)

print("=== ALL events ===")
for i, ev in enumerate(result.get("events", [])):
    print(f"  [{i}] {ev}")

print(f"\n=== Trades ===")
for t in result.get("trades", []):
    print(f"  Entry: {t['entry_time']} @ {t['entry_price']}, SL: {t['sl']}")
    print(f"  Exit: {t.get('exit_time')} @ {t.get('exit_price')}, outcome: {t.get('outcome')}")

print(f"\n=== Pending direct history ===")
pd_events = [e for e in result.get("events", []) if "pending_direct" in e.get("type", "")]
print(f"Total pending_direct events: {len(pd_events)}")
for e in pd_events:
    print(f"  bar={e['bar']} time={e['time']} level={e.get('level')} armed_ts={e.get('armed_ts')}")