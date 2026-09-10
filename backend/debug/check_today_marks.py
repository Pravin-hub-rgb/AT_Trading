"""Check what marks fire on 2026-09-09 from the backtest chain."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle
import pandas as pd

df = pd.read_csv("../data/btc/BTCUSDT_15m.csv")
flow = [FlowCandle(date=r.timestamp, open=r.open, high=r.high, low=r.low, close=r.close)
        for _, r in df.iterrows()]

# Find indices for Sep 9
sep9_indices = [i for i, c in enumerate(flow) if c.date >= "2026-09-09"]
print(f"Sep 9 candles: {len(sep9_indices)} (idx {sep9_indices[0]}..{sep9_indices[-1]})")

sw = compute_btc_swings(flow, opts={"minBars": 2}, max_swings=len(flow) // 2)

marks = []
for s in sw:
    for b in s.get("breaks", []):
        if int(b["idx"]) in sep9_indices:
            marks.append({
                **b,
                "swing_no": s["swing_index"],
                "swing_confirmed": s.get("confirmed_at_time", ""),
                "swing_kind": s.get("kind", ""),
                "date": flow[int(b["idx"])].date,
            })

print(f"Total swings: {len(sw)}")
print(f"Marks on 2026-09-09: {len(marks)}")
for m in sorted(marks, key=lambda x: x["date"]):
    print(f'  {m["date"]} {m["kind"]:<4} {m["dir"]:<4} sw{m["swing_no"]} @ {m["px"]:.2f} confirmed@{m["swing_confirmed"]} ({m["swing_kind"]})')
