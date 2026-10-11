import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2024-07-16", "17:00", "18:30"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)

ROWS = []
real = SwingEngine._chop_target_high


def spy(self):
    p = real(self)
    t = self.t
    if str(t).startswith(DAY) and LO <= str(t)[11:16] <= HI:
        base = self.latest_sealed_high
        ROWS.append({
            "t": str(t)[11:16], "dir": self.dir, "bs": self.bars_seen,
            "base_px": getattr(base, "px", None), "base_idx": getattr(base, "idx", None),
            "base_time": getattr(base, "time", None),
            "g3_too_new": (base.idx > self.g_idx - 2) if base else None,
            "g4_early": ((0 <= self.dir_established_idx and base.idx <= self.dir_established_idx)
                         if base else None),
            "g5_gap": (self.bar_highs.get(base.idx + 1) if base else None),
            "g6_spent": (round(base.px, 4) in self._spent) if base else None,
            "result": getattr(p, "px", None),
            "hi": self.hi,
        })
    return p


SwingEngine._chop_target_high = spy

SHARED = set()
ri = SwingEngine.__init__


def init(self, *a, **kw):
    ri(self, *a, **kw)
    self.spent_levels = SHARED


SwingEngine.__init__ = init
from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 104)
print("WHY THE 17:45 BREAK OF 63845.8 IS INVISIBLE")
print("=" * 104)
print("  time   dir  bs   latest_sealed_high   pivot at    g3_new  g4_early  g5_gap     g6_spent  RESULT   barHigh")
print("  " + "-" * 102)
for r in ROWS:
    print("  %s  %-5s %-4d %-18s %-11s %-8s %-9s %-10s %-9s %-8s %.1f"
          % (r["t"], r["dir"], r["bs"],
             r["base_px"] if r["base_px"] is not None else "None",
             (r["base_time"] or "-")[11:16] if r["base_time"] else "-",
             "-" if r["g3_too_new"] is None else ("REJ" if r["g3_too_new"] else "ok"),
             "-" if r["g4_early"] is None else ("REJ" if r["g4_early"] else "ok"),
             r["g5_gap"] if r["g5_gap"] is not None else "-",
             "-" if r["g6_spent"] is None else ("SPENT" if r["g6_spent"] else "fresh"),
             r["result"] if r["result"] is not None else "None",
             r["hi"]))
