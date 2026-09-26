"""H1: the 4/4-negative cohorts as SIZING targets, not removals.

WHY
---
Stage B found four cohorts that were net-negative in all four cells. Testing
them as removals failed 0/4, and the cascade decomposition showed why: removing
a trade freed busy_until slots and admitted worse entries, costing 3-5x more
than the removed losers returned. The cohorts really were losing - the
measurement method was wrong, not the finding.

REMOVAL -> SIZING
-----------------
Instead of deleting a flagged trade, trade it at a reduced lot. This is
cascade-free BY CONSTRUCTION: sizing changes R on a trade, never which trades
are taken, so the trade list is identical and no gate state moves. That is the
exemption recorded in AGENT_COORDINATION.md, and it is verified against the
engine source (no equity / size / notional / qty state anywhere in
v18_streak_halt.py, and the loss streak counts losses not R at line 714).

So the same cohorts get a second, fair test. The bleed becomes a partial loss
instead of a full one, with zero state disruption.

ARMS (pre-registered, fixed before the run)
-------------------------------------------
  x0.50   halve the flagged cohort
  x0.75   cut it by a quarter
  x1.00   baseline (reported so every arm has its own control)

PRE-REGISTERED PASS RULE (fixed before the run)
----------------------------------------------
  An arm PASSES iff, in ALL 4 cells:
    dNet > 0                      (strictly positive in both eras, both lanes)
    curve_better is True          (risk-adjusted, not just net R)
    dDD is not worse than +5%      (no meaningful drawdown blow-up)

  And an arm is only a CANDIDATE if it passes 4/4 cells. Anything less is
  reported as descriptive and NOT promoted.

  This is deliberately a modest target: the cohorts are ~12-15% of the book,
  so the ceiling on any sizing lift is small. Do not chase a big number, and do
  not promote an arm that wins on net but loses on curve.

CAUSALITY
---------
Features are the Stage B closed-only ones (`enrich_sequential` + `compute_new`,
the versions fixed for the lookahead leak). A trade counts a prior trade only
when `exit_ts <= candidate entry_ts`. No re-derivation here - reuse, so this
harness cannot drift from the audited definitions.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_bleed_sizing_down.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
CELLS = ("is|champion", "is|utcsat", "oos|champion", "oos|utcsat")
SIZES = (1.0, 0.75, 0.5)
DD_TOLERANCE_PCT = 5.0

# The four Stage B qualifiers, exactly as pre-registered there.
COHORTS = ("chain_r_so_far", "chain_wl_streak", "wick_atr12@short", "flips96@short")

# Exact bucket edges, read from _regime_structure_is.json (Z1 IS-derived).
# Not retyped approximations - see the note in bucket_hit.
WICK_Q1 = 6.026
FLIPS_LO, FLIPS_HI = 4.0, 6.0


def bucket_hit(trade, feat, name):
    """Does this trade fall in the named Stage B cohort? Same boundaries the
    audit recorded. Kept in one place so every arm sees one definition.

    Takes BOTH the trade and its feature dict, because they carry different
    things and getting this wrong is silent:

      * `dir` ("long"/"short") lives on the TRADE only. `compute_new` derives a
        local sign but never stores it on the feature dict, so reading
        `feat["dir"]` yields None and the dir-masked cohorts match nothing.
      * `wick_atr12` / `flips96` live on the Z1 plane, not the Stage-B
        `compute_new` plane. The Stage B harness attaches them as
        `feat["_z1"]` via `z1_compute`, so read them from there.

    The exact bucket edges are the IS-derived ones in
    _regime_structure_is.json: wick_atr12 Q1 = <=6.026 (labelled "<=6.03"
    after rounding) and flips96 Q3 = 4.0..6.0. Hard-coding "4..5" flagged
    zero trades; the non-zero guard in main() is what turns that class of
    mistake into a loud failure instead of a null arm that reads as "no
    effect".
    """
    z = feat.get("_z1") or {}
    if name == "chain_r_so_far":
        v = feat.get("chain_r_so_far")
        return v is not None and v < 0
    if name == "chain_wl_streak":
        return feat.get("chain_wl_streak") == -1
    if name == "wick_atr12@short":
        if trade.get("dir") != "short":
            return False
        v = z.get("wick_atr12", feat.get("wick_atr12"))
        return v is not None and v <= WICK_Q1
    if name == "flips96@short":
        if trade.get("dir") != "short":
            return False
        v = z.get("flips96", feat.get("flips96"))
        return v is not None and FLIPS_LO <= v < FLIPS_HI
    raise SystemExit(f"unknown cohort {name}")


def size_trades(trades, feats, cohort, mult):
    """Return a copy of `trades` with R scaled on the flagged cohort.

    Sizing only - no trade is added or removed, so the ledger keys are
    identical to the baseline by construction. That is what makes this
    cascade-free.
    """
    out = []
    for t, f in zip(trades, feats):
        t2 = dict(t)
        if f.get("ok") and bucket_hit(t, f, cohort):
            t2["r_multiple"] = float(t["r_multiple"]) * mult
            t2["_sized"] = True
        out.append(t2)
    return out


def main():
    t0 = time.time()
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r
    from test_experiments_craze import build_module
    from exp_boundary_state_autopsy import load_scope, obs_ts
    from exp_regime_structure_autopsy import build_arrays
    from exp_bleed_autopsy import (compute_new, build_ctx, enrich_sequential,
                                   _chop_series_1h, z1_compute)
    from exp_equity_quality import equity_quality, arm_scores, curve_better

    sim = build_module()
    payload = {
        "stage": "bleed_sizing_down",
        "instrument": "BTCUSDT_BYBIT",
        "lens": ("post-process sizing on the Stage B 4/4-negative cohorts; "
                 "identity = same trade keys; cascade-free by construction"),
        "pre_registered": {
            "pass_rule": ("dNet>0 AND curve_better AND dDD not worse than "
                          f"+{DD_TOLERANCE_PCT}% in ALL 4 cells"),
            "sizes": list(SIZES),
            "dd_tolerance_pct": DD_TOLERANCE_PCT,
            "promotion": "candidate only if 4/4 cells pass",
        },
        "cohorts": list(COHORTS),
        "years": YEARS,
        "cells": {},
    }

    books = {}
    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_scope(scope)
        arr = build_arrays(data["c1h"])
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx = build_ctx(data, arr, chop)
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            trades = sorted(trades, key=lambda t: int(t["entry_ts"]))
            feats = [compute_new(t, ctx) for t in trades]
            enrich_sequential(trades, feats)
            # Attach the Z1 plane (wick_atr12 / flips96) the same way Stage B's
            # main loop does. Without this the two masked cohorts cannot be
            # evaluated at all.
            for t, f in zip(trades, feats):
                f["_z1"] = z1_compute(t, ctx)
            books[f"{scope}|{lane}"] = (trades, feats)
            print(f"  {scope}|{lane}: {len(trades)} trades, "
                  f"net {net_r(trades):+.1f}R", flush=True)

    # ---- score every cohort x size in every cell -------------------------
    for cell in CELLS:
        trades, feats = books[cell]
        years = YEARS[cell.split("|")[0]]
        base_q = equity_quality(trades, years)
        entry = {"n": len(trades), "base_net": round(net_r(trades), 2), "arms": {}}
        arms = entry["arms"]
        for cohort in COHORTS:
            for mult in SIZES:
                if mult == 1.0 and cohort != COHORTS[0]:
                    continue  # control reported once, not per cohort
                sized = size_trades(trades, feats, cohort, mult)
                n_flag = sum(1 for t in sized if t.get("_sized"))
                if n_flag == 0:
                    # A zero here means the cohort predicate matched nothing,
                    # which is ALWAYS a bug (every Stage B qualifier flagged
                    # n>=15 in all 4 cells). Fail loudly rather than reporting
                    # a null arm that looks like "no effect".
                    raise SystemExit(
                        f"{cell} {cohort}@x{mult}: 0 flagged trades - cohort "
                        f"predicate is broken, not the arm"
                    )
                keys_same = ([t["entry_ts"] for t in sized]
                             == [t["entry_ts"] for t in trades])
                q = equity_quality(sized, years)
                d = arm_scores(q, base_q)
                cb = curve_better(d)
                dnet = q["net"] - base_q["net"]
                dd_pct = (100.0 * d["d_max_dd"] / base_q["max_dd"]
                          if base_q["max_dd"] else 0.0)
                arms[f"{cohort}@x{mult}"] = {
                    "n_flagged": n_flag,
                    "identity_keys_same": keys_same,
                    "dNet": round(dnet, 2),
                    "d_dd": round(d["d_max_dd"], 2),
                    "d_dd_pct": round(dd_pct, 1),
                    "d_calmar": round(d["d_calmar"], 3),
                    "d_pf": round(d.get("d_pf", 0.0), 3),
                    "curve_better": cb,
                    "pass": bool(dnet > 0 and cb
                                 and dd_pct <= DD_TOLERANCE_PCT),
                }
        entry["arms"] = arms
        payload["cells"][cell] = entry
    # ---- roll up against the pre-registered rule -------------------------
    arm_names = set()
    for c in payload["cells"].values():
        arm_names |= set(c["arms"].keys())

    rollup = {}
    for arm in sorted(arm_names):
        cells_seen = 0
        cells_pass = 0
        all_identity = True
        for cell, c in payload["cells"].items():
            a = c["arms"].get(arm)
            if not a or "skip" in a:
                continue
            cells_seen += 1
            all_identity &= bool(a["identity_keys_same"])
            if a["pass"]:
                cells_pass += 1
        cohort, mult = arm.split("@x")
        is_control = (mult == "1.0")
        rollup[arm] = {
            "cohort": cohort,
            "size": float(mult),
            "cells": cells_seen,
            "cells_pass": cells_pass,
            "is_control": is_control,
            "identity_ok_all": all_identity,
            "passes_4of4": (cells_seen == 4 and cells_pass == 4
                            and all_identity and not is_control),
        }

    candidates = [k for k, v in rollup.items() if v["passes_4of4"]]
    payload["rollup"] = rollup
    payload["result"] = {
        "candidate_arms": candidates,
        "n_candidates": len(candidates),
        "verdict": (
            "SIZING-DOWN WORKS - a bleed cohort can be de-risked without "
            "removing it." if candidates else
            "NO 4/4 CANDIDATE. Sizing down the 4/4-negative cohorts does not "
            "clear the pre-registered bar. This does NOT contradict the sizing "
            "exemption: the exemption says sizing measurements are VALID "
            "post-process, not that every cohort is worth sizing."
        ),
    }

    # ---- report ----------------------------------------------------------
    print("\n" + "=" * 100, flush=True)
    print("  H1: BLEED COHORTS AS SIZING TARGETS (x1.00 control, x0.75, x0.50)",
          flush=True)
    print("=" * 100, flush=True)
    for cell in CELLS:
        c = payload["cells"][cell]
        print(f"\n  [{cell}]  n={c['n']}  base net {c['base_net']:+.1f}R",
              flush=True)
        print(f"    {'arm':30s} {'flag':>4s} {'dNet':>8s} {'dDD':>7s} "
              f"{'dDD%':>7s} {'dCal':>7s} {'curve':>6s} {'pass':>5s}",
              flush=True)
        for arm, a in c["arms"].items():
            if "skip" in a:
                print(f"    {arm:30s} {a['n_flagged']:4d}   (no flagged trades)",
                      flush=True)
                continue
            print(f"    {arm:30s} {a['n_flagged']:4d} {a['dNet']:+8.1f} "
                  f"{a['d_dd']:+7.1f} {a['d_dd_pct']:+7.1f} {a['d_calmar']:+7.3f} "
                  f"{str(a['curve_better']):>6s} {str(a['pass']):>5s}", flush=True)

    print("\n" + "-" * 100, flush=True)
    print("  ROLLUP (pre-registered: candidate needs 4/4)", flush=True)
    for arm, v in sorted(rollup.items(),
                         key=lambda kv: (-kv[1]["cells_pass"], kv[0])):
        tag = "CONTROL" if v["is_control"] else (
            "CANDIDATE" if v["passes_4of4"] else "")
        print(f"    {arm:30s} pass {v['cells_pass']}/{v['cells']}  "
              f"identity={v['identity_ok_all']}  {tag}", flush=True)
    print()
    print(f"  CANDIDATES (4/4): {candidates if candidates else 'NONE'}",
          flush=True)
    print("=" * 100, flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()