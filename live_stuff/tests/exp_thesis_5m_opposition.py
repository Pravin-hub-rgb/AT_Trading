"""Bybit BTCUSDT perpetual 5m opposition autopsy.

Uses completed 5m bars from the IS-overlap file and the downloaded,
gap-free 2021-2022 OOS file. Walker state is built with the repository
WalkerEngine; no future completed bar is used at a 15m decision instant.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import params_for
from src.walker import FlowCandle, WalkerEngine

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_5m_opposition_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_5m_opposition_results_oos.json",
}
DATA5 = {
    "is": ROOT / "data/bybit/BTCUSDT_5m.csv",
    "oos": ROOT / "data/unseen/bybit/BTCUSDT_5m.csv",
}
CONFIGURATIONS = (
    ("pure_v18_single", params_for("pure_v18_single")),
    ("pure_v18_multi", params_for("pure_v18_multi")),
    ("fullstack_single", {**BP, **EXPERIMENTS["fullstack_wage10_cd0_single_sw10"]["params"]}),
    ("champion_multi", {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}),
    ("utcsat_multi", {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}),
)


def load_5m(scope="is"):
    path = DATA5[scope]
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    rows = []
    for r in df.itertuples():
        date = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ts = int(r.timestamp.value // 10**9) - 19800
        rows.append({"date": date, "ts": ts, "open": float(r.open), "high": float(r.high),
                     "low": float(r.low), "close": float(r.close),
                     "volume": float(getattr(r, "volume", 0.0))})
    return rows


def build_5m_state(c5):
    by_day = defaultdict(list)
    for i, c in enumerate(c5):
        by_day[c["date"][:10]].append((i, c))
    states = [None] * len(c5)
    for day in by_day.values():
        eng = WalkerEngine()
        for i, c in day:
            eng.process_bar(FlowCandle(c["date"], c["open"], c["high"], c["low"], c["close"]), i)
            states[i] = {"direction": eng.dir, "close_ts": c["ts"] + 300, "idx": i}
    return states


def summary(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "wr_pct": round(100.0 * len(wins) / len(xs), 3), "avg_win": round(aw, 4),
            "avg_loss": round(al, 4), "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "median": round(statistics.median(xs), 6)}


def classify(trade, c5, states, state_ts):
    entry = int(trade["entry_ts"])
    entry_instant = entry + 900
    exit_ts = int(trade.get("exit_ts") or entry)
    j = bisect.bisect_right(state_ts, entry_instant) - 1
    if j < 0 or j >= len(states):
        return None
    direction = 1 if trade.get("dir") == "long" else -1
    at_entry = int((direction > 0 and states[j]["direction"] == "down") or
                   (direction < 0 and states[j]["direction"] == "up"))
    first_after = None
    first_mfe = None
    entry_price = float(trade["entry_price"])
    risk = max(abs(entry_price - float(trade["sl"])), 1e-9)
    for k, state in enumerate(states):
        if state is None or state["close_ts"] <= entry_instant or state["close_ts"] > exit_ts:
            continue
        c = c5[k]
        mfe = ((c["high"] - entry_price) if direction > 0 else
               (entry_price - c["low"])) / risk
        if first_mfe is None and mfe >= 0.5:
            first_mfe = k
        opposed = ((direction > 0 and state["direction"] == "down") or
                   (direction < 0 and state["direction"] == "up"))
        if first_after is None and opposed:
            first_after = k
    if first_after is None:
        bucket = "no_post_opposition"
    elif first_mfe is not None and first_after <= first_mfe:
        bucket = "post_opposition_before_0.5R"
    else:
        bucket = "post_opposition_after_0.5R"
    return {"bucket": bucket, "opposed_at_entry": at_entry,
            "first_opposition_after_entry": first_after is not None,
            "opposition_before_mfe": bool(first_after is not None and first_mfe is not None and first_after <= first_mfe),
            "entry_state_direction": states[j]["direction"],
            "first_opposition_idx": first_after, "first_mfe_0_5_idx": first_mfe,
            "r": float(trade.get("r_multiple") or 0.0)}


def run(scope):
    if scope == "is":
        data = get_data()
    else:
        from test_4_new_concepts import load_fine_1m, load_unseen
        from src.btc.btc_routes import _compute_swings
        from engine.v18_params import SWING
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        data = {"c15": c15, "c1h": c1h,
                "sw10": _compute_swings(f1h, "continuous", min_bars=10),
                "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    identity_gate(data, build_module()) if scope == "is" else None
    c5 = load_5m(scope)
    states = build_5m_state(c5)
    state_ts = [x["close_ts"] for x in states]
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope,
              "data_5m": {"rows": len(c5), "start": c5[0]["ts"], "end": c5[-1]["ts"],
                          "oos_available": scope == "oos"}, "configs": {}}
    sim = build_module()
    for name, params in CONFIGURATIONS:
        params = dict(params)
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        rows = [classify(t, c5, states, state_ts) for t in trades]
        rows = [r for r in rows if r is not None]
        buckets = defaultdict(list)
        for row in rows:
            buckets[row["bucket"]].append(row["r"])
            buckets["entry_opposed" if row["opposed_at_entry"] else "entry_aligned"].append(row["r"])
        result["configs"][name] = {
            "trade_count": len(trades), "overlap_rows": len(rows),
            "buckets": {k: summary(v) for k, v in sorted(buckets.items())},
            "rows": rows,
        }
        print(f"  {name:20} trades={len(trades):4d} 5m_rows={len(rows):4d} "
              f"buckets={list(result['configs'][name]['buckets'])}", flush=True)
    OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    for _scope in (("is", "oos") if args.scope == "both" else (args.scope,)):
        run(_scope)

