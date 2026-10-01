"""P5-SENS - is M = 479.9R / 193.4R a property of the book, or of BLOCK=20?

WHY THIS FILE IS THE PRIORITY
=============================
P5 produced the most consequential number in the repo: the champion's own
net sits at the 46th/48th percentile of a reshuffle of itself, so every
dNet must clear M = 479.9R IS / 193.4R OOS before it counts. That rests on
ONE methodological choice - block length 20, pre-registered to match
exp_montecarlo_dd.py rather than derived. If M moves materially with block
length, the bar every result is scored against is arbitrary.

This is the cheapest possible test of the most important number in the
repo, and the honest thing to do immediately after publishing M rather
than a year later.

THE TRADE-OFF BEING MEASURED, NOT ASSUMED
=========================================
  block TOO SHORT -> preserves little serial structure, null collapses
                     toward the iid case, M understates
  block TOO LONG  -> resamples nearly the whole series as one unit, the
                     bootstrap degenerates and the null loses meaning

Reported: M at every block length, plus the null's mean and spread, so the
shape of the dependence is visible rather than asserted. A plateau means
block=20 is fine and the conclusion hardens. A cliff means the conclusion
needs a caveat proportional to its width.
"""
from __future__ import annotations

import random
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
DRAWS = 10_000
SEED = 20260928
BLOCKS = [5, 10, 15, 20, 30, 40, 60, 90]


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


def null_stats(rs, per_cost, block, draws=DRAWS, seed=SEED):
    """Move-block bootstrap. Returns M, mean, p05|net|, 2.5%, 97.5%."""
    n = len(rs)
    nb = max(1, n // block)
    span = max(1, n - block + 1)
    rng = random.Random(seed)
    nets = []
    for _ in range(draws):
        tot = 0.0
        for _ in range(nb):
            start = rng.randrange(0, span) if n > block else 0
            for i in range(start, start + block):
                tot += rs[i] - per_cost
        nets.append(tot)
    nets.sort()
    absn = sorted(abs(x) for x in nets)
    return (absn[int(0.95 * len(absn))], sum(nets) / len(nets),
            absn[int(0.05 * len(absn))],
            nets[int(0.025 * len(nets))], nets[int(0.975 * len(nets))])


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 96)
    print("  P5-SENS  IS M A PROPERTY OF THE BOOK, OR OF BLOCK=20?")
    print("=" * 96)
    print(f"  M at block=20 was 479.9R IS / 193.4R OOS.")
    print(f"  blocks: {BLOCKS}   draws: {DRAWS:,}   seed: {SEED}\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    books = {}
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
        books[scope] = ([float(t["r_multiple"]) for t in tr], c2 / len(tr), got)
    print()

    for scope in ("is", "oos"):
        rs, per_cost, obs = books[scope]
        print("-" * 96)
        print(f"  [{scope}]  n={len(rs)}  observed netNET = {obs:+.1f}R")
        print(f"  {'block':>6}  {'M':>10}  {'null mean':>10}  "
              f"{'p05|net|':>9}  {'2.5%':>9}  {'97.5%':>9}")
        rows = []
        for b in BLOCKS:
            M, mean, p05, lo, hi = null_stats(rs, per_cost, b)
            rows.append((b, M))
            print(f"  {b:>6}  {M:>9.1f}R  {mean:>+9.1f}R  {p05:>8.1f}R  "
                  f"{lo:>+8.1f}R  {hi:>+8.1f}R")
        ms = [r[1] for r in rows]
        lo_, hi_ = min(ms), max(ms)
        base = dict(rows).get(20)
        print(f"  -> M spans {lo_:.1f}R .. {hi_:.1f}R  "
              f"(x{hi_/max(lo_,1e-9):.2f} across block lengths)")
        if base:
            print(f"  -> M(block=20)={base:.1f}R. Block choice moves the bar "
                  f"by up to {100.0*(hi_-lo_)/base:.0f}% of its own value.")
        verdict = ("STABLE - a plateau, so block=20 is a defensible choice "
                   "and the M finding hardens"
                   if hi_ / max(lo_, 1e-9) < 1.5 else
                   "SENSITIVE - M is materially a methodological choice, "
                   "and the P5 conclusion needs that caveat")
        print(f"  -> {verdict}\n")


if __name__ == "__main__":
    main()
