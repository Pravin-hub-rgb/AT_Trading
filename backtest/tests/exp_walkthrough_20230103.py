"""2023-01-03, the owner's walkthrough, answered bar by bar.

Owner, verbatim:
  "FS is marked at 23:30. But, like, why FS is not marked before here? Because the
   50 candle is somewhere around 17:00 you said, and here we are looking for a down
   break. And there are many down breaks, but low breaks happened at 20:00, some
   happened at 18:15 too. So, like, why these are not marked? Is there a rule that
   there should be a one candle gap, something like that, just like B2 have a rule
   that this must be a one candle gap rule for B2. So is there a rule for FS too?
   Because we are looking for opposite direction chop, and no chop happens after,
   like, the 50-hour between this, somewhere around 17:00 to 20:00, nothing happens
   here. This is what I want to ask. So then this flip happens at 20:15. So now from
   here we are looking for an FS, which is upside direction. And so if that's the
   case, then 21:30 is the right candidate to mark an FS. But that doesn't happen.
   But finally, the FS is marked at 23:30. So what is going on?"

So print, for every bar from 17:00 to 23:45: the leg state, the 50-bar boundary, the
candidate pivot the chop path is looking at, and which gate rejects it - by name.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2023-01-03", "16:00", "23:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)

ROWS = []
real_step = SwingEngine.process_bar
real_hi = SwingEngine._chop_target_high
real_lo = SwingEngine._chop_target_low
rh = SwingEngine._chop_target_high
rl = SwingEngine._chop_target_low


def why(self, p, kind):
    if p is None:
        return "no sealed pivot"
    r = []
    if p.idx > self.g_idx - 2:
        r.append("too new (p.idx %d > bar %d-2)" % (p.idx, self.g_idx))
    if 0 <= self.dir_established_idx and p.idx <= self.dir_established_idx:
        r.append("pivot %d predates dir_established %d" % (p.idx, self.dir_established_idx))
    gh = self.bar_highs.get(p.idx + 1)
    gl = self.bar_lows.get(p.idx + 1)
    if kind == "H":
        if gh is None or gh > p.px:
            r.append("GAP: next bar high %s vs pivot %.1f" % (gh, p.px))
    else:
        if gl is None or gl < p.px:
            r.append("GAP: next bar low %s vs pivot %.1f" % (gl, p.px))
    if not r:
        return "PASSES ALL GATES"
    return " | ".join(r)


def wrap_hi(self):
    p = rh(self)
    rec(self, "H", p)
    return p


def wrap_lo(self):
    p = rl(self)
    rec(self, "L", p)
    return p


def rec(self, kind, p):
    t = self.t
    if not str(t).startswith(DAY) or not (LO <= str(t)[11:16] <= HI):
        return
    cross = p is not None and ((self.dir == "down" and self.hi > p.px)
                               or (self.dir == "up" and self.lo < p.px))
    ROWS.append({"t": str(t)[11:16], "dir": self.dir, "bs": self.bars_seen,
                 "kind": kind, "px": getattr(p, "px", None),
                 "ptime": getattr(p, "time", None),
                 "why": why(self, p, kind), "cross": cross,
                 "hi": self.hi, "lo": self.lo,
                 "dir_est": self.dir_established_idx})


SwingEngine._chop_target_high = wrap_hi
SwingEngine._chop_target_low = wrap_lo
SwingEngine.process_bar = real_step

SHARED = set()
ri = SwingEngine.__init__


def init(self, *a, **kw):
    ri(self, *a, **kw)
    self.spent_levels = SHARED
    self._leg_start_bar = None


SwingEngine.__init__ = init
from src.btc.btc_swing import compute_btc_swings
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

# find the leg the owner is describing: starts 05:45, FS at 23:30
leg = [s for s in sw if str(s.get("fs_at_time", "")).startswith(DAY) and s.get("fs_at_time", "")[11:16] == "23:30"]
print("=" * 104)
if leg:
    s = leg[0]
    st = s["seg"]["start_idx"]
    print("LEG %d   calculation candle %s   50th bar = %s   FS at %s"
          % (s["swing_index"], candles[st]["date"][:16],
             candles[st + 49]["date"][:16] if st + 49 < len(candles) else "?",
             s.get("fs_at_time")))
    print("  breaks:", [(b["time"][11:16], b["kind"], round(b["px"], 1)) for b in s["breaks"]])
print("=" * 104)
print("  time   dir  bs    kind  candidate pivot  pivot at      bar H / L       verdict")
print("  " + "-" * 102)
for r in ROWS:
    print("  %s  %-5s %-4d %s  %-15s %-13s %.1f / %-9.1f %s"
          % (r["t"], r["dir"], r["bs"], r["kind"],
             r["px"] if r["px"] is not None else "None",
             (r["ptime"] or "-")[11:16] if r["ptime"] else "-",
             r["hi"], r["lo"],
             ("CROSS -> " if r["cross"] else "") + r["why"]))
