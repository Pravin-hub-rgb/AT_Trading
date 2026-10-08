"""exp_flip_period - the framework's own instrument on flip_quality.

WHY THIS RUNS
=============
`exp_mode_confirm2.py` found that `mode="flip_quality"` is ahead of
`fsent_champ_long` on all three books of its family, with drawdown flat or better
on each. That is a real result and it is still one number away from being one,
because this repo's framework requires an arm to carry information the DATE does
not before anything is believed.

Every other regime-conditional tweak in this repo failed exactly there. The
framework's discriminator, from CEILING_REGCTRL_P87: a regime proxy collapses
once the period is controlled, a real filter barely moves. The ATR% ceiling kept
91-99% of its gap under a half-year fixed effect. Everything else went to zero.

So this runs the instrument:

    R_i = a + b * cohort_i + g_halfyear(i) + e_i

`cohort` is 1 for a trade `flip_quality` KEEPS and 0 for one it drops. `b` is
therefore the arm's effect AFTER everything the calendar explains. Cluster-robust
variance by month, plus month-cluster and half-year-cluster bootstraps. All three
reported; none selectable.

P82'S LESSON, CARRIED OVER, NOT RELEARNED
==========================================
Survivors do NOT cancel. A trade matched on (entry_ts, direction) in both books
is not the same trade: a different routing changes the window it sits in, so its
exit, its hold and its costs move. In P80 that term was **+28.6R of +184.8R** and
two earlier harness versions got it wrong before the assertion caught them.

So the decomposition is asserted exact per cell, and `b` is computed on the
NON-SURVIVOR marginal cohorts only - which is where a routing change's
information actually lives. Survivors are reported separately and excluded from
`b`, because including them mixes "did the regime change pay" with "did the exit
move", and only the first is a claim about the routing.

THE MANDATORY POWER GATE
========================
Printed before the result is interpreted. MDE = 1.96 * SE(b). If MDE exceeds the
effect being looked for, a null is a statement about the test, not about the
arm - P85's lesson, and this repo has twice produced a confident p from a test
with no power.

THE THIRD GATE
==============
The half-year partition. A candidate that trades IS for OOS passes a single
period's control and fails this. `exp_paired_bootstrap` from P82 measures the
partition; here it is a direct per-cell comparison, which is the same question
without the bootstrap's machinery.

Run:  cd backtest/tests
      python -u exp_flip_period.py
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

ARM = "flip_quality"
BOOK = "fsent_champ_long"
FAMILY = ("fsent_champ_long", "fsent_utcsat_long", "fsent_champ_short")
DRAWS = 4000
SEED = 20261008
OUT_JSON = Path(__file__).parent / "_flip_period.json"
OUT_MD = Path(__file__).parent / "_flip_period.md"


def mon(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%02d" % (d.year, d.month)


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def instrument(y, coh, groups, clusters, seed):
    """P87's construction verbatim: intercept + cohort + one dummy per group
    EXCEPT the first, and pinv rather than a plain inverse - a full dummy set is
    rank-deficient and returns b=0 silently on real data."""
    import numpy as np
    y = np.asarray(y, dtype=float)
    coh = np.asarray(coh, dtype=float)
    uniq = sorted(set(groups))
    cols = [np.ones(len(y)), coh]
    for g in uniq[1:]:
        cols.append(np.array([1.0 if x == g else 0.0 for x in groups]))
    X = np.column_stack(cols)
    Xi = np.linalg.pinv(X.T @ X)
    beta = Xi @ (X.T @ y)
    resid = y - X @ beta
    b = float(beta[1])

    # cluster-robust SE
    Xi = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in set(clusters):
        m = np.array([x == c for x in clusters])
        u = X[m].T @ resid[m]
        meat += np.outer(u, u)
    G = len(set(clusters))
    V = Xi @ meat @ Xi * (G / max(1, G - 1))
    se = math.sqrt(max(float(V[1, 1]), 1e-18))
    t = b / se if se > 0 else 0.0
    mde = 1.96 * se

    # cluster bootstrap, refitting on resampled clusters
    rnd = random.Random(seed)
    by = {}
    for i, g in enumerate(clusters):
        by.setdefault(g, []).append(i)
    keys = list(by)
    acc = []
    for _ in range(DRAWS):
        idx = [i for k in [rnd.choice(keys) for _ in range(len(keys))] for i in by[k]]
        if len(set(idx)) < 4:
            continue
        bb = np.linalg.pinv(X[idx].T @ X[idx]) @ (X[idx].T @ y[idx])
        acc.append(float(bb[1]))
    b_boot = (sum(acc) / len(acc)) if acc else 0.0
    return {"b": b, "t": t, "se": se, "mde": mde, "b_boot": b_boot,
            "n_groups": len(uniq), "n_clusters": G,
            "all_sign": (b > 0 and t > 0 and b_boot > 0)}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], "sw10")

    def run(era, name, mode=None):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        if mode:
            p["mode"] = mode
        d = data[era]
        o = sim(d["c1h"], sw[era], d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]

    print("=" * 112)
    print("  PERIOD CONTROL ON %r  -  does the arm's effect survive the calendar?" % ARM)
    print("=" * 112)
    print("  R = a + b*cohort + half-year fixed effect.  cohort 1 = KEPT by the arm.")
    print("  b is the arm's information AFTER the period explains everything.")
    print("  Survivors are excluded from b and reported separately (P82: they do not")
    print("  cancel; in P80 that term was +28.6R of +184.8R).")
    print("  MDE printed with every result, because a null from an underpowered test is")
    print("  a statement about the test.")
    print("  DRAWS=%d seed=%d\n" % (DRAWS, SEED))

    report = {}
    for fam in FAMILY:
        print("#" * 112)
        print("# %s" % fam)
        print("#" * 112)
        for era in ("is", "oos"):
            base = run(era, fam)
            arm = run(era, fam, ARM)
            bk = {(int(t["entry_ts"]), t["dir"]): t for t in base}
            ak = {(int(t["entry_ts"]), t["dir"]): t for t in arm}
            surv = sorted(set(bk) & set(ak))
            new = sorted(set(ak) - set(bk))
            drop = sorted(set(bk) - set(ak))

            surv_cost = sum(net_r([ak[k]]) - net_r([bk[k]]) for k in surv)
            new_sum = sum(net_r([ak[k]]) for k in new)
            drop_sum = sum(net_r([bk[k]]) for k in drop)
            dnet = sum(net_r([t]) for t in arm) - sum(net_r([t]) for t in base)
            recon = surv_cost + new_sum - drop_sum

            print("\n  %s" % era.upper())
            print("    base %dt / %+.2fR      arm %dt / %+.2fR      dNet %+.2fR"
                  % (len(base), sum(net_r([t]) for t in base),
                     len(arm), sum(net_r([t]) for t in arm), dnet))
            print("    survivors %d (%+.2fR cost)   NEW %d (%+.2fR)   DROPPED %d (%+.2fR)"
                  % (len(surv), surv_cost, len(new), new_sum, len(drop), drop_sum))
            print("    ASSERT exact: %s" % ("OK" if abs(dnet - recon) < 1e-6 else
                                           "MISMATCH %.4f vs %.4f - STOP" % (dnet, recon)))
            if abs(dnet - recon) >= 1e-6:
                print("    decomposition does not close; b below would be meaningless")
                return 1

            # ---- the instrument, on the DISAGREEMENT only ----
            #
            # CORRECTION, and it is a design error not a typo. The first version
            # labelled SURVIVORS as cohort=1 and dropped trades as cohort=0, and
            # printed a t of 7.672 out of sample-of-sample. That number is
            # meaningless: it is the regression saying "the arm's 527 surviving
            # trades beat that one dropped trade", which is true and says nothing
            # about the mode. Survivors belong to neither cohort. P82's lesson was
            # that survivors do not cancel when their R moves; here they do cancel
            # exactly (+0.00R in all six cells), because the mode only changes
            # entry selection and never the exit of a trade both books took. So
            # the honest cohort is the disagreement set:
            #
            #     cohort 1 = NEW    the arm took it, base did not
            #     cohort 0 = DROPPED  base took it, the arm did not
            #
            # That is the arm's actual choice, and the only thing worth testing.
            if not new or not drop:
                print("    NO DISAGREEMENT in this cell: %d NEW / %d DROPPED." % (len(new), len(drop)))
                print("    b is NOT ESTIMABLE here. The arm and the base took the same")
                print("    trades. Any 'effect' in this cell would be an artefact of")
                print("    labelling survivors, so none is reported.")
                report.setdefault(fam, {}).setdefault(era, {
                    "dnet": round(dnet, 2), "recon": round(recon, 2),
                    "surv_n": len(surv), "surv_cost": round(surv_cost, 2),
                    "new_n": len(new), "new_sum": round(new_sum, 2),
                    "drop_n": len(drop), "drop_sum": round(drop_sum, 2),
                    "raw_gap_per_trade": None, "b": None, "t": None, "se": None,
                    "mde": None, "b_boot_month": None, "b_boot_half": None,
                    "shrink_pct": None, "estimable": False,
                    "partition": {}, "partition_wins": 0, "partition_cells": 0,
                    "note": "no disagreement between arm and base in this cell",
                })
                continue

            # grp is the half-year label (the fixed effect); mons is the month
            # label (the clustering unit). They are different things and passing
            # one where the other is expected is what crashed the first version.
            cohort, y, grp, mons = [], [], [], []
            for k in new:
                cohort.append(1)
                y.append(net_r([ak[k]]))
                grp.append(half(ak[k]["entry_ts"]))
                mons.append(mon(ak[k]["entry_ts"]))
            for k in drop:
                cohort.append(0)
                y.append(net_r([bk[k]]))
                grp.append(half(bk[k]["entry_ts"]))
                mons.append(mon(bk[k]["entry_ts"]))

            res_m = instrument(y, cohort, grp, mons, SEED)
            # half-year clustering for the second bootstrap
            res_h = instrument(y, cohort, grp, grp, SEED + 1)
            raw_gap = (sum(y[i] for i in range(len(y)) if cohort[i])
                       - sum(y[i] for i in range(len(y)) if not cohort[i]))
            n1 = sum(cohort)
            n0 = len(cohort) - n1
            per_trade = raw_gap / (n1 + n0) if (n1 + n0) else 0.0
            shrink = 100.0 * (1 - res_m["b"] / raw_gap) if raw_gap else 0.0

            print("    marginal cohorts: %d kept, %d dropped   raw gap %+.3fR/trade"
                  % (n1, n0, per_trade))
            print("    b after period control      %+.4f    (%.0f%% of the raw gap survives)"
                  % (res_m["b"], 100 - shrink))
            print("    cluster-robust t (month)   %+.3f     SE %.4f"
                  % (res_m["t"], res_m["se"]))
            print("    month-cluster bootstrap    %+.4f    (b, %d draws)" % (res_m["b_boot"], DRAWS))
            print("    half-year-cluster boot    %+.4f    (b, %d draws)" % (res_h["b_boot"], DRAWS))
            print("    MDE = 1.96*SE = %.4f   vs effect %.4f   -> %s"
                  % (res_m["mde"], abs(res_m["b"]),
                     "UNDERPOWERED, the effect is inside the noise floor"
                     if res_m["mde"] > abs(res_m["b"]) else
                     "powered: the effect exceeds the detectable minimum"))
            print("    POWER GATE PRINTED BEFORE ANY VERDICT, as required.")

            # ---- the third gate: half-year partition ----
            #
            # CORRECTION. The first version accumulated the base side from
            # DROPPED trades only, so in every cell where nothing was dropped the
            # base printed +0.0 and the arm "won" the cell for free - it printed
            # 8 of 8 on a cell where both books took identical trades. A partition
            # must compare like with like, so both sides are the FULL per-cell net
            # of each book, which is the question the owner actually asked.
            cells = {}
            for k, v in ak.items():
                h = half(k[0])
                cells.setdefault(h, [0.0, 0.0])[0] += net_r([v])
            for k, v in bk.items():
                h = half(k[0])
                cells.setdefault(h, [0.0, 0.0])[1] += net_r([v])
            wins = sum(1 for v in cells.values() if v[0] > v[1])
            ties = sum(1 for v in cells.values() if abs(v[0] - v[1]) < 1e-9)
            print("    half-year partition (full per-cell net): arm ahead in %d of %d cells%s"
                  % (wins, len(cells), ", %d tied" % ties if ties else ""))
            for k in sorted(cells):
                a_, b_ = cells[k]
                tag = "arm" if a_ > b_ + 1e-9 else ("base" if b_ > a_ + 1e-9 else "tie")
                print("       %-8s arm %+7.1f   base %+7.1f   %s" % (k, a_, b_, tag))

            report.setdefault(fam, {})[era] = {
                "dnet": round(dnet, 2), "recon": round(recon, 2),
                "surv_n": len(surv), "surv_cost": round(surv_cost, 2),
                "new_n": len(new), "new_sum": round(new_sum, 2),
                "drop_n": len(drop), "drop_sum": round(drop_sum, 2),
                "raw_gap_per_trade": round(per_trade, 4),
                "b": round(res_m["b"], 4), "t": round(res_m["t"], 3),
                "se": round(res_m["se"], 4), "mde": round(res_m["mde"], 4),
                "b_boot_month": round(res_m["b_boot"], 4),
                "b_boot_half": round(res_h["b_boot"], 4),
                "shrink_pct": round(shrink, 1),
                "partition": {k: [round(v[0], 1), round(v[1], 1)] for k, v in cells.items()},
                "partition_wins": wins, "partition_cells": len(cells),
                "estimable": True,
            }
        print()

    print("=" * 112)
    print("VERDICT - framework section 6: b = 0 means a regime proxy, not a rule")
    print("=" * 112)
    print("  %-22s %-4s %10s %10s %8s %10s %8s" % ("book", "era", "raw gap", "b after", "shrink",
                                                  "t(month)", "powered"))
    for fam in FAMILY:
        for era in ("is", "oos"):
            r = report[fam][era]
            if not r.get("estimable", True):
                print("  %-22s %-4s %10s %10s %8s %10s %8s"
                      % (fam, era.upper(), "-", "-", "-", "-", "n/a"))
                continue
            print("  %-22s %-4s %10.4f %10.4f %7.0f%% %10.3f %8s"
                  % (fam, era.upper(), r["raw_gap_per_trade"], r["b"], r["shrink_pct"],
                     r["t"], "yes" if r["mde"] <= abs(r["b"]) else "NO"))
    print()

    est = [(f, e) for f in FAMILY for e in ("is", "oos") if report[f][e].get("estimable", True)]
    n_est = len(est)
    print("  Estimable cells: %d of 6." % n_est)
    if n_est < 6:
        print("  In the other %d cells the arm and the base took IDENTICAL trades, so there is"
              % (6 - n_est))
        print("  no disagreement to measure. That is not a pass and not a fail - it means")
        print("  the mode does nothing there. Read the next section before any verdict.")

    # The disqualifying finding, stated plainly rather than averaged away.
    inert = [f for f in FAMILY
             if report[f]["is"].get("new_n", 0) == 0 and report[f]["is"].get("drop_n", 0) <= 1]
    if len(inert) == len(FAMILY):
        print()
        print("  *** THE MODE IS IN-SAMPLE INERT ON ALL THREE BOOKS. ***")
        print("  In IS the arm takes the same trades as the base: 0 new, and at most one")
        print("  dropped. Every R of the IS 'improvement' is one trade. All of the")
        print("  disagreement is out of sample only, which is the definition of fitting")
        print("  the era - the one thing this framework exists to catch.")
    all_pos = all(report[f][e]["b"] > 0 for f, e in est) if est else False
    all_powered = all(report[f][e]["mde"] <= abs(report[f][e]["b"]) for f, e in est) if est else False
    print()
    if not est:
        print("  No cell is estimable. Nothing to adopt.")
    elif all_pos and all_powered and n_est == 6:
        print("  b survives the period control in all six cells and the effect exceeds the")
        print("  power floor in all six. By the framework's own discriminator this is a")
        print("  FILTER and not a regime proxy - the same category as the ATR% ceiling,")
        print("  which was the only other result in this repo's history to get here.")
    elif all_pos:
        print("  b is positive in every estimable cell, but only %d of 6 cells were" % n_est)
        print("  estimable at all, and the mode is in-sample inert on all three books.")
        print("  Direction survives; magnitude is not established and the instrument")
        print("  cannot be called on the cells where the mode never acted.")
    else:
        print("  b does NOT survive in every cell. The arm is carrying the era, not")
        print("  information - the regime-proxy case the framework exists to catch.")
    print()
    print("  Nothing promoted. Adoption also needs the drawdown budget test and a")
    print("  decision on chop_thresh, which this branch reads and which is not currently")
    print("  in this book's config.")

    OUT_JSON.write_text(json.dumps({"arm": ARM, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# period control on mode='%s'" % ARM, "",
             "R = a + b*cohort + half-year fixed effect. Survivors excluded from b and",
             "reported separately. MDE printed with every result.", "",
             "| book | era | dNet | survivors | NEW | DROPPED | raw gap/trade | b | shrink | t(month) | month boot | half-year boot | MDE | powered | partition |",
             "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for fam in FAMILY:
        for era in ("is", "oos"):
            r = report[fam][era]
            if not r.get("estimable", True):
                lines.append("| %s | %s | %+.1f | %d (%+.1f) | %d (%+.1f) | %d (%+.1f) | "
                             "no disagreement | - | - | - | - | - | - | - | %d/%d |" % (
                                 fam, era.upper(), r["dnet"], r["surv_n"], r["surv_cost"],
                                 r["new_n"], r["new_sum"], r["drop_n"], r["drop_sum"],
                                 r["partition_wins"], r["partition_cells"]))
                continue
            lines.append("| %s | %s | %+.1f | %d (%+.1f) | %d (%+.1f) | %d (%+.1f) | %.4f | %+.4f | %.0f%% | %+.3f | %+.4f | %+.4f | %.4f | %s | %d/%d |" % (
                fam, era.upper(), r["dnet"], r["surv_n"], r["surv_cost"], r["new_n"],
                r["new_sum"], r["drop_n"], r["drop_sum"], r["raw_gap_per_trade"], r["b"],
                r["shrink_pct"], r["t"], r["b_boot_month"], r["b_boot_half"], r["mde"],
                "yes" if r["mde"] <= abs(r["b"]) else "no",
                r["partition_wins"], r["partition_cells"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())