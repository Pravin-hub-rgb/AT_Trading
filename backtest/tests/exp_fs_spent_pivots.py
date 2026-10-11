"""One question, one answer: on the bar where the engine declares an FS, WHICH PIVOT
does it claim to be breaking, and is that pivot actually still alive?

The owner's core rule, 2026-07-20, and I am not arguing with it:
  "the fundamental core of B1, FS, flip, B2 ... they are marked because these are
   breaking an extreme or a pivot. So if any of these are marked where the previous
   candles have broken the pivot, and yet they are not marked there, and yet they are
   marked after the candle ... that is the fundamental breakdown of not following the
   rule."

So for every single FS in the chain: at the bar it is declared, is there a live pivot
that bar genuinely breaks? If the pivot is already spent, the mark is late and wrong.

Capture the target at the exact call the engine makes, inside the snapshot swap, and
record whether that pivot had already been broken earlier in the same leg.
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
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

# every pivot break the engine performs, in order, per leg
BREAKS = []
LIVE = {"high": set(), "low": set()}
LEG = {"n": 0}

real_step = SwingEngine.process_bar
rh = SwingEngine._chop_target_high
rl = SwingEngine._chop_target_low
rc = SwingEngine._confirm


def wrap_hi(self):
    p = rh(self)
    if p is not None and self.hi > p.px:
        key = (p.idx, p.px)
        BREAKS.append({"leg": LEG["n"], "t": self.t, "kind": "H",
                       "px": p.px, "pidx": p.idx, "ptime": p.time,
                       "bar_hi": self.hi, "bar_lo": self.lo,
                       "dir": self.dir, "bs": self.bars_seen,
                       "already_broken": key in LIVE["high"]})
        LIVE["high"].add(key)
    return p


def wrap_lo(self):
    p = rl(self)
    if p is not None and self.lo < p.px:
        key = (p.idx, p.px)
        BREAKS.append({"leg": LEG["n"], "t": self.t, "kind": "L",
                       "px": p.px, "pidx": p.idx, "ptime": p.time,
                       "bar_hi": self.hi, "bar_lo": self.lo,
                       "dir": self.dir, "bs": self.bars_seen,
                       "already_broken": key in LIVE["low"]})
        LIVE["low"].add(key)
    return p


real_init = SwingEngine.__init__


def init(self, *a, **kw):
    real_init(self, *a, **kw)
    LIVE["high"].clear()
    LIVE["low"].clear()
    LEG["n"] += 1


SwingEngine.__init__ = init
SwingEngine._chop_target_high = wrap_hi
SwingEngine._chop_target_low = wrap_lo

_c, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

by_leg = collections.defaultdict(list)
for b in BREAKS:
    by_leg[b["leg"]].append(b)

print("=" * 92)
print("EVERY PIVOT BREAK, AND WHETHER THAT PIVOT WAS ALREADY SPENT")
print("=" * 92)
print("  total pivot breaks performed : %d" % len(BREAKS))
spent = [b for b in BREAKS if b["already_broken"]]
print("  breaks of an ALREADY-SPENT pivot : %d" % len(spent))
print()
for b in spent[:12]:
    print("     %-20s leg=%-5d dir=%-4s pivot %-10s (%s)  bar H/L %.1f/%.1f"
          % (b["t"], b["leg"], b["dir"], b["px"], b["ptime"], b["bar_hi"], b["bar_lo"]))
print()

print("=" * 92)
print("OWNER'S DATES - every break on that leg, in order")
print("=" * 92)
for day in ("2025-07-20", "2024-07-16"):
    print()
    print("  %s" % day)
    legs = {b["leg"] for b in BREAKS if b["t"].startswith(day)}
    for lg in sorted(legs):
        for b in by_leg[lg]:
            if not b["t"].startswith(day):
                continue
            print("     %s  dir=%-4s bs=%-4d pivot %-10s sealed %-20s  %s"
                  % (b["t"][11:16], b["dir"], b["bs"], b["px"], b["ptime"],
                     "*** SPENT PIVOT ***" if b["already_broken"] else "live"))

(HERE / "_fs_breaks.json").write_text(json.dumps(BREAKS, indent=1, default=str), encoding="utf-8")
