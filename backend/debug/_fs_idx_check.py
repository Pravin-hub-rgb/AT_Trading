"""Check first-swing FS index in 1-min vs 5-min for 28 Aug."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _classify_first_swing_v2, _prep_day

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

c5 = _prep_day(aug28_5)
c1 = _prep_day(aug28_1)

print("=== 5-min first swing ===")
dir5, start5, ev5, fs5, end5, end5_px, end5_time = _classify_first_swing_v2(c5, "2026-08-28")
print(f"  dir={dir5} fs_confirmed_idx={fs5} end_idx={end5} end_time={end5_time}")

print("\n=== 1-min first swing ===")
dir1, start1, ev1, fs1, end1, end1_px, end1_time = _classify_first_swing_v2(c1, "2026-08-28")
print(f"  dir={dir1} fs_confirmed_idx={fs1} end_idx={end1} end_time={end1_time}")
print(f"  Bar {fs1} 1-min = time {c1[fs1]['time']}")

# Map 1-min FS idx to 5-min idx
fs1_ts = c1[fs1]["ts"]
m5_idx = -1
for j, c5b in enumerate(c5):
    if c5b["ts"] <= fs1_ts:
        m5_idx = j
    else:
        break
print(f"  Mapped to 5-min bar idx: {m5_idx} (bar {m5_idx} spans {c5[m5_idx]['time']})")

# What 5-min bar is the user saying FS is at? They said 10:21.
# 5-min grid: idx 0=09:15, idx 12=10:15, idx 13=10:20, idx 14=10:25
# So 10:21 should be in idx 13 (10:20-10:25)
print(f"\n5-min bar 13: time={c5[13]['time']} ts={c5[13]['ts']}")
print(f"5-min bar 14: time={c5[14]['time']} ts={c5[14]['ts']}")
print(f"5-min bar 12: time={c5[12]['time']} ts={c5[12]['ts']}")
print(f"\n1-min FS at idx {fs1} time {c1[fs1]['time']} ts {c1[fs1]['ts']}")
