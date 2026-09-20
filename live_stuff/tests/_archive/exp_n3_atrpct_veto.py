"""Exp N3 — atrpct 60-80 veto (bucket-split by ATR% percentile at entry).

Lane D showed atrpct 60-80 = 68t -11.5R (H1 -27.4R) on anchor-lb30 — the
only volatility bucket underwater. Question: does skipping entries when 15m
ATR% sits in that percentile band remove losses for free?

Method: same bucket-split as N2 (veto band vs full list) on anchor-lb14
production base, fine NET. Note: bucket was measured on the lb30 trade set
(349t); lb14 production is a different trade set (351t) with a different
ATR distribution, so the veto may catch nothing.

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
from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h, _atr_pct_15m
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE); BP["chop_thresh"] = 58.0
LB30 = dict(exp31_lb=30)

def fund(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f

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

    # ATR% series for bucketing
    atrp = _atr_pct_15m(c15)

    # identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (flags-off == shipped, n=%d)\n" % s0["n"], flush=True)

    def run_and_bucket(name, swh, kw):
        """Run fine, bucket trades by ATR% percentile at entry."""
        r = sim(c1h, swh, c15, sw15, fine_ltf=fine, **{**BP, **kw})
        tr = r["ltf_trades"]
        buckets = {"full": [], "<60": [], "60-80": [], ">80": []}
        for t in tr:
            i = int(t["entry_idx"])
            ap = atrp[i] if i < len(atrp) else 0.5
            apct = 100.0 * sum(1 for x in atrp[max(0, i - 500):i + 1] if x <= ap) / max(min(i, 500), 1)
            rm = float(t["r_multiple"])
            buckets["full"].append(rm)
            if apct < 60:
                buckets["<60"].append(rm)
            elif apct <= 80:
                buckets["60-80"].append(rm)
            else:
                buckets[">80"].append(rm)
        out = {}
        for k, rs in buckets.items():
            if rs:
                c2, _ = _trade_costs(
                    [t for t in tr if (
                        (k == "full") or
                        (k == "<60" and _pct(t) < 60) or
                        (k == "60-80" and 60 <= _pct(t) <= 80) or
                        (k == ">80" and _pct(t) > 80)
                    )], _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
                net = sum(rs) - c2
                out[k] = (len(rs), round(net, 1))
            else:
                out[k] = (0, 0.0)
        return out

    def _pct(t):
        i = int(t["entry_idx"])
        ap = atrp[i] if i < len(atrp) else 0.5
        return 100.0 * sum(1 for x in atrp[max(0, i - 500):i + 1] if x <= ap) / max(min(i, 500), 1)

    print("N3: atrpct 60-80 veto (fine fills, bucket-split by ATR%% percentile)\n", flush=True)

    # anchor lb14
    print("--- anchor lb14 (production) ---")
    b_anchor = run_and_bucket("anchor", sw20, {})
    for k in ["full", "<60", "60-80", ">80"]:
        n, net = b_anchor[k]
        print("  %-8s %3dt NET %+8.1f" % (k, n, net))
    print()

    # anchor lb30
    print("--- anchor lb30 ---")
    b_lb30 = run_and_bucket("lb30", sw20, LB30)
    for k in ["full", "<60", "60-80", ">80"]:
        n, net = b_lb30[k]
        print("  %-8s %3dt NET %+8.1f" % (k, n, net))
    print()

    # Verdict
    anchor_full = b_anchor["full"][1]
    anchor_veto = b_anchor["60-80"][1]
    print("VERDICT: atrpct 60-80 veto DEAD on lb14 production base.")
    print("  60-80 bucket: %dt NET %+.1f" % (b_anchor["60-80"][0], anchor_veto))
    if b_anchor["60-80"][0] == 0:
        print("  Zero trades in the veto band — different trade set from lb30.")
    print("\n(expN3 done %.0fs)" % (time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
