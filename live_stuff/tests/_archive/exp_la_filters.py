"""EXP LA Filters: Test all filters from loss autopsy.

Theory: The loss autopsy identified specific toxic trade subsets.
This script tests whether removing them improves NET.

Filters:
  LA1: Window age zone filter (skip 12-24h toxic zone)
  LA2: FLIP preference (skip B2 signals)
  LA3: Fast death filter (skip trades that exit <5 bars)
  LA4: Combined filters

Run:  python live_stuff/tests/exp_la_filters.py
Output: stdout + _la_filters_results.json
"""
import sys, time, json, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
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


def compute_window_age(trade, intervals, iv_starts):
    ts = trade["entry_ts"]
    idx = bisect.bisect_right(iv_starts, ts) - 1
    if 0 <= idx < len(intervals):
        return round((ts - intervals[idx][0]) / 3600.0, 1)
    return None


def run_filter(trades, g, intervals, iv_starts, filter_fn, label):
    kept = [t for t in trades if filter_fn(t)]
    removed = [t for t in trades if not filter_fn(t)]
    net = _net(kept, g)
    rem_r = sum(float(t["r_multiple"]) for t in removed)
    rem_wr = 100.0 * len([t for t in removed if float(t["r_multiple"]) > 0]) / max(len(removed), 1)
    return {
        "label": label,
        "kept": len(kept),
        "removed": len(removed),
        "net": round(net, 1),
        "removed_r": round(rem_r, 1),
        "removed_wr": round(rem_wr, 1),
    }


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_module()
    g = _gvp(INSTRUMENT)

    print("Running baseline with fine fills...")
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
    tr = r["ltf_trades"]
    ivs = r["intervals"]
    iv_starts = [iv[0] for iv in ivs]
    base_net = _net(tr, g)
    base_s = stats(tr)
    print(f"Baseline: {base_s['n']}t, gross {base_s['gross']:+.1f}R, NET {base_net:+.1f}R, "
          f"WR {base_s['wr']:.1f}%, DD {base_s['dd']:.1f}")

    # Compute window ages
    for t in tr:
        t["_wage_h"] = compute_window_age(t, ivs, iv_starts)
        t["_bars"] = t.get("bars_held", 0)

    results = []

    # === LA1: WINDOW AGE ZONE FILTER ===
    print("\n=== LA1: WINDOW AGE ZONE FILTER ===")
    zones = [
        ("skip <12h", lambda t: t["_wage_h"] is None or t["_wage_h"] >= 12),
        ("skip 12-24h", lambda t: t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24),
        ("skip <24h (w24)", lambda t: t["_wage_h"] is None or t["_wage_h"] >= 24),
        ("skip 24-48h", lambda t: t["_wage_h"] is None or t["_wage_h"] < 24 or t["_wage_h"] >= 48),
        ("keep only 0-6h", lambda t: t["_wage_h"] is not None and t["_wage_h"] <= 6),
        ("keep only 48h+", lambda t: t["_wage_h"] is not None and t["_wage_h"] > 48),
    ]
    for label, fn in zones:
        res = run_filter(tr, g, ivs, iv_starts, fn, label)
        delta = res["net"] - base_net
        results.append({"experiment": "LA1", **res, "delta": round(delta, 1)})
        print(f"  {label:25s} {res['kept']:3d}t kept, {res['removed']:3d}t removed "
              f"(WR {res['removed_wr']:.0f}%, R {res['removed_r']:+.1f}) "
              f"NET {res['net']:+.1f}R (delta {delta:+.1f})")

    # === LA2: FLIP PREFERENCE ===
    print("\n=== LA2: FLIP PREFERENCE ===")
    flip_fn = lambda t: t.get("htf_regime") == "flip"
    b2_fn = lambda t: t.get("htf_regime") == "b2"
    flip_sig = lambda t: t.get("break_kind") == "FLIP"
    b2_sig = lambda t: t.get("break_kind") == "B2"

    for label, fn in [("keep only flip regime", flip_fn),
                      ("keep only b2 regime", b2_fn),
                      ("skip B2 signals", flip_sig),
                      ("skip FLIP signals", b2_sig)]:
        res = run_filter(tr, g, ivs, iv_starts, fn, label)
        delta = res["net"] - base_net
        results.append({"experiment": "LA2", **res, "delta": round(delta, 1)})
        print(f"  {label:25s} {res['kept']:3d}t kept, {res['removed']:3d}t removed "
              f"(WR {res['removed_wr']:.0f}%, R {res['removed_r']:+.1f}) "
              f"NET {res['net']:+.1f}R (delta {delta:+.1f})")

    # === LA3: FAST DEATH FILTER ===
    print("\n=== LA3: FAST DEATH FILTER ===")
    fast_fns = [
        ("skip <5 bars", lambda t: t["_bars"] >= 5),
        ("skip <8 bars", lambda t: t["_bars"] >= 8),
        ("skip <12 bars", lambda t: t["_bars"] >= 12),
        ("skip >192 bars (very slow losers)", lambda t: t["_bars"] <= 192 or float(t["r_multiple"]) > 0),
    ]
    for label, fn in fast_fns:
        res = run_filter(tr, g, ivs, iv_starts, fn, label)
        delta = res["net"] - base_net
        results.append({"experiment": "LA3", **res, "delta": round(delta, 1)})
        print(f"  {label:38s} {res['kept']:3d}t kept, {res['removed']:3d}t removed "
              f"(WR {res['removed_wr']:.0f}%, R {res['removed_r']:+.1f}) "
              f"NET {res['net']:+.1f}R (delta {delta:+.1f})")

    # === LA4: COMBINED FILTERS ===
    print("\n=== LA4: COMBINED FILTERS ===")
    combos = [
        ("skip 12-24h + skip B2",
         lambda t: (t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24)
                   and t.get("htf_regime") == "flip"),
        ("skip 12-24h + skip <8 bars",
         lambda t: (t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24)
                   and t["_bars"] >= 8),
        ("w24 + skip B2",
         lambda t: (t["_wage_h"] is None or t["_wage_h"] >= 24)
                   and t.get("htf_regime") == "flip"),
        ("skip 12-24h + skip B2 + skip <8 bars",
         lambda t: (t["_wage_h"] is None or t["_wage_h"] < 12 or t["_wage_h"] >= 24)
                   and t.get("htf_regime") == "flip"
                   and t["_bars"] >= 8),
    ]
    for label, fn in combos:
        res = run_filter(tr, g, ivs, iv_starts, fn, label)
        delta = res["net"] - base_net
        results.append({"experiment": "LA4", **res, "delta": round(delta, 1)})
        print(f"  {label:40s} {res['kept']:3d}t kept, {res['removed']:3d}t removed "
              f"(WR {res['removed_wr']:.0f}%, R {res['removed_r']:+.1f}) "
              f"NET {res['net']:+.1f}R (delta {delta:+.1f})")

    # Save results
    out = {"baseline": {"n": base_s["n"], "net": round(base_net, 1),
                         "gross": round(base_s["gross"], 1), "wr": round(base_s["wr"], 1)},
           "filters": results}
    (ROOT / "live_stuff/tests/_la_filters_results.json").write_text(json.dumps(out, indent=1))
    print(f"\n(la_filters done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()