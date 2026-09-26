"""Bybit BTCUSDT perpetual campaign-policy path-true sweep.

The policy gate is test-only. It blocks a new same-window add-on when the
existing same-direction cohort is red below a marked-R threshold, or when
optional caps are enabled. Existing positions are never closed by this study.
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
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_campaign_policy_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_campaign_policy_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "pure_v18_single",
    "pure_v18_multi",
    "literal_v18_single",
    "literal_v18_multi",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)


def load_scope(scope):
    if scope == "is":
        data = get_data()
        identity_gate(data, build_module())
        return data
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}


def _one(xs):
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if x > 0:
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
        "n": len(xs), "sum_r": round(sum(xs), 4),
        "avg_r": round(sum(xs) / len(xs), 6) if xs else 0.0,
        "wins": len(wins), "losses": len(losses),
        "wr_pct": round(100 * len(wins) / len(xs), 3) if xs else 0.0,
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws,
        "median": round(statistics.median(xs), 6) if xs else 0.0,
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
    }


def summary(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years_g = {}
    years_n = {}
    for t, g, n in zip(trades, gross, net):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[year] = round(years_g.get(year, 0.0) + g, 4)
        years_n[year] = round(years_n.get(year, 0.0) + n, 4)
    return {
        "gross": _one(gross), "net": _one(net),
        "cost_funding": round(sum(gross) - sum(net), 4),
        "yearly_gross": years_g, "yearly_net": years_n,
        "runners": {str(k): sum(x >= k for x in gross) for k in (3, 5, 10, 15)},
    }


def configs_for(key):
    if key.startswith("pure_") or key.startswith("literal_"):
        from exp_geom_pure_v18_sweep import params_for
        return params_for(key)
    return {**BP, **EXPERIMENTS[key]["params"]}


def policies():
    return [
        ("baseline", {}),
        ("green_require_m05", {"exp_campaign_require_marked_r": -0.5}),
        ("green_require_0", {"exp_campaign_require_marked_r": 0.0}),
        ("green_require_p05", {"exp_campaign_require_marked_r": 0.5}),
        ("max_total_1", {"exp_campaign_max_total": 1}),
        ("max_total_2", {"exp_campaign_max_total": 2}),
        ("max_total_3", {"exp_campaign_max_total": 3}),
        ("max_total_4", {"exp_campaign_max_total": 4}),
        ("max_addons_1", {"exp_campaign_max_addons": 1}),
        ("max_addons_2", {"exp_campaign_max_addons": 2}),
        ("max_addons_3", {"exp_campaign_max_addons": 3}),
        ("max_addons_4", {"exp_campaign_max_addons": 4}),
        ("block_mixed", {"exp_campaign_block_mixed": 1}),
        ("green_m05_total3", {"exp_campaign_require_marked_r": -0.5, "exp_campaign_max_total": 3}),
        ("green_0_total3", {"exp_campaign_require_marked_r": 0.0, "exp_campaign_max_total": 3}),
        ("green_m05_addons2", {"exp_campaign_require_marked_r": -0.5, "exp_campaign_max_addons": 2}),
        ("green_0_addons2", {"exp_campaign_require_marked_r": 0.0, "exp_campaign_max_addons": 2}),
    ]


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"scope": scope, "instrument": "BTCUSDT_BYBIT", "configs": {}}
    for key in CONFIGS:
        base = configs_for(key)
        result["configs"][key] = {}
        for name, flags in policies():
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"]
            row = {"flags": flags, "metrics": summary(trades),
                   "campaign_stats": out.get("campaign_stats", {})}
            result["configs"][key][name] = row
            g = row["metrics"]["gross"]
            n = row["metrics"]["net"]
            blocked = sum(row["campaign_stats"].values()) if row["campaign_stats"] else 0
            print(f"{scope.upper():3} {key:34} {name:20} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} wr={g['wr_pct']:5.1f}% pf={g['pf']:.2f} dd={n['max_dd']:.1f} blocks={blocked}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()

