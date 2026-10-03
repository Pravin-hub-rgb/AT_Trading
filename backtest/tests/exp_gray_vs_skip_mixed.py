"""P31 - THREE THINGS: true GRAY vs SKIP, and the mixed mirror.

PART 1 - GRAY vs SKIP, THE ACCOUNTING
=====================================
The user caught this: *"acha toh gray hai toh T jo hai woh 500T hi
rahega kabhi 300 something hoga hi nahi."* They are right, and P15 did not
do what its own docstring claimed.

P15's docstring says: "GRAY the signal. No new trade. No shift. Survivors
keep their own entry, exit and R." But a post-hoc list filter REMOVES the
trade from the book, so n fell 500 -> 307. That is a **SKIP**, not a gray.
A true gray keeps the trade, suppresses its P&L (r = 0), and still pays
its costs - you took the position, you just did not let it print.

    SKIP   net = sum(r_kept)                  - per * n_kept
    GRAY   net = sum(r_kept) + 0 * n_grayed   - per * n_all

The second line is the honest one and it has never been computed. This is
not a rounding difference: 193 trades' worth of fees and slippage.

PART 2 - THE MIXED MIRROR
=========================
P29 showed, on mean gross R of kept trades:

    LONG  side   one-sided +1.685   mirror +1.474
    SHORT side   one-sided +0.990   mirror +0.328

One-sided wins on BOTH sides, which predicts the mixed version is WORSE
than one-sided. That is a prediction, not a result, so it is run:

    M1  LONG judged by SELLING decay, SHORT by BUYING decay
    M2  LONG by BUYING, SHORT by SELLING   (the P24 direction arm, for
                                           comparison on the same footing)

Both reported next to the one-sided incumbent B.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import legs_by_dir, decay_pair  # noqa: E402
from exp_stack_paired import pf, dd  # noqa: E402

NLEG, THR = 4, 0.75

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (453, 279.5), (254, 66.9)),
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
    print("  P31  TRUE GRAY vs SKIP   +   THE MIXED MIRROR")
    print("=" * 100)
    print(f"  n={NLEG} 15m legs, thr={THR}\n")
    print("  GRAY keeps the trade at r=0 and STILL pays its cost.")
    print("  SKIP deletes it. P15 implemented SKIP while calling it GRAY.\n")

    for key_, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key_]["params"]}
        sim = tc.build_module()
        print(f"  --- {key_}")
        for scope, pin in (("is", ispin), ("oos", oospin)):
            c1h, sw10, c15, sw15, fine = load(scope, swtag)
            r = sim(c1h, sw10, c15, sw15, fine, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb = net_r(tr)
            n_all = len(tr)
            per = (sum(float(t["r_multiple"]) for t in tr) - nb) / n_all
            up, dn = legs_by_dir(sw15)
            fts = [int(c["ts"]) for c in fine]
            flo = [float(c["low"]) for c in fine]
            fhi = [float(c["high"]) for c in fine]
            U, V = {}, {}
            for t in tr:
                a, b = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi,
                                  fts, n=NLEG)
                U[key(t)] = 0.5 if a is None else a
                V[key(t)] = 0.5 if b is None else b

            ok = ("PIN ok" if abs(nb - pin[1]) <= 2 and
                  abs(n_all - pin[0]) <= 2 else "PIN MISS")
            print(f"    [{scope}] baseline {n_all}t {nb:+.1f}R  ({ok})")

            keep = [t for t in tr if U[key(t)] < THR]
            gray = [t for t in tr if U[key(t)] >= THR]
            rk = sum(float(t["r_multiple"]) for t in keep)
            skip_net = rk - per * len(keep)
            gray_net = rk - per * n_all
            gr = [float(t["r_multiple"]) for t in keep]
            print(f"      GRAY vs SKIP  (buying decay >= {THR} grays)")
            print(f"        SKIP  keep {len(keep):>3} drop {len(gray):>3}"
                  f"  net {skip_net:>+8.1f}R  dNet {skip_net-nb:>+7.1f}R"
                  f"  PF {pf(gr):>4.2f}  DD {dd(gr):>5.1f}")
            print(f"        GRAY  keep {len(keep):>3} gray {len(gray):>3}"
                  f"  net {gray_net:>+8.1f}R  dNet {gray_net-nb:>+7.1f}R"
                  f"  n stays {n_all}")
            print(f"        the {len(gray)} grayed trades cost "
                  f"{per*len(gray):+.1f}R in fees/slippage")

            def sel(fn):
                return [t for t in tr
                        if fn(U[key(t)], V[key(t)], t["dir"] == "long")]

            arms = {
                "B one-sided (buying)": sel(lambda u, v, ln: u < THR),
                "M1 LONG<-sell SHORT<-buy":
                    sel(lambda u, v, ln: (v < THR) if ln else (u < THR)),
                "M2 LONG<-buy SHORT<-sell":
                    sel(lambda u, v, ln: (u < THR) if ln else (v < THR)),
            }
            for lbl, tl in arms.items():
                if len(tl) < 20:
                    print(f"        {lbl:<26} {len(tl):>4}t  (too few)")
                    continue
                rs = [float(t["r_multiple"]) for t in tl]
                net = net_r(tl)
                print(f"        {lbl:<26} {len(tl):>4}t {net:>+8.1f}R  "
                      f"dNet {net-nb:>+7.1f}R  PF {pf(rs):>4.2f}  "
                      f"DD {dd(rs):>5.1f}")
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()
