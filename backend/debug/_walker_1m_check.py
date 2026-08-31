"""Debug: trace the 1-min walker pivot_break detection on 28 Aug."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import simulate_day, _prep_day
from src.walker import WalkerEngine, FlowCandle

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts"] = df5["ts"].astype("int64")
df5 = df5.sort_values("timestamp")

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")

aug28_5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()
aug28_1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

print(f"5min bars: {len(aug28_5)}, 1min bars: {len(aug28_1)}")
c5 = _prep_day(aug28_5)
c1 = _prep_day(aug28_1)

# Build walker_1m
walker_1m = WalkerEngine()
normal_lows_1m = []
for idx, mc in enumerate(c1):
    mc_dt = f"2026-08-28T{mc['time']}:00"
    fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
    new_p = walker_1m.process_bar(fc, idx)
    for p in new_p:
        if p.kind == "L":
            normal_lows_1m.append(p)

print(f"\n1-min walker L pivots found: {len(normal_lows_1m)}")
for p in normal_lows_1m[-10:]:
    print(f"  idx={p.idx} px={p.px} time={p.time}")

# Check what happens at bar 14 (10:25) on 5min
bar14 = c5[14]
print(f"\n5min bar 14: time={bar14['time']} ts={bar14['ts']}")
print(f"  open={bar14['open']} high={bar14['high']} low={bar14['low']} close={bar14['close']}")

# Find 1-min bars within this 5min bar's window
print("\n1-min bars inside 5min bar 14 window (ts <= 10:29:59):")
bar14_end_ts = bar14["ts"] + 5 * 60 - 1
for idx in range(len(c1) - 1, -1, -1):
    if c1[idx]["ts"] <= bar14_end_ts:
        mc = c1[idx]
        print(f"  idx={idx} time={mc['time']} ts={mc['ts']} "
              f"open={mc['open']} high={mc['high']} low={mc['low']} close={mc['close']}")
        break

# Check if the 10:25 bar broke below the last 1-min L pivot
if normal_lows_1m:
    last_pivot = normal_lows_1m[-1]
    print(f"\nLast 1-min L pivot: idx={last_pivot.idx} px={last_pivot.px} time={last_pivot.time}")
    # Find the 10:25 bar
    for idx in range(len(c1) - 1, -1, -1):
        if c1[idx]["ts"] <= bar14_end_ts:
            mc = c1[idx]
            broke = mc["close"] < last_pivot.px
            print(f"\n10:25 1-min bar: idx={idx} time={mc['time']} close={mc['close']}")
            print(f"  Break? close={mc['close']} < pivot={last_pivot.px} = {broke}")
            break
else:
    print("\nNO 1-min L pivots found!")
    # Maybe the walker needs to be built incrementally? Check first few bars
    print("\nChecking first 20 1-min bars for context:")
    for idx in range(min(20, len(c1))):
        mc = c1[idx]
        print(f"  idx={idx} time={mc['time']} ts={mc['ts']} low={mc['low']}")
