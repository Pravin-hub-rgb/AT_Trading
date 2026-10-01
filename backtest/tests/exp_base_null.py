"""P5 - THE BASE-BOOK NULL. How big must dNet be to mean anything?

THE QUESTION EVERY RESULT IN THIS REPO HAS BEEN SCORED AGAINST WITHOUT
ASKING IT
=====================================================================
`+325.8R` and `+70.1R` are called "the champion". Every pass in the
registry is a dNet against those. But no experiment has ever established
what dNet has to be for that to be more than luck. So this computes M:
the |dNet| at which a reshuffle of the champion's own trades would
produce the same number 95% of the time.

If M > the champion's own OOS net, then the champion is statistically
indistinguishable from a reordering of itself, and NO OOS pass in this
repo should be believed. That is the uncomfortable output and it gets
published either way.

METHOD, and why block bootstrap and not shuffle
=============================================
A plain shuffle destroys the one thing that matters here. `IS_IT_RIGHT.md`
already reports OOS ACF lag-1 = +0.498, and the champion's own trades are
serial: 500 IS trades containing a 30% win rate clustered into runs of
10R+ winners. A shuffle destroys that clustering, so it would UNDERSTATE
the null and make the book look better than it is. A MOVE-BLOCK
bootstrap preserves it.

Block length 20 trades, pre-registered to match the existing
`exp_montecarlo_dd.py` choice, resampling whole blocks of consecutive
trades with replacement until the trade count is restored. This preserves
within-block serial dependence, the win/loss run structure, the streak
process, and the trade count - all four, which a shuffle preserves none
of. 10,000 draws.

Reported per era, and BOTH tails, because the book is positive-skewed and
a one-sided test would be the wrong test:
  - the 95th percentile of |net| under the null  -> M
  - where the champion's own net sits in that distribution (its percentile)
  - the two-sided p-value

STEP 1 IS A PIN REPRODUCTION, ALWAYS
====================================
`CHAMPION_FLOOR_REJECTED.md` records that three experiments today were run
against a book that was not the champion, because the config and the
metric were guessed. This file does not guess them: it imports
`EXPERIMENTS["champion_multi_sw10"]` and `net_r()` directly, and refuses
to compute anything unless 500t/+325.8R and 279t/+70.1R come out.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
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
BLOCK = 20
DRAWS = 10_000
SEED = 20260928


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


def block_bootstrap_nets(rs, costs, block, draws, seed):
    """Resample BLOCKS of consecutive trades; keep count, cost pairing."""
    n = len(rs)
    nb = max(1, n // block)
    rng = random.Random(seed)
    out = []
    for _ in range(draws):
        idx = []
        for _ in range(nb):
            start = rng.randrange(0, n - block + 1) if n > block else 0
            idx.extend(range(start, start + block))
        out.append(sum(rs[i] for i in idx) - sum(costs[i] for i in idx))
    return sorted(out)


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 92)
    print("  P5  THE BASE-BOOK NULL   (what dNet has to clear to mean anything)")
    print("=" * 92)
    print(f"  config: champion_multi_sw10, engine=patched, metric=NET")
    print(f"  block bootstrap: block={BLOCK} trades, {DRAWS:,} draws, seed={SEED}")
    print("  preserves: trade count, within-block serial dependence, run/streak\n")

    sim = build_module()
    res = {}
    for scope in ("is", "oos"):
        print("-" * 92)
        a = load(scope)
        tr = [t for t in sim(*a, **PARAMS)["ltf_trades"]
              if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got_net = net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got_net - want_net) <= 1.0
        print(f"  [{scope}] PIN: n={len(tr)} netNET={got_net:+.1f}  "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing to compute a null against the wrong book.")
            return
        res[scope] = tr

    print()
    print("=" * 92)
    print("  THE NULL")
    print("=" * 92)
    for scope in ("is", "oos"):
        tr = res[scope]
        g = SYMBOL_PARAMS["BTCUSDT"]
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        rs = [float(t["r_multiple"]) for t in tr]
        costs = [per] * len(tr)
        obs = net_r(tr)
        nulls = block_bootstrap_nets(rs, costs, BLOCK, DRAWS, SEED)
        absn = sorted(abs(x) for x in nulls)
        p95 = absn[int(0.95 * len(absn))]
        p05 = absn[int(0.05 * len(absn))]
        below = sum(1 for x in nulls if x >= obs)
        pct = 100.0 * below / len(nulls)
        print(f"  [{scope}]  n={len(tr)}  observed netNET = {obs:+.1f}R")
        print(f"    null |net|   p05 = {p05:6.1f}R    p95 = {p95:6.1f}R")
        print(f"    null net     mean = {sum(nulls)/len(nulls):+6.1f}R"
              f"    min = {nulls[0]:+7.1f}    max = {nulls[-1]:+7.1f}")
        print(f"    M (|net| the 95th pct of a reshuffle reaches) = {p95:.1f}R")
        print(f"    observed sits at the {pct:.1f}th percentile"
              f"   two-sided p ~ {2.0*min(pct,100-pct)/100.0:.3f}")
        verdict = ("INDISTINGUISHABLE from a reshuffle"
                   if abs(obs) <= p95 else
                   "clears the reshuffle null")
        print(f"    -> {verdict}")
        if abs(obs) <= p95:
            print(f"    *** {abs(obs):.1f}R <= M={p95:.1f}R. The book's own OOS/IS net")
            print(f"        is inside what a reordering of its own trades produces. ***")
        print()

    print("=" * 92)
    print("  M, TO CARRY FORWARD")
    print("=" * 92)
    print("  Every dNet in this repo must exceed these numbers before it")
    print("  counts. Publishing whichever way it lands.")


if __name__ == "__main__":
    main()
