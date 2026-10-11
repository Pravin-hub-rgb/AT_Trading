"""Which gate refuses to recognise the 14:45 low 118037.0 as a pivot on 15:15?

The owner, 2025-07-20:
  "14:45 is a pivot. The low of it is the same which you have written, 118037.0. And
   then 15:00, this is not breaking it. Low is equals, so we cannot rule it out. Then
   15:15 did break it. This is a pivot. ... Then there is no pivot here, which the
   15:30 candle is breaking. So this is very wrong."

Engine returns None for the target on 14:45, 15:00 and 15:15, and only produces a
target at 15:30. So the 14:45 low is not being recognised as a sealed pivot until
three bars late, which is exactly why 15:30 gets to re-break it.

_chop_target_low applies four gates after fetching latest_sealed_low:
    1  p is None
    2  p.idx < 0
    3  p.idx > g_idx - 2        (pivot must be at least 2 bars old)
    4  p.idx <= dir_established_idx  (pivot must form after the leg was established)
    5  gap rule                 (next candle's low must not breach the pivot)
    6  dead-pivot ledger         (added today)

Print each gate's verdict for the bars around the owner's case, along with what the
walker thinks latest_sealed_low is at that moment. That separates "the walker has not
sealed it yet" from "a gate is rejecting a pivot it already has".
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

DAY = "2025-07-20"
WATCH = ("14:00", "16:30")
ROWS = []

real = SwingEngine.process_bar


def step(self, c, i):
    r = real(self, c, i)
    if not str(c.date).startswith(DAY):
        return r
    if not (WATCH[0] <= str(c.date)[11:16] <= WATCH[1]):
        return r
    if self.dir != "up":
        return r
    p = self.latest_sealed_low
    tgt = self._chop_target_low()
    ROWS.append({
        "t": str(c.date)[11:16], "bs": self.bars_seen,
        "latest_idx": getattr(p, "idx", None), "latest_px": getattr(p, "px", None),
        "latest_time": getattr(p, "time", None),
        "snap_px": getattr(getattr(self, "_snap_low", None), "px", None),
        "snap_idx": getattr(getattr(self, "_snap_low", None), "idx", None),
        "dir_est": self.dir_established_idx,
        "g3_p_too_new": (p.idx > i - 2) if p is not None else None,
        "g4_formed_early": ((0 <= self.dir_established_idx and p.idx <= self.dir_established_idx)
                            if p is not None else None),
        "g5_gap": (self.bar_lows.get(p.idx + 1) if p is not None else None),
        "g6_dead": ((p.idx, p.px) in self._crossed_low_pivots) if p is not None else None,
        "tgt": getattr(tgt, "px", None), "lo": self.lo,
    })
    return r


SwingEngine.process_bar = step

_c, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 100)
print("WHY 118037.0 IS NOT A PIVOT UNTIL 15:30   (dir=up leg, target = low pivot)")
print("=" * 100)
print("  time   bs  latest_sealed_low            snap_low              dir_est g3     g4     g5(gap)  g6     TARGET   bar low")
print("  " + "-" * 99)
for r in ROWS:
    lt = r["latest_time"] or "-"
    print("  %s  %-4s %-10s @%-10s %-10s %-11s %-6s %-6s %-5s %-9s %-6s %-9s %.1f"
          % (r["t"], r["bs"],
             ("%s" % (lt[11:16] if r["latest_time"] else "None")),
             r["latest_px"] if r["latest_px"] is not None else "-",
             (("%s" % r["snap_idx"]) if r["snap_idx"] is not None else "None"),
             r["snap_px"] if r["snap_px"] is not None else "-",
             r["dir_est"] if r["dir_est"] >= 0 else "none",
             "REJ" if r["g3_p_too_new"] else "ok",
             "REJ" if r["g4_formed_early"] else "ok",
             (r["g5_gap"] if r["g5_gap"] is not None else "-"),
             "DEAD" if r["g6_dead"] else "ok",
             r["tgt"] if r["tgt"] is not None else "None",
             r["lo"]))
