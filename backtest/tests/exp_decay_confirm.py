"""P30 - THE USER'S NEW THESIS: decay as CONFIRMATION, not as a block.

THE THESIS, STATED BACK SO IT CAN BE CHECKED
=============================================
"buying swing low breaking is sign of good selling side participation. agar
htf bhi selling bias hai toh we should take them"

"htf buying toh selling swing ke high break honge... jab hoga tabhi hum
buying position lenge. aur jab htf selling hai toh agar is bar buying ke
lows break honge toh hi hum selling position lenge"

So the rule is not "broken structure = bad trade". It is:

    take the trade when the OPPOSITE side's structure is breaking

    HTF window LONG  -> take LONG  when SELLING legs' highs break
    HTF window SHORT -> take SHORT when BUYING  legs' lows break

This is the mirror used as a POSITIVE selector rather than a negative one.
Every decay experiment to date used buying-decay as a BLOCK, which asks
"is my own side failing?" - and this asks "is the other side failing?",
which is the opposite question and has never been asked.

Note the engine guarantees the trade direction already equals the HTF
window direction (`if sig["dir"] != d: continue`), so the trade's own
direction IS the window direction. No extra join is needed.

ARMS
====
  A  baseline
  B  decay<0.75 buying-side, blocks both     (the incumbent, P15)
  C  decay<0.75 selling-side only, blocks both (mirror, never run alone)
  D  CONFIRM, opposite side   HTF LONG  & selling decay high -> take
                              HTF SHORT & buying  decay high -> take
  E  CONFIRM, own side       HTF LONG  & buying  decay high -> take
                              HTF SHORT & selling decay high -> take
  F  FLIP                    HTF LONG  & buying  decay high -> take SHORT
                              HTF SHORT & selling decay high -> take LONG

D is the user's thesis as stated. E is the same construction on the other
pairing, printed because it costs nothing and distinguishes "confirms
direction" from "confirms opposite side". F is the explicit flip.

Everything is causal: both components are computed from legs confirmed at
or before the entry and 1m bars up to the entry. Nothing is adopted here.
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
from exp_stack_paired import pf, dd  # noqa: E402

NLEG, THR = 4, 0.75
DRAWS, SEED = 10_000, 20260929
BLOCK = 20

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
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


def boot_p(d):
    """paired block bootstrap p on the differences"""
    import numpy as np
    n = len(d)
    if n < 2 * BLOCK:
        return None
    obs = float(sum(d))
    a = np.asarray(d, dtype=np.float64)
    cs = np.concatenate(([0.0], np.cumsum(a)))
    st = np.arange(0, n - BLOCK + 1)
    nb = n // BLOCK
    rs = np.random.RandomState(SEED)
    tot = cs[st + BLOCK] - cs[st]
    s = tot[rs.randint(0, len(st), size=(DRAWS, nb))].sum(axis=1)
    s = s + a[nb * BLOCK:].sum()
    return float((s >= obs - 1e-9).mean())


def main():
    print("=" * 100)
    print("  P30  DECAY AS CONFIRMATION  -  the user's thesis, as stated")
    print("=" * 100)
    print(f"  n={NLEG} 15m legs, thr={THR}.  The engine already forces")
    print("  trade direction == HTF window direction, so the trade's own")
    print("  direction IS the window direction.\n")

    for key_, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key_]["params"]}
        sim = tc.build_module()
        print(f"  --- {key_}")
        for scope, pin in (("is", ispin), ("oos", oospin)):
            c1h, sw10, c15, sw15, fine = load(scope, swtag)
            r = sim(c1h, sw10, c15, sw15, fine, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb = net_r(tr)
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
            L = {k for k in U if tr[0] and True}

            def sel(fn):
                return [t for t in tr if fn(U[key(t)], V[key(t)],
                                            t["dir"] == "long")]

            arms = {
                "A baseline": tr,
                f"B buy-block <{THR}":
                    sel(lambda u, v, ln: u < THR),
                f"C sell-block <{THR}":
                    sel(lambda u, v, ln: v < THR),
                f"D CONFIRM opposite":
                    sel(lambda u, v, ln: (v >= THR) if ln else (u >= THR)),
                f"E CONFIRM own":
                    sel(lambda u, v, ln: (u >= THR) if ln else (v >= THR)),
                "F both sides high":
                    sel(lambda u, v, ln: u >= THR and v >= THR),
            }
            bmap = {key(t): float(t["r_multiple"]) for t in tr}
            ok = ("PIN ok" if abs(nb - pin[1]) <= 2 and
                  abs(len(tr) - pin[0]) <= 2 else "PIN MISS")
            print(f"    [{scope}] baseline {len(tr)}t {nb:+.1f}R  ({ok})")
            for lbl, tl in arms.items():
                if len(tl) < 20:
                    print(f"      {lbl:<22} {len(tl):>4}t  (too few)")
                    continue
                rs = [float(t["r_multiple"]) for t in tl]
                net = net_r(tl)
                tmap = {key(t): float(t["r_multiple"]) for t in tl}
                sh = [k for k in bmap if k in tmap]
                p = boot_p([tmap[k] - bmap[k] for k in sorted(sh)])
                pv = "  n/a" if p is None else f"{p:5.3f}"
                st = "*" if (p is not None and p < 0.05) else " "
                print(f"      {lbl:<22} {len(tl):>4}t {net:>+8.1f}R "
                      f"dNet {net-nb:>+7.1f}R  PF {pf(rs):>4.2f} "
                      f"DD {dd(rs):>5.1f}  p={pv}{st}")
            print()
    print("  * = paired block bootstrap p<0.05. Nothing adopted.")


if __name__ == "__main__":
    main()

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)
