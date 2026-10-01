"""Stage 14 — causal 15m imbalance/FVG context autopsy.

Bybit BTCUSDT perpetual only. For each real v18 trade, reconstruct the most
recent three-candle 15m imbalance known at the signal-bar close and classify
whether it is aligned/opposite and unfilled/partial/filled. Descriptive only:
no thresholds, no engine change, no path-true policy adoption.
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
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = {
    "is": ROOT / "backtest/tests/_thesis_imbalance_context_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_imbalance_context_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)


def stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for value in xs:
        cum += value; peak = max(peak, cum); dd = max(dd, peak - cum)
        if value > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
            "losses": len(losses), "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 4), "avg_loss": round(al, 4),
            "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls,
            "max_win_streak": mws, "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    years = Counter(str(t.get("exit_date") or t.get("entry_date") or "")[:4] for t in trades)
    return {"gross": stats(gross), "net": stats(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4),
            "yearly_counts": dict(sorted(years.items()))}


def fvg_events(candles):
    """Return 15m FVGs, known at the right candle close."""
    events = []
    for i in range(2, len(candles)):
        left, middle, right = candles[i - 2], candles[i - 1], candles[i]
        if float(middle["low"]) > float(left["high"]):
            events.append({"direction": "bullish", "formed_idx": i,
                           "formed_ts": int(right["ts"]) + 900,
                           "lower": float(left["high"]), "upper": float(middle["low"])})
        if float(middle["high"]) < float(left["low"]):
            events.append({"direction": "bearish", "formed_idx": i,
                           "formed_ts": int(right["ts"]) + 900,
                           "lower": float(middle["high"]), "upper": float(left["low"])})
    return events


def fill_state(event, candles, entry_idx):
    start, end = event["formed_idx"] + 1, min(entry_idx, len(candles) - 1)
    lower, upper = event["lower"], event["upper"]
    if event["direction"] == "bullish":
        touched = any(float(c["low"]) <= upper for c in candles[start:end + 1])
        full = any(float(c["low"]) <= lower for c in candles[start:end + 1])
    else:
        touched = any(float(c["high"]) >= lower for c in candles[start:end + 1])
        full = any(float(c["high"]) >= upper for c in candles[start:end + 1])
    return "filled" if full else ("partial" if touched else "unfilled")


def context_for_trade(trade, candles, events):
    idx = int(trade["entry_idx"]); direction = 1 if trade.get("dir") == "long" else -1
    cutoff = int(candles[idx]["ts"]) + 900
    known = [e for e in events if e["formed_idx"] <= idx and e["formed_ts"] <= cutoff]
    if not known:
        return {"state": "no_fvg", "direction": None, "fill": None,
                "age_bars": None, "distance_atr": None, "formed_idx": None}
    event = known[-1]; lower, upper = event["lower"], event["upper"]
    fill = fill_state(event, candles, idx)
    alignment = "aligned" if ((direction == 1 and event["direction"] == "bullish") or
                              (direction == -1 and event["direction"] == "bearish")) else "opposite"
    price = float(trade["entry_price"]); lo = max(0, idx - 13)
    ranges = [float(c["high"]) - float(c["low"]) for c in candles[lo:idx + 1]]
    atr = sum(ranges) / len(ranges) if ranges else 0.0
    distance = min(abs(price - lower), abs(price - upper)) / atr if atr else None
    return {"state": alignment + "_" + fill, "direction": event["direction"],
            "fill": fill, "age_bars": idx - event["formed_idx"],
            "distance_atr": distance, "formed_idx": event["formed_idx"],
            "zone_lower": lower, "zone_upper": upper}


def analyze(data, key):
    params = {**BP, **EXPERIMENTS[key]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    out = build_module()(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                         fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    events = fvg_events(data["c15"])
    rows = [(trade, context_for_trade(trade, data["c15"], events)) for trade in trades]
    buckets = defaultdict(list)
    for trade, context in rows:
        buckets[context["state"]].append(trade)
    return {"config": key, "description": EXPERIMENTS[key].get("desc", ""),
            "trade_count": len(trades), "fvg_event_count": len(events),
            "baseline": trade_metrics(trades),
            "contexts": {name: trade_metrics(values) for name, values in sorted(buckets.items())},
            "context_counts": dict(sorted(Counter(c["state"] for _, c in rows).items()))}


def run_scope(scope):
    started = time.time(); data = load_scope(scope)
    result = {"stage": 14, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "definition": "latest causal 15m 3-candle FVG known at signal close; bullish gap if middle low > left high, bearish gap if middle high < left low",
              "configurations": {}}
    for key in CONFIGS:
        row = analyze(data, key); result["configurations"][key] = row
        print(f"\n  {scope.upper()} {key}: {row['trade_count']} trades, {row['fvg_event_count']} FVGs", flush=True)
        for state, metrics in row["contexts"].items():
            g = metrics["gross"]
            print(f"    {state:20s} n={g['n']:3d} gross={g['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:4.2f}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args(); scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 120, flush=True); print(f"  STAGE 14 IMBALANCE/FVG CONTEXT — BYBIT {scope.upper()}", flush=True); print("=" * 120, flush=True)
        result = run_scope(scope); OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
