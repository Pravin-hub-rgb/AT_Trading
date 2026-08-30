"""Diagnostic: how often does FirstSwingEngine declare, per day?"""
import sys
backend_dir = sys.argv[1]
sys.path.insert(0, backend_dir)
import pandas as pd
from src.intraday import _prep_day, _classify_first_swing_v2
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

declared = 0
none = 0
by_dir = {}
for d, sub in df.groupby("date"):
    candles = _prep_day(sub)
    if len(candles) < 20:
        continue
    swing_dir, swing_start, ev = _classify_first_swing_v2(candles, str(d))
    if swing_dir is None:
        none += 1
    else:
        declared += 1
        by_dir[swing_dir] = by_dir.get(swing_dir, 0) + 1

print(f"declared={declared}  no_swing={none}  buying={by_dir.get('buying',0)} selling={by_dir.get('selling',0)}")
