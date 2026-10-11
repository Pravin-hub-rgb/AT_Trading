"""2023-01-03, 20:15-23:45 - why does 21:30 get nothing?

Owner: "the pivot was at 20:30. The one who breaks it is at 21:30. We are not
marking where the pivot is. We are marking that candle which is breaking the pivot.
Pivots were clearly at 20:30, and 21:30 breaks. This candle breaks the pivot of 20:30.
So FS should be marked here. Why there isn't no explanation for that one?"

The previous trace said "no sealed pivot" at 21:30, but that was the RESULT being
None - which conflates "the walker has no pivot at all" with "a gate rejected the
pivot the walker had". Print the raw candidate and every gate separately.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2023-01-03", "20:00", "23:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

ROWS = []
rh = SwingEngine._chop_target_high
rl = SwingEngine._chop_target_low


def wrap(orig, kind):
    def f(self):
        raw = self.latest_sealed_high if kind == "H" else self.latest_sealed_low
        res = orig(self)
        t = self.t
        if not str(t).startswith(DAY) or not (LO <= str(t)[11:16] <= HI):
            return res
        cross = raw is not None and ((self.dir == "down" and self.hi > raw.px)
                                     or (self.dir == "up" and self.lo < raw.px))
        g_new = (raw.idx > self.g_idx - 2) if raw else None
        g_early = ((0 <= self.dir_established_idx and raw.idx <= self.dir_established_idx)
                   if raw else None)
        if raw and kind == "H":
            gap = self.bar_highs.get(raw.idx + 1)
            g_gap = (gap is None or gap > raw.px)
        elif raw:
            gap = self.bar_lows.get(raw.idx + 1)
            g_gap = (gap is None or gap < raw.px)
        else:
            gap = None
            g_gap = None
        spent = (round(raw.px, 4) in self._spent) if raw else None
        ROWS.append({"t": str(t)[11:16], "dir": self.dir, "kind": kind,
                     "raw": getattr(raw, "px", None), "raw_i": getattr(raw, "idx", None),
                     "raw_t": getattr(raw, "time", None), "gap": gap,
                     "g_new": g_new, "g_early": g_early, "g_gap": g_gap,
                     "spent": spent, "res": getattr(res, "px", None),
                     "cross": cross, "hi": self.hi, "lo": self.lo,
                     "dir_est": self.dir_established_idx})
        return res
    return f


SwingEngine._chop_target_high = wrap(rh, "H")
SwingEngine._chop_target_low = wrap(rl, "L")

SHARED = set()
ri = SwingEngine.__init__


def init(self, *a, **kw):
    ri(self, *a, **kw)
    self.spent_levels = SHARED


SwingEngine.__init__ = init
from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 112)
print("2023-01-03 %s-%s   owner: pivot 20:30, broken by 21:30, FS should be at 21:30" % (LO, HI))
print("=" * 112)
print("  time   dir  kind  raw pivot  pivot at   g_new  g_early  g_gap  spent  RESULT   cross   barH / barL")
print("  " + "-" * 110)
for r in ROWS:
    if r["dir"] != "down":
        continue
    print("  %s  %-5s %s  %-11s %-11s %-6s %-8s %-6s %-6s %-8s %-8s %.1f / %.1f"
          % (r["t"], r["dir"], r["kind"],
             r["raw"] if r["raw"] is not None else "None",
             (r["raw_t"] or "-")[11:16] if r["raw_t"] else "-",
             "-" if r["g_new"] is None else ("REJ" if r["g_new"] else "ok"),
             "-" if r["g_early"] is None else ("REJ" if r["g_early"] else "ok"),
             "-" if r["g_gap"] is None else ("REJ" if r["g_gap"] else "ok"),
             "-" if r["spent"] is None else ("YES" if r["spent"] else "no"),
             r["res"] if r["res"] is not None else "None",
             "CROSS" if r["cross"] else "-", r["hi"], r["lo"]))
print()
print("gate meanings:")
print("  g_new    pivot must be at least 2 bars old")
print("  g_early  pivot must have formed AFTER the leg direction was established")
print("  g_gap    the candle right after the pivot must not breach it (1-candle gap)")
print("  spent    level already broken by an earlier mark")
