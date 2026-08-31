"""Check 1-min chart context at 10:21 to understand what user means by 'FS'."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _classify_first_swing_v2, _prep_day, detect_second_swing
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle as _FC
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

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

c1 = _prep_day(aug28_1)
c5 = _prep_day(aug28_5)

# The 5-min FS end time = 10:15, confirmed at 10:25. The 5-min FS is at bar 14 (10:25).
# But the 10:21 reference doesn't match either of those. Let me look at the 1-min chart in the 10:00-10:30 window.

# 5-min FS info
print("=== 5-min FS ===")
fs5_dir, _, _, fs5_conf, fs5_end_idx, fs5_end_px, fs5_end_time = _classify_first_swing_v2(c5, "2026-08-28")
print(f"  5min FS: dir={fs5_dir} fs_conf={fs5_conf} end_idx={fs5_end_idx} end_time={fs5_end_time}")

# Map 5-min end to 1-min
fs5_end_ts = c5[fs5_end_idx].get("ts", 0)
print(f"  5min end ts: {fs5_end_ts} = {datetime.fromtimestamp(fs5_end_ts, tz=IST)}")

# 5min bar 14 spans 10:25 (so 10:20-10:25)
# 5min bar 13 spans 10:20 (so 10:15-10:20)
# So 5min bar 13's 10:20 timeframe is when the FS was CONFIRMED
# 5min bar 14 is 10:25 (next bar)
# 10:21 falls in 5min bar 13 (10:15-10:20)? No - 10:21 is after 10:20
# Wait: 5min bar 13 = 10:20 means it BEGINS at 10:20
# 5min bar 14 = 10:25 means it BEGINS at 10:25
# So 10:21-10:25 falls in bar 14

# So at 10:21 we are inside the 5min bar 14
# 5min bar 14 (10:25 bar) starts at 10:25 ... no wait
# Let me check
print(f"\n=== 5-min bars 12-15 ===")
for i in range(12, 16):
    c = c5[i]
    print(f"  bar {i} time={c['time']} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}")

# What time is "10:21" in 1-min?
print(f"\n=== 1-min bars 60-72 (10:15 to 10:27) ===")
for i in range(60, 73):
    c = c1[i]
    print(f"  idx={i} time={c['time']} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}")

# Run the 5-min second swing detection
print(f"\n=== 5-min second swing ===")
fs2_dir, fs2_start, fs2_ev, fs2_conf = detect_second_swing(c5, "2026-08-28", fs5_dir, fs5_end_idx, fs5_end_px, fs5_end_time, m1_candles=c1)
print(f"  fs2_dir={fs2_dir} fs2_conf_idx={fs2_conf}")
for ev in fs2_ev:
    if ev.get("type") in ("fs2_segment", "swing2_classified", "fs1_end_map"):
        print(f"  {ev}")
