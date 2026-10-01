"""Exp 23 — COMBO: B3 k8-close entry + halt=6 (both param-level, composable).

Usage: python exp23_combo.py          -> coarse grid vs all baselines
       python exp23_combo.py --fine   -> fine-fill NET for the combo only
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE,
                                    load_candles, _compute_swings, SWING,
                                    INSTRUMENT, MB15)
from engine.v18_params import get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs

_pv = dict(get_v18_params(INSTRUMENT)); _pv.update(V18_ENGINE)


def net_of(tr):
    c2, _ = _trade_costs(tr, _pv["fee_pct"], 0.0,
                         _pv["entry_slip_pct"], _pv["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


COMBO = dict(b3_k=8, b3_mode="close", max_consecutive_losses=6)

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sim = build_module()

if "--fine" in sys.argv:
    from src.btc.btc_routes import _load_fine_1m
    print("loading fine 1m...")
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **COMBO})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    print("COMBO fine: %dt gross %+.1f NET %+.1f WR %.1f%% DD %.1f streak %d H1 %+.1f H2 %+.1f"
          % (s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["mx"], s["h1"], s["h2"]))
    print("  per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})
    print("  references: v18 340t NET +182.3 | B3 alone 206t NET +278.6 | halt6 alone 369t NET +187.9")
    sys.exit(0)

# ---- coarse ----
print("=== EXP 23 COMBO (coarse) ===")
runs = [("v18 anchor (halt3, no B3)", dict()),
        ("B3 k8 close alone", dict(b3_k=8, b3_mode="close")),
        ("halt=6 alone", dict(max_consecutive_losses=6)),
        ("COMBO B3+halt6", COMBO)]
for tag, over in runs:
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **{**BASE, **over})
    show(tag, stats(r["ltf_trades"] if isinstance(r, dict) else r))
