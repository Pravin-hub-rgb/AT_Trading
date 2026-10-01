"""Frozen pure-v18 stale-B1 age sweep (Bybit BTCUSDT perpetual).

Promotion rule: a threshold must improve both single controls in both IS and
reused OOS. Multi controls are supporting evidence, not an optimization target.
No production code is changed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from exp_geom_pure_v18_sweep import load_data, params_for, stats
from run_experiment import identity_gate
from test_experiments_craze import build_module

OUT = {"is": ROOT / "backtest/tests/_geom_stale_b1_sweep_results_is.json",
       "oos": ROOT / "backtest/tests/_geom_stale_b1_sweep_results_oos.json"}
THRESHOLDS = (8, 16, 32, 48, 64, 96, 128, 192)
CONTROLS = ("pure_v18_single", "literal_v18_single")


def run_scope(scope):
    data = load_data(scope)
    sim = build_module()
    if scope == "is":
        identity_gate({"c1h": data[0], "sw20": data[1], "c15": data[2], "sw15": data[3]}, sim)
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "thresholds_bars": THRESHOLDS, "controls": CONTROLS,
              "promotion_rule": "threshold improves both single controls in IS and reused OOS",
              "variants": {}}
    for control in CONTROLS:
        base = params_for(control)
        out0 = sim(*data, **base)
        trades0 = out0["ltf_trades"] if isinstance(out0, dict) else out0
        rows = {"baseline": {"flags": {}, "metrics": stats(trades0)}}
        for threshold in THRESHOLDS:
            geom_rows = []
            flags = {"exp_geom_mode": "not_stale_b1", "exp_geom_b1_min": threshold,
                     "exp_geom_stats": geom_rows}
            out = sim(*data, **{**base, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            rows[str(threshold)] = {
                "flags": {k: v for k, v in flags.items() if k != "exp_geom_stats"},
                "activation": {
                    "candidates_seen": len(geom_rows),
                    "blocked": sum(not int(r.get("allowed", 1)) for r in geom_rows),
                    "b1_age_min": min([r["b1_age"] for r in geom_rows if r.get("b1_age") is not None] or [None]),
                    "b1_age_max": max([r["b1_age"] for r in geom_rows if r.get("b1_age") is not None] or [None]),
                },
                "metrics": stats(trades),
            }
            b = rows["baseline"]["metrics"]; m = rows[str(threshold)]["metrics"]
            print(f"  {scope.upper():3} {control:19} stale>={threshold:<3d} "
                  f"blocked={rows[str(threshold)]['activation']['blocked']:3d} "
                  f"n={m['n']:3d} G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} "
                  f"dN={m['net_r']-b['net_r']:+7.1f} DD={m['max_net_dd']:5.1f}", flush=True)
        result["variants"][control] = rows
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    for scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        print("=" * 120, flush=True)
        print(f"PURE V18 STALE-B1 AGE SWEEP — BYBIT {scope.upper()}", flush=True)
        print("=" * 120, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
