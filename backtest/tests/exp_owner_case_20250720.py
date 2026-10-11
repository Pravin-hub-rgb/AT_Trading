"""Trace the 2025-07-20 swing the owner flagged: FS is on 15:30, he wants 15:15.

Owner, verbatim:
  "the marking of 2025-7-20 is wrong. The marking should be at 15:15, but it is at
   15:30. So this is wrong."

and, earlier, the general rule:
  "Where B1 is marked, FS would be also marked on the same candle."

So the candle that FIRST breaks the pivot carries B1, and the owner wants the FS on
that same candle. Print, for this one leg: where the leg starts, where the 50-bar
window ends, every cross on the leg with bars_seen at the time, and the pivot each
cross was aimed at. The question is whether 15:15 is inside the window or not - if it
is, the two rules genuinely collide and the owner has to pick; if it is outside, the
engine is simply arming too late.
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

CALLS = []
rh = SwingEngine._chop_target_high
rl = SwingEngine._chop_target_low
rc = SwingEngine._confirm


def wh(self):
    p = rh(self)
    CALLS.append({"t": self.t, "dir": self.dir, "kind": "H-target",
                  "px": getattr(p, "px", None), "pidx": getattr(p, "idx", None),
                  "ptime": getattr(p, "time", None),
                  "cross": bool(p) and self.hi > p.px,
                  "bs": self.bars_seen, "hi": self.hi, "lo": self.lo,
                  "dead": bool(p) and (p.idx, p.px) in self._crossed_high_pivots})
    return p


def wl(self):
    p = rl(self)
    CALLS.append({"t": self.t, "dir": self.dir, "kind": "L-target",
                  "px": getattr(p, "px", None), "pidx": getattr(p, "idx", None),
                  "ptime": getattr(p, "time", None),
                  "cross": bool(p) and self.lo < p.px,
                  "bs": self.bars_seen, "hi": self.hi, "lo": self.lo,
                  "dead": bool(p) and (p.idx, p.px) in self._crossed_low_pivots})
    return p


SwingEngine._chop_target_high = wh
SwingEngine._chop_target_low = wl

candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

# the swing that declares on this day
target = [s for s in sw if str(s.get("fs_at_time", "")).startswith(DAY)]
print("=" * 86)
print("SWINGS WITH AN FS ON %s : %d" % (DAY, len(target)))
print("=" * 86)
for s in target:
    st_i = s["seg"]["start_idx"]
    print()
    print("  swing %d  dir=%s" % (s["swing_index"], s["dir"]))
    print("     leg / calculation start : %s" % candles[st_i]["date"][:16])
    print("     50th bar from start    : %s   (index +%d)"
          % (candles[st_i + 49]["date"][:16] if st_i + 49 < len(candles) else "?",
             49))
    print("     first bar AFTER window : %s"
          % (candles[st_i + 50]["date"][:16] if st_i + 50 < len(candles) else "?"))
    print("     segment                : %s -> %s" % (candles[s["seg"]["start_idx"]]["date"][:16],
                                                      candles[s["seg"]["end_idx"]]["date"][:16]))
    print("     fs_at / confirmed_at   : %s / %s" % (s.get("fs_at_time"), s.get("confirmed_at_time")))
    print("     marks on this swing    :")
    for b in s["breaks"]:
        print("        %-18s %-5s %-5s @%.1f" % (b["time"][:16], b["kind"], b["dir"], b["px"]))

print()
print("=" * 86)
print("EVERY _chop_target_* CALL ON %s BETWEEN %s AND %s" % (DAY, *WATCH))
print("=" * 86)
print("  time      dir   bs   target px     pivot at          cross?  dead?   bar H / L")
print("  " + "-" * 96)
for c in CALLS:
    if not c["t"].startswith(DAY):
        continue
    if not (WATCH[0] <= c["t"][11:16] <= WATCH[1]):
        continue
    print("  %s  %-5s %-4d %-12s %-16s %-7s %-7s %.1f / %.1f"
          % (c["t"][11:16], c["dir"], c["bs"],
             c["px"] if c["px"] is not None else "None",
             (c["ptime"] or "-"), "CROSS" if c["cross"] else "-",
             "DEAD" if c["dead"] else "-", c["hi"], c["lo"]))
