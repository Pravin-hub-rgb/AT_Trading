"""Show all 1-min L pivots that exist before 10:30 on 28 Aug."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _prep_day
from src.walker import WalkerEngine, FlowCandle

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")

aug28_1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

c1 = _prep_day(aug28_1)
walker_1m = WalkerEngine()
normal_lows_1m = []
normal_highs_1m = []
for idx, mc in enumerate(c1):
    mc_dt = f"2026-08-28T{mc['time']}:00"
    fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
    new_p = walker_1m.process_bar(fc, idx)
    for p in new_p:
        if p.kind == "L":
            normal_lows_1m.append(p)
        else:
            normal_highs_1m.append(p)

print(f"Total 1-min L pivots: {len(normal_lows_1m)}")
print(f"Total 1-min H pivots: {len(normal_highs_1m)}")

# Show first 20 L pivots
print("\nFirst 20 L pivots:")
for p in normal_lows_1m[:20]:
    print(f"  idx={p.idx} px={p.px} time={p.time}")

print("\nL pivots in 09:30 - 10:30 window:")
for p in normal_lows_1m:
    if "10:00" <= p.time <= "10:30":
        print(f"  idx={p.idx} px={p.px} time={p.time}")
