"""Check 1-min ts values and the m1_end_idx calculation for 5-min bar 4."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import datetime
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["ts"] = df["ts"].astype("int64")
df = df[df["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)

print(f"1-min bars: {len(df)}")
# Show 09:30 to 09:40 range
for i, row in df.iterrows():
    ts = int(row["ts"])
    ist_dt = datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=5, minutes=30)
    tstr = ist_dt.strftime("%H:%M")
    if tstr >= "09:28" and tstr <= "09:40":
        print(f"  [{i}] ts={ts} IST={tstr} | O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")

print()

# 5-min bar 4 ts
bar4_ts = 1787889900
print(f"5-min bar 4 ts = {bar4_ts}")
print(f"  IST = {datetime.datetime.utcfromtimestamp(bar4_ts) + datetime.timedelta(hours=5, minutes=30)}")

# Find m1_end_idx for bar 4
m1_end_idx = -1
for k in range(len(df) - 1, -1, -1):
    if df.iloc[k]["ts"] <= bar4_ts:
        m1_end_idx = k
        break
print(f"m1_end_idx for bar 4 = {m1_end_idx}")
if m1_end_idx >= 0:
    row = df.iloc[m1_end_idx]
    ts = int(row["ts"])
    ist_dt = datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=5, minutes=30)
    print(f"  Last 1-min bar: [{m1_end_idx}] ts={ts} IST={ist_dt.strftime('%H:%M')} | O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")