"""Trace 09:42-09:55 to find why 2nd entry doesn't fire at 09:49."""
import sys
sys.path.insert(0, ".")
import os
os.chdir(os.path.dirname(__file__) or ".")

from src.walker import WalkerEngine, FlowCandle
from src.intraday import (
    _prep_day, simulate_day, resolve_cfg
)
from src.config import DATA_DIR
import pandas as pd

# Load 1-min data for 2026-08-28
m1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
m1["ts_str"] = m1["timestamp"].astype(str).str[:10]
m1 = m1[m1["ts_str"] == "2026-08-28"].reset_index(drop=True)
m1["timestamp"] = pd.to_datetime(m1["timestamp"])
m1["ts"] = m1["timestamp"].astype("int64") // 10**9

# Run 1-min Walker to find pivots
walker = WalkerEngine()
print("=== WalkerEngine 1-min pivots (full day) ===")
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
print(f"HIGH pivots: {all_highs}")
print(f"LOW pivots: {all_lows}")

# Now iterate 1-min bars from 09:42 to 09:55 and check for breaks
print(f"\n=== 1-min bar walkthrough 09:42-09:55 ===")
print(f"After 09:42 SL hit, next pivot low break should be entry")
print()
# Look at 09:47 low pivot first
for idx in range(len(m1)):
    row = m1.iloc[idx]
    bar_time = str(row["timestamp"])[11:16]
    if not ("09:42" <= bar_time <= "09:55"):
        continue
    low = float(row["low"])
    high = float(row["high"])
    close = float(row["close"])
    # Find pivot low just before this bar
    last_low_piv = None
    for (pidx, ppx, ptime) in all_lows:
        if pidx < idx and (last_low_piv is None or pidx > last_low_piv[0]):
            last_low_piv = (pidx, ppx, ptime)
    last_high_piv = None
    for (pidx, ppx, ptime) in all_highs:
        if pidx < idx and (last_high_piv is None or pidx > last_high_piv[0]):
            last_high_piv = (pidx, ppx, ptime)
    print(f"  Bar {idx} {bar_time}: L={low} H={high} C={close}")
    print(f"    last_low_pivot: idx={last_low_piv[0] if last_low_piv else None} time={last_low_piv[2] if last_low_piv else None} px={last_low_piv[1] if last_low_piv else None}")
    print(f"    last_high_pivot: idx={last_high_piv[0] if last_high_piv else None} time={last_high_piv[2] if last_high_piv else None} px={last_high_piv[1] if last_high_piv else None}")
    # Check break
    if last_low_piv and low < last_low_piv[1]:
        print(f"    >>> SHORT BREAK: low {low} < pivot {last_low_piv[1]}")
    if last_high_piv and high > last_high_piv[1]:
        print(f"    >>> LONG BREAK: high {high} > pivot {last_high_piv[1]}")