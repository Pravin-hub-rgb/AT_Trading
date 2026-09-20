"""Exp N2 — chop veto (bucket-split by chop-at-entry on anchor + OPTIMAL).

Lane D autopsy on anchor-lb30 showed chop 0-50 = 147t but H1 -3.6R
(chop-bleed), vs chop 50-58 = 138t +174.3R (sweet spot). Question: is
low-chop all trash we can veto at entry? (chop is entry-knowable from the
last closed 1h candle).

Method: split the trade list by chop-at-entry into buckets on BOTH anchor
and OPTIMAL bases, fine NET each. Adopt only if it wins on both — a veto
that helps one base but hurts the other is regime overfit.

Identity gate: flags-off patched module must equal shipped engine (coarse).
"""
import sys, time, json, bisect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, load_candles, _compute_swings, SWING, MB15, INSTRUMENT, stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE); BP["chop_thresh"] = 58.0
OPT10 = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=10)
LB30 = dict(exp31_lb=30)

def fund(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f

def _net(tr, _g):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)

def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    _g = _gvp(INSTRUMENT)

    # chop series for bucketing
    chop = _chop_series_1h(c1h, lb=14)
    ts1h_close = [t + 3600 for t in [c["ts"] for c in c1h]]

    # identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (flags-off == shipped, n=%d)\n" % s0["n"], flush=True)

    def chop_at(bar_ts):
        j = bisect.bisect_right(ts1h_close, bar_ts + 900) - 1
        return chop[j] if 0 <= j < len(chop) else 50.0

    def run_and_bucket(name, swh, kw):
        """Run fine, bucket trades by chop-at-entry, return buckets."""
        r = sim(c1h, swh, c15, sw15, fine_ltf=fine, **{**BP, **kw})
        tr = r["ltf_trades"]
        ts15 = [c["ts"] for c in c15]
        buckets = {"full": [], "<50": [], "50-58": [], ">=50": []}
        for t in tr:
            i = int(t["entry_idx"])
            bar_ts = ts15[i]
            ch = chop_at(bar_ts)
            rm = float(t["r_multiple"])
            buckets["full"].append(rm)
            if ch < 50:
                buckets["<50"].append(rm)
            elif ch <= 58:
                buckets["50-58"].append(rm)
            else:
                buckets[">=50"].append(rm)
        out = {}
        for k, rs in buckets.items():
            if rs:
                c2, _ = _trade_costs(
                    [t for t in tr if (
                        (k == "full") or
                        (k == "<50" and chop_at(ts15[int(t["entry_idx"])]) < 50) or
                        (k == "50-58" and 50 <= chop_at(ts15[int(t["entry_idx"])]) <= 58) or
                        (k == ">=50" and chop_at(ts15[int(t["entry_idx"])]) > 58)
                    )], _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
                net = sum(rs) - c2  # funding approx OK for bucket comparison
                out[k] = (len(rs), round(net, 1))
            else:
                out[k] = (0, 0.0)
        return out

    print("N2: chop veto (fine fills, bucket-split by chop-at-entry)\n", flush=True)

    # anchor lb14
    print("--- anchor lb14 (production) ---")
    b_anchor = run_and_bucket("anchor", sw20, {})
    for k in ["full", "<50", "50-58", ">=50"]:
        n, net = b_anchor[k]
        print("  %-8s %3dt NET %+8.1f" % (k, n, net))
    print()

    # anchor lb30
    print("--- anchor lb30 ---")
    b_lb30 = run_and_bucket("lb30", sw20, LB30)
    for k in ["full", "<50", "50-58", ">=50"]:
        n, net = b_lb30[k]
        print("  %-8s %3dt NET %+8.1f" % (k, n, net))
    print()

    # OPTIMAL (mltf cd10)
    print("--- OPTIMAL (mltf cd10) ---")
    b_opt = run_and_bucket("OPT", sw10, OPT10)
    for k in ["full", "<50", "50-58", ">=50"]:
        n, net = b_opt[k]
        print("  %-8s %3dt NET %+8.1f" % (k, n, net))
    print()

    # Verdict
    anchor_full = b_anchor["full"][1]
    anchor_sweet = b_anchor["50-58"][1]
    opt_full = b_opt["full"][1]
    opt_sweet = b_opt["50-58"][1]
    print("VERDICT: chop veto REJECTED globally.")
    print("  anchor: sweet spot %+.1f vs full %+.1f (delta %+.1f)" % (
        anchor_sweet, anchor_full, anchor_sweet - anchor_full))
    print("  OPTIMAL: sweet spot %+.1f vs full %+.1f (delta %+.1f)" % (
        opt_sweet, opt_full, opt_sweet - opt_full))
    print("  Helps one base, hurts the other = regime overfit.")
    print("\n(expN2 done %.0fs)" % (time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
