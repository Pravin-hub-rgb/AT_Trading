"""Bybit-only HTF boundary-state autopsy for single and multi v18 references.

Descriptive only. Reconstructs causal prior completed week/month ranges,
developing-range location, boundary acceptance/rejection, daily/4h EMA distance
and slope, range expansion, and compares cohort quality for single and multi.
No production code or strategy parameters are changed.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
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

OUT = {
    "is": ROOT / "backtest/tests/_thesis_boundary_state_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_boundary_state_results_oos.json",
}
CONFIGS = ("fullstack_wage10_cd0_single_sw10", "champion_multi_sw10", "utcsat_multi_sw10")


def utc_dt(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def period_start(ts, period):
    dt = utc_dt(ts)
    if period == "week":
        return int((dt - timedelta(days=dt.weekday(), hours=dt.hour,
                                     minutes=dt.minute, seconds=dt.second,
                                     microseconds=dt.microsecond)).timestamp())
    first = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(first.timestamp())


def previous_start(ts, period):
    dt = utc_dt(ts)
    if period == "week":
        return period_start(ts, "week") - 7 * 86400
    first = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month = first - timedelta(days=1)
    return int(prev_month.replace(day=1).timestamp())


def obs_ts(trade):
    return int(trade["entry_ts"]) + 900


def completed_hours(c1h, cutoff):
    return [c for c in c1h if int(c["ts"]) + 3600 <= cutoff]


def period_bars(c15, start, cutoff):
    return [c for c in c15 if start <= int(c["ts"]) < cutoff]


def range_stats(bars):
    if not bars:
        return {"high": None, "low": None, "close": None, "first_ts": None, "last_ts": None}
    return {"high": max(float(c["high"]) for c in bars),
            "low": min(float(c["low"]) for c in bars),
            "close": float(bars[-1]["close"]),
            "first_ts": int(bars[0]["ts"]), "last_ts": int(bars[-1]["ts"])}


def ema(values, span):
    if not values:
        return None
    alpha = 2.0 / (span + 1.0)
    x = float(values[0])
    for v in values[1:]:
        x = alpha * float(v) + (1.0 - alpha) * x
    return x


def true_ranges(candles):
    out = []
    prev = None
    for c in candles:
        hi, lo = float(c["high"]), float(c["low"])
        tr = hi - lo if prev is None else max(hi - lo, abs(hi - prev), abs(lo - prev))
        out.append(tr)
        prev = float(c["close"])
    return out


def atr(candles, n=14):
    tr = true_ranges(candles)
    return sum(tr[-n:]) / min(n, len(tr)) if tr else 0.0



def aggregate_hours(hours, bucket_hours, cutoff):
    groups = defaultdict(list)
    for c in hours:
        bucket = (int(c["ts"]) // (bucket_hours * 3600)) * bucket_hours * 3600
        if bucket + bucket_hours * 3600 > cutoff:
            continue
        groups[bucket].append(c)
    out = []
    for start in sorted(groups):
        bars = sorted(groups[start], key=lambda x: int(x["ts"]))
        out.append({"ts": start, "date": bars[-1]["date"],
                    "open": float(bars[0]["open"]),
                    "high": max(float(x["high"]) for x in bars),
                    "low": min(float(x["low"]) for x in bars),
                    "close": float(bars[-1]["close"])})
    return out


def ema_state(c1h, cutoff, price):
    hours = completed_hours(c1h, cutoff)
    four = aggregate_hours(hours, 4, cutoff)
    daily_groups = defaultdict(list)
    for c in hours:
        daily_groups[utc_dt(int(c["ts"])).date()].append(c)
    daily = []
    for day in sorted(daily_groups):
        bars = sorted(daily_groups[day], key=lambda x: int(x["ts"]))
        if int(bars[-1]["ts"]) + 86400 > cutoff:
            continue
        daily.append({"ts": int(bars[-1]["ts"]),
                      "high": max(float(x["high"]) for x in bars),
                      "low": min(float(x["low"]) for x in bars),
                      "close": float(bars[-1]["close"])})
    four_ema20 = ema([c["close"] for c in four], 20)
    four_ema50 = ema([c["close"] for c in four], 50)
    day_ema20 = ema([c["close"] for c in daily], 20)
    day_ema50 = ema([c["close"] for c in daily], 50)
    a4 = atr(four, 14) or atr(hours, 14) or 0.0
    ad = atr(daily, 14) or a4 or 0.0
    four_slope = ((four_ema20 - ema([c["close"] for c in four[:-5]], 20)) / a4
                  if four_ema20 is not None and len(four) > 5 and a4 else 0.0)
    day_slope = ((day_ema20 - ema([c["close"] for c in daily[:-5]], 20)) / ad
                 if day_ema20 is not None and len(daily) > 5 and ad else 0.0)
    return {"ema4h20": round(four_ema20, 6) if four_ema20 is not None else None,
            "ema4h50": round(four_ema50, 6) if four_ema50 is not None else None,
            "ema1d20": round(day_ema20, 6) if day_ema20 is not None else None,
            "ema1d50": round(day_ema50, 6) if day_ema50 is not None else None,
            "ema4h20_atr": round((price - four_ema20) / a4, 6) if four_ema20 is not None and a4 else None,
            "ema1d20_atr": round((price - day_ema20) / ad, 6) if day_ema20 is not None and ad else None,
            "ema4h20_slope_atr": round(four_slope, 6),
            "ema1d20_slope_atr": round(day_slope, 6),
            "atr4h": round(a4, 8), "atr1d": round(ad, 8)}


def boundary_state(period, trade, c15, c1h):
    cutoff = obs_ts(trade)
    current_start = period_start(cutoff, period)
    prior_start = previous_start(cutoff, period)
    prior = range_stats(period_bars(c15, prior_start, current_start))
    current = range_stats(period_bars(c15, current_start, cutoff))
    price = float(trade["entry_price"])
    if prior["high"] is None or prior["high"] <= prior["low"]:
        return {"period": period, "state": "unknown", "position": None}
    width = prior["high"] - prior["low"]
    position = (price - prior["low"]) / width
    current_hours = [c for c in completed_hours(c1h, cutoff)
                     if current_start <= int(c["ts"])]
    high_break = current["high"] is not None and current["high"] > prior["high"]
    low_break = current["low"] is not None and current["low"] < prior["low"]
    close_above = any(float(c["close"]) > prior["high"] for c in current_hours)
    close_below = any(float(c["close"]) < prior["low"] for c in current_hours)
    entry_above_high = price > prior["high"]
    entry_below_low = price < prior["low"]
    if high_break and close_above:
        state = "break_accepted_high"
        entry_state = "accepted_now" if entry_above_high else "accepted_then_back_inside"
    elif high_break:
        state = "break_rejected_high"
        entry_state = "rejected_now" if not entry_above_high else "rejected_but_close_above"
    elif low_break and close_below:
        state = "break_accepted_low"
        entry_state = "accepted_now" if entry_below_low else "accepted_then_back_inside"
    elif low_break:
        state = "break_rejected_low"
        entry_state = "rejected_now" if not entry_below_low else "rejected_but_close_below"
    elif position >= 0.85:
        state = "near_high_unbroken"
        entry_state = "near_high_unbroken"
    elif position <= 0.15:
        state = "near_low_unbroken"
        entry_state = "near_low_unbroken"
    else:
        state = "middle_of_prior_range"
        entry_state = "middle_of_prior_range"
    tests = sum(1 for c in current_hours
                if float(c["high"]) >= prior["high"] or float(c["low"]) <= prior["low"])
    return {"period": period, "state": state, "position": round(position, 6),
            "prior_high": prior["high"], "prior_low": prior["low"],
            "current_high": current["high"], "current_low": current["low"],
            "range_expansion": round((current["high"] - current["low"]) / width, 6)
            if current["high"] is not None else None,
            "boundary_tests": tests,
            "entry_state": entry_state,
            "age_hours": round((cutoff - current_start) / 3600.0, 3)}


def direction_bucket(trade, boundary):
    pos = boundary.get("position")
    if pos is None:
        return "unknown"
    side = "high" if pos >= 0.85 else "low" if pos <= 0.15 else "middle"
    return f"{trade['dir']}_{side}"


def classify_extension(trade, ema4, ema1):
    e4 = ema4.get("ema4h20_atr")
    ed = ema1.get("ema1d20_atr")
    if e4 is None:
        return "unknown"
    direction = 1 if trade["dir"] == "long" else -1
    signed4 = direction * float(e4)
    signed1 = direction * float(ed) if ed is not None else signed4
    if signed4 <= -0.5:
        return "opposite_ema"
    if signed4 <= 0:
        return "pullback_toward_ema"
    if signed4 < 1.0:
        return "aligned_near_ema"
    if signed4 < 2.0:
        return "aligned_extended"
    return "aligned_far_extended"





def add_bucket_fields(row):
    for period in ("week", "month"):
        b = row[f"{period}_boundary"]
        pos = b.get("position")
        row[f"{period}_boundary_state"] = b.get("state", "unknown")
        row[f"{period}_entry_state"] = b.get("entry_state", "unknown")
        row[f"{period}_side"] = ("near_high" if pos is not None and pos >= 0.85 else
                                  "near_low" if pos is not None and pos <= 0.15 else
                                  "middle_or_other")
        row[f"{period}_position_band"] = ("near_high" if pos is not None and pos >= 0.85 else
                                          "near_low" if pos is not None and pos <= 0.15 else
                                          "middle")
    row["week_boundary_plus_ema4h"] = f"{row['week_boundary_state']}|{row['ema4h_bucket']}"
    row["month_boundary_plus_ema1d"] = f"{row['month_boundary_state']}|{row['ema1d_bucket']}"
    return row

def stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in xs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x > 0:
            ws += 1; ls = 0
        else:
            ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 4), "avg_loss": round(al, 4),
            "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) != 0 else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls,
            "max_win_streak": mws, "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    return {"gross": stats(gross), "net": stats(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4)}


def enrich_trade(trade, c15, c1h):
    cutoff = obs_ts(trade)
    weeks = boundary_state("week", trade, c15, c1h)
    months = boundary_state("month", trade, c15, c1h)
    ema4 = ema_state(c1h, cutoff, float(trade["entry_price"]))
    ema1 = ema_state(c1h, cutoff, float(trade["entry_price"]))
    return {**trade, "week_boundary": weeks, "month_boundary": months,
            "ema4h": ema4, "ema1d": ema1,
            "ema4h_bucket": classify_extension(trade, ema4, ema1),
            "ema1d_bucket": classify_extension(trade, ema1, ema4),
            "week_side": direction_bucket(trade, weeks),
            "month_side": direction_bucket(trade, months)}


def grouped_metrics(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    return {name: trade_metrics(items) for name, items in sorted(groups.items())}



def load_scope(scope):
    if scope == "is":
        data = get_data()
        identity_gate(data, build_module())
        return data
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return {"c15": c15, "c1h": c1h, "sw15": sw15, "sw10": sw10,
            "fine": load_fine_1m(c1h[0]["ts"], c1h[-1]["ts"])}


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"stage": 12, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "configs": {}, "definitions": {
                  "near_high": "entry position >= 0.85 in prior completed range",
                  "near_low": "entry position <= 0.15 in prior completed range",
                  "accepted_break": "current period traded beyond prior boundary and has a completed 1h close beyond it",
                  "rejected_break": "current period traded beyond prior boundary but no completed 1h close beyond it",
                  "ema_distance": "(price - EMA20) / causal ATR; signed by trade direction in bucket",
              }}
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        rows = [add_bucket_fields(enrich_trade(t, data["c15"], data["c1h"])) for t in trades]
        cfg_result = {
            "description": cfg["desc"],
            "trade_count": len(rows),
            "overall": trade_metrics(rows),
            "cohorts": {},
            "feature_ranges": {},
        }
        for group_key in ("week_boundary_state", "month_boundary_state",
                          "week_entry_state", "month_entry_state",
                          "week_side", "month_side", "ema4h_bucket", "ema1d_bucket",
                          "week_boundary_plus_ema4h", "month_boundary_plus_ema1d"):
            cfg_result["cohorts"][group_key] = grouped_metrics(rows, group_key)
        for period in ("week", "month"):
            positions = [float(r[f"{period}_boundary"]["position"]) for r in rows
                         if r[f"{period}_boundary"].get("position") is not None]
            expansions = [float(r[f"{period}_boundary"]["range_expansion"]) for r in rows
                          if r[f"{period}_boundary"].get("range_expansion") is not None]
            cfg_result["feature_ranges"][period] = {
                "position": stats(positions), "range_expansion": stats(expansions),
                "boundary_tests": stats([r[f"{period}_boundary"].get("boundary_tests") for r in rows]),
                "age_hours": stats([r[f"{period}_boundary"].get("age_hours") for r in rows]),
            }
        result["configs"][key] = cfg_result
        g = cfg_result["overall"]["gross"]; n = cfg_result["overall"]["net"]
        print(f"  {scope.upper():3} {key:34} n={g['n']:3d} gross={g['sum_r']:+8.1f} net={n['sum_r']:+8.1f} avg={g['avg_r']:+.3f} WR={g['win_rate_pct']:5.1f}% PF={g['pf']:4.2f} DD={g['max_dd']:5.1f}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 120, flush=True)
        print(f"  HIGHER-TIMEFRAME BOUNDARY-STATE AUTOPSY — BYBIT {scope.upper()}", flush=True)
        print("=" * 120, flush=True)
        result = run_scope(scope)
        output = OUT[scope]
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {output}", flush=True)


if __name__ == "__main__":
    main()

