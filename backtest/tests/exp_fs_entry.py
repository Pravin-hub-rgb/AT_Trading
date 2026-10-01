"""ENTER AT FS INSTEAD OF B2/FLIP - the user's proposal, measured.

THE IDEA
========
Today the engine enters on the FIRST break mark (B2 or flip), which is early -
and that is exactly why M2 had to be forward-looking: at B2 the swing has not
ended, so `seg.end_px` is not knowable.

The user proposes dropping the early entry entirely: wait for the swing to
CONFIRM (FS), and enter THERE. At that moment the swing's final geometry is
known by definition, so M2 stops being look-ahead and becomes an ordinary
legal entry-time feature. The whole M2 problem dissolves by changing when
we enter rather than by trying to repair the feature.

This is the cleanest available resolution of the look-ahead, so it is worth
one honest measurement before anything else is tried.

THE TWO NUMBERS THAT DECIDE IT
==============================
1. IS THERE MOVE LEFT AFTER FS? If a trade entered at the FS close earns
   meaningful R from there to the eventual exit, the idea has legs. Measured
   as: R from the FS close to the original exit, in units of the NEW risk
   (|fs_close - sl|), because entering later means a different stop distance.
2. HOW MANY FS SIGNALS EXIST? If only the ~63% of current trades that survive
   to FS are available, this is a smaller book. If every confirmed swing in
   the data is a candidate, it could be a much larger one - the current
   B2/flip filter is a restriction, and FS is a different gate.

Both are reported. Neither is a recommendation.

HONEST LIMITS OF THIS RUN
========================
- The trade list is still the engine's B2/flip book, so this measures "if we
  had entered these same swings later", not a fresh FS-only signal engine.
  A true FS-entry engine could take swings that never produced a B2/flip
  entry, which would be a LARGER book - counted here but not simulated.
- Exits are the original ones. A genuinely late entry would trail differently.
- M2's bucket is legal here by construction - the swing is confirmed before
  entry - so bucket splits in this run are NOT look-ahead.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_fs_entry.json"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))


def atr_at(c15, i, lb=15):
    if i < lb:
        return None
    trs = []
    for k in range(i - lb + 1, i + 1):
        c, pc = c15[k], c15[k - 1]["close"]
        trs.append(max(float(c["high"]) - float(c["low"]),
                       abs(float(c["high"]) - pc),
                       abs(float(c["low"]) - pc)))
    return sum(trs) / lb

def build(scope, name, key):
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r
    data, _ = load_book(scope)
    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    by_i = {int(s["swing_index"]): s for s in data["sw15"]}
    sim = build_family_module()
    trades = sim(data["c1h"], data["sw10"], c15, data["sw15"],
                 fine_ltf=data["fine"],
                 **{**BP, **EXPERIMENTS[key]["params"]})["ltf_trades"]
    net_r(trades)
    n_sw = len(data["sw15"])
    n_fs = sum(1 for s in data["sw15"] if s.get("fs_at_idx") is not None)
    rows = []
    for t in trades:
        s = by_i.get(int(t.get("swing_no", -1)))
        rec = {"base_r": float(t["r_multiple"]), "dir": t["dir"]}
        if not s or s.get("fs_at_idx") is None:
            rows.append(rec)
            continue
        fi = int(s["fs_at_idx"])
        if not (0 <= fi < len(c15)):
            rows.append(rec)
            continue
        fs_ts = ts15[fi]
        if not (int(t["entry_ts"]) < fs_ts < int(t["exit_ts"])):
            rows.append(rec)          # not open at FS -> would be MISSED
            continue
        seg = s.get("seg", {})
        atr = atr_at(c15, fi)
        fs_px = float(c15[fi]["close"])
        sl = float(t["sl"])
        d = 1 if t["dir"] == "long" else -1
        new_risk = abs(fs_px - sl)
        r_fs_entry = (None if new_risk <= 0 else
                      d * (float(t["exit_price"]) - fs_px) / new_risk)
        rec["eligible"] = True
        rec["mag"] = (None if not atr else
                      abs(float(seg["end_px"]) - float(seg["start_px"])) / atr)
        rec["r_fs_entry"] = r_fs_entry
        rec["bars_to_exit"] = (int(t["exit_ts"]) - fs_ts) // 900
        rows.append(rec)
    return trades, rows, n_sw, n_fs


def summarise(rs):
    """Chronological drawdown. A previous pass sorted `rs` before computing
    the peak/drawdown walk, which silently destroyed the drawdown (every cell
    reported max_dd 1.0, i.e. just the largest single loss). Drawdown is only
    meaningful on the curve in TIME order, so no sorting here."""
    if not rs:
        return None
    seq = list(rs)                      # keep author order - do not sort
    k = max(1, len(seq) // 10)
    net = sum(seq)
    peak = dd = 0.0
    for x in seq:
        peak = max(peak, x)
        dd = max(dd, peak - x)
    return {"n": len(seq), "net": round(net, 1),
            "avg": round(statistics.mean(seq), 3),
            "trimmed": round(statistics.mean(
                sorted(seq)[k:len(seq) - k] or seq), 3),
            "median": round(statistics.median(seq), 3),
            "max_dd": round(dd, 1),
            "wr": round(100.0 * sum(1 for x in seq if x > 0) / len(seq), 1)}


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  ENTER AT FS (not B2/flip) - M2 becomes legal by construction",
          flush=True)
    print("=" * 100, flush=True)
    payload = {"stage": "fs_entry", "cells": {}}
    for scope in ("is", "oos"):
        for name, key in LANES:
            trades, rows, n_sw, n_fs = build(scope, name, key)
            elig = [r for r in rows if r.get("eligible")]
            base = [r["base_r"] for r in rows]
            fe = [r["r_fs_entry"] for r in elig if r["r_fs_entry"] is not None]
            print(f"\n  [{scope}/{name}] swings {n_sw}  with FS {n_fs}", flush=True)
            print(f"    BASE book (enter B2/flip) {len(base)}t: "
                  f"{summarise(base)}", flush=True)
            print(f"    MISSED if we wait for FS: {len(rows)-len(elig)}t "
                  f"({100.0*(len(rows)-len(elig))/len(rows):.1f}% of the book)",
                  flush=True)
            fsb = summarise(fe)
            print(f"    FS-ENTRY on survivors {len(fe)}t: {fsb}", flush=True)
            # M2 bucket split - LEGAL here, swing already confirmed
            cell = {"base": summarise(base), "fs_entry": fsb,
                    "n_swings": n_sw, "n_with_fs": n_fs,
                    "missed": len(rows) - len(elig), "buckets": {}}
            mags = sorted(r["mag"] for r in elig if r["mag"] is not None)
            if mags:
                t1 = mags[len(mags) // 3]
                t2 = mags[2 * len(mags) // 3]
                # Mutually exclusive bands. The previous form nested the
                # conditionals so the "mid" band was `mag <= t2`, which
                # re-included the small bucket (mid came out n210 = 105+105).
                def in_band(m, b):
                    if b == 0:
                        return m <= t1
                    if b == 1:
                        return t1 < m <= t2
                    return m > t2
                for b, lbl in ((0, "small swing"), (1, "mid swing"),
                               (2, "BIG swing (M2 bucket)")):
                    g = [r["r_fs_entry"] for r in elig
                         if r["mag"] is not None
                         and r["r_fs_entry"] is not None
                         and in_band(r["mag"], b)]
                    if g:
                        cell["buckets"][lbl] = summarise(g)
                        s = cell["buckets"][lbl]
                        print(f"      {lbl:<22} n{s['n']:>3} net{s['net']:>+7.1f} "
                              f"avg{s['avg']:>+6.3f} trim{s['trimmed']:>+6.3f} "
                              f"DD{s['max_dd']:>5.1f} WR{s['wr']:>5.1f}%",
                              flush=True)
            payload["cells"][f"{scope}/{name}"] = cell
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
