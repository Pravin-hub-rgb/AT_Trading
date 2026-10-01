"""REPRODUCE the documented Stage-B stack book. Not a new idea — a verification.

The 2026-09-24/26 docs (EQUITY_CURVE_STUDY.md, TRAIL_MECHANICS.md,
CAPITAL_STAGE_PLAN.md) record an exit-side candidate stack that was measured,
causality-audited, and left **default-off**:

    half+delay1   exp_trail_half=1, exp_trail_delay_r=1.0   (wider, delayed trail)
    skip_decisive exp_skip_decisive=1                        (skip use=="decisive")
    STACK         both

Documented champion numbers: 325.8 IS / 70.2 OOS baseline -> 429.6 IS / 110.5 OOS
on the stack book. CAPITAL_STAGE_PLAN section 2 line 46 quotes exactly those
stack-book figures ("429.6->802.8 IS / 110.5->277.7 OOS" for sMZX sizing on top).

Those numbers are 1-3 days old and were produced by a different harness. This
re-runs them through the current engine build to answer one question: **is the
single best documented configuration still exactly what the docs claim?**

That matters more than any new experiment, because the audit in IS_IT_RIGHT.md
concluded the shipped book's OOS edge is three trades wide with a 53.2R DD. If
the stack book reproduces, the fix is already sitting in the repo, fully
causality-audited, and needs no new research — only a deployment decision.

All three flags already exist in the built engine signature (default 0). Nothing
here is new; this only reads documented knobs.

Also runs age10, where the docs predict BOTH arms FAIL (-13.1R IS / -15.7R OOS).
Testing a documented failure is as valuable as testing a documented success.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_stack_repro.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "backtest/tests/_stack_repro.json"

LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))

# (arm, kwargs). Expected nets are PER LANE below, not here - a first version of
# this harness carried one expected table for all three lanes and reported 20
# spurious "mismatches" that were in fact exact reproductions of each lane's own
# documented value. Correction: None means the docs do not state that cell, and
# it is scored as "not stated" rather than as a pass or a fail.
ARM_DEFS = (
    ("baseline",      {}),
    ("half",          {"exp_trail_half": 1}),
    ("half+delay1",   {"exp_trail_half": 1, "exp_trail_delay_r": 1.0}),
    ("skip_decisive", {"exp_skip_decisive": 1}),
    ("STACK",         {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
                       "exp_skip_decisive": 1}),
)
# SOURCE: EQUITY_CURVE_STUDY.md sections 2/3, TRAIL_MECHANICS.md results table,
# CAPITAL_STAGE_PLAN.md section 2 line 46 (the 429.6/110.5 stack-book figures).
EXPECTED = {
    ("is", "champion"):  {"baseline": 325.8, "half": 428.6, "half+delay1": 429.6,
                          "skip_decisive": 325.8, "STACK": 429.6},
    ("oos", "champion"): {"baseline": 70.2, "half": 72.8, "half+delay1": 89.8,
                          "skip_decisive": 99.3, "STACK": 110.5},
    ("is", "utcsat"):    {"baseline": 358.9, "half": None, "half+delay1": 411.1,
                          "skip_decisive": 358.9, "STACK": None},
    ("oos", "utcsat"):   {"baseline": 60.2, "half": 66.3, "half+delay1": 87.1,
                          "skip_decisive": 76.8, "STACK": None},
    ("is", "age10"):     {"baseline": 435.7, "half": None, "half+delay1": 422.6,
                          "skip_decisive": 425.3, "STACK": None},
    ("oos", "age10"):    {"baseline": 43.2, "half": 28.0, "half+delay1": 27.5,
                          "skip_decisive": 16.0, "STACK": None},
}


def dd(rs):
    peak = cum = m = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        m = max(m, peak - cum)
    return round(m, 1)


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    res, checks = {}, []
    for era in ("is", "oos"):
        data, _ = load_book(era)
        ei = 2 if era == "is" else 3
        print(f"\n=== bybit {era.upper()} ===", flush=True)
        for lane, key in LANES:
            row = {}
            for name, kw in ARM_DEFS:
                out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                          fine_ltf=data["fine"],
                          **{**BP, **EXPERIMENTS[key]["params"]}, **kw)
                rs = [net_r([t]) for t in out["ltf_trades"]]
                exp = EXPECTED[(era, lane)].get(name)
                row[name] = {"n": len(rs), "net": round(sum(rs), 1),
                             "max_dd": dd(rs),
                             "median": round(statistics.median(rs), 3),
                             "doc_net": exp,
                             "delta": (None if exp is None
                                       else round(sum(rs) - exp, 1))}
            res.setdefault(era, {})[lane] = row
            print(f"  {lane}", flush=True)
            for name, _ in ARM_DEFS:
                r = row[name]
                dtxt = "  n/a" if r["delta"] is None else f"{r['delta']:>+6.1f}"
                xtxt = "  --- " if r["doc_net"] is None else f"{r['doc_net']:>+7.1f}"
                print(f"    {name:<15} n={r['n']:>3} net={r['net']:>+7.1f} "
                      f"doc={xtxt} d={dtxt} DD={r['max_dd']:>5.1f}", flush=True)

    scored = [c for b in res.values() for lane in b.values() for c in lane.values()
              if c["delta"] is not None]
    ok = [c for c in scored if abs(c["delta"]) < 0.5]
    bad = [c for c in scored if abs(c["delta"]) >= 0.5]
    unstated = sum(1 for b in res.values() for lane in b.values()
                   for c in lane.values() if c["delta"] is None)
    payload = {"stage": "stack_book_reproduction",
               "reproduced": len(ok), "mismatched": len(bad),
               "not_stated_in_docs": unstated,
               "books": res}
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\n{'='*70}\nREPRODUCED {len(ok)}/{len(scored)} documented cells "
          f"({unstated} not stated in the docs)")
    for c in bad:
        print(f"  MISMATCH net={c['net']:+.1f} doc={c['doc_net']:+.1f}")
    if not bad:
        print("Every cell the docs state reproduced exactly, including the "
              "documented age10 FAILURE.")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
