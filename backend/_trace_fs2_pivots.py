"""Trace which high pivots exist BEFORE bar 36 (09:51)."""
import sys
sys.path.insert(0, ".")

import pandas as pd
from src.config import DATA_DIR
from src.walker import WalkerEngine, FlowCandle

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
aug27 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-27"].reset_index(drop=True)

walker = WalkerEngine()
highs = []
lows = []
for i, r in aug27.iterrows():
    if i > 40:
        break
    fc = FlowCandle(date=r["timestamp"].strftime("%Y-%m-%dT%H:%M:%S"),
                    open=r["open"], high=r["high"], low=r["low"], close=r["close"])
    pivs = walker.process_bar(fc, i)
    for p in pivs:
        if p.kind == "H":
            highs.append(p)
        else:
            lows.append(p)

print("HIGH pivots seen before bar 41:")
for p in highs:
    t = aug27.iloc[p.idx]["timestamp"].strftime("%H:%M")
    print(f"  idx={p.idx} time={t} px={p.px:.2f}")

print("\nLOW pivots seen before bar 41:")
for p in lows:
    t = aug27.iloc[p.idx]["timestamp"].strftime("%H:%M")
    print(f"  idx={p.idx} time={t} px={p.px:.2f}")

print(f"\nFS2 start_idx=22 end_idx=34 end_px=24228.2")
print(f"FS2 internal HIGH pivots (start_idx < idx <= end_idx):")
for p in highs:
    if 22 < p.idx <= 34:
        t = aug27.iloc[p.idx]["timestamp"].strftime("%H:%M")
        print(f"  idx={p.idx} time={t} px={p.px:.2f}")

print(f"\nLOW pivots in (start_idx, end_idx]:")
for p in lows:
    if 22 < p.idx <= 34:
        t = aug27.iloc[p.idx]["timestamp"].strftime("%H:%M")
        print(f"  idx={p.idx} time={t} px={p.px:.2f}")
