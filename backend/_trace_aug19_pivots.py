"""Trace 1-min pivots and breaks for 19 Aug."""
import sys
sys.path.insert(0, ".")
from src.walker import WalkerEngine, FlowCandle
from src.config import DATA_DIR
import pandas as pd

# Load 1-min data for 19 Aug
m1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
m1["ts_str"] = m1["timestamp"].astype(str).str[:10]
m1 = m1[m1["ts_str"] == "2026-08-19"].reset_index(drop=True)
m1["timestamp"] = pd.to_datetime(m1["timestamp"])

# Run WalkerEngine to find pivots
walker = WalkerEngine()
all_highs = []
all_lows = []
for idx, row in m1.iterrows():
    fc = FlowCandle(
        date=str(row["timestamp"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )
    new_p = walker.process_bar(fc, idx)
    for p in new_p:
        if p.kind == "H":
            all_highs.append((idx, p.px, str(row["timestamp"])[11:16]))
        else:
            all_lows.append((idx, p.px, str(row["timestamp"])[11:16]))
walker.finalize()

print("=== 1-min pivots 09:30-10:30 ===")
print("HIGH pivots:")
for h in all_highs:
    if "09:30" <= h[2] <= "10:30":
        print(f"  idx={h[0]} time={h[2]} px={h[1]}")
print("LOW pivots:")
for l in all_lows:
    if "09:30" <= l[2] <= "10:30":
        print(f"  idx={l[0]} time={l[2]} px={l[1]}")

# Check 09:55 break
print("\n=== Check pivot breaks around 09:55 ===")
print("Looking for SHORT breaks (low < prev LOW pivot)")
for idx in range(len(m1)):
    row = m1.iloc[idx]
    bar_time = str(row["timestamp"])[11:16]
    if not ("09:30" <= bar_time <= "10:30"):
        continue
    low = float(row["low"])
    # Find most recent LOW pivot before this bar
    last_low = None
    for (pidx, ppx, ptime) in all_lows:
        if pidx < idx and (last_low is None or pidx > last_low[0]):
            last_low = (pidx, ppx, ptime)
    if last_low and low < last_low[1]:
        print(f"  Bar {idx} {bar_time}: low={low:.2f} BREAKS LOW pivot idx={last_low[0]} time={last_low[2]} px={last_low[1]:.2f}")

# Check first swing confirmation
print("\n=== Check first swing (FsV2) ===")
from src.intraday import simulate_day, resolve_cfg
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-19"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

cfg = resolve_cfg({
    "swing_mode": "opposite_swing_needed",
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
})

result = simulate_day(day_5m, "bearish", cfg, m1_day=m1, ctx={"gap": "flat", "extreme": None})

# Show all swing-related events
for ev in result.get("events", []):
    if "swing" in ev.get("type", "") or "fs_" in ev.get("type", "") or "second_swing" in ev.get("type", ""):
        print(f"  {ev}")