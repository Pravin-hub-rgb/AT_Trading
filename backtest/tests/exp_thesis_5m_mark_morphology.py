"""Stage 33 — Bybit BTCUSDT perpetual 5m FirstSwing mark morphology.

Descriptive post-entry autopsy. Uses the actual 5m FirstSwing chain (B1/B2/FLIP
marks plus FS confirmation marker), the same 15m real ledgers, and completed 5m
close timestamps. A mark counts only after the 15m entry instant and no later
than the real exit. No production change and no post-hoc P&L claim.
"""
from __future__ import annotations

import argparse
import bisect
import json
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
from run_experiment import identity_gate, net_r
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import params_for
from exp_thesis_structure_volume import load_scope
from exp_thesis_5m_opposition import load_5m
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

OUT = {
    "is": ROOT / "backtest/tests/_thesis_5m_mark_morphology_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_5m_mark_morphology_results_oos.json",
}
CONFIGS = (
    ("pure_v18_single", params_for("pure_v18_single")),
    ("pure_v18_multi", params_for("pure_v18_multi")),
    ("literal_v18_single", params_for("literal_v18_single")),
    ("literal_v18_multi", params_for("literal_v18_multi")),
    ("fullstack_single", {**BP, **EXPERIMENTS["fullstack_wage10_cd0_single_sw10"]["params"]}),
    ("champion_multi", {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}),
    ("utcsat_multi", {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}),
)
EVENT_KINDS = ("B1", "B2", "FLIP", "FS")
PAIRS = ("B1>B2", "B1>FLIP", "FLIP>B2", "FS>B2", "FS>FLIP")


def direction_num(value):
    return 1 if value in ("up", "long", "B") else -1 if value in ("down", "short", "S") else 0


def summary(rows):
    if not rows:
        return {"n": 0}
    gross = [float(r.get("r_multiple") or 0.0) for r in rows]
    nets = [net_r([r]) for r in rows]
    wins = [x for x in gross if x > 0]
    losses = [x for x in gross if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for value in nets:
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

    def dist(field):
        values = [float(r[field]) for r in rows if r.get(field) is not None]
        return None if not values else {
            "n": len(values), "mean": round(sum(values) / len(values), 6),
            "median": round(statistics.median(values), 6),
        }

    return {
        "n": len(rows), "gross_r": round(sum(gross), 6), "net_r": round(sum(nets), 6),
        "avg_gross_r": round(sum(gross) / len(gross), 6),
        "avg_net_r": round(sum(nets) / len(nets), 6),
        "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / len(gross), 3),
        "avg_win": round(aw, 6), "avg_loss": round(al, 6),
        "payoff": round(aw / abs(al), 6) if al else 0.0,
        "gross_pf": round(sum(wins) / abs(sum(losses)), 6) if losses else 0.0,
        "net_max_dd": round(dd, 6), "max_loss_streak": mls, "max_win_streak": mws,
        "median_net_r": round(statistics.median(nets), 6),
        "mfe_r": dist("mfe_r"), "mae_r": dist("mae_r"),
        "runners": {"3R": sum(x >= 3.0 for x in gross),
                    "5R": sum(x >= 5.0 for x in gross),
                    "10R": sum(x >= 10.0 for x in gross)},
    }



def build_5m_events(c5):
    flow = [FlowCandle(c["date"], c["open"], c["high"], c["low"], c["close"]) for c in c5]
    swings = _compute_swings(flow, "continuous", min_bars=14)
    events = []
    for sw in swings:
        for mark in sw.get("breaks") or []:
            idx = int(mark.get("idx", -1))
            if 0 <= idx < len(c5):
                events.append({"kind": str(mark.get("kind") or ""),
                               "dir": direction_num(mark.get("dir")), "idx": idx,
                               "close_ts": int(c5[idx]["ts"]) + 300,
                               "swing_index": int(sw.get("swing_index", -1))})
        fs_idx = int(sw.get("fs_at_idx", sw.get("confirmed_at_idx", -1)))
        if 0 <= fs_idx < len(c5):
            events.append({"kind": "FS", "dir": direction_num(sw.get("dir")),
                           "idx": fs_idx, "close_ts": int(c5[fs_idx]["ts"]) + 300,
                           "swing_index": int(sw.get("swing_index", -1))})
    events.sort(key=lambda e: (e["close_ts"], e["idx"], e["kind"], e["swing_index"]))
    return swings, events


def path_excursion(trade, c5, ts5, entry_instant, exit_ts):
    direction = 1 if trade.get("dir") == "long" else -1
    entry_px = float(trade["entry_price"]); sl = float(trade["sl"])
    risk = abs(entry_px - sl)
    if risk <= 0:
        return None, None, None
    start = bisect.bisect_right(ts5, entry_instant)
    end = bisect.bisect_right(ts5, int(exit_ts)) - 1
    mfe = mae = 0.0
    first_half = None
    for idx in range(start, end + 1):
        c = c5[idx]
        fav = (float(c["high"]) - entry_px) if direction > 0 else (entry_px - float(c["low"]))
        adv = (entry_px - float(c["low"])) if direction > 0 else (float(c["high"]) - entry_px)
        mfe = max(mfe, fav / risk)
        mae = max(mae, adv / risk)
        if first_half is None and fav / risk >= 0.5:
            first_half = idx
    return mfe, mae, first_half


def classify(trade, c5, ts5, event_ts, events):
    entry = int(trade["entry_ts"])
    entry_instant = entry + 900
    exit_ts = int(trade.get("exit_ts") or entry)
    direction = 1 if trade.get("dir") == "long" else -1
    left = bisect.bisect_right(event_ts, entry_instant)
    right = bisect.bisect_right(event_ts, exit_ts)
    post = [e for e in events[left:right] if e["dir"] == -direction]
    compact = []
    for event in post:
        if not compact or compact[-1]["kind"] != event["kind"]:
            compact.append(event)
    mfe, mae, first_half = path_excursion(trade, c5, ts5, entry_instant, exit_ts)
    sequence = ">".join(e["kind"] for e in compact) or "none"
    adjacent_pairs = {f"{a['kind']}>{b['kind']}" for a, b in zip(compact, compact[1:])}
    distinct = []
    for event in compact:
        if event["kind"] not in distinct:
            distinct.append(event["kind"])
    ordered_pair = f"{distinct[0]}>{distinct[1]}" if len(distinct) >= 2 else "none"
    return {
        **trade,
        "trade_no": trade.get("trade_no"), "entry_ts": entry, "exit_ts": exit_ts,
        "dir": trade.get("dir"), "r_multiple": float(trade.get("r_multiple") or 0.0),
        "mfe_r": mfe, "mae_r": mae, "first_mfe_0_5_idx": first_half,
        "post_sequence": sequence, "post_kinds": sorted({e["kind"] for e in compact}),
        "adjacent_pairs": sorted(adjacent_pairs), "ordered_pair": ordered_pair,
        "first_event": None if not compact else {
            k: compact[0][k] for k in ("kind", "dir", "idx", "close_ts", "swing_index")},
        "events": compact,
    }



def report(rows, total_events):
    buckets = defaultdict(list)
    for row in rows:
        buckets["none" if row["post_sequence"] == "none" else "any_opposition"].append(row)
        for kind in EVENT_KINDS:
            if kind in row["post_kinds"]:
                buckets[f"opposite_{kind}"].append(row)
        for pair in PAIRS:
            if pair in row["adjacent_pairs"]:
                buckets[f"pair_{pair.replace('>', '_to_')}"].append(row)
        buckets[f"ordered_{row['ordered_pair']}"].append(row)
        phase_seen = set()
        for event in row["events"]:
            half = row["first_mfe_0_5_idx"]
            phase = "no_0_5R" if half is None else ("before_0_5R" if event["idx"] <= half else "after_0_5R")
            phase_key = (event["kind"], phase)
            if phase_key in phase_seen:
                continue
            phase_seen.add(phase_key)
            buckets[f"phase_{event['kind']}_{phase}"].append(row)
    return {"baseline": summary(rows), "event_coverage": total_events,
            "buckets": {name: summary(subset) for name, subset in sorted(buckets.items())},
            "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    started = time.time()
    for scope in scopes:
        data = load_scope(scope)
        if scope == "is":
            identity_gate(data, build_module())
        c5 = load_5m(scope)
        ts5 = [int(c["ts"]) for c in c5]
        sw5, events = build_5m_events(c5)
        event_ts = [int(e["close_ts"]) for e in events]
        coverage = Counter(e["kind"] for e in events)
        print(f"5M MORPHOLOGY {scope.upper()}: c5={len(c5)} swings={len(sw5)} events={dict(coverage)}", flush=True)
        sim = build_module()
        result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
                  "chain": {"timeframe": "5m", "min_bars": 14,
                            "event_coverage": dict(coverage), "swing_count": len(sw5)},
                  "configs": {}}
        for name, params in CONFIGS:
            params = dict(params)
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            rows = [classify(t, c5, ts5, event_ts, events) for t in trades]
            result["configs"][name] = report(rows, dict(coverage))
            b = result["configs"][name]["baseline"]
            opposed = sum(r["post_sequence"] != "none" for r in rows)
            print(f"  {name:20} n={b['n']:3d} G={b['gross_r']:+8.1f} N={b['net_r']:+8.1f} "
                  f"avg={b['avg_net_r']:+.3f} WR={b['win_rate_pct']:5.1f}% opposed={opposed:3d}", flush=True)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)
    print(f"done in {time.time() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()

