"""Redefine M2 so it is computable at order-send time, then re-validate it.

WHY
---
The order-time bridge test (exp_m2_live_bridge.py) found M2 is NOT deployable
as measured: cur_mag_atr uses seg.end_px, and a swing's FS/SUS confirmation
happens at or after that end bar (backend_check_wd_days.py:108 literally
asserts fs_at_idx >= seg.end_idx). A live process cannot know end_px at
send time, so the backtest flag and the live flag agreed on only 46.5% of
trades.

That test also showed something useful: both send-time proxies kept dNet
positive in 6/6 cells. So the neighbourhood carries signal - it just is not M2.

THIS EXPERIMENT
---------------
Build send-time-computable alternatives that use only the swing's start price
and prices observed at or before the entry bar, then re-run the full 6-cell
rule on each. Any that clears is a genuine replacement for M2.

CANDIDATES (all use only known-at-send-time data)
-------------------------------------------------
  mag_so_far = |last_closed - seg.start_px| / atr15(entry bar)
      The segment's magnitude measured up to NOW, not to its eventual end.
      Threshold-free variant of M2's intent: "how big has this swing already
      travelled".

  ramp_so_far = clamp(1 + 0.25*(mag_so_far - 2), 1, 2)
      The ramp_mag shape applied to the live-computable read, so the queue's
      continuous-sizing idea is tested in a deployable form.

  M2_oracle  = the original seg.end_px flag, for reference only
      Carried so every cell reports the backtest number beside the live one.
      NOT deployable; present to quantify the gap, not to promote.

PRE-REGISTERED (fixed before the run)
--------------------------------------
  A candidate is a REPLACEMENT iff in ALL 6 cells:
    dNet > 0 AND curve_better AND dDD not worse than +5% of base maxDD,
    AND it flags at least 5% and at most 40% of the book (a flag that covers
    ~everything is leverage, not selection - this is the M1 trap from 24.58).

  The send-time feature must also be reproducible from the same inputs a live
  order would have, which is checked by construction: it reads nothing past
  the entry bar.
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_m2_sendtime_feature.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
M2_THRESH = 3.0
M2_SIZE = 1.5
RAMP_LO, RAMP_HI = 1.0, 2.0
RAMP_SLOPE = 0.25
RAMP_PIVOT = 2.0
DD_TOL_PCT = 5.0
FLAG_MIN_PCT, FLAG_MAX_PCT = 5.0, 40.0


def atr15_at(c15, idx, n=14):
    """ATR proxy at a 15m index, DELEGATED to the audited atr_at().

    NOTE this is NOT Wilder ATR. exp_thesis_swing_geometry_deep.atr_at is
    `max(high) - min(low)` over the last 14 bars - a range, not a true-range
    average. A local reimplementation using mean-true-range produced an oracle
    flag rate of 98% instead of the correct ~25.6%, which silently invalidated
    the whole comparison. Reuse the audited function instead of re-deriving it.
    """
    from exp_thesis_swing_geometry_deep import atr_at
    if idx <= 0:
        return None
    return atr_at(c15, idx, n)


def swing_of(trade, sw15):
    by_index = {int(s.get("swing_index", -1)): s for s in sw15}
    return by_index.get(int(trade.get("swing_no", -1)))


def mag_so_far(trade, c15, ts15, sw15):
    """|last closed close - seg.start_px| / atr15. Send-time computable.

    Reads only bars at or before the entry bar and the swing's start price,
    both of which exist before an order is sent. Deliberately does NOT touch
    seg.end_px.
    """
    s = swing_of(trade, sw15)
    if s is None:
        return None
    start_px = s.get("seg", {}).get("start_px")
    if start_px is None:
        return None
    idx = max(0, bisect.bisect_right(ts15, int(trade["entry_ts"])) - 1)
    a = atr15_at(c15, idx)
    if not a or a <= 0:
        return None
    return abs(float(c15[idx]["close"]) - float(start_px)) / a

def oracle_mag(trade, c15, ts15, sw15):
    """Original M2 magnitude (uses seg.end_px). Reference only."""
    s = swing_of(trade, sw15)
    if s is None:
        return None
    seg = s.get("seg", {})
    idx = max(0, bisect.bisect_right(ts15, int(trade["entry_ts"])) - 1)
    a = atr15_at(c15, idx)
    if not a or a <= 0:
        return None
    return abs(float(seg.get("end_px", 0.0)) - float(seg.get("start_px", 0.0))) / a


def apply_sizes(trades, sizes, yrs):
    from run_experiment import net_r
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    sized = []
    for t, m in zip(trades, sizes):
        t2 = dict(t)
        t2["r_multiple"] = float(t["r_multiple"]) * (m if m else 1.0)
        sized.append(t2)
    base = equity_quality(trades, yrs)
    q = equity_quality(sized, yrs)
    d = arm_scores(q, base)
    dd_pct = (100.0 * d["d_max_dd"] / base["max_dd"]) if base["max_dd"] else 0.0
    eff = sum(m for m in sizes if m) / max(1, len(sizes))
    flagged_pct = 100.0 * sum(1 for m in sizes if m) / len(sizes)
    return {
        "net": round(q["net"], 2),
        "dNet": round(q["net"] - base["net"], 2),
        "d_max_dd": round(d["d_max_dd"], 2),
        "d_dd_pct": round(dd_pct, 1),
        "d_calmar": round(d["d_calmar"], 3),
        "d_pf": round(d.get("d_pf", 0.0), 3),
        "curve_better": curve_better(d),
        "flagged_pct": round(flagged_pct, 1),
        "avg_size_mult": round(eff, 3),
        "pass": bool((q["net"] - base["net"]) > 0 and curve_better(d)
                     and dd_pct <= DD_TOL_PCT
                     and FLAG_MIN_PCT <= flagged_pct <= FLAG_MAX_PCT),
    }


def main():
    t0 = time.time()
    from experiment_registry import BP, EXPERIMENTS
    from test_experiments_craze import build_module
    from exp_boundary_state_autopsy import load_scope
    from exp_thesis_swing_geometry_deep import trade_rows

    sim = build_module()
    payload = {
        "stage": "m2_sendtime_feature",
        "goal": "redefine M2 so it is order-send-time computable, then re-validate",
        "sendtime_computable": ["mag_so_far", "ramp_so_far"],
        "reference_only": ["M2_oracle (seg.end_px)"],
        "pre_registered": {
            "pass_rule": (f"dNet>0 AND curve_better AND dDD<={DD_TOL_PCT}% AND "
                          f"flagged {FLAG_MIN_PCT}-{FLAG_MAX_PCT}% in ALL 6 cells"),
        },
        "years": YEARS,
        "cells": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_scope(scope)
        c15, sw15 = data["c15"], data["sw15"]
        ts15 = [int(c["ts"]) for c in c15]
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            tr = sorted(out["ltf_trades"] if isinstance(out, dict) else out,
                        key=lambda t: int(t["entry_ts"]))
            yrs = YEARS[scope]

            mags, oracles = [], []
            for t in tr:
                m = mag_so_far(t, c15, ts15, sw15)
                mags.append(m)
                oracles.append(oracle_mag(t, c15, ts15, sw15))

            s_m2 = [M2_SIZE if (o is not None and o >= M2_THRESH) else None
                    for o in oracles]
            s_bin = [M2_SIZE if (m is not None and m >= M2_THRESH) else None
                     for m in mags]
            s_ramp = [min(RAMP_HI, max(RAMP_LO, 1 + RAMP_SLOPE * (m - RAMP_PIVOT)))
                      if m is not None else None for m in mags]

            cell = {
                "n": len(tr),
                "M2_oracle": apply_sizes(tr, s_m2, yrs),
                "mag_so_far_bin": apply_sizes(tr, s_bin, yrs),
                "ramp_so_far": apply_sizes(tr, s_ramp, yrs),
            }
            payload["cells"][f"{scope}|{lane}"] = cell
            o, b, r = cell["M2_oracle"], cell["mag_so_far_bin"], cell["ramp_so_far"]
            print(f"  {scope}|{lane:9s} n={len(tr):4d}  "
                  f"oracle dNet {o['dNet']:+7.1f} ({o['flagged_pct']:4.1f}%)  "
                  f"bin dNet {b['dNet']:+7.1f} ({b['flagged_pct']:4.1f}%)  "
                  f"ramp dNet {r['dNet']:+7.1f} ({r['flagged_pct']:4.1f}%)",
                  flush=True)
    cells = payload["cells"]
    arms = ("mag_so_far_bin", "ramp_so_far")
    rollup = {}
    for arm in arms:
        ps = [c[arm]["pass"] for c in cells.values()]
        dns = [c[arm]["dNet"] for c in cells.values()]
        rollup[arm] = {
            "cells_passed": sum(ps), "total": len(ps),
            "min_dNet": round(min(dns), 2),
            "all_pass": all(ps),
            "sendtime_computable": True,
        }
    # oracle is reported but can never be promoted
    rollup["M2_oracle"] = {
        "cells_passed": sum(c["M2_oracle"]["pass"] for c in cells.values()),
        "total": len(cells),
        "sendtime_computable": False,
        "note": "reference only - uses seg.end_px, not live-knowable",
    }
    winners = [a for a in arms if rollup[a]["all_pass"]]
    payload["rollup"] = rollup
    payload["result"] = {
        "replacements": winners,
        "verdict": (
            f"REPLACEMENT FOUND: {winners}" if winners else
            "NO send-time replacement clears 6/6. The M2 neighbourhood has no "
            "deployable form among these candidates - a new feature would be "
            "needed, not a reparameterisation."
        ),
    }
    print("\n" + "=" * 88, flush=True)
    print("  M2 SEND-TIME REDEFINITION", flush=True)
    print("=" * 88, flush=True)
    for a in ("M2_oracle",) + arms:
        r = rollup[a]
        tag = "REFERENCE" if not r["sendtime_computable"] else (
            "REPLACEMENT" if r["all_pass"] else "fails")
        print(f"   {a:18s} {r['cells_passed']}/{r['total']}  {tag}", flush=True)
    print(f"   REPLACEMENTS: {winners if winners else 'NONE'}", flush=True)
    print("=" * 88, flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
