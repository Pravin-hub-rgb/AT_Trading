"""Stage 18 — Bybit-only moving-average trailing exit autopsy.

The real v18 entry sequence and initial structural stop are preserved. The
only new exit is a completed-15m-close SMA20/50/100 close-confirmation exit,
evaluated alongside the existing structural trail. This is a path-true
read-only study for single king, champion multi, and UTC-Saturday multi.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
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
    "is": ROOT / "live_stuff/tests/_thesis_ma_trail_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_ma_trail_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
ARMS = (("baseline", 0), ("sma20", 20), ("sma50", 50), ("sma100", 100))


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
            ws += 1; ls = 0
        else:
            ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(xs), "sum_r": round(sum(xs), 4),
        "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
        "losses": len(losses), "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws, "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
    }


def metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years_g = defaultdict(float); years_n = defaultdict(float)
    for t, g, n in zip(trades, gross, net):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[year] += g; years_n[year] += n
    return {
        "gross": stats(gross), "net": stats(net),
        "cost_and_funding": round(sum(gross) - sum(net), 4),
        "yearly_gross": dict(sorted(years_g.items())),
        "yearly_net": dict(sorted(years_n.items())),
        "outcomes": dict(Counter(str(t.get("outcome") or "") for t in trades)),
        "runners": {str(th): {"n": sum(g >= th for g in gross),
                               "r": round(sum(g for g in gross if g >= th), 4)}
                     for th in (2.0, 3.0, 5.0, 10.0)},
    }


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    data = get_data()
    identity_gate(data, build_module())
    return data


def run_scope(scope):
    started = time.time(); data = load_scope(scope); sim = build_module()
    result = {
        "stage": 18, "instrument": "BTCUSDT_BYBIT", "scope": scope,
        "definition": "completed 15m close below/above SMA20/50/100; structural SL and structural trail remain active",
        "pre_registered": True, "arms": [{"name": n, "period": p} for n, p in ARMS],
        "configs": {},
    }
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}; params.setdefault("exp_partial_r", 0.0)
        result["configs"][key] = {"description": EXPERIMENTS[key].get("desc", ""), "arms": {}}
        base_metrics = None
        for name, period in ARMS:
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**params, "exp_ma_trail_period": period})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            m = metrics(trades)
            if base_metrics is None: base_metrics = m
            result["configs"][key]["arms"][name] = {
                "flags": {"exp_ma_trail_period": period}, "metrics": m,
                "delta_vs_baseline": {
                    "gross_r": round(m["gross"]["sum_r"] - base_metrics["gross"]["sum_r"], 4),
                    "net_r": round(m["net"]["sum_r"] - base_metrics["net"]["sum_r"], 4),
                    "trade_count": m["gross"]["n"] - base_metrics["gross"]["n"],
                },
            }
            g = m["gross"]; n = m["net"]
            print(f"  {scope.upper():3} {key:34} {name:8} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avgNet={(n['sum_r']/n['n'] if n['n'] else 0):+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:4.2f} DDnet={n['max_dd']:5.1f} ma={m['outcomes'].get('ma_trail', 0):3d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 145, flush=True)
        print(f"  STAGE 18 MOVING-AVERAGE TRAIL — BYBIT {scope.upper()}", flush=True)
        print("=" * 145, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()

