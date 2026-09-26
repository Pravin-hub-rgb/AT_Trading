"""Stage A — pure-v18 large-swing threshold reality check.

Bybit BTCUSDT perpetual only. Tests current-swing magnitude thresholds 2/3/4/5
ATR as both a selective large-swing arm and a reject-large arm on the raw
single/multi and literal v18 controls.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from exp_geom_pure_v18_sweep import load_data, params_for, stats
from run_experiment import identity_gate
from test_experiments_craze import build_module

OUT = {"is": ROOT / "live_stuff/tests/_geom_large_swing_sweep_results_is.json",
       "oos": ROOT / "live_stuff/tests/_geom_large_swing_sweep_results_oos.json"}
CONTROLS = ("pure_v18_single", "pure_v18_multi", "literal_v18_single", "literal_v18_multi")
THRESHOLDS = (2.0, 3.0, 4.0, 5.0)


def run_scope(scope):
    data = load_data(scope)
    sim = build_module()
    if scope == "is":
        identity_gate({"c1h": data[0], "sw20": data[1], "c15": data[2], "sw15": data[3]}, sim)
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "thresholds_atr": THRESHOLDS, "controls": CONTROLS,
              "policies": ["only_large", "reject_large"], "variants": {}}
    for control in CONTROLS:
        base = params_for(control)
        zero = sim(*data, **base)
        zero_trades = zero["ltf_trades"] if isinstance(zero, dict) else zero
        rows = {"baseline": {"flags": {}, "metrics": stats(zero_trades)}}
        for threshold in THRESHOLDS:
            for policy in ("only_large", "reject_large"):
                mode = "large_mag" if policy == "only_large" else "not_large_mag"
                gates = []
                flags = {"exp_geom_mode": mode, "exp_geom_mag_min_atr": threshold,
                         "exp_geom_stats": gates}
                out = sim(*data, **{**base, **flags})
                trades = out["ltf_trades"] if isinstance(out, dict) else out
                m = stats(trades); b = rows["baseline"]["metrics"]
                name = f"{policy}_{threshold:g}atr"
                rows[name] = {"flags": {k: v for k, v in flags.items() if k != "exp_geom_stats"},
                              "activation": {"candidates": len(gates),
                                             "blocked": sum(not int(r.get("allowed", 1)) for r in gates)},
                              "metrics": m}
                print(f"  {scope.upper():3} {control:19} {name:20} "
                      f"n={m['n']:3d} G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} "
                      f"dN={m['net_r']-b['net_r']:+7.1f} avgN={m['avg_net_r']:+.3f} "
                      f"WR={m['win_rate_pct']:5.1f}% DD={m['max_net_dd']:5.1f}", flush=True)
        result["variants"][control] = rows
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    for scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        print("=" * 125, flush=True)
        print(f"PURE V18 LARGE-SWING THRESHOLD REALITY CHECK — BYBIT {scope.upper()}", flush=True)
        print("=" * 125, flush=True)
        out = OUT[scope]
        out.write_text(json.dumps(run_scope(scope), indent=2), encoding="utf-8")
        print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    main()
