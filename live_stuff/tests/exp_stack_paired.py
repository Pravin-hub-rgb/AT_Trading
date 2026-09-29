"""P27 - THE STACK, PROPERLY TESTED. The #1 candidate was never scored right.

WHAT I GOT WRONG, IN TWO PLACES
===============================
1. **I dismissed the exit family.** `SMOOTH_BOOK.md` says "the entire exit
   family is closed - trail/half/delay/tighten/partial are all rejected"
   and points at entry filters instead. That is **false**. `exp_trail_half`
   + `exp_trail_delay_r` + `exp_skip_decisive` (the STACK) is the single
   largest documented improvement in the repo: champion IS +325.8 -> +429.6
   with maxDD 27.7 -> 27.0, OOS +70.2 -> +110.5 with maxDD 53.2 -> 30.6.
   Log 113 reproduced it 24/24 and checklist 24.24 passed a retroactivity
   audit. Six entry-side experiments (P19-P24) then produced nothing that
   cleared any bar, and I concluded "the grid is exhausted". **The grid was
   never exhausted; I was looking on one side of the book.**

2. **`BASE_BOOK_NULL.md` scored it with the wrong test.** It took
   +103.8R IS dNet against `M` = 479.9R and called it "inside the null".
   But `M` is a move-block bootstrap of the book's own **level** - the right
   question for "is this book distinguishable from a reshuffle of itself",
   the wrong one for "did this change help". A change like this is a
   **paired** before/after on largely the same trades, and all the
   book-level variance that makes `M` 480R wide cancels in the pairing.

THE RIGHT TEST HERE
===================
Per trade, keep the pairing:

    d[i] = r_stack[i] - r_baseline[i]     for trades in both books

Then move-block bootstrap the **differences** d[] (block 20, preserving
serial dependence and streak structure) and ask
`p = P(sum(d*) >= sum(d))`. This keeps every hard-won property of the P5
method and removes the one thing that made it useless here: the level.

WHAT IS RUN
===========
  1. pins reproduced first, all three lanes, both eras
  2. decomposition - is the gain from FEWER trades, or better exits on the
     SAME trades? (the two are very different claims)
  3. paired block bootstrap on d[]
  4. STACK x decay<0.75 - the two candidates are on opposite sides of the
     book (exit vs entry) and have never been combined
  5. why age10 breaks: STACK takes it from +43.2R to -0.3R

`skip_decisive` is a perfect IS no-op on both multi lanes (0 decisive
trades in 2023-26) - all of its evidence is the 57 OOS trades it removes,
and that is stated rather than folded into the headline.
"""
from __future__ import annotations

import bisect as bs
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import legs_by_dir, decay_pair  # noqa: E402

BLOCK, DRAWS, SEED = 20, 10_000, 20260929
STACK = dict(exp_trail_half=1, exp_trail_delay_r=1.0,
             exp_skip_decisive=1)
HALF_D1 = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
THR, NLEG = 0.75, 4

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
    ("age10_dirmatch_swingpause_single_sw10", "sw10", (130, 435.7), (76, 43.2)),
)



def load(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def block_boot_p(d, draws, rng):
    """p = P(sum(d*) >= sum(d)) under a move-block bootstrap of d[].

    Block length BLOCK preserves the serial dependence, the win/loss run
    structure and the streak process - the same reason P5 blocked. The
    only thing that changes is that we resample the DIFFERENCES, so the
    book's own variance is differenced out instead of dominating.

    Vectorised: the pure-Python version was minutes per cell.
    """
    n = len(d)
    if n < 2 * BLOCK:
        return None, 0.0
    import numpy as np
    obs = float(sum(d))
    a = np.asarray(d, dtype=np.float64)
    csum = np.concatenate(([0.0], np.cumsum(a)))
    starts = np.arange(0, n - BLOCK + 1)
    nb = n // BLOCK
    rs = np.random.RandomState(SEED)
    tot = csum[starts + BLOCK] - csum[starts]          # block sums
    idx = rs.randint(0, len(starts), size=(draws, nb))
    s = tot[idx].sum(axis=1)
    tail = a[nb * BLOCK:].sum()
    s = s + tail
    return obs, float((s >= obs - 1e-9).mean())


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    eq = pk = d = 0.0
    for x in rs:
        eq += x
        pk = max(pk, eq)
        d = max(d, pk - eq)
    return d


def key(t):
    """Pair trades on entry instant + direction, which is invariant to the
    exit being changed. Returns a dict keyed by that pair."""
    return (int(t["entry_ts"]), t["dir"])


def main():
    print("=" * 100)
    print("  P27  THE STACK, SCORED WITH A PAIRED TEST (the correct one)")
    print("=" * 100)
    print(f"  STACK = exp_trail_half=1 + exp_trail_delay_r=1.0 "
          f"+ exp_skip_decisive=1")
    print(f"  block={BLOCK} draws={DRAWS}  p = P(sum(d*) >= sum(d)) on the")
    print("  per-trade DIFFERENCES. This is what BASE_BOOK_NULL should have")
    print("  used instead of the level.\n")

    for key_, swtag, ispin, oospin in LANES:
        if key_ not in EXPERIMENTS:
            print(f"  --- {key_}: NOT IN REGISTRY, skipped")
            continue
        params = {**BP, **EXPERIMENTS[key_]["params"]}
        sim = tc.build_module()
        print(f"  --- {key_}")
        for scope, pin in (("is", ispin), ("oos", oospin)):
            args = load(scope, swtag)

            def run(extra):
                r = sim(args[0], args[1], args[2], args[3], args[4],
                        **params, **extra)
                return [t for t in r["ltf_trades"]
                        if t.get("outcome") != "open"]

            base = run({})
            h1 = run(HALF_D1)
            st = run(STACK)
            nb, nh, ns = net_r(base), net_r(h1), net_r(st)
            ok = "PIN ok" if abs(nb - pin[1]) <= 2 and \
                abs(len(base) - pin[0]) <= 2 else \
                f"PIN MISS(want {pin[0]}/{pin[1]})"

            bm = {key(t): float(t["r_multiple"]) for t in base}
            sm = {key(t): float(t["r_multiple"]) for t in st}
            common = [k for k in bm if k in sm]
            d = [sm[k] - bm[k] for k in sorted(common)]
            only_b = [k for k in bm if k not in sm]
            only_s = [k for k in sm if k not in bm]

            obs, p = block_boot_p(d, DRAWS,
                                  random.Random(SEED))
            sb = [float(t["r_multiple"]) for t in base]
            ss = [float(t["r_multiple"]) for t in st]
            print(f"    [{scope}] base {len(base):>4}t {nb:>+8.1f}R  ({ok})")
            print(f"      half+delay1  {len(h1):>4}t {nh:>+8.1f}R  "
                  f"dNet {nh-nb:>+7.1f}R  DD {dd([float(t['r_multiple']) for t in h1]):>5.1f}")
            print(f"      STACK        {len(st):>4}t {ns:>+8.1f}R  "
                  f"dNet {ns-nb:>+7.1f}R  DD {dd(ss):>5.1f}  PF {pf(ss):>4.2f}")
            print(f"      paired: {len(d)} shared trades, sum(d) = "
                  f"{obs:+.1f}R   p = {p:.4f}  "
                  f"{'PASSES' if (p is not None and p < 0.05) else 'no'}")
            print(f"      dropped by STACK: {len(only_b)}   "
                  f"added by STACK: {len(only_s)}")
            if only_b:
                print(f"        dropped R = {sum(bm[k] for k in only_b):+.1f}R"
                      f"   added R = "
                      f"{sum(sm[k] for k in only_s) if only_s else 0.0:+.1f}R")
            print(f"      exit-only effect (shared trades) = "
                  f"{obs:+.1f}R   |   count effect = "
                  f"{ns - nb - obs:+.1f}R")
        print()


if __name__ == "__main__":
    main()
