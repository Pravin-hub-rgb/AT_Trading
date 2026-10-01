"""P29 - WHY DID THE MIRROR FAIL? Leg-count and signal-strength autopsy.

THE USER'S OBJECTION IS LOGICALLY SOUND
=======================================
"jab htf selling bias, to short position ke liye bhi hum longs ke lows
break pe decide kar rahe hai?? this is dumb. shorts ke liye previous
selling swings ke high break decide karne chahiye, tabhi sahi mirror hoga"

They are right about the logic. The mirror (arm C in P24) was built exactly
that way and it LOST: IS -31.6R / OOS -0.8R against the one-sided rule's
+39.0R / +9.7R. A logically correct rule losing is informative, not
embarrassing - so it deserves an explanation rather than a shrug.

THE CANDIDATE EXPLANATION
=========================
`decay_pair` returns (broken_up_frac, broken_dn_frac). Only the FIRST has
ever been used. The second is computed and thrown away, so the mirror has
never had a fair test IF the two components are not equally well
estimated. They need not be: a drifting asset produces far more up-legs
than down-legs, and a fraction taken over 3 down-legs is a far noisier
measurement than the same fraction over 12 up-legs.

So the question is NOT "is the mirror logically right" - it is "is the
mirror even measurable at the same resolution as the one-sided rule". If
the down side is thin, the mirror is not a fair refutation of the user's
reasoning; it is a measurement with less resolution, and the honest
conclusion is that the mirror is UNTESTED rather than DEAD.

WHAT IS PRINTED
===============
  1. leg census - up vs down 15m legs, and how many are visible at entry
  2. the distribution of both components, so granularity is visible
     (0/3 vs 0/12 is the whole argument)
  3. how many trades have a usable down-side value at all
  4. mean gross R of kept trades under each rule, on the SIDE each rule is
     actually judging - the number that says whether the signal carries
     information on that side

No filter is proposed here and nothing is adopted.
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
from exp_decay_switch import legs_by_dir, decay_pair  # noqa: E402

NLEG, THR = 4, 0.75
KEY = "champion_multi_sw10"


def main():
    print("=" * 96)
    print("  P29  WHY THE MIRROR LOST  -  is the down side measurable?")
    print("=" * 96)
    print(f"  champion, 15m legs, lookback n={NLEG}\n")

    params = {**BP, **EXPERIMENTS[KEY]["params"]}
    d = get_data()
    identity_gate(d, tc.build_module())
    sim = tc.build_module()
    r = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"],
            **params)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    print(f"  control: {len(tr)} trades, {net_r(tr):+.1f}R\n")

    up, dn = legs_by_dir(d["sw15"])
    fts = [int(c["ts"]) for c in d["fine"]]
    flo = [float(c["low"]) for c in d["fine"]]
    fhi = [float(c["high"]) for c in d["fine"]]

    print("  1. LEG CENSUS (whole 15m chain)")
    print(f"     up (buying) legs : {len(up)}")
    print(f"     dn (selling) legs: {len(dn)}")
    print(f"     ratio            : {len(up)/max(1,len(dn)):.2f}x more ups\n")

    rows = []
    for t in tr:
        u, v = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi, fts, n=NLEG)
        rows.append((t["dir"], u, v))
    nu = sum(1 for _, u, _ in rows if u is not None)
    nd = sum(1 for _, _, v in rows if v is not None)
    print("  2. VISIBLE AT ENTRY (confirmed at or before the entry)")
    print(f"     trades with a usable UP   value: {nu}/{len(rows)}")
    print(f"     trades with a usable DOWN value: {nd}/{len(rows)}")

    def dist(vals, name):
        cnt = {}
        for v in vals:
            k = "none" if v is None else f"{v:.2f}"
            cnt[k] = cnt.get(k, 0) + 1
        print(f"     {name}: " +
              "  ".join(f"{k}={cnt[k]}" for k in sorted(cnt)))

    print("\n  3. VALUE DISTRIBUTION (granularity is the argument)")
    dist([u for _, u, _ in rows], "up-side  ")
    dist([v for _, _, v in rows], "down-side")

    nl = sum(1 for r in rows if r[0] == "long")
    ns = sum(1 for r in rows if r[0] == "short")
    print(f"\n  4. SIDE COUNTS: {nl} long, {ns} short")

    def kept(pick, side):
        out = []
        for t, (dr, u, v) in zip(tr, rows):
            if dr != side:
                continue
            x = pick(u, v)
            if x is not None and x < THR:
                out.append(float(t["r_multiple"]))
        return out

    def f(a):
        return (f"n={len(a):>3} meanR={sum(a)/len(a):+.3f}" if a
                else "n=0  (nothing kept)")

    print("\n  5. DOES THE SIGNAL CARRY INFORMATION ON ITS OWN SIDE?")
    print("     (mean GROSS R of kept trades, not NET)")
    for side, label in (("long", "LONG side - buying legs decide"),
                        ("short", "SHORT side - selling legs decide")):
        allr = [float(t["r_multiple"]) for t, (dr, _, _) in
                zip(tr, rows) if dr == side]
        print(f"     {label}")
        print(f"        all trades      {f(allr)}")
        print(f"        one-sided keeps {f(kept(lambda u, v: u, side))}")
        print(f"        mirror keeps    {f(kept(lambda u, v: v, side))}")
    print("\n  Nothing here proposes a filter or adopts anything. This is")
    print("  the evidence needed before running the mirror properly.")


if __name__ == "__main__":
    main()

    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from exp_decay_switch import legs_by_dir, decay_pair  # noqa: E402

NLEG, THR = 4, 0.75
KEY = "champion_multi_sw10"
