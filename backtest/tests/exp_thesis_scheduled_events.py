"""Official scheduled-event thesis: descriptive coverage and path-true autopsy.

Only events with reproducible official advance scheduling are eligible. Core
cross-era calendar is BLS + FOMC. BEA current API rows are supplemental. No
post-event direction or reaction labels are used.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

CALENDAR = ROOT / "data/scheduled_events/official_us_events_2021_2026.json"
OUT = {
    "is": ROOT / "backtest/tests/_thesis_scheduled_events_results_is.json",
    "oos": ROOT / "backtest/tests/_thesis_scheduled_events_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
ENTRY_DELAY_S = 900
WINDOW_PRE_S = 3600
WINDOW_POST_S = 1800


def parse_stamp(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def load_calendar():
    data = json.loads(CALENDAR.read_text(encoding="utf-8"))
    exact = defaultdict(list)
    dates = defaultdict(list)
    for event in data["events"]:
        if event.get("timestamp_utc"):
            exact[event["family"]].append({**event, "ts": parse_stamp(event["timestamp_utc"])})
        elif event.get("date_utc"):
            dates[event["family"]].append({**event, "date": event["date_utc"]})
    for rows in exact.values():
        rows.sort(key=lambda e: e["ts"])
    return data, exact, dates


def stats(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    if not gross:
        return {"n": 0}
    wins = [x for x in gross if x > 0]
    losses = [x for x in gross if x <= 0]
    gp = sum(wins); gl = abs(sum(losses))
    return {
        "n": len(gross), "gross_r": round(sum(gross), 4), "net_r": round(sum(net), 4),
        "avg_gross_r": round(sum(gross) / len(gross), 6),
        "avg_net_r": round(sum(net) / len(net), 6),
        "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(gross), 3),
        "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "pf": round(gp / gl, 4) if gl else 0.0,
        "median": round(statistics.median(gross), 6),
    }


def matches_event(entry_ts, event):
    return event["ts"] - WINDOW_PRE_S <= entry_ts <= event["ts"] + WINDOW_POST_S



def trade_groups(trades, exact, dates):
    groups = defaultdict(list)
    detail = []
    for trade in trades:
        entry_ts = int(trade["entry_ts"]) + ENTRY_DELAY_S
        day = datetime.fromtimestamp(entry_ts, timezone.utc).date().isoformat()
        hits = []
        for family in ("bls", "fomc", "bea"):
            for event in exact[family]:
                if matches_event(entry_ts, event):
                    hits.append((family, event["event_type"], event["name"], event["ts"], event["source_url"]))
        for event in dates["political"]:
            if day == event["date"]:
                hits.append(("political", event["event_type"], event["name"], None, event["source_url"]))
        if hits:
            for family, event_type, name, _event_ts, _source in hits:
                groups[f"{family}:{event_type}"].append(trade)
            detail.append({"trade_no": trade.get("trade_no"), "entry_ts": entry_ts,
                           "entry_date": trade.get("entry_date"), "r": trade.get("r_multiple"),
                           "hits": hits})
    return dict(groups), detail



def policy_flags(key, exact, dates):
    core_ts = tuple(event["ts"] for family in ("bls", "fomc") for event in exact[family])
    core_dates = tuple(sorted({datetime.fromtimestamp(event["ts"], timezone.utc).date().isoformat()
                              for family in ("bls", "fomc") for event in exact[family]}))
    political_dates = tuple(sorted(event["date"] for event in dates["political"]))
    policies = [
        ("baseline", {}),
        ("core_exact_60pre_30post", {"exp_event_mode": "exact", "exp_event_timestamps": core_ts}),
        ("core_exact_utc_day", {"exp_event_mode": "day", "exp_event_dates": core_dates}),
        ("political_fixed_day", {"exp_event_mode": "day", "exp_event_dates": political_dates}),
    ]
    if key != "fullstack_wage10_cd0_single_sw10":
        policies += [
            ("placebo_minus_1d", {"exp_event_mode": "exact", "exp_event_timestamps": core_ts, "exp_event_shift_min": -1440}),
            ("placebo_plus_1d", {"exp_event_mode": "exact", "exp_event_timestamps": core_ts, "exp_event_shift_min": 1440}),
        ]
    return policies


def trade_side_stats(trades):
    return {
        "long": stats([t for t in trades if t.get("dir") == "long"]),
        "short": stats([t for t in trades if t.get("dir") == "short"]),
    }


def run_scope(scope, exact, dates, metadata, descriptive_only=False):
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": 22, "scope": scope, "instrument": "BTCUSDT_BYBIT",
        "policy": "official advance-scheduled events only; no hindsight direction",
        "calendar_schema": metadata["schema"],
        "calendar_built_at_utc": metadata["built_at_utc"],
        "entry_instant": "trade entry_ts + 900 seconds",
        "configs": {},
    }
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        config_result = {"policies": {}}
        for policy_name, flags in policy_flags(key, exact, dates):
            if descriptive_only and policy_name != "baseline":
                continue
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**params, **flags})
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            row = {
                "flags": {name: (list(value) if isinstance(value, tuple) else value)
                          for name, value in flags.items()},
                "metrics": stats(trades),
                "sides": trade_side_stats(trades),
                "event_stats": out.get("event_stats", {"blocked": 0}) if isinstance(out, dict) else {"blocked": 0},
            }
            if policy_name == "baseline":
                groups, detail = trade_groups(trades, exact, dates)
                config_result["event_groups"] = {name: stats(rows) for name, rows in sorted(groups.items())}
                config_result["event_trade_details"] = detail
            config_result["policies"][policy_name] = row
            metric = row["metrics"]
            print(f"  {scope.upper()} {key:36} {policy_name:24} n={metric['n']:3d} gross={metric['gross_r']:+8.1f} net={metric['net_r']:+8.1f} avg={metric['avg_net_r']:+.3f} WR={metric['win_rate_pct']:5.1f}% blocked={row['event_stats']['blocked']:3d}", flush=True)
        result["configs"][key] = config_result
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    parser.add_argument("--descriptive-only", action="store_true")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    metadata, exact, dates = load_calendar()
    print("calendar counts", {k: len(v) for k, v in exact.items()}, {k: len(v) for k, v in dates.items()}, flush=True)
    for scope in scopes:
        result = run_scope(scope, exact, dates, metadata, descriptive_only=args.descriptive_only)
        if args.descriptive_only:
            result["stage_status"] = "descriptive_complete_path_true_pending"
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
