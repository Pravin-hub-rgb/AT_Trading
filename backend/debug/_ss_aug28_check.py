"""Detailed trace of Aug 28 second-swing detection."""
import sys
sys.path.insert(0, '.')

import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG, _prep_day
from src.bias import compute_bias
from src.config import DATA_DIR
from src.swing_engine import FsV2Engine
from src.walker import FlowCandle
from datetime import datetime, timezone, timedelta

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1_path = DATA_DIR / "nifty_1min.csv"
df1 = pd.read_csv(df1_path) if df1_path.exists() else None
if df1 is not None:
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])

daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily_df)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

aug28_str = "2026-08-28"
aug28_5min = df5[(df5["timestamp"].astype(str).str[:10] == aug28_str)].copy()
aug28_1min = df1[(df1["timestamp"].astype(str).str[:10] == aug28_str)].copy() if df1 is not None else None

# Set ts on both (same as run_backtest does now)
aug28_5min["ts"] = (aug28_5min["timestamp"].astype("int64") // 1_000_000_000).astype("int64")
aug28_1min["ts"] = (aug28_1min["timestamp"].astype("int64") // 1_000_000_000).astype("int64")

# Prepare candles
c5 = _prep_day(aug28_5min)
m1 = _prep_day(aug28_1min) if aug28_1min is not None else []

print(f"5min candles: {len(c5)}")
print(f"1min candles: {len(m1)}")
print(f"5min first ts: {c5[0]['ts']} = {datetime.fromtimestamp(c5[0]['ts'], tz=timezone.utc)}")
print(f"5min[15] ts: {c5[15]['ts']} = {datetime.fromtimestamp(c5[15]['ts'], tz=timezone.utc)}, time={c5[15]['time']}")

# Run FsV2 on 5min
IST = timezone(timedelta(hours=5, minutes=30))
flow5 = []
for c in c5:
    dt = datetime.fromtimestamp(c["ts"], tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
    flow5.append(FlowCandle(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"]))

eng5 = FsV2Engine()
for i, fc in enumerate(flow5):
    eng5.process_bar(fc, i)
    if eng5.declared and eng5.dir is not None and i >= 20:  # Let it run past first swing
        pass

print(f"\nFsV2 5min result:")
print(f"  dir={eng5.dir}, confirmed_at_idx={eng5.confirmed_at_idx}, confirmed_at_time={eng5.confirmed_at_time}")
print(f"  end_idx={eng5.end_idx}, end_px={eng5.end_px}, end_time={eng5.end_time}")
print(f"  start_idx={eng5.start_idx}, start_px={eng5.start_px}, start_time={eng5.start_time}")

fs1_end_idx = eng5.confirmed_at_idx
fs1_end_px = eng5.end_px
fs1_end_time = eng5.confirmed_at_time
fs1_end_ts = c5[fs1_end_idx]["ts"]

print(f"\nFirst swing ends at 5min idx={fs1_end_idx}, ts={fs1_end_ts} = {datetime.fromtimestamp(fs1_end_ts, tz=IST)}")

# Find corresponding 1min bar
print(f"\nFinding 1min bar for fs1_end_ts={fs1_end_ts}:")
fs1_end_m1_idx = -1
for k, mc in enumerate(m1):
    if mc["ts"] <= fs1_end_ts:
        fs1_end_m1_idx = k
    else:
        break
print(f"  fs1_end_m1_idx = {fs1_end_m1_idx}")
print(f"  1min[fs1_end_m1_idx] = {m1[fs1_end_m1_idx]['time']} ts={m1[fs1_end_m1_idx]['ts']}")
if fs1_end_m1_idx + 1 < len(m1):
    print(f"  1min[fs1_end_m1_idx+1] = {m1[fs1_end_m1_idx+1]['time']} ts={m1[fs1_end_m1_idx+1]['ts']}")

# Run FsV2 on 1min from fs1 end
post_m1 = m1[fs1_end_m1_idx + 1:]
print(f"\nPost-fs1 1min bars: {len(post_m1)}, first: {post_m1[0]['time'] if post_m1 else 'N/A'}")

flow1 = []
for mc in post_m1:
    dt = datetime.fromtimestamp(mc["ts"], tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
    flow1.append(FlowCandle(date=dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"]))

eng1 = FsV2Engine()
eng1.reset(fs1_end_px, fs1_end_m1_idx, fs1_end_time)

for i, fc in enumerate(flow1):
    g_idx = fs1_end_m1_idx + 1 + i
    eng1.process_bar(fc, g_idx)

print(f"\nFsV2 1min result:")
print(f"  declared={eng1.declared}, dir={eng1.dir}")
print(f"  start_idx={eng1.start_idx}, start_px={eng1.start_px}, start_time={eng1.start_time}")
print(f"  confirmed_at_idx={eng1.confirmed_at_idx}, confirmed_at_time={eng1.confirmed_at_time}")
print(f"  end_idx={eng1.end_idx}, end_px={eng1.end_px}, end_time={eng1.end_time}")

# Map back to 5min
def m1_idx_to_5(idx):
    mts = m1[idx]["ts"]
    for j, c5b in enumerate(c5):
        if c5b["ts"] <= mts:
            return j
    return len(c5) - 1

print(f"\nMapping 1min indices to 5min:")
if eng1.start_idx >= 0:
    print(f"  start: 1min idx={eng1.start_idx} -> 5min idx={m1_idx_to_5(eng1.start_idx)}")
if eng1.confirmed_at_idx >= 0:
    print(f"  confirmed: 1min idx={eng1.confirmed_at_idx} -> 5min idx={m1_idx_to_5(eng1.confirmed_at_idx)}")
if eng1.end_idx >= 0:
    print(f"  end: 1min idx={eng1.end_idx} -> 5min idx={m1_idx_to_5(eng1.end_idx)}")

# Verify by checking times
if eng1.confirmed_at_idx >= 0:
    m1_conf_time = m1[eng1.confirmed_at_idx]["time"]
    m1_conf_ts = m1[eng1.confirmed_at_idx]["ts"]
    mapped_5_idx = m1_idx_to_5(eng1.confirmed_at_idx)
    c5_conf_time = c5[mapped_5_idx]["time"]
    c5_conf_ts = c5[mapped_5_idx]["ts"]
    print(f"\nVerification:")
    print(f"  1min confirmed: {m1_conf_time} ts={m1_conf_ts}")
    print(f"  5min mapped: idx={mapped_5_idx}, time={c5_conf_time} ts={c5_conf_ts}")
    print(f"  Check: is 1min ts >= 5min ts? {m1_conf_ts} >= {c5_conf_ts} = {m1_conf_ts >= c5_conf_ts}")
