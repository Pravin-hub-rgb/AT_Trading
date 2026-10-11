"""Who put 16680.0 into the chain-wide spent set? (attaching to the REAL set)

The previous attempt injected its own set in __init__, but compute_btc_swings assigns
eng.spent_levels = spent_levels right after construction and clobbers it - so the
injected set stayed empty and reported "never added" for everything. Capture the set
the chain actually uses, on the first process_bar of each engine.

Owner, 2023-01-03: the pivot is the 20:30 high 16680.0, 21:30 breaks it (16686.0), and
the engine refuses because it believes the level is already spent. No mark anywhere in
the chain uses 16680.0, so it was recorded without a break.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

WATCH = {16680.0, 16667.0, 16686.0, 16635.5}
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

REAL = []
seen = set()
HITS = []
real_step = SwingEngine.process_bar
NOW = {"t": "", "i": -1, "leg": [0]}


class Watch(set):
    def add(self, x):
        if x in WATCH and x not in self:
            HITS.append({"px": x, "at": NOW["t"], "bar": NOW["i"], "leg": NOW["leg"][0]})
        super().add(x)


def _bind(s):
    orig = s.add

    def add(x):
        if x in WATCH and x not in s:
            HITS.append({"px": x, "at": NOW["t"], "bar": NOW["i"], "leg": NOW["leg"][0]})
        orig(x)

    try:
        object.__setattr__(s, "add", add)
    except AttributeError:
        s.__class__ = _Bound


class _Bound(set):
    def add(self, x):
        if x in WATCH and x not in self:
            HITS.append({"px": x, "at": NOW["t"], "bar": NOW["i"], "leg": NOW["leg"][0]})
        super().add(x)


def step(self, c, i):
    NOW["t"] = str(c.date)
    NOW["i"] = i
    s = self.spent_levels
    if s is not None and id(s) not in seen:
        seen.add(id(s))
        REAL.append(s)
        _bind(s)
    return real_step(self, c, i)


SwingEngine.process_bar = step

from src.btc.btc_swing import compute_btc_swings
compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 86)
print("THE REAL CHAIN SPENT SETS")
print("=" * 86)
print("  distinct sets created by compute_btc_swings : %d" % len(REAL))
for k, s in enumerate(REAL):
    print("     set %d  size %d" % (k, len(s)))
print()
print("  watched prices present in any of them:")
for w in sorted(WATCH):
    where = [k for k, s in enumerate(REAL) if w in s]
    print("     %-10.1f -> %s" % (w, ("in set %s" % where) if where else "NOT PRESENT"))
print()
print("  when each watched price was added:")
if not HITS:
    print("     (nothing recorded)")
for h in HITS:
    idx = next((i for i, c in enumerate(candles) if str(c["date"]) == h["at"]), None)
    cc = candles[idx] if idx is not None else None
    print("     %-10.1f at %s (bar %d, leg %d)   that candle H=%s L=%s"
          % (h["px"], h["at"], h["bar"], h["leg"],
             cc["high"] if cc else "?", cc["low"] if cc else "?"))
