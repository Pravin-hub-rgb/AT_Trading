"""Exp 20 Phase 1 — close-confirmed initial SL counterfactual (read-only study).

M1 (Exp 19): 56% of SL deaths are wick-only (no close beyond SL). Would a
close-based INITIAL stop (exit only on CLOSE beyond SL, fill at that close)
have helped? Counterfactual per trade:
- SL losses: scan bars i+1..j+W (W=250) for first close beyond SL. Survived
  window -> indicative R at window end (real trail would exit inside window).
  Close-through -> fill at that close (often worse than -1R).
- winners + trail-negatives: killed early if a close-beyond-initial-SL occurs
  before their actual exit (CONSERVATIVE BOUND: ignores trail ratchet lifting
  the stop — overstates kills; stated in output).
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
trades = r["ltf_trades"] if isinstance(r, dict) else r
close = [float(c["close"]) for c in c15]
lo15 = [float(c["low"]) for c in c15]
hi15 = [float(c["high"]) for c in c15]
n = len(c15)
W = 250  # post-death evaluation window (~2.6 days)

def close_through_bar(i, j_end, d, sl):
    """First bar in (i, j_end] with CLOSE beyond sl (long: close < sl)."""
    for b in range(i + 1, min(j_end, n - 1) + 1):
        if (d == 1 and close[b] < sl) or (d == -1 and close[b] > sl):
            return b
    return None

agg = defaultdict(lambda: [0, 0.0])
res = dict(saved=0, saved_R=0.0, worse=0, worse_R=0.0, killed=0, killed_R=0.0,
           unaffected=0)
net = 0.0
for t in trades:
    i = int(t["entry_idx"]); j = int(t["exit_idx"])
    d = 1 if t["dir"] == "long" else -1
    sl = float(t["sl"]); entry = float(t["entry_price"]); rv = float(t["r_multiple"])
    risk = abs(entry - sl)
    if risk <= 0: continue
    yr = (t.get("entry_date") or "")[:4]
    b = close_through_bar(i, (j + W) if t["outcome"] == "sl" else j, d, sl)
    if t["outcome"] == "sl":
        if b is None:  # survived the close-based stop past the original death
            r_cf = d * (close[min(j + W, n - 1)] - entry) / risk
            res["saved"] += 1; res["saved_R"] += r_cf
        else:
            r_cf = d * (close[b] - entry) / risk
            res["worse"] += 1; res["worse_R"] += r_cf
        a = agg[yr]; a[0] += 1; a[1] += r_cf - rv
        net += r_cf - rv
    else:  # winners + trail-negatives
        if b is not None:
            r_cf = d * (close[b] - entry) / risk
            res["killed"] += 1; res["killed_R"] += r_cf
            a = agg[yr]; a[0] += 1; a[1] += r_cf - rv
            net += r_cf - rv
        else:
            res["unaffected"] += 1

print("=== EXP 20 Phase 1: close-confirmed initial SL (coarse, rough) ===")
print("SL losses (132): saved %d (window R %+.1f) | close-through %d (R %+.1f)"
      % (res["saved"], res["saved_R"], res["worse"], res["worse_R"]))
print("  -> wick-only deaths were 74; close-based saves those that never close through")
print("winners+trail-negs: killed early %d (R %+.1f) | unaffected %d"
      % (res["killed"], res["killed_R"], res["unaffected"]))
print("  NOTE: killed count is an UPPER BOUND (ignores trail ratchet lifting")
print("  the stop before the close-through; Phase-2 walk would refine).")
print("ROUGH NET: %+.1fR" % net)
for y in sorted(agg):
    a = agg[y]
    print("  %s: affected=%d deltaR=%+.1f" % (y, a[0], a[1]))
print("(exp20 done)")
