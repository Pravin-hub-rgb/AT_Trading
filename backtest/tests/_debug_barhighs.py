import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from replay_harness import load_candles

(c15, f15), (c1h, f1h) = load_candles()

start_idx = 0
for i, c in enumerate(f15):
    if c.date.startswith("2023-01-01"):
        start_idx = i
        break

opts = {"minBars": 50, "sustainBars": 7, "b2GapBars": 1, "timeCap": "09:29", "debugSuppressed": True}
eng = SwingEngine(opts)
print(f"b2_gap_bars = {eng.b2_gap_bars}")

# Process a few bars
for i in range(start_idx, start_idx + 4):
    c = f15[i]
    eng.process_bar(c, i)

print(f"After 4 bars: bar_highs = {eng.bar_highs}")
print(f"b2_gap_bars = {eng.b2_gap_bars}")