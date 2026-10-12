"""Why is 118037.0 not in the ledger when the B1 at 15:15 broke it?

At 15:30 the chop finds pivot 118037.0 and the verdict is OK, so
(pivot.idx, 118037.0) is NOT in the spent set - even though a B1 marked
"B1 down @118037.0" at 15:15. So the key the B1 stored and the key the chop looks up
are not the same. Print both.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2025-07-20", "15:00", "15:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

MARK_ADD = []
real_step = SwingEngine.process_bar
real_lock = SwingEngine._lock


def lock(self, dir):
    r = real_lock(self, dir)
    MARK_ADD.append({"t": self.t, "dir": dir, "locked_level": self.locked_level,
                     "e_hi_prev": (self.e_hi_prev.px, self.e_hi_prev.idx),
                     "e_lo_prev": (self.e_lo_prev.px, self.e_lo_prev.idx),
                     "key": ((self.e_hi_prev if dir == "up" else self.e_lo_prev).idx,
                             round((self.e_hi_prev if dir == "up" else self.e_lo_prev).px, 4))})
    return r


def step(self, c, i):
    r = real_step(self, c, i)
    t = str(c.date)
    if t.startswith(DAY) and LO <= t[11:16] <= HI and self.dir == "up":
        p = self.latest_sealed_low
        if p is not None and abs(p.px - 118037.0) < 0.5:
            key = (p.idx, round(p.px, 4))
            print("  %s  chop sees pivot %s   key=%s   spent=%s"
                  % (t[11:16], p.px, key, key in self._spent))
            for k in self._spent:
                if abs(k[1] - 118037.0) < 0.5:
                    print("        ledger has %s" % (k,))
    return r


SwingEngine._lock = lock
SwingEngine.process_bar = step

from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print()
print("B1 marks recorded in this window:")
for m in MARK_ADD:
    if str(m["t"]).startswith(DAY) and LO <= str(m["t"])[11:16] <= HI:
        print("  %s  dir=%-5s locked_level=%.1f  key stored=%s"
              % (str(m["t"])[11:16], m["dir"], m["locked_level"], m["key"]))
        print("        e_hi_prev=%s   e_lo_prev=%s" % (m["e_hi_prev"], m["e_lo_prev"]))
