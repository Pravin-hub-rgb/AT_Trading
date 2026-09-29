"""P8 - WHICH DECOMPOSITION OF THE CHAMPION CLEARS ITS OWN NULL?

WHY THIS EXISTS
===============
P5 established the uncomfortable result: the champion's net R sits at the
46th/48th percentile of a reshuffle of itself, and M = 479.9R IS / 193.4R
OOS is the bar every dNet must clear. P5-SENS confirmed M is a property of
the book, not of the block length.

That is a statement about ONE statistic on 500 trades. It is NOT a
statement that nothing in the book is real. A heavy-tailed book has an
enormous reshuffle variance for its NET, but its sub-parts may have much
tighter nulls, and a component that clears its own null is a component
worth trading even if the total does not clear the total's.

The repo already computes three such decompositions and has never checked
any of them against a null:
  - per calendar year  (removes regime drift)
  - per HTF regime     (champion's htf_regime field: flip / b2)
  - ex-best-5          (removes the tail concentration that the whole
                        repo's autopsies keep landing on)

So: split the champion three ways, give each split its OWN block-bootstrap
null built from that split's own trade sequence, and report which splits
clear. The null is per-split, not shared - a 2023 book should not be
judged by a 2025 book reshuffle.

This is the direct, useful consequence of P5. Not "the book is luck" but
"here is the part that is not, if any." And it is the statistic that
could survive into a live rule.

METHOD
======
Same move-block bootstrap as P5 (preserves serial dependence, run
structure, streak), block=20, 10,000 draws, seed fixed. Per split, per
era:
  - M_split = 95th percentile of |net| under a reshuffle of THAT split
  - observed net of that split
  - does observed > M_split ?
Reported for every split including the whole book, so the components are
read against the total on the same scale.

Pins reproduced first, as always. Nothing here is accepted or rejected -
it is a map of where the book is solid, which is the input to every
future decision about it.
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
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

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}
BLOCK, DRAWS, SEED = 20, 10_000, 20260928


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


def M_of(rs, per_cost, block=BLOCK, draws=DRAWS, seed=SEED):
    """95th pct of |net| under a move-block reshuffle of this sequence."""
    n = len(rs)
    if n < 10:
        return float("nan"), float("nan")
    nb = max(1, n // block)
    span = max(1, n - block + 1)
    rng = random.Random(seed)
    nets = []
    for _ in range(draws):
        tot = 0.0
        for _ in range(nb):
            s = rng.randrange(0, span) if n > block else 0
            for i in range(s, s + block):
                tot += rs[i] - per_cost
        nets.append(tot)
    absn = sorted(abs(x) for x in nets)
    return absn[int(0.95 * len(absn))], sum(nets) / len(nets)


def report(name, tr, per_cost):
    rs = [float(t["r_multiple"]) for t in tr]
    obs = sum(rs) - per_cost * len(tr)
    n = len(rs)
    M, mean = M_of(rs, per_cost)
    clears = "CLEARS" if (M == M and abs(obs) > M) else "inside null"
    wr = 100.0 * sum(1 for x in rs if x > 0) / max(n, 1)
    print(f"    {name:<18} n={n:<4} net={obs:+8.1f}R  WR={wr:>5.1f}%  "
          f"M={M:>7.1f}R  nullmean={mean:+8.1f}R  {clears}")
    return clears == "CLEARS"


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 96)
    print("  P8  WHICH DECOMPOSITION CLEARS ITS OWN NULL?")
    print("=" * 96)
    print("  Each split gets its OWN move-block null from its own trades.")
    print("  Whole-book row included so splits read against the total.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    winners = []
    for scope in ("is", "oos"):
        a = load(scope)
        tr = [t for t in sim(*a, **PARAMS)["ltf_trades"]
              if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got = net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got - want_net) <= 1.0
        print(f"  [{scope}] PIN n={len(tr)} netNET={got:+.1f} "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing to compute.")
            return
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        print(f"\n  [{scope}] WHOLE BOOK")
        report("all", tr, per)

        # --- split 1: calendar year -------------------------------
        print(f"  [{scope}] BY CALENDAR YEAR (of exit)")
        byy = defaultdict(list)
        for t in tr:
            y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
            byy[y].append(t)
        for y in sorted(byy):
            if report(f"  {y}", byy[y], per):
                winners.append(f"{scope} year {y}")

        # --- split 2: HTF regime ------------------------------------
        print(f"  [{scope}] BY HTF REGIME")
        byr = defaultdict(list)
        for t in tr:
            byr[t.get("htf_regime", "?")].append(t)
        for k in sorted(byr):
            if report(f"  {k}", byr[k], per):
                winners.append(f"{scope} regime {k}")

        # --- split 3: ex-best-5 ------------------------------------
        print(f"  [{scope}] TAIL REMOVED (ex-best-5)")
        rs = sorted(tr, key=lambda t: -float(t["r_multiple"]))
        ex5 = rs[5:]
        if report("  ex-best-5", ex5, per):
            winners.append(f"{scope} ex-best-5")
        print(f"    (top 5 were "
              f"{sum(float(t['r_multiple']) for t in rs[:5]):+.1f}R of "
              f"{sum(float(t['r_multiple']) for t in tr):+.1f}R gross)\n")

    print("=" * 96)
    print("  SPLITS THAT CLEAR THEIR OWN NULL")
    print("=" * 96)
    if winners:
        for w in winners:
            print(f"    {w}")
    else:
        print("    NONE. Not one decomposition beats a reshuffle of itself.")
    print("=" * 96)


if __name__ == "__main__":
    main()
