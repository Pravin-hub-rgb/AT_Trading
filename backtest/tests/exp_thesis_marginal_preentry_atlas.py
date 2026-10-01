"""Stages 44-46: Bybit BTCUSDT marginal-cohort, pre-entry 5m, and loss-scene atlas.

Read-only research harness. The actual trade ledger is never modified. Stage 41
reconstructs multi cohort state at each actual entry; Stage 42 uses only completed
5m candles before the 15m entry; Stage 43 adds post-entry MFE/MAE only to describe
loss scenes. No post-entry label is converted into an entry rule in this file.
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
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import params_for
from exp_thesis_5m_opposition import load_5m, build_5m_state, CONFIGURATIONS
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "backtest/tests/_thesis_marginal_preentry_atlas_is.json",
    "oos": ROOT / "backtest/tests/_thesis_marginal_preentry_atlas_oos.json",
}
SCOPES = ("is", "oos")


def finite(x):
    try:
        return float(x) if math.isfinite(float(x)) else None
    except (TypeError, ValueError):
        return None


def stats(values):
    xs = [finite(x) for x in values if finite(x) is not None]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in xs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "wr_pct": round(100.0 * len(wins) / len(xs), 3),
            "avg_win": round(aw, 4), "avg_loss": round(al, 4),
            "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and abs(sum(losses)) > 0 else None,
            "max_dd": round(dd, 4), "max_loss_streak": mls,
            "max_win_streak": mws,
            "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}


def trade_stats(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    out = stats(net)
    out["gross"] = stats(gross)
    out["net"] = stats(net)
    out["costs_and_funding"] = round(sum(gross) - sum(net), 4)
    out["runners"] = {str(k): sum(x >= k for x in gross) for k in (3, 5, 10, 15)}
    return out


def load_scope(scope):
    if scope == "is":
        data = get_data()
        identity_gate(data, build_module())
    else:
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        data = {"c15": c15, "c1h": c1h, "sw10": sw10, "sw15": sw15,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    return data


def signal_key(row):
    sig = row["signal"]
    direction = 1 if int(sig.get("dir")) > 0 else -1
    return (int(row["entry_idx"]), direction)


def trade_key(trade):
    return (int(trade["entry_idx"]), 1 if trade.get("dir") == "long" else -1)


def mark_position(active, now_ts, fine, fine_ts):
    """Mark active positions using only 1m information available at now_ts."""
    end = bisect.bisect_right(fine_ts, now_ts) - 1
    if end < 0 or not fine:
        return []
    rows = []
    for t in active or []:
        entry = float(t["entry_price"]); sl = float(t["sl"])
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        start = bisect.bisect_left(fine_ts, int(t["entry_ts"]) + 900)
        end_i = min(end, len(fine) - 1)
        if start > end_i:
            continue
        highs = [float(fine[k]["high"]) for k in range(start, end_i + 1)]
        lows = [float(fine[k]["low"]) for k in range(start, end_i + 1)]
        d = 1 if t.get("dir") == "long" else -1
        price = float(fine[end]["close"])
        marked = ((price - entry) * d) / risk
        mfe = (((max(highs) - entry) * d) / risk if highs else 0.0)
        mae = (((entry - min(lows)) * d) / risk if lows else 0.0)
        rows.append({"dir": t.get("dir"), "entry_ts": t.get("entry_ts"),
                     "marked_r": round(marked, 6), "mfe_r": round(mfe, 6),
                     "mae_r": round(mae, 6),
                     "age_h": round((now_ts - int(t["entry_ts"])) / 3600.0, 4)})
    return rows


def enrich_path(trade, fine, fine_ts):
    entry = float(trade["entry_price"]); sl = float(trade["sl"])
    d = 1 if trade.get("dir") == "long" else -1
    risk = abs(entry - sl)
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if risk <= 0 or start >= end:
        return {"mfe_r": None, "mae_r": None, "path_bars": 0}
    highs = [float(fine[k]["high"]) for k in range(start, end)]
    lows = [float(fine[k]["low"]) for k in range(start, end)]
    mfe = ((max(highs) - entry) if d > 0 else (entry - min(lows))) / risk
    mae = ((entry - min(lows)) if d > 0 else (max(highs) - entry)) / risk
    return {"mfe_r": round(mfe, 6), "mae_r": round(mae, 6), "path_bars": end - start}


def bucket_scene(row):
    if row["wick_ratio"] is not None and row["wick_ratio"] >= 0.45:
        return "wick_rejection"
    if (row["overlap_ratio"] is not None and row["overlap_ratio"] >= 0.65) or \
       (row["efficiency"] is not None and row["efficiency"] <= 0.35):
        return "overlap_chop"
    if (row["efficiency"] is not None and row["efficiency"] >= 0.60 and
            (row["overlap_ratio"] is None or row["overlap_ratio"] <= 0.35) and
            row["directional_return"] is not None and row["directional_return"] > 0):
        return "clean_continuation"
    if row["directional_return"] is not None and row["directional_return"] < -0.001:
        return "pre_entry_pullback"
    return "other_orderly_path"


def preentry_5m(trade, c5, state_ts, states):
    entry = int(trade["entry_ts"]); instant = entry + 900
    j = bisect.bisect_right(state_ts, instant) - 1
    if j < 0:
        return {"prior5m_direction": None, "preentry_5m_opposed": None,
                "efficiency": None, "overlap_ratio": None, "body_ratio": None,
                "wick_ratio": None, "directional_return": None,
                "pullback_atr": None, "scene": "missing"}
    lo = max(0, j - 5); bars = c5[lo:j + 1]
    d = 1 if trade.get("dir") == "long" else -1
    closes = [float(c["close"]) for c in bars]
    ranges = [max(float(c["high"]) - float(c["low"]), 1e-12) for c in bars]
    bodies = [abs(float(c["close"]) - float(c["open"])) for c in bars]
    wicks = [(float(c["high"]) - max(float(c["open"]), float(c["close"])) +
              min(float(c["open"]), float(c["close"])) - float(c["low"])) for c in bars]
    changes = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    efficiency = abs(closes[-1] - closes[0]) / sum(changes) if changes else 0.0
    overlap_num = 0.0; overlap_den = 0.0
    for a, b in zip(bars, bars[1:]):
        overlap_num += max(0.0, min(float(a["high"]), float(b["high"])) -
                           max(float(a["low"]), float(b["low"])))
        overlap_den += min(float(a["high"]) - float(a["low"]),
                           float(b["high"]) - float(b["low"]))
    overlap = overlap_num / overlap_den if overlap_den else 0.0
    body = sum(bodies) / sum(ranges) if ranges else 0.0
    wick = sum(wicks) / sum(ranges) if ranges else 0.0
    recent_high = max(float(c["high"]) for c in bars)
    recent_low = min(float(c["low"]) for c in bars)
    atr = sum(ranges) / len(ranges) if ranges else 1.0
    pull = (recent_high - closes[-1]) / atr if d > 0 else (closes[-1] - recent_low) / atr
    directional_return = d * (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
    state = states[j]
    opposed = (d > 0 and state["direction"] == "down") or (d < 0 and state["direction"] == "up")
    row = {"prior5m_direction": state["direction"], "preentry_5m_opposed": int(opposed),
           "efficiency": round(efficiency, 6), "overlap_ratio": round(overlap, 6),
           "body_ratio": round(body, 6), "wick_ratio": round(wick, 6),
           "directional_return": round(directional_return, 8),
           "pullback_atr": round(pull, 6), "scene": None}
    row["scene"] = bucket_scene(row)
    return row


def cohort_rows(trades, fine, fine_ts):
    ordered = sorted(trades, key=lambda t: (int(t.get("entry_ts") or 0), int(t.get("trade_no") or 0)))
    seen_window = defaultdict(int); rows = []
    for i, t in enumerate(ordered):
        entry = int(t["entry_ts"]); direction = 1 if t.get("dir") == "long" else -1
        wk = t.get("window_key")
        active = [p for p in ordered[:i] if int(p.get("exit_ts") or p.get("entry_ts") or entry) > entry]
        same = [p for p in active if (1 if p.get("dir") == "long" else -1) == direction]
        opposite = [p for p in active if (1 if p.get("dir") == "long" else -1) != direction]
        marks = mark_position(active, entry, fine, fine_ts)
        same_marks = [m for m in marks if (1 if m.get("dir") == "long" else -1) == direction]
        marked_sum = sum(m["marked_r"] for m in same_marks)
        if wk is not None:
            seen_window[wk] += 1; cohort_seq = seen_window[wk]
        else:
            cohort_seq = 0
        campaign = "first" if not active else "mixed_cohort" if opposite else "green_addon" if marked_sum > 0 else "red_addon"
        prior_same = [p for p in ordered[:i] if wk is not None and p.get("window_key") == wk and
                      (1 if p.get("dir") == "long" else -1) == direction]
        last_prior = prior_same[-1] if prior_same else None
        rows.append({"trade": t, "cohort_seq": cohort_seq, "active_count": len(active),
                     "same_active_count": len(same), "opposite_active_count": len(opposite),
                     "cohort_marked_r": round(marked_sum, 6), "campaign": campaign,
                     "prior_same_trade_count": len(prior_same),
                     "last_prior_r": None if last_prior is None else float(last_prior.get("r_multiple") or 0.0),
                     "prior_mfe_r": max([m["mfe_r"] for m in same_marks], default=None),
                     "cohort_marks": marks})
    return rows


def config_run(params, data, c5, states, state_ts, fine_ts, fine):
    params = dict(params); params.setdefault("exp_partial_r", 0.0)
    out = build_module()(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                         fine_ltf=fine, **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    cohort = cohort_rows(trades, fine, fine_ts); rows = []
    for item in cohort:
        t = item["trade"]
        rows.append({**t, **{k: v for k, v in item.items() if k != "trade"},
                     "net_r": net_r([t]), **preentry_5m(t, c5, state_ts, states),
                     **enrich_path(t, fine, fine_ts)})
    return trades, rows


def report_config(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[f"cohort_seq_{r['cohort_seq']}"].append(r)
        groups[f"campaign_{r['campaign']}"].append(r)
        groups[f"active_{r['active_count']}"].append(r)
        groups[f"same_active_{r['same_active_count']}"].append(r)
        groups[f"scene_{r['scene']}"].append(r)
        groups["prior5m_opposed" if r["preentry_5m_opposed"] else "prior5m_aligned" if r["preentry_5m_opposed"] == 0 else "prior5m_missing"].append(r)
        if r["r_multiple"] <= 0:
            m = r["mfe_r"] or 0.0
            label = "immediate" if m < .25 else "fade" if m < .5 else "early_peak" if m < 1 else "giveback"
        else:
            label = "winner"
        groups[f"loss_scene_{label}"].append(r)
    out = {"baseline": trade_stats([r for r in rows]), "buckets": {}}
    for name, subset in sorted(groups.items()):
        out["buckets"][name] = {"n": len(subset),
                                "gross": stats([r["r_multiple"] for r in subset]),
                                "net": stats([r["net_r"] for r in subset]),
                                "avg_mfe": stats([r["mfe_r"] for r in subset]),
                                "avg_cohort_marked": stats([r["cohort_marked_r"] for r in subset])}
    return out


def run_scope(scope):
    data = load_scope(scope); c5 = load_5m(scope)
    states = build_5m_state(c5); state_ts = [x["close_ts"] for x in states]
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    result = {"stage": "44-46", "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "five_m_bars": len(c5), "configs": {}}
    for name, params in CONFIGURATIONS:
        trades, rows = config_run(params, data, c5, states, state_ts, fine_ts, data["fine"])
        result["configs"][name] = report_config(rows)
        b = result["configs"][name]["baseline"]
        print(f"  {scope.upper():3} {name:24} n={b['n']:4d} G={b['gross']['sum_r']:+8.1f} N={b['net']['sum_r']:+8.1f} WR={b['gross']['wr_pct']:5.1f}%", flush=True)
    OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"  wrote {OUT[scope]}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=(*SCOPES, "both"), default="both")
    args = parser.parse_args()
    for scope in (SCOPES if args.scope == "both" else (args.scope,)):
        run_scope(scope)


if __name__ == "__main__":
    main()

