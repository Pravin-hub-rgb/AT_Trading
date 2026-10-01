"""Bybit-only loss-triggered HTF-window kill sweep.

At a completed losing streak N, the current parent HTF window is invalidated
for new LTF entries. Soft leaves existing positions untouched. Hard closes
active positions in that window at the causal trigger timestamp. The next
parent HTF window resumes normally. This is test-only and path-true.
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
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "backtest/tests/_thesis_loss_window_kill_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_loss_window_kill_results_oos.json",
}
CONFIGS = (
    "pure_v18_single", "pure_v18_multi",
    "literal_v18_single", "literal_v18_multi",
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10", "utcsat_multi_sw10",
)
LEVELS = (2, 3, 4, 5)
SCOPES = ("window", "global")
ACTIONS = ("soft", "hard")


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


def params_for(key):
    if key.startswith("pure_") or key.startswith("literal_"):
        from exp_geom_pure_v18_sweep import params_for as pure_params
        return pure_params(key)
    return {**BP, **EXPERIMENTS[key]["params"]}


def _stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in xs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
            "losses": len(losses), "wr_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 4), "avg_loss": round(al, 4),
            "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls,
            "max_win_streak": mws, "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
            "runners_3r": sum(x >= 3 for x in xs),
            "runners_5r": sum(x >= 5 for x in xs),
            "runners_10r": sum(x >= 10 for x in xs)}


def summary(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years_g = {}; years_n = {}
    for t, g, n in zip(trades, gross, net):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[year] = round(years_g.get(year, 0.0) + g, 4)
        years_n[year] = round(years_n.get(year, 0.0) + n, 4)
    return {"gross": _stats(gross), "net": _stats(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4),
            "yearly_gross": years_g, "yearly_net": years_n}


def policies():
    rows = [("baseline", {}), ("no_builtin_halt", {"max_consecutive_losses": 0})]
    for scope in SCOPES:
        for action in ACTIONS:
            for n in LEVELS:
                name = f"{scope}_{action}_n{n}"
                flags = {"max_consecutive_losses": 0,
                         "exp_window_loss_kill_n": n,
                         "exp_window_loss_kill_scope": scope,
                         "exp_window_loss_kill_action": action}
                rows.append((name, flags))
    return rows


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": 48,
        "instrument": "BTCUSDT_BYBIT",
        "scope": scope,
        "policy": "completed-loss streak kills current parent HTF window; next parent window resumes",
        "policies": {},
    }
    for key in CONFIGS:
        base = params_for(key)
        result["policies"][key] = {}
        for name, flags in policies():
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"]
            row = {
                "flags": flags,
                "metrics": summary(trades),
                "loss_window_kill_stats": out.get("loss_window_kill_stats", {}),
            }
            result["policies"][key][name] = row
            g = row["metrics"]["gross"]
            n = row["metrics"]["net"]
            st = row["loss_window_kill_stats"]
            print(f"{scope.upper():3} {key:36} {name:22} n={g['n']:3d} "
                  f"gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} "
                  f"avg={g['avg_r']:+.3f} WR={g['wr_pct']:5.1f}% "
                  f"PF={g['pf']:.2f} DD={n['max_dd']:.1f} "
                  f"trig={st.get('triggered', 0):3d} "
                  f"blocked={st.get('blocked_entries', 0):3d} "
                  f"closed={st.get('hard_closed', 0):3d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 150, flush=True)
        print(f"  LOSS-TRIGGERED HTF WINDOW KILL — BYBIT {scope.upper()}", flush=True)
        print("=" * 150, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()

