"""Debug WalkerEngine pivot tracking on 29 May 2026."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import _prep_day, simulate_day, _classify_first_swing_v2, DEFAULT_CFG, FALLBACK_AVG_RANGE
from src.walker import WalkerEngine, FlowCandle
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

target = pd.Timestamp("2026-05-29").date()
sub = df[df["date"] == target].copy()

candles = _prep_day(sub)
print(f"Total 5min candles: {len(candles)}")

# Build FlowCandles and walk through with WalkerEngine
walker = WalkerEngine()
normal_lows = []
normal_highs = []

for i, c in enumerate(candles):
    fc = FlowCandle(
        date=f"2026-05-29T{c['time']}:00",
        open=float(c["open"]),
        high=float(c["high"]),
        low=float(c["low"]),
        close=float(c["close"]),
    )
    pivots = walker.process_bar(fc, i)
    for p in pivots:
        print(f"  [{i:02d}] {c['time']} {p.kind}={p.px:.2f} sealed={p.sealed}")
        for p in pivots:
            if p.kind == "H":
                normal_highs.append(p)
            elif p.kind == "L":
                normal_lows.append(p)

walker.finalize()
print(f"\nSummary: {len(normal_highs)} HIGH pivots, {len(normal_lows)} LOW pivots")
print("\nHIGH pivots:")
for p in normal_highs:
    print(f"  {p.time} idx={p.g_idx} px={p.px:.2f}")
print("\nLOW pivots:")
for p in normal_lows:
    print(f"  {p.time} idx={p.g_idx} px={p.px:.2f}")

# Also check the 9:55 candle
nine55 = [c for c in candles if c["time"] == "09:55"]
if nine55:
    print(f"\n9:55 candle: high={nine55[0]['high']} low={nine55[0]['low']} close={nine55[0]['close']}")

# What did the walker's last sealed normal_lows contain?
print(f"\nLast 5 normal_lows: {[(p.time, p.px) for p in normal_lows[-5:]]}")
print(f"Last 5 normal_highs: {[(p.time, p.px) for p in normal_highs[-5:]]}")
