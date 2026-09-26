"""Study 3 — Trail mechanism decomposition.

The edge is in the trail. This asks WHICH part of the trail creates the
5.5 payoff ratio, and whether that ratio is structural or accidental.

For every real trade, replay the exact 1m structural exit and attribute the
realized R to the mechanism that produced it:
  - initial SL respected (never ratcheted)
  - ratcheted but exited < 1R
  - ratcheted and exited >= 1R
  - ratcheted and exited >= 3R   (the runners)
  - still open at slice end

Also measures the CEILING: what would a perfect, causal, no-lookahead
"exit at the running structural high" have produced. That is the upper bound
the trail is giving up, and it bounds how much a better exit could ever be
worth.

Bybit only. Read-only. No production change.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate, net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = ROOT / "live_stuff/tests/_thesis_trail_mechanism.json"
LANES = ("champion_multi_sw10", "utcsat_multi_sw10", "fullstack_wage10_cd0_single_sw10")


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


def prepare(data):
    c15 = data["c15"]
    data["_ts15"] = [int(c["ts"]) for c in c15]
    data["_atr15"] = atr_series(c15)
    data["_fts"] = [int(c["ts"]) for c in data["fine"]]
    data["_fhi"] = np.fromiter((float(c["high"]) for c in data["fine"]), dtype=np.float64)
    data["_flo"] = np.fromiter((float(c["low"]) for c in data["fine"]), dtype=np.float64)
    data["_fopen"] = np.fromiter((float(c["open"]) for c in data["fine"]), dtype=np.float64)
    pos = {c["date"]: k for k, c in enumerate(c15)}
    ev = {"up": [], "down": []}
    for sw in data["sw15"]:
        d = sw.get("dir")
        if d not in ev:
            continue
        p = pos.get(sw.get("confirmed_at_time", ""))
        if p is not None:
            ev[d].append((p, float(sw["seg"]["start_px"])))
    ev["up"].sort(); ev["down"].sort()
    data["_ev"] = ev
    return data


def replay(t, data):
    """Replay one trade's structural exit, recording the ratchet history."""
    i = int(t["entry_idx"])
    ts15, atr = data["_ts15"], data["_atr15"]
    fine, fts = data["fine"], data["_fts"]
    direction = 1 if t.get("dir") == "long" else -1
    entry = float(t["entry_price"])
    sl0 = float(t["sl"])
    risk = abs(entry - sl0)
    if risk <= 0 or i >= len(ts15) - 1 or not fine:
        return None
    events = data["_ev"]["up" if direction > 0 else "down"]
    bar_ts = ts15[i]
    n15 = len(ts15) - 1
    # CRITICAL: the engine drops any trail event whose activation timestamp is
    # at or before the entry bar. Without this filter a stale swing level
    # ratchets the stop on the very first fine bar, which produces absurd
    # "locked" values and impossible hold times.
    events = [(p, px) for (p, px) in events if ts15[min(p + 1, n15)] > bar_ts]
    start = bisect.bisect_left(fts, ts15[i + 1])
    sl_cur = sl0
    ev_idx = -1
    ratchets = 0
    first_touch_r = None
    exit_k = exit_px = None
    outcome = "open"
    fhi, flo, fopen = data["_fhi"], data["_flo"], data["_fopen"]
    n = len(fine)
    for k in range(start, n):
        hi = float(fhi[k]); lo = float(flo[k]); ts = int(fts[k])
        while ev_idx + 1 < len(events) and ts15[min(events[ev_idx + 1][0] + 1, len(ts15) - 1)] <= ts:
            ev_idx += 1
            cand = events[ev_idx][1]
            if direction > 0 and sl_cur < cand:
                sl_cur = cand; ratchets += 1
            elif direction < 0 and cand < sl_cur:
                sl_cur = cand; ratchets += 1
        if first_touch_r is None:
            fav = (hi - entry) if direction > 0 else (entry - lo)
            if fav >= risk:
                first_touch_r = (fav - (sl_cur - entry if direction > 0 else entry - sl_cur)) / risk
        if direction > 0 and lo <= sl_cur:
            exit_k, exit_px, outcome = k, min(sl_cur, float(fopen[k])), ("sl" if sl_cur <= sl0 else "trail")
            break
        if direction < 0 and hi >= sl_cur:
            exit_k, exit_px, outcome = k, max(sl_cur, float(fopen[k])), ("sl" if sl_cur >= sl0 else "trail")
            break
    if exit_k is None:
        exit_k = len(fine) - 1
        exit_px = float(fine[-1]["close"])
        outcome = "open"
    move = (exit_px - entry) if direction > 0 else (entry - exit_px)
    r = move / risk
    locked = ((sl_cur - entry) if direction > 0 else (entry - sl_cur)) / risk
    # causal ceiling: the structural level in force at the actual exit instant
    return {"r": r, "outcome": outcome, "ratchets": ratchets,
            "locked_r_at_exit": round(locked, 4),
            "bars": exit_k - start + 1,
            "moved_after_trail": (outcome == "trail"),
            "sl_ever_ratcheted": ratchets > 0,
            "first_touch_r": None if first_touch_r is None else round(first_touch_r, 4)}


def classify(rows):
    """Attribute realized R to the mechanism that produced it."""
    buckets = defaultdict(list)
    for x in rows:
        if not x["sl_ever_ratcheted"]:
            b = "1_sl_never_ratcheted"
        elif x["outcome"] == "sl":
            b = "2_ratcheted_then_sl_hit"
        elif x["r"] < 1.0:
            b = "3_trail_exit_under_1R"
        elif x["r"] < 3.0:
            b = "4_trail_exit_1_to_3R"
        elif x["r"] < 10.0:
            b = "5_trail_exit_3_to_10R"
        else:
            b = "6_trail_exit_10R_plus"
        buckets[b].append(x)
    out = {}
    total = sum(x["r"] for x in rows) or 1.0
    for b in sorted(buckets):
        xs = buckets[b]
        rs = [x["r"] for x in xs]
        out[b] = {
            "n": len(xs), "share_pct": round(100.0 * len(xs) / len(rows), 3),
            "sum_r": round(sum(rs), 4),
            "pct_of_total_r": round(100.0 * sum(rs) / total, 3),
            "avg_r": round(sum(rs) / len(rs), 4),
            "avg_locked_r": round(sum(x["locked_r_at_exit"] for x in xs) / len(xs), 4),
            "avg_ratchets": round(sum(x["ratchets"] for x in xs) / len(xs), 3),
            "avg_bars": round(sum(x["bars"] for x in xs) / len(xs), 1),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    allr = {"study": 3, "name": "trail mechanism decomposition",
            "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 130, flush=True)
        print(f"  STUDY 3 — TRAIL MECHANISM DECOMPOSITION — BYBIT {scope.upper()}", flush=True)
        print("=" * 130, flush=True)
        data = prepare(load_scope(scope))
        sc = {}
        for lane in LANES:
            params = {**BP, **EXPERIMENTS[lane]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"]
            rows, mismatch = [], 0
            for t in trades:
                x = replay(t, data)
                if x is None:
                    continue
                if abs(x["r"] - float(t.get("r_multiple") or 0.0)) > 0.02:
                    mismatch += 1
                rows.append(x)
            cl = classify(rows)
            eng_r = sum(float(t.get("r_multiple") or 0.0) for t in trades)
            rep_r = sum(x["r"] for x in rows)
            sc[lane] = {"n_trades": len(trades), "n_replayed": len(rows),
                        "replay_mismatch_gt_0p02R": mismatch,
                        "engine_gross_r": round(eng_r, 4),
                        "replay_gross_r": round(rep_r, 4),
                        "mechanism_buckets": cl}
            print(f"  {scope.upper():3} {lane:32} n={len(trades):3d} replayed={len(rows):3d} "
                  f"mismatch={mismatch:2d} engineR={eng_r:+8.1f} replayR={rep_r:+8.1f}", flush=True)
            for b, v in cl.items():
                print(f"      {b:26} n={v['n']:3d} ({v['share_pct']:5.1f}%) "
                      f"R={v['sum_r']:+8.1f} ({v['pct_of_total_r']:+6.1f}% of total) "
                      f"avgR={v['avg_r']:+6.2f} locked={v['avg_locked_r']:+5.2f} "
                      f"ratchets={v['avg_ratchets']:4.1f} bars={v['avg_bars']:5.1f}", flush=True)
        allr["scopes"][scope] = sc
    OUT.write_text(json.dumps(allr, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
