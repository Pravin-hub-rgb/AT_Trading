"""Read-only thesis autopsy: does a v18 entry select better future movement?

Stage 1 compares real entries with matched non-entry bars from the same parent
HTF interval, direction, UTC hour, and nearest ATR%. It is diagnostic only:
no engine patch, no new trading flag, and no filter adoption.

Run:
  python -m backtest.tests.exp_thesis_autopsy --stage 1
  python -m backtest.tests.exp_thesis_autopsy --stage 1 --scope oos
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import BP, get_data, identity_gate, net_r
from test_experiments_craze import build_module
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_fine_1m as load_fine_unseen, load_unseen
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.walker import FlowCandle

OUT_IS = ROOT / "backtest/tests/_thesis_stage1_results_is.json"
OUT_OOS = ROOT / "backtest/tests/_thesis_stage1_results_oos.json"
OUT_STAGE2_IS = ROOT / "backtest/tests/_thesis_stage2_results_is.json"
OUT_STAGE2_OOS = ROOT / "backtest/tests/_thesis_stage2_results_oos.json"
OUT_STAGE3_IS = ROOT / "backtest/tests/_thesis_stage3_results_is.json"
OUT_STAGE3_OOS = ROOT / "backtest/tests/_thesis_stage3_results_oos.json"
OUT_STAGE4_IS = ROOT / "backtest/tests/_thesis_stage4_results_is.json"
OUT_STAGE4_OOS = ROOT / "backtest/tests/_thesis_stage4_results_oos.json"
OUT_STAGE5 = ROOT / "backtest/tests/_thesis_stage5_results.json"
STAGE2_TARGETS = (1.0, 2.0, 3.0, 5.0)
STAGE2_BARS = (16, 32, 48, 96)
STAGE3_DELAYS = (4, 8, 16, 32)
STAGE4_BOOTSTRAPS = 5000
STAGE4_SEED = 2701
HORIZONS = (1, 4, 8, 16, 32, 48)
MAX_CONTROLS = 20
SEED = 1701


def pct(value):
    return None if value is None else round(100.0 * float(value), 4)


def stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    ys = sorted(xs)
    return {
        "n": len(xs),
        "mean": round(sum(xs) / len(xs), 6),
        "median": round(ys[len(ys) // 2], 6),
        "positive_pct": round(100.0 * sum(x > 0 for x in xs) / len(xs), 3),
        "q10": round(ys[max(0, int(0.10 * len(ys)) - 1)], 6),
        "q90": round(ys[min(len(ys) - 1, int(0.90 * len(ys)))], 6),
    }


def causal_atr_pct(candles):
    tr = [0.0] * len(candles)
    atr = [0.0] * len(candles)
    for i, candle in enumerate(candles):
        hi, lo = float(candle["high"]), float(candle["low"])
        prev_close = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
        j = max(0, i - 13)
        atr[i] = sum(tr[j:i + 1]) / (i - j + 1)
    return [100.0 * atr[i] / float(candles[i]["close"])
            if float(candles[i]["close"]) else 0.0 for i in range(len(candles))]


def forward_path(candles, index, direction, horizon):
    if index + horizon >= len(candles):
        return None, None, None
    close = float(candles[index]["close"])
    if close <= 0:
        return None, None, None
    end = index + horizon
    forward = direction * (float(candles[end]["close"]) / close - 1.0)
    highs = [float(candles[k]["high"]) for k in range(index + 1, end + 1)]
    lows = [float(candles[k]["low"]) for k in range(index + 1, end + 1)]
    if direction > 0:
        mfe = max(highs) / close - 1.0
        mae = min(lows) / close - 1.0
    else:
        mfe = 1.0 - min(lows) / close
        mae = 1.0 - max(highs) / close
    return forward, mfe, mae


def parent_interval(trade, intervals):
    timestamp = int(trade["entry_ts"])
    direction = 1 if trade["dir"] == "long" else -1
    matches = [iv for iv in intervals
               if int(iv[0]) < timestamp <= int(iv[1]) and int(iv[2]) == direction]
    if not matches:
        return None
    return min(matches, key=lambda iv: abs((timestamp - int(iv[0]))
                                            - (int(iv[1]) - timestamp)))


def matched_control_indices(trade, intervals, candles, actual_entry_ts, atr_pct):
    interval = parent_interval(trade, intervals)
    if interval is None:
        return []
    start, end, direction = int(interval[0]), int(interval[1]), int(interval[2])
    entry_ts = int(trade["entry_ts"])
    actual_i = next((i for i, c in enumerate(candles) if int(c["ts"]) == entry_ts), None)
    if actual_i is None:
        return []
    actual_atr = atr_pct[actual_i]
    actual_hour = time.gmtime(entry_ts).tm_hour
    candidates = []
    for i, candle in enumerate(candles):
        timestamp = int(candle["ts"])
        if not (start + 2700 < timestamp <= end + 2700):
            continue
        if timestamp in actual_entry_ts or i + max(HORIZONS) >= len(candles):
            continue
        if time.gmtime(timestamp).tm_hour != actual_hour:
            continue
        candidates.append((abs(atr_pct[i] - actual_atr), i))
    candidates.sort()
    return [i for _, i in candidates[:MAX_CONTROLS]]


def run_stage1(scope):
    started = time.time()
    print("=" * 100, flush=True)
    print("  THESIS AUTOPSY — STAGE 1 — SIGNAL PREDICTIVE POWER", flush=True)
    print("=" * 100, flush=True)
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_unseen(c15[0]["ts"], c15[-1]["ts"])
        data = {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}
    else:
        data = get_data()
    sim = build_module()
    if scope != "oos":
        identity_gate(data, sim)
    atr_pct = causal_atr_pct(data["c15"])
    all_rows = {}
    for key in ("champion_multi_sw10", "utcsat_multi_sw10"):
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"]
        intervals = out.get("intervals", [])
        actual_entry_ts = {int(t["entry_ts"]) for t in trades}
        rows = []
        for trade in trades:
            entry_ts = int(trade["entry_ts"])
            index = next((i for i, c in enumerate(data["c15"])
                          if int(c["ts"]) == entry_ts), None)
            if index is None:
                continue
            direction = 1 if trade["dir"] == "long" else -1
            controls = matched_control_indices(trade, intervals, data["c15"],
                                               actual_entry_ts, atr_pct)
            row = {"trade_no": trade.get("trade_no"), "entry_ts": entry_ts,
                   "direction": direction, "kind": trade.get("break_kind"),
                   "regime": trade.get("htf_regime"), "net_r": net_r([trade]),
                   "n_controls": len(controls), "actual": {}, "control": {}}
            for horizon in HORIZONS:
                actual = forward_path(data["c15"], index, direction, horizon)
                controls_path = [forward_path(data["c15"], k, direction, horizon)
                                 for k in controls]
                row["actual"][str(horizon)] = {
                    "forward": pct(actual[0]), "mfe": pct(actual[1]), "mae": pct(actual[2])}
                row["control"][str(horizon)] = {
                    "forward": stats([pct(x[0]) for x in controls_path]),
                    "mfe": stats([pct(x[1]) for x in controls_path]),
                    "mae": stats([pct(x[2]) for x in controls_path]),
                }
            rows.append(row)
        all_rows[key] = {"trade_count": len(trades), "net_r": net_r(trades), "rows": rows}
        print(f"\n  {key}: {len(trades)} trades / NET {net_r(trades):+.1f}R", flush=True)
        for horizon in HORIZONS:
            actual = [r["actual"][str(horizon)]["forward"] for r in rows]
            a = stats(actual)
            control_stats = [r["control"][str(horizon)]["forward"] for r in rows]
            control_n = sum(s.get("n", 0) for s in control_stats)
            control_mean = (sum(s.get("mean", 0.0) * s.get("n", 0) for s in control_stats)
                            / control_n if control_n else 0.0)
            print(f"  {horizon:>2} bars: actual={a.get('mean', 0.0):+.3f}% "
                  f"control={control_mean:+.3f}% "
                  f"delta={a.get('mean', 0.0) - control_mean:+.3f}%", flush=True)
    result = {"stage": 1, "scope": scope, "horizons": HORIZONS, "seed": SEED,
              "match": "same parent HTF interval + direction + UTC hour + nearest ATR%",
              "elapsed_sec": round(time.time() - started, 2), "configs": all_rows}
    output = OUT_OOS if scope == "oos" else OUT_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output} ({result['elapsed_sec']}s)", flush=True)
    return result



def fixed_exit_path(fine, fine_ts, entry_ts, entry, initial_sl, direction,
                    target_r=None, time_bars=None):
    """Replay one real entry with no structural trail and an optional target/time exit."""
    start = bisect.bisect_left(fine_ts, int(entry_ts) + 900)
    if start >= len(fine):
        return None
    risk = abs(float(entry) - float(initial_sl))
    if risk <= 0:
        return None
    target = None
    if target_r is not None:
        target = float(entry) + direction * target_r * risk
    end = len(fine) if time_bars is None else min(len(fine), start + int(time_bars))
    for k in range(start, end):
        candle = fine[k]
        hi, lo, op = float(candle["high"]), float(candle["low"]), float(candle["open"])
        if direction > 0:
            if lo <= initial_sl:
                exit_px = min(initial_sl, op)
                outcome = "sl"
                break
            if target is not None and hi >= target:
                exit_px, outcome = target, "target"
                break
        else:
            if hi >= initial_sl:
                exit_px = max(initial_sl, op)
                outcome = "sl"
                break
            if target is not None and lo <= target:
                exit_px, outcome = target, "target"
                break
    else:
        k = max(start, end - 1)
        exit_px = float(fine[k]["close"])
        outcome = "time" if time_bars is not None else "open"
    move = (exit_px - float(entry)) if direction > 0 else (float(entry) - exit_px)
    return {"r": move / risk, "exit_px": exit_px, "outcome": outcome,
            "bars": k - start + 1, "entry_fine_idx": start, "exit_fine_idx": k}


def stage2_summary(trades, paths):
    rows = []
    for trade, path_set in zip(trades, paths):
        if path_set is None:
            continue
        row = {"trade_no": trade.get("trade_no"),
               "entry_ts": int(trade["entry_ts"]),
               "direction": 1 if trade["dir"] == "long" else -1,
               "current_r": float(trade["r_multiple"]), "variants": path_set}
        rows.append(row)
    return rows


def run_stage2(scope):
    started = time.time()
    print("=" * 100, flush=True)
    print("  THESIS AUTOPSY — STAGE 2 — ENTRY VS EXIT DECOMPOSITION", flush=True)
    print("=" * 100, flush=True)
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_unseen(c15[0]["ts"], c15[-1]["ts"])
        data = {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}
    else:
        data = get_data()
    sim = build_module()
    if scope != "oos":
        identity_gate(data, sim)
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    result = {"stage": 2, "scope": scope, "targets": STAGE2_TARGETS,
              "time_bars": STAGE2_BARS, "configs": {}}
    for key in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"]
        rows = []
        for trade in trades:
            entry = float(trade["entry_price"])
            sl = float(trade["sl"])
            direction = 1 if trade["dir"] == "long" else -1
            variants = {"current": {"r": float(trade["r_multiple"]),
                                    "bars": int(trade.get("bars_held") or 0),
                                    "outcome": trade.get("outcome")}}
            for target_r in STAGE2_TARGETS:
                path = fixed_exit_path(data["fine"], fine_ts, int(trade["entry_ts"]),
                                       entry, sl, direction, target_r=target_r)
                variants[f"target_{target_r:g}R"] = path
            for bars in STAGE2_BARS:
                path = fixed_exit_path(data["fine"], fine_ts, int(trade["entry_ts"]),
                                       entry, sl, direction, time_bars=bars)
                variants[f"time_{bars}m"] = path
            rows.append({"trade_no": trade.get("trade_no"),
                         "entry_ts": int(trade["entry_ts"]), "direction": direction,
                         "kind": trade.get("break_kind"), "regime": trade.get("htf_regime"),
                         "variants": variants})
        summaries = {}
        for name in rows[0]["variants"]:
            values = [r["variants"][name]["r"] for r in rows
                      if r["variants"].get(name)]
            summaries[name] = {"n": len(values), "sum_r": round(sum(values), 4),
                               "mean_r": round(sum(values) / len(values), 6),
                               "win_pct": round(100.0 * sum(v > 0 for v in values) / len(values), 3),
                               "losers": sum(v <= 0 for v in values),
                               "winners": sum(v > 0 for v in values)}
        result["configs"][key] = {"trade_count": len(trades), "net_r": net_r(trades),
                                  "summaries": summaries, "rows": rows}
        print(f"\n  {key}: {len(trades)} trades / current NET {net_r(trades):+.1f}R", flush=True)
        for name, summary in summaries.items():
            print(f"    {name:<14} sum={summary['sum_r']:+8.1f} "
                  f"avg={summary['mean_r']:+.3f} WR={summary['win_pct']:5.1f}%", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    output = OUT_STAGE2_OOS if scope == "oos" else OUT_STAGE2_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output} ({result['elapsed_sec']}s)", flush=True)
    return result




def stage3_path(fine, fine_ts, c15, candles, trade, direction_override=None,
                delay_bars=0, random_index=None):
    direction = (direction_override if direction_override is not None
                 else (1 if trade["dir"] == "long" else -1))
    entry_ts = int(trade["entry_ts"])
    entry_i = next((i for i, c in enumerate(candles) if int(c["ts"]) == entry_ts), None)
    if entry_i is None:
        return None
    if random_index is not None:
        entry_i = random_index
        entry_ts = int(candles[entry_i]["ts"])
    entry_i += int(delay_bars)
    if entry_i >= len(candles):
        return None
    entry_ts = int(candles[entry_i]["ts"])
    entry = float(candles[entry_i]["close"])
    original_risk = abs(float(trade["entry_price"]) - float(trade["sl"]))
    initial_sl = entry - direction * original_risk
    result = {"direction": direction, "entry_ts": entry_ts, "entry_price": entry,
              "initial_sl": initial_sl, "risk": original_risk}
    for target_r in STAGE2_TARGETS:
        result[f"target_{target_r:g}R"] = fixed_exit_path(
            fine, fine_ts, entry_ts, entry, initial_sl, direction, target_r=target_r)
    for bars in STAGE2_BARS:
        result[f"time_{bars}m"] = fixed_exit_path(
            fine, fine_ts, entry_ts, entry, initial_sl, direction, time_bars=bars)
    return result


def run_stage3(scope):
    started = time.time()
    print("=" * 100, flush=True)
    print("  THESIS AUTOPSY — STAGE 3 — PLACEBO / DELAY / REVERSE CONTROLS", flush=True)
    print("=" * 100, flush=True)
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_unseen(c15[0]["ts"], c15[-1]["ts"])
        data = {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}
    else:
        data = get_data()
    sim = build_module()
    if scope != "oos":
        identity_gate(data, sim)
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    c15 = data["c15"]
    atr_pct = causal_atr_pct(c15)
    result = {"stage": 3, "scope": scope, "delays": STAGE3_DELAYS, "configs": {}}
    for key in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], c15, data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"]
        actual_entry_ts = {int(t["entry_ts"]) for t in trades}
        rows = []
        for trade in trades:
            direction = 1 if trade["dir"] == "long" else -1
            parent = parent_interval(trade, out.get("intervals", []))
            candidates = []
            if parent is not None:
                start, end = int(parent[0]), int(parent[1])
                ets = int(trade["entry_ts"])
                actual_i = next((i for i, c in enumerate(c15)
                                 if int(c["ts"]) == ets), None)
                actual_atr = atr_pct[actual_i] if actual_i is not None else 0.0
                actual_hour = time.gmtime(ets).tm_hour
                for i, c in enumerate(c15):
                    ts = int(c["ts"])
                    if not (start + 2700 < ts <= end + 2700):
                        continue
                    if ts in actual_entry_ts or i + max(STAGE3_DELAYS) >= len(c15):
                        continue
                    if time.gmtime(ts).tm_hour != actual_hour:
                        continue
                    candidates.append((abs(atr_pct[i] - actual_atr), i))
                candidates.sort()
            row = {"trade_no": trade.get("trade_no"),
                   "entry_ts": int(trade["entry_ts"]), "direction": direction,
                   "current_r": float(trade["r_multiple"]), "controls": {}}
            row["controls"]["random_entry"] = stage3_path(
                data["fine"], fine_ts, c15, c15, trade,
                random_index=(random.Random(SEED + int(trade.get("trade_no") or 0)).choice(candidates)[1]
                              if candidates else None))
            for delay in STAGE3_DELAYS:
                row["controls"][f"delay_{delay}"] = stage3_path(
                    data["fine"], fine_ts, c15, c15, trade, delay_bars=delay)
            row["controls"]["reverse_direction"] = stage3_path(
                data["fine"], fine_ts, c15, c15, trade, direction_override=-direction)
            rows.append(row)
        summaries = {}
        control_names = ["random_entry"] + [f"delay_{d}" for d in STAGE3_DELAYS] + ["reverse_direction"]
        for control in control_names:
            for variant in ("target_3R", "target_5R", "time_96m"):
                values = []
                for row in rows:
                    path = row["controls"].get(control)
                    if path and path.get(variant):
                        values.append(path[variant]["r"])
                summaries[f"{control}/{variant}"] = {
                    "n": len(values), "sum_r": round(sum(values), 4),
                    "mean_r": round(sum(values) / len(values), 6),
                    "win_pct": round(100.0 * sum(v > 0 for v in values) / len(values), 3),
                }
        result["configs"][key] = {"trade_count": len(trades), "net_r": net_r(trades),
                                  "summaries": summaries, "rows": rows}
        print(f"\n  {key}: {len(trades)} trades / current NET {net_r(trades):+.1f}R", flush=True)
        for name, summary in summaries.items():
            print(f"    {name:<30} sum={summary['sum_r']:+8.1f} "
                  f"avg={summary['mean_r']:+.3f} WR={summary['win_pct']:5.1f}%", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    output = OUT_STAGE3_OOS if scope == "oos" else OUT_STAGE3_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output} ({result['elapsed_sec']}s)", flush=True)
    return result




def month_key(timestamp):
    tm = time.gmtime(int(timestamp))
    return f"{tm.tm_year:04d}-{tm.tm_mon:02d}"


def block_bootstrap(values, blocks, reps=STAGE4_BOOTSTRAPS, seed=STAGE4_SEED):
    grouped = defaultdict(list)
    for value, block in zip(values, blocks):
        grouped[block].append(float(value))
    block_values = [sum(grouped[k]) for k in sorted(grouped)]
    rng = random.Random(seed)
    samples = []
    for _ in range(reps):
        samples.append(sum(rng.choice(block_values) for _ in block_values))
    return stats(samples)


def research_inventory():
    tests = ROOT / "backtest/tests"
    docs = ROOT / "backtest/docs"
    return {
        "experiment_harnesses": len(list(tests.glob("exp_*.py"))),
        "test_harnesses": len(list(tests.glob("test_*.py"))),
        "experiment_documents": len(list(docs.glob("*experiment*.md"))),
        "registry_keys": len(EXPERIMENTS),
        "note": "Lower-bound inventory of current files/registry, not a reconstruction of every historical variant.",
    }


def run_stage4(scope):
    started = time.time()
    print("=" * 100, flush=True)
    print("  THESIS AUTOPSY — STAGE 4 — NULL / BOOTSTRAP / SELECTION CHECK", flush=True)
    print("=" * 100, flush=True)
    source = OUT_STAGE3_OOS if scope == "oos" else OUT_STAGE3_IS
    data = json.loads(source.read_text(encoding="utf-8"))
    result = {"stage": 4, "scope": scope, "source": str(source),
              "bootstrap_reps": STAGE4_BOOTSTRAPS, "seed": STAGE4_SEED,
              "research_inventory": research_inventory(), "configs": {}}
    for key, cfg in data["configs"].items():
        rows = cfg["rows"]
        current = [float(r["current_r"]) for r in rows]
        blocks = [month_key(r["entry_ts"]) for r in rows]
        current_boot = block_bootstrap(current, blocks)
        by_year = defaultdict(list)
        for value, block in zip(current, blocks):
            by_year[block[:4]].append(value)
        leave_year = {year: round(sum(current) - sum(values), 4)
                      for year, values in sorted(by_year.items())}
        result["configs"][key] = {
            "n": len(current), "observed_sum_r": round(sum(current), 4),
            "monthly_bootstrap": current_boot,
            "leave_one_year_out": leave_year,
            "positive_months": sum(1 for b in sorted(set(blocks))
                                    if sum(v for v, x in zip(current, blocks) if x == b) > 0),
            "months": len(set(blocks)),
            "control_summaries": cfg.get("summaries", {}),
        }
        print(f"\n  {key}: observed {sum(current):+.1f}R / {len(current)} trades", flush=True)
        print(f"    month bootstrap mean {current_boot.get('mean', 0.0):+.1f}R, "
              f"positive {100.0 * current_boot.get('positive_pct', 0.0) / 100.0:.1f}%", flush=True)
        print(f"    leave-one-year-out: {leave_year}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    output = OUT_STAGE4_OOS if scope == "oos" else OUT_STAGE4_IS
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {output} ({result['elapsed_sec']}s)", flush=True)
    return result




def load_venue(symbol):
    frames = {}
    for tf in ("15m", "1h"):
        df = load_btc_df(tf, symbol)
        candles, flow = [], []
        for row in df.itertuples():
            date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                            "high": float(row.high), "low": float(row.low),
                            "close": float(row.close),
                            "volume": float(getattr(row, "volume", 0.0) or 0.0)})
            flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                                   low=float(row.low), close=float(row.close)))
        frames[tf] = (candles, flow)
    c15, f15 = frames["15m"]
    c1h, f1h = frames["1h"]
    fine = _load_fine_1m(min(c15[0]["ts"], c1h[0]["ts"]),
                        max(c15[-1]["ts"], c1h[-1]["ts"]), symbol=symbol)
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "fine": fine}


def trade_summary(trades):
    rs = [float(t.get("r_multiple") or 0.0) for t in trades]
    if not rs:
        return {"n": 0, "gross_r": 0.0, "net_common_cost_r": 0.0, "wr": 0.0,
                "pf": 0.0, "dd": 0.0, "years": {}, "avg_bars": 0.0}
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    peak = cum = dd = 0.0
    for value in rs:
        cum += value
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    years = defaultdict(float)
    for trade, value in zip(trades, rs):
        years[(trade.get("entry_date") or "")[:4]] += value
    costs, _ = _trade_costs(list(trades), 0.055, 0.0, 0.005, 0.010)
    # Common-cost estimate deliberately excludes funding so spot/perp compare fairly.
    return {"n": len(rs), "gross_r": round(sum(rs), 3),
            "net_common_cost_r": round(sum(rs) - costs, 3),
            "wr": round(100.0 * len(wins) / len(rs), 3),
            "pf": round(sum(wins) / abs(sum(losses)), 3) if losses else 0.0,
            "dd": round(dd, 3), "years": {k: round(v, 3) for k, v in sorted(years.items())},
            "avg_bars": round(sum(int(t.get("bars_held") or 0) for t in trades) / len(trades), 2)}


def run_stage5():
    started = time.time()
    print("=" * 100, flush=True)
    print("  THESIS AUTOPSY — STAGE 5 — FIXED-ARCHITECTURE VENUE REPLICATION", flush=True)
    print("=" * 100, flush=True)
    sim = build_module()
    venues = {"BTCUSDT_BYBIT": "Bybit BTC perp",
              "BTCUSDT_PERP": "Binance BTC perp",
              "BTCUSDT": "Binance BTC spot"}
    configs = {"champion_multi_sw10": EXPERIMENTS["champion_multi_sw10"]["params"],
               "utcsat_multi_sw10": EXPERIMENTS["utcsat_multi_sw10"]["params"]}
    result = {"stage": 5, "architecture": "current v18 champion/king params, no venue retuning",
              "common_cost": {"fee_pct": 0.055, "entry_slip_pct": 0.005,
                              "exit_slip_pct": 0.010, "funding": "excluded for cross-venue comparison"},
              "venues": {}}
    for symbol, label in venues.items():
        print(f"\n  loading {label} ({symbol})", flush=True)
        data = load_venue(symbol)
        result["venues"][symbol] = {"label": label, "configs": {}}
        for key, overrides in configs.items():
            params = {**BP, **overrides}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            summary = trade_summary(trades)
            result["venues"][symbol]["configs"][key] = summary
            print(f"    {key}: n={summary['n']} gross={summary['gross_r']:+.1f}R "
                  f"net(common)={summary['net_common_cost_r']:+.1f}R "
                  f"WR={summary['wr']:.1f}% DD={summary['dd']:.1f}", flush=True)
        del data
    result["elapsed_sec"] = round(time.time() - started, 2)
    OUT_STAGE5.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT_STAGE5} ({result['elapsed_sec']}s)", flush=True)
    return result



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, default=1)
    parser.add_argument("--scope", choices=("is", "oos"), default="is")
    args = parser.parse_args()
    if args.stage == 1:
        run_stage1(args.scope)
    elif args.stage == 2:
        run_stage2(args.scope)
    elif args.stage == 3:
        run_stage3(args.scope)
    elif args.stage == 4:
        run_stage4(args.scope)
    elif args.stage == 5:
        run_stage5()
    else:
        raise SystemExit("Only stages 1, 2, 3, 4, and 5 are registered so far")


if __name__ == "__main__":
    main()

