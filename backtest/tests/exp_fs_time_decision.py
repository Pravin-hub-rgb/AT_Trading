"""FS-TIME DECISION: exit if bad, ADD if good - tested both ways, with a null.

THE USER'S DESIGN (both directions, which my previous run only half-tested)
========================================================================
At FS (swing confirmation) the swing's true geometry is legally known. So:
  swing is BAD  -> exit right away
  swing is GOOD -> ADD 0.5 position here
My previous run measured only aggregate remaining-R per tercile. That is
exactly the aggregation error M2 itself made: an aggregate can be positive
while individual trades are not, so it cannot decide trade-by-trade. This run
decides PER TRADE, and prices both directions.

THE NULL (this is the whole point)
==================================
Any FS-time feature is tested against a PERMUTATION null: shuffle the
feature across trades, recompute the strategy value, repeat. A feature that
picks winners in hindsight will beat the null; a feature that is pure noise
will not. This is the test M2 never got, and the reason the earlier
"remaining R is flat" reading needs re-checking at the per-trade level.

WHAT IS AVAILABLE AT FS (legally - closed bars only)
===================================================
  mag_atr   |seg.end_px - seg.start_px| / atr15    <- M2's formula, read late
  r_fs      R already banked at FS
  bars_fs   15m bars from entry to FS
  dir_ok    swing direction == trade direction
  pos_in_seg where the entry sits inside the swing segment (0=start,1=end)

EACH DIRECTION IS PRICED, NOT ASSUMED
=====================================
  EXIT  value = +remaining R, realised by closing at FS. Only positive if the
        trade, on average, loses money from FS onward.
  ADD   value = +0.5 x remaining R, on the trades the feature selects.
        Positive if the SELECTED trades have positive remaining R. Note the
        pyramid family is CLOSED in this repo (V4 -111.3/-87.3, no arm passed)
        - but that was triggered on R milestones, NOT on swing confirmation,
        so this is a genuinely different trigger and is tested fresh.

Also reported: how often each direction fires, and net value in R, so an
arm that fires on 3 trades is visibly different from one that fires on 100.

DESCRIPTIVE ONLY - proposes no gate, changes no engine, adopts nothing.
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

OUT = ROOT / "backtest/tests/_fs_time_decision.json"
N_PERM = 200
SEED = 20260928
ADD_SIZE = 0.5
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
FEATURES = ("mag_atr", "r_fs", "bars_fs", "pos_in_seg")

def build_rows(scope, name, key):
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from experiment_registry import BP, EXPERIMENTS
    from exp_fs_time_geometry import atr_at_15m
    data, _ = load_book(scope)
    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    by_i = {int(s["swing_index"]): s for s in data["sw15"]}
    sim = build_family_module()
    trades = sim(data["c1h"], data["sw10"], c15, data["sw15"],
                 fine_ltf=data["fine"],
                 **{**BP, **EXPERIMENTS[key]["params"]})["ltf_trades"]
    rows = []
    for t in trades:
        s = by_i.get(int(t.get("swing_no", -1)))
        if not s or s.get("fs_at_idx") is None:
            continue
        fi = int(s["fs_at_idx"])
        if not (0 <= fi < len(c15)):
            continue
        fs_ts = ts15[fi]
        e_ts, x_ts = int(t["entry_ts"]), int(t["exit_ts"])
        if not (e_ts < fs_ts < x_ts):        # must be open AT fs to act
            continue
        seg = s.get("seg", {})
        if not seg or "end_px" not in seg or "start_px" not in seg:
            continue
        atr = atr_at_15m(c15, fi)
        if not atr or atr <= 0:
            continue
        entry, sl = float(t["entry_price"]), float(t["sl"])
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        d = 1 if t["dir"] == "long" else -1
        sd = s.get("dir")
        swing_sign = 1 if sd in ("up", "long", 1) else -1
        r_fs = d * (float(c15[fi]["close"]) - entry) / risk
        r_final = float(t["r_multiple"])
        si, ei = int(seg.get("start_idx", fi)), int(seg.get("end_idx", fi))
        # entry bar index in the 15m series
        import bisect as _b
        e_idx = _b.bisect_right(ts15, e_ts) - 1
        pos = (e_idx - si) / (ei - si) if ei > si else 0.5
        rows.append({
            "mag_atr": abs(float(seg["end_px"]) - float(seg["start_px"])) / atr,
            "r_fs": r_fs, "remaining": r_final - r_fs,
            "bars_fs": (fs_ts - e_ts) // 900,
            "dir_ok": (1 if d == swing_sign else 0),
            "pos_in_seg": min(1.0, max(0.0, pos)),
        })
    return rows


def tercile_edges(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 3], s[2 * n // 3]


def exit_value(rows, sel):
    """Closing at FS captures +remaining for the selected trades. Positive
    only if they lose money from FS onward."""
    return sum(r["remaining"] for r in sel)


def add_value(rows, sel):
    """Adding ADD_SIZE at FS earns ADD_SIZE x remaining on selected trades."""
    return ADD_SIZE * sum(r["remaining"] for r in sel)


def perm_null(rows, feat, lo, hi, pick_low_as_exit, add_frac):
    """Permutation null: shuffle the FEATURE, keep the book. Recompute both
    directions. Returns the distribution of each value."""
    import random as _r
    rng = _r.Random(SEED)
    evals, avals = [], []
    for _ in range(N_PERM):
        fv = [r[feat] for r in rows]
        rng.shuffle(fv)
        for i, r in enumerate(rows):
            r["_f"] = fv[i]
        sel = [r for r in rows if r["_f"] <= lo]
        evals.append(exit_value(rows, sel))
        # add picks the best `add_frac` by feature
        k = max(1, int(len(rows) * add_frac))
        top = sorted(rows, key=lambda r: -r["_f"])[:k]
        avals.append(add_value(rows, top))
    return evals, avals

def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  FS-TIME DECISION - exit if bad, ADD if good (per-trade + null)",
          flush=True)
    print("=" * 100, flush=True)
    payload = {"stage": "fs_time_decision", "n_perm": N_PERM, "cells": {}}
    for scope in ("is", "oos"):
        for name, key in LANES:
            rows = build_rows(scope, name, key)
            n = len(rows)
            if n < 60:
                print(f"  [{scope}/{name}] only {n} open at FS - TOO THIN",
                      flush=True)
                payload["cells"][f"{scope}/{name}"] = {"insufficient": n}
                continue
            base_remaining = sum(r["remaining"] for r in rows)
            print(f"\n  [{scope}/{name}] {n} trades open at FS   "
                  f"total remaining {base_remaining:+.1f}R", flush=True)
            cell = {"n_open": n, "total_remaining": round(base_remaining, 1),
                    "features": {}}
            for feat in FEATURES:
                vals = [r[feat] for r in rows]
                lo, hi = tercile_edges(vals)
                # EXIT direction: exit the LOW third of the feature
                sel_exit = [r for r in rows if r[feat] <= lo]
                ev_real = exit_value(rows, sel_exit)
                # ADD direction: add 0.5 to the TOP third
                k = max(1, n // 3)
                sel_add = sorted(rows, key=lambda r: -r[feat])[:k]
                av_real = add_value(rows, sel_add)
                ev_null, av_null = perm_null(rows, feat, lo, hi, True, k / n)
                # EXIT direction: exiting GIVES UP the remaining R. So a good
                # exit is a LOW (ideally negative) exit_value. Beating the
                # null here means being in the BOTTOM tail of the null
                # distribution, not the top.
                # ADD direction: adding EARNS remaining. So a good add is a
                # HIGH add_value - the TOP tail of the null.
                ev_p = sum(1 for v in ev_null if v <= ev_real) / len(ev_null)
                av_p = sum(1 for v in av_null if v <= av_real) / len(av_null)
                cell["features"][feat] = {
                    "n_exit": len(sel_exit), "n_add": len(sel_add),
                    "exit_giveup_R": round(ev_real, 1),
                    "exit_pctile": round(100 * ev_p, 1),
                    "exit_GOOD": bool(ev_real < 0),
                    "add_value_R": round(av_real, 1),
                    "add_pctile": round(100 * av_p, 1),
                    "add_GOOD": bool(av_p > 0.95 and av_real > 0),
                    "exit_mean_null": round(statistics.mean(ev_null), 1),
                    "add_mean_null": round(statistics.mean(av_null), 1)}
                # A feature only counts if the ACTION it implies is positive
                # in R. Positive giveup = exit is bad. Positive add = add pays.
                flag_e = ("EXIT PAYS" if ev_real < 0 and ev_p < 0.05
                          else "null")
                flag_a = ("ADD PAYS" if av_p > 0.95 and av_real > 0
                          else "null")
                print(f"    {feat:<12} EXIT low-third n{len(sel_exit):>3}: "
                      f"gives up {ev_real:+7.1f}R (null mean "
                      f"{statistics.mean(ev_null):+6.1f}, "
                      f"{ev_p*100:>5.1f}%) {flag_e}", flush=True)
                print(f"    {'':<12} ADD  top-third n{len(sel_add):>3}: "
                      f"earns    {av_real:+7.1f}R (null mean "
                      f"{statistics.mean(av_null):+6.1f}, "
                      f"{av_p*100:>5.1f}%) {flag_a}", flush=True)
            payload["cells"][f"{scope}/{name}"] = cell
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

