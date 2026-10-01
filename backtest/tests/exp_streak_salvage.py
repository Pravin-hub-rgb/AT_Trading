"""Stage 9 salvage: decompose opposite-swing reversal, then test augment mode.

Phase A (decomposition): re-run Stage 9 opposite cells and split P&L into
  - opposite_override trades (the added reverse leg)
  - non-opposite trades vs exact baseline (blocked/path-changed aligned leg)

Phase B (augment): NEW action — during a completed-loss streak, allow the
  next one-shot opposite LTF swing WITHOUT blocking aligned signals.
  Aligned recovery trades stay available (Stage 9 failure mode).

Pre-registered: Bybit BTCUSDT perp only; champion_multi_sw10 + utcsat_multi_sw10;
modes global/window x levels 2/3/4/5; controls exact_baseline + no_builtin_halt;
Research comparison: report both-sides deltas; no fixed ship threshold.
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
from exp_thesis_streak_reversal import CONFIGS, LEVELS, load_scope, metrics, tagged
from run_experiment import net_r
from test_experiments_craze import build_module

OUT = {
    "is": ROOT / "backtest/tests/_streak_salvage_results_is.json",
    "oos": ROOT / "backtest/tests/_streak_salvage_results_oos.json",
}

DECOMP_CELLS = ("global_opposite_2", "window_opposite_2", "window_opposite_4")


def trade_rows(trades):
    rows = []
    for t in trades:
        rows.append({
            "entry_ts": int(t.get("entry_ts") or 0),
            "exit_ts": int(t.get("exit_ts") or 0),
            "dir": str(t.get("dir") or ""),
            "r_gross": float(t.get("r_multiple") or 0.0),
            "r_net": float(net_r([t])),
            "opposite": bool(t.get("opposite_override")),
            "streak": int(t.get("loss_streak_at_entry") or 0),
            "triggered": bool(t.get("loss_streak_triggered")),
            "kind": str(t.get("kind") or ""),
        })
    return rows


def split_decomp(trades, baseline_trades):
    opp = [t for t in trades if t.get("opposite_override")]
    non = [t for t in trades if not t.get("opposite_override")]
    base_net = sum(net_r([t]) for t in baseline_trades)
    opp_net = sum(net_r([t]) for t in opp)
    non_net = sum(net_r([t]) for t in non)
    return {
        "baseline_net": round(base_net, 4),
        "variant_net": round(opp_net + non_net, 4),
        "delta_total": round(opp_net + non_net - base_net, 4),
        "opposite": {
            "n": len(opp),
            "net": round(opp_net, 4),
            "gross": round(sum(float(t.get("r_multiple") or 0) for t in opp), 4),
            "win_rate_pct": round(
                100.0 * sum(1 for t in opp if float(t.get("r_multiple") or 0) > 0) / len(opp), 3
            ) if opp else 0.0,
        },
        "aligned_path": {
            "n": len(non),
            "net": round(non_net, 4),
            "vs_baseline": round(non_net - base_net, 4),
        },
    }


def run(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": "9salvage",
        "instrument": "BTCUSDT_BYBIT",
        "scope": scope,
        "phases": {
            "decomposition": "Stage 9 opposite cells split into opposite-leg vs aligned-path P&L",
            "augment": "one-shot opposite allowed during streak; aligned NEVER blocked",
        },
        "research_policy": "Report both-sides deltas vs exact baseline; no fixed R/year ship threshold.",
        "variants": {},
        "decomposition": {},
    }
    for key in CONFIGS:
        base = {**BP, **EXPERIMENTS[key]["params"]}
        base.setdefault("exp_partial_r", 0.0)
        result["variants"][key] = {}
        result["decomposition"][key] = {}

        policies = [
            ("exact_baseline", {}),
            ("no_builtin_halt", {"max_consecutive_losses": 0}),
        ]
        for mode in ("global", "window"):
            for level in LEVELS:
                policies.append((f"{mode}_opposite_{level}", {
                    "max_consecutive_losses": 0,
                    "exp_loss_streak_n": level,
                    "exp_loss_streak_mode": mode,
                    "exp_loss_streak_action": "opposite",
                }))
                policies.append((f"{mode}_augment_{level}", {
                    "max_consecutive_losses": 0,
                    "exp_loss_streak_n": level,
                    "exp_loss_streak_mode": mode,
                    "exp_loss_streak_action": "augment",
                }))

        baseline_trades = None
        for name, flags in policies:
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            row = {
                "flags": flags,
                "trade_count": len(trades),
                "metrics": metrics(trades),
                "tags": tagged(trades),
            }
            result["variants"][key][name] = row
            if name == "exact_baseline":
                baseline_trades = trades
            if name in DECOMP_CELLS and baseline_trades is not None:
                result["decomposition"][key][name] = split_decomp(trades, baseline_trades)
                result["decomposition"][key][name]["trades"] = trade_rows(trades)
            g = row["metrics"]["gross"]
            n = row["metrics"]["net"]
            print(f"  {scope.upper():3} {key:24} {name:22} n={g['n']:3d} "
                  f"gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} "
                  f"avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% "
                  f"opp={row['tags']['opposite_trades']:3d}", flush=True)

        # decomposition summary lines
        for cell, d in result["decomposition"][key].items():
            print(f"  {scope.upper():3} {key:24} DECOMP {cell:18} "
                  f"opp_n={d['opposite']['n']:3d} opp_net={d['opposite']['net']:+8.1f} "
                  f"aligned_d={d['aligned_path']['vs_baseline']:+8.1f} "
                  f"total_d={d['delta_total']:+8.1f}", flush=True)

    result["elapsed_sec"] = round(time.time() - started, 2)
    OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"  wrote {OUT[scope]}", flush=True)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 115, flush=True)
        print(f"  STAGE 9 SALVAGE — DECOMP + AUGMENT — BYBIT {scope.upper()}", flush=True)
        print("=" * 115, flush=True)
        run(scope)


if __name__ == "__main__":
    main()
