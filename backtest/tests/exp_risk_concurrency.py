"""P45 - P2, RISK-WEIGHTED CONCURRENCY.

THE QUEUE ITEM
    "`exp_max_concurrent` counts open positions, treating a 3-ATR stop and a
    1-ATR stop as identical risk. Cap the SUM of open risk instead. Zero
    repo hits for `sum_risk`/`open_risk`/`risk_cap`. The stated blocker (no
    size channel) does not apply - a skip rule needs only the open positions
    and their `sl`, which v18 has. Cheapest real edge candidate.
    Caveat: the graveyard's one consistent brake lesson is that every brake
    that actually binds costs R."

PART 0 IS THE WHOLE ANSWER, AND IT IS STRUCTURAL
    v18_streak_halt.py:743 sets `busy_until = exit_date` and line 577 skips
    every bar while `bar_time <= busy_until`. The LTF book is strictly
    serial: there is never more than one open position, in any cell, ever.
    So the count-based cap and a risk-weighted cap are the SAME RULE on this
    book - there is nothing for a sum to weigh. The queue's blocker was
    wrong about the mechanism and right about the data, but the item as
    written has no surface to bind on. That is measured here, not asserted.

PART 1 - the only non-vacuous form
    If "risk weighted" is read per-trade instead of per-book - skip a trade
    whose stop distance is wide - that DOES have surface, and it is exactly
    the shape of brake the graveyard warns about. Swept as a percentile of
    stop distance, both eras, both lanes.

PART 2 - is there a gradient at all
    The census of stop distance. If wide-stop trades are indistinguishable
    from the rest, no threshold can work and the sweep is over before it
    starts.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING

PCTS = (50, 60, 70, 80, 90)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (453, 279.5), (254, 66.9)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def pct(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    k = int(round((len(s) - 1) * q / 100.0))
    return s[k]


def row(lbl, sel, nb):
    if len(sel) < 15:
        print("      %-42s %5d   (too few)" % (lbl, len(sel)))
        return
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    print("      %-42s %5d %+9.1fR %+8.1fR %6.2f %7.1f%%"
          % (lbl, len(sel), net, net - nb, pf(rs), hit))


def main():
    print("=" * 100)
    print("  P45  P2 - RISK-WEIGHTED CONCURRENCY")
    print("=" * 100)
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, n0, nb))
                return
            for t in tr:
                ep = float(t["entry_price"])
                t["_rk"] = abs(ep - float(t["sl"])) / ep * 100.0
            # PART 0 - concurrency census
            ov = 0
            maxov = 0
            span = sorted([[int(t["entry_ts"]), int(t["exit_ts"])]
                           for t in tr])
            for a0, a1 in span:
                c = sum(1 for b0, b1 in span if b0 <= a0 < b1)
                ov += c
                maxov = max(maxov, c)
            print("    [%s] control %dt %+.1fR (PIN ok)" % (scope.upper(),
                                                            n0, nb))
            print("      PART 0  max concurrent open positions: %d "
                  "(1 = serial, a risk-sum cap cannot bind)" % maxov)
            # PART 2 - gradient census
            rks = [t["_rk"] for t in tr]
            print("      PART 2  stop distance %% of price: p10 %.3f  p50 "
                  "%.3f  p90 %.3f  max %.3f"
                  % (pct(rks, 10), pct(rks, 50), pct(rks, 90), max(rks)))
            med = pct(rks, 50)
            lo = [t for t in tr if t["_rk"] <= med]
            hi = [t for t in tr if t["_rk"] > med]
            for lbl, grp in (("half the book: tight stop", lo),
                             ("half the book: wide stop", hi)):
                rs = [float(x["r_multiple"]) for x in grp]
                print("      %-42s %5d %+9.1fR %7.3fR %6.2f %7.1f%%"
                      % (lbl, len(grp), net_r(grp), sum(rs) / len(rs),
                         pf(rs), 100.0 * sum(1 for x in rs if x > 0) / len(rs)))
            # PART 1 - per-trade risk gate
            print("      PART 1  skip trades wider than the pX stop")
            row("A no filter", tr, nb)
            for q in PCTS:
                thr = pct(rks, q)
                row("skip widest %d%% (stop > %.3f%%)" % (100 - q, thr),
                    [t for t in tr if t["_rk"] <= thr], nb)
            for q in PCTS:
                thr = pct(rks, q)
                row("KEEP widest %d%% only (stop > %.3f%%)" % (100 - q, thr),
                    [t for t in tr if t["_rk"] > thr], nb)
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()