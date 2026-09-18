"""CRAZE: halt=6 fine-fill check (one param change on the shipped engine)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import stats, BASE, load_candles, _compute_swings, SWING, INSTRUMENT
from engine.v18_params import get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_pv = dict(get_v18_params(INSTRUMENT)); _pv.update(V18_ENGINE)


def net_of(tr):
    c2, _ = _trade_costs(tr, _pv["fee_pct"], 0.0,
                         _pv["entry_slip_pct"], _pv["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
print("loading fine 1m...")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
kw6 = dict(BASE); kw6["max_consecutive_losses"] = 6
for tag, kw in [("halt=3 anchor", BASE), ("halt=6", kw6)]:
    r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine, **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    print("  %-13s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  streak %2d  H1 %+7.1f H2 %+7.1f"
          % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["mx"], s["h1"], s["h2"]))
