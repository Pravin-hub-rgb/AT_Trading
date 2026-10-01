"""Exp 32b — (a) trail-mb=80 coarse probe (monotonicity check at chop52/lb60);
(b) fine NET: base (55,50,trail50) vs (55,50,trail65) vs (52,60,trail65)."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP = dict(BASE)
BP["chop_thresh"] = 58.0
H = dict(b3_k=8, b3_mode="close", exp_persist=2, max_consecutive_losses=6)
_g = _gvp(INSTRUMENT)


def net_of(tr):
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    tch = {mb: _compute_swings(f15, "continuous", min_bars=mb)
           for mb in (SWING["min_bars_15m"], 65, 80)}
    sim = build_module()
    print("=== (a) trail-mb coarse probe at chop52/lb60 ===")
    for mb in (SWING["min_bars_15m"], 65, 80):
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=[],
                **{**BP, **H, "chop_thresh": 52.0, "exp31_lb": 60,
                   "swings_trail": tch[mb]})
        s = stats(r["ltf_trades"])
        print("  trail-mb=%-3d %4dt %+8.1fR  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
              % (mb, s["n"], s["gross"], s["wr"], s["dd"], s["h1"], s["h2"]))
    print("\n=== (b) fine NET ===")
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    for tag, chop, lb, tmb in [
            ("base (55,50,trail50)", 55.0, 50, SWING["min_bars_15m"]),
            ("(55,50,trail65)", 55.0, 50, 65),
            ("(52,60,trail65)", 52.0, 60, 65)]:
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine,
                **{**BP, **H, "chop_thresh": chop, "exp31_lb": lb,
                   "swings_trail": tch[tmb]})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        print("  %-22s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
              % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["h1"], s["h2"]))
        print("      per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})
    print("\n(exp32b done)")


if __name__ == "__main__":
    main()
