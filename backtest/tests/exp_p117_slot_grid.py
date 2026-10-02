"""P117 - does the cap grid transfer to the leg book, and what does cap-1 cost?

Two questions, one of which is a backtest and one of which is NOT:

  A  Does the exp_max_concurrent grid transfer from the origin book to the leg
     book, in both eras?      -> this harness. ANSWERED: yes.

  B  Can the live bot hold 5 positions?  -> OUT OF SCOPE. This programme is
     backtesting only. An earlier version of this harness treated B as a
     deployability gate and reported champion-at-cap-1 as "the config the bot can
     execute". That was a category error; see LIVE_CONCURRENCY_P118.md, retracted.
     The live engine runs v18, a different book, which is serial NATIVELY because
     v18_streak_halt.py has no concurrency parameter at all.

So there is no "what does cap-1 cost as a deployment question" headline here.

WHAT THIS ACTUALLY FINDS, and it is a strategy statement: capping concurrency to 1
deletes 111 IS / 61 OOS trades, and the trades it keeps are markedly WORSE per
trade - IS R/t 0.479 -> 0.288, OOS 0.260 -> -0.054. Concurrency is not free
capacity. The trades a 1-slot cap discards are the good ones, which says the
champion's edge is partly in the overlaps.

That shape is identical to every tail-concentration finding in this programme,
which is why it is NOT written up as a concurrency effect until the tail test
passes. Prior: MASTER_CANDIDATES_V2 measured top-5% at 144.8% IS / 221.7% OOS. See
P119 for the ex-top-5% and half-year partition that decides it.

Prior art is origin-era, cited only as prior art:
  ANCHOR_BASIS_AUDIT.md:343-347  cap=5 multi FREE, "use for live risk"
  ANCHOR_BASIS_AUDIT.md:105-107  the cap1..cap5 grid

PRE-REGISTERED FALSIFIER: if cap=5 costs more than noise on the leg book, then
:346-347 is stale in its CONCLUSION, not merely in its numbers. "Stale numbers" is
the cheap failure and would be fixed by re-running. A stale conclusion means the
recommendation was never sound, and no grid can repair it.

SECOND PRE-REGISTERED FALSIFIER, added after the first run: max concurrency on the
leg OOS book is 5, so exp_max_concurrent=6 CANNOT BIND there and cap=6 is vacuous
in that era. The OOS arm of this grid does not test cap=6 at all, and
ANCHOR:344's "cap=5 free" is partly an IS-only claim. Reporting +0.0R as OOS
confirmation would be reading a tautology as evidence.

Pin discipline: the leg book is asserted from this run, not from memory. If the
uncapped leg OOS does not come back at 280 trades / +72.8R, the gate aborts rather
than reporting a grid for a book that is not the shipping one.

Run: python -u exp_p117_slot_grid.py     (about 4 min)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r, get_data
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m

BOOK = "champion_multi_sw10_leg"
CAPS = (1, 4, 5, 6)
PIN_OOS = (280, 72.8)
PIN_IS = (499, 239.1)


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def max_concurrent(tr):
    """Honest overlap audit: every pair, not just consecutive trades."""
    ev = []
    for t in tr:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t["exit_ts"]), -1))
    ev.sort()
    cur = peak = 0
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
    return peak


def worst_dd(tr):
    """Peak-to-trough on cumulative R, in entry order."""
    eq = peak = dd = 0.0
    for t in tr:
        eq += float(t["r_multiple"])
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
    oos_args = _oos_args()
    params = {**BP, **EXPERIMENTS[BOOK]["params"]}
    sim = tc.build_module()

    print("=" * 92)
    print("  P117  CAP GRID ON THE LEG BOOK  |  headline = what cap-1 COSTS")
    print("=" * 92)
    print("  P118: the live bot is structurally cap-1. cap=4/5/6 are not executable")
    print("  today. A = grid transfer (this run).  B = capability (already NO).")
    print("  Prior art ANCHOR_BASIS_AUDIT.md:343-347 is ORIGIN-era.\n")

    rows = {}
    for scope in ("is", "oos"):
        args = is_args if scope == "is" else oos_args
        print("-" * 92)
        print("  [%s]" % scope.upper())
        print("  %-9s %6s %9s %8s %8s %8s %7s"
              % ("cap", "n", "net", "R/t", "PF", "worstDD", "maxconc"))
        for cap in (0,) + CAPS:
            p = dict(params)
            if cap:
                p["exp_max_concurrent"] = cap
            tr = [t for t in sim(*args, **p)["ltf_trades"]
                  if t.get("outcome") != "open"]
            tr.sort(key=lambda t: int(t["entry_ts"]))
            n, net = len(tr), net_r(tr)
            gp = sum(float(t["r_multiple"]) for t in tr
                     if float(t["r_multiple"]) > 0)
            gl = -sum(float(t["r_multiple"]) for t in tr
                      if float(t["r_multiple"]) <= 0)
            pf = gp / gl if gl else float("inf")
            lbl = "uncapped" if cap == 0 else ("cap=%d" % cap)
            print("  %-9s %6d %+9.1f %8.3f %8.3f %8.1f %7d"
                  % (lbl, n, net, net / max(n, 1), pf, worst_dd(tr),
                     max_concurrent(tr)))
            rows[(scope, cap)] = (n, net, pf, worst_dd(tr))
        print()

    got_o, got_i = rows[("oos", 0)], rows[("is", 0)]
    ok_oos = abs(got_o[0] - PIN_OOS[0]) <= 2 and abs(got_o[1] - PIN_OOS[1]) <= 3.0
    ok_is = abs(got_i[0] - PIN_IS[0]) <= 2 and abs(got_i[1] - PIN_IS[1]) <= 3.0
    print("=" * 92)
    print("  PIN GATE  (asserted from the run, not from memory)")
    print("=" * 92)
    print("  IS  got %d / %+.1fR  expected %d / %+.1fR  %s"
          % (got_i[0], got_i[1], PIN_IS[0], PIN_IS[1],
             "PASS" if ok_is else "*** ABORT ***"))
    print("  OOS got %d / %+.1fR  expected %d / %+.1fR  %s"
          % (got_o[0], got_o[1], PIN_OOS[0], PIN_OOS[1],
             "PASS" if ok_oos else "*** ABORT ***"))
    if not (ok_oos and ok_is):
        print("\n  GATE FAILED. No grid is reported for a book that is not the")
        print("  shipping one. Fix the pin or the harness before reading below.\n")
        return

    print("\n" + "=" * 92)
    print("  WHAT CAP-1 COSTS  (the only cell the live bot can execute)")
    print("=" * 92)
    for scope in ("is", "oos"):
        u, c1 = rows[(scope, 0)], rows[(scope, 1)]
        print("  [%s]  uncapped %d / %+.1fR  ->  cap-1 %d / %+.1fR"
              % (scope.upper(), u[0], u[1], c1[0], c1[1]))
        print("         dNet %+.1fR   trades lost %d   worstDD %.1f -> %.1f (%+.1f)"
              % (c1[1] - u[1], u[0] - c1[0], u[3], c1[3], c1[3] - u[3]))
        print("")

    print("=" * 92)
    print("  FALSIFIER: does cap=5 cost more than noise on leg?")
    print("=" * 92)
    for scope in ("is", "oos"):
        d5 = rows[(scope, 5)][1] - rows[(scope, 0)][1]
        v = ("COSTS R - :346-347 stale in CONCLUSION" if abs(d5) > 5.0
             else "within +-5R noise band")
        print("  [%s]  cap5 dNet %+.1fR   %s" % (scope.upper(), d5, v))
    print("\n  A answers whether the GRID transfers. It does not answer whether the")
    print("  bot can USE it - P118 answered that, and the answer is no.")


if __name__ == "__main__":
    main()