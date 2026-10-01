"""P23 - HOW MANY SWINGS? The decay lookback was never justified.

THE USER'S QUESTION, AND IT IS THE RIGHT ONE
============================================
"yeh decay kitne recents hai cluttered hai toh better may be or not aisa
kuch karo nah yaar, kitne lookback swing etc etc waha par cap aisa kuch,
yaar sab mai he karra hu variation kitne hai karo nah yaar kuch"

N_SWINGS = 4 is a constant in `decay_pair()` (exp_decay_switch.py:139). It
was never derived, never swept, and never justified. The whole `decay<0.75`
story - and the 2025 regression that nearly buried the user's own idea -
rests on that one arbitrary integer.

So sweep it. If the result is FLAT across lookbacks then 4 was arbitrary
and the whole decay family is noise, which is a real and useful answer.
If some lookback is dramatically better that is MORE suspicious, not less:
it means the family was selected best-of-N.

WHAT IS SWEPT
=============
    n       2, 3, 4, 5, 6, 8, 10, 12   (legs of lookback)
    thr     0.25 0.4 0.5 0.6 0.75 0.9   (the "how broken" gate)

Reported per arm, both eras: n, NET, WR, PF, DD, R/trade, and the year
count that clears the champion's own year (P16's floor, the only thing that
ever killed a decay arm).

M NULL
======
P5 established the noise band: IS dNet must exceed 479.9R, OOS 193.4R. A
dNet inside that is not a finding. It is printed per arm so the size of
these numbers is visible rather than implied.

Causality is NOT re-litigated: `decay_pair` reads only legs confirmed at or
before t and only 1m bars up to t. Varying `n` adds no future information.
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

LOOKBACKS = (2, 3, 4, 5, 6, 8, 10, 12)
THRESH = (0.25, 0.4, 0.5, 0.6, 0.75, 0.9)
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


def yr(rs, ys):
    o = {}
    for r, y in zip(rs, ys):
        o.setdefault(y, 0.0)
        o[y] += r
    return o


def main():
    print("=" * 100)
    print("  P23  HOW MANY SWINGS?  -  N_SWINGS=4 was never justified")
    print("=" * 100)
    print(f"  M (P5 noise band): IS dNet > {M_IS}R   OOS dNet > {M_OOS}R")
    print("  A dNet inside M is not a finding.\n")

    D = {}
    for sc in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(sc)
        eng = tc.build_module()
        r = eng(c1h, sw10, c15, sw15, fine_ltf=fine, **PARAMS)
        tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
        fts = [int(c["ts"]) for c in fine]
        flo = [float(c["low"]) for c in fine]
        fhi = [float(c["high"]) for c in fine]
        ups, dns = legs_by_dir(sw15)
        D[sc] = (tr, ups, dns, flo, fhi, fts, net_r(tr))
        print(f"  [{sc}] control n={len(tr)}  netNET={D[sc][6]:+.1f}R")

    for sc in ("is", "oos"):
        tr, ups, dns, flo, fhi, fts, base = D[sc]
        M = M_IS if sc == "is" else M_OOS
        base_yr = yr([float(t["r_multiple"]) for t in tr],
                     [t["exit_date"][:4] for t in tr])
        print(f"\n  --- {sc.upper()}  champion by year: " +
              "  ".join(f"{k}:{v:+.1f}" for k, v in sorted(base_yr.items())))

        dec = {}
        for n in LOOKBACKS:
            col = []
            for t in tr:
                v, _ = decay_pair(ups, dns, int(t["entry_ts"]), flo, fhi,
                                  fts, n=n)
                col.append(0.5 if v is None else v)
            dec[n] = col

        print(f"\n    {'n':>3} {'thr':>5} {'keep':>5} {'n':>5} {'net':>9} "
              f"{'dNet':>8} {'WR':>6} {'PF':>5} {'DD':>6} {'R/tr':>6}  yr/M")
        for n in LOOKBACKS:
            for thr in THRESH:
                rs, ys = [], []
                for t, v in zip(tr, dec[n]):
                    if v < thr:
                        rs.append(float(t["r_multiple"]))
                        ys.append(t["exit_date"][:4])
                if len(rs) < 30:
                    continue
                # BUG FIX: per must be the COST per trade, not net/n.
                # net_r(tr) is already net, so cost = gross - net.
                per = (sum(float(t["r_multiple"]) for t in tr) - base) \
                    / float(len(tr))
                netN = sum(rs) - per * len(rs)
                y = yr(rs, ys)
                ok = sum(1 for k in y if y[k] >= base_yr.get(k, 0))
                flag = "INSIDE M" if abs(netN - base) < M else "clears M"
                print(f"    {n:>3} {thr:>5.2f} "
                      f"{100.0*len(rs)/len(tr):>4.0f}% {len(rs):>5} "
                      f"{netN:>+9.1f} {netN-base:>+8.1f} "
                      f"{100.0*sum(1 for x in rs if x>0)/len(rs):>5.1f}% "
                      f"{pf(rs):>5.2f} {dd(rs):>6.1f} "
                      f"{sum(rs)/len(rs):>+6.2f}  {ok}/{len(y)} {flag}")
    print()


if __name__ == "__main__":
    main()
