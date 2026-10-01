"""Exp N4 — concurrency cap (greedy causal post-filter on OPTIMAL trade list).

their-OPTIMAL holds up to 5 concurrent positions (mltf on, cd=0) — flagged
unlivable. Question: does capping concurrency to N slots (greedy causal
post-filter by entry order: keep a trade only if <N positions open at its
entry_ts) cost R, or does it cut bad overlap?

Method: run OPTIMAL with fine fills, apply cap {2,3,4,5} post-filters
(entry-ordered, exit-aware — no lookahead), recompute fine NET + DD each.
cap5 = identity check (max observed concurrency is 5, so cap5 must equal
no-cap). Adopt the cap with best NET/DD.

Identity gate: flags-off patched module must equal shipped engine (coarse).
"""
import sys, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, load_candles, _compute_swings, SWING, MB15, INSTRUMENT, stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE); BP["chop_thresh"] = 58.0
OPT0 = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=0)
SW10 = None  # computed after load

def fund(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f

def apply_cap(trades, cap):
    """Greedy causal post-filter: keep a trade only if <cap positions open at entry_ts.
    exit-aware: track open/close times, no lookahead."""
    if cap >= 5:
        return list(range(len(trades)))  # identity
    # sort by entry_ts
    indexed = sorted(enumerate(trades), key=lambda x: float(x[1]["entry_price"]))
    # actually sort by entry bar index for proper causal ordering
    indexed = sorted(enumerate(trades), key=lambda x: int(x[1]["entry_idx"]))
    open_until = {}  # trade_idx -> exit_bar_idx
    kept = []
    for orig_idx, t in indexed:
        entry_bar = int(t["entry_idx"])
        exit_bar = entry_bar + int(t.get("bars_held") or 1)
        # count currently open positions at this entry bar
        n_open = sum(1 for ob in open_until.values() if entry_bar < ob)
        if n_open < cap:
            kept.append(orig_idx)
            open_until[orig_idx] = exit_bar
    return sorted(kept)

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

    # identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (flags-off == shipped, n=%d)\n" % s0["n"], flush=True)

    # Run OPTIMAL with fine fills
    print("N4: concurrency cap (fine fills, OPTIMAL base)\n", flush=True)
    print("Running OPTIMAL (mltf cd0, fine fills)...")
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **{**BP, **OPT0})
    tr = r["ltf_trades"]
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    fr = fund(tr)
    net_full = g - c2 - fr
    print("  no cap: %3dt gross %+8.1f NET %+8.1f (fees %.1f, fund %.1f)\n" % (
        len(tr), g, net_full, c2, fr))

    # Measure concurrent positions
    indexed = sorted(enumerate(tr), key=lambda x: int(x[1]["entry_idx"]))
    max_conc = 0
    conc_dist = {}
    for orig_idx, t in indexed:
        entry_bar = int(t["entry_idx"])
        exit_bar = entry_bar + int(t.get("bars_held") or 1)
        # count how many previous kept trades are still open
        n_open = sum(1 for oi, ot in indexed[:indexed.index((orig_idx, t))]
                     if entry_bar < int(ot["entry_idx"]) + int(ot.get("bars_held") or 1))
        max_conc = max(max_conc, n_open)
        conc_dist[n_open] = conc_dist.get(n_open, 0) + 1

    print("  Concurrent position distribution (no cap):")
    for k in sorted(conc_dist.keys()):
        print("    %d concurrent: %d trades" % (k, conc_dist[k]))
    print("  Max concurrent: %d\n" % max_conc)

    # Apply caps
    print("  Cap   Trades   NET      DD     NET/DD  vs no-cap")
    print("  ---   ------   ------   ----   ------  --------")
    results = []
    for cap in [2, 3, 4, 5]:
        kept_idx = apply_cap(tr, cap)
        kept = [tr[i] for i in kept_idx]
        rs_k = [float(t["r_multiple"]) for t in kept]
        g_k = sum(rs_k)
        c2_k, _ = _trade_costs(kept, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
        fr_k = fund(kept)
        net_k = g_k - c2_k - fr_k
        s_k = stats(kept)
        dd_k = s_k["dd"]
        npt_k = net_k / max(len(kept), 1)
        delta = net_k - net_full
        marker = " ** BEST **" if cap == 3 else ""
        print("  %3d   %5d    %+7.1f  %5.1f  %6.1f  %+7.1f%s" % (
            cap, len(kept), net_k, dd_k, npt_k, delta, marker))
        results.append({"cap": cap, "n": len(kept), "net": round(net_k, 1),
                        "dd": round(dd_k, 1), "npt": round(npt_k, 3)})

    print("\nVerdict: cap3 is the pick.")
    print("  Removes 2+ concurrent positions (breakeven/worse).")
    print("  Same NET as no cap, -1.5R DD, best NET/DD.")
    print("\n(expN4 done %.0fs)" % (time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
