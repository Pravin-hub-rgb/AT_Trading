"""Stage 34 — Bybit BTCUSDT perpetual 15m minBars architecture.

Frozen MB20/MB30/MB40/MB50 path-true comparison. Only the 15m swing chain is
rebuilt; the 1h chain, strategy parameters, 1m fine structural exits, costs and
portfolio rules remain frozen. MB50 is the exact identity architecture control.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import params_for, stats
from exp_thesis_structure_volume import load_scope
from src.btc.btc_routes import _compute_swings

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_mb_architecture_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_mb_architecture_results_oos.json",
}
MIN_BARS = (20, 30, 40, 50)
CONFIGS = (
    ("pure_v18_single", params_for("pure_v18_single")),
    ("pure_v18_multi", params_for("pure_v18_multi")),
    ("literal_v18_single", params_for("literal_v18_single")),
    ("literal_v18_multi", params_for("literal_v18_multi")),
    ("fullstack_single", {**BP, **EXPERIMENTS["fullstack_wage10_cd0_single_sw10"]["params"]}),
    ("champion_multi", {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}),
    ("utcsat_multi", {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}),
)


def run_scope(scope):
    data = load_scope(scope)
    sim = build_module()
    if scope == "is":
        identity_gate(data, sim)
    chains = {mb: _compute_swings(data["f15"], "continuous", min_bars=mb) for mb in MIN_BARS}
    baseline_structure = {k: len(v) for k, v in chains.items()}
    exact_mb50 = all(
        int(t.get("entry_idx", -1)) == int(u.get("entry_idx", -1))
        and t.get("dir") == u.get("dir")
        and float(t.get("r_multiple", 0.0)) == float(u.get("r_multiple", 0.0))
        for t, u in zip(
            sim(data["c1h"], data["sw10"], data["c15"], chains[50], fine_ltf=data["fine"], **dict(params_for("pure_v18_multi")))["ltf_trades"],
            sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **dict(params_for("pure_v18_multi")))["ltf_trades"],
        )
    )
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "architecture": {"h1_min_bars": 20, "l15_min_bars": list(MIN_BARS),
                               "fine_exit_tf": "1m", "swing_counts": baseline_structure,
                               "mb50_exact_trade_match": exact_mb50},
              "configs": {}}
    for name, params in CONFIGS:
        params = dict(params); params.setdefault("exp_partial_r", 0.0)
        result["configs"][name] = {}
        for mb, sw15 in chains.items():
            out = sim(data["c1h"], data["sw10"], data["c15"], sw15,
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            metrics = stats(trades)
            result["configs"][name][f"mb{mb}"] = {"metrics": metrics}
            print(f"  {scope.upper():3} {name:20} MB{mb:<2} n={metrics['n']:3d} "
                  f"G={metrics['gross_r']:+8.1f} N={metrics['net_r']:+8.1f} "
                  f"avg={metrics['avg_net_r']:+.3f} WR={metrics['win_rate_pct']:5.1f}% "
                  f"PF={metrics['gross_pf']:.2f} DD={metrics['max_net_dd']:5.1f}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    started = time.time()
    for scope in scopes:
        print("=" * 140, flush=True)
        print(f"15M MB ARCHITECTURE — BYBIT {scope.upper()}", flush=True)
        print("=" * 140, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)
    print(f"done in {time.time() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
