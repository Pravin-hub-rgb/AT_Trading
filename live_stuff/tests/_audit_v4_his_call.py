"""AUDIT v4 — the shipped engine with HIS EXACT call (only btc_routes params).

His claim: simulate_htf_ltf_streak_halt() with btc_routes 914-941 params
gives 351t/+238.0R. My runs give 340t/+251.6R. This script runs the shipped
engine with EXACTLY his keyword set (no window_end, no atr kwargs, no htf_rr)
on his exact data loading (test_experiments.load_window), and prints the result.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments import load_window, SYMBOL
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
print("1h: %d | 15m: %d" % (len(c1h), len(c15)))
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
print("swings: 1h=%d 15m=%d" % (len(sw1h), len(sw15)))
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
print("fine: %d" % len(fine))

r = simulate_htf_ltf_streak_halt(
    candles_htf=c1h,
    swings_htf=sw1h,
    candles_ltf=c15,
    swings_ltf=sw15,
    fine_ltf=fine,
    sl_buf_atr=0.01,
    ext_stop_r=1.5,
    mode="b2_vs_flip_chop",
    chop_thresh=58.0,
    cooldown_bars=10,
    max_consecutive_losses=3,
)
ts = r["ltf_trades"] if isinstance(r, dict) else r
print("RESULT: %dt  R=%+.2f" % (len(ts), sum(float(x["r_multiple"]) for x in ts)))
from collections import defaultdict
py = defaultdict(float)
for x in ts:
    py[(x.get("exit_date") or x.get("entry_date") or "")[:4]] += float(x["r_multiple"])
print("per-year: %s" % {k: round(v, 1) for k, v in sorted(py.items())})
print("(audit v4 done)")
