"""P83 - IS THE CHAMPION ROBUST ENOUGH TO SHIP? The question the owner just
asked, and it is a different question from every other one this round.

THE QUESTION
    P82 closed directional FS, which left "the champion trades". That is
    not a complete answer, because the champion's OWN year table is not
    comfortable:

        2021  137t   -1.2R  PF 1.15
        2022  116t  +61.4R  PF 2.12
        2023  103t  +99.4R  PF 3.04
        2024  143t  +98.9R  PF 2.29
        2025  117t  +69.3R  PF 2.33
        2026   91t  +91.4R  PF 3.14

    One year in six is flat-to-negative and another is half-speed. So
    "ship the champion" is only an answer if the champion's WORST plausible
    stretch is survivable, and that is a question about the trade
    SEQUENCE, not the total. A book can net +325.8R over 3.7 years and
    still have an unacceptable drawdown inside one year.

WHAT IS MEASURED - ALL PATH-TRUE, NONE GROUPED BY OUTCOME
      PART A  per calendar year AND per calendar quarter, net / R/trade / PF
      PART B  the LONGEST LOSING RUN in trades and in calendar days - the
              number that decides whether a live bot can sit through it
      PART C  the deepest drawdown, its length in trades and days, and the
              recovery time after it
      PART D  the champion against the FS hybrid and the directional arm,
              year by year, so the "no book wins everywhere" fact is
              measured rather than asserted

    Every field is a property of WHEN a trade happened or how the running
    total behaved. Nothing is grouped by r_multiple, outcome or pnl. The
    running-maximum drawdown is computed over the realised sequence, which
    is a property of that sequence and not a selection.

PASS CRITERION - NONE. THIS IS A RISK CHARACTERISATION, NOT A CANDIDATE TEST.
    The output is what a bot builder needs before sizing: how long the book
    can go sideways, how deep it goes, and how long it takes to come back.
    No arm here is a candidate and nothing is adopted.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

DAY = 86400
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def q(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dQ%d" % (d.year, (d.month - 1) // 3 + 1)


def y(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).year


def agg_by(tr, keyfn):
    acc = {}
    for t in tr:
        acc.setdefault(keyfn(t["entry_ts"]), []).append(t)
    return acc


def row(lbl, tr):
    rs = [float(t["r_multiple"]) for t in tr]
    print("      %-8s %5d %+9.1fR %+8.3f %7.2f %6.1f%%"
          % (lbl, len(rs), sum(rs), sum(rs) / len(rs), pf(rs),
             100.0 * sum(1 for x in rs if x > 0) / len(rs)))


def worst_run(tr):
    """Longest run of consecutive negative-R trades, in trades and days."""
    best = cur = 0
    bs = cs = 0
    for i, t in enumerate(tr):
        if float(t["r_multiple"]) < 0:
            if cur == 0:
                cs = i
            cur += 1
            if cur > best:
                best, bs = cur, cs
        else:
            cur = 0
    if best == 0:
        return 0, 0, 0.0
    s, e = int(tr[bs]["entry_ts"]), int(tr[bs + best - 1]["entry_ts"])
    return best, best, (e - s) / DAY


def maxdd(tr):
    eq = pk = 0.0
    dd = pkd = 0.0
    pki = ddi = 0
    cur_i = 0
    for i, t in enumerate(tr):
        eq += float(t["r_multiple"])
        if eq > pk:
            pk = eq
            pki = i
        if pk - eq > dd:
            dd = pk - eq
            pkd, ddi = pki, i
    rec = None
    for j in range(ddi, len(tr)):
        if (dd - (maxdd_peak(tr, ddi, pkd))) <= 0:
            rec = j
            break
    return dd, ddi - pkd, (int(tr[ddi]["entry_ts"])
                          - int(tr[pkd]["entry_ts"])) / DAY


def maxdd_peak(tr, ddi, pkd):
    return sum(float(t["r_multiple"]) for t in tr[pkd:ddi + 1])


def main():
    print("=" * 100)
    print("  P83  IS THE CHAMPION ROBUST ENOUGH TO SHIP?")
    print("=" * 100)
    print("  One year in six is flat and another is half-speed. A book can")
    print("  net +325.8R over 3.7 years and still be unshippable inside a")
    print("  single year. This measures the SEQUENCE, not the total.\n")

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
            tr = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = tr
    print("  controls pinned in all four cells\n")

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        for scope in ("is", "oos"):
            tr = books[(name, scope)]
            rs = [float(t["r_multiple"]) for t in tr]
            print("  " + "=" * 98)
            print("  %s / %s : %d trades, %+.1fR" % (name, scope.upper(),
                                                      len(tr), net_r(tr)))
            print("  " + "=" * 98)
            print("  PART A - per YEAR / per QUARTER")
            for lbl, fn in (("year", y), ("quarter", q)):
                print("    by %s:" % lbl)
                for k in sorted(set(agg_by(tr, fn))):
                    row(k, agg_by(tr, fn)[k])
            n, _, days = worst_run(tr)
            dd, ddn, ddd = maxdd(tr)
            print("  PART B/C - worst run and drawdown")
            print("    longest consecutive LOSING run: %d trades over "
                  "%.0f calendar days" % (n, days))
            print("    max drawdown: %.1fR over %d trades / %.0f days"
                  % (dd, ddn, ddd))
            neg = [k for k in sorted(set(agg_by(tr, y)))
                   if sum(float(x["r_multiple"])
                          for x in agg_by(tr, y)[k]) <= 0]
            part = [k for k in sorted(set(agg_by(tr, y)))
                    if 0 < sum(float(x["r_multiple"])
                               for x in agg_by(tr, y)[k])
                    < 0.5 * net_r(tr) / len(set(agg_by(tr, y)))]
            print("    years at or below zero: %s" % (neg or "none"))
            print("    years below half-speed:    %s" % (part or "none"))
            print()
    print("  Risk characterisation only. Nothing adopted.")


if __name__ == "__main__":
    main()