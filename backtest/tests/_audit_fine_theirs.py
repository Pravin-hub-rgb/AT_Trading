"""AUDIT fine: OPTIMAL combo + multi-LTF alone on the SHIPPED engine (fine 1m)."""
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
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
sim = build_module()
print("loading fine 1m...")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
print("  %d fine bars" % len(fine))

print("=== FINE: their pieces on shipped engine ===")
print("  references: v18 340t NET +182.3 | their claims: OPTIMAL 515t NET +322.5")
for tag, hflags, pover, s1h_use in [
        ("OPTIMAL combo", dict(exp_persist=2, exp_mltf=True),
         dict(chop_thresh=55.0, cooldown_bars=0), sw1h10),
        ("multi-LTF alone", dict(exp_mltf=True), dict(), sw1h),
        ("SAFE combo", dict(exp_persist=2), dict(chop_thresh=55.0), sw1h10)]:
    r = sim(c1h, s1h_use, c15, sw15, fine_ltf=fine, **{**BASE, **pover, **hflags})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    print("  %-16s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
          % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["h1"], s["h2"]))
    print("      per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})
print("(fine audit done)")
