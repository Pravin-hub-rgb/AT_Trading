import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import compute_swing_results
from replay_harness import load_candles

(c15, f15), (c1h, f1h) = load_candles()
opts = {"minBars": 50, "sustainBars": 7, "b2GapBars": 1, "timeCap": "00:00", "debugSuppressed": True}
results = compute_swing_results(f15, opts, swing_count=1)

for r in results[:1]:
    print("Swing 0 breaks:")
    for b in r.get("breaks", []):
        print(f"  {b['kind']} {b['dir']} {b['time']}")
    sup = r.get("suppressed", [])
    if sup:
        print("Suppressed:", sup[:10])