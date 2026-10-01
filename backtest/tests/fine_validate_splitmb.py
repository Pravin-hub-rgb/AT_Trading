"""CRAZE fine-fill validation for Exp 11 split-mb winners (trail=75, trail=100).

Reuses the identity-gated harness. Fine 1m exits + net costs.
Also: per-month 2023 breakdown for trail=100 (concentration check).
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE,
                                    load_candles, _compute_swings,
                                    SWING, INSTRUMENT, MB15)
from engine.v18_params import get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _trade_costs

_pv = dict(get_v18_params(INSTRUMENT)); _pv.update(V18_ENGINE)


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _pv["fee_pct"], 0.0,
                         _pv["entry_slip_pct"], _pv["exit_slip_pct"])
    return sum(rs) - c2, c2


def months(tr, year):
    mo = defaultdict(float)
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        if d.startswith(year):
            mo[d[:7]] += float(t["r_multiple"])
    return dict(sorted(mo.items()))


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw100 = _compute_swings(f15, "continuous", min_bars=100)
    sw75 = _compute_swings(f15, "continuous", min_bars=75)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print("loading fine 1m...")
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]),
                         symbol=INSTRUMENT)
    print("  %d fine bars" % len(fine))
    sim_mb = build_module()

    print("\n=== FINE-FILL VALIDATION ===")
    runs = [("anchor e50/t50", sw15, sw15), ("e50/t75", sw15, sw75),
            ("e50/t100", sw15, sw100)]
    results = {}
    for tag, se, st in runs:
        if st is not sw15:
            r = sim_mb(c1h, sw1h, c15, se, fine_ltf=fine, swings_trail=st, **BASE)
        else:
            r = sim_mb(c1h, sw1h, c15, se, fine_ltf=fine, **BASE)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        results[tag] = (tr, s)
        net, cost = net_of(tr)
        print("  %-14s %4dt gross %+8.1f  NET %+8.1f (cost %+.1f)  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
              % (tag, s["n"], s["gross"], net, cost, s["wr"], s["dd"], s["h1"], s["h2"]))

    print("\n=== trail=100 coarse: 2023 per-month (concentration check) ===")
    r = sim_mb(c1h, sw15, c15, sw15, fine_ltf=[], swings_trail=sw100, **BASE)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    mo = months(tr, "2023")
    for k in sorted(mo):
        print("    %s %+8.1f" % (k, mo[k]))

    print("\n=== trail=100 fine: 2023 + 2024 per-month ===")
    tr100 = results["e50/t100"][0]
    for y in ("2023", "2024"):
        mo = months(tr100, y)
        print("  %s: %s" % (y, {k: round(v, 1) for k, v in sorted(mo.items())}))


if __name__ == "__main__":
    main()
