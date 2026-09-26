"""Stage 32 — 5m-confirmed entry and first-loss fresh-swing cohort policies.

Bybit BTCUSDT perpetual only. Fixed path-true policies, no threshold sweep:
baseline, completed-5m confirmation, first-loss fresh-swing wait, two-loss
fresh-swing freeze, and the 5m+cohort combination. The 15m structural stop and
trail remain the exit logic; the 5m arm only relocates entry.
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

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import load_data, params_for, stats
from exp_thesis_5m_opposition import load_5m

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_5m_confirm_cohort_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_5m_confirm_cohort_results_oos.json",
}
POLICIES = (
    ("baseline", {}),
    ("five_m_confirm", {"exp_5m_confirm": 1, "exp_5m_wait_min": 240}),
    ("first_loss_fresh_swing", {"exp_cohort_swingpause": 1, "exp_cohort_loss_n": 1, "exp_cohort_rearm": 1}),
    ("two_loss_fresh_swing", {"exp_cohort_swingpause": 1, "exp_cohort_loss_n": 2, "exp_cohort_rearm": 1}),
    ("five_m_plus_first_loss", {"exp_5m_confirm": 1, "exp_5m_wait_min": 240,
                                 "exp_cohort_swingpause": 1, "exp_cohort_loss_n": 1, "exp_cohort_rearm": 1}),
)


def run_scope(scope):
    data = load_data(scope)
    c5 = load_5m(scope)
    sim = build_module()
    if scope == "is":
        identity_gate({"c1h": data[0], "sw20": data[1], "c15": data[2], "sw15": data[3]}, sim)
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "five_m": {"rows": len(c5), "start": c5[0]["ts"], "end": c5[-1]["ts"]},
              "policies": [name for name, _ in POLICIES], "variants": {}}
    configs = {
        "pure_v18_single": params_for("pure_v18_single"),
        "pure_v18_multi": params_for("pure_v18_multi"),
        "literal_v18_single": params_for("literal_v18_single"),
        "literal_v18_multi": params_for("literal_v18_multi"),
        "fullstack_single": {**BP, **EXPERIMENTS["fullstack_wage10_cd0_single_sw10"]["params"]},
        "champion_multi": {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]},
        "utcsat_multi": {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]},
    }
    for name, base in configs.items():
        result["variants"][name] = {}
        for policy, flags in POLICIES:
            out = sim(*data, **{**base, **flags, "exp_5m_data": c5})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            row = {"flags": flags, "metrics": stats(trades),
                   "five_m_stats": out.get("five_m_stats", {}) if isinstance(out, dict) else {},
                   "cohort_stats": out.get("cohort_stats", {}) if isinstance(out, dict) else {}}
            result["variants"][name][policy] = row
            m = row["metrics"]
            print(f"  {scope.upper():3} {name:20} {policy:22} n={m['n']:3d} "
                  f"G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} "
                  f"avgN={m['avg_net_r']:+.3f} WR={m['win_rate_pct']:5.1f}% "
                  f"DD={m['max_net_dd']:5.1f} 5m={row['five_m_stats']} "
                  f"cohort={row['cohort_stats']}", flush=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    for scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        print("=" * 150, flush=True)
        print(f"5M CONFIRM + COHORT LIFECYCLE — BYBIT {scope.upper()}", flush=True)
        print("=" * 150, flush=True)
        out = OUT[scope]
        out.write_text(json.dumps(run_scope(scope), indent=2), encoding="utf-8")
        print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    main()
