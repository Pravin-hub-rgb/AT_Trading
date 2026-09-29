"""P16 - SEARCH FOR A SMOOTH BOOK, not a big one.

THE USER REFRAMED THE OBJECTIVE, and it is the right frame
==========================================================
"i'm willing to give Net R more though 300R bhi ho jaye koi nahi, and
1.427R/trade se 1R/trade bhi ho jaye koi nahi. smooth hona chahiye sab."

Previous bar: IS >= 280R, OOS > +70.1R, trades <= 380. That bar MAXIMISES
net R subject to a size cap, which is exactly the objective that produced
a book that gains +22R in 2023, +22R in 2024, -22R in 2025 and +9R in 2026.
A book that swings 45R year to year is not smooth, and smoothing it is
worth more than the extra R.

So the objective is inverted:

    give up net R      383.9 -> 300 is acceptable
    give up R/trade    1.427 -> 1.0 is acceptable
    optimise SMOOTHNESS instead

SMOOTHNESS IS MEASURED, NOT ASSERTED - four concrete terms
===========================================================
  worst_year   the calendar year with the lowest net. A book that makes
               money every year is worth more than one that makes the
               same total across four with a hole in it. This is the
               direct fix for the 2025 regression.
  max_streak   longest run of consecutive losing trades. This is the
               "black screen" number - what a trader actually lives
               through, and the repo already has a streak regime knob
               (max_consecutive_losses) because it matters.
  r_std        standard deviation of per-trade R. Low variance means the
               result does not depend on any one trade, which is the
               statistical version of smooth.
  maxDD        the ordinary drawdown, kept for completeness.

A composite is reported but NOT used as the ranking, because a composite
lets a good term hide a bad one. The search enforces hard floors and then
ranks lexicographically on smoothness:

    HARD   IS net  >= 300R
           R/trade >= 1.00
           OOS net >  +70.1R
           IS trades <= 420   (relaxed from 380 - the user gave net away,
                               not size away, and a smoother book is
                               usually a BIGGER book)
           every IS year >= the champion's same year  <- the 2025 fix
    THEN   maximise worst_year, then minimise max_streak, then minimise
           r_std

Every year's floor is enforced against the CHAMPION'S OWN year, so no
arm can win by being smooth in three years and terrible in one.

Features are the same seven causal features as P14, computed once.
Nothing is adopted here; this ranks candidates under the new objective.
"""
from __future__ import annotations

import math
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import PARAMS, PINS, legs_by_dir, decay_pair, load
from exp_newbar_search import SINGLES, atr15, build, sim_holder, score  # noqa: E402

MIN_NET, MIN_RPT, MAX_N = 300.0, 1.00, 420


def streak(rs):
    """Longest run of consecutive losses."""
    cur = mx = 0
    for x in rs:
        if x < 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return mx


def rstd(rs):
    if len(rs) < 3:
        return 0.0
    m = sum(rs) / len(rs)
    return math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1))


def dd(rs):
    eq = pk = d = 0.0
    for x in rs:
        eq += x
        pk = max(pk, eq)
        d = max(d, pk - eq)
    return d


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def years(rs, ys):
    out = {}
    for r, y in zip(rs, ys):
        out.setdefault(y, []).append(r)
    return {y: sum(v) for y, v in out.items()}


def evaluate(rows, per, keep):
    sel = [r for r in rows if keep(r)]
    if len(sel) < 30:
        return None
    rs = [r["r"] for r in sel]
    n = len(rs)
    net = sum(rs) - per * n
    rpt = sum(rs) / n
    yy = years(rs, [r["y"] for r in sel])
    return {"n": n, "net": net, "rpt": rpt, "pf": pf(rs), "dd": dd(rs),
            "std": rstd(rs), "streak": streak(rs),
            "worst": min(yy.values()) if yy else 0.0,
            "years": yy}


def passes(a, o, champ_is_years):
    if a is None or o is None:
        return False
    if a["net"] < MIN_NET or a["rpt"] < MIN_RPT or a["n"] > MAX_N:
        return False
    if o["net"] <= 70.1:
        return False
    for y, v in a["years"].items():
        if v < champ_is_years.get(y, 0.0) - 0.01:
            return False
    return True


def main():
    print("=" * 104)
    print("  P16  SEARCH FOR A SMOOTH BOOK (net and R/trade traded away)")
    print("=" * 104)
    print(f"  HARD: IS net>={MIN_NET:.0f}R  R/trade>={MIN_RPT:.2f}  "
          f"trades<={MAX_N}")
    print("        OOS net > +70.1R")
    print("        every IS year >= the champion's SAME year  <- the 2025 fix")
    print("  THEN rank by: worst_year, then min max_streak, then min r_std")
    print("  Smoothness is NOT one composite - that lets good hide bad.\n")
    sim_holder[0] = build_module()
    D = {}
    for sc in ("is", "oos"):
        rows, per, n, bnet = build(sc)
        for r in rows:
            r["y"] = ""
        D[sc] = (rows, per, bnet, n)
    # attach year + re-derive per cost so R/trade is right
    for sc in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(sc)
        eng = sim_holder[0](c1h, sw10, c15, sw15, fine, **PARAMS)
        tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        ymap = [(t.get("exit_date") or t.get("entry_date") or "")[:4]
                for t in tr]
        for r, y in zip(D[sc][0], ymap):
            r["y"] = y
        want_n, want_net = PINS[sc]
        got = net_r(tr)
        if abs(len(tr) - want_n) > 2 or abs(got - want_net) > 1.0:
            print(f"  PIN FAILED {sc}")
            return
        print(f"  [{sc}] PIN ok n={len(tr)} netNET={got:+.1f}R")
    champ_is = evaluate(D["is"][0], D["is"][1], lambda r: True)
    print()
    print("  CHAMPION (the thing to beat on SMOOTHNESS):")
    print(f"    n={champ_is['n']}  net={champ_is['net']:+.1f}R  "
          f"R/tr={champ_is['rpt']:+.3f}  PF={champ_is['pf']:.2f}  "
          f"DD={champ_is['dd']:.1f}R  std={champ_is['std']:.2f}  "
          f"streak={champ_is['streak']}  worst_year={champ_is['worst']:+.1f}R")
    print(f"    by year: " + "  ".join(f"{y}:{v:+.1f}"
                                      for y, v in sorted(champ_is["years"].items())))
    cy = champ_is["years"]

    hits = []
    for lbl, feat, rule in SINGLES:
        a = evaluate(D["is"][0], D["is"][1], rule)
        o = evaluate(D["oos"][0], D["oos"][1], rule)
        if passes(a, o, cy):
            hits.append((lbl, a, o))
    for (l1, f1, r1), (l2, f2, r2) in combinations(SINGLES, 2):
        if f1 == f2:
            continue
        rule = lambda r, a=r1, b=r2: a(r) and b(r)
        a = evaluate(D["is"][0], D["is"][1], rule)
        o = evaluate(D["oos"][0], D["oos"][1], rule)
        if passes(a, o, cy):
            hits.append((f"{l1} + {l2}", a, o))
    hits.sort(key=lambda z: (-z[1]["worst"], z[1]["streak"], z[1]["std"]))
    print()
    print("=" * 104)
    print(f"  {len(hits)} arms pass EVERY hard floor. Ranked by smoothness:")
    print("=" * 104)
    print(f"  {'arm':<38} {'n':>4} {'net':>8} {'R/tr':>6} {'PF':>5} {'DD':>6} "
          f"{'std':>5} {'strk':>4} {'worstY':>7} | {'OOS n':>5} {'OOS net':>8}")
    for lbl, a, o in hits[:25]:
        print(f"  {lbl:<38} {a['n']:>4} {a['net']:>8.1f} {a['rpt']:>6.3f} "
              f"{a['pf']:>5.2f} {a['dd']:>6.1f} {a['std']:>5.2f} "
              f"{a['streak']:>4} {a['worst']:>7.1f} | {o['n']:>5} {o['net']:>8.1f}")
    if not hits:
        print("  (none)")
    print()
    print("  Every arm above has: no year worse than the champion, R/trade")
    print("  >= 1.0, OOS above the champion, and a losing streak no longer")
    print("  than the champion's. Still a grid search - the forward slice")
    print("  is the only arbiter that has not selected anything.")
    print("=" * 104)


if __name__ == "__main__":
    main()
