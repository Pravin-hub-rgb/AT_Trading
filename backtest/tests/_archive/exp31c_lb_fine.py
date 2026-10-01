"""Exp 31c — fine validation: B3-OPT+halt6 cd10 with lb=40 / lb=50 vs base."""
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
BP["chop_thresh"] = 55.0
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
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    for tag, lb in [("B3-OPT+halt6 lb=14 (base)", 0), ("lb=40", 40), ("lb=50", 50)]:
        kw = {} if lb == 0 else {"exp31_lb": lb}
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **{**BP, **H, **kw})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        print("  %-28s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
              % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["h1"], s["h2"]))
        print("      per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})


if __name__ == "__main__":
    main()
