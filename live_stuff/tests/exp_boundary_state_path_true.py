"""Stage 13 — pre-registered path-true weekly acceptance policy test.

Bybit BTCUSDT perpetual only. The only policy variants are:
- baseline
- skip weekly accepted_then_back_inside
- weekly accepted_now_only

The state is recomputed causally inside the entry gate on every candidate.
No monthly/EMA variants and no threshold sweep. Production code is untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_boundary_state_path_true_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_boundary_state_path_true_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
VARIANTS = (
    ("baseline", ""),
    ("skip_weekly_accepted_then_back_inside", "skip_back_inside"),
    ("weekly_accepted_now_only", "accepted_now_only"),
)


def stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for value in xs:
        cum += value
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if value > 0:
            ws += 1
            ls = 0
        else:
            ls += 1
            ws = 0
        mls = max(mls, ls)
        mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(xs),
        "sum_r": round(sum(xs), 4),
        "avg_r": round(sum(xs) / len(xs), 6),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(aw, 4),
        "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4),
        "max_loss_streak": mls,
        "max_win_streak": mws,
        "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
    }


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    return {
        "gross": stats(gross),
        "net": stats(net),
        "cost_and_funding": round(sum(gross) - sum(net), 4),
        "runners": {
            str(th): {
                "n": sum(r >= th for r in gross),
                "r": round(sum(r for r in gross if r >= th), 4),
            }
            for th in (2.0, 3.0, 5.0, 10.0)
        },
    }


def trade_key(trade):
    return (int(trade["entry_idx"]), 1 if trade.get("dir") == "long" else -1)


def path_shift(baseline, candidate):
    b = {trade_key(t): t for t in baseline}
    c = {trade_key(t): t for t in candidate}
    common = set(b) & set(c)
    return {
        "baseline_trades": len(b),
        "candidate_trades": len(c),
        "common_entries": len(common),
        "missing_entries": len(set(b) - set(c)),
        "new_entries": len(set(c) - set(b)),
        "common_entry_pct": round(100.0 * len(common) / max(len(b), 1), 3),
        "gross_delta_common": round(sum(
            float(c[k].get("r_multiple") or 0.0) - float(b[k].get("r_multiple") or 0.0)
            for k in common
        ), 4),
    }


def state_summary(rows):
    counts = Counter(str(r.get("state")) for r in rows)
    allowed = Counter(str(r.get("state")) for r in rows if r.get("allowed"))
    blocked = Counter(str(r.get("state")) for r in rows if not r.get("allowed"))
    return {
        "candidate_rows": len(rows),
        "states": dict(sorted(counts.items())),
        "allowed_states": dict(sorted(allowed.items())),
        "blocked_states": dict(sorted(blocked.items())),
        "blocked_total": sum(1 for r in rows if not r.get("allowed")),
    }



def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": 13,
        "instrument": "BTCUSDT_BYBIT",
        "scope": scope,
        "pre_registered": True,
        "weekly_only": True,
        "definitions": {
            "accepted_now": "current developing week traded beyond prior completed weekly boundary and has a completed 1h close beyond it; entry remains outside the prior boundary",
            "accepted_then_back_inside": "same causal boundary acceptance occurred, but the entry price is back inside the prior completed weekly range",
            "policy": "state is evaluated at signal entry instant; skipped candidates never enter the actual chain",
        },
        "configs": {},
    }
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        cfg_result = {"description": cfg.get("desc", ""), "variants": {}}
        baseline_trades = None
        for name, action in VARIANTS:
            variant_params = {**params}
            if action:
                variant_params["exp_weekly_state_action"] = action
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **variant_params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            if name == "baseline":
                baseline_trades = trades
            rows = out.get("weekly_state_rows", []) if isinstance(out, dict) else []
            row = {
                "action": action,
                "trade_count": len(trades),
                "metrics": trade_metrics(trades),
                "state_rows": state_summary(rows),
                "path_shift_vs_baseline": path_shift(baseline_trades or [], trades),
            }
            cfg_result["variants"][name] = row
            g = row["metrics"]["gross"]
            n = row["metrics"]["net"]
            print(
                f"  {scope.upper():3} {key:34} {name:38} n={g['n']:3d} "
                f"gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} "
                f"avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% "
                f"PF={g['pf']:4.2f} DD={g['max_dd']:5.1f} "
                f"blocked={row['state_rows']['blocked_total']:3d}",
                flush=True,
            )
        result["configs"][key] = cfg_result
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 145, flush=True)
        print(f"  STAGE 13 WEEKLY ACCEPTANCE PATH-TRUE TEST — BYBIT {scope.upper()}", flush=True)
        print("=" * 145, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
