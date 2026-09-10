"""Compare backtest marks vs live rolling-window marks for the same candles."""
import sys
sys.path.insert(0, ".")

import pandas as pd
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

# Load full 15m history
df = pd.read_csv("../data/btc/BTCUSDT_15m.csv")
print(f"Full history: {len(df)} rows, {df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}")

# Build flow candles
flow = [
    FlowCandle(date=r["timestamp"], open=r["open"], high=r["high"], low=r["low"], close=r["close"])
    for _, r in df.iterrows()
]

# Full-history chain (backtest ground truth) — use last 5000 bars only for speed
flow_tail = flow[-5000:]
swings_full = compute_btc_swings(flow_tail, opts={"minBars": 2}, max_swings=len(flow_tail) // 2)
print(f"\nFull-history chain (last 5000 bars): {len(swings_full)} swings")

# Collect all marks from full-history chain (indices relative to flow_tail)
full_marks = {}
offset = len(flow) - 5000
for s in swings_full:
    for b in s.get("breaks", []):
        idx = int(b.get("idx", -1)) + offset  # map to global index
        full_marks[idx] = {
            "kind": b["kind"],
            "dir": b["dir"],
            "px": float(b["px"]),
            "swing_no": s.get("swing_index"),
            "bar_date": flow[idx].date if idx < len(flow) else "",
        }

print(f"Full-history marks: {len(full_marks)} total")

# Show marks near the tail (last 500 bars)
tail_marks = {k: v for k, v in full_marks.items() if k >= len(flow) - 500}
print(f"\nMarks in last 500 bars (full-history chain):")
for idx in sorted(tail_marks.keys())[-10:]:
    m = tail_marks[idx]
    print(f"  idx={idx} {m['bar_date']} {m['kind']} {m['dir']} sw{m['swing_no']} @{m['px']:.2f}")

# Now simulate the live rolling window (last ~2880 bars = 30 days)
window_size = 2880
flow_window = flow[-window_size:]
swings_window = compute_btc_swings(flow_window, opts={"minBars": 2}, max_swings=len(flow_window) // 2)
print(f"\nRolling-window chain: {len(swings_window)} swings")

# Collect marks from rolling-window chain (indices are relative to window)
window_marks = {}
for s in swings_window:
    for b in s.get("breaks", []):
        idx = int(b.get("idx", -1))
        global_idx = len(flow) - window_size + idx  # map to global index
        window_marks[global_idx] = {
            "kind": b["kind"],
            "dir": b["dir"],
            "px": float(b["px"]),
            "swing_no": s.get("swing_index"),
            "bar_date": flow_window[idx].date if idx < len(flow_window) else "",
        }

print(f"Rolling-window marks: {len(window_marks)} total")

# Show marks near the tail of the window
tail_window = {k: v for k, v in window_marks.items() if k >= len(flow) - 500}
print(f"\nMarks in last 500 bars (rolling-window chain):")
for idx in sorted(tail_window.keys())[-10:]:
    m = tail_window[idx]
    print(f"  gidx={idx} {m['bar_date']} {m['kind']} {m['dir']} sw{m['swing_no']} @{m['px']:.2f}")

# Compare: how many of the full-history tail marks are in the window chain?
common = set(tail_marks.keys()) & set(tail_window.keys())
only_full = set(tail_marks.keys()) - set(tail_window.keys())
only_window = set(tail_window.keys()) - set(tail_marks.keys())

print(f"\n--- Comparison (last 500 bars) ---")
print(f"Full-history marks: {len(tail_marks)}")
print(f"Rolling-window marks: {len(tail_window)}")
print(f"Common (same global idx): {len(common)}")
print(f"Only in full-history: {len(only_full)}")
print(f"Only in rolling-window: {len(only_window)}")

if only_full:
    print(f"\nMarks in full-history but NOT in rolling-window:")
    for idx in sorted(only_full)[-5:]:
        m = tail_marks[idx]
        print(f"  gidx={idx} {m['bar_date']} {m['kind']} {m['dir']} sw{m['swing_no']}")

if only_window:
    print(f"\nMarks in rolling-window but NOT in full-history:")
    for idx in sorted(only_window)[-5:]:
        m = tail_window[idx]
        print(f"  gidx={idx} {m['bar_date']} {m['kind']} {m['dir']} sw{m['swing_no']}")
