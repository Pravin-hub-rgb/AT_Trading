"""Stage 15 — causal pre-impulse supply/demand zone retest autopsy.

Bybit BTCUSDT perpetual only. A 15m impulse is a closed candle that closes
through the prior three-candle high/low. The preceding candle is the zone.
For each real v18 trade, classify the latest aligned/opposite impulse in a
fixed 32-bar lookback and whether the entry candle overlaps the zone. This is
descriptive only: no engine change, no threshold sweep, no adoption.
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
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_supply_demand_zone_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_supply_demand_zone_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
LOOKBACK_BARS = 32
IMPULSE_PRIOR_BARS = 3


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


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years = Counter(str(t.get("exit_date") or t.get("entry_date") or "")[:4] for t in trades)
    return {"gross": stats(gross), "net": stats(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4),
            "yearly_counts": dict(sorted(years.items()))}


def is_impulse(candles, j):
    if j < IMPULSE_PRIOR_BARS:
        return None
    c = candles[j]
    prior = candles[j - IMPULSE_PRIOR_BARS:j]
    if float(c["close"]) > max(float(x["high"]) for x in prior) and float(c["close"]) > float(c["open"]):
        return "up"
    if float(c["close"]) < min(float(x["low"]) for x in prior) and float(c["close"]) < float(c["open"]):
        return "down"
    return None


def zone_context(trade, candles):
    idx = int(trade["entry_idx"])
    if idx < 0 or idx >= len(candles) - 1:
        return {"state": "invalid_index", "alignment": None, "impulse_idx": None,
                "zone_low": None, "zone_high": None, "zone_age_bars": None,
                "entry_overlap": False, "retest_state": None}
    direction = "up" if trade.get("dir") == "long" else "down"
    start = max(IMPULSE_PRIOR_BARS, idx - LOOKBACK_BARS)
    candidates = []
    for j in range(idx - 1, start - 1, -1):
        impulse = is_impulse(candles, j)
        if impulse:
            candidates.append((j, impulse))
    if not candidates:
        return {"state": "no_recent_impulse", "alignment": None, "impulse_idx": None,
                "zone_low": None, "zone_high": None, "zone_age_bars": None,
                "entry_overlap": False, "retest_state": None}
    j, impulse = candidates[0]
    zone = candles[j - 1]
    zlo, zhi = float(zone["low"]), float(zone["high"])
    entry = candles[idx]
    entry_overlap = float(entry["low"]) <= zhi and float(entry["high"]) >= zlo
    touched_since = any(float(c["low"]) <= zhi and float(c["high"]) >= zlo
                        for c in candles[j + 1:idx])
    if entry_overlap:
        retest = "retest_now"
    elif touched_since:
        retest = "retested_then_left"
    else:
        retest = "unretested"
    alignment = "aligned" if impulse == direction else "opposite"
    return {"state": alignment + "_" + retest, "alignment": alignment,
            "impulse_idx": j, "impulse_direction": impulse,
            "zone_low": zlo, "zone_high": zhi, "zone_age_bars": idx - j,
            "entry_overlap": entry_overlap, "retest_state": retest,
            "impulse_range": round(float(candles[j]["high"]) - float(candles[j]["low"]), 8),
            "zone_range": round(zhi - zlo, 8)}


def analyze(data, key):
    params = {**BP, **EXPERIMENTS[key]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    out = build_module()(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                         fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    rows = [(trade, zone_context(trade, data["c15"])) for trade in trades]
    buckets = defaultdict(list)
    for trade, context in rows:
        buckets[context["state"]].append(trade)
    return {"config": key, "description": EXPERIMENTS[key].get("desc", ""),
            "trade_count": len(trades), "baseline": trade_metrics(trades),
            "contexts": {name: trade_metrics(values) for name, values in sorted(buckets.items())},
            "context_counts": dict(sorted(Counter(c["state"] for _, c in rows).items()))}


def run_scope(scope):
    started = time.time(); data = load_scope(scope)
    result = {"stage": 15, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "lookback_bars": LOOKBACK_BARS, "impulse_prior_bars": IMPULSE_PRIOR_BARS,
              "definition": "impulse is a closed 15m close through the prior three-bar high/low; zone is the immediately preceding candle; latest impulse in fixed lookback is classified aligned/opposite and retest state",
              "configurations": {}}
    for key in CONFIGS:
        row = analyze(data, key); result["configurations"][key] = row
        print(f"\n  {scope.upper()} {key}: {row['trade_count']} trades", flush=True)
        for state, metrics in row["contexts"].items():
            g = metrics["gross"]
            print(f"    {state:28s} n={g['n']:3d} gross={g['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:4.2f}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 130, flush=True)
        print(f"  STAGE 15 PRE-IMPULSE SUPPLY/DEMAND ZONE — BYBIT {scope.upper()}", flush=True)
        print("=" * 130, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
