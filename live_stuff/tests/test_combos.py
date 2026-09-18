"""Combo experiments — stack the winning experiments."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from test_experiments import (load_window, simulate_v18_experiments, run_and_report,
                               fmt, SYMBOL, PARAMS)
from src.btc.btc_routes import _compute_swings, _load_fine_1m

def main():
    print("Loading data...")
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
    print(f"  Data loaded. 1h: {len(c1h)}, 15m: {len(c15)}, 1m: {len(fine)}")

    base_kw = dict(sl_buf_atr=PARAMS["sl_buf_atr"], ext_stop_r=PARAMS["ext_stop_r"],
                    chop_thresh=PARAMS["chop_thresh"], cooldown_bars=PARAMS["cooldown_bars"],
                    max_consecutive_losses=PARAMS["max_consecutive_losses"])

    # Baseline
    t0b = time.time()
    base_tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **base_kw)["ltf_trades"]
    base = run_and_report("v18 BASELINE", base_tr)
    base_r = base["total_r"]
    print(f"\n{'='*110}")
    print(f"  BASELINE: {base_r:+.1f}R")
    print(f"{'='*110}")

    # --- Single best experiments (recap) ---
    combos = [
        # Solo winners
        ("Multi-LTF only", {"exp_multi_ltf": True}),
        ("Dual-Active only", {"exp_dual_active": True}),
        ("Persist=5 only", {"exp_regime_persist": 5}),
        ("Persist=3 only", {"exp_regime_persist": 3}),
        # Two-way combos
        ("Multi-LTF + Dual-Active", {"exp_multi_ltf": True, "exp_dual_active": True}),
        ("Multi-LTF + Persist=5", {"exp_multi_ltf": True, "exp_regime_persist": 5}),
        ("Multi-LTF + Persist=3", {"exp_multi_ltf": True, "exp_regime_persist": 3}),
        ("Dual-Active + Persist=5", {"exp_dual_active": True, "exp_regime_persist": 5}),
        ("Dual-Active + Persist=3", {"exp_dual_active": True, "exp_regime_persist": 3}),
        # Three-way combos
        ("Multi-LTF + Dual + Persist=5", {"exp_multi_ltf": True, "exp_dual_active": True, "exp_regime_persist": 5}),
        ("Multi-LTF + Dual + Persist=3", {"exp_multi_ltf": True, "exp_dual_active": True, "exp_regime_persist": 3}),
        # Adaptive Halt combos
        ("Multi-LTF + Adaptive Halt", {"exp_multi_ltf": True, "exp_adaptive_halt": True}),
        ("Multi-LTF + Dual + Adaptive Halt", {"exp_multi_ltf": True, "exp_dual_active": True, "exp_adaptive_halt": True}),
        ("Multi-LTF + Dual + Persist=5 + Adaptive", {"exp_multi_ltf": True, "exp_dual_active": True, "exp_regime_persist": 5, "exp_adaptive_halt": True}),
        # Quality filter combos
        ("Multi-LTF + Quality=10%", {"exp_multi_ltf": True, "exp_window_quality": 0.1}),
        ("Multi-LTF + Quality=20%", {"exp_multi_ltf": True, "exp_window_quality": 0.2}),
        ("Dual + Persist=5 + Quality=10%", {"exp_dual_active": True, "exp_regime_persist": 5, "exp_window_quality": 0.1}),
    ]

    results = [base]
    for name, kwargs in combos:
        t0e = time.time()
        tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **base_kw, **kwargs)["ltf_trades"]
        dt = time.time() - t0e
        r = run_and_report(name, tr)
        results.append(r)
        print(fmt(r, base_r) + f"  ({dt:.1f}s)")

    # Summary
    print(f"\n{'='*110}")
    print("  COMBO SUMMARY (sorted by R)")
    print(f"{'='*110}")
    results.sort(key=lambda x: -x["total_r"])
    for i, r in enumerate(results):
        marker = " *** BASELINE ***" if r["name"] == "v18 BASELINE" else ""
        better = " ^" if r["total_r"] > base_r else ""
        print(f"  #{i+1:2d} {fmt(r, base_r)}{better}{marker}")

    best = results[0]
    print(f"\n  BEST: {best['name']} — {best['total_r']:+.1f}R ({best['total_r'] - base_r:+.1f}R vs baseline)")
    print(f"  Trades: {best['trades']}, WR: {best['wr']:.1f}%, PF: {best['pf']:.2f}")

if __name__ == "__main__":
    main()
