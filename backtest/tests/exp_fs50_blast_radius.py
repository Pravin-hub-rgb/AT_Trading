"""How many swings currently declare on a cross that started BEFORE the 50th bar?

OWNER'S RULE (verbatim, 2026-10-11)
-----------------------------------
"if any FS comes before 50th bar, we look. We neglect it. We just going to neglect
it. We will wait 50th bar, and we will be looking new FS after the 50th bar. If this
is not happening, so there is something wrong here. And if we are just declaring,
like FS is there, but it hasn't given the signal of 50th bar, and the 50th bar comes,
then we are declaring that there is an FS. So this is wrong, because we have to enter
at FS."

WHAT THE ENGINE DOES INSTEAD
-----------------------------
firstswing.py:567-579 calls _confirm("chop") on EVERY bar while the cross is active.
_confirm() returns early while bars_seen < min_bars and then fires as soon as
min_bars is reached - so a cross that opened on bar 12 gets declared on bar 50
anyway. last_chop_cross_idx, which becomes fs_at_idx, keeps pointing at the stale
cross.

So the question is not whether the gap is big. It is how many of the 2952 swings are
declared off a cross that was already open before the leg reached 50 bars.

Also counted: the same shape via time_cap (09:29), which gates declaration on the
clock rather than on the cross.
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
CAP = "09:29"

# Every cross that opens, with bars_seen at the moment it opened.
CROSSES = []
real_step = SwingEngine.process_bar


def step(self, c, i):
    was = self._chop_cross_active
    r = real_step(self, c, i)
    if not was and self._chop_cross_active:
        CROSSES.append({"eng_bars_seen_at_open": self.bars_seen,
                        "g_idx": self.g_idx, "time": self.t,
                        "declared": self.declared,
                        "min_bars": self.min_bars, "time_cap": self.time_cap})
    return r


SwingEngine.process_bar = step

candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                        max_swings=max(1, len(flow) // 2))

print("=" * 78)
print("BLAST RADIUS  -  swings declared off a cross that opened before the 50th bar")
print("=" * 78)
print("  swings in chain              : %d" % len(sw))
print("  crosses observed             : %d" % len(CROSSES))
print()

opened_early = [c for c in CROSSES if c["eng_bars_seen_at_open"] < MIN_BARS]
print("  crosses that OPENED before the leg reached 50 bars : %d" % len(opened_early))
print("     of those, the engine DID declare on them       : %d"
      % sum(1 for c in opened_early if c["declared"]))
print()

# tie it to the swings that actually got declared
dec_early = [c for c in opened_early if c["declared"]]
print("  SWINGS AFFECTED (declared off a stale cross): %d of %d  (%.1f%%)"
      % (len(dec_early), len(sw), 100.0 * len(dec_early) / max(1, len(sw))))
print()
print("  bars_seen when those crosses opened:", dict(sorted(collections.Counter(
    c["eng_bars_seen_at_open"] for c in dec_early).items())[:12]))
print()

# how many swings have fs_at before their own 50th bar - the owner-facing symptom
stale = []
for s in sw:
    fa = s.get("fs_at_idx")
    ca = s.get("confirmed_at_idx")
    if fa is None or ca is None:
        continue
    if ca > fa:
        stale.append(s)
print("  swings where the DECLARATION is later than the FS cross : %d" % len(stale))
print("     -> these are exactly the entries the owner says must be")
print("        thrown away and re-sought after the 50th bar")
print()
print("  gap distribution on those:", dict(sorted(collections.Counter(
    s["confirmed_at_idx"] - s["fs_at_idx"] for s in stale).items())))
print()
print("  first 12 affected swings (fs_at -> confirmed_at):")
for s in stale[:12]:
    print("     swing %-6d %s  ->  %s   (+%d bars)"
          % (s["swing_index"], candles[s["fs_at_idx"]]["date"][:16],
             candles[s["confirmed_at_idx"]]["date"][:16],
             s["confirmed_at_idx"] - s["fs_at_idx"]))

# time_cap exposure
precap = [c for c in dec_early if c["time"] < c["time_cap"]]
print()
print("  of the affected crosses, %d opened before the %s time cap as well"
      % (len(precap), CAP))

(HERE / "_blast_radius.json").write_text(json.dumps({
    "swings": len(sw), "crosses": len(CROSSES),
    "opened_before_50": len(opened_early),
    "declared_off_stale": len(dec_early),
    "swing_declaration_later_than_fs": len(stale),
    "gap_hist": dict(collections.Counter(
        s["confirmed_at_idx"] - s["fs_at_idx"] for s in stale)),
}, indent=1), encoding="utf-8")
