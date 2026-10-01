"""Bybit-only HTF-window opportunity-budget autopsy.

Tests the thesis that an HTF window is a small campaign: keep opening LTF
positions only while the window is still under a realized/marked R budget, then
let surviving positions run through the normal structural trail and 16-day HTF
cap. The gate is causal and blocks new entries only; it never closes an
existing position. Diagnostic only; production engine is untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT_IS = ROOT / "backtest/tests/_thesis_window_budget_results_is.json"
OUT_OOS = ROOT / "backtest/tests/_thesis_window_budget_results_oos.json"
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
VARIANTS = (
    ("baseline", {}),
    ("entry_cap_1", {"exp_window_entry_cap": 1}),
    ("entry_cap_2", {"exp_window_entry_cap": 2}),
    ("entry_cap_3", {"exp_window_entry_cap": 3}),
    ("realized_r_cap_1", {"exp_window_r_cap": 1.0}),
    ("realized_r_cap_2", {"exp_window_r_cap": 2.0}),
    ("realized_r_cap_3", {"exp_window_r_cap": 3.0}),
    ("marked_r_cap_1", {"exp_window_r_cap": 1.0, "exp_window_budget_mode": "marked"}),
    ("marked_r_cap_2", {"exp_window_r_cap": 2.0, "exp_window_budget_mode": "marked"}),
    ("marked_r_cap_3", {"exp_window_r_cap": 3.0, "exp_window_budget_mode": "marked"}),
)


def _values_summary(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    loss_streak = win_streak = max_loss_streak = max_win_streak = 0
    for value in xs:
        cum += value
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if value > 0:
            win_streak += 1
            loss_streak = 0
        else:
            loss_streak += 1
            win_streak = 0
        max_loss_streak = max(max_loss_streak, loss_streak)
        max_win_streak = max(max_win_streak, win_streak)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
            "losses": len(losses), "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(avg_win, 4), "avg_loss": round(avg_loss, 4),
            "payoff": round(avg_win / abs(avg_loss), 4) if avg_loss else 0.0,
            "profit_factor": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": max_loss_streak,
            "max_win_streak": max_win_streak,
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
            "median": round(statistics.median(xs), 6)}


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years_gross = defaultdict(float)
    years_net = defaultdict(float)
    for trade, g, n in zip(trades, gross, net):
        year = str(trade.get("exit_date") or trade.get("entry_date") or "")[:4]
        years_gross[year] += g
        years_net[year] += n
    return {"gross": _values_summary(gross), "net": _values_summary(net),
            "total_cost_and_funding_r": round(sum(gross) - sum(net), 4),
            "yearly_gross": dict(sorted(years_gross.items())),
            "yearly_net": dict(sorted(years_net.items()))}


def window_metrics(trades):
    grouped = defaultdict(list)
    for trade in trades:
        key = trade.get("window_key")
        if key:
            grouped[str(key)].append(trade)
    rows = []
    for key, group in grouped.items():
        gross = [float(t.get("r_multiple") or 0.0) for t in group]
        net = [net_r([t]) for t in group]
        rows.append({"window_key": key, "entries": len(group),
                     "gross_r": round(sum(gross), 4), "net_r": round(sum(net), 4),
                     "avg_gross_r": round(sum(gross) / len(group), 6),
                     "avg_net_r": round(sum(net) / len(group), 6),
                     "wins": sum(x > 0 for x in gross), "losses": sum(x <= 0 for x in gross),
                     "win_rate_pct": round(100.0 * sum(x > 0 for x in gross) / len(group), 3),
                     "first_entry_ts": min(int(t["entry_ts"]) for t in group),
                     "last_entry_ts": max(int(t["entry_ts"]) for t in group)})
    return rows


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
        return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}
    data = get_data()
    identity_gate(data, build_module())
    return data


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "policy": "stop new LTF entries after parent HTF window budget; existing positions unchanged",
              "variants": {}}
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        base_params = {**BP, **cfg["params"]}
        base_params.setdefault("exp_partial_r", 0.0)
        result["variants"][key] = {}
        for name, flags in VARIANTS:
            params = {**base_params, **flags}
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            result["variants"][key][name] = {
                "flags": flags, "trade_count": len(trades),
                "metrics": trade_metrics(trades), "windows": window_metrics(trades)}
            m = result["variants"][key][name]["metrics"]
            print(f"  {scope.upper():3} {key:24} {name:18} n={m['gross']['n']:3d} "
                  f"gross={m['gross']['sum_r']:+8.1f} net={m['net']['sum_r']:+8.1f} "
                  f"avgR={m['gross']['avg_r']:+.3f} WR={m['gross']['win_rate_pct']:5.1f}%", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    all_result = {"stage": 8, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 110, flush=True)
        print(f"  HTF WINDOW OPPORTUNITY BUDGET — BYBIT {scope.upper()}", flush=True)
        print("=" * 110, flush=True)
        all_result["scopes"][scope] = run_scope(scope)
        output = OUT_OOS if scope == "oos" else OUT_IS
        output.write_text(json.dumps(all_result["scopes"][scope], indent=2), encoding="utf-8")
        print(f"  wrote {output}", flush=True)


if __name__ == "__main__":
    main()

