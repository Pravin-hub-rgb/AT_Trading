"""M2 order-time sizing bridge: can the backtest flag be computed at send time?

THE GAP THIS CLOSES
-------------------
Every M2 number in the repo (+152.7 IS / +29.1 OOS champion, 6/6 cells, and the
Binance transfer) is POST-PROCESS. The sizing exemption makes those numbers
valid as backtest numbers because scaling never changes which trades fire. But
the exemption says nothing about whether the flag can be READ AT ORDER TIME.

CAPITAL_STAGE_PLAN.md section 4a lists this as the one hard engineering blocker
before any live sizing, and it is correct: nothing in this repo has ever
computed cur_mag_atr from the state available at send time.

THE FEATURE
-----------
    cur_mag_atr = |swing.seg.end_px - swing.seg.start_px| / atr15(entry bar)

where swing is the 15m swing the trade belongs to and atr15 is ATR at the entry
bar. Sourced from exp_thesis_swing_geometry_deep.trade_rows, which is what M2
and every M2-derived arm were actually measured on.

THE BRIDGE QUESTION
-------------------
A live order is sent BEFORE its own 15m bar closes, and the swing's end_px is a
property of a segment that may not be final at send time. So the backtest flag
can read a value that a live process could not have known. This measures that
directly instead of assuming it.

PRE-REGISTERED (fixed before the run)
--------------------------------------
  BRIDGE IS CLEAN iff, replaying the shipped book through a send-time-only
  reader (no swing end_px, no future bar):
    1. flag agreement >= 95% of trades, AND
    2. no cell has agreement < 90%, AND
    3. dNet computed from send-time flags stays positive in all 6 cells
       (i.e. the edge survives the approximation, not just the arithmetic).

  A flag that needs the segment's END price to be live-computable is a REAL
  blocker, not a rounding detail, and must be reported as such.
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_m2_live_bridge.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
CELLS = tuple(f"{s}|{l}" for s in ("is", "oos") for l, _ in LANES)

M2_THRESH = 3.0
M2_SIZE = 1.5
AGREE_MIN = 95.0
AGREE_CELL_MIN = 90.0


def atr_at(c15, idx, n=14):
    """ATR proxy at a 15m bar index, DELEGATED to the audited atr_at().

    CORRECTED 2026-09-26. The original version of this file used a
    mean-true-range average and described it as "matching the engine's
    convention". It does not: exp_thesis_swing_geometry_deep.atr_at is
    max(high) - min(low) over the last 14 bars - a RANGE, not a true-range
    mean. The wrong denominator inflated every send-time magnitude, so the
    send-time flags in the first run of this harness (and the dNet figures
    beside them) were not the intended measurement. This run supersedes it.
    """
    from exp_thesis_swing_geometry_deep import atr_at as _audited
    if idx <= 0:
        return None
    return _audited(c15, idx, n)


def send_time_flag(trade, c15, ts15, sw15):
    """M2 flag using ONLY what a live process has at order-send time.

    The backtest feature divides the swing SEGMENT's end price by ATR. The
    segment end is not known at send time, so this substitutes the last
    CLOSED 15m close at or before the signal bar - the newest price the live
    loop could actually see when it places the order.

    Returns (flag, mag, mode) or (None, None, 'no_atr') if ATR is unavailable.
    """
    entry_idx = max(0, bisect.bisect_right(ts15, int(trade["entry_ts"])) - 1)
    a = atr_at(c15, entry_idx)
    if not a or a <= 0:
        return None, None, "no_atr"
    last_closed = float(c15[entry_idx]["close"])
    by_index = {int(s.get("swing_index", -1)): (j, s) for j, s in enumerate(sw15)}
    cur_j, cur = by_index.get(int(trade.get("swing_no", -1)), (-1, None))
    if cur is None:
        return None, None, "no_swing"
    seg = cur.get("seg", {})
    start_px = seg.get("start_px")
    if start_px is None:
        return None, None, "no_seg"
    # send-time proxy: distance from segment start to the last closed bar
    mag = abs(last_closed - float(start_px)) / a
    return mag >= M2_THRESH, mag, "proxy_close"


def backtest_flag(trade, c15, ts15, sw15):
    """M2 exactly as the backtest measured it.

    DELEGATES to trade_rows() rather than recomputing the feature here. An
    earlier version of this file reimplemented `cur_mag_atr` as
    |seg.end_px - seg.start_px| / atr_at() and produced 490 flags on 500
    champion trades - flatly contradicting the 128 that CHECKLIST 24.78
    records, because the atr_at() here is not the atr15 the feature actually
    uses. Reusing the audited function is the only way to get a reference
    reader that is correct by construction.

    Returns (flag, mag). mag may be None if trade_rows skipped the trade.
    """
    from exp_thesis_swing_geometry_deep import trade_rows
    rows = trade_rows([trade], {"c15": c15, "c1h": None, "sw15": sw15})
    if not rows:
        return None, None
    r = rows[0]
    mag = r.get("cur_mag_atr")
    if mag is None:
        return None, None
    return float(mag) >= M2_THRESH, float(mag)

def lagged_flag(trade, c15, ts15, sw15, lag=1):
    """A more conservative live proxy: the last CLOSED bar, one bar back.

    If the entry bar itself is not yet closed when the order fires, the live
    loop cannot use its close either. This measures how much of the agreement
    survives under that stricter assumption.
    """
    entry_idx = max(0, bisect.bisect_right(ts15, int(trade["entry_ts"])) - 1)
    a = atr_at(c15, entry_idx)
    if not a or a <= 0:
        return None, None
    px_idx = entry_idx - lag
    if px_idx < 0:
        return None, None
    last_closed = float(c15[px_idx]["close"])
    by_index = {int(s.get("swing_index", -1)): (j, s) for j, s in enumerate(sw15)}
    cur_j, cur = by_index.get(int(trade.get("swing_no", -1)), (-1, None))
    if cur is None:
        return None, None
    start_px = cur.get("seg", {}).get("start_px")
    if start_px is None:
        return None, None
    mag = abs(last_closed - float(start_px)) / a
    return mag >= M2_THRESH, mag


def score(trades, flags, yrs):
    sized = []
    for t, fl in zip(trades, flags):
        t2 = dict(t)
        if fl:
            t2["r_multiple"] = float(t["r_multiple"]) * M2_SIZE
        sized.append(t2)
    from run_experiment import net_r
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    base = equity_quality(trades, yrs)
    q = equity_quality(sized, yrs)
    d = arm_scores(q, base)
    return {
        "n": len(trades),
        "n_flagged": sum(1 for f in flags if f),
        "net": round(q["net"], 2),
        "dNet": round(q["net"] - base["net"], 2),
        "d_calmar": round(d["d_calmar"], 3),
        "curve_better": curve_better(d),
    }


def main():
    t0 = time.time()
    from experiment_registry import BP, EXPERIMENTS
    from test_experiments_craze import build_module
    from exp_boundary_state_autopsy import load_scope

    sim = build_module()
    payload = {
        "stage": "m2_live_bridge",
        "feature": "cur_mag_atr = |seg.end_px - seg.start_px| / atr15",
        "threshold": M2_THRESH,
        "size": M2_SIZE,
        "pre_registered": {
            "agree_min_pct": AGREE_MIN,
            "agree_cell_min_pct": AGREE_CELL_MIN,
            "rule": ("BRIDGE CLEAN iff send-time agreement >= 95% overall AND "
                     "no cell < 90% AND dNet>0 in all 6 cells"),
        },
        "readers": {
            "backtest": "seg.end_px (NOT live-computable; reference only)",
            "sendtime_close": "last closed 15m close at entry bar",
            "sendtime_lag1": "last closed 15m close one bar back",
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
            tr = out["ltf_trades"] if isinstance(out, dict) else out
            tr = sorted(tr, key=lambda t: int(t["entry_ts"]))

            # Reference flags come from the audited trade_rows() in ONE bulk
            # call (it needs c1h for the 1h chop series, so it cannot be
            # called with c1h=None). It may skip trades, so flags are aligned
            # back by entry_ts rather than by position.
            from exp_thesis_swing_geometry_deep import trade_rows as _tr
            ref_rows = _tr(tr, {"c15": c15, "c1h": data["c1h"], "sw15": sw15})
            ref = {}
            for r in ref_rows:
                ets = r.get("entry_ts")
                m = r.get("cur_mag_atr")
                if ets is not None and m is not None:
                    ref[int(ets)] = float(m) >= M2_THRESH

            fb, f_send, f_lag = [], [], []
            for t in tr:
                b = ref.get(int(t["entry_ts"]), False)
                s, _, _ = send_time_flag(t, c15, ts15, sw15)
                l, _ = lagged_flag(t, c15, ts15, sw15)
                fb.append(bool(b)); f_send.append(bool(s)); f_lag.append(bool(l))

            n = len(tr)
            agree = 100.0 * sum(1 for a, b in zip(fb, f_send) if a == b) / n
            yrs = YEARS[scope]
            cell = {
                "n": n,
                "n_backtest_flag": sum(fb),
                "n_sendtime_flag": sum(f_send),
                "n_lag1_flag": sum(f_lag),
                "agreement_pct": round(agree, 1),
                "backtest_arm": score(tr, fb, yrs),
                "sendtime_arm": score(tr, f_send, yrs),
                "lag1_arm": score(tr, f_lag, yrs),
            }
            payload["cells"][f"{scope}|{lane}"] = cell
            print(f"  {scope}|{lane:9s} n={n:4d} agree={agree:5.1f}%  "
                  f"bt_flag={cell['n_backtest_flag']:3d} "
                  f"send={cell['n_sendtime_flag']:3d} lag1={cell['n_lag1_flag']:3d}  "
                  f"dNet send={cell['sendtime_arm']['dNet']:+7.1f} "
                  f"lag1={cell['lag1_arm']['dNet']:+7.1f}", flush=True)
    cells = payload["cells"]
    agree_all = sum(c["agreement_pct"] * c["n"] for c in cells.values()) / \
        sum(c["n"] for c in cells.values())
    worst_cell = min(c["agreement_pct"] for c in cells.values())
    all_pos = all(c["sendtime_arm"]["dNet"] > 0 for c in cells.values())
    lag_all_pos = all(c["lag1_arm"]["dNet"] > 0 for c in cells.values())
    clean = (agree_all >= AGREE_MIN and worst_cell >= AGREE_CELL_MIN and all_pos)
    payload["result"] = {
        "agreement_overall_pct": round(agree_all, 1),
        "worst_cell_agreement_pct": worst_cell,
        "sendtime_dNet_positive_all_cells": all_pos,
        "lag1_dNet_positive_all_cells": lag_all_pos,
        "bridge_clean": clean,
        "verdict": (
            "BRIDGE CLEAN - the send-time reader reproduces the backtest flag "
            "and the edge survives it."
            if clean else
            "BRIDGE BLOCKED - the flag is NOT reproducible from send-time "
            "state at the pre-registered threshold. M2 cannot be deployed as a "
            "live lot size without changing the feature definition, which "
            "would be a NEW pre-registered experiment."
        ),
    }
    print("\n" + "=" * 84, flush=True)
    print("  M2 ORDER-TIME BRIDGE", flush=True)
    print("=" * 84, flush=True)
    print(f"  overall agreement : {agree_all:.1f}%  (rule >= {AGREE_MIN}%)", flush=True)
    print(f"  worst cell         : {worst_cell:.1f}%  (rule >= {AGREE_CELL_MIN}%)", flush=True)
    print(f"  send-time dNet > 0 : {all_pos}", flush=True)
    print(f"  lag-1    dNet > 0 : {lag_all_pos}", flush=True)
    print(f"  VERDICT: {payload['result']['verdict'][:70]}", flush=True)
    print("=" * 84, flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
