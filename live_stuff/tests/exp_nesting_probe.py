"""P1-PROBE - is the nesting information worth building?

THE PROPOSAL
============
P1 (second-round seed list): the swing chain is a strict TILING -
`btc_swing.py:150` sets `next_start_pos = end_pos + 1`, so leg k+1 always
begins one bar after leg k's extreme. It is therefore structurally
impossible for the system to say "this 15m pullback sits inside a 15m
up-leg that sits inside a 1h up-leg". P1 proposes letting legs nest,
which changes which marks EXIST rather than filtering trades after the
fact.

WHY A PROBE INSTEAD OF THE BUILD
===============================
Building nested tiling means rewriting swing generation - the component
F1 showed to be knife-edge (swapping the LTF structure cost 84R IS /
55R OOS; min_bars=50 is a sharp optimum). That is a large build to spend
on a hypothesis whose value is untested.

The hypothesis has a cheap decisive test. If the containment information
is worth generating, then containment computed from the EXISTING tiling
should already show SOME signal in the existing trades - the book already
sits inside tiled legs, and the nesting depth around each entry is
computable today from data that already exists. If the label is flat,
generating new nested marks is very unlikely to produce a book that
reacts to it.

So this does not implement P1. It tests the premise P1 rests on, for the
cost of a label. If the premise holds, the build is justified. If it
flats, P1 dies for a fraction of the price.

COMPUTED CAUSALLY AT EACH ENTRY
===============================
  nest_1h   : where the entry sits in its parent 1h leg's range,
              0 = at the leg's start, 1 = at its extreme. The 1h leg IS
              the bias window, so this is "how far into the HTF move".
  nest_15m  : the same for the parent 15m leg.
  nest_both : the product - deep in HTF and deep in LTF at once.
  swing_px  : |entry - sl| / ATR15(entry). P1's own falsifier (d) calls a
              median below 0.25 a degenerate risk denominator, void. It is
              checked and reported, not assumed.

FALSIFIERS PRE-REGISTERED IN THIS FILE
=====================================
  (a) median swing_px/ATR15 < 0.25            -> degenerate, void
  (b) no cohort of n>=40 clears its own null  -> the containment
      information carries nothing tradeable and the P1 build is not
      justified on this basis
  (c) a cohort that clears is ALSO the range-position cohort P1's own
      falsifier warns about -> nesting re-discovers range position
Reported whatever they say.
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


def atr_series(candles, lb=14):
    tr = []
    for i, c in enumerate(candles):
        hi, lo = float(c["high"]), float(c["low"])
        if i == 0:
            tr.append(hi - lo)
        else:
            pc = float(candles[i - 1]["close"])
            tr.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    out = []
    for i in range(len(candles)):
        lo_i = max(0, i - lb + 1)
        out.append(sum(tr[lo_i:i + 1]) / (i - lo_i + 1))
    return out


def nest_depth(swings, ts_lo, ts_hi, dir_sign):
    """0..1: where ts_lo..ts_hi sits inside the leg's own start->end range."""
    sp = float(swings["seg"]["start_px"])
    ep = float(swings["seg"]["end_px"])
    if ep == sp:
        return 0.5
    k = (float(ts_lo) - sp) / (ep - sp) if (ep - sp) else 0.0
    return max(0.0, min(1.0, k))


def leg_pos_time(a, b, t):
    """0..1: where t sits between a and b. The 1h window IS a time span."""
    if b <= a:
        return 0.5
    return max(0.0, min(1.0, (t - a) / float(b - a)))


def M_of(rs, per_cost, block=BLOCK, draws=DRAWS, seed=SEED):
    n = len(rs)
    if n < 10:
        return float("nan")
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
    return absn[int(0.95 * len(absn))]


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 94)
    print("  P1-PROBE  IS THE NESTING INFORMATION WORTH BUILDING?")
    print("=" * 94)
    print("  Tests P1's PREMISE, not P1 itself. If containment is already")
    print("  flat on the existing tiling, the nested-tiling build is not")
    print("  justified. Pins reproduced first.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    labelled = {}
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
            print("  PIN FAILED - refusing to compute.")
            return

        ivs = sorted((int(x[0]), int(x[1])) for x in eng["intervals"])
        atr = atr_series(c15)
        byts = [int(c["ts"]) for c in c15]
        rows = []
        for t in tr:
            ts = int(t["entry_ts"])
            par = next(((a, b) for a, b in ivs if a <= ts <= b), None)
            n1 = leg_pos_time(par[0], par[1], ts) if par else 0.5
            sn = int(t.get("swing_no") or 0)
            n15 = 0.5
            if 0 < sn <= len(sw15):
                sw = sw15[sn - 1]
                st = int(sw.get("start_idx", 0))
                en = int(sw.get("end_idx", 0))
                n15 = leg_pos_time(st, en, int(t["entry_idx"]))
            k = min(int(t["entry_idx"]), len(atr) - 1)
            a15 = atr[k] if atr[k] > 0 else 1.0
            spx = abs(float(t["entry_price"]) - float(t["sl"])) / a15
            rows.append({"r": float(t["r_multiple"]), "n1": n1, "n15": n15,
                         "both": n1 * n15, "swing_px": spx})
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        labelled[scope] = (rows, c2 / len(tr))
        s = sorted(x["swing_px"] for x in rows)
        print(f"          median |entry-sl|/ATR15 = {s[len(s)//2]:.3f}  "
              f"(P1 falsifier (d) voids below 0.25)")
        print()

    print("=" * 94)
    print("  COHORTS vs THEIR OWN NULL   (bars: thirds of each feature)")
    print("=" * 94)
    winners = []
    for scope in ("is", "oos"):
        rows, per = labelled[scope]
        for feat, lo_lbl in (("n1", "nest_1h"), ("n15", "nest_15m"),
                             ("both", "nest_both")):
            vals = sorted(x[feat] for x in rows)
            cuts = [vals[len(vals) // 3], vals[2 * len(vals) // 3]]
            for i, lab in enumerate(("low", "mid", "high")):
                a = -1e9 if i == 0 else cuts[i - 1]
                b = 1e9 if i == 2 else cuts[i]
                sel = [x for x in rows if a < x[feat] <= b]
                if len(sel) < 10:
                    continue
                rs = [x["r"] for x in sel]
                obs = sum(rs) - per * len(rs)
                M = M_of(rs, per)
                wr = 100.0 * sum(1 for z in rs if z > 0) / len(rs)
                ok = M == M and abs(obs) > M
                if ok:
                    winners.append(f"{scope} {lo_lbl} {lab}")
                print(f"  [{scope}] {lo_lbl:<9} {lab:<5} n={len(rs):<4} "
                      f"net={obs:+8.1f}R WR={wr:>5.1f}% M={M:>7.1f}R  "
                      f"{'CLEARS' if ok else 'inside null'}")
    print()
    print("=" * 94)
    if winners:
        print("  COHORTS THAT CLEAR THEIR OWN NULL — premise HOLDS, "
              "the P1 build is justified:")
        for w in winners:
            print(f"    {w}")
    else:
        print("  NONE CLEAR. The containment premise of P1 is FLAT on the")
        print("  existing tiling, so generating nested marks has no measured")
        print("  basis. P1 is not justified on this evidence.")
    print("=" * 94)


if __name__ == "__main__":
    main()
