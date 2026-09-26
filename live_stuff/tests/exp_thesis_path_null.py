"""Bybit-only chronology-destruction autopsy.

Keeps real trades, risk distances, and structural trail-event timing, but
replaces the 1m BTC path with deterministic block-bootstrap synthetic paths.
This is a null diagnostic, not a deployable strategy.

Run:
  python -m live_stuff.tests.exp_thesis_path_null --scope both
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import BP, get_data, identity_gate
from test_experiments_craze import build_module
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT_IS = ROOT / "live_stuff/tests/_thesis_path_null_results_is.json"
OUT_OOS = ROOT / "live_stuff/tests/_thesis_path_null_results_oos.json"
BLOCKS = (60, 240, 1440)
SEEDS = (1701, 2701, 3701)
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")


def summarize(values):
    xs = [float(x) for x in values]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    max_loss_streak = max_win_streak = 0
    loss_streak = win_streak = 0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if x <= 0:
            loss_streak += 1
            win_streak = 0
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            win_streak += 1
            loss_streak = 0
            max_win_streak = max(max_win_streak, win_streak)
    return {"n": len(xs), "sum_r": round(sum(xs), 4),
            "avg_r": round(sum(xs) / len(xs), 6),
            "wr": round(100.0 * len(wins) / len(xs), 3),
            "wins": len(wins), "losses": len(losses),
            "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
            "payoff": round((sum(wins) / len(wins)) / abs(sum(losses) / len(losses)), 4)
                      if wins and losses else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "dd": round(dd, 4), "max_loss_streak": max_loss_streak,
            "max_win_streak": max_win_streak,
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
            "median": round(statistics.median(xs), 6)}


def build_events(c15, sw15):
    date_to_i = {str(c["date"]): i for i, c in enumerate(c15)}
    by_dir = {1: [], -1: []}
    for swing in sw15:
        direction = 1 if swing.get("dir") == "up" else -1
        confirmed = str(swing.get("confirmed_at_time") or "")[:19]
        index = date_to_i.get(confirmed)
        if index is None or index + 1 >= len(c15):
            continue
        pivot = float(swing.get("seg", {}).get("start_px", 0.0))
        if pivot > 0:
            by_dir[direction].append((int(c15[index + 1]["ts"]), pivot))
    for direction in by_dir:
        by_dir[direction].sort()
    return by_dir


def replay_path(path, fine_ts, trade, events):
    entry_ts = int(trade["entry_ts"])
    entry = float(trade["entry_price"])
    initial_sl = float(trade["sl"])
    direction = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - initial_sl)
    if risk <= 0:
        return None
    start = bisect.bisect_left(fine_ts, entry_ts + 900)
    end_ts = int(trade.get("exit_ts") or fine_ts[-1])
    end = bisect.bisect_right(fine_ts, end_ts)
    end = min(end, len(path), len(fine_ts))
    if start >= end or start >= len(path):
        return None
    sl_cur = initial_sl
    event_list = events[direction]
    event_i = bisect.bisect_right([x[0] for x in event_list], entry_ts)
    exit_px = None
    outcome = "open"
    exit_i = end - 1
    for i in range(start, end):
        candle = path[i]
        timestamp = int(fine_ts[i])
        while event_i < len(event_list) and event_list[event_i][0] <= timestamp:
            candidate = float(event_list[event_i][1])
            if direction > 0 and candidate > sl_cur:
                sl_cur = candidate
            elif direction < 0 and candidate < sl_cur:
                sl_cur = candidate
            event_i += 1
        high = float(candle["high"])
        low = float(candle["low"])
        op = float(candle["open"])
        if direction > 0 and low <= sl_cur:
            exit_px = min(sl_cur, op)
            outcome = "sl" if sl_cur <= initial_sl else "trail"
            exit_i = i
            break
        if direction < 0 and high >= sl_cur:
            exit_px = max(sl_cur, op)
            outcome = "sl" if sl_cur >= initial_sl else "trail"
            exit_i = i
            break
    if exit_px is None:
        exit_px = float(path[exit_i]["close"])
    move = (exit_px - entry) if direction > 0 else (entry - exit_px)
    return {"r": move / risk, "outcome": outcome, "exit_i": exit_i}


def synthetic_path(real_path, rng, block, anchor):
    """Resample returns/wicks, then anchor synthetic prices to the real first open."""
    count = len(real_path)
    if count < 2:
        return real_path
    returns = []
    upper = []
    lower = []
    for i in range(1, count):
        prev = float(real_path[i - 1]["close"])
        close = float(real_path[i]["close"])
        returns.append(math.log(close / prev) if prev > 0 and close > 0 else 0.0)
    for candle in real_path:
        op = float(candle["open"])
        close = float(candle["close"])
        hi = float(candle["high"])
        lo = float(candle["low"])
        upper.append(max(hi - op, hi - close, 0.0) / close if close > 0 else 0.0)
        lower.append(max(op - lo, close - lo, 0.0) / close if close > 0 else 0.0)
    if len(returns) < 2:
        return real_path
    block_size = min(block, len(returns))
    blocks_needed = (len(returns) + block_size - 1) // block_size
    source = []
    while len(source) < blocks_needed:
        begin = rng.randrange(0, len(returns) - block_size + 1)
        source.extend(range(begin, begin + block_size))
    source = source[:len(returns)]
    first = real_path[0]
    out = [{"ts": int(first["ts"]), "open": float(anchor),
            "high": float(anchor) * (1.0 + upper[0]),
            "low": max(float(anchor) * (1.0 - lower[0]), 0.0),
            "close": float(anchor)}]
    previous_close = float(anchor)
    for j, source_i in enumerate(source, start=1):
        ret = returns[source_i]
        op = previous_close
        close = op * math.exp(ret)
        hi = max(op, close) * (1.0 + upper[source_i])
        lo = min(op, close) * (1.0 - lower[source_i])
        out.append({"ts": int(real_path[j]["ts"]), "open": op,
                    "high": hi, "low": max(lo, 0.0), "close": close})
        previous_close = close
    return out


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


def run_null(config_key, data, events, fine_ts, trades):
    actual_values = [float(t["r_multiple"]) for t in trades]
    real_replay_values = []
    real_errors = []
    for trade in trades:
        start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
        end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
        if start >= end:
            continue
        result = replay_path(data["fine"][start:end], fine_ts[start:end], trade, events)
        if result is not None:
            real_replay_values.append(result["r"])
            real_errors.append(abs(result["r"] - float(trade["r_multiple"])))
    validation = {
        "n_compared": len(real_errors),
        "exact_count": sum(err <= 0.01 for err in real_errors),
        "max_abs_error_r": max(real_errors) if real_errors else None,
        "mean_abs_error_r": sum(real_errors) / len(real_errors) if real_errors else None,
        "real_replay_summary": summarize(real_replay_values),
    }
    synthetic_rows = []
    for block in BLOCKS:
        for seed in SEEDS:
            rng = random.Random(seed + block + 101 * CONFIGS.index(config_key))
            vals = []
            for trade in trades:
                start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
                end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
                if start >= end:
                    continue
                segment = data["fine"][start:end]
                synthetic = synthetic_path(segment, rng, block, float(segment[0]["open"]))
                result = replay_path(synthetic, fine_ts[start:end], trade, events)
                if result is not None:
                    vals.append(result["r"])
            synthetic_rows.append({"block_bars": block, "seed": seed,
                                   "summary": summarize(vals)})
    return {"real_summary": summarize(actual_values),
            "real_path_validation": validation, "synthetic": synthetic_rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="is")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    result = {"stage": 6, "instrument": "BTCUSDT_BYBIT", "blocks": BLOCKS,
              "seeds": SEEDS, "scopes": {}}
    for scope in scopes:
        print("=" * 100, flush=True)
        print(f"  CHRONOLOGY-DESTRUCTION NULL — BYBIT {scope.upper()}", flush=True)
        print("=" * 100, flush=True)
        data = load_scope(scope)
        sim = build_module()
        events = build_events(data["c15"], data["sw15"])
        fine_ts = [int(c["ts"]) for c in data["fine"]]
        scope_result = {}
        for key in CONFIGS:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            config_result = run_null(key, data, events, fine_ts, out["ltf_trades"])
            scope_result[key] = config_result
            print(f"\n  {key}: real {config_result['real_summary']}", flush=True)
            print(f"    real-path validation: {config_result['real_path_validation']}", flush=True)
            for row in config_result["synthetic"]:
                s = row["summary"]
                print(f"    block={row['block_bars']:>4} seed={row['seed']} "
                      f"sum={s.get('sum_r', 0):+8.1f} avg={s.get('avg_r', 0):+.3f} "
                      f"WR={s.get('wr', 0):5.1f}% PF={s.get('pf', 0):.2f}", flush=True)
        result["scopes"][scope] = scope_result
    output = OUT_OOS if args.scope == "oos" else OUT_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output}", flush=True)


if __name__ == "__main__":
    main()


