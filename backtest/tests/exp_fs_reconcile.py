"""B - reconcile check 3, and fix check 4's origin.

CHECK 4 WAS WRONG IN MY LAST MESSAGE. It compared the FS bar against
seg.start_idx + 50, but seg.start_idx is NOT the leg's calculation candle. The engine
sets start_idx from _lock, and exp_missing_leg_seed.py already documents the trap:
"It is not the seed: _lock sets start_idx to ... start_idx is 29, and comparing the
two produced 1,013 false misses." I used the wrong origin and reported 89 failures
that may not exist. The real origin is the first bar each engine processes, so this
captures it by instrumenting SwingEngine.__init__.

CHECK 3 RECONCILIATION. The validator identifies the level from the global flow line
(compute_btc_flow), the engine takes it from latest_sealed_high/low. Both are the
walker, but the engine's walker is per-leg and reset each swing while the flow line is
one continuous walk over the whole window. So for each FS, compare the engine's own
target against the nearest flow-line corner and report whether they are the same point.
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
from src.btc.btc_swing import compute_btc_swings, compute_btc_flow

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000

candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
candles = list(candles)
flow = list(flow)

# ---- true leg origin: the first bar each engine ever processes -----------------
ENG_START = []
real_init = SwingEngine.__init__


def init(self, *a, **kw):
    real_init(self, *a, **kw)
    ENG_START.append({"i": -1, "legs": []})


real_step = SwingEngine.process_bar


def step(self, c, i):
    if ENG_START[-1]["i"] < 0:          # FIRST bar only, not the last
        ENG_START[-1]["i"] = i
    return real_step(self, c, i)


SwingEngine.__init__ = init
SwingEngine.process_bar = step

DECL = []
real_confirm = SwingEngine._confirm


def confirm(self, src, trig=None):
    ok = self.t[11:16] >= self.time_cap and self.bars_seen >= self.min_bars
    if ok and self._chop_cross_active:
        DECL.append({"leg": len(ENG_START) - 1, "i": self.g_idx,
                     "t": str(self.t), "dir": self.dir,
                     "bars_at_declare": self.bars_seen,
                     "cross_bar": (self.last_chop_cross_idx, self.last_chop_cross_px),
                     "target": (self.last_confirm_hit or {}).get("idx"),
                     "target_px": (self.last_confirm_hit or {}).get("px")})
    return real_confirm(self, src, trig)


SwingEngine._confirm = confirm

sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(flow) // 2))
segs = compute_btc_flow(flow, day_mode="continuous")

corners = {}
for s in segs:
    corners.setdefault(s["endIdx"], set()).add(round(s["endPx"], 1))
    corners.setdefault(s["startIdx"], set()).add(round(s["startPx"], 1))

print("=" * 88)
print("CHECK 4 REDONE WITH THE REAL LEG ORIGIN")
print("=" * 88)
print("  %-18s %-6s %-8s %-9s %s" % ("FS bar", "leg", "bars_seen", "leg start", "verdict"))
bad4 = []
for d in DECL:
    origin = ENG_START[d["leg"]]["i"]
    if origin < 0:
        continue
    d["bars_in_leg"] = d["i"] - origin
    d["origin"] = origin
    # the engine's own counter is the authority: _confirm() refuses while
    # bars_seen < min_bars, so a declaration can only ever happen at >= min_bars.
    if d["bars_at_declare"] < MIN_BARS:
        bad4.append(d)
print("  FS declarations: %d" % len(DECL))
print("  inside the 50-bar window (correct origin): %d" % len(bad4))
for d in bad4[:10]:
    print("     %s  leg %-6d bars_in=%-4d origin=%s %s"
          % (d["t"][:16], d["leg"], d["bars_in_leg"], candles[d["origin"]]["date"][:16], d["dir"]))
print()

print("=" * 88)
print("CHECK 3 RECONCILIATION: engine target vs the nearest flow-line corner")
print("=" * 88)
same = diff = nocorner = 0
diff_rows = []
for d in DECL:
    ti, tp = d.get("target"), d.get("target_px")
    if ti is None or tp is None or ti < 0:
        continue
    tpx = round(tp, 1)
    if ti in corners and tpx in corners[ti]:
        same += 1
        continue
    # is there a corner with this price somewhere near?
    hit = [k for k in corners if k <= ti and tpx in corners[k]]
    if hit:
        diff += 1
        diff_rows.append((d, max(hit)))
    else:
        nocorner += 1
        diff_rows.append((d, None))
print("  FS whose engine target IS that exact flow-line corner : %d" % same)
print("  same price, DIFFERENT index on the flow line        : %d" % diff)
print("  no flow-line corner carries that price at all      : %d" % nocorner)
print()
print("  first 12 mismatches:")
for d, k in diff_rows[:12]:
    ti, tp = d["target"]
    print("     %s  engine target idx=%s px=%-10s  flow corner idx=%-8s %s"
          % (d["t"][:16], ti, round(tp, 1),
             (str(k) if k is not None else "NONE"),
             candles[k]["date"][:16] if k is not None else ""))

Path(HERE / "_fs_reconcile.json").write_text(json.dumps({
    "inside_window_correct_origin": len(bad4),
    "target_matches_corner": same,
    "same_price_diff_index": diff,
    "no_corner_with_price": nocorner,
    "inside_window": [{"time": d["t"][:16], "bars_in": d["bars_in_leg"],
                       "origin": candles[d["origin"]]["date"][:16]} for d in bad4[:200]],
}, indent=1, default=str), encoding="utf-8")
print()
print("wrote _fs_reconcile.json")
