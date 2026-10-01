"""Final one-shot loss-streak reversal matrix for Bybit BTCUSDT perpetual.

This is the validated Stage 9 artifact. It includes only:
- exact baseline;
- no built-in halt;
- global one-shot opposite-swing override;
- parent-window one-shot opposite-swing override.

The earlier persistent-override and broken skip-control runs are not used.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from exp_thesis_streak_reversal import CONFIGS, LEVELS, load_scope, metrics, tagged

OUT = {
    "is": ROOT / "backtest/tests/_thesis_streak_reversal_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_streak_reversal_results_oos.json",
}


def run(scope):
    started = time.time(); data = load_scope(scope); sim = build_module()
    result = {
        "stage": 9,
        "instrument": "BTCUSDT_BYBIT",
        "scope": scope,
        "policy": "after completed-loss threshold, reject aligned LTF swings until one actual opposite swing is accepted; then resume normal aligned handling",
        "streak_counting": "only completed trades with exit_ts <= candidate entry timestamp count",
        "existing_positions": "not closed; normal structural exits continue",
        "excluded_rows": ["persistent-override pre-fix", "broken causal-skip control", "underpowered B2/FLIP lane"],
        "variants": {},
    }
    for key in CONFIGS:
        base = {**BP, **EXPERIMENTS[key]["params"]}
        base.setdefault("exp_partial_r", 0.0)
        policies = [("exact_baseline", {}), ("no_builtin_halt", {"max_consecutive_losses": 0})]
        for mode in ("global", "window"):
            for level in LEVELS:
                policies.append((f"{mode}_opposite_{level}", {
                    "max_consecutive_losses": 0,
                    "exp_loss_streak_n": level,
                    "exp_loss_streak_mode": mode,
                    "exp_loss_streak_action": "opposite",
                }))
        result["variants"][key] = {}
        for name, flags in policies:
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            row = {"flags": flags, "trade_count": len(trades),
                   "metrics": metrics(trades), "tags": tagged(trades)}
            result["variants"][key][name] = row
            g = row["metrics"]["gross"]; n = row["metrics"]["net"]
            print(f"  {scope.upper():3} {key:24} {name:22} n={g['n']:3d} "
                  f"gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} "
                  f"avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% "
                  f"opp={row['tags']['opposite_trades']:3d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos"), required=True)
    args = parser.parse_args()
    run(args.scope)
