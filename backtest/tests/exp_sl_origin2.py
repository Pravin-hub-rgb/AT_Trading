"""
Second look from the chart: 30 Nov 2023 23:45, a +18.61R winner under RETRO
that becomes a -1.00R stop-out under CAUSAL. Largest single gap left.

Reader's reading of the chart:
  prev swing ended  30 Nov 19:30
  next swing starts 30 Nov 19:45
  lowest from there to the entry is the 21:15 candle
  the stop as drawn sits at 22:45, which is further back than that
  therefore the stop is still reading a candle that belongs to the finished leg

Prints the swing boundaries, the raw running low from the confirmed-swing reset,
where that low actually sits, and the forming-swing low - so the claim is
either confirmed or not.

Run: python -u exp_sl_origin2.py
"""
import sys, os, pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15, sw15 = d["c15"], d["sw15"]
n = len(c15)


def i_of(mm):
    for k, c in enumerate(c15):
        if str(c["date"])[:16] == mm:
            return k
    return -1


T = i_of("2023-11-30 23:45")
print("entry bar %d  %s" % (T, c15[T]["date"][:16]))
print()

print("=" * 78)
print("SWING BOUNDARIES AROUND THE ENTRY")
print("=" * 78)
for s in sw15:
    si = int(s.get("seg", {}).get("start_idx", -1))
    ei = int(s.get("seg", {}).get("end_idx", -1))
    ca = int(s.get("confirmed_at_idx", -1))
    if not (-40 <= ei <= T + 5) and not (-40 <= si <= T + 5):
        continue
    print("  #%-5d %-4s seg %s -> %s   confirmed@%s"
          % (s.get("swing_index", -1), s.get("dir"),
             c15[si]["date"][:16] if si >= 0 else "?",
             c15[ei]["date"][:16] if ei >= 0 else "?",
             c15[ca]["date"][:16] if ca >= 0 else "?"))

print()
print("=" * 78)
print("THE TWO LOWS")
print("=" * 78)

# what the engine now does: reset to seg_end + 1 on confirm
_conf = []
for s in sw15:
    ca = int(s.get("confirmed_at_idx", -1))
    ei = int(s.get("seg", {}).get("end_idx", -1))
    if ca >= 0 and ei >= 0:
        _conf.append((ca, ei))
_conf.sort()
_lo = float(c15[0]["low"])
_ce = 0
_run = [0.0] * n
for ci in range(n):
    while _ce < len(_conf) and _conf[_ce][0] <= ci:
        _cref = _conf[_ce][1] + 1
        _ce += 1
        if _cref <= ci and _cref < n:
            _lo = float(c15[_cref]["low"])
    if float(c15[ci]["low"]) < _lo:
        _lo = float(c15[ci]["low"])
    _run[ci] = _lo

_j = _run.index(_run[T])
print("  ENGINE running low at entry : %.2f   (that low is at %s)"
      % (_run[T], c15[_j]["date"][:16]))

ca, s = None, None
for x in sw15:
    xc = int(x.get("confirmed_at_idx", -1))
    if 0 <= xc <= T and (ca is None or xc > ca):
        ca, s = xc, x
ei = int(s["seg"]["end_idx"])
print("  last confirmed swing        : #%s  confirmed@%s  seg_end %s"
      % (s.get("swing_index"), c15[ca]["date"][:16], c15[ei]["date"][:16]))
print()
print("  reset point the engine used : %s   (= seg_end + 1)"
      % c15[ei + 1]["date"][:16] if ei + 1 < n else "?")
print()
fs = ei + 1
lows = [(float(c15[k]["low"]), k) for k in range(fs, T + 1)]
lo_v, lo_k = min(lows)
print("  FORMING low from %s to entry : %.2f   (at %s)"
      % (c15[fs]["date"][:16], lo_v, c15[lo_k]["date"][:16]))
print()
print("  reader says the low should be the 21:15 candle:")
k2115 = i_of("2023-11-30 21:15")
print("    21:15 low = %.2f" % float(c15[k2115]["low"]))
print()
print()
print("=" * 78)
print("WHY IS THE ENGINE LOW 37633.20 WHEN 21:15 = 37515.50?")
print("=" * 78)
# print the running low at every bar from the reset to the entry
print("  bar          low        running  new?")
prev_run = None
for k in range(fs, T + 1):
    print("  %-12s  low=%-10.2f  running=%-10.2f"
          % (c15[k]["date"][:16], float(c15[k]["low"]), _run[k]))
    prev_run = _run[k]

print()
# find where the 21:15 low should have been taken
k2115 = i_of("2023-11-30 21:15")
print("  21:15 bar index = %d" % k2115)
print("  21:15 low      = %.2f" % float(c15[k2115]["low"]))
print("  _run[21:15]    = %.2f   <-- what the engine had by then" % _run[k2115])
print("  _run[entry]    = %.2f" % _run[T])
print()
if _run[k2115] > float(c15[k2115]["low"]) + 1e-6:
    print("  >>> BUG: the 21:15 low was never captured. min-tracking failed.")
else:
    print("  21:15 low WAS captured. The 37633.20 comes from somewhere else.")
    for k in range(fs, n):
        if abs(float(c15[k]["low"]) - 37633.20) < 0.01:
            print("    found at bar %d  %s" % (k, c15[k]["date"][:16]))
            if k > T:
                print("    ^^^ THIS IS AFTER THE ENTRY - reading a future bar!")
            break

