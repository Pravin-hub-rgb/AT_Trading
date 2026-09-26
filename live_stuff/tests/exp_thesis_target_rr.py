"""Stage 16 — target-derived minimum RR autopsy (Bybit BTCUSDT perp only).

This is distinct from the older 24h opposing-extreme room test. For each
real trade, the target is a completed 15m structural swing endpoint already
known before the entry bar:

- long: nearest known structural high above entry;
- short: nearest known structural low below entry;
- room_R = target distance / initial risk.

The only pre-registered cohort threshold is room_R >= 2.5. This harness is
read-only and does not add an engine gate.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
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
    "is": ROOT / "live_stuff/tests/_thesis_target_rr_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_target_rr_results_oos.json",
}
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
RR_THRESHOLD = 2.5


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
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(xs), "sum_r": round(sum(xs), 4),
        "avg_r": round(sum(xs) / len(xs), 6), "wins": len(wins),
        "losses": len(losses), "win_rate_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(avg_win, 4), "avg_loss": round(avg_loss, 4),
        "payoff": round(avg_win / abs(avg_loss), 4) if avg_loss else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws, "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
    }


def trade_metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    yearly_g = defaultdict(float)
    yearly_n = defaultdict(float)
    for g, n, t in zip(gross, net, trades):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly_g[year] += g
        yearly_n[year] += n
    return {
        "gross": stats(gross), "net": stats(net),
        "cost_and_funding": round(sum(gross) - sum(net), 4),
        "yearly_gross": dict(sorted(yearly_g.items())),
        "yearly_net": dict(sorted(yearly_n.items())),
        "runners": {
            str(th): {"n": sum(r >= th for r in gross),
                      "r": round(sum(r for r in gross if r >= th), 4)}
            for th in (2.0, 3.0, 5.0, 10.0)
        },
    }


def known_targets(data):
    """Return causal 15m structural high/low levels by confirmation index."""
    c15 = data["c15"]
    levels = []
    for sw in data["sw15"]:
        seg = sw.get("seg") or {}
        conf = int(sw.get("confirmed_at_idx", -1))
        if conf < 0 or conf >= len(c15):
            continue
        start = float(seg.get("start_px", 0.0) or 0.0)
        end = float(seg.get("end_px", 0.0) or 0.0)
        if start <= 0 or end <= 0:
            continue
        levels.append({
            "conf_idx": conf, "high": max(start, end),
            "low": min(start, end),
            "swing_index": int(sw.get("swing_index", -1)),
            "direction": sw.get("dir", ""),
        })
    levels.sort(key=lambda x: x["conf_idx"])
    by_idx = defaultdict(list)
    for level in levels:
        by_idx[level["conf_idx"]].append(level)
    return by_idx


def target_for_trade(trade, by_idx):
    entry_idx = int(trade["entry_idx"])
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    risk = abs(entry - sl)
    if risk <= 0:
        return {"cohort": "invalid_risk", "room_r": None, "target": None}
    direction = 1 if trade.get("dir") == "long" else -1
    candidates = []
    for conf_idx, levels in by_idx.items():
        if conf_idx >= entry_idx:
            break
        for level in levels:
            px = level["high"] if direction > 0 else level["low"]
            if (direction > 0 and px > entry) or (direction < 0 and px < entry):
                candidates.append((abs(px - entry), px, level))
    if not candidates:
        return {"cohort": "no_known_target", "room_r": None, "target": None}
    distance, px, level = min(candidates, key=lambda x: x[0])
    room_r = distance / risk
    return {
        "cohort": "room_ge_2.5" if room_r >= RR_THRESHOLD else "room_lt_2.5",
        "room_r": round(room_r, 6), "target": px,
        "target_distance": round(distance, 8),
        "target_conf_idx": level["conf_idx"],
        "target_swing_index": level["swing_index"],
        "target_direction": level["direction"],
    }

def enrich(trades, data):
    by_idx = known_targets(data)
    return [{**trade, **target_for_trade(trade, by_idx)} for trade in trades]


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {
        "stage": 16, "instrument": "BTCUSDT_BYBIT", "scope": scope,
        "pre_registered": True, "threshold": RR_THRESHOLD,
        "definition": "nearest completed 15m structural endpoint above/below entry, confirmed before entry_idx; no fixed-target or 24h room",
        "configs": {},
    }
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        rows = enrich(trades, data)
        groups = {"all": rows}
        for cohort in ("room_ge_2.5", "room_lt_2.5", "no_known_target", "invalid_risk"):
            groups[cohort] = [r for r in rows if r["cohort"] == cohort]
        cfg_result = {
            "description": cfg.get("desc", ""), "trade_count": len(rows),
            "target_count": sum(r["target"] is not None for r in rows),
            "groups": {
                name: {"count": len(rs), "metrics": trade_metrics(rs),
                       "room_r": stats([r["room_r"] for r in rs])}
                for name, rs in groups.items()
            },
        }
        result["configs"][key] = cfg_result
        print(f"  {scope.upper():3} {key:34} baseline {len(rows):3d} targets={cfg_result['target_count']:3d}")
        for name in ("room_ge_2.5", "room_lt_2.5", "no_known_target", "invalid_risk"):
            m = cfg_result["groups"][name]["metrics"]
            g = m["gross"]; n = m["net"]
            print(f"    {name:16} n={g.get('n', 0):3d} gross={g.get('sum_r', 0.0):+8.1f} net={n.get('sum_r', 0.0):+8.1f} avgGross={g.get('avg_r', 0.0):+.3f} WR={g.get('win_rate_pct', 0.0):5.1f}% PF={g.get('pf', 0.0):4.2f} DD={g.get('max_dd', 0.0):5.1f}")
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 140, flush=True)
        print(f"  STAGE 16 TARGET-DERIVED MINIMUM RR — BYBIT {scope.upper()}", flush=True)
        print("=" * 140, flush=True)
        result = run_scope(scope)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
