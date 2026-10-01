"""Bybit-only loss-streak opposite-swing reversal autopsy.

Thesis: after a completed losing streak, the HTF directional window may be
stale. Reject aligned LTF swings and allow the next actual opposite LTF swing
inside that same window. This does not fabricate a reverse-direction trade and
does not alter exits. The gate is causal: only trades exited by the candidate
entry timestamp can contribute to the streak.
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

OUT_IS = ROOT / "backtest/tests/_thesis_streak_reversal_results_is.json"
OUT_OOS = ROOT / "backtest/tests/_thesis_streak_reversal_results_oos.json"
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
MODES = ("global", "window", "regime")
LEVELS = (2, 3, 4, 5)


def summary(values):
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
            ws += 1; ls = 0
        else:
            ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
            "losses": len(losses), "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 4), "avg_loss": round(al, 4),
            "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
            "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}


def metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years_g = defaultdict(float); years_n = defaultdict(float)
    for t, g, n in zip(trades, gross, net):
        y = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[y] += g; years_n[y] += n
    return {"gross": summary(gross), "net": summary(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4),
            "yearly_gross": dict(sorted(years_g.items())),
            "yearly_net": dict(sorted(years_n.items()))}


def tagged(trades):
    return {"opposite_trades": sum(bool(t.get("opposite_override")) for t in trades),
            "triggered_trades": sum(bool(t.get("loss_streak_triggered")) for t in trades),
            "max_streak_seen": max([int(t.get("loss_streak_at_entry") or 0) for t in trades] or [0]),
            "loss_streak_buckets": {str(k): summary([float(t.get("r_multiple") or 0.0) for t in trades if int(t.get("loss_streak_at_entry") or 0) == k]) for k in sorted(set(int(t.get("loss_streak_at_entry") or 0) for t in trades))}}


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    data = get_data(); identity_gate(data, build_module()); return data


def run_scope(scope):
    started = time.time(); data = load_scope(scope); sim = build_module()
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "policy": "completed-loss streak; aligned signals blocked, next opposite LTF swing allowed",
              "controls": ["exact_baseline", "no_builtin_halt", "causal_skip_3"],
              "variants": {}}
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]; base = {**BP, **cfg["params"]}; base.setdefault("exp_partial_r", 0.0)
        result["variants"][key] = {}
        policies = [("exact_baseline", {}), ("no_builtin_halt", {"max_consecutive_losses": 0}),
                    ("causal_skip_3", {"max_consecutive_losses": 0, "exp_loss_streak_n": 3, "exp_loss_streak_mode": "global", "exp_loss_streak_action": "skip"})]
        policies += [(f"{mode}_opposite_{n}", {"max_consecutive_losses": 0, "exp_loss_streak_n": n, "exp_loss_streak_mode": mode, "exp_loss_streak_action": "opposite"}) for mode in MODES for n in LEVELS]
        for name, flags in policies:
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **{**base, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            row = {"flags": flags, "trade_count": len(trades), "metrics": metrics(trades), "tags": tagged(trades)}
            result["variants"][key][name] = row
            g = row["metrics"]["gross"]; n = row["metrics"]["net"]
            print(f"  {scope.upper():3} {key:24} {name:22} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% opp={row['tags']['opposite_trades']:3d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def run_causal_skip_only(scope, output):
    data = load_scope(scope); sim = build_module()
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "policy": "causal skip-after-3 control only", "variants": {}}
    for key in CONFIGS:
        base = {**BP, **EXPERIMENTS[key]["params"], "max_consecutive_losses": 0,
                "exp_loss_streak_n": 3, "exp_loss_streak_mode": "global",
                "exp_loss_streak_action": "skip"}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **base)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        row = {"flags": {k: v for k, v in base.items() if k.startswith("exp_loss_streak") or k == "max_consecutive_losses"},
               "trade_count": len(trades), "metrics": metrics(trades), "tags": tagged(trades)}
        result["variants"][key] = row
        g = row["metrics"]["gross"]; n = row["metrics"]["net"]
        print(f"  {scope.upper():3} {key:24} causal_skip_3 n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f}", flush=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    all_result = {"stage": 9, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 115, flush=True)
        print(f"  LOSS-STREAK OPPOSITE-SWING OVERRIDE — BYBIT {scope.upper()}", flush=True)
        print("=" * 115, flush=True)
        all_result["scopes"][scope] = run_scope(scope)
        output = OUT_OOS if scope == "oos" else OUT_IS
        output.write_text(json.dumps(all_result["scopes"][scope], indent=2), encoding="utf-8")
        print(f"  wrote {output}", flush=True)


if __name__ == "__main__":
    main()
