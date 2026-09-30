"""P87 - THE INSTRUMENT P85 ASKED FOR. Does the ATR ceiling predict R once
you already know which half-year it is? And is that prediction stable?

WHY THIS QUESTION AND NOT "IS dNet BIG"
    P69's ATR% ceiling at 0.40% removes trades that are NET NEGATIVE in
    OOS (-41.6R and -37.1R, PF 0.78 on both lanes) and worth nothing in IS.
    P85's permutation test came back p = 0.96-0.99 and was correctly
    declared uninformative, because block-permuting 99-106 trades yields two
    or three independent blocks and a null far coarser than the effect.

    But p = 0.97 was never the right question either. **The right question
    is whether the ceiling tells you anything you could not already get
    from knowing the period.** Every other finding in this round is an
    era-split: the expiry (P56), granularity (P58, P66), the candidate's
    stability (P61), layer agreement (P59), and the long-side defect (P78).
    If the ceiling's power is one more of those, it is a REGIME PROXY and
    not a filter - and a regime proxy is not a rule, because P55, P67 and
    P68 all failed to make the eras separable at decision time.

THE MODEL
        R_i = a  +  b * cohort_i  +  g_{halfyear(i)}  +  e_i

    cohort is 1 for a trade the ceiling KEEPS, 0 for one it DROPS.
    g is a half-year FIXED EFFECT, so b is the cohort difference AFTER
    removing everything the period explains.

    b = 0 means the ceiling carries no information beyond the date.
    b significantly positive means it does, and the filter is a filter.

    Cluster-robust variance by MONTH, not by trade. Trades inside a month
    share a regime - the whole reason the raw p-value in P85 was unusable -
    and a cluster-robust SE with ~24-42 clusters is the smallest unit that
    still leaves a usable number of clusters. Half-year clustering with 4
    and 8 clusters would be fewer than the standard error itself can carry.

    TWO CROSS-CHECKS, because a single statistic on this data is thin:
      CLUSTER BOOTSTRAP  resample whole MONTHS with replacement, refit,
                         and read the share of draws where b comes out <= 0.
                         Months are the cluster, so the resampling respects
                         exactly the dependence the SE assumes.
      HALF-YEAR BOOTSTRAP  resample half-YEARS instead. Far fewer draws,
                         so it can rule and not confirm - P63's finding,
                         in a new place - but it is the most conservative
                         instrument available and it is reported anyway.

WHAT WOULD SETTLE THIS
    b significantly positive on BOTH eras in BOTH lanes, and the month
    bootstrap agreeing. If b collapses when the half-year fixed effect goes
    in, the ceiling was a regime proxy all along and the correct verdict is
    that P69's result and this one are the same finding wearing different
    clothes.
"""
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

import bisect as bs
from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
CEIL = 0.40
ATR_BARS = 96
DRAWS = 4000
SEED = 20261002
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def as_flow(c):
    from src.walker import FlowCandle
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


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


def atr_pct(ts, tr, cl, entry_ts):
    j = bs.bisect_left(ts, int(entry_ts))
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
    """[intercept, cohort, one dummy per group except the first]"""
    cols = [np.ones(len(y)), np.asarray(coh, dtype=float)]
    uniq = sorted(set(groups))
    for g in uniq[1:]:
        cols.append(np.array([1.0 if x == g else 0.0 for x in groups]))
    return np.column_stack(cols)


def fit(X, y):
    XtX = X.T @ X
    Xi = np.linalg.pinv(XtX)
    b = Xi @ (X.T @ y)
    return b, Xi, y - X @ b


def cluster_se(X, e, clusters):
    XtX = X.T @ X
    Xi = np.linalg.pinv(XtX)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in set(clusters):
        m = np.array([x == c for x in clusters])
        u = X[m].T @ e[m]
        meat += np.outer(u, u)
    G = len(set(clusters))
    V = Xi @ meat @ Xi * (G / max(1, G - 1))
    return np.sqrt(np.maximum(np.diag(V), 0.0)), G


def boot_b(y, coh, groups, clusters, draws, rnd):
    """Resample whole clusters with replacement and refit. Returns the share
    of draws in which the cohort coefficient comes out <= 0."""
    idx_by = {}
    for i, c in enumerate(clusters):
        idx_by.setdefault(c, []).append(i)
    keys = sorted(idx_by)
    cnt = 0
    got = 0
    for _ in range(draws):
        pick = []
        for _ in range(len(keys)):
            pick.extend(idx_by[keys[rnd.randrange(len(keys))]])
        if len(pick) < len(y):
            pick += list(range(len(y)))
        pick = sorted(set(pick))
        X = design([y[i] for i in pick], [coh[i] for i in pick],
                   [groups[i] for i in pick])
        bb, _, _ = fit(X, np.array([y[i] for i in pick], dtype=float))
        got += 1
        if len(bb) > 1 and bb[1] <= 0:
            cnt += 1
    return cnt / float(got)


def main():
    print("=" * 100)
    print("  P87  DOES THE ATR CEILING PREDICT R, ONCE YOU KNOW THE PERIOD?")
    print("=" * 100)
    print("  R = a + b*cohort + half-year fixed effect.  cohort 1 = KEPT.")
    print("  Cluster-robust SE by MONTH, plus month and half-year cluster")
    print("  bootstraps.  b is the ceiling's information AFTER the period.")
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

    verdicts = []
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            ctl = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            ts, cl, tr = series(args[2])
            rows = []
            for t in ctl:
                v = atr_pct(ts, tr, cl, t["entry_ts"])
                if v is not None:
                    rows.append((t, 1 if v <= CEIL else 0))
            y = [float(t["r_multiple"]) for t, _ in rows]
            coh = [c for _, c in rows]
            gm = [mon(t["entry_ts"]) for t, _ in rows]
            gh = [half(t["entry_ts"]) for t, _ in rows]
            X = design(y, coh, gh)
            b, Xi, e = fit(X, np.array(y))
            se, G = cluster_se(X, e, gm)
            tstat = b[1] / se[1] if se[1] > 0 else float("nan")
            rnd = random.Random(SEED)
            pm = boot_b(y, coh, gm, gm, DRAWS, rnd)
            ph = boot_b(y, coh, gh, gh, DRAWS // 4, rnd)
            print("  --- [%s]  kept %d, dropped %d"
                  % (scope.upper(), sum(coh), len(coh) - sum(coh)))
            print("      b (kept minus dropped, period-adjusted) = %+.4f R/trade"
                  % b[1])
            nk = max(1, sum(coh))
            nd = max(1, len(coh) - sum(coh))
            raw = (sum(y[i] for i in range(len(y)) if coh[i]) / nk
                   - sum(y[i] for i in range(len(y)) if not coh[i]) / nd)
            print("      raw gap                             = %+.4f R/trade"
                  % raw)
            print("      cluster-robust SE (month, %2d clusters) = %.4f   "
                  "t = %+.2f" % (G, se[1], tstat))
            print("      month-cluster bootstrap  p(b<=0) = %.4f  (%d draws)"
                  % (pm, DRAWS))
            print("      half-year-cluster boot  p(b<=0) = %.4f  (%d draws, "
                  "conservative)" % (ph, DRAWS // 4))
            sig = abs(tstat) >= 1.96 and pm < 0.05
            verdicts.append(sig)
            print("      -> %s" % ("SIGNIFICANT after period control"
                                  if sig else "NOT significant after period "
                                               "control"))
            print()
    ok = all(verdicts)
    print("  " + "=" * 98)
    print("  ALL FOUR CELLS: %s" % ("YES" if ok else "NO"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()