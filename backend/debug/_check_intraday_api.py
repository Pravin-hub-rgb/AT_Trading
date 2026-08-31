"""Check what the intraday API returns for 28 Aug."""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day
from src.config import DATA_DIR
import pandas as pd

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

cfg = {
    "sl": "avg", "sl_mult": 1.0,
    "execution": "1min",
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

result = simulate_day(aug28_5, "2026-08-28", cfg, m1_day=aug28_1)

# Print FS-related info
print(f"first_swing_confirmed_idx: {result.get('first_swing_confirmed_idx', 'N/A')}")
print(f"swing_direction: {result.get('swing_direction', 'N/A')}")
print(f"swing2_direction: {result.get('swing2_direction', 'N/A')}")
print(f"swing2_confirmed_idx: {result.get('swing2_confirmed_idx', 'N/A')}")

# Find FS events
for ev in result.get("events", []):
    t = ev.get("type", "")
    if any(x in t for x in ["fs", "swing", "FS", "swing", "first", "second"]):
        print(f"  {ev}")

# Also run FsV2 on 1-min directly
from src.intraday import _classify_first_swing_v2, _prep_day
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle as FC
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
c1 = _prep_day(aug28_1)
fs1_dir, _, fs1_ev, fs1_conf, fs1_end_idx, fs1_end_px, fs1_end_time = _classify_first_swing_v2(c1, "2026-08-28")
print(f"\n1-min FS direct: dir={fs1_dir} conf_idx={fs1_conf} end_idx={fs1_end_idx} end_time={fs1_end_time}")
print(f"  end_px={fs1_end_px}")
print(f"  conf bar time: {c1[fs1_conf]['time'] if fs1_conf >= 0 else 'N/A'}")
