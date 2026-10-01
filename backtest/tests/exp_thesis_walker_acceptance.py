"""Bybit-only Walker post-entry acceptance/rejection autopsy.

This is diagnostic only. It reconstructs causal Walker pivots at 1m, 5m,
and 15m, classifies real v18 trades, and measures counterfactual exit value.
It does not modify the production engine or apply a live gate.
"""
from __future__ import annotations

import argparse
import bisect
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
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle, WalkerEngine
from engine.v18_params import SWING

CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
OUT = {
    "is": ROOT / "backtest/tests/_thesis_walker_acceptance_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_walker_acceptance_results_oos.json",
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


def flow(candles):
    return [FlowCandle(date=c["date"], open=float(c["open"]), high=float(c["high"]),
                       low=float(c["low"]), close=float(c["close"])) for c in candles]


def aggregate_5m(candles_1m):
    """Aggregate closed 1m bars into UTC-aligned 5m OHLC bars."""
    groups = defaultdict(list)
    for c in candles_1m:
        groups[(int(c["ts"]) // 300) * 300].append(c)
    out = []
    for ts in sorted(groups):
        bars = sorted(groups[ts], key=lambda c: int(c["ts"]))
        out.append({"ts": int(ts), "date": bars[0]["date"],
                    "open": float(bars[0]["open"]),
                    "high": max(float(x["high"]) for x in bars),
                    "low": min(float(x["low"]) for x in bars),
                    "close": float(bars[-1]["close"])})
    return out


def normalize_events(events):
    """Match Walker batch finalization: exact dedupe, then alternating kinds."""
    out = []
    for e in sorted(events, key=lambda x: (x["pivot_idx"], x["seal_idx"])):
        if out and e["pivot_idx"] == out[-1]["pivot_idx"] and e["kind"] == out[-1]["kind"] and e["px"] == out[-1]["px"]:
            continue
        if out and e["kind"] == out[-1]["kind"]:
            better = e["px"] > out[-1]["px"] if e["kind"] == "H" else e["px"] < out[-1]["px"]
            if better:
                out[-1] = e
            continue
        out.append(e)
    return out



def walker_events(candles, bar_seconds):
    """Emit each sealed pivot with the close time at which it became knowable."""
    by_day = defaultdict(list)
    for idx, c in enumerate(candles):
        by_day[c["date"][:10]].append((idx, c))
    events = []
    for day in sorted(by_day):
        eng = WalkerEngine()
        day_events = []
        items = sorted(by_day[day], key=lambda x: int(x[1]["ts"]))
        for g_idx, c in items:
            for p in eng.process_bar(flow([c])[0], g_idx):
                day_events.append({"pivot_idx": int(p.idx), "seal_idx": int(g_idx),
                                   "kind": p.kind, "px": float(p.px), "sealed": bool(p.sealed),
                                   "pivot_ts": int(candles[p.idx]["ts"]),
                                   "seal_ts": int(c["ts"]) + int(bar_seconds), "time": p.time})
        tail = eng.finalize()
        if tail is not None:
            day_events.append({"pivot_idx": int(tail.idx), "seal_idx": int(items[-1][0]),
                               "kind": tail.kind, "px": float(tail.px), "sealed": False,
                               "pivot_ts": int(candles[tail.idx]["ts"]),
                               "seal_ts": int(items[-1][1]["ts"]) + int(bar_seconds), "time": tail.time})
        events.extend(normalize_events(day_events))
    return sorted(events, key=lambda e: (e["seal_ts"], e["seal_idx"], e["pivot_idx"]))


def event_index(events):
    return [int(e["seal_ts"]) for e in events]


def signed_pivot(kind, direction):
    return "H" if (direction == 1 and kind == "H") or (direction == -1 and kind == "L") else "L"


def summary(values):
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
    return {"n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "wr_pct": round(100.0 * len(wins) / len(xs), 3), "avg_win": round(aw, 4),
            "avg_loss": round(al, 4), "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
            "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}



def fine_mfe_mae(trade, fine, fine_ts):
    entry = float(trade["entry_price"]); risk = abs(entry - float(trade["sl"]))
    start = bisect.bisect_right(fine_ts, int(trade["entry_ts"]))
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if risk <= 0 or start >= end:
        return None
    direction = 1 if trade.get("dir") == "long" else -1
    mfe = mae = 0.0; mfe_ts = None; first_half = None
    for k in range(start, end):
        c = fine[k]
        fav = (float(c["high"]) - entry) if direction == 1 else (entry - float(c["low"]))
        adv = (entry - float(c["low"])) if direction == 1 else (float(c["high"]) - entry)
        if fav > mfe: mfe = fav; mfe_ts = int(c["ts"])
        mae = max(mae, adv)
        if first_half is None and fav >= 0.5 * risk:
            first_half = int(c["ts"])
    return {"mfe_r": mfe / risk, "mae_r": mae / risk, "mfe_ts": mfe_ts,
            "first_half_ts": first_half}


def pivot_features(trade, events, event_ts, fine, fine_ts):
    entry_ts = int(trade["entry_ts"]); exit_ts = int(trade.get("exit_ts") or entry_ts)
    direction = 1 if trade.get("dir") == "long" else -1
    # Only pivots sealed during the trade interval. The index is causal.
    end = bisect.bisect_right(event_ts, exit_ts)
    evs = [e for e in events[:end] if e["seal_ts"] >= entry_ts]
    favorable = []; adverse = []; failed_reclaims = 0
    max_adverse_streak = 0; adverse_streak = 0; last_fav = None
    for e in evs:
        is_fav = signed_pivot(e["kind"], direction) == "H"
        if is_fav:
            if last_fav is not None:
                extends = (e["px"] > last_fav["px"] if direction == 1 else e["px"] < last_fav["px"])
                if not extends:
                    failed_reclaims += 1
            favorable.append(e); last_fav = e; adverse_streak = 0
        else:
            adverse.append(e); adverse_streak += 1
            max_adverse_streak = max(max_adverse_streak, adverse_streak)
    fav_disp = 0.0
    for a, b in zip(evs, evs[1:]):
        if signed_pivot(b["kind"], direction) == "H":
            fav_disp += max(0.0, (b["px"] - a["px"]) * direction)
    path = fine_mfe_mae(trade, fine, fine_ts) or {"mfe_r": 0.0, "mae_r": 0.0, "mfe_ts": None, "first_half_ts": None}
    # A single adverse pivot is not rejection. Rejection is either a failed
    # favorable extension or two adverse pivots before a favorable reclaim.
    first_reject = None; strong_reject = None; adverse_run = 0
    prior_fav = None; failed_fav = None
    for e in evs:
        is_fav = signed_pivot(e["kind"], direction) == "H"
        if is_fav:
            if prior_fav is not None:
                extends = (e["px"] > prior_fav["px"] if direction == 1 else e["px"] < prior_fav["px"])
                if not extends:
                    if first_reject is None:
                        first_reject = e
                    failed_fav = e
                else:
                    failed_fav = None
            prior_fav = e; adverse_run = 0
        else:
            adverse_run += 1
            if adverse_run >= 2 and first_reject is None:
                first_reject = e
            if adverse_run >= 3 and strong_reject is None:
                strong_reject = e
            if failed_fav is not None and strong_reject is None:
                strong_reject = e
                failed_fav = None
    return {"events": evs, "favorable_count": len(favorable), "adverse_count": len(adverse),
            "failed_reclaims": failed_reclaims, "max_adverse_streak": max_adverse_streak,
            "favorable_displacement": fav_disp, "mfe": path,
            "first_reject": first_reject, "strong_reject": strong_reject}


def r_at(trade, timestamp, fine, fine_ts):
    if not fine or not fine_ts:
        return None
    entry = float(trade["entry_price"]); risk = abs(entry - float(trade["sl"]))
    idx = bisect.bisect_left(fine_ts, int(timestamp)) - 1
    if idx < 0 or risk <= 0:
        return None
    c = fine[idx]; direction = 1 if trade.get("dir") == "long" else -1
    return ((float(c["close"]) - entry) if direction == 1 else (entry - float(c["close"]))) / risk



def compact_event(event):
    return None if event is None else {"kind": event["kind"], "px": round(float(event["px"]), 8),
                                      "pivot_ts": int(event["pivot_ts"]), "seal_ts": int(event["seal_ts"])}


def classify(tf_features):
    mfe = float((tf_features.get("mfe") or {}).get("mfe_r") or 0.0)
    first_half = (tf_features.get("mfe") or {}).get("first_half_ts")
    strong = tf_features.get("strong_reject")
    if strong and mfe >= 0.5 and (first_half is None or strong["seal_ts"] > first_half):
        return "mfe_then_rejection"
    if strong:
        return "pre_mfe_rejection"
    if tf_features.get("adverse_count", 0) > 0 and tf_features.get("favorable_count", 0) > 0:
        return "healthy_pullback"
    if tf_features.get("adverse_count", 0) > 0:
        return "early_stress"
    return "immediate_acceptance"


def time_class(tf_features, first_half_ts):
    reject = tf_features.get("first_reject")
    if not reject:
        return "no_rejection"
    if first_half_ts is not None and int(reject["seal_ts"]) > int(first_half_ts):
        return "after_first_half_r"
    return "before_first_half_r"


def counterfactual_rows(trade, tf, data, fine_ts):
    entry = int(trade["entry_ts"]); actual = float(trade.get("r_multiple") or 0.0)
    candidates = {
        "reject_1m": compact_event(tf["1m"].get("first_reject")),
        "reject_5m": compact_event(tf["5m"].get("first_reject")),
        "reject_15m": compact_event(tf["15m"].get("first_reject")),
        "strong_1m": compact_event(tf["1m"].get("strong_reject")),
        "strong_5m": compact_event(tf["5m"].get("strong_reject")),
        "strong_15m": compact_event(tf["15m"].get("strong_reject")),
    }
    for name, parts in (("confirm_5m_15m", ("strong_5m", "strong_15m")),
                        ("confirm_1m_5m_15m", ("strong_1m", "strong_5m", "strong_15m"))):
        es = [candidates[p] for p in parts]
        action = max((e["seal_ts"] for e in es), default=None) if all(es) else None
        candidates[name] = {"seal_ts": action} if action is not None else None
    out = {"actual_r": actual, "candidates": {}}
    for name, event in candidates.items():
        if not event or int(event["seal_ts"]) < entry:
            continue
        rr = r_at(trade, int(event["seal_ts"]), data["fine"], fine_ts)
        if rr is None:
            continue
        out["candidates"][name] = {"seal_ts": int(event["seal_ts"]), "r_at_reject": round(rr, 6),
                                   "delta_full": round(rr - actual, 6),
                                   "delta_half": round(0.5 * (rr - actual), 6)}
    return out


def outcome_stats(rows):
    return summary([float(r["trade"].get("r_multiple") or 0.0) for r in rows])



def run_scope(scope):
    started = time.time(); data = load_scope(scope); sim = build_module()
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    c5 = aggregate_5m(data["fine"])
    ev = {"1m": walker_events(data["fine"], 60), "5m": walker_events(c5, 300), "15m": walker_events(data["c15"], 900)}
    ts = {tf: event_index(events) for tf, events in ev.items()}
    result = {"stage": 11, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "pivot_counts": {tf: len(items) for tf, items in ev.items()}, "configs": {}}
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}; params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        rows = []
        for trade in trades:
            tf = {name: pivot_features(trade, ev[name], ts[name], data["fine"], fine_ts) for name in ev}
            first_half = tf["1m"]["mfe"].get("first_half_ts")
            rows.append({"trade": trade, "tf": tf, "class": {name: classify(tf[name]) for name in tf},
                         "timing": {name: time_class(tf[name], first_half) for name in tf},
                         "counterfactual": counterfactual_rows(trade, tf, data, fine_ts)})
        def subset(field, value):
            return [r for r in rows if r[field] == value]
        by_class = {}
        by_timing = {}
        for name in ev:
            by_class[name] = {c: outcome_stats([r for r in rows if r["class"][name] == c])
                              for c in sorted(set(r["class"][name] for r in rows))}
            by_timing[name] = {c: outcome_stats([r for r in rows if r["timing"][name] == c])
                               for c in sorted(set(r["timing"][name] for r in rows))}
        cf = {"baseline_gross": round(sum(float(r["trade"].get("r_multiple") or 0.0) for r in rows), 4), "variants": {}}
        names = sorted(set(name for r in rows for name in r["counterfactual"]["candidates"]))
        for name in names:
            for mode in ("full", "half"):
                vals = []
                for r in rows:
                    c = r["counterfactual"]["candidates"].get(name)
                    actual = float(r["trade"].get("r_multiple") or 0.0)
                    if c and c.get("r_at_reject") is not None:
                        rr = float(c["r_at_reject"]); vals.append(rr if mode == "full" else 0.5 * rr + 0.5 * actual)
                    else:
                        vals.append(actual)
                cf["variants"][f"{name}_{mode}"] = summary(vals)
        result["configs"][key] = {"trade_count": len(trades), "actual": outcome_stats(rows),
                                  "actual_net": round(net_r(trades), 4), "by_class": by_class,
                                  "by_timing": by_timing, "counterfactual": cf}
        result["configs"][key]["trade_features"] = [{"trade_no": r["trade"].get("trade_no"),
                                                     "class": r["class"], "timing": r["timing"],
                                                     "counterfactual": r["counterfactual"]} for r in rows]
        print(f"  {scope.upper()} {key}: n={len(trades)} gross={result['configs'][key]['actual']['sum_r']:+.1f}R net={result['configs'][key]['actual_net']:+.1f}R", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result





def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args(); scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 110, flush=True); print(f"  WALKER ACCEPTANCE AUTOPSY — BYBIT {scope.upper()}", flush=True); print("=" * 110, flush=True)
        result = run_scope(scope); OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()

