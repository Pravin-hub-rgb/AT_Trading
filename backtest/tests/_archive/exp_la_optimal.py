"""Test best autopsy filters on OPTIMAL config to check generalization."""
import sys, time, json, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, BASE, load_candles,
    _compute_swings, SWING, MB15, INSTRUMENT, stats)
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _trade_costs, _load_fine_1m


def _net(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return sum(rs) - c2 - f


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_module()
    g = _gvp(INSTRUMENT)

    # OPTIMAL config
    OPT = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=10)

    print("Running OPTIMAL (mltf cd10) with fine fills...")
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **{**BASE, **OPT})
    tr = r["ltf_trades"]
    ivs = r["intervals"]
    iv_starts = [iv[0] for iv in ivs]
    base_net = _net(tr, g)
    base_s = stats(tr)
    print(f"OPTIMAL baseline: {base_s['n']}t, NET {base_net:+.1f}R, WR {base_s['wr']:.1f}%, DD {base_s['dd']:.1f}")

    # Compute window ages and bars
    for t in tr:
        ts = t["entry_ts"]
        idx = bisect.bisect_right(iv_starts, ts) - 1
        t["_wage_h"] = round((ts - ivs[idx][0]) / 3600.0, 1) if 0 <= idx < len(ivs) else None
        t["_bars"] = t.get("bars_held", 0)

    # Test best filters
    filters = [
        ("skip 12-24h", lambda t: t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24),
        ("skip <12 bars", lambda t: t["_bars"] >= 12),
        ("skip <8 bars", lambda t: t["_bars"] >= 8),
        ("skip 12-24h + skip <8 bars",
         lambda t: (t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24) and t["_bars"] >= 8),
    ]

    print(f"\n{'Filter':40s} {'Kept':>5s} {'Rem':>5s} {'NET':>8s} {'Delta':>8s}")
    print("-" * 70)
    for label, fn in filters:
        kept = [t for t in tr if fn(t)]
        rem = [t for t in tr if not fn(t)]
        net = _net(kept, g)
        delta = net - base_net
        print(f"  {label:38s} {len(kept):5d} {len(rem):5d} {net:+8.1f} {delta:+8.1f}")

    # Also test w24 for reference
    print("\n  (reference: w24 on OPT-cd10)")
    r24 = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **{**BASE, **OPT, "exp_wage_h": 24})
    tr24 = r24["ltf_trades"]
    net24 = _net(tr24, g)
    print(f"  w24: {len(tr24)}t NET {net24:+.1f}R (delta {net24-base_net:+.1f})")

    print(f"\n(optimal filters done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()