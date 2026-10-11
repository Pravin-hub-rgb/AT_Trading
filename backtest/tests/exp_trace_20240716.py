import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2024-07-16", "17:00", "19:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)

rows = []
real_step = SwingEngine.process_bar
real_hi = SwingEngine._chop_target_high
real_lo = SwingEngine._chop_target_low


def capture(self, kind, px, ptime):
    """Record what the engine is looking at, at the moment it looks."""
    t = self.t
    if not str(t).startswith(DAY) or not (LO <= str(t)[11:16] <= HI):
        return
    rows.append({"t": str(t)[11:16], "dir": self.dir, "bs": self.bars_seen,
                 "kind": kind, "tgt": px, "ptime": ptime,
                 "in_spent": (round(px, 4) in self._spent) if px is not None else None,
                 "hi": self.hi, "lo": self.lo, "g": self.g_idx})


def wh(self):
    p = real_hi(self)
    capture(self, "H", getattr(p, "px", None), getattr(p, "time", None))
    return p


def wl(self):
    p = real_lo(self)
    capture(self, "L", getattr(p, "px", None), getattr(p, "time", None))
    return p


def step(self, c, i):
    n0 = len(self._spent)
    r = real_step(self, c, i)
    if str(c.date).startswith(DAY) and LO <= str(c.date)[11:16] <= HI:
        if len(self._spent) != n0:
            rows.append({"t": str(c.date)[11:16], "dir": self.dir, "bs": self.bars_seen,
                         "kind": "SPENT", "tgt": None, "ptime": None,
                         "in_spent": None, "hi": self.hi, "lo": self.lo, "g": i,
                         "n": len(self._spent) - n0})
    return r


SwingEngine._chop_target_high = wh
SwingEngine._chop_target_low = wl
SwingEngine.process_bar = step

SHARED = set()
ri = SwingEngine.__init__


def init(self, *a, **kw):
    ri(self, *a, **kw)
    self.spent_levels = SHARED


SwingEngine.__init__ = init
from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 96)
print("%s  %s-%s   (owner: FS should be 19:00)" % (DAY, LO, HI))
print("=" * 96)
print("  time   dir   bs   H/L tgt   target      pivot at   spent?  cross  barH / barL   note")
print("  " + "-" * 94)
for r in rows:
    if r["kind"] == "SPENT":
        print("  %s  %-5s %-4d   ----    %-11s %-10s %-7s %-6s %.1f / %.1f    %d level(s) spent"
              % (r["t"], r["dir"], r["bs"], "-", "-", "-", "-", r["hi"], r["lo"], r["n"]))
        continue
    px = r["tgt"]
    cross = px is not None and ((r["dir"] == "down" and r["hi"] > px) or (r["dir"] == "up" and r["lo"] < px))
    print("  %s  %-5s %-4d   %s    %-11s %-10s %-7s %-6s %.1f / %.1f"
          % (r["t"], r["dir"], r["bs"], r["kind"],
             px if px is not None else "None",
             (r["ptime"] or "-")[11:16] if r["ptime"] else "-",
             "-" if r["in_spent"] is None else ("SPENT" if r["in_spent"] else "fresh"),
             "CROSS" if cross else "-", r["hi"], r["lo"]))
