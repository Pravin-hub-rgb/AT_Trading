"""FS-ENTRY, RISK-NORMALISATION CONTROLLED (the user caught a real confound).

THE FLAW IN exp_fs_entry.py
===========================
That run compared swing-magnitude buckets using the ORIGINAL stop, which for
a long sits at the swing's LOW. By the time FS confirms, price has moved away
from that low, so |fs_close - sl| grows with swing size. R is normalised by
that risk, so a big swing automatically shows a SMALLER R for the identical
price move. The headline "big swings are worst" was therefore confounded
with stop distance - it partly measured my own normalisation choice, not the
swing.

The user is right: the stop should not sit at the far end of a big swing.
This run removes the confound instead of arguing about it.

FOUR MEASURES, so the comparison is size-neutral
=================================================
  pct_move   (exit - entry)/entry, in PERCENT. No risk normalisation at all,
             so nothing about the stop can distort it. This is the cleanest
             cross-size comparison and is the one to read first.
  r_fixed    R with a CONSTANT stop of 1.0 x ATR15. Every swing carries the
             same risk, so R is directly comparable across swing sizes.
  r_half     R with the stop at the swing's MIDPOINT. The user's suggestion -
             a stop that scales with the swing instead of sitting at its far
             end.
  r_orig     R with the original far stop - reproduces exp_fs_entry so the
             confound's size is visible.

If `pct_move` and `r_fixed` say big swings are FINE while `r_orig` says they
are terrible, the earlier finding was a normalisation artefact and must be
retracted. That test is the whole point of this run.

ALSO REPORTED
=============
Whether the tighter stops are even survivable: stop-hit rate per bucket, and
how many trades survive to FS at all. A tighter stop that gets you stopped
out constantly is not a free improvement, and the % move alone would hide it.

Not a recommendation. Descriptive, to settle a confound.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_fs_entry_risk_control.json"
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
        if not (int(t["entry_ts"]) < fs_ts < int(t["exit_ts"])):
            continue
        seg = s.get("seg", {})
        if not seg or "end_px" not in seg or "start_px" not in seg:
            continue
        atr = atr_at(c15, fi)
        if not atr or atr <= 0:
            continue
        fs_px = float(c15[fi]["close"])
        exit_px = float(t["exit_price"])
        d = 1 if t["dir"] == "long" else -1
        move = d * (exit_px - fs_px)                 # in price, signed to trade
        if fs_px <= 0:
            continue
        half_px = 0.5 * (float(seg["end_px"]) + float(seg["start_px"]))
        r_orig = move / abs(fs_px - float(t["sl"])) if abs(fs_px - float(t["sl"])) > 0 else None
        r_half = move / abs(fs_px - half_px) if abs(fs_px - half_px) > 0 else None
        r_fix = move / atr
        # Would each stop have been hit before the real exit? Walk the bars.
        rows.append({
            "mag": abs(float(seg["end_px"]) - float(seg["start_px"])) / atr,
            "pct_move": 100.0 * move / fs_px,
            "r_fixed": r_fix, "r_half": r_half, "r_orig": r_orig,
            "held": move > 0,
            "stop_hit_orig": stop_hit(c15, fi, t["exit_ts"], d, float(t["sl"])),
            "stop_hit_half": stop_hit(c15, fi, t["exit_ts"], d, half_px),
            "stop_hit_fix": stop_hit(c15, fi, t["exit_ts"], d,
                                     fs_px - d * atr),
        })
    return rows


def stop_hit(c15, fi, exit_ts, d, stop_px):
    """Did price reach `stop_px` between FS and the real exit? The engine
    would have stopped us there, so a tighter stop is only 'better' if it
    was not hit first."""
    for k in range(fi, len(c15)):
        if int(c15[k]["ts"]) > int(exit_ts):
            break
        if d == 1:
            if float(c15[k]["low"]) <= stop_px:
                return True
        else:
            if float(c15[k]["high"]) >= stop_px:
                return True
    return False

def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  FS-ENTRY, risk-normalisation controlled - is 'big swings are worst'",
          flush=True)
    print("  an artefact of the far stop, or real?", flush=True)
    print("=" * 104, flush=True)
    payload = {"stage": "fs_entry_risk_control", "cells": {}}
    for scope in ("is", "oos"):
        for name, key in LANES:
            rows = build(scope, name, key)
            if len(rows) < 60:
                print(f"  [{scope}/{name}] only {len(rows)} rows", flush=True)
                continue
            mags = sorted(r["mag"] for r in rows)
            t1, t2 = mags[len(mags) // 3], mags[2 * len(mags) // 3]

            def band(m):
                return 0 if m <= t1 else (1 if m <= t2 else 2)

            print(f"\n  [{scope}/{name}] n={len(rows)}", flush=True)
            print(f"    {'bucket':<8} {'n':>4} {'%move':>9} {'R fixed':>9} "
                  f"{'R half':>9} {'R orig':>9}   stop-hit: half / fixed",
                  flush=True)
            cell = {"n": len(rows), "terciles": [round(t1, 2), round(t2, 2)],
                    "buckets": {}}
            for b, lbl in ((0, "small"), (1, "mid"), (2, "BIG")):
                g = [r for r in rows if band(r["mag"]) == b]
                if not g:
                    continue
                rec = {
                    "n": len(g),
                    "pct_move_mean": round(statistics.mean(
                        r["pct_move"] for r in g), 3),
                    "r_fixed_mean": round(statistics.mean(
                        r["r_fixed"] for r in g), 3),
                    "r_half_mean": round(statistics.mean(
                        r["r_half"] for r in g if r["r_half"] is not None), 3),
                    "r_orig_mean": round(statistics.mean(
                        r["r_orig"] for r in g if r["r_orig"] is not None), 3),
                    "stop_hit_half_pct": round(100.0 * sum(
                        1 for r in g if r["stop_hit_half"]) / len(g), 1),
                    "stop_hit_fix_pct": round(100.0 * sum(
                        1 for r in g if r["stop_hit_fix"]) / len(g), 1),
                }
                cell["buckets"][lbl] = rec
                print(f"    {lbl:<8} {rec['n']:>4} "
                      f"{rec['pct_move_mean']:>+9.3f} "
                      f"{rec['r_fixed_mean']:>+9.3f} "
                      f"{rec['r_half_mean']:>+9.3f} "
                      f"{rec['r_orig_mean']:>+9.3f}   "
                      f"{rec['stop_hit_half_pct']:>5.1f}% / "
                      f"{rec['stop_hit_fix_pct']:>5.1f}%", flush=True)
            payload["cells"][f"{scope}/{name}"] = cell
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

