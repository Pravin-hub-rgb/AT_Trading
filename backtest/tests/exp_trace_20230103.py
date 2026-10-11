import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

TARGETS = {16713.0, 16726.5, 16708.0}
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)

EV = []
real_step = SwingEngine.process_bar
real_init = SwingEngine.__init__
real_mark_B1 = None


def init(self, *a, **kw):
    real_init(self, *a, **kw)
    self.spent_levels = SHARED
    self._leg_start = None


def step(self, c, i):
    n0 = len(self._spent)
    r = real_step(self, c, i)
    t = str(c.date)
    if not t.startswith("2023-01-03") or not ("11:30" <= t[11:16] <= "13:30"):
        return r
    added = [x for x in (list(self._spent) if isinstance(self._spent, list) else [])]
    new = []
    if len(self._spent) > n0:
        new = list(self._spent)[-3:]
    marks = [(m.kind, m.px) for m in self.break_marks]
    EV.append({"t": t[11:16], "dir": self.dir, "bs": self.bars_seen,
               "hi": self.hi, "lo": self.lo,
               "tgt": getattr(self._chop_target_high() if self.dir == "down"
                              else self._chop_target_low(), "px", None),
               "marks": marks, "nspent": len(self._spent),
               "recent": [x for x in SHARED if abs(x - 16713.0) < 0.5]})
    return r


SHARED = set()
SwingEngine.__init__ = init
SwingEngine.process_bar = step

from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 92)
print("2023-01-03 11:30-13:30   - who spends 16713.0 before 12:45?")
print("=" * 92)
print("  time   dir  bs   bar H / L        chop target   marks so far                 16713 spent?")
print("  " + "-" * 90)
for e in EV:
    print("  %s  %-5s %-4d %.1f / %-9.1f %-13s %-30s %s"
          % (e["t"], e["dir"], e["bs"], e["hi"], e["lo"],
             e["tgt"] if e["tgt"] is not None else "None",
             ",".join(m[0] for m in e["marks"]) or "-",
             "YES" if e["recent"] else "no"))
