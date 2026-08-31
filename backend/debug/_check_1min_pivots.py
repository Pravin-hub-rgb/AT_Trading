"""Trace 1-min pivots detected by WalkerEngine for 28-Aug."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.config import DATA_DIR
from src.walker import WalkerEngine, FlowCandle

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
m1_day = df1[df1["ts_str"] == "2026-08-28"].reset_index(drop=True)

# Build candles dict directly (avoids _prep_day strftime issue)
m1_candles = []
for i, row in enumerate(m1_day.itertuples()):
    ts_str = str(row.timestamp)
    time_str = ts_str[11:16] if len(ts_str) > 16 else ts_str
    m1_candles.append({
        "index": i,
        "time": time_str,
        "ts": int(row.ts) if hasattr(row, 'ts') and not isinstance(row.ts, str) else 0,
        "open": float(row.open),
        "high": float(row.high),
        "low": float(row.low),
        "close": float(row.close),
    })

# Try to get ts from the original df
for i, row in m1_day.iterrows():
    ts_str = str(row["timestamp"])
    if " " in ts_str:
        from datetime import datetime
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        m1_candles[i]["ts"] = int(dt.timestamp())
    else:
        m1_candles[i]["ts"] = int(row.get("ts", 0))

print(f"1-min bars: {len(m1_candles)}")

walker = WalkerEngine()
normal_highs = []
normal_lows = []
for idx, mc in enumerate(m1_candles):
    mc_dt = f"2026-08-28T{mc['time']}:00"
    fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
    new_p = walker.process_bar(fc, idx)
    for p in new_p:
        if p.kind == "H":
            normal_highs.append(p)
        else:
            normal_lows.append(p)

print(f"\nPivot summary: {len(normal_highs)} highs, {len(normal_lows)} lows")

# Show all low pivots in the 09:25-09:45 range
print("\nLOW pivots from 09:20 to 09:45:")
for p in sorted(normal_lows, key=lambda x: x.idx):
    t = m1_candles[p.idx]["time"]
    if "09:20" <= t <= "09:45":
        print(f"  idx={p.idx} time={t} px={p.px}")

# Show all high pivots in the 09:25-09:45 range
print("\nHIGH pivots from 09:20 to 09:45:")
for p in sorted(normal_highs, key=lambda x: x.idx):
    t = m1_candles[p.idx]["time"]
    if "09:20" <= t <= "09:45":
        print(f"  idx={p.idx} time={t} px={p.px}")

# Show the 09:31 area with context
print("\n1-min candles from 09:25 to 09:40:")
for i, c in enumerate(m1_candles):
    if not ("09:2" in c["time"] or "09:3" in c["time"]):
        continue
    # Check if pivot at this idx
    is_pivot = ""
    for p in normal_highs:
        if p.idx == i:
            is_pivot = f" <<< HIGH PIVOT @ {p.px}"
            break
    for p in normal_lows:
        if p.idx == i:
            is_pivot = f" <<< LOW PIVOT @ {p.px}"
            break
    print(f"  [{i:2d}] {c['time']} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}{is_pivot}")
