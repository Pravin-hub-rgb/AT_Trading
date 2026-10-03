"""P88 - THE FOUR-POINT CEILING GRID, FAMILY-WISE, UNDER P87's INSTRUMENT.

WHY THIS IS THE ONE THING LEFT TO RUN
    P87 built the instrument P85 asked for and it changed the picture: the
    ATR% ceiling's effect survives a half-year fixed effect (only 1-9% of
    the gap is removed) and a month-cluster bootstrap, in three of four
    cells. That is the first result this round that is not an era-split,
    and therefore the first a live system could actually act on.

    But 0.40% is a PEAK of P69's four-point grid, and P69 never tested the
    family. That is precisely the weakness P87 named: the IS cell may fail
    at every level or only at the chosen one, and nobody knows which.

    **This run answers it. It is also the prerequisite for handing the
    context to a fresh round of bots - an unresolved family is the worst
    thing to hand someone.**

THE GRID - FIXED NOW, BEFORE RUNNING, FAMILY-WISE
    ceilings 0.30 / 0.40 / 0.50 / 0.60 percent trailing ATR% (96 x 15m)

    The pass criterion is JOINT, as everywhere else in this programme:
    **every ceiling must (a) beat the champion in net in BOTH eras in BOTH
    lanes, (b) survive the calendar half-year partition, and (c) show
    b significantly positive after period control.** Any level that fails
    any of the three kills the family, and a single surviving level is not
    enough.

    Four ceilings is four chances to look good. Requiring all four is the
    only thing that makes this different from the grid-peek P69 committed.

THE MODEL - IDENTICAL TO P87, NOT MODIFIED
        R_i = a + b*cohort_i + g_halfyear(i) + e_i
    cohort = 1 if the ceiling KEEPS the trade, 0 if it DROPS it.
    Cluster-robust SE by month; month-cluster and half-year-cluster
    bootstraps. Changing the instrument between the grid read and this run
    would invalidate the comparison, so nothing is changed.

THE INSTRUMENT DISAGREEMENT IS CARRIED FORWARD, NOT RESOLVED AWAY
    P87 found the cluster-robust t and the bootstraps disagree on champion
    IS at 0.40% (t = +1.66 vs p = 0.0027 and p = 0.0150). Rather than pick
    the flattering one, **all three are reported for every level**, and a
    level is called significant only when all three agree. That is the
    strictest reading available and it is fixed before running.

WHAT A POSITIVE FAMILY WOULD AND WOULD NOT MEAN
    It would mean the ceiling is a real, causal, replayable feature whose
    information survives period control - not a regime proxy, and not a
    grid peak. It would NOT mean adoptable: the deck-relative null M, the
    forward slice, and the owner decision all still apply. P63 is explicit
    that a forward slice can rule and never confirm.
"""
import bisect as bs
import collections
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
CEILS = (0.30, 0.40, 0.50, 0.60)     # percent ATR%, fixed now
ATR_BARS = 96
DRAWS = 3000
SEED = 20261003
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def series(c15):
    ts, cl, tr = [], [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    return ts, cl, tr


def atr_pct(ts, tr, cl, e):
    j = bs.bisect_left(ts, int(e))
    if j <= 0:
        return None
    seg = tr[max(0, j - ATR_BARS):j]
    px = cl[j - 1]
    return (sum(seg) / len(seg)) / px * 100.0 if seg and px > 0 else None


def mon(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%02d" % (d.year, d.month)


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def design(y, coh, groups):
    cols = [np.ones(len(y)), np.asarray(coh, dtype=float)]
    for g in sorted(set(groups))[1:]:
        cols.append(np.array([1.0 if x == g else 0.0 for x in groups]))
    return np.column_stack(cols)


def fit(X, y):
    Xi = np.linalg.pinv(X.T @ X)
    b = Xi @ (X.T @ y)
    return b, y - X @ b


def cluster_t(X, e, clusters):
    Xi = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in set(clusters):
        m = np.array([x == c for x in clusters])
        u = X[m].T @ e[m]
        meat += np.outer(u, u)
    G = len(set(clusters))
    V = Xi @ meat @ Xi * (G / max(1, G - 1))
    return np.sqrt(np.maximum(np.diag(V), 0.0))


def boot_p(y, coh, groups, clusters, draws, rnd):
    idx = {}
    for i, c in enumerate(clusters):
        idx.setdefault(c, []).append(i)
    keys = sorted(idx)
    cnt = got = 0
    for _ in range(draws):
        pick = []
        for _ in range(len(keys)):
            pick.extend(idx[keys[rnd.randrange(len(keys))]])
        if len(pick) < len(y):
            pick += list(range(len(y)))
        pick = sorted(set(pick))
        X = design([y[i] for i in pick], [coh[i] for i in pick],
                   [groups[i] for i in pick])
        bb, _ = fit(X, np.array([y[i] for i in pick], dtype=float))
        got += 1
        if len(bb) > 1 and bb[1] <= 0:
            cnt += 1
    return cnt / float(got)


def main():
    print("=" * 104)
    print("  P88  THE FOUR CEILINGS, FAMILY-WISE, UNDER P87's INSTRUMENT")
    print("=" * 100)
    print("  Ceilings %%: %s   - fixed now, before running." % (CEILS,))
    print("  FAMILY-WISE: every level must beat in both eras both lanes,")
    print("  survive the half-year partition, AND show b significant after")
    print("  period control on ALL THREE instruments.")
    print("  M = %.1fR\n" % M_NULL)

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

    books = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            ctl = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(ctl) - PIN[name][i][0]) > 2
                    or abs(net_r(ctl) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = (ctl, series(src[scope][2]))
    print("  controls pinned in all four cells\n")

    lvl_ok = {c: [] for c in CEILS}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 102)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            ctl, (ts, cl, tr) = books[(name, scope)]
            base = net_of(ctl)
            pc = collections.defaultdict(list)
            for t in ctl:
                pc[half(t["entry_ts"])].append(float(t["r_multiple"]))
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(ctl), base))
            print("      %-8s %5s %9s %9s %8s %8s %10s %9s %8s"
                  % ("ceiling", "kept", "net", "dNet", "R/t", "PF",
                     "part", "b", "t"))
            for cv in CEILS:
                kept, rows = [], []
                for t in ctl:
                    v = atr_pct(ts, tr, cl, t["entry_ts"])
                    if v is None:
                        continue
                    if v <= cv:
                        kept.append(t)
                        rows.append(t)
                    else:
                        rows.append(t)
                coh = [1 if t in kept else 0 for t in rows]
                if sum(coh) < 5 or len(coh) - sum(coh) < 5:
                    print("      %-8.2f  cohort too small" % cv)
                    continue
                y = [float(t["r_multiple"]) for t in rows]
                gm = [mon(t["entry_ts"]) for t in rows]
                gh = [half(t["entry_ts"]) for t in rows]
                X = design(y, coh, gh)
                b, e = fit(X, np.array(y))
                se = cluster_t(X, e, gm)
                tst = b[1] / se[1] if se[1] > 0 else float("nan")
                rnd = random.Random(SEED)
                pm = boot_p(y, coh, gm, gm, DRAWS, rnd)
                ph = boot_p(y, coh, gh, gh, max(500, DRAWS // 3), rnd)
                pp = collections.defaultdict(list)
                for t, c in zip(rows, coh):
                    if c:
                        pp[half(t["entry_ts"])].append(
                            float(t["r_multiple"]))
                w = l = 0
                for k in set(pc) | set(pp):
                    a, q = pc.get(k, []), pp.get(k, [])
                    if not (a and q):
                        continue
                    if sum(q) / len(q) > sum(a) / len(a):
                        w += 1
                    else:
                        l += 1
                net = net_of(kept)
                rs = [float(t["r_multiple"]) for t in kept]
                sig = abs(tst) >= 1.96 and pm < 0.05 and ph < 0.05
                cell_ok = (net > base) and w > l and sig
                lvl_ok[cv].append(cell_ok)
                print("      %-8.2f %5d %+9.1fR %+9.1fR %+8.3f %8.2f "
                      "%4d-%-4d %+9.4f %+8.2f  %s"
                      % (cv, len(rs), net, net - base, net / len(rs),
                         pf(rs), w, l, b[1], tst,
                         "PASS" if cell_ok else "fail"))
                print("              month-boot p=%.4f  half-year-boot p=%.4f"
                      % (pm, ph))
            print()

    print("  " + "=" * 102)
    print("  FAMILY-WISE VERDICT - every level must pass all four cells")
    print("  " + "=" * 102)
    allok = True
    for cv in CEILS:
        v = lvl_ok[cv]
        ok = len(v) == 4 and all(v)
        allok = allok and ok
        print("    ceiling %.2f%%   cells %s   %s"
              % (cv, " ".join("P" if x else "f" for x in v),
                 "PASSES" if ok else "FAILS"))
    print("\n  FAMILY: %s" % ("PASSES" if allok else "FAILS"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()