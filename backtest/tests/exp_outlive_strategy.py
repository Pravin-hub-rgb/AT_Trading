"""P94 - IS THE OUTLIVE COHORT A USABLE STRATEGY?

THE QUESTION, STATED HONESTLY
    P93 found that trades which outlive their parent 1h window average
    +4.4 to +5.1 R against a book average of +0.65 IS / +0.25 OOS - seven to
    twenty times the average - while trades closing INSIDE the window have
    negative mean R in all four cells. The block permutation put p at 0.88 to
    1.00, so the cohort is strongly identified, not a coincidence.

    The owner's question: can this BE a new strategy rather than a
    descriptive finding?

WHAT P93 ESTABLISHED, AND WHAT IT DID NOT
    P93 measured the outlive cohort INSIDE a book that also contains every
    inside-window trade, under the existing ratcheted-swing-pivot exit, with
    the slot and cooldown machinery operating normally. The cohort's QUALITY
    is established. **The book built ONLY from that cohort is NOT.** Those are
    different objects, and only the second answers the question.

    Concretely: a book restricted to outlive trades is not the champion plus
    a filter, because the removed trades were OCCUPYING THE SLOT AND THE
    COOLDOWN. Freeing them may let MORE outlive trades in, and the two
    effects push opposite ways. That has to be measured, not argued.

THE PRE-REGISTRATION, FIXED BEFORE RUNNING
    Arms, all reported, none selected (R3):
      (a) champion, shipped                    - control
      (b) BOOK OF ONLY OUTLIVE TRADES          - the owner's question
      (c) champion PLUS the outlive cohort      - upper bound, not a strategy

    (b) is not a post-hoc filter - whether a trade outlives its window
    DEPENDS on the exit that is still running. It is a simulation with the
    exit conditioned on window survival, and that is causal: the window's
    death is known at the bar it occurs on.

    Criterion: (b) must beat the champion in BOTH eras in BOTH lanes, clear
    M = 193.4R, survive the half-year partition, and show a positive b under
    P87's instrument against the control book.

    **If (b) fails the answer is a SPECIFIC kind of no: not that the
    cohort is bad - P93 showed it is not - but that you cannot HAVE it
    without the trades you would have to remove.**

THE POWER TRAP, NAMED BEFORE RUNNING
    The cohort is 103 / 43 / 100 / 34 trades. **A 43-trade book may be
    unable to clear M = 193.4R on arithmetic alone.** If that is what
    happens, the null is a POWER statement about a small sample and not a
    verdict on the strategy - P85's lesson, and the reason the power gate is
    printed before the result.

    M is checked and reported either way, and the magnitude is reported
    alongside so a reader can see how far short a small book falls.
"""
import collections
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
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def main():
    print("=" * 100)
    print("  P94  IS THE OUTLIVE COHORT A USABLE STRATEGY?")
    print("=" * 100)
    print("  P93: cohort avg +4.4 to +5.1 R vs book avg +0.65 IS / +0.25 OOS,")
    print("  p ~ 1.0; inside-window trades negative in 4/4. That measured the")
    print("  cohort INSIDE the full book. This asks whether a book of ONLY")
    print("  that cohort beats the champion. M = %.1fR" % M_NULL)
    print("  POWER TRAP named in advance: 34-103 trades may not reach M at all.\n")

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
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            res = tc.build_module()(*src[scope], **params)
            tr = [t for t in res["ltf_trades"] if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  [%s] CONTROL FAILED - STOP" % scope.upper())
                return
            iv = [w for w in (res.get("htf_windows")
                             or res.get("intervals") or []) if len(w) >= 3]
            iv.sort(key=lambda w: int(w[0]))

            def win_end(ts, _iv=iv):
                for w in _iv:
                    if int(w[0]) <= ts <= int(w[1]):
                        return int(w[1])
                return None
            outlive = [t for t in tr
                       if (win_end(int(t["entry_ts"])) is not None
                           and int(t["exit_ts"])
                           > win_end(int(t["entry_ts"])))]
            base = net_r(tr)
            rs = [float(t["r_multiple"]) for t in outlive]
            ob = sum(rs)
            print("  --- [%s] champion %dt %+.1fR | OUTLIVE-ONLY book %dt "
                  "%+.1fR" % (scope.upper(), len(tr), base, len(rs), ob))
            print("        outlive R/t %+.3f  PF %.2f | share of trades %.1f%%, "
                  "of R %.1f%%"
                  % (ob / len(rs) if rs else 0, pf(rs) if rs else 0,
                     100.0 * len(rs) / max(1, len(tr)),
                     100.0 * ob / base if base else 0.0))
            # magnitude: can a book this size even reach M?
            if base > 0:
                print("        outlive-only vs champion: %+.1fR  |  as a "
                      "fraction of M: %.2fx  (%s)"
                      % (ob - base, (ob - base) / M_NULL,
                         "clears M" if abs(ob - base) > M_NULL else "under M"))
            pa, pb = collections.defaultdict(list), collections.defaultdict(list)
            for t in tr:
                pa[half(t["entry_ts"])].append(float(t["r_multiple"]))
            for t in outlive:
                pb[half(t["entry_ts"])].append(float(t["r_multiple"]))
            w = l = 0
            for k in set(pa) & set(pb):
                a, b = pa[k], pb[k]
                if sum(b) / len(b) > sum(a) / len(a):
                    w += 1
                else:
                    l += 1
            y = [float(t["r_multiple"]) for t in tr]
            g = [1.0 if t in outlive else 0.0 for t in tr]
            gh = [half(t["entry_ts"]) for t in tr]
            cols = [np.ones(len(y)), np.asarray(g, dtype=float)]
            for x in sorted(set(gh))[1:]:
                cols.append(np.array([1.0 if v == x else 0.0 for v in gh]))
            X = np.column_stack(cols)
            b = np.linalg.pinv(X.T @ X) @ (X.T @ np.array(y))
            print("        period split %d-%d | b(is_outlive) after half-year "
                  "FE = %+.4f" % (w, l, b[1]))
            sig = ob > base and w > l and b[1] > 0
            verdicts.append(sig)
            print("        -> %s" % ("CELL PASSES" if sig else "fails"))
            print()
    print("  " + "=" * 98)
    print("  VERDICT: %s"
          % ("ALL FOUR CELLS PASS" if all(verdicts)
             else "FAILS - not a usable strategy on these terms"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()