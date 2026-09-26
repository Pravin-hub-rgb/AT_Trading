"""Compute the direct-vs-cascade decomposition for the Stage B wick removal.

WHY THIS EXISTS
---------------
`wick_atr12@short <= 6.03` was removed two ways and the two disagree:

  * post-process - delete the trades from a finished ledger. dNet is -cohortR,
    i.e. POSITIVE, because the cohort was losing.
  * path-true    - refuse the entry inside the engine. dNet is usually NEGATIVE,
    because under exp_mltf a removed trade occupied a busy_until slot and
    suppressed worse entries.

The gap between them is the cascade, and it is the whole reason the removal
retracted. This script derives that gap instead of leaving it to be typed by
hand into prose.

It exists because that number WAS typed by hand, and got the sign wrong: the
cohort R (-28.1) was pasted into the dNet column, turning a cascade of -78.6
into -22.4 and understating it as "45-75%" when it is 125-156% of the total
damage. `AGENT_COORDINATION.md` carries a table derived here; this file is what
keeps that table honest.

NO ENGINE RUN. Pure arithmetic over two existing artifacts, so it is cheap,
deterministic and re-runnable:

  _bleed_autopsy_results.json -> the cohort's n / share / netR (cohortR)
  _wick_short_pathtrue.json   -> the path-true dNet and base/filt nets

FORMULAS
--------
  dNet_postproc = -cohortR                (removing a losing cohort gains R)
  cascade       = dNet_path_true - dNet_postproc
  cascade / direct = |cascade| / |dNet_postproc|
  cascade / total  = |cascade| / |dNet_path_true|

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_wick_cascade_decomposition.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "live_stuff/tests"
BLEED = TESTS / "_bleed_autopsy_results.json"
PATHTRUE = TESTS / "_wick_short_pathtrue.json"
OUT = TESTS / "_wick_cascade_decomposition.json"

# Only the wick cohort is decomposed; the chain cohorts died to the lookahead
# leak and flips96 was never rerun (same lever as wick, same expected fate).
FEATURE = "wick_atr12@short"
CELLS = ("is|champion", "is|utcsat", "oos|champion", "oos|utcsat")

# Sanity envelope. If a future rerun moves these, the artifacts changed shape
# and the doc table is stale - fail loudly rather than emit a wrong number.
EXPECTED = {
    "is|champion": (500, 389, 325.78, 275.23),
    "is|utcsat": (454, 362, 358.95, 304.41),
    "oos|champion": (279, 216, 70.15, -7.81),
    "oos|utcsat": (253, 198, 60.21, 0.59),
}


def _cohort_cells(bleed: dict) -> dict:
    """Pull the [n, share, netR] triple for FEATURE out of the bleed autopsy."""
    for q in bleed["qualifiers_phase1"]:
        if q["name"] == FEATURE:
            return q["cells"]
    raise SystemExit(f"feature {FEATURE!r} not in {BLEED.name}")

def main() -> int:
    t0 = time.time()
    bleed = json.loads(BLEED.read_text(encoding="utf-8"))
    ptrue = json.loads(PATHTRUE.read_text(encoding="utf-8"))
    cohorts = _cohort_cells(bleed)

    result = {
        "stage": "cascade_decomposition",
        "feature": FEATURE,
        "instrument": bleed.get("instrument", "BTCUSDT_BYBIT"),
        "source_postprocess": BLEED.name,
        "source_path_true": PATHTRUE.name,
        "note": (
            "Arithmetic over two existing artifacts. No engine run. "
            "dNet_postproc = -cohortR; cascade = dNet_path_true - dNet_postproc."
        ),
        "cells": {},
    }
    problems: list[str] = []

    for key in CELLS:
        n_coh, share, cohort_r = cohorts[key]
        cell = ptrue["cells"][key]
        base_n, filt_n = cell["base_n"], cell["filt_n"]
        base_net, filt_net = cell["base_net"], cell["filt_net"]

        # dNet as recorded by the two runs must agree with the raw nets.
        rec_pp = -cohort_r
        rec_pt = filt_net - base_net
        if abs(rec_pt - cell["dNet"]) > 0.05:
            problems.append(f"{key}: dNet {cell['dNet']} != filt-base {rec_pt:.2f}")

        cascade = rec_pt - rec_pp
        result["cells"][key] = {
            "n_cohort": n_coh,
            "share": share,
            "cohortR": round(cohort_r, 4),
            "n_base": base_n,
            "n_filtered": filt_n,
            "n_removed": base_n - filt_n,
            "base_net": base_net,
            "filtered_net": filt_net,
            "dNet_postproc": round(rec_pp, 4),
            "dNet_path_true": round(rec_pt, 4),
            "cascade": round(cascade, 4),
            "cascade_over_direct_pct": round(100 * abs(cascade) / abs(rec_pp), 1),
            "cascade_over_total_pct": round(100 * abs(cascade) / abs(rec_pt), 1),
            "direct_was_positive": rec_pp > 0,
            "curve_better": cell.get("curve_better"),
            "identity_identical": cell.get("identical"),
            "base_eq": cell.get("base_eq"),
            "filt_eq": cell.get("filt_eq"),
        }

        exp = EXPECTED[key]
        got = (base_n, filt_n, base_net, filt_net)
        for label, e, g in zip(("base_n", "filt_n", "base_net", "filt_net"), exp, got):
            if abs(float(e) - float(g)) > 0.05:
                problems.append(f"{key}.{label}: expected {e}, artifact has {g}")
    # The load-bearing conclusion: the direct effect was right every time, and
    # the cascade is several times larger than it.
    all_direct_pos = all(r["direct_was_positive"] for r in result["cells"].values())
    worst = min(
        (r["cascade_over_direct_pct"] for r in result["cells"].values()), default=0.0
    )
    result["summary"] = {
        "direct_positive_in_all_cells": all_direct_pos,
        "cascade_exceeds_direct_everywhere": worst > 100.0,
        "min_cascade_over_direct_pct": worst,
        "verdict": (
            "Removal is structurally hopeless under exp_mltf: the cohorts were "
            "genuinely losing (direct effect positive everywhere) but the freed "
            "slots cost more than the removed losers returned. Pivot to sizing."
        ),
    }
    result["elapsed_sec"] = round(time.time() - t0, 2)

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    hdr = (
        f"{'cell':16s} {'n_coh':>5s} {'cohortR':>8s} {'dNet_pp':>8s} "
        f"{'dNet_pt':>8s} {'cascade':>8s} {'c/dir%':>7s}"
    )
    print(hdr)
    print("-" * len(hdr))
    for key in CELLS:
        r = result["cells"][key]
        print(
            f"{key:16s} {r['n_cohort']:5d} {r['cohortR']:8.1f} "
            f"{r['dNet_postproc']:8.1f} {r['dNet_path_true']:8.1f} "
            f"{r['cascade']:8.1f} {r['cascade_over_direct_pct']:7.1f}"
        )
    print()
    print(f"direct positive in all 4 cells : {all_direct_pos}")
    print(f"cascade exceeds direct         : {worst:.1f}% min")
    print(f"wrote {OUT.relative_to(ROOT)}")

    if problems:
        print("\nARTIFACT DRIFT:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())