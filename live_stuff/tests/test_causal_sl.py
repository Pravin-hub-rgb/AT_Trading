"""Causal SL comparison — batch (retroactive) vs causal (live-honest) SL.

Runs 3 configs with and without exp_causal_sl=1 to measure the retroactive SL advantage.

Usage:
    python live_stuff/tests/test_causal_sl.py
"""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, _compute_swings, stats
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs
from run_experiment import fund, INSTRUMENT
import run_experiment as re_mod

_g = get_v18_params(INSTRUMENT)

CONFIGS = {
    "champion_multi": {
        "desc": "champion_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
    },
    "utcsat_multi": {
        "desc": "utcsat_multi_sw10 (KING MULTI)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "window_end": "exit"},
        "swing": "sw10",
    },
    "king_single": {
        "desc": "fullstack_wage10_cd0_single_sw10 (KING SINGLE)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 10,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
    },
}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def run_one(name, cfg, data, sim, causal=False):
    params = {**cfg["params"]}
    if causal:
        params["exp_causal_sl"] = 1
    sw = data["sw10"] if cfg["swing"] == "sw10" else data["sw15"]

    t0 = time.time()
    r = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
    elapsed = time.time() - t0
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    nt = net_of(tr)

    tag = "causal" if causal else "batch"
    return {
        "name": name, "tag": tag, "n": s["n"], "gross": s["gross"],
        "net": nt, "wr": s["wr"], "dd": s["dd"], "mx": s["mx"],
        "elapsed": elapsed,
    }


def main():
    print("=" * 70)
    print("  CAUSAL SL COMPARISON: batch (retroactive) vs causal (live-honest)")
    print("=" * 70)

    print("\n  Loading data...")
    t0 = time.time()
    data = re_mod.get_data()
    print("  Data loaded in %.0fs" % (time.time() - t0))

    print("  Building patched engine...")
    sim = build_module()
    print("  Engine ready.\n")

    results = []
    for name, cfg in CONFIGS.items():
        print(f"  [{name}] running batch SL...", end="", flush=True)
        r_batch = run_one(name, cfg, data, sim, causal=False)
        print(f" n={r_batch['n']} NET={r_batch['net']:+.1f}R DD={r_batch['dd']:.1f}  ({r_batch['elapsed']:.1f}s)")

        print(f"  [{name}] running causal SL...", end="", flush=True)
        r_causal = run_one(name, cfg, data, sim, causal=True)
        print(f" n={r_causal['n']} NET={r_causal['net']:+.1f}R DD={r_causal['dd']:.1f}  ({r_causal['elapsed']:.1f}s)")

        delta = r_causal["net"] - r_batch["net"]
        dd_delta = r_causal["dd"] - r_batch["dd"]
        print(f"  [{name}] DELTA: {delta:+.1f}R  DD delta: {dd_delta:+.1f}")
        print()

        results.append((name, cfg["desc"], r_batch, r_causal, delta))

    # Summary table
    print("=" * 80)
    print("  SUMMARY: Retroactive vs Causal SL")
    print("=" * 80)
    print(f"\n  {'Config':<25} {'Batch NET':>10} {'Causal NET':>11} {'Delta':>8} {'Batch DD':>9} {'Causal DD':>10}")
    print(f"  {'-'*75}")
    for name, desc, rb, rc, delta in results:
        print(f"  {desc:<25} {rb['net']:>+9.1f}R {rc['net']:>+10.1f}R {delta:>+7.1f}R {rb['dd']:>8.1f}R {rc['dd']:>9.1f}R")

    print(f"\n  Retroactive SL advantage: {sum(r[4] for r in results)/len(results):+.1f}R average")
    print(f"  These are the REAL numbers for live trading.")


if __name__ == "__main__":
    main()
