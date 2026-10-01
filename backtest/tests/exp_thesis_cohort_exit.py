"""Bybit-only multi-position cohort lifecycle replay.

This is a read-only event-timestamp study over accepted opportunities from the
existing multi engine. It tests whether lifecycle coupling between simultaneous
positions helps: newest-stop closes older positions, newest-loss closes older
positions, opposite 15m swings close/freeze entries, and a combined policy.
No production engine is modified.
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
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_thesis_shadow_book import load_scope, prepare_shadow_cache

OUT = {
    "is": ROOT / "backtest/tests/_thesis_cohort_exit_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_cohort_exit_results_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")
POLICIES = (
    "baseline",
    "newest_sl_close_older",
    "newest_loss_close_older",
    "newest_sl_close_older_overlap_only",
    "opposite_swing_close_older",
    "opposite_swing_freeze",
    "sl_close_plus_opposite_freeze",
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
        "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws,
        "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
        "runners_3r": sum(x >= 3.0 for x in xs),
        "runners_5r": sum(x >= 5.0 for x in xs),
        "runners_10r": sum(x >= 10.0 for x in xs),
    }


def make_exit(trade, ts, data, reason):
    """Close a trade at the causal timestamp's latest closed 1m price."""
    fine = data["fine"]
    fine_ts = data["_shadow_fine_ts"]
    idx = bisect.bisect_right(fine_ts, int(ts)) - 1
    if idx < 0:
        idx = 0
    price = float(fine[idx]["close"])
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    risk = abs(entry - sl)
    direction = 1 if trade.get("dir") == "long" else -1
    r = ((price - entry) if direction > 0 else (entry - price)) / risk if risk else 0.0
    out = dict(trade)
    out.update({
        "exit_ts": int(ts), "exit_date": fine[idx].get("date", ""),
        "exit_price": round(price, 2), "outcome": reason,
        "r_multiple": round(r, 6),
        "bars_held": max(0, int((int(ts) - int(trade["entry_ts"])) // 900)),
        "cohort_close": True,
    })
    return out


def add_years(row):
    gross = defaultdict(float)
    net = defaultdict(float)
    for trade in row["trades"]:
        year = str(trade.get("exit_date") or trade.get("entry_date") or "")[:4]
        gross[year] += float(trade.get("r_multiple") or 0.0)
        net[year] += net_r([trade])
    row["yearly_gross"] = dict(sorted(gross.items()))
    row["yearly_net"] = dict(sorted(net.items()))
    return row


def swing_events(data):
    c15 = data["c15"]
    cts = data["_shadow_candle_ts"]
    pos_by_date = {str(c["date"]): i for i, c in enumerate(c15)}
    rows = []
    for swing in data["sw15"]:
        direction = swing.get("dir")
        if direction not in ("up", "down"):
            continue
        confirmed = str(swing.get("confirmed_at_time") or "")
        idx = pos_by_date.get(confirmed)
        if idx is None:
            continue
        rows.append({
            "ts": int(cts[min(idx + 1, len(cts) - 1)]),
            "direction": direction,
            "confirmed": confirmed,
        })
    rows.sort(key=lambda x: x["ts"])
    return rows


def newest(positions):
    if not positions:
        return None
    return max(positions.values(), key=lambda t: (int(t["entry_ts"]), int(t["trade_id"])))


def replay_policy(trades, data, policy):
    """Event-time replay over the actual accepted trade opportunities."""
    originals = []
    for trade_no, trade in enumerate(trades):
        row = dict(trade)
        row["trade_id"] = trade_no
        originals.append(row)
    positions = {}
    ledger = {}
    frozen = False
    skipped_frozen = 0
    max_active = 0
    overlap_entries = 0
    active_buckets = Counter()
    event_counts = Counter()
    natural_exits = []
    swing_rows = swing_events(data)

    events = []
    for row in originals:
        events.append((int(row["entry_ts"]), 2, int(row["trade_id"]), "entry", row))
        events.append((int(row.get("exit_ts") or row["entry_ts"]), 0, int(row["trade_id"]), "exit", row))
    for idx, row in enumerate(swing_rows):
        events.append((int(row["ts"]), 1, idx, "swing", row))
    events.sort(key=lambda event: (event[0], event[1], event[2]))

    def remove(trade_id):
        positions.pop(int(trade_id), None)

    def close_older(keep, ts, reason, event_name):
        for older in list(positions.values()):
            if int(older["trade_id"]) == int(keep["trade_id"]):
                continue
            closed = make_exit(older, ts, data, reason)
            remove(older["trade_id"])
            ledger[int(older["trade_id"])] = closed
            event_counts[f"closed_older_{event_name}"] += 1

    for ts, _kind, _idx, kind, payload in events:
        if kind == "entry":
            if frozen and positions:
                skipped_frozen += 1
                event_counts["frozen_entry"] += 1
                continue
            row = dict(payload)
            positions[int(row["trade_id"])] = row
            ledger[int(row["trade_id"])] = row
            active = len(positions)
            max_active = max(max_active, active)
            active_buckets[str(active)] += 1
            overlap_entries += int(active >= 2)
            continue

        if kind == "swing":
            if not positions:
                frozen = False
                continue
            latest = newest(positions)
            latest_dir = "up" if latest.get("dir") == "long" else "down"
            if payload["direction"] == latest_dir:
                continue
            event_counts["opposite_swing_with_open_cohort"] += 1
            if policy in ("opposite_swing_close_older", "sl_close_plus_opposite_freeze"):
                close_older(latest, ts, "cohort_opposite_swing", "opposite_swing")
            if policy in ("opposite_swing_freeze", "sl_close_plus_opposite_freeze"):
                frozen = True
                event_counts["freeze_opposite_swing"] += 1
            continue

        trade_id = int(payload["trade_id"])
        current = positions.get(trade_id)
        if current is None:
            continue
        was_newest = current["trade_id"] == newest(positions)["trade_id"]
        active_count = len(positions)
        r = float(current.get("r_multiple") or 0.0)
        remove(trade_id)
        natural_exits.append({"trade_id": trade_id, "entry_ts": int(current["entry_ts"]),
                              "exit_ts": int(payload.get("exit_ts") or ts), "r": r,
                              "was_newest": was_newest, "active_count": active_count})
        if not positions:
            frozen = False
            continue
        if not was_newest:
            continue
        if policy in ("newest_sl_close_older", "newest_sl_close_older_overlap_only") and r <= -0.9:
            if policy.endswith("overlap_only") and active_count < 2:
                continue
            event_counts["newest_sl_trigger"] += 1
            for older in list(positions.values()):
                closed = make_exit(older, ts, data, "cohort_newest_sl")
                remove(older["trade_id"])
                ledger[int(older["trade_id"])] = closed
                event_counts["closed_older_newest_sl"] += 1
        elif policy == "newest_loss_close_older" and r < 0:
            event_counts["newest_loss_trigger"] += 1
            for older in list(positions.values()):
                closed = make_exit(older, ts, data, "cohort_newest_loss")
                remove(older["trade_id"])
                ledger[int(older["trade_id"])] = closed
                event_counts["closed_older_newest_loss"] += 1

    return {
        "trades": [ledger[i] for i in sorted(ledger)],
        "events": dict(event_counts), "frozen_candidates": skipped_frozen,
        "max_active": max_active, "overlap_entries": overlap_entries,
        "active_buckets": dict(active_buckets), "natural_exits": natural_exits,
    }


def metric_row(replay):
    trades = replay["trades"]
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    net_total = net_r(trades)
    net_stats = stats(net)
    net_stats["sum_r"] = round(net_total, 6)
    net_stats["avg_r"] = round(net_total / len(trades), 6) if trades else 0.0
    net_stats["net_total"] = round(net_total, 6)
    row = {
        "count": len(trades), "gross": stats(gross), "net": net_stats,
        "cost_and_funding": round(sum(gross) - net_total, 4),
        "events": replay["events"], "frozen_candidates": replay["frozen_candidates"],
        "max_active": replay["max_active"], "overlap_entries": replay["overlap_entries"],
        "active_buckets": replay["active_buckets"], "trades": trades,
    }
    return add_years(row)


def run_policy(trades, data, policy):
    return metric_row(replay_policy(trades, data, policy))


def run_scope(scope, data, sim):
    result = {
        "instrument": "BTCUSDT_BYBIT", "scope": scope,
        "architecture_note": "event-timestamp replay over accepted multi opportunities; not a rewrite of the multi engine",
        "configs": {},
    }
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        output = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                     fine_ltf=data["fine"], **params)
        trades = output["ltf_trades"] if isinstance(output, dict) else output
        result["configs"][key] = {"baseline_trade_count": len(trades), "policies": {}}
        for policy in POLICIES:
            row = run_policy(trades, data, policy)
            result["configs"][key]["policies"][policy] = row
            gross = row["gross"]
            net = row["net"]
            print(f"  {scope.upper():3} {key:24} {policy:34} n={net['n']:3d} "
                  f"gross={gross['sum_r']:+8.1f} net={net['sum_r']:+8.1f} "
                  f"WR={gross['win_rate_pct']:5.1f}% PF={gross['pf']:5.2f} "
                  f"DD={gross['max_dd']:5.1f} events={sum(row['events'].values()):3d}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    all_result = {"stage": 20, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 130, flush=True)
        print(f"  MULTI COHORT LIFECYCLE EVENT REPLAY — BYBIT {scope.upper()}", flush=True)
        print("=" * 130, flush=True)
        data = prepare_shadow_cache(load_scope(scope))
        result = run_scope(scope, data, sim)
        all_result["scopes"][scope] = result
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)
    (ROOT / "backtest/tests/_thesis_cohort_exit_results.json").write_text(
        json.dumps(all_result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

