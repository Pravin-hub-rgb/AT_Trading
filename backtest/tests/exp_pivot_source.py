"""
Why is the RETRO stop 42921.47 when price reached 42932.07 before the entry?

The two rules are not two ways of computing the same quantity. They return
different quantities:

  retro   sig["swing_start_px"]  - a structural pivot from the swing
  causal  _csh[i]                - the actual highest price seen to the bar

For a short the stop must sit above the highest price that has occurred since
the position was opened. If retro's number is BELOW a price that was already
reached before the entry, retro is not placing the stop where a live trader
would have placed it.

This prints, for the 18 Jan 2024 13:30 short:
  - the swing's declared start price and the bar it sits on
  - the highest price from the forming swing's start to the entry bar, and when
  - whether that swing start is the swing's own high, or some other bar

Run: python -u exp_pivot_source.py
"""
import sys, os, pickle, types, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from src.btc.btc_engine import _collect_signals

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15, sw15 = d["c15"], d["sw15"]


def i_of(mm):
    for k, c in enumerate(c15):
        if str(c["date"])[:16] == mm:
            return k
    return -1


ENTRY = i_of("2024-01-18 13:30")
sigs = _collect_signals(sw15, "decisive", skip_first=True,
                        selection="stream", candles=c15)
sig = [s for s in sigs if str(s["bar"])[:16] == "2024-01-18 13:30"][0]
sn = int(sig["swing_no"])
sw = [s for s in sw15 if int(s.get("swing_index", -1)) == sn][0]
seg = sw["seg"]

print("=" * 76)
print("18 Jan 2024 13:30 SHORT - where does each number come from?")
print("=" * 76)
print()
print("  swing #%d  dir=%s" % (sn, sw["dir"]))
print("    seg  start %s @ %s" % (c15[seg["start_idx"]]["date"][:16],
                                   c15[seg["start_idx"]]["date"][:16]))
print("    seg  end   %s" % c15[seg["end_idx"]]["date"][:16])
print("    confirmed   %s" % c15[int(sw["confirmed_at_idx"])]["date"][:16])
print()
print("  RETRO pivot (sig['swing_start_px']) = %.2f" % float(sig["swing_start_px"]))
print("    is that the price AT seg start_idx?   %s"
      % (abs(float(sig["swing_start_px"]) - float(c15[seg["start_idx"]]["close"])) < 0.01))
print("    is that the HIGH of the start candle?  %s"
      % (abs(float(sig["swing_start_px"]) - float(c15[seg["start_idx"]]["high"])) < 0.01))
print("    is that the LOW  of the start candle?  %s"
      % (abs(float(sig["swing_start_px"]) - float(c15[seg["start_idx"]]["low"])) < 0.01))
print()
print("  swing's declared end bar %s  high=%.2f"
      % (c15[seg["end_idx"]]["date"][:16], float(c15[seg["end_idx"]]["high"])))

fs = seg["start_idx"]          # the swing's OWN first bar
print("  swing's own first bar = %s" % c15[fs]["date"][:16])
print("  entry bar             = %s" % c15[ENTRY]["date"][:16])
print("  bars in the swing by entry time: %d" % (ENTRY - fs + 1))
print()
print("  every bar in the swing up to the entry:")
for k in range(fs, ENTRY + 1):
    mark = "  <-- ENTRY" if k == ENTRY else ""
    print("    %-16s  O %-10.2f  H %-10.2f  L %-10.2f  C %-10.2f%s"
          % (c15[k]["date"][:16], float(c15[k]["open"]), float(c15[k]["high"]),
             float(c15[k]["low"]), float(c15[k]["close"]), mark))
hi_v, hi_k = max(((float(c15[k]["high"]), k) for k in range(fs, ENTRY + 1)))
print()
print("  highest high in the swing up to entry : %.2f  (at %s)"
      % (hi_v, c15[hi_k]["date"][:16]))
print("  high of the swing's FIRST candle      : %.2f" % float(c15[fs]["high"]))
print()
print()
print("  entry bar  %s  close %.2f  high %.2f"
      % (c15[ENTRY]["date"][:16], float(c15[ENTRY]["close"]),
         float(c15[ENTRY]["high"])))
print()
print("=" * 76)
print("THE COMPARISON THAT MATTERS")
print("=" * 76)
p = float(sig["swing_start_px"])
print("  retro pivot  %.2f" % p)
print("  forming high %.2f  (highest price actually seen before entry)" % hi_v)
print("  difference   %+.2f" % (p - hi_v))
print()
if p < hi_v:
    print("  The retro pivot is BELOW a price that was already reached before the")
    print("  position existed. A live trader watching those bars would have put the")
    print("  stop above %.2f. Retro puts it %.2f lower, which makes the risk smaller"
          % (hi_v, hi_v - p))
    print("  and therefore the R on a winner larger. The trade behaves identically -")
    print("  it exits at the same price either way - so this is arithmetic, not a")
    print("  better trade.")
