"""Bybit-only portfolio loss-forensics autopsy.

Read-only. Separates loss causes into:
- immediate structural failure (low MFE before stop)
- favorable excursion then loss
- clustered multi-position failure episodes
- post-loss recovery behavior

No filters or engine changes. Run champion and king on IS/OOS.
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
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import BP, get_data, identity_gate, net_r
from test_experiments_craze import build_module
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT_IS = ROOT / "live_stuff/tests/_thesis_loss_forensics_results_is.json"
OUT_OOS = ROOT / "live_stuff/tests/_thesis_loss_forensics_results_oos.json"
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
SCOPES = ("is", "oos")


def stats(values):
    xs = [float(x) for x in values if x is not None]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    max_loss_streak = max_win_streak = 0
    ls = ws = 0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if x <= 0:
            ls += 1
            ws = 0
            max_loss_streak = max(max_loss_streak, ls)
        else:
            ws += 1
            ls = 0
            max_win_streak = max(max_win_streak, ws)
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6),
            "wr": round(100.0 * len(wins) / len(xs), 3),
            "wins": len(wins), "losses": len(losses),
            "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
            "payoff": (round((sum(wins) / len(wins)) / abs(sum(losses) / len(losses)), 4)
                       if wins and losses and abs(sum(losses)) > 0 else 0.0),
            "pf": (round(sum(wins) / abs(sum(losses)), 4)
                    if losses and abs(sum(losses)) > 0 else 0.0),
            "dd": round(dd, 4), "max_loss_streak": max_loss_streak,
            "max_win_streak": max_win_streak,
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
            "median": round(statistics.median(xs), 6)}


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
        return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}
    data = get_data()
    identity_gate(data, build_module())
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    result = {"stage": 7, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 100, flush=True)
        print(f"  PORTFOLIO LOSS FORENSICS — BYBIT {scope.upper()}", flush=True)
        print("=" * 100, flush=True)
        data = load_scope(scope)
        scope_result = {}
        for key in CONFIGS:
            result_key = analyze(data, scope, key)
            scope_result[key] = result_key
            print(f"\n  {key}: {result_key['trade_count']} trades / NET {result_key['net_r']:+.1f}R", flush=True)
            print(f"    losses={result_key['loss_stats']['n']} avg_loss={result_key['loss_stats']['avg_loss']:+.3f} "
                  f"loss MFE={result_key['loss_mfe']['avg_r']:+.3f}R "
                  f"MFE>=0.5R={result_key['loss_mfe_over_05r_pct']:.1f}% "
                  f"MFE<0.25R={result_key['loss_mfe_under_025r_pct']:.1f}%", flush=True)
            print(f"    recovery after loss={result_key['recovery']['after_loss']}", flush=True)
            print(f"    overlap buckets={result_key['by_overlap']}", flush=True)
            print(f"    24h episodes={result_key['episodes']['24']}", flush=True)
        result["scopes"][scope] = scope_result
    output = OUT_OOS if args.scope == "oos" else OUT_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output}", flush=True)


def episode_stats(trades, gap_hours):
    ordered = sorted(trades, key=lambda t: int(t["entry_ts"]))
    episodes = []
    current = []
    max_end = None
    for trade in ordered:
        ets = int(trade["entry_ts"])
        xts = int(trade.get("exit_ts") or ets)
        if current and ets > (max_end or ets) + gap_hours * 3600:
            episodes.append(current)
            current = []
            max_end = None
        current.append(trade)
        max_end = max(max_end or xts, xts)
    if current:
        episodes.append(current)
    rows = []
    for ep in episodes:
        rs = [float(t.get("r_multiple") or 0.0) for t in ep]
        rows.append({"n": len(ep), "losses": sum(x <= 0 for x in rs),
                     "wins": sum(x > 0 for x in rs), "gross_r": sum(rs),
                     "avg_r": sum(rs) / len(rs), "start_ts": int(ep[0]["entry_ts"]),
                     "end_ts": max(int(t.get("exit_ts") or t["entry_ts"]) for t in ep)})
    return rows


def recovery_stats(trades):
    ordered = sorted(trades, key=lambda t: int(t["entry_ts"]))
    after_loss = []
    after_win = []
    for i, trade in enumerate(ordered[:-1]):
        nxt = ordered[i + 1]
        if int(nxt["entry_ts"]) < int(trade.get("exit_ts") or trade["entry_ts"]):
            continue
        r = float(nxt.get("r_multiple") or 0.0)
        (after_loss if float(trade.get("r_multiple") or 0.0) <= 0 else after_win).append(r)
    return {"after_loss": stats(after_loss), "after_win": stats(after_win)}


def analyze(data, scope, key):
    params = {**BP, **EXPERIMENTS[key]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    sim = build_module()
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    overlap = overlap_features(trades)
    overlap_by_trade = {id(x["trade"]): x for x in overlap}
    rows = []
    for trade in trades:
        p = enrich_path(trade, data["fine"], fine_ts)
        if p is None:
            continue
        o = overlap_by_trade[id(trade)]
        rows.append({**trade, **p, "r": float(trade.get("r_multiple") or 0.0),
                     "active_at_entry": o["active_at_entry"],
                     "same_dir_at_entry": o["same_dir_at_entry"],
                     "opposite_at_entry": o["opposite_at_entry"]})
    losses = [r for r in rows if r["r"] <= 0]
    wins = [r for r in rows if r["r"] > 0]
    by_overlap = {}
    for k in sorted(set(r["active_at_entry"] for r in rows)):
        sub = [r for r in rows if r["active_at_entry"] == k]
        by_overlap[str(k)] = {"all": stats([r["r"] for r in sub]),
                              "losses": stats([r["r"] for r in sub if r["r"] <= 0])}
    by_kind = {}
    for kind in sorted(set(r.get("break_kind") for r in rows)):
        sub = [r for r in rows if r.get("break_kind") == kind]
        by_kind[str(kind)] = {"all": stats([r["r"] for r in sub]),
                             "losses": stats([r["r"] for r in sub if r["r"] <= 0])}
    by_regime = {}
    for regime in sorted(set(r.get("htf_regime") for r in rows)):
        sub = [r for r in rows if r.get("htf_regime") == regime]
        by_regime[str(regime)] = {"all": stats([r["r"] for r in sub]),
                                  "losses": stats([r["r"] for r in sub if r["r"] <= 0])}
    episodes = {str(gap): episode_stats(rows, gap) for gap in (6, 24, 72)}
    episode_summary = {}
    for gap, eps in episodes.items():
        worst = sorted(eps, key=lambda e: e["gross_r"])[:20]
        episode_summary[gap] = {"episodes": len(eps),
                                "loss_episodes": sum(e["gross_r"] < 0 for e in eps),
                                "worst": worst[:10],
                                "losses_in_worst_10": sum(e["losses"] for e in worst[:10]),
                                "gross_in_worst_10": sum(e["gross_r"] for e in worst[:10])}
    return {"trade_count": len(trades), "net_r": net_r(trades),
            "gross_stats": stats([r["r"] for r in rows]),
            "loss_stats": stats([r["r"] for r in losses]),
            "win_stats": stats([r["r"] for r in wins]),
            "loss_mfe": stats([r["mfe_r"] for r in losses]),
            "loss_mae": stats([r["mae_r"] for r in losses]),
            "loss_mfe_over_1r_pct": 100.0 * sum(r["mfe_r"] >= 1.0 for r in losses) / max(len(losses), 1),
            "loss_mfe_over_05r_pct": 100.0 * sum(r["mfe_r"] >= 0.5 for r in losses) / max(len(losses), 1),
            "loss_mfe_under_025r_pct": 100.0 * sum(r["mfe_r"] < 0.25 for r in losses) / max(len(losses), 1),
            "by_overlap": by_overlap, "by_kind": by_kind, "by_regime": by_regime,
            "recovery": recovery_stats(rows), "episodes": episode_summary,
            "rows": rows}


def enrich_path(trade, fine, fine_ts):
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    direction = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - sl)
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if risk <= 0 or start >= end:
        return None
    highs = [float(c["high"]) for c in fine[start:end]]
    lows = [float(c["low"]) for c in fine[start:end]]
    if direction > 0:
        mfe = (max(highs) - entry) / risk
        mae = (entry - min(lows)) / risk
    else:
        mfe = (entry - min(lows)) / risk
        mae = (max(highs) - entry) / risk
    return {"mfe_r": round(mfe, 4), "mae_r": round(mae, 4),
            "mfe_pct_of_1r": round(mfe, 4), "mae_pct_of_1r": round(mae, 4),
            "bars_path": end - start}


def overlap_features(trades):
    ordered = sorted(trades, key=lambda t: int(t["entry_ts"]))
    rows = []
    for i, trade in enumerate(ordered):
        ets = int(trade["entry_ts"])
        active = [p for p in ordered[:i]
                  if int(p.get("exit_ts") or p["entry_ts"]) > ets]
        same_dir = sum(p["dir"] == trade["dir"] for p in active)
        rows.append({"trade": trade, "active_at_entry": len(active),
                     "same_dir_at_entry": same_dir,
                     "opposite_at_entry": len(active) - same_dir,
                     "all_prior_active": active})
    return rows


if __name__ == "__main__":
    main()

