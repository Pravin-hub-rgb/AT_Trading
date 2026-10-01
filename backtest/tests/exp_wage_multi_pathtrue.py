"""Stage W — pre-registered path-true exp_wage_h test on champion/utcsat multi.

Pre-registration: CHECKLIST 24.69 (Deep HTF-layer autopsy) verdict — "S67
warrants exactly one pre-registered path-true exp_wage_h test on
champion/utcsat multi." Motivation: S67 window-age buckets 0-6h and 6-12h are
NEGATIVE in 12/12 cells (3 refs x 2 eras), yet champion_multi_sw10 and
utcsat_multi_sw10 carry NO window-age gate (fullstack single has wage10).

Prior art (checked before running):
  - wage24 on the multi family: TESTED DEAD (-82R, ANCHOR_BASIS_AUDIT 3d)
  - wage12 threshold on lb30/A4/lb14/OPT lanes: ruled out except OPT-cd10
  - wage6 / wage10 on champion_multi_sw10 / utcsat_multi_sw10: NEVER RUN
    (registry has wage12/wage24_utcsat entries marked "never tested on king",
    no logged result exists)

Arms: exp_wage_h in {0(identity), 6, 10, 12, 24} x 2 lanes x IS/OOS.
The gate skips a candidate when (entry_ts - window_start)/3600 < wage_h
(entry-causal; craze knob, identity no-op at 0).

PASS rule (pre-registered, strict): the SAME wage value must show
dNet > 0 vs its w0 control on ALL 4 cells (2 lanes x 2 eras), with IS maxDD
not worse by more than 2R. Anything else = family CLOSED on multi.

Read-only. Production engine untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = {
    "is": ROOT / "backtest/tests/_wage_multi_pathtrue_is.json",
    "oos": ROOT / "backtest/tests/_wage_multi_pathtrue_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
WAGES = (0, 6, 10, 12, 24)


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
        "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4),
        "max_loss_streak": mls,
        "median": round(statistics.median(xs), 6),
    }


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    return {
        "gross": stats(gross),
        "net": stats(net),
        "runners3": sum(r >= 3.0 for r in gross),
        "monsters10": sum(r >= 10.0 for r in gross),
    }


def trade_key(trade):
    return (int(trade["entry_idx"]), 1 if trade.get("dir") == "long" else -1)


def removed_bucket(baseline, candidate):
    b = {trade_key(t): t for t in baseline}
    c = {trade_key(t): t for t in candidate}
    missing = [b[k] for k in (set(b) - set(c))]
    added = [c[k] for k in (set(c) - set(b))]
    mg = [float(t.get("r_multiple") or 0.0) for t in missing]
    ag = [float(t.get("r_multiple") or 0.0) for t in added]
    return {
        "removed_n": len(missing),
        "removed_gross_r": round(sum(mg), 4),
        "removed_avg": round(sum(mg) / len(mg), 6) if mg else None,
        "removed_win_pct": round(100.0 * sum(1 for x in mg if x > 0) / len(mg), 3) if mg else None,
        "removed_runners3": sum(x >= 3.0 for x in mg),
        "added_n": len(added),
        "added_gross_r": round(sum(ag), 4),
        "common_entries": len(set(b) & set(c)),
    }


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": "W",
        "instrument": "BTCUSDT_BYBIT",
        "scope": scope,
        "pre_registered_by": "CHECKLIST 24.69",
        "pass_rule": ("same wage, dNet>0 vs w0 on ALL 4 cells "
                      "(2 lanes x 2 eras), IS maxDD not worse by >2R"),
        "configs": {},
    }
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        params.setdefault("exp_wage_h", 0)
        base_trades = None
        base_row = None
        arms = {}
        for wage in WAGES:
            p = {**params, "exp_wage_h": wage}
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **p)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            if wage == 0:
                base_trades = trades
            row = {
                "wage_h": wage,
                "metrics": trade_metrics(trades),
                "vs_w0": removed_bucket(base_trades, trades) if base_trades is not None else None,
            }
            arms[str(wage)] = row
            g = row["metrics"]["gross"]
            n = row["metrics"]["net"]
            dnet = (n["sum_r"] - base_row["metrics"]["net"]["sum_r"]) if base_row else 0.0
            print(
                "  %3s %-24s w%-3s n=%3d gross=%+8.1f net=%+8.1f avg=%+.3f "
                "WR=%5.1f%% PF=%4.2f DD=%5.1f dNet=%+7.1f removed=%3d/%+7.1f"
                % (scope.upper(), key, wage, g["n"], g["sum_r"], n["sum_r"],
                   g["avg_r"], g["win_rate_pct"], g["pf"], g["max_dd"], dnet,
                   row["vs_w0"]["removed_n"] if row["vs_w0"] else 0,
                   row["vs_w0"]["removed_gross_r"] if row["vs_w0"] else 0.0),
                flush=True,
            )
            if wage == 0:
                base_row = row
        result["configs"][key] = {"arms": arms}
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 130, flush=True)
        print("  STAGE W — PATH-TRUE exp_wage_h ON MULTI (pre-registered 24.69) — BYBIT %s"
              % scope.upper(), flush=True)
        print("=" * 130, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("  wrote %s" % OUT[scope], flush=True)


if __name__ == "__main__":
    main()
