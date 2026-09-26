"""Bybit-only shadow-book opportunity autopsy.

For every post-HTF, pre-portfolio LTF candidate, record the causal decision
state and calculate a standalone structural shadow outcome. Accepted rows are
matched to the actual trade ledger. This is diagnostic only; production code is
untouched.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import numpy as np
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_shadow_book_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_shadow_book_results_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")


def prepare_shadow_cache(data):
    data["_shadow_candle_ts"] = [int(c["ts"]) for c in data["c15"]]
    data["_shadow_fine_ts"] = [int(c["ts"]) for c in data["fine"]]
    data["_shadow_atr"] = atr_series(data["c15"])
    data["_shadow_fine_hi"] = np.fromiter((float(c["high"]) for c in data["fine"]), dtype=np.float64)
    data["_shadow_fine_lo"] = np.fromiter((float(c["low"]) for c in data["fine"]), dtype=np.float64)
    data["_shadow_fine_open"] = np.fromiter((float(c["open"]) for c in data["fine"]), dtype=np.float64)
    data["_shadow_fine_close"] = np.fromiter((float(c["close"]) for c in data["fine"]), dtype=np.float64)
    pos_by_date = {c["date"]: k for k, c in enumerate(data["c15"])}
    events = {"up": [], "down": []}
    for swing in data["sw15"]:
        direction = swing.get("dir")
        if direction not in events:
            continue
        confirmed = swing.get("confirmed_at_time", "")
        pos = pos_by_date.get(confirmed)
        if pos is not None:
            events[direction].append((pos, float(swing["seg"]["start_px"])))
    events["up"].sort(); events["down"].sort()
    data["_shadow_events"] = events
    return data


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    data = get_data()
    identity_gate(data, build_module())
    return data


def stats(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for value in xs:
        cum += value; peak = max(peak, cum); dd = max(dd, peak - cum)
        if value > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    loss_sum = sum(losses)
    win_sum = sum(wins)
    return {"n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "wr_pct": round(100.0 * len(wins) / len(xs), 3), "avg_win": round(aw, 4),
            "avg_loss": round(al, 4), "payoff": round(aw / abs(al), 4) if al else None,
            "pf": round(win_sum / abs(loss_sum), 4) if loss_sum else None,
            "max_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
            "median": round(statistics.median(xs), 6),
            "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0}


def atr_series(candles):
    tr = []
    for i, c in enumerate(candles):
        if i == 0:
            tr.append(float(c["high"]) - float(c["low"]))
        else:
            pc = float(candles[i - 1]["close"])
            tr.append(max(float(c["high"]) - float(c["low"]),
                          abs(float(c["high"]) - pc), abs(float(c["low"]) - pc)))
    out = []
    for i in range(len(candles)):
        lo = max(0, i - 13)
        out.append(sum(tr[lo:i + 1]) / (i - lo + 1))
    return out


def active_mark(active, candles, fine, fine_ts, now_ts):
    """Mark active trades causally at the candidate timestamp."""
    idx = bisect.bisect_right(fine_ts, now_ts) - 1
    if idx < 0:
        idx = 0
    mark_rows = []
    for t in active or []:
        entry = float(t["entry_price"]); sl = float(t["sl"])
        risk = abs(entry - sl)
        start = bisect.bisect_left(fine_ts, int(t["entry_ts"]))
        end = min(idx, len(fine) - 1)
        highs = [float(fine[k]["high"]) for k in range(start, end + 1)]
        lows = [float(fine[k]["low"]) for k in range(start, end + 1)]
        direction = 1 if t.get("dir") == "long" else -1
        price = float(fine[idx]["close"]) if fine else float(candles[-1]["close"])
        marked = ((price - entry) if direction > 0 else (entry - price)) / risk if risk else 0.0
        mfe = ((max(highs) - entry) if direction > 0 else (entry - min(lows))) / risk if highs and lows and risk else 0.0
        mae = ((entry - min(lows)) if direction > 0 else (max(highs) - entry)) / risk if highs and lows and risk else 0.0
        mark_rows.append({"dir": t.get("dir"), "entry_ts": t.get("entry_ts"),
                          "marked_r": round(marked, 6), "mfe_r": round(mfe, 6),
                          "mae_r": round(mae, 6),
                          "age_hours": round((now_ts - int(t["entry_ts"])) / 3600.0, 3)})
    return mark_rows


def trade_key(trade):
    return (int(trade["entry_idx"]), 1 if trade.get("dir") == "long" else -1)


def attach_shadow_rows(rows, data, params, real_trades):
    """Attach standalone outcomes and mark real accept/skip provenance."""
    real_by_key = {trade_key(t): t for t in real_trades}
    enriched = []
    for row in rows:
        sig = row["signal"]; i = int(row["entry_idx"])
        now = int(row["entry_ts"])
        direction = 1 if sig.get("dir") == 1 else -1
        key = (i, direction)
        real = real_by_key.get(key)
        shadow = shadow_trade(row, data, params)
        reason = row.get("reason", "accepted")
        if real is None and reason == "accepted":
            reason = "not_taken_after_record"
        active = row.get("active", [])
        marked = active_mark(active, data["c15"], data["fine"],
                             [int(c["ts"]) for c in data["fine"]], now)
        enriched.append({
            "entry_idx": i, "entry_ts": now, "bar_time": row["bar_time"],
            "dir": "long" if direction > 0 else "short", "use": row.get("use"),
            "signal": sig, "reason": reason, "active_count": row.get("active_count", 0),
            "active": active, "active_marked": marked,
            "real_trade_no": real.get("trade_no") if real else None,
            "real_trade": real,
            "real_r": float(real.get("r_multiple")) if real else None,
            "real_exit_ts": int(real.get("exit_ts")) if real else None,
            "shadow": shadow,
        })
    return enriched


def metrics_for_rows(rows, field):
    values = [r[field].get("r_multiple") for r in rows if r.get(field)]
    return stats(values)


def row_metrics(rows):
    return {
        "count": len(rows),
        "real": metrics_for_rows(rows, "real_trade"),
        "shadow": metrics_for_rows(rows, "shadow"),
        "mfe": stats([r["shadow"].get("mfe_r") for r in rows if r.get("shadow")]),
        "mae": stats([r["shadow"].get("mae_r") for r in rows if r.get("shadow")]),
        "time_to_mfe_min": stats([r["shadow"].get("time_to_mfe_min") for r in rows if r.get("shadow")]),
    }


def shadow_trade(row, data, params):
    """Run the current v18 structural exit for one candidate in isolation."""
    sig = row["signal"]; i = int(row["entry_idx"]); c15 = data["c15"]; fine = data["fine"]
    if i < 0 or i >= len(c15) - 1 or not fine:
        return None
    direction = int(sig["dir"]); entry = float(c15[i]["close"])
    atr = data["_shadow_atr"][i]
    pivot = float(sig["swing_start_px"])
    if direction > 0:
        sl = pivot - float(params.get("sl_buf_atr", 0.0)) * atr
        risk = entry - sl
        if sl >= entry or risk < 0.0005 * entry:
            return None
    else:
        sl = pivot + float(params.get("sl_buf_atr", 0.0)) * atr
        risk = sl - entry
        if sl <= entry or risk < 0.0005 * entry:
            return None
    target = entry + (3.0 * risk if direction > 0 else -3.0 * risk)




    candle_ts = data["_shadow_candle_ts"]
    fine_ts = data["_shadow_fine_ts"]
    n = len(candle_ts)
    bar_ts = candle_ts[i]
    want_dir = "up" if direction > 0 else "down"
    events = [e for e in data["_shadow_events"][want_dir]
              if candle_ts[min(e[0] + 1, n - 1)] > bar_ts]
    f_start = bisect.bisect_left(fine_ts, candle_ts[i + 1])
    event_positions = [bisect.bisect_left(fine_ts, candle_ts[min(e[0] + 1, n - 1)])
                       for e in events]
    event_positions = [p for p in event_positions if p >= f_start]
    events = [e for e, p in zip(events, [p for p in [bisect.bisect_left(fine_ts, candle_ts[min(e[0] + 1, n - 1)]) for e in events] if p >= f_start])]
    sl_cur = sl; ev_idx = -1
    exit_k = None; exit_px = None; outcome = "open"
    mfe = 0.0; mae = 0.0; first_mfe_ts = None
    hi_arr = data["_shadow_fine_hi"]; lo_arr = data["_shadow_fine_lo"]
    open_arr = data["_shadow_fine_open"]
    k = f_start
    while k < len(fine):
        while ev_idx + 1 < len(event_positions) and event_positions[ev_idx + 1] <= k:
            ev_idx += 1
            pivot_px = events[ev_idx][1]
            if direction > 0 and sl_cur < pivot_px:
                sl_cur = pivot_px
            elif direction < 0 and pivot_px < sl_cur:
                sl_cur = pivot_px
        end = event_positions[ev_idx + 1] if ev_idx + 1 < len(event_positions) else len(fine)
        end = max(k + 1, min(int(end), len(fine)))
        seg_hi = hi_arr[k:end]; seg_lo = lo_arr[k:end]
        if direction > 0:
            hit = np.flatnonzero(seg_lo <= sl_cur)
        else:
            hit = np.flatnonzero(seg_hi >= sl_cur)
        metric_len = int(hit[0]) + 1 if len(hit) else len(seg_hi)
        metric_hi = seg_hi[:metric_len]; metric_lo = seg_lo[:metric_len]
        fav = float(np.max(metric_hi) - entry) if direction > 0 else float(entry - np.min(metric_lo))
        adv = float(entry - np.min(metric_lo)) if direction > 0 else float(np.max(metric_hi) - entry)
        if fav > mfe:
            mfe = fav
            rel = int(np.argmax(metric_hi)) if direction > 0 else int(np.argmin(metric_lo))
            first_mfe_ts = int(fine_ts[k + rel])
        if adv > mae:
            mae = adv
        if len(hit):
            rel = int(hit[0]); exit_k = k + rel
            exit_px = (min(sl_cur, float(open_arr[exit_k])) if direction > 0
                       else max(sl_cur, float(open_arr[exit_k])))
            outcome = "sl" if (sl_cur <= sl if direction > 0 else sl_cur >= sl) else "trail"
            break
        k = end
    if exit_k is None:
        exit_k = len(fine) - 1; exit_px = float(data["_shadow_fine_close"][-1]); outcome = "open"
    move = (exit_px - entry) if direction > 0 else (entry - exit_px)
    r = move / risk if risk else 0.0
    return {"entry_idx": i, "entry_ts": bar_ts, "exit_ts": int(fine[exit_k]["ts"]),
            "dir": "long" if direction > 0 else "short", "entry_price": entry,
            "sl": sl, "target": target, "exit_price": exit_px, "outcome": outcome,
            "r_multiple": round(r, 6), "mfe_r": round(mfe / risk, 6) if risk else 0.0,
            "mae_r": round(mae / risk, 6) if risk else 0.0,
            "time_to_mfe_min": round((first_mfe_ts - bar_ts) / 60.0, 3) if first_mfe_ts else None,
            "bars_held": max(0, exit_k - f_start + 1), "shadow": True}


def net_stats(trades):
    if not trades:
        return {"n": 0}
    gross = stats([float(t.get("r_multiple") or 0.0) for t in trades])
    net = stats([net_r([t]) for t in trades])
    return {"gross": gross, "net": net, "cost_and_funding": round(gross["sum_r"] - net["sum_r"], 4)}


def summarize_rows(rows):
    accepted = [r for r in rows if r.get("real_trade") is not None]
    skipped = [r for r in rows if r.get("real_trade") is None]
    real_trades = [r["real_trade"] for r in accepted]
    shadow_trades = [r["shadow"] for r in rows if r.get("shadow")]
    reasons = defaultdict(list)
    for r in rows:
        reasons[r.get("reason", "unknown")].append(r)
    active = defaultdict(list)
    for r in rows:
        active[str(int(r.get("active_count") or 0))].append(r)
    marked = defaultdict(list)
    for r in rows:
        vals = [float(x.get("marked_r") or 0.0) for x in r.get("active_marked", [])]
        if not vals:
            bucket = "none"
        else:
            m = sum(vals) / len(vals)
            bucket = "<=-0.5" if m <= -0.5 else "-0.5..0" if m < 0 else "0..1" if m < 1 else ">=1"
        marked[bucket].append(r)
    return {
        "candidate_count": len(rows), "accepted_count": len(accepted), "skipped_count": len(skipped),
        "accepted_match": {"real_trade_count": len(real_trades),
                           "real_gross": round(sum(float(t.get("r_multiple") or 0.0) for t in real_trades), 6),
                           "real_net": round(sum(net_r([t]) for t in real_trades), 6)},
        "accepted": row_metrics(accepted), "skipped": row_metrics(skipped),
        "all_shadow": row_metrics(rows),
        "by_reason": {k: row_metrics(v) for k, v in sorted(reasons.items())},
        "by_active_count": {k: row_metrics(v) for k, v in sorted(active.items(), key=lambda z: int(z[0]))},
        "by_active_marked_r": {k: row_metrics(v) for k, v in sorted(marked.items())},
        "real_net_stats": net_stats(real_trades),
    }


def run_scope(scope, data, sim):
    result = {"instrument": "BTCUSDT_BYBIT", "scope": scope, "configs": {}}
    for key in CONFIGS:
        base = {**BP, **EXPERIMENTS[key]["params"]}
        base.setdefault("exp_partial_r", 0.0)
        params = {**base, "exp_shadow_book": True}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        real = out["ltf_trades"] if isinstance(out, dict) else out
        rows = out.get("shadow_rows", []) if isinstance(out, dict) else []
        enriched = attach_shadow_rows(rows, data, base, real)
        result["configs"][key] = {"baseline_trade_count": len(real),
                                   "shadow_candidate_count": len(rows),
                                   "summary": summarize_rows(enriched)}
        s = result["configs"][key]["summary"]
        print(f"  {scope.upper():3} {key:24} candidates={s['candidate_count']:4d} accepted={s['accepted_count']:3d} skipped={s['skipped_count']:3d} | real net={s['real_net_stats']['net']['sum_r']:+7.1f}R shadow all gross={sum(float(r['shadow']['r_multiple']) for r in enriched if r.get('shadow')):+7.1f}R", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    for scope in scopes:
        print("=" * 115, flush=True)
        print(f"  SHADOW-BOOK OPPORTUNITY AUTOPSY — BYBIT {scope.upper()}", flush=True)
        print("=" * 115, flush=True)
        data = prepare_shadow_cache(load_scope(scope))
        result = run_scope(scope, data, sim)
        OUT[scope].write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {OUT[scope]}", flush=True)


if __name__ == "__main__":
    main()
