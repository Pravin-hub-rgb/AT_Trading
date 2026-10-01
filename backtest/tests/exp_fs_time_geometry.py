"""FS-TIME SWING GEOMETRY: the legal version of M2 (user's idea).

THE PROBLEM THIS SOLVES
=======================
M2 (`cur_mag_atr = |seg.end_px - seg.start_px| / atr15`) is the strongest
sizing flag in the repo and it is FORWARD-LOOKING: it reads the swing
segment's `end_px`, and `backend_check_wd_days.py:108` asserts
`fs_at_idx >= seg.end_idx` - the geometry is only final once the swing is
confirmed, which is after the B2/flip entry. No send-time replacement exists
(CAPITAL_STAGE_PLAN tested this: `mag_so_far` 0/6, `ramp_so_far` 0/6).

THE USER'S RESOLUTION
=====================
Don't try to know the swing at entry. WAIT for it. At the moment the swing
confirms (`fs_at_idx`), the same `end_px` that made M2 illegal at entry is
now legally known. So:

  entry  ->  swing confirms (FS)  ->  read the swing's true geometry
         ->  bucket it  ->  if the bucket is bad, EXIT HERE and gray onward

This is a LATE MANAGEMENT action, not an entry filter. Nothing in it needs
information that does not exist at the moment it is used.

FEASIBILITY (measured before designing anything else)
=====================================================
On is/champion: 500/500 trades have an FS, the FS ALWAYS lands after the
entry (median 9.2h, p25 5.5h, p75 11.2h), and **62.8% of trades are still
OPEN at FS time**. So there is a large, actionable population - and it is
actionable precisely because the information is available exactly then.

WHAT THIS RUN ANSWERS
=====================
The idea only pays if the FS-known swing geometry predicts what happens
AFTER the FS. If the remaining P&L from FS to exit is flat across swing-
magnitude buckets, there is nothing to act on and the idea is dead here.

So this run is DESCRIPTIVE and it asks one question:
  does `swing_mag_atr` measured at FS (legally known) separate the REMAINING
  R (entry -> FS already banked; FS -> exit is what is still at risk)?

Reported per cell: remaining R by tercile bucket of FS-time swing magnitude,
plus the full swing_mag_atr -> final R relationship for contrast.

If remaining R is flat, the honest answer is that FS-time geometry adds
nothing and the idea needs a different trigger.
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

OUT = ROOT / "backtest/tests/_fs_time_geometry.json"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))


def atr_at_15m(c15, i, lb=15):
    if i < lb:
        return None
    trs = []
    for k in range(i - lb + 1, i + 1):
        c = c15[k]
        pc = c15[k - 1]["close"]
        trs.append(max(float(c["high"]) - float(c["low"]),
                       abs(float(c["high"]) - pc),
                       abs(float(c["low"]) - pc)))
    return sum(trs) / lb


def build_rows(scope, name, key):
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from experiment_registry import BP, EXPERIMENTS
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
        seg = s.get("seg", {})
        if not seg or "end_px" not in seg or "start_px" not in seg:
            continue
        # Swing magnitude AS KNOWN AT FS - identical formula to M2, but read
        # at the moment it is legal rather than back at the entry.
        atr = atr_at_15m(c15, fi)
        if not atr or atr <= 0:
            continue
        mag = abs(float(seg["end_px"]) - float(seg["start_px"])) / atr
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        d = 1 if t["dir"] == "long" else -1
        px_fs = float(c15[fi]["close"])
        r_fs = d * (px_fs - entry) / risk
        r_final = float(t["r_multiple"])
        rows.append({
            "mag": mag, "r_fs": r_fs, "r_final": r_final,
            "remaining": r_final - r_fs,
            "open_at_fs": e_ts < fs_ts < x_ts,
            "bars_to_fs": (fs_ts - e_ts) // 1800,
        })
    return rows

def trimmed(rs):
    s = sorted(rs)
    k = int(len(s) * 0.10)
    t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
    return sum(t) / len(t)


def stat(rs):
    if not rs:
        return None
    return {"n": len(rs), "net": round(sum(rs), 1),
            "mean": round(statistics.mean(rs), 3),
            "trimmed": round(trimmed(rs), 3),
            "median": round(statistics.median(rs), 3)}


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  FS-TIME SWING GEOMETRY - M2's information, read when it is legal",
          flush=True)
    print("=" * 100, flush=True)
    payload = {"stage": "fs_time_geometry", "cells": {}}
    for scope in ("is", "oos"):
        for name, key in LANES:
            rows = build_rows(scope, name, key)
            if not rows:
                print(f"  [{scope}/{name}] no rows", flush=True)
                continue
            openrows = [r for r in rows if r["open_at_fs"]]
            n = len(openrows)
            if n < 40:
                print(f"  [{scope}/{name}] only {n} open at FS - TOO THIN",
                      flush=True)
                payload["cells"][f"{scope}/{name}"] = {"insufficient": n}
                continue
            mags = sorted(r["mag"] for r in openrows)
            t1, t2 = mags[n // 3], mags[2 * n // 3]

            def bucket(m):
                return 0 if m <= t1 else (1 if m <= t2 else 2)

            print(f"\n  [{scope}/{name}] {len(rows)} trades, {n} OPEN at FS "
                  f"({100.0*n/len(rows):.1f}%)", flush=True)
            print(f"    swing_mag_atr terciles: low<={t1:.2f} "
                  f"mid<={t2:.2f} high>{t2:.2f}", flush=True)
            print(f"    {'bucket':<10} {'n':>4} {'R@FS':>7} {'REMAINING':>18}"
                  f"   {'finalR':>16}", flush=True)
            cell = {"n_all": len(rows), "n_open": n,
                    "terciles": [round(t1, 2), round(t2, 2)], "buckets": {}}
            for b, lbl in ((0, "low mag"), (1, "mid mag"), (2, "high mag")):
                g = [r for r in openrows if bucket(r["mag"]) == b]
                if not g:
                    continue
                rem = stat([r["remaining"] for r in g])
                rfs = stat([r["r_fs"] for r in g])
                fin = stat([r["r_final"] for r in g])
                cell["buckets"][lbl] = {"remaining": rem, "r_at_fs": rfs,
                                        "final": fin,
                                        "mean_mag": round(
                                            statistics.mean(r["mag"] for r in g), 2)}
                print(f"    {lbl:<10} {rem['n']:>4} {rfs['mean']:>+7.3f}  "
                      f"net{rem['net']:>+7.1f} trim{rem['trimmed']:>+6.3f}"
                      f"   net{fin['net']:>+7.1f} trim{fin['trimmed']:>+6.3f}",
                      flush=True)
            lows = [r for r in openrows if bucket(r["mag"]) == 0]
            highs = [r for r in openrows if bucket(r["mag"]) == 2]
            if lows and highs:
                diff = (statistics.mean(r["remaining"] for r in highs) -
                        statistics.mean(r["remaining"] for r in lows))
                cell["remaining_high_minus_low"] = round(diff, 3)
                print(f"    >>> remaining R: high-mag minus low-mag = "
                      f"{diff:+.3f}R per trade", flush=True)
                print(f"    >>> exiting ALL low-mag trades at FS would give up "
                      f"{-sum(r['remaining'] for r in lows):+.1f}R over "
                      f"{len(lows)} trades", flush=True)
            payload["cells"][f"{scope}/{name}"] = cell
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
