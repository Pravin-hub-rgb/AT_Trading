"""Compare frontend-style walker vs backend walker on 29 May data."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.walker import WalkerEngine as PyWalker, FlowCandle as PyFlowCandle
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
sub = df[df["date"] == pd.Timestamp("2026-05-29").date()].copy().reset_index(drop=True)
sub["time"] = sub["timestamp"].dt.strftime("%H:%M")
walker = PyWalker()
normal_lows = []
normal_highs = []

for i, row in sub.iterrows():
    idx = sub.index.get_loc(i)
    dt_str = f"2026-05-29T{row['time']}:00"
    fc = PyFlowCandle(date=dt_str, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"]))
    pivots = walker.process_bar(fc, idx)
    for p in pivots:
        if p.kind == "H":
            normal_highs.append(p)
        else:
            normal_lows.append(p)

walker.finalize()

print("=== BACKEND walker (walker.py) - LOW pivots ===")
for p in normal_lows[:20]:
    print(f"  [{p.idx:02d}] {p.time} L={p.px:.2f} sealed={p.sealed}")
print(f"  ... total {len(normal_lows)} lows, {len(normal_highs)} highs")

print("\n=== Looking for 9:55 candle ===")
for i, row in sub.iterrows():
    if row["time"] == "09:55":
        print(f"  9:55: H={row['high']} L={row['low']} C={row['close']}")

# Check: does any pivot match 9:55 low?
target_low = 23887.4
print(f"\nPivots near {target_low}:")
for p in normal_lows:
    if abs(p.px - target_low) < 5:
        print(f"  {p.time} idx={p.idx} L={p.px:.2f}")
