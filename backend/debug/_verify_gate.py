"""Verify the 1-min FS gate mapping for 28-Aug."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.config import DATA_DIR
from src.intraday import _prep_day, _classify_first_swing_v2

# Read 1-min and 5-min data for 28-Aug
df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")

# Filter 2026-08-28
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
m1_day = df1[df1["ts_str"] == "2026-08-28"].reset_index(drop=True)
m5_day = df5[df5["ts_str"] == "2026-08-28"].reset_index(drop=True)

print(f"1-min bars on 2026-08-28: {len(m1_day)}")
print(f"5-min bars on 2026-08-28: {len(m5_day)}")

# Show first 25 1-min bars with timestamps
print("\nFirst 25 1-min bars:")
for i, r in m1_day.head(25).iterrows():
    print(f"  [{i:2d}] {r['timestamp']} O={r['open']} H={r['high']} L={r['low']} C={r['close']}")

# Show first 10 5-min bars
print("\nFirst 10 5-min bars:")
for i, r in m5_day.head(10).iterrows():
    print(f"  [{i:2d}] {r['timestamp']} O={r['open']} H={r['high']} L={r['low']} C={r['close']}")

# Compute 1-min FS
m1_candles = _prep_day(m1_day)
m5_candles = _prep_day(m5_day)

dir1, _, _, conf_idx1, end_idx1, end_px1, end_time1 = _classify_first_swing_v2(m1_candles, "2026-08-28")
print(f"\n1-min FS: dir={dir1} conf_idx={conf_idx1} end_idx={end_idx1} end_time={end_time1} end_px={end_px1}")
print(f"  1-min bar {conf_idx1} time: {m1_candles[conf_idx1]['time']}")
print(f"  1-min bar {end_idx1} time: {m1_candles[end_idx1]['time']}")

# Map to 5-min idx
mts = m1_candles[conf_idx1]["ts"]
print(f"\n  1-min FS confirmed ts: {mts}")
mapped_5 = -1
for k5, c5 in enumerate(m5_candles):
    if c5["ts"] <= mts:
        mapped_5 = k5
    else:
        break
print(f"  Mapped to 5-min bar idx: {mapped_5}")
if mapped_5 >= 0:
    print(f"  5-min bar {mapped_5} time: {m5_candles[mapped_5]['time']}")

# So gate should open at 5-min bar mapped_5, and entries at bar > mapped_5 are allowed
print(f"\n  Gate: entries allowed for bar i > {mapped_5}")
print(f"  -> 09:55 entry at bar 7, gate={mapped_5}: 7 > {mapped_5} = {7 > mapped_5}")
