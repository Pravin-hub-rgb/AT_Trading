"""Read what _chop_target_low ACTUALLY returns. No re-derivation.

The previous trace recomputed the gates by hand, which is how it reported OK at 15:30
while the ledger already held the pivot. It has to read the function's own result.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2025-07-20", "14:45", "16:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

real_tgt = SwingEngine._chop_target_low
real_tgt_hi = SwingEngine._chop_target_high
real_step = SwingEngine.process_bar


def wrap(orig, kind):
    def f(self):
        res = orig(self)
        t = str(self.t)
        if t.startswith(DAY) and LO <= t[11:16] <= HI:
            raw = self.latest_sealed_high if kind == "H" else self.latest_sealed_low
            key = (getattr(raw, "idx", None), round(getattr(raw, "px", 0), 4))
            cross = False
            if res is not None:
                cross = (self.hi > res.px) if kind == "H" else (self.lo < res.px)
            print("  %s leg%-5d %s dir=%-5s bs=%-3d | walker pivot %-10s key=%-18s spent=%-5s | ENGINE RETURNS %-10s %s"
                  % (t[11:16], LEG["n"], kind, self.dir, self.bars_seen,
                     getattr(raw, "px", None), key, key in self._spent,
                     ("%.1f" % res.px) if res else "None",
                     "CROSS" if cross else ""))
        return res
    return f


LEG = {"n": 0}
ri = SwingEngine.__init__


def init(self, *a, **kw):
    LEG["n"] += 1
    ri(self, *a, **kw)


SwingEngine.__init__ = init
SwingEngine._chop_target_low = wrap(real_tgt, "L")
SwingEngine._chop_target_high = wrap(real_tgt_hi, "H")
SwingEngine.process_bar = real_step

from src.btc.btc_swing import compute_btc_swings
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print()
print("FS lands at:")
for s in sw:
    if str(s.get("fs_at_time", "")).startswith(DAY):
        print("   swing %d  %s" % (s["swing_index"], s["fs_at_time"]))
