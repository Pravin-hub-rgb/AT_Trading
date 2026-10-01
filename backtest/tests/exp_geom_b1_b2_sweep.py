"""Pure-v18 B1->B2 timing path-true policies (Bybit BTCUSDT perp).

Fixed policies only: block immediate B1->B2 (0-2 bars) and allow only
B1->B2 delayed 3-8 bars. FLIP handling is unchanged.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from exp_geom_pure_v18_sweep import load_data, params_for, stats
from run_experiment import identity_gate
from test_experiments_craze import build_module

OUT = {"is": ROOT / "backtest/tests/_geom_b1_b2_results_is.json",
       "oos": ROOT / "backtest/tests/_geom_b1_b2_results_oos.json"}
CONTROLS = ("pure_v18_single", "pure_v18_multi", "literal_v18_single", "literal_v18_multi")
POLICIES = ("block_immediate", "only_delayed_3_8")


def run_scope(scope):
    data = load_data(scope)
    sim = build_module()
    if scope == "is":
        identity_gate({"c1h": data[0], "sw20": data[1], "c15": data[2], "sw15": data[3]}, sim)
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope, "controls": CONTROLS,
              "policies": list(POLICIES), "variants": {}}
    for control in CONTROLS:
        base = params_for(control)
        out0 = sim(*data, **base)
        trades0 = out0["ltf_trades"] if isinstance(out0, dict) else out0
        result["variants"][control] = {"baseline": {"metrics": stats(trades0)}}
        for policy in POLICIES:
            gate_rows = []
            out = sim(*data, **base, exp_b1_b2_mode=policy, exp_b1_b2_stats=gate_rows)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            m = stats(trades); b = result["variants"][control]["baseline"]["metrics"]
            result["variants"][control][policy] = {
                "activation": {"b2_candidates": len(gate_rows),
                               "blocked": sum(not int(r["allowed"]) for r in gate_rows)},
                "metrics": m,
            }
            print(f"  {scope.upper():3} {control:19} {policy:20} blocked={sum(not int(r['allowed']) for r in gate_rows):3d} "
                  f"n={m['n']:3d} G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} "
                  f"dN={m['net_r']-b['net_r']:+7.1f} DD={m['max_net_dd']:5.1f}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    for scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        print("=" * 115, flush=True)
        print(f"PURE V18 B1->B2 TIMING — BYBIT {scope.upper()}", flush=True)
        print("=" * 115, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
