"""Verify the live engine's chain matches the backtest chain."""
import sys
sys.path.insert(0, ".")

import pandas as pd
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

# Load full 15m history (same as backtest)
df = pd.read_csv("../data/btc/BTCUSDT_15m.csv")
flow = [FlowCandle(date=r.timestamp, open=r.open, high=r.high, low=r.low, close=r.close)
        for _, r in df.iterrows()]

swings = compute_btc_swings(flow, opts={"minBars": 2}, max_swings=len(flow) // 2)
print(f"Full history 15m chain: {len(swings)} swings")

# Marks on Sep 9
marks = [(b, s) for s in swings for b in s.get("breaks", [])
         if "2026-09-09" in flow[b["idx"]].date]
print(f"Marks on Sep 9: {len(marks)}")
for b, s in marks:
    print(f"  {b['kind']:<4} {b['dir']:<4} @ {flow[b['idx']].date}  (sw{s['swing_index']})")

# Last 5 swings (to verify chain structure)
print(f"\nLast 5 swings:")
for s in swings[-5:]:
    print(f"  sw{s['swing_index']} {s['kind']} {s['dir']}  {s['seg']['start_time']} -> {s['seg']['end_time']}  confirmed@{s.get('confirmed_at_time','pending')}")
