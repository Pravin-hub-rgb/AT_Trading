import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _compute_swings
from replay_harness import load_candles

(c15, f15), (c1h, f1h) = load_candles()
sw = _compute_swings(f15, "continuous", min_bars=50)

for s in sw:
    seg = s.get("seg", {})
    start_idx = seg.get("start_idx", -1)
    start_time = f15[start_idx].date if 0 <= start_idx < len(f15) else "?"
    if "2023-01-02" in str(start_time):
        print("Swing " + str(s["swing_index"]) + " start=" + str(start_time))
        for b in (s.get("breaks") or []):
            print("  " + b["kind"] + " " + b["dir"] + " " + b["time"])