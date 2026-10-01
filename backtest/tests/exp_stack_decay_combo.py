"""P28 - STACK x decay. The two candidates have never been combined.

WHY THIS COMBINATION IS NEW
===========================
`decay<0.75` is an ENTRY filter: it refuses trades whose buying structure
is already broken. `half+delay1` is an EXIT change: it stops ratcheting
the stop until the trade has run 1R, and moves the ratchet only halfway.
They act on opposite ends of the same trade, and every experiment to date
has tested one or the other:

    P11/P15  decay alone           (entry)
    P23      decay alone, swept    (entry)
    P24      decay directional/1h  (entry)
    P26      decay under permutation null (entry)
    P27      half+delay1 paired    (exit)
    log 113  half+delay1 + skip_decisive (exit)

If the exit rule is rescuing trades that decay would have refused, the two
overlap and the combination should be worth less than the sum. If they are
catching different things, the combination should beat both. **That is a
real question with a real answer either way, and it is the last cell
anyone has left untested.**

ARMS
====
  A  baseline
  B  decay<0.75                    (entry only)
  C  half+delay1                   (exit only)
  D  STACK (half+delay1+skipD)     (the documented #1)
  E  decay<0.75 + half+delay1      (the untested cell)
  F  decay<0.75 + STACK            (all three)

P27 already showed the exit effect does not clear a paired block
bootstrap and that a large share of STACK's headline is `skip_decisive`
acting on 57 OOS trades. So E is the honest version of the combination and
D/F are printed for completeness rather than as the recommendation.

Every cell is scored with the same paired block bootstrap on the
per-trade differences against baseline, block 20, 10,000 draws.
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
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import legs_by_dir, decay_pair  # noqa: E402
from exp_stack_paired import block_boot_p, pf, dd  # noqa: E402

BLOCK, DRAWS, SEED = 20, 10_000, 20260929
HALF_D1 = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
STACK = dict(exp_trail_half=1, exp_trail_delay_r=1.0,
             exp_skip_decisive=1)
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


def key(t):
    return (int(t["entry_ts"]), t["dir"])


def main():
    print("=" * 100)
    print("  P28  STACK x DECAY  -  entry filter and exit change, together")
    print("=" * 100)
    print(f"  decay<{THR} (n={NLEG} 15m legs) x {{half+delay1, STACK}}")
    print("  Every arm scored by paired block bootstrap on the per-trade")
    print(f"  differences vs baseline. block={BLOCK} draws={DRAWS}\n")

    for key_, swtag, ispin, oospin in LANES:
        if key_ not in EXPERIMENTS:
            print(f"  --- {key_}: NOT IN REGISTRY, skipped")
            continue
        params = {**BP, **EXPERIMENTS[key_]["params"]}
        sim = tc.build_module()
        print(f"  --- {key_}")
        for scope, pin in (("is", ispin), ("oos", oospin)):
            c1h, sw10, c15, sw15, fine = load(scope, swtag)

            def run(extra):
                r = sim(c1h, sw10, c15, sw15, fine, **params, **extra)
                return [t for t in r["ltf_trades"]
                        if t.get("outcome") != "open"]

            base = run({})
            h1 = run(HALF_D1)
            st = run(STACK)
            nb = net_r(base)

            # decay is an ENTRY-time feature, unaffected by which exit
            # produced the trade: compute it once per entry instant.
            up, dn = legs_by_dir(sw15)
            fts = [int(c["ts"]) for c in fine]
            flo = [float(c["low"]) for c in fine]
            fhi = [float(c["high"]) for c in fine]
            dec = {}
            for t in base:
                v, _ = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi,
                                  fts, n=NLEG)
                dec[key(t)] = 0.5 if v is None else v

            def keep(t):
                return dec.get(key(t), 0.5) < THR

            arms = {
                "A baseline": base,
                f"B decay<{THR}": [t for t in base if keep(t)],
                "C half+delay1": h1,
                "E decay + half+d1": [t for t in h1 if keep(t)],
                "D STACK": st,
                f"F decay + STACK": [t for t in st if keep(t)],
            }
            bmap = {key(t): float(t["r_multiple"]) for t in base}
            ok = ("PIN ok" if abs(nb - pin[1]) <= 2 and
                  abs(len(base) - pin[0]) <= 2 else "PIN MISS")
            print(f"    [{scope}] baseline {len(base)}t {nb:+.1f}R  ({ok})")
            for lbl, tl in arms.items():
                rs = [float(t["r_multiple"]) for t in tl]
                net = net_r(tl)
                tmap = {key(t): float(t["r_multiple"]) for t in tl}
                shared = [k for k in bmap if k in tmap]
                d = [tmap[k] - bmap[k] for k in sorted(shared)]
                obs, p = block_boot_p(d, DRAWS, random.Random(SEED))
                pv = "  n/a " if p is None else f"{p:5.3f}"
                star = "*" if (p is not None and p < 0.05) else " "
                print(f"      {lbl:<20} {len(tl):>4}t {net:>+8.1f}R "
                      f"dNet {net-nb:>+7.1f}R  PF {pf(rs):>4.2f} "
                      f"DD {dd(rs):>5.1f}  p={pv}{star} "
                      f"(paired n={len(d)})")
            print()
    print("  * = clears a paired block bootstrap at p<0.05. No arm is")
    print("    adopted here; this is the last untried cell, not a verdict.")


if __name__ == "__main__":
    main()
