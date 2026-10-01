"""Active B2/FLIP routing arm for the loss-streak opposite-swing thesis.

The normal champion/king configurations use atr_high routing, so their
regime-streak rows collapse to the FLIP lane. This arm changes only the
routing mode to b2_vs_flip_chop and compares the same Bybit-only policies
within that explicit B2/FLIP architecture. It is diagnostic, not a candidate
configuration recommendation.
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

from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from exp_thesis_streak_reversal import LEVELS, MODES, load_scope, metrics, tagged

OUT_IS = ROOT / "backtest/tests/_thesis_streak_reversal_b2flip_results_is.json"
OUT_OOS = ROOT / "backtest/tests/_thesis_streak_reversal_b2flip_results_oos.json"
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"stage": "9B", "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "routing_mode": "b2_vs_flip_chop",
              "note": "explicit B2/FLIP arm; normal champion/king routing is atr_high",
              "variants": {}}
    for key in CONFIGS:
        base = {**BP, **EXPERIMENTS[key]["params"], "mode": "b2_vs_flip_chop"}
        base.setdefault("exp_partial_r", 0.0)
        policies = [
            ("exact_baseline", {}),
            ("no_builtin_halt", {"max_consecutive_losses": 0}),
            ("causal_skip_3", {"max_consecutive_losses": 0,
                                "exp_loss_streak_n": 3,
                                "exp_loss_streak_mode": "global", "exp_loss_streak_action": "skip"}),
        ]
        policies += [
            (f"{mode}_opposite_{n}", {"max_consecutive_losses": 0,
                                      "exp_loss_streak_n": n,
                                      "exp_loss_streak_mode": mode,
                                      "exp_loss_streak_action": "opposite"})
            for mode in MODES for n in LEVELS
        ]
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
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    all_result = {"stage": "9B", "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 115, flush=True)
        print(f"  ACTIVE B2/FLIP LOSS-STREAK OVERRIDE — BYBIT {scope.upper()}", flush=True)
        print("=" * 115, flush=True)
        all_result["scopes"][scope] = run_scope(scope)
        output = OUT_OOS if scope == "oos" else OUT_IS
        output.write_text(json.dumps(all_result["scopes"][scope], indent=2), encoding="utf-8")
        print(f"  wrote {output}", flush=True)


if __name__ == "__main__":
    main()
