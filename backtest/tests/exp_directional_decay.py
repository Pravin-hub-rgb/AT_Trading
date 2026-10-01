"""P24 - DIRECTIONAL DECAY, ON BOTH TIMEFRAMES. The user's two corrections.

TWO THINGS THE USER CAUGHT THAT NOBODY ELSE DID
===============================================
(1) DIRECTION. `decay<0.75` counts broken BUYING lows and then blocks the
    trade WHATEVER ITS SIDE. So a short taken while four buying legs are
    being broken gets blocked too - for a reason that has nothing to do
    with it. If buying structure is failing that is a LONG-side fact. The
    mirror test - selling legs broken -> block SHORTS - has never been
    run as a gate, only ever as a description (P18's asymmetric arm used
    the difference as a score, not as a side-specific block).

(2) TIMEFRAME. Every decay number in this repo is built from 15m legs.
    The 1h legs - the ones that actually decide direction and hold the
    window open - have never been through this calculation at all. The
    1h structure is the parent of the 15m structure; if the parent is
    broken, "how many of the last four buying legs broke" is a local
    detail measured inside a parent that is already failing.

ARMS
====
  A  control                        500 / 279
  B  15m BOTH sides   (P15)         the current rule: 15m buying-decay
                                    blocks longs AND shorts
  C  15m DIRECTIONAL   (NEW)         broken BUYING legs block LONGS only;
                                    broken SELLING legs block SHORTS only
  D  1h  BOTH sides   (NEW tf)      same rule, legs from the 1h chain
  E  1h  DIRECTIONAL   (NEW tf)     both new things at once
  F  15m AND 1h (consensus)         a trade must pass on BOTH chains

C, D, E, F are the untested cells. B is the incumbent and is the bar they
must beat. Decay on 1h legs uses 1h candles to test whether an 1h leg's
own extreme was broken - all data at or before the entry, so causality is
identical to the 15m version and is not re-argued here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import PARAMS, legs_by_dir, decay_pair  # noqa: E402

THR = 0.75
N15, N1H = 4, 4
M_IS, M_OOS = 479.9, 193.4



def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    eq = pk = d = 0.0
    for x in rs:
        eq += x
        pk = max(pk, eq)
        d = max(d, pk - eq)
    return d


def streak(rs):
    cur = mx = 0
    for x in rs:
        cur = cur + 1 if x < 0 else 0
        mx = max(mx, cur)
    return mx


def main():
    print("=" * 100)
    print("  P24  DIRECTIONAL DECAY + THE 1h CHAIN  (both untested)")
    print("=" * 100)
    print(f"  thr={THR}  n15={N15}  n1h={N1H}   M: IS {M_IS}R / OOS {M_OOS}R")
    print("  B blocks BOTH sides (the incumbent).  C/E block only the side")
    print("  whose own structure broke.\n")

    ARMS = ("B 15m both", "C 15m DIRECT", "D 1h both",
            "E 1h DIRECT", "F 15m AND 1h")

    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        sim = tc.build_module()
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **PARAMS)
        tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
        base = net_r(tr)
        per = (sum(float(t["r_multiple"]) for t in tr) - base) / len(tr)
        M = M_IS if scope == "is" else M_OOS
        print(f"  --- {scope.upper()}   control n={len(tr)}  net={base:+.1f}R")

        up15, dn15 = legs_by_dir(sw15)
        up1h, dn1h = legs_by_dir(sw10)
        fts = [int(c["ts"]) for c in fine]
        flo = [float(c["low"]) for c in fine]
        fhi = [float(c["high"]) for c in fine]
        hts = [int(c["ts"]) for c in c1h]
        hlo = [float(c["low"]) for c in c1h]
        hhi = [float(c["high"]) for c in c1h]

        keep = {k: [] for k in ARMS}
        for t in tr:
            ts = int(t["entry_ts"])
            lng = t["dir"] == "long"
            u15, d15 = decay_pair(up15, dn15, ts, flo, fhi, fts, n=N15)
            u1h, d1h = decay_pair(up1h, dn1h, ts, hlo, hhi, hts, n=N1H)
            u15 = 0.5 if u15 is None else u15
            d15 = 0.5 if d15 is None else d15
            u1h = 0.5 if u1h is None else u1h
            d1h = 0.5 if d1h is None else d1h
            keep["B 15m both"].append(u15 < THR)
            keep["C 15m DIRECT"].append((d15 if not lng else u15) < THR)
            keep["D 1h both"].append(u1h < THR)
            keep["E 1h DIRECT"].append((d1h if not lng else u1h) < THR)
            keep["F 15m AND 1h"].append((d15 if not lng else u15) < THR
                                         and (d1h if not lng else u1h) < THR)

        print(f"\n    {'arm':<13} {'n':>4} {'net':>9} {'dNet':>8} {'WR':>6} "
              f"{'PF':>5} {'DD':>6} {'strk':>5} {'R/tr':>6}  vs M")
        for k in ARMS:
            rs = [float(t["r_multiple"]) for t, ok in zip(tr, keep[k]) if ok]
            if len(rs) < 30:
                print(f"    {k:<13} {len(rs):>4}   (too few)")
                continue
            net = sum(rs) - per * len(rs)
            d = net - base
            print(f"    {k:<13} {len(rs):>4} {net:>+9.1f} {d:>+8.1f} "
                  f"{100.0*sum(1 for x in rs if x>0)/len(rs):>5.1f}% "
                  f"{pf(rs):>5.2f} {dd(rs):>6.1f} {streak(rs):>5} "
                  f"{sum(rs)/len(rs):>+6.2f}  "
                  f"{'INSIDE M' if abs(d) < M else 'CLEARS M'}")
    print()


if __name__ == "__main__":
    main()
