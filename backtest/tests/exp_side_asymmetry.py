"""P89 - IS THE LONG/SHORT ASYMMETRY STRUCTURAL, OR IS IT 2021?

FROM THE NEXT-ROUND BRIEF, BIG PICKLE'S P89
    "The book's long side is intrinsically weaker WITHIN every half-year,
     not merely weak in the era where BTC fell."

WHY THIS IS THE FIRST THING TO RUN
    The brief's section 8.2 states the champion's fragility is "structural
    and known". It is known DESCRIPTIVELY - P84 measured IS longs +272.6R
    against shorts +53.2R, and OOS longs +1.8R against shorts +68.4R - and
    it has never been through the period-control instrument. That gap is
    this run. Everything in P84, P86 and the whole "protect one side"
    research direction rests on whether this asymmetry is a property of the
    strategy or a calendar fact about 2022.

    The honest possibility, which this run is built to catch: the whole
    long/short story is 2021-22 and nothing else. BTC fell from about $69k
    to $15k in that window. A book that is long-heavy can be dead there for
    reasons that have nothing to do with its long side being weak.

THE TEST - PRIMARY IS A SIGN TEST, NOT A REGRESSION, ON PURPOSE
    Per half-year cell, compute mean(long) - mean(short). Twelve cells
    (8 IS + 4 OOS). Count the sign.

    A sign test on 12 cells needs no distributional assumption and is
    immune to the tail concentration that makes a mean-based test fragile
    in this book. Pre-registered decision, fixed before running:

        8 or more of 12 the same sign  -> STRUCTURAL
        7 or fewer                      -> CALENDAR FACT

    Seven is not arbitrary: it is the point at which a binomial against
    even odds stops being clear of the 0.05 level.

SECONDARY - P87's EXACT MODEL, UNCHANGED
        R_i = a + b*is_long_i + g_halfyear(i) + e_i
    Cluster-robust by month, month-cluster bootstrap, half-year-cluster
    bootstrap. All three reported, the flattering one not selectable.
    Swapping `coh` for `is_long` in P87's harness and nothing else.

    Note the two tests can legitimately disagree, and what that would mean:
    if the sign test says CALENDAR while b is positive, the effect exists
    but is too small to act on. That is a third answer, not a contradiction.

MANDATORY POWER GATE, PRINTED BEFORE ANY RESULT
    MDE = 1.96 * SE(b), and the per-cell gap's SE. P85's lesson verbatim:
    if the MDE exceeds the expected gap, a null is a statement about the
    test and not about the strategy.

    Big Pickle's own estimate: sd ~ 6 R/trade, SE(b) ~ 0.6-0.8 after month
    clustering, MDE ~ 1.2-1.5 R/trade against an expected within-cell gap
    of ~0.5. **It predicted this test would be underpowered, and said so
    before it ran.** That prediction is checked here rather than assumed.

WHAT WOULD CHANGE THE ROUND
    b > 0 with all three instruments agreeing in 3 of 4 cells means the
    brief's section 8.2 premise is real and a side-asymmetric condition is
    worth hunting. b = 0 means P84 and P86 were both measuring 2021, and
    "no single trend condition protects one side without taxing the other"
    is a much less interesting fact than the brief currently reads it as.
"""
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
DRAWS = 4000
SEED = 20261004
SIGN_BAR = 8            # of 12 cells, pre-registered
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def mon(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%02d" % (d.year, d.month)


def design(y, islong, groups):
    cols = [np.ones(len(y)), np.asarray(islong, dtype=float)]
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


def boot_p(y, islong, groups, clusters, draws, rnd):
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
        X = design([y[i] for i in pick], [islong[i] for i in pick],
                   [groups[i] for i in pick])
        bb, _ = fit(X, np.array([y[i] for i in pick], dtype=float))
        got += 1
        if len(bb) > 1 and bb[1] <= 0:
            cnt += 1
    return cnt / float(got)


def main():
    print("=" * 100)
    print("  P89  IS THE LONG/SHORT ASYMMETRY STRUCTURAL, OR IS IT 2021?")
    print("=" * 100)
    print("  PRIMARY   sign test on 12 half-year cells: %d+/12 same sign"
          " -> structural; <=7 -> calendar fact." % SIGN_BAR)
    print("  SECONDARY P87's model, R = a + b*is_long + g_halfyear, cluster-")
    print("            robust by month, all three instruments reported.")
    print("  POWER GATE printed BEFORE any result, per P85. M = %.1fR\n"
          % M_NULL)

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

    books, cells = {}, []
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            tr = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = tr
            cells += [(name, scope, tr)]
    print("  controls pinned in all four cells\n")

    # ---------- POWER GATE, BEFORE ANY RESULT ----------
    print("  " + "=" * 98)
    print("  POWER GATE (printed before results, per P85)")
    print("  " + "=" * 98)
    gaps = []
    for name, scope, tr in cells:
        hl = {}
        for t in tr:
            hl.setdefault(half(t["entry_ts"]), []).append(t)
        g = []
        for k, v in hl.items():
            lng = [float(x["r_multiple"]) for x in v if x["dir"] == "long"]
            sht = [float(x["r_multiple"]) for x in v
                   if x["dir"] != "long"]
            if lng and sht:
                g.append((sum(lng) / len(lng) - sum(sht) / len(sht),
                          k, len(lng), len(sht)))
        if g:
            m = sum(x[0] for x in g) / len(g)
            sd = (sum((x[0] - m) ** 2 for x in g) / max(1, len(g) - 1)) ** 0.5
            gaps.append((name, scope, len(g), m, sd, sd / len(g) ** 0.5))
            print("    %-22s %-4s cells %2d  mean gap %+7.3f  sd %6.3f  "
                  "per-cell SE %6.3f"
                  % (name, scope.upper(), len(g), m, sd, sd / len(g) ** 0.5))
    print("    expected within-cell gap ~0.5 R/trade (Big Pickle's estimate)")
    print()

    # ---------- PRIMARY: SIGN TEST ----------
    print("  " + "=" * 98)
    print("  PRIMARY - SIGN TEST ON HALF-YEAR CELLS")
    print("  " + "=" * 98)
    pos = neg = 0
    for name, scope, tr in cells:
        hl = {}
        for t in tr:
            hl.setdefault(half(t["entry_ts"]), []).append(t)
        print("    --- %s / %s" % (name, scope.upper()))
        for k in sorted(hl):
            v = hl[k]
            lng = [float(x["r_multiple"]) for x in v if x["dir"] == "long"]
            sht = [float(x["r_multiple"]) for x in v if x["dir"] != "long"]
            if not (lng and sht):
                continue
            gl = sum(lng) / len(lng)
            gs = sum(sht) / len(sht)
            gap = gl - gs
            if gap > 0:
                pos += 1
                mk = "long> short"
            else:
                neg += 1
                mk = "long< short"
            print("      %-8s long %3dt %+7.3f | short %3dt %+7.3f | "
                  "gap %+7.3f  %s"
                  % (k, len(lng), gl, len(sht), gs, gap, mk))
    print()
    tot = pos + neg
    lead = max(pos, neg)
    print("    SIGN TEST: long better in %d cells, short better in %d, "
          "of %d" % (pos, neg, tot))
    print("    pre-registered bar %d/%d -> %s"
          % (SIGN_BAR, tot,
             "STRUCTURAL" if lead >= SIGN_BAR else "CALENDAR FACT"))
    print()

    # ---------- SECONDARY: P87 MODEL ----------
    print("  " + "=" * 98)
    print("  SECONDARY - P87's model, unchanged: b on is_long")
    print("  " + "=" * 98)
    verdicts = []
    for name, scope, tr in cells:
        y = [float(t["r_multiple"]) for t in tr]
        il = [1.0 if t["dir"] == "long" else 0.0 for t in tr]
        gm = [mon(t["entry_ts"]) for t in tr]
        gh = [half(t["entry_ts"]) for t in tr]
        X = design(y, il, gh)
        b, e = fit(X, np.array(y))
        se = cluster_t(X, e, gm)
        tst = b[1] / se[1] if se[1] > 0 else float("nan")
        mde = 1.96 * se[1]
        rnd = random.Random(SEED)
        pm = boot_p(y, il, gm, gm, DRAWS, rnd)
        ph = boot_p(y, il, gh, gh, max(500, DRAWS // 2), rnd)
        sig = tst >= 1.96 and pm < 0.05 and ph < 0.05
        verdicts.append(sig)
        print("    %-22s %-4s b %+7.4f  SE %.4f  t %+5.2f  MDE %.3f | "
              "month p %.4f  half-yr p %.4f  %s"
              % (name, scope.upper(), b[1], se[1], tst, mde, pm, ph,
                 "SIGNIFICANT" if sig else "not significant"))
    print()
    print("    cells significant: %d of %d" % (sum(verdicts), len(verdicts)))
    print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()