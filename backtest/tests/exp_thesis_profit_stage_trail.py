"""Stage 21 — Bybit-only profit-stage trailing study.

Normal v18 structural trail remains active. Once a trade's prior completed
1m peak reaches a trigger R, a causal peak-distance stage stop is armed for
subsequent 1m bars. Existing structural stops are never loosened. This is
separate from half+delay1 and from moving-average trailing.
"""
from __future__ import annotations

import argparse
import bisect
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
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_trail_slower import load_scope, run

OUT = {
    "is": ROOT / "backtest/tests/_thesis_profit_stage_trail_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_profit_stage_trail_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
ARMS = [("baseline", {})]
for trigger in (3.0, 4.0, 5.0, 6.0):
    for distance in (0.5, 1.0, 2.0):
        ARMS.append((f"stage_{trigger:g}R_{distance:g}R", {
            "exp_profit_stage_r": trigger,
            "exp_profit_stage_distance_r": distance,
        }))
ARMS.append(("tight_5R_0.25R", {
    "exp_profit_stage_r": 5.0,
    "exp_profit_stage_distance_r": 0.25,
}))


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
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) != 0 else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws,
        "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
        "runners_3r": sum(x >= 3.0 for x in xs),
        "runners_5r": sum(x >= 5.0 for x in xs),
        "runners_10r": sum(x >= 10.0 for x in xs),
    }


def path_mfe(trade, data):
    fine = data["fine"]
    fine_ts = data.get("_fine_ts")
    if fine_ts is None:
        fine_ts = [int(c["ts"]) for c in fine]
        data["_fine_ts"] = fine_ts
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if start >= end:
        return None
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    highs = [float(fine[k]["high"]) for k in range(start, end)]
    lows = [float(fine[k]["low"]) for k in range(start, end)]
    if trade.get("dir") == "long":
        mfe = (max(highs) - entry) / risk
        mae = (entry - min(lows)) / risk
    else:
        mfe = (entry - min(lows)) / risk
        mae = (max(highs) - entry) / risk
    r = float(trade.get("r_multiple") or 0.0)
    return {"mfe_r": mfe, "mae_r": mae,
            "giveback_r": max(0.0, mfe - max(0.0, r)),
            "bars": end - start}


def metrics(trades, data):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    net_total = net_r(trades)
    net_stats = stats(net)
    net_stats["sum_r"] = round(net_total, 6)
    net_stats["avg_r"] = round(net_total / len(trades), 6) if trades else 0.0
    net_stats["net_total"] = round(net_total, 6)
    paths = [path_mfe(t, data) for t in trades]
    paths = [p for p in paths if p is not None]
    years_g = defaultdict(float); years_n = defaultdict(float)
    for t, g, n in zip(trades, gross, net):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        years_g[year] += g; years_n[year] += n
    return {
        "gross": stats(gross), "net": net_stats,
        "cost_and_funding": round(sum(gross) - net_total, 6),
        "mfe": stats([p["mfe_r"] for p in paths]),
        "mae": stats([p["mae_r"] for p in paths]),
        "giveback": stats([p["giveback_r"] for p in paths]),
        "path_bars": stats([p["bars"] for p in paths]),
        "stage_fired": sum(bool(t.get("profit_stage_fired")) for t in trades),
        "yearly_gross": dict(sorted(years_g.items())),
        "yearly_net": dict(sorted(years_n.items())),
        "outcomes": {k: sum(str(t.get("outcome") or "") == k for t in trades)
                      for k in sorted(set(str(t.get("outcome") or "") for t in trades))},
    }


def _checkpoint_payload(scope, key, result):
    return {"stage": 21, "instrument": "BTCUSDT_BYBIT", "scope": scope,
            "definition": "causal prior-completed-1m peak trigger; peak-distance stage stop; structural trail remains active",
            "pre_registered": True, "arms": [{"name": n, "flags": f} for n, f in ARMS],
            "partial": True, "configs": {key: result}}


def _write_json_atomic(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def run_config(data, sim, key, checkpoint=None, scope="is"):
    params = {**BP, **EXPERIMENTS[key]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    result = {"baseline": None, "arms": {}}
    if checkpoint is not None and checkpoint.exists():
        previous = json.loads(checkpoint.read_text(encoding="utf-8"))
        if key in previous.get("configs", {}):
            result = previous["configs"][key]
    for name, flags in ARMS:
        if name in result["arms"]:
            print(f"  CONFIG {key:38} {name:14} RESUME skip completed", flush=True)
            continue
        trades = run(sim, data, params, **flags)
        m = metrics(trades, data)
        if name == "baseline":
            result["baseline"] = m
        row = {"flags": flags, "metrics": m}
        if name != "baseline":
            if result["baseline"] is None:
                raise RuntimeError("baseline must complete before an arm")
            base = result["baseline"]
            row["delta_vs_baseline"] = {
                "gross_r": round(m["gross"]["sum_r"] - base["gross"]["sum_r"], 6),
                "net_r": round(m["net"]["sum_r"] - base["net"]["sum_r"], 6),
                "trade_count": m["gross"]["n"] - base["gross"]["n"],
            }
        result["arms"][name] = row
        if checkpoint is not None:
            _write_json_atomic(checkpoint, _checkpoint_payload(scope, key, result))
        g = m["gross"]; n = m["net"]
        print(f"  CONFIG {key:38} {name:14} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:5.2f} DD={g['max_dd']:5.1f} stage={m['stage_fired']:3d} R3+={g['runners_3r']:3d} R5+={g['runners_5r']:3d} R10+={g['runners_10r']:3d}", flush=True)
    return result


def run_scope(scope, data, sim):
    result = {"stage": 21, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "definition": "causal prior-completed-1m peak trigger; peak-distance stage stop; structural trail remains active",
              "pre_registered": True, "arms": [{"name": n, "flags": f} for n, f in ARMS],
              "configs": {}}
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        result["configs"][key] = {"baseline": None, "arms": {}}
        for name, flags in ARMS:
            trades = run(sim, data, params, **flags)
            m = metrics(trades, data)
            if name == "baseline":
                result["configs"][key]["baseline"] = m
            row = {"flags": flags, "metrics": m}
            if name != "baseline":
                base = result["configs"][key]["baseline"]
                row["delta_vs_baseline"] = {
                    "gross_r": round(m["gross"]["sum_r"] - base["gross"]["sum_r"], 6),
                    "net_r": round(m["net"]["sum_r"] - base["net"]["sum_r"], 6),
                    "trade_count": m["gross"]["n"] - base["gross"]["n"],
                }
            result["configs"][key]["arms"][name] = row
            g = m["gross"]; n = m["net"]
            print(f"  {scope.upper():3} {key:38} {name:14} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:5.2f} DD={g['max_dd']:5.1f} stage={m['stage_fired']:3d} R3+={g['runners_3r']:3d} R5+={g['runners_5r']:3d} R10+={g['runners_10r']:3d}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    parser.add_argument("--config", choices=CONFIGS, default=None)
    args = parser.parse_args()
    if args.config:
        if args.scope == "both":
            parser.error("--config requires --scope is or oos")
        data = load_scope(args.scope)
        sim = build_module()
        started = time.time()
        output = ROOT / f"backtest/tests/_thesis_profit_stage_trail_results_{args.scope}_{args.config}.json"
        config_result = run_config(data, sim, args.config, checkpoint=output, scope=args.scope)
        result = {"stage": 21, "instrument": "BTCUSDT_BYBIT", "scope": args.scope,
                  "definition": "causal prior-completed-1m peak trigger; peak-distance stage stop; structural trail remains active",
                  "pre_registered": True, "arms": [{"name": n, "flags": f} for n, f in ARMS],
                  "partial": False, "configs": {args.config: config_result}}
        result["elapsed_sec"] = round(time.time() - started, 2)
        _write_json_atomic(output, result)
        print(f"  wrote {output}", flush=True)
        return
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    for scope in scopes:
        print("=" * 150, flush=True)
        print(f"  STAGE 21 PROFIT-STAGE TRAIL — BYBIT {scope.upper()}", flush=True)
        print("=" * 150, flush=True)
        data = load_scope(scope)
        started = time.time()
        result = run_scope(scope, data, sim)
        result["elapsed_sec"] = round(time.time() - started, 2)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
