"""P10 - THE RIDER WAS NEVER A TRADER. Identify runners while they run.

THE USER'S INSIGHT, which the repo's own data already proves
===========================================================
"the big winner - he rode it, it wasn't a trend. that's why they kept
riding: the swing ratchet was never crossed, so it just kept going. that's
what caught it. so now we have to find out how the market can tell us."

`_trail3.out.txt` (STUDY 3) answers the first half of this exactly, and
the numbers are a perfect monotonic separator:

  IS champion_multi_sw10, n=500
    0 ratchets (37.4%)   -187.0R   avgR -1.00   bars   193.3
    1.8 ratchets (42.4%) -111.3R   avgR -0.52   bars  1691.2
    3.4 ratchets (7.6%)    +69.1R  avgR +1.82   bars  3001.7
    4.8 ratchets (9.2%)   +253.2R  avgR +5.51   bars  5140.3
    6.6 ratchets (3.4%)   +421.1R  avgR +24.77  bars  7518.9

**6.8% of trades carry +151% of gross P&L. 37.4% carry -42%.** And the
separating variable is exactly what the user named: how many times the
ratchet moved. The user is right, and it is not a new observation.

THE PROBLEM, which is what this file is for
==========================================
`ratchets` and `bars` are measured AT EXIT. They are hindsight. Knowing
at close that a trade ratcheted six times tells you nothing you could have
acted on. The repo's trail-family work is saturated on the exit side -
half/delay1/tighten all REJECTED - because exit modulation cannot fix an
entry problem.

So the live question is: **at a moment you could actually act, can you
tell a runner from a non-runner?**

There is exactly one such moment in this book, and it is a market
observable, not a strategy internal: **the instant the trade first touches
+1R.** At that bar you know the trade survived its initial risk, you know
how long it took, you know how deep the drawdown was on the way, and you
know whether the ratchet had already moved. Everything after that is the
exit question, which is closed.

WHAT THIS MEASURES
==================
For every champion trade, replayed on the 1m fine series:
  t_1R     bars (15m) until the trade first reaches +1R
  mae_1R   worst excursion (in R) BEFORE it reached +1R
  r_at_1R  how many times the ratchet had moved by +1R
Then, for each bucket, the ACTUAL final outcome - what fraction went on
to 3R+, 10R+, and what fraction died at -1R.

The output is a conditional-probability table, not a P&L table. The
question it answers is binary and actionable: **is there a live state at
+1R where the odds of a 10R+ runner are high enough to be worth acting on,
or is +1R uninformative?** If P(10R+ | state) is flat across every
bucketing, then the runner is unknowable in real time, the exit family
stays closed, and the user's "market can tell us" has a definitive no.
That is worth as much as a yes.

FALSIFIERS, PRE-REGISTERED HERE
==============================
  (a) P(10R+ | t_1R bucket) shows no monotone ordering in BOTH eras
      -> +1R is uninformative, runners are not identifiable live
  (b) the ordering exists in IS and inverts in OOS -> hindsight only
  (c) P(10R+) never exceeds ~5% in any bucket -> nothing worth acting on
      even if ordered
Reported whichever lands.
"""
from __future__ import annotations

import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}


def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, build_module())
    return (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])


def trace(tr, fts, fpx):
    """Replay one trade on the 1m series up to +1R. Returns the LIVE state.

    Everything read here is knowable at the +1R bar: bars elapsed, worst
    excursion on the way, and the ratchet level already locked. Nothing
    after that bar is read.
    """
    d = 1 if tr["dir"] == "long" else -1
    e = float(tr["entry_price"])
    sl = float(tr["sl"])
    risk = abs(e - sl)
    if risk <= 0:
        return None
    a = bs.bisect_left(fts, int(tr["entry_ts"]))
    b = bs.bisect_left(fts, int(tr["exit_ts"]))
    if a >= len(fpx):
        return None
    mae = 0.0
    ratchet = -risk            # locked R; only ever moves up
    t0 = fts[a]
    bars = 0.0
    for k in range(a, min(b + 1, len(fpx))):
        adv = d * (fpx[k] - e)
        if adv > ratchet:
            ratchet = adv
        if adv < mae:
            mae = adv
        if adv <= -risk:        # stopped out before ever reaching +1R
            return {"reached": False, "t_1R": None, "mae": mae / risk,
                    "r_1R": None, "final_r": float(tr["r_multiple"])}
        if adv >= risk:         # +1R reached: freeze the live state HERE
            return {"reached": True, "t_1R": (fts[k] - t0) / 900.0,
                    "mae": mae / risk, "r_1R": ratchet / risk,
                    "final_r": float(tr["r_multiple"])}
    return {"reached": False, "t_1R": None, "mae": mae / risk,
            "r_1R": None, "final_r": float(tr["r_multiple"])}

def show(scope, tag, rows, key, edges):
    print(f"  [{scope}] {tag}")
    print(f"    {'bucket':<18} {'n':>4} {'P(3R+)':>8} {'P(10R+)':>8} "
          f"{'P(die)':>9} {'avgR':>8}")
    for i in range(len(edges) + 1):
        lo = -1e18 if i == 0 else edges[i - 1]
        hi = 1e18 if i == len(edges) else edges[i]
        sel = [x for x in rows if x["reached"] and lo < x[key] <= hi]
        lab = ("<=" + f"{edges[0]:.1f}" if i == 0 else
               (f">{edges[-1]:.1f}" if i == len(edges) else
                f"{edges[i-1]:.1f}-{edges[i]:.1f}"))
        if not sel:
            print(f"    {lab:<18} {0:>4}")
            continue
        n = len(sel)
        p3 = 100.0 * sum(1 for x in sel if x["final_r"] >= 3) / n
        p10 = 100.0 * sum(1 for x in sel if x["final_r"] >= 10) / n
        pd = 100.0 * sum(1 for x in sel if x["final_r"] <= -0.9) / n
        print(f"    {lab:<18} {n:>4} {p3:>7.1f}% {p10:>7.1f}% {pd:>8.1f}% "
              f"{sum(x['final_r'] for x in sel)/n:>+8.2f}")


def main():
    print("=" * 92)
    print("  P10  CAN A RUNNER BE IDENTIFIED WHILE IT IS STILL RUNNING?")
    print("=" * 92)
    print("  The only actionable moment is +1R. State read there, frozen.")
    print("  Below: what the live state BUYS, as outcome probabilities.")
    print("  Pins reproduced first.\n")
    sim = build_module()
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        eng = sim(c1h, sw10, c15, sw15, fine, **PARAMS)
        tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got = net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got - want_net) <= 1.0
        print(f"  [{scope}] PIN n={len(tr)} netNET={got:+.1f} "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing.")
            return
        fts = [int(c["ts"]) for c in fine]
        fpx = [float(c["close"]) for c in fine]
        rows = [x for x in (trace(t, fts, fpx) for t in tr) if x]
        nr = sum(1 for x in rows if x["reached"])
        print(f"    {len(rows)} replayed; {nr} reached +1R "
              f"({100.0*nr/len(rows):.1f}%), {len(rows)-nr} died before it")
        show(scope, "BY TIME TO +1R (15m bars)", rows, "t_1R", [8, 24, 72, 200])
        print()
        show(scope, "BY MAE BEFORE +1R (R, negative)", rows, "mae",
             [-0.9, -0.6, -0.3, -0.1])
        print()
        show(scope, "BY RATCHET LOCKED AT +1R (R)", rows, "r_1R",
             [0.0, 0.1, 0.25, 0.5])
        print()
    print("=" * 92)
    print("  READ: if the P(10R+) column is flat, +1R is uninformative and")
    print("  the runner is visible only in hindsight.")
    print("=" * 92)


if __name__ == "__main__":
    main()
