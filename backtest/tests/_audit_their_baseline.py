"""AUDIT: their harness baseline vs the shipped v18 engine — trade-by-trade diff.

Their doc claims baseline = 351t / +238.0R and "all simulation logic identical".
The shipped engine gives 340t / +225.3R on the same data. 11 trades and +12.7R
of divergence BEFORE any experiment = their entire table is measured on a
different engine. This audit finds where they diverge.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments import load_window, simulate_v18_experiments
from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

print("loading data + swings...")
c1h_t, f1h_t = load_window("1h")
c15_t, f15_t = load_window("15m")
sw15 = _compute_swings(f15_t, "continuous", min_bars=SWING["min_bars_15m"])
sw1h = _compute_swings(f1h_t, "continuous", min_bars=SWING["min_bars_1h"])

from src.btc.btc_routes import _load_fine_1m
fine = _load_fine_1m(min(c1h_t[0]["ts"], c15_t[0]["ts"]),
                     max(c1h_t[-1]["ts"], c15_t[-1]["ts"]), symbol="BTCUSDT_BYBIT")
print("fine bars: %d" % len(fine))

print("running THEIR harness baseline (WITH fine, their exact invocation)...")
theirs = simulate_v18_experiments(c1h_t, sw1h, c15_t, sw15, fine)
tt = theirs["ltf_trades"] if isinstance(theirs, dict) else theirs
print("  their baseline: %dt  R=%+.2f" % (len(tt), sum(float(x["r_multiple"]) for x in tt)))

print("running SHIPPED engine (get_v18_params, WITH fine)...")
_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
(c15, f15), (c1h, f1h) = load_candles()
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
ts = r["ltf_trades"] if isinstance(r, dict) else r
print("  shipped:        %dt  R=%+.2f" % (len(ts), sum(float(x["r_multiple"]) for x in ts)))

# ---- diff by entry_ts ----
by_ts_s = {int(x["entry_ts"]): x for x in ts}
by_ts_t = {int(x["entry_ts"]): x for x in tt}
only_ship = [k for k in by_ts_s if k not in by_ts_t]
only_their = [k for k in by_ts_t if k not in by_ts_s]
common = [k for k in by_ts_s if k in by_ts_t]
print("\ncommon entries: %d | only-shipped: %d | only-theirs: %d"
      % (len(common), len(only_ship), len(only_their)))
diff_r = [(k, by_ts_s[k]["r_multiple"], by_ts_t[k]["r_multiple"])
          for k in common if abs(float(by_ts_s[k]["r_multiple"]) - float(by_ts_t[k]["r_multiple"])) > 1e-6]
print("common with different R: %d" % len(diff_r))
for k, a, b in diff_r[:10]:
    print("  ts=%d ship r=%s | their r=%s | %s" % (k, a, b, by_ts_s[k]["entry_date"]))
for k in only_ship[:6]:
    x = by_ts_s[k]
    print("  only-shipped: %s %s r=%s" % (x["entry_date"], x["dir"], x["r_multiple"]))
for k in only_their[:6]:
    x = by_ts_t[k]
    print("  only-theirs : %s %s r=%s" % (x["entry_date"], x["dir"], x["r_multiple"]))
print("(audit done)")
