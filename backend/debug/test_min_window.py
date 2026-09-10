"""Find the minimum rolling window that reproduces full-history tail marks."""
import sys
sys.path.insert(0, ".")

import pandas as pd
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

df = pd.read_csv("../data/btc/BTCUSDT_15m.csv")
flow = [FlowCandle(date=r.timestamp, open=r.open, high=r.high, low=r.low, close=r.close) for _, r in df.iterrows()]

# Full-history marks (ground truth) — last 200 bars
sw_full = compute_btc_swings(flow, opts={"minBars": 2}, max_swings=len(flow) // 2)
full_marks = {}
for s in sw_full:
    for b in s.get("breaks", []):
        idx = int(b.get("idx", -1))
        if idx >= len(flow) - 200:
            full_marks[idx] = (b["kind"], b["dir"], round(float(b["px"]), 2))

print(f"Full-history marks in last 200 bars: {len(full_marks)}")

# Test different window sizes
for w in [50, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000]:
    flow_w = flow[-w:]
    sw_w = compute_btc_swings(flow_w, opts={"minBars": 2}, max_swings=w // 2)
    w_marks = {}
    for s in sw_w:
        for b in s.get("breaks", []):
            idx = int(b.get("idx", -1))
            global_idx = len(flow) - w + idx
            if global_idx >= len(flow) - 200:
                w_marks[global_idx] = (b["kind"], b["dir"], round(float(b["px"]), 2))
    
    # Compare
    match = sum(1 for k in full_marks if k in w_marks and full_marks[k] == w_marks[k])
    only_full = sum(1 for k in full_marks if k not in w_marks)
    diff = sum(1 for k in full_marks if k in w_marks and full_marks[k] != w_marks[k])
    
    print(f"  window={w:4d}: match={match:2d}  missing={only_full:2d}  diff={diff:2d}  {'OK' if match == len(full_marks) else 'MISMATCH'}")
