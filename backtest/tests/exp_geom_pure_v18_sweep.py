"""Pure-v18 B1/swing-geometry path-true sweep (Bybit BTCUSDT perp).

Controls are low-filter v18, not champion/king. Each arm is rerun through the
actual engine so skipped signals can change later entries and portfolio state.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import BASE, build_module
from run_experiment import _load_fine_1m, identity_gate, net_r
from engine.v18_params import V18, V18_ENGINE
from replay_harness import load_candles
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings

OUT = {"is": ROOT / "backtest/tests/_geom_pure_v18_results_is.json",
       "oos": ROOT / "backtest/tests/_geom_pure_v18_results_oos.json"}
CONTROLS = ("pure_v18_single", "pure_v18_multi", "literal_v18_single", "literal_v18_multi")
ARMS = (
    ("baseline", {}),
    ("fresh_b1_0_1", {"exp_geom_mode": "fresh_b1", "exp_geom_b1_max": 1}),
    ("reject_stale_b1_96plus", {"exp_geom_mode": "not_stale_b1", "exp_geom_b1_min": 96}),
    ("large_swing_4atr", {"exp_geom_mode": "large_mag", "exp_geom_mag_min_atr": 4.0}),
    ("near_start_1atr", {"exp_geom_mode": "near_start", "exp_geom_start_dist_max_atr": 1.0}),
    ("fresh_b1_plus_large_swing", {"exp_geom_mode": "fresh_b1+large_mag", "exp_geom_b1_max": 1, "exp_geom_mag_min_atr": 4.0}),
    ("fresh_b1_plus_near_start", {"exp_geom_mode": "fresh_b1+near_start", "exp_geom_b1_max": 1, "exp_geom_start_dist_max_atr": 1.0}),
)


def load_data(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
    else:
        (c15, f15), (c1h, f1h) = load_candles()
        fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    sw20 = _compute_swings(f1h, "continuous", min_bars=20)
    return c1h, sw20, c15, sw15, fine


def params_for(control):
    if control.startswith("pure_v18"):
        params = dict(BASE)
        params["exp_mltf"] = control.endswith("multi")
        params["exp_partial_r"] = 0.0
        return params
    params = dict(V18)
    params.update(V18_ENGINE)
    if "rr_target" in params:
        params["htf_rr"] = params.pop("rr_target")
    params["chop_thresh"] = 61.8
    params["window_end"] = "exit"
    params["exp_mltf"] = control.endswith("multi")
    params["exp_partial_r"] = 0.0
    return params


def stats(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    nets = [net_r([t]) for t in trades]
    wins = [x for x in gross if x > 0]
    losses = [x for x in gross if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in nets:
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
    years_g = defaultdict(float)
    years_n = defaultdict(float)
    for t, g, n in zip(trades, gross, nets):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[year] += g
        years_n[year] += n
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(trades), "gross_r": round(sum(gross), 4), "net_r": round(sum(nets), 4),
        "avg_gross_r": round(sum(gross) / len(gross), 6) if gross else 0.0,
        "avg_net_r": round(sum(nets) / len(nets), 6) if nets else 0.0,
        "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / len(gross), 3) if gross else 0.0,
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "gross_pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
        "max_net_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
        "median_net_r": round(statistics.median(nets), 6) if nets else 0.0,
        "yearly_gross": dict(sorted(years_g.items())), "yearly_net": dict(sorted(years_n.items())),
        "runners": {str(k): sum(1 for x in gross if x >= k) for k in (3, 5, 10, 15)},
    }


def run_scope(scope):
    data = load_data(scope)
    sim = build_module()
    result = {}
    if scope == "is":
        identity_gate({"c1h": data[0], "sw20": data[1], "c15": data[2], "sw15": data[3]}, sim)
    for control in CONTROLS:
        base_params = params_for(control)
        result[control] = {}
        for name, flags in ARMS:
            out = sim(*data, **{**base_params, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            metrics = stats(trades)
            result[control][name] = {"flags": flags, "metrics": metrics}
            print(f"  {scope.upper():3} {control:19} {name:28} n={metrics['n']:3d} "
                  f"G={metrics['gross_r']:+8.1f} N={metrics['net_r']:+8.1f} "
                  f"avgN={metrics['avg_net_r']:+.3f} WR={metrics['win_rate_pct']:5.1f}% "
                  f"DD={metrics['max_net_dd']:5.1f}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 125, flush=True)
        print(f"PURE V18 GEOMETRY SWEEP — BYBIT {scope.upper()}", flush=True)
        print("=" * 125, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()

