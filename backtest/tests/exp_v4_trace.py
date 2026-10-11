"""Where does confirmed_at - fs_at actually come from?

Two guesses so far were wrong. Instrument the declaration event itself instead of
inferring it.

For every cross that opens, record bars_seen at the moment it opened. For every
declaration, record the cross that declared it. Then look at the ones that declare
LATER than the cross that opened.
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_swing import compute_btc_swings
from src.btc.btc_routes import _load_window

MIN_BARS = 50

real_step = SwingEngine.process_bar
OPEN = {}      # engine id -> the cross currently open


def step(self, c, i):
    was = self._chop_cross_active
    bs_before = self.bars_seen
    r = real_step(self, c, i)
    if not was and self._chop_cross_active:
        OPEN[id(self)] = {"open_g": i, "open_bs": bs_before,
                          "open_time": self.t, "open_px": self.hi if self.dir == "up" else self.lo}
    if self.declared:
        o = OPEN.get(id(self), {})
        rec = {"t": self.t, "decl_g": i, "decl_bs": bs_before,
               "conf_idx": self.confirmed_at_idx, "last_cross": self.last_chop_cross_idx,
               "end_idx": self.end_idx, "dir": self.dir,
               "open_g": o.get("open_g"), "open_bs": o.get("open_bs"),
               "open_time": o.get("open_time")}
        DECLS.append(rec)
    return r


DECLS = []
SwingEngine.process_bar = step

candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(flow) // 2))

print("=" * 78)
print("DECLARATION EVENTS: %d   swings out: %d" % (len(DECLS), len(sw)))
print("=" * 78)

gap = collections.Counter(d["conf_idx"] - d["last_cross"] for d in DECLS
                          if d["last_cross"] >= 0)
print("  confirmed_at - last_chop_cross :", dict(sorted(gap.items())))
print()

late = [d for d in DECLS if d["last_cross"] >= 0 and d["conf_idx"] > d["last_cross"]]
print("  declarations later than their cross : %d" % len(late))
print()
print("  For those, bars_seen when the cross OPENED vs at DECLARATION:")
h = collections.Counter((d["open_bs"] // 10 * 10, d["decl_bs"] // 10 * 10) for d in late)
for k, v in sorted(h.items())[:14]:
    print("     cross opened at bars_seen %3d-%3d   declared at bars_seen %3d-%3d   x%d"
          % (k[0], k[0] + 9, k[1], k[1] + 9, v))
print()
print("  cross opened BELOW min_bars in those?  %d of %d"
      % (sum(1 for d in late if d["open_bs"] < MIN_BARS), len(late)))
print("  cross opened ABOVE min_bars in those?  %d of %d"
      % (sum(1 for d in late if d["open_bs"] >= MIN_BARS), len(late)))
print()
print("  first 6 late declarations, full detail:")
for d in late[:6]:
    print("     dir=%-4s cross opened g=%-7s bs=%-4s | declared g=%-7s bs=%-4s | conf=%-7s last_cross=%-7s"
          % (d["dir"], d["open_g"], d["open_bs"], d["decl_g"], d["decl_bs"],
             d["conf_idx"], d["last_cross"]))
    print("        open time=%s   declared time=%s" % (d["open_time"], d["t"]))
