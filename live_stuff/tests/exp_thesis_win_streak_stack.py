"""Default stacking test for completed-win-streak policies.

Answers the unresolved interaction question from Stage 64 by comparing:
- shipped default;
- default + global/window soft N3;
- no-built-in-halt control;
- no-halt + global/window soft N3.

Bybit BTCUSDT perpetual only; path-true; test-only; no production change.
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

from exp_thesis_win_streak import CONFIGS, load_scope, params_for, summary
from test_experiments_craze import build_module

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_win_streak_stack_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_win_streak_stack_results_oos.json",
}
WIN3 = {"exp_window_win_kill_n": 3, "exp_window_win_kill_action": "soft"}


def policies():
    return [
        ("shipped_default", {}),
        ("default_global_soft_n3", {**WIN3, "exp_window_win_kill_scope": "global"}),
        ("default_window_soft_n3", {**WIN3, "exp_window_win_kill_scope": "window"}),
        ("no_builtin_halt", {"max_consecutive_losses": 0}),
        ("no_halt_global_soft_n3", {"max_consecutive_losses": 0, **WIN3,
                                     "exp_window_win_kill_scope": "global"}),
        ("no_halt_window_soft_n3", {"max_consecutive_losses": 0, **WIN3,
                                    "exp_window_win_kill_scope": "window"}),
    ]


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"stage": 65, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "purpose": "direct stacking of shipped loss-halt and completed-win N3 policies",
              "policies": {}}
    for key in CONFIGS:
        base = params_for(key)
        result["policies"][key] = {"shipped_max_consecutive_losses":
                                   base.get("max_consecutive_losses"), "variants": {}}
        for name, flags in policies():
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"]
            row = {"flags": flags, "metrics": summary(trades),
                   "win_streak_stats": out.get("win_window_kill_stats", {})}
            result["policies"][key]["variants"][name] = row
            g = row["metrics"]["gross"]; n = row["metrics"]["net"]; st = row["win_streak_stats"]
            print(f"{scope.upper():3} {key:36} {name:26} n={g['n']:3d} "
                  f"G={g['sum_r']:+8.1f} N={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} "
                  f"WR={g['wr_pct']:5.1f}% PF={g['pf']:.2f} DD={n['max_dd']:5.1f} "
                  f"trig={st.get('triggered', 0):3d} block={st.get('blocked_entries', 0):3d} "
                  f"R3+={g['runners_3r']:3d} R10+={g['runners_10r']:2d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 185, flush=True)
        print(f"  WIN-STREAK DEFAULT STACKING — BYBIT {scope.upper()}", flush=True)
        print("=" * 185, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
