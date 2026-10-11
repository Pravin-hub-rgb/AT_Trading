"""Capture the pivot the engine ACTUALLY used, not a re-derivation of it.

CORRECTION
----------
A previous version of this probe reported 389 FS with "no target" and 447 that did
not breach their target. Both numbers were wrong and both came from the probe, not
the engine. _check_chop temporarily swaps latest_sealed_high for _snap_high before
calling _chop_target_high(), and does the mirror for the low:

    _orig = self.latest_sealed_high
    if _snap is not None: self.latest_sealed_high = _snap
    tgt = self._chop_target_high()
    self.latest_sealed_high = _orig

Re-deriving the target outside that swap reads a different - older - pivot, so most
of the chain appeared to have no valid target at all. The engine was never wrong
here; the measurement was.

This version wraps _chop_target_high and _chop_target_low themselves and records
every return value with the state at the moment of the call. That is the exact pivot
the engine acted on, by construction.
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

CALLS = []          # every _chop_target_* call, with its return
real_hi = SwingEngine._chop_target_high
real_lo = SwingEngine._chop_target_low
real_step = SwingEngine.process_bar


def wrap(orig, kind):
    def f(self):
        p = orig(self)
        CALLS.append({"kind": kind, "g": self.g_idx, "t": self.t, "dir": self.dir,
                      "px": getattr(p, "px", None), "idx": getattr(p, "idx", None),
                      "time": getattr(p, "time", None),
                      "lo": self.lo, "hi": self.hi,
                      "crossing": (p is not None
                                   and ((self.dir == "up" and self.lo < p.px)
                                        or (self.dir == "down" and self.hi > p.px)))})
        return p
    return f


SwingEngine._chop_target_high = wrap(real_hi, "high")
SwingEngine._chop_target_low = wrap(real_lo, "low")

# which call produced each declaration
DECL = []
real_confirm = SwingEngine._confirm


def confirm(self, src, trig=None):
    ok = self.t[11:16] >= self.time_cap and self.bars_seen >= self.min_bars
    if ok and self._chop_cross_active:
        DECL.append({"g": self.g_idx, "t": self.t, "dir": self.dir,
                     "bars_seen": self.bars_seen})
    return real_confirm(self, src, trig)


SwingEngine._confirm = confirm

candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 80)
print("THE PIVOT THE ENGINE ACTUALLY USED  (captured at the call, not re-derived)")
print("=" * 80)
print("  _chop_target_* calls made      : %d" % len(CALLS))
print("  returned a pivot               : %d" % sum(1 for c in CALLS if c["px"] is not None))
print("  returned None                  : %d" % sum(1 for c in CALLS if c["px"] is None))
print("  returned a pivot AND crossing  : %d" % sum(1 for c in CALLS if c["crossing"]))
print("  declarations                    : %d" % len(DECL))
print()

# every declaration must correspond to a crossing call on the same bar
cross_by_bar = {}
for c in CALLS:
    if c["crossing"]:
        cross_by_bar.setdefault(c["g"], c)

ok = bad = 0
bad_rows = []
for d in DECL:
    c = cross_by_bar.get(d["g"])
    if c is None:
        bad += 1
        bad_rows.append((d, None))
    else:
        ok += 1
        d["tgt_px"] = c["px"]; d["tgt_idx"] = c["idx"]; d["tgt_time"] = c["time"]

print("  declarations backed by a real pivot break : %d" % ok)
print("  declarations with NO pivot break          : %d" % bad)
print()
for d, c in bad_rows[:12]:
    print("     %-20s dir=%-4s bars_seen=%-4d   no target was ever returned on this bar"
          % (d["t"], d["dir"], d["bars_seen"]))
print()

print("=" * 80)
print("OWNER'S DATES - pivot actually used for each FS")
print("=" * 80)
for day in ("2025-07-20", "2024-07-16", "2025-07-09", "2025-07-21"):
    rows = [d for d in DECL if d["t"][:10] == day]
    print()
    print("  %s   (%d FS)" % (day, len(rows)))
    for d in rows:
        tp = d.get("tgt_px")
        print("     FS %s  dir=%-4s  pivot px=%s  sealed %s"
              % (d["t"][11:16], d["dir"], tp, d.get("tgt_time")))
        ti = d.get("tgt_idx")
        if ti is not None and 0 <= ti < len(candles):
            c = candles[ti]
            print("        pivot candle %s  H=%-10.1f L=%-10.1f" % (c["date"][:16], c["high"], c["low"]))

(HERE / "_fs_targets.json").write_text(json.dumps(DECL, indent=1, default=str), encoding="utf-8")
