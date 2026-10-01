"""Bybit-only post-MFE 5m Walker opposition counterfactual.

Completed 5m bars are aligned to each 15m trade. After cumulative favorable
excursion reaches 0.5R, 1R, or 2R, the first opposing completed 5m Walker
state defines a gross-R full-exit and 50%-de-risk counterfactual. This is
diagnostic only and does not claim path-true net results.
"""
from __future__ import annotations

import argparse
import bisect
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import params_for
from exp_thesis_5m_opposition import load_5m, build_5m_state

OUT = {
    "is": ROOT / "backtest/tests/_thesis_5m_post_mfe_exit_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_5m_post_mfe_exit_results_oos.json",
}
THRESHOLDS = (0.5, 1.0, 2.0)
CONFIGS = (
    ("pure_v18_single", params_for("pure_v18_single")),
    ("pure_v18_multi", params_for("pure_v18_multi")),
    ("fullstack_single", {**BP, **EXPERIMENTS["fullstack_wage10_cd0_single_sw10"]["params"]}),
    ("champion_multi", {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}),
    ("utcsat_multi", {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}),
)


def metrics(values):
    xs = [float(x) for x in values]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]; losses = [x for x in xs if x <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
            "losses": len(losses), "wr_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 6), "avg_loss": round(al, 6),
            "payoff": round(aw / abs(al), 6) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 6) if losses else 0.0,
            "median": round(statistics.median(xs), 6),
            "runners_3r": sum(x >= 3.0 for x in xs),
            "runners_5r": sum(x >= 5.0 for x in xs),
            "runners_10r": sum(x >= 10.0 for x in xs)}


def event_for(trade, c5, states, state_ts, threshold):
    entry = int(trade["entry_ts"]); entry_instant = entry + 900
    exit_ts = int(trade.get("exit_ts") or entry)
    direction = 1 if trade.get("dir") == "long" else -1
    entry_px = float(trade["entry_price"]); risk = max(abs(entry_px - float(trade["sl"])), 1e-9)
    j = bisect.bisect_right(state_ts, entry_instant) - 1
    if j < 0 or j >= len(states):
        return None
    cumulative_mfe = 0.0
    for k in range(j + 1, len(states)):
        state = states[k]
        if state is None or state["close_ts"] <= entry_instant or state["close_ts"] > exit_ts:
            continue
        c = c5[k]
        bar_mfe = ((c["high"] - entry_px) if direction > 0 else (entry_px - c["low"])) / risk
        cumulative_mfe = max(cumulative_mfe, bar_mfe)
        opposed = ((direction > 0 and state["direction"] == "down") or
                   (direction < 0 and state["direction"] == "up"))
        if cumulative_mfe >= threshold and opposed:
            exit_r = ((c["close"] - entry_px) if direction > 0 else (entry_px - c["close"])) / risk
            return {"event_idx": k, "event_close_ts": int(state["close_ts"]),
                    "mfe_r": round(cumulative_mfe, 6), "exit_r": round(exit_r, 6),
                    "opposition_direction": state["direction"]}
    return None



def run(scope):
    if scope == "is":
        data = get_data(); identity_gate(data, build_module())
    else:
        from test_4_new_concepts import load_fine_1m, load_unseen
        from src.btc.btc_routes import _compute_swings
        from engine.v18_params import SWING
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        data = {"c15": c15, "c1h": c1h,
                "sw10": _compute_swings(f1h, "continuous", min_bars=10),
                "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    c5 = load_5m(scope); states = build_5m_state(c5); state_ts = [x["close_ts"] for x in states]
    sim = build_module(); result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
                                     "policy": "first completed 5m Walker opposition after cumulative MFE threshold",
                                     "thresholds_r": THRESHOLDS,
                                     "counterfactual_pnl": "gross R only; not path-true net",
                                     "data_5m": {"rows": len(c5), "start": c5[0]["ts"], "end": c5[-1]["ts"]},
                                     "configs": {}}
    for name, params in CONFIGS:
        params = dict(params); params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        all_gross = [float(t.get("r_multiple") or 0.0) for t in trades]
        all_net = [net_r([t]) for t in trades]
        cfg_result = {"trade_count": len(trades), "baseline_gross": metrics(all_gross),
                      "baseline_net": metrics(all_net), "thresholds": {}}
        for threshold in THRESHOLDS:
            rows = []
            for t in trades:
                e = event_for(t, c5, states, state_ts, threshold)
                if e is None:
                    continue
                actual = float(t.get("r_multiple") or 0.0)
                rows.append({"event": e, "actual_r": actual, "full_exit_r": e["exit_r"],
                             "half_exit_r": 0.5 * e["exit_r"] + 0.5 * actual,
                             "entry_ts": int(t["entry_ts"]), "dir": t.get("dir")})
            cell = {"event_count": len(rows), "actual": metrics([r["actual_r"] for r in rows]),
                    "full_exit": metrics([r["full_exit_r"] for r in rows]),
                    "half_exit": metrics([r["half_exit_r"] for r in rows]), "rows": rows}
            cell["full_exit_delta_r"] = round(cell["full_exit"]["sum_r"] - cell["actual"]["sum_r"], 6)
            cell["half_exit_delta_r"] = round(cell["half_exit"]["sum_r"] - cell["actual"]["sum_r"], 6)
            cfg_result["thresholds"][f"{threshold:g}R"] = cell
            print(f"  {name:20} threshold={threshold:g}R events={len(rows):3d} "
                  f"actual={cell['actual']['sum_r']:+8.1f} full={cell['full_exit']['sum_r']:+8.1f} "
                  f"d={cell['full_exit_delta_r']:+7.1f} half={cell['half_exit']['sum_r']:+8.1f} "
                  f"d={cell['half_exit_delta_r']:+7.1f}", flush=True)
        result["configs"][name] = cfg_result
    output = OUT[scope]
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    for scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        run(scope)
