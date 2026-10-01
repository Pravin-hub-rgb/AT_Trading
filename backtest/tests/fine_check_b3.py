"""CRAZE: fine-fill validation for B3 winners (k8 close, k8 wick, k4 close)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE,
                                    load_candles, _compute_swings, SWING,
                                    INSTRUMENT, MB15)
from engine.v18_params import get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _trade_costs

_pv = dict(get_v18_params(INSTRUMENT)); _pv.update(V18_ENGINE)


def net_of(tr):
    c2, _ = _trade_costs(tr, _pv["fee_pct"], 0.0,
                         _pv["entry_slip_pct"], _pv["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sim = build_module()
print("loading fine 1m...")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
print("  %d fine bars" % len(fine))

print("=== B3 FINE-FILL (anchor fine known: 340t / +251.6 gross / +182.3 net / H1 +101.0 / H2 +150.6) ===")
for tag, kw in [("k8 close", dict(b3_k=8, b3_mode="close")),
                ("k8 wick", dict(b3_k=8, b3_mode="wick")),
                ("k4 close", dict(b3_k=4, b3_mode="close"))]:
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **kw})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    print("  %-9s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  streak %2d  H1 %+7.1f H2 %+7.1f"
          % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["mx"], s["h1"], s["h2"]))
    print("           per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})
