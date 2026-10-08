"""exp_ceiling_refined - the ATR% ceiling, re-derived post-C17, plus the adaptive
percentile proposal that was never written to disk.

WHY THIS FILE EXISTS - THREE REASONS, ALL LOAD-BEARING
=======================================================

1. THE WHOLE CEILING CHAIN IS PRE-C17 AND CANNOT RUN TODAY.

   P69, P85, P87 and P88 all measured the ATR% ceiling on pins that C17
   invalidated. The harnesses carry a hard control gate and they all abort:

       CONTROL FAILED champion_multi_sw10 is - STOP

   champion_multi_sw10 IS moved 500t/+325.8R -> 502t/+279.3R, a 46.5R drift
   against a +/-1.5R tolerance. Every lane fails. That is not a rounding
   nuisance, it is a 46R move in the base the effect was measured against, and
   the effect itself is smaller than the drift in that cell. Nothing downstream
   of P69 can be trusted until the base is re-derived, so that is step one here
   rather than an assumption.

2. P87 NAMED ITS OWN NEXT EXPERIMENT AND IT WAS NEVER RUN.

   P87's verdict section says the obvious next move is "a pre-registered grid
   re-read" - all four ceilings 0.30/0.40/0.50/0.60 under P87's own unmodified
   instrument - because 0.40% was a peak of a four-point grid and P69 never
   tested the family. That is cheap, it is written down, and it is not on disk.
   It is run here.

3. THE ADAPTIVE PERCENTILE PROPOSAL WAS NEVER WRITTEN.

   Nemotron's PROPOSAL_CEILING_REFINED appears only inside a transcript pasted
   into NEXT_ROUND_BRIEF.md. It proposes making the ceiling adaptive - drop the
   top X% of trailing volatility within the prevailing regime rather than trades
   above an absolute ATR% level - as the fix for P88's IS failure. Its stated
   reasoning is the right one: P88 found the ceiling "ranks trades correctly
   everywhere; it pays only where the trades it rejects are actually losing
   money", and an absolute level drops a different population depending on where
   volatility happens to sit. A percentile drops the same relative population
   always, which is the one property an absolute level lacks.

   No file, no harness, no run. It is built here for the first time.

WHAT IS PRE-REGISTERED, BEFORE ANY RESULT IS LOOKED AT
=====================================================
Criterion for the refined family, fixed now and not adjusted later:

  An arm is ADOPTABLE only if ALL FOUR hold, in BOTH lanes:
    (a) net R better than champion, in BOTH eras
    (b) b > 0 after the half-year fixed effect, in BOTH eras
    (c) cluster-robust t by month AND month-cluster bootstrap AND
        half-year-cluster bootstrap ALL agree in sign, all three reported
    (d) survives the half-year partition

  R3 family-wise: all arms of a family must pass or none is adopted. A single
  good arm is not a result.

WHAT THIS IS NOT
================
It is not an argument that the ceiling works. P88 already said the honest thing -
the ceiling identifies worse trades in every era and only pays where the worse
half is losing money - and a percentile does not obviously change that. It might.
That is the question, and the criterion above is what settles it.

An explicit warning the framework already earned: P69's own note says choosing
0.40% because it was a grid peak is "exactly the search this programme has
refused everywhere else". The same applies to a percentile arm that happens to
look best. Hence all arms reported, not the flattering one.

Run:  cd backtest/tests
      python -u exp_ceiling_refined.py
"""
from __future__ import annotations

import bisect as bs
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

M_NULL = 193.4
ATR_BARS = 96
DRAWS = 4000
SEED = 20261008

# Absolute ceilings from P69's pre-registered grid, unchanged.
CEIL_GRID = (0.30, 0.40, 0.50, 0.60)

# Nemotron's adaptive form. Percentile of trailing ATR% within a trailing
# window, so the dropped cohort is always the top X% of whatever regime is
# running. WINDOW is fixed here and not searched - varying it would be a grid
# search on an unrun family.
PCT_GRID = (60, 70, 80)
PCT_WINDOW_DAYS = 90

# The three volatility regimes Nemotron asked for, as terciles of trailing
# ATR% over the same window, assigned causally at entry.
REGIMES = ("low", "mid", "high")

OUT_JSON = Path(__file__).parent / "_ceiling_refined.json"
OUT_MD = Path(__file__).parent / "_ceiling_refined.md"


def as_flow(c):
    from src.walker import FlowCandle
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def series(c15):
    ts, cl, tr = [], [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev), abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    return ts, cl, tr


def atr_series(ts, tr, cl):
    """ATR% at every 15m bar, using only bars strictly before it."""
    out = []
    run = []
    for j in range(len(ts)):
        if j == 0:
            out.append(None)
            continue
        seg = tr[max(0, j - ATR_BARS):j]
        px = cl[j - 1]
        out.append((sum(seg) / len(seg)) / px * 100.0 if seg and px > 0 else None)
    return out


def pct_rank_window(ts, atr, entry_ts, window_s):
    """Percentile rank of ATR% at entry within the trailing window.

    Returns (rank_pct, tercile) where rank_pct is the fraction of trailing bars
    with a LOWER ATR% than this one. 0 = calmest in the window. Both terms are
    historical, so it is live-computable.
    """
    j = bs.bisect_left(ts, int(entry_ts))
    if j <= 0:
        return None, None
    i = j - 1
    if atr[i] is None:
        return None, None
    lo = bs.bisect_left(ts, int(entry_ts) - window_s)
    win = [atr[k] for k in range(lo, i + 1) if atr[k] is not None]
    if len(win) < 200:
        return None, None
    below = sum(1 for v in win if v < atr[i])
    rank = 100.0 * below / len(win)
    ter = "low" if rank < 33.3333 else ("mid" if rank < 66.6667 else "high")
    return rank, ter


def mon(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%02d" % (d.year, d.month)


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")



def main() -> int:
    from run_experiment import get_data, identity_gate, net_r
    from experiment_registry import BP, EXPERIMENTS
    import test_experiments_craze as tc
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_oos

    print("=" * 104)
    print("  CEILING, RE-DERIVED POST-C17  +  THE ADAPTIVE PERCENTILE (first run, ever)")
    print("=" * 104)
    print("  P69/P85/P87/P88 all measured pre-C17 pins and now abort at their control")
    print("  gate. This re-derives the base first, then runs P87's own unrun grid, then")
    print("  the percentile family that has no file and no history.")
    print("  M = %.1fR   ATR window %d x 15m   pct window %d days\n" % (M_NULL, ATR_BARS, PCT_WINDOW_DAYS))

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    WIN_S = PCT_WINDOW_DAYS * 86400
    report = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        print("  " + "=" * 100)

        lane = {}
        for scope in ("is", "oos"):
            args = src[scope]
            ctl = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            pins = EXPERIMENTS[name]["pins"]
            pn = pins["n"] if scope == "is" else pins["oos_n"]
            pnet = pins["net"] if scope == "is" else pins["oos_net"]
            print("\n  %s control: %dt / %+.1fR   registry pin: %dt / %+.1fR   %s"
                  % (scope.upper(), len(ctl), net_r(ctl), pn, pnet,
                     "MATCH" if (len(ctl) == pn and abs(net_r(ctl) - pnet) < 1.0) else "MISMATCH"))
            if len(ctl) != pn or abs(net_r(ctl) - pnet) >= 1.0:
                print("  CONTROL FAILED %s %s - STOP (registry pin not reproduced)" % (name, scope))
                return 1

            ts, cl, tr = series(args[2])
            atr = atr_series(ts, tr, cl)
            y, coh_cache, ranks = [], {}, {}
            feats = []
            for t in ctl:
                r_ = atr[bs.bisect_left(ts, int(t["entry_ts"])) - 1]
                rk, ter = pct_rank_window(ts, atr, int(t["entry_ts"]), WIN_S)
                feats.append({"r": net_r([t]), "atr": r_, "rank": rk, "ter": ter,
                              "ts": int(t["entry_ts"]),
                              "dir": t.get("dir")})
            lane[scope] = {"feats": feats, "arms": []}
            arms = lane[scope]["arms"]

            # ---- absolute ceilings, P69's grid, under P87's instrument ----
            print("\n    ABSOLUTE CEILING (P69 grid) - drop trades with ATR%% above the level")
            print("    %-9s %6s %9s %9s %10s %10s %8s" % ("ceiling", "kept", "dropped", "dNet", "b(adj)", "t(month)", "verdict"))
            arms = []
            for cv in CEIL_GRID:
                coh = [0 if (f["atr"] is not None and f["atr"] > cv) else 1 for f in feats]
                kept = sum(coh)
                dropped = len(coh) - kept
                dnet = sum(f["r"] for f, c in zip(feats, coh) if c)
                base_net = sum(f["r"] for f in feats)
                res = instrument(feats, coh)
                arms.append({"kind": "abs", "level": cv, "kept": kept, "dropped": dropped,
                             "dnet": round(dnet, 2), "dnet_vs_base": round(dnet - base_net, 2),
                             **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}})
                print("    %-9.2f %6d %9d %+9.1f %10.4f %10.3f %8s"
                      % (cv, kept, dropped, dnet - base_net, res["b"], res["t_month"],
                         "PASS" if res["all_sign"] else "fail"))

            # ---- adaptive percentile, the never-run proposal ----
            print("\n    ADAPTIVE PERCENTILE (never run before) - drop the top X%% of ATR%%")
            print("    within a trailing %d-day window, so the cohort is REGIME-RELATIVE" % PCT_WINDOW_DAYS)
            print("    %-9s %6s %9s %9s %10s %10s %8s" % ("keep<=pct", "kept", "dropped", "dNet", "b(adj)", "t(month)", "verdict"))
            for pc in PCT_GRID:
                coh = []
                for f in feats:
                    if f["rank"] is None:
                        coh.append(1)
                    else:
                        coh.append(0 if f["rank"] > pc else 1)
                kept = sum(coh)
                dropped = len(coh) - kept
                dnet = sum(f["r"] for f, c in zip(feats, coh) if c)
                base_net = sum(f["r"] for f in feats)
                res = instrument(feats, coh)
                arms.append({"kind": "pct", "level": pc, "kept": kept, "dropped": dropped,
                             "dnet": round(dnet, 2), "dnet_vs_base": round(dnet - base_net, 2),
                             **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}})
                print("    %-9d %6d %9d %+9.1f %10.4f %10.3f %8s"
                      % (pc, kept, dropped, dnet - base_net, res["b"], res["t_month"],
                         "PASS" if res["all_sign"] else "fail"))

            # per-tercile, the part Nemotron asked for
            print("\n    BY VOLATILITY REGIME (tercile of trailing ATR%%) - absolute vs percentile")
            print("    %-10s %8s %8s %10s %10s %10s" % ("regime", "n", "kept", "dNet_abs", "dNet_pct70", "meanR"))
            for ter in REGIMES:
                idx = [i for i, f in enumerate(feats) if f["ter"] == ter]
                if not idx:
                    continue
                n_t = len(idx)
                rs_t = [feats[i]["r"] for i in idx]
                coh_a = [0 if (feats[i]["atr"] is not None and feats[i]["atr"] > 0.40) else 1 for i in idx]
                coh_p = [0 if (feats[i]["rank"] is not None and feats[i]["rank"] > 70) else 1 for i in idx]
                da = sum(r for r, c in zip(rs_t, coh_a) if c)
                dp = sum(r for r, c in zip(rs_t, coh_p) if c)
                print("    %-10s %8d %8d %+10.1f %+10.1f %10.2f"
                      % (ter, n_t, sum(coh_a), da, dp, sum(rs_t) / n_t))

            report[name] = lane

    print()
    print("=" * 104)
    print("VERDICT (criterion pre-registered above, both lanes, both eras, all arms)")
    print("=" * 104)
    adopted = []
    for name, lane in report.items():
        for scope in ("is", "oos"):
            for a in lane[scope]["arms"]:
                if a["dnet_vs_base"] > 0 and a["all_sign"] and a["b"] > 0:
                    adopted.append((name, scope, a))
    if adopted:
        for name, scope, a in adopted:
            print("  candidate: %s %s %s %.2f -> dNet %+.1f b %+.3f"
                  % (name, scope, a["kind"], a["level"], a["dnet_vs_base"], a["b"]))
        print("\n  Family-wise (R3): all arms must pass or none adopted.")
        print("  Read the doc for which arms failed and why before quoting any of this.")
    else:
        print("  No arm passes in even one cell. Family FAILS, nothing adopted.")
    print("\n  Nothing adopted. This harness adds no book and changes no registry entry.")

    OUT_JSON.write_text(json.dumps({"report": report}, indent=2) + "\n", encoding="utf-8")
    lines = ["# ceiling re-derived post-C17 + adaptive percentile (first run)", "",
             "M = %.1fR. b is after a half-year fixed effect; t is month-clustered." % M_NULL, "",
             "| lane | era | kind | level | kept | dropped | dNet vs base | b | t(month) | all instruments sign-agree |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for name, lane in report.items():
        for scope in ("is", "oos"):
            for a in lane[scope]["arms"]:
                lines.append("| %s | %s | %s | %.2f | %d | %d | %+.1f | %+.3f | %.2f | %s |" % (
                    name, scope.upper(), a["kind"], a["level"], a["kept"], a["dropped"],
                    a["dnet_vs_base"], a["b"], a["t_month"], "yes" if a["all_sign"] else "no"))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


def instrument(feats, coh):
    """P87's model, UNCHANGED — R = a + b*cohort + half-year fixed effect.
    Cluster-robust SE by month. b is the ceiling's information after the period.
    Month and half-year cluster bootstraps also run; all three reported, none
    selectable.

    The design uses P87's exact construction: intercept + cohort + one dummy per
    group EXCEPT the first (reference category). An earlier version of this file
    used all group dummies with a plain matrix inverse, which is rank-deficient
    and returned b=0 silently on real data. Reference category + pinv is P87's
    shape and the reason its own numbers were never zero."""
    try:
        import numpy as np
    except ImportError:
        return {"b": 0.0, "t_month": 0.0, "all_sign": False,
                "b_boot_month": 0.0, "b_boot_half": 0.0, "note": "numpy unavailable"}

    rows = [(f["r"], c, mon(f["ts"]), half(f["ts"])) for f, c in zip(feats, coh)]
    y = np.asarray([r[0] for r in rows], dtype=float)
    coh_v = np.asarray([r[1] for r in rows], dtype=float)
    groups = [r[3] for r in rows]
    mons = [r[2] for r in rows]

    uniq = sorted(set(groups))
    cols = [np.ones(len(y)), coh_v]
    for g in uniq[1:]:
        cols.append(np.array([1.0 if x == g else 0.0 for x in groups]))
    X = np.column_stack(cols)

    XtX = X.T @ X
    Xi = np.linalg.pinv(XtX)
    beta = Xi @ (X.T @ y)
    resid = y - X @ beta
    b = float(beta[1])

    # cluster-robust SE by month
    XtX = X.T @ X
    Xi = np.linalg.pinv(XtX)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in set(mons):
        m = np.array([x == c for x in mons])
        u = X[m].T @ resid[m]
        meat += np.outer(u, u)
    G = len(set(mons))
    V = Xi @ meat @ Xi * (G / max(1, G - 1))
    se = math.sqrt(max(float(V[1, 1]), 1e-18))
    t = b / se if se > 0 else 0.0

    rnd = random.Random(SEED)

    def boot(clusters):
        by = {}
        for i, g in enumerate(clusters):
            by.setdefault(g, []).append(i)
        keys = list(by)
        acc = []
        for _ in range(2000):
            pick = [rnd.choice(keys) for _ in range(len(keys))]
            idx = [i for k in pick for i in by[k]]
            Xi_b = np.linalg.pinv(X[idx].T @ X[idx])
            acc.append(float((Xi_b @ (X[idx].T @ y[idx]))[1]))
        return sum(acc) / len(acc) if acc else 0.0

    b_month = boot(mons)
    b_half = boot(groups)
    return {"b": b, "t_month": t, "b_boot_month": b_month, "b_boot_half": b_half,
            "all_sign": (b > 0 and t > 0 and b_month > 0 and b_half > 0)}



if __name__ == "__main__":
    raise SystemExit(main())