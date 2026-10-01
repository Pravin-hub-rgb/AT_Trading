import sys, pickle
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
from src.btc.btc_engine import _collect_signals
with open(Path(__import__("os").environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
print("TEST 1: stream path, candles=None (the sweep_pref_fs.py case)")
try:
    s1 = _collect_signals(d["sw15"], "decisive", skip_first=True, selection="stream", candles=None)
    print("  PASS - no crash. signals=%d" % len(s1))
    print("  sample swing_start_px = %.2f  (should be seg_start, not the leg extreme)"
          % float(s1[0]["swing_start_px"]))
except TypeError as e:
    print("  FAIL - TypeError: %s" % e)
except Exception as e:
    print("  FAIL - %s: %s" % (type(e).__name__, e))
print()
print("TEST 2: stream path, candles present (normal case) - must be unchanged")
s2 = _collect_signals(d["sw15"], "decisive", skip_first=True, selection="stream", candles=d["c15"])
print("  signals=%d  first swing_start_px=%.2f" % (len(s2), float(s2[0]["swing_start_px"])))
print()
print("TEST 3: final path, candles=None")
try:
    s3 = _collect_signals(d["sw15"], "decisive", skip_first=True, selection="final", candles=None)
    print("  PASS - no crash. signals=%d" % len(s3))
except TypeError as e:
    print("  FAIL - TypeError: %s" % e)
except Exception as e:
    print("  FAIL - %s: %s" % (type(e).__name__, e))
