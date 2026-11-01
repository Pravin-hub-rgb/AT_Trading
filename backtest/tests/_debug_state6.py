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

for i in range(start_idx, start_idx + 12):
    c = f15[i]
    
    # Replicate up_break computation
    up_break = c.high > eng.e_hi.px if eng.e_hi.px == eng.e_hi.px else True
    down_break = c.low < eng.e_lo.px if eng.e_lo.px == eng.e_lo.px else True
    
    result = eng.process_bar(c, i)
    
    if "07:45" in c.date:
        print(f"\nAt 07:45:")
        print(f"  dir={eng.dir}, dir_confirmed={eng.dir_confirmed}")
        print(f"  b1_bar_idx={eng.b1_bar_idx}, b2_done={eng._b2_done_in_dir}")
        print(f"  e_hi_prev (before _step) was: need to check")
        print(f"  up_break={up_break}, down_break={down_break}")
        print(f"  breaks: {[b.kind+' '+b.dir+' '+b.time for b in eng.break_marks]}")
        print(f"  suppressed: {eng.suppressed[-3:] if eng.suppressed else 'none'}")
    
    if result:
        print(f"  {c.date}: SWING declared -> {result.get('break_kind')}")