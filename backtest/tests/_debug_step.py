import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

# Monkey-patch _step to add debug
from src.firstswing import SwingEngine
original_step = SwingEngine._step

def debug_step(self, down_break, up_break):
    if self.t.startswith("2023-01-01 07:45"):
        print(f"  _step called: dir={self.dir}, up_break={up_break}, down_break={down_break}")
        print(f"    b1_bar_idx={self.b1_bar_idx}, b2_done={self._b2_done_in_dir}")
        print(f"    e_hi_prev={self.e_hi_prev.px if self.e_hi_prev else None} (idx={self.e_hi_prev.idx if self.e_hi_prev else None})")
        print(f"    hi={self.hi}, lo={self.lo}")
    original_step(self, down_break, up_break)
    if self.t.startswith("2023-01-01 07:45"):
        print(f"    after _step: breaks={[b.kind+' '+b.dir+' '+b.time for b in self.break_marks]}")
        print(f"    b2_done={self._b2_done_in_dir}")

SwingEngine._step = debug_step

from replay_harness import load_candles
(c15, f15), (c1h, f1h) = load_candles()

start_idx = 0
for i, c in enumerate(f15):
    if c.date.startswith("2023-01-01"):
        start_idx = i
        break

opts = {"minBars": 50, "sustainBars": 7, "b2GapBars": 1, "timeCap": "09:29", "debugSuppressed": True}
eng = SwingEngine(opts)

for i in range(start_idx, start_idx + 12):
    c = f15[i]
    result = eng.process_bar(c, i)
    if "07:45" in c.date:
        pass  # debug in _step
    if result:
        print(f"  {c.date}: SWING declared")