import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import compute_fs_v2_results
from src.walker import FlowCandle
from replay_harness import load_candles

(c15, f15), (c1h, f1h) = load_candles()

# Get Jan 2 candles
jan2 = [c for c in f15 if c.date.startswith("2023-01-02")]
print(f"Jan 2 candles: {len(jan2)}")

# Run first_second
results = compute_fs_v2_results(jan2, opts={"minBars": 50, "timeCap": "09:29"})
for r in results:
    print("Day " + r.day + ":")
    for b in r.breaks:
        print("  " + b.kind + " " + b.dir + " " + b.time)