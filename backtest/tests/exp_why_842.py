"""
Two questions, one run.

  Q1  Why 842 trades instead of 500?
  Q2  Why TRAIL 0 when the harness has 741 trail exits?

The frontend calls the route, which builds swings with
btc_swing.compute_btc_swings. The champion harness builds them with
tc._compute_swings. If those two disagree on swing count, confirmed_at_idx or
the dir convention, both symptoms follow from the same cause: trail events never
arm, and the signal stream is a different length.

This loads the data exactly the way the route does, builds both, and runs the
committed v19 engine on each. Everything is printed; nothing is asserted.

Run: python -u exp_why_842.py
"""
import sys, inspect
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from src.btc.btc_swing import compute_btc_swings
from src.btc.btc_engine import _trail_events, _collect_signals, CandleStore
from src.btc.btc_routes import _load_window
from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
import test_experiments_craze as tc

MIN_BARS = 50

res = _load_window("15m", None, "BTCUSDT_BYBIT")
(candles, flow), err = res
print("candles from _load_window: %d" % len(candles))

hres = _load_window("1h", None, "BTCUSDT_BYBIT")
(hcandles, hflow), herr = hres
print("1h candles: %d" % len(hcandles))
print()

# ---------------------------------------------------------------- swings
cap = max(1, len(flow) // 2)
B = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=cap)
H = tc._compute_swings(flow, "continuous", min_bars=MIN_BARS)
BH = compute_btc_swings(hflow, opts={"minBars": 10}, max_swings=max(1, len(hflow) // 2))
HH = tc._compute_swings(hflow, "continuous", min_bars=10)


def describe(name, sw):
    if not sw:
        print("  %-26s EMPTY" % name)
        return
    conf = [s for s in sw if s.get("confirmed_at_idx") is not None
            and int(s.get("confirmed_at_idx", -1)) >= 0]
    dirs = Counter(str(s.get("dir")) for s in sw)
    print("  %-26s n=%-6d conf>=0: %-6d dirs=%r"
          % (name, len(sw), len(conf), dict(dirs)))
    print("  %-26s keys=%s" % ("", sorted(sw[0].keys())))


print("=" * 78)
print("SWINGS: 15m @ min_bars=50")
print("=" * 78)
describe("backend compute_btc_swings", B)
describe("harness tc._compute_swings", H)
print()
print("=" * 78)
print("SWINGS: 1h @ min_bars=10")
print("=" * 78)
describe("backend compute_btc_swings", BH)
describe("harness tc._compute_swings", HH)
print()

print("=" * 78)
print("TRAIL EVENTS")
print("=" * 78)
for name, sw in (("backend 15m", B), ("harness 15m", H),
                 ("backend 1h", BH), ("harness 1h", HH)):
    if not sw:
        print("  %-14s EMPTY" % name)
        continue
    lo = len(_trail_events(sw, 1))
    sh = len(_trail_events(sw, -1))
    print("  %-14s long=%-6d short=%-6d total=%d" % (name, lo, sh, lo + sh))
print()

print("=" * 78)
print("SIGNALS  (what the entry loop actually consumes)")
print("=" * 78)
for name, sw in (("backend 15m", B), ("harness 15m", H)):
    if not sw:
        print("  %-14s no swings" % name)
        continue
    sig = _collect_signals(sw, "decisive", skip_first=True,
                           selection="stream", candles=candles)
    print("  %-14s %d signals" % (name, len(sig)))
    if sig:
        n_sl = sum(1 for s in sig if "swing_start_px" in s)
        print("  %-14s with swing_start_px: %d" % ("", n_sl))
print()

# ---------------------------------------------------------------- engine
print("=" * 78)
print("V19 ENGINE on each swing set  (IS, retro)")
print("=" * 78)
import types
SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
mod = types.ModuleType("probe")
mod.__file__ = "probe.py"
exec(compile(SRC, "probe.py", "exec"), mod.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(mod.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

import pickle, os
with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
fine = d["fine"]

for name, sw15, sw1h, c15, c1h in (
    ("harness swings", H, HH, d["c15"], d["c1h"]),
    ("backend swings", B, BH, candles, hcandles),
):
    if not sw15 or not sw1h:
        print("  %-16s skipped (empty swings)" % name)
        continue
    r = mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine, **pr)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    oc = Counter(t.get("outcome") for t in tr)
    print("  %-16s n=%-5d net=%+8.2fR  outcomes=%r"
          % (name, len(tr), net_r(tr), dict(oc)))
