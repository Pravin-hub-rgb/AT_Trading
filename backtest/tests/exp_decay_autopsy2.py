"""P37 - WHY DO SHORTS DIE AT HIGH BUYING DECAY? An autopsy, not a story.

THE OBJECTION, STATED PLAINLY
    For a long, "buyers keep being stopped" obviously means do not buy -
    buyers are weak. Fine. But on a SHORT the seller is strong by
    construction: we are selling into strength. If buyers are also being
    stopped out, the tape is trending down, which is exactly when a short
    should work. Blocking it makes no sense, and the data says the block
    helps, so one of those two things is wrong. This file answers it by
    looking at what actually happens to those shorts rather than by
    re-asserting the claim.

TWO UNTESTED THINGS THE USER RAISED, ALSO HERE
    1. `decay_pair` filters to BUYING legs and then takes the last n of
       them. So it is the last 4 BUYING legs, NOT the last 4 swings. If
       the most recent swings are all selling, the buying legs being
       measured can be arbitrarily old. There should be a cap on their
       age and there is not.
    2. That age is therefore a live hypothesis: if the measured buying
       legs are stale, the "decay" is describing an old regime and should
       carry less weight. The rule should then RELAX when they are old,
       not block.

OUTPUT
    A  bucket autopsy of mean gross R by decay bucket, split long/short,
       so the short side is read directly instead of inferred
    B  the four buying legs' age at entry, bucketed, with the same split
    C  the same rule but with an age cap, swept
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from exp_decay_switch import legs_by_dir, decay_pair

KEY = "champion_multi_sw10"
BUCKETS = (0.0, 0.25, 0.5, 0.75, 1.01)
AGE_CAPS = (1.0, 2.0, 3.0, 5.0, 7.0, 1e9)


def meanR(rs):
    return sum(rs) / len(rs) if rs else 0.0


def main():
    print("=" * 96)
    print("  P37  SHORT-SIDE AUTOPSY + the staleness the rule never checked")
    print("=" * 96)
    params = {**BP, **EXPERIMENTS[KEY]["params"]}
    d = get_data()
    identity_gate(d, tc.build_module())
    r = tc.build_module()(d["c1h"], d["sw10"], d["c15"], d["sw15"],
                          fine_ltf=d["fine"], **params)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    nb = net_r(tr)
    print("  control %dt %+.1fR  (pin 500 / +325.8)\n" % (len(tr), nb))
    up, dn = legs_by_dir(d["sw15"])
    fts = [int(c["ts"]) for c in d["fine"]]
    flo = [float(c["low"]) for c in d["fine"]]
    fhi = [float(c["high"]) for c in d["fine"]]
    U, V, AGE = {}, {}, {}
    for t in tr:
        ts = int(t["entry_ts"])
        a, b = decay_pair(up, dn, ts, flo, fhi, fts, n=4)
        U[ts] = 0.5 if a is None else a
        V[ts] = 0.5 if b is None else b
        vis = [L for L in up if L["cts"] <= ts][-4:]
        AGE[ts] = ((ts - vis[-1]["cts"]) / 86400.0) if vis else 99.0
        t["_u"], t["_v"], t["_age"] = U[ts], V[ts], AGE[ts]

    print("  A. BUCKET AUTOPSY - mean GROSS R by buying decay, per side")
    print("     %-14s %28s %28s" % ("decay", "LONG", "SHORT"))
    print("     %-14s %6s %8s %8s %6s %8s %8s"
          % ("bucket", "n", "meanR", "totR", "n", "meanR", "totR"))
    for lo, hi in zip(BUCKETS[:-1], BUCKETS[1:]):
        L = [t for t in tr if t["dir"] == "long" and lo <= t["_u"] < hi]
        S = [t for t in tr if t["dir"] == "short" and lo <= t["_u"] < hi]
        lr = [float(x["r_multiple"]) for x in L]
        sr = [float(x["r_multiple"]) for x in S]
        lbl = "%.2f-%.2f" % (lo, min(hi, 1.0))
        print("     %-14s %6d %+8.3f %+8.1f %6d %+8.3f %+8.1f"
              % (lbl, len(lr), meanR(lr), sum(lr),
                 len(sr), meanR(sr), sum(sr)))

    print("\n  B. HOW OLD ARE THE 4 BUYING LEGS BEING MEASURED?")
    print("     %-12s %6s %10s %10s %10s"
          % ("oldest leg", "n", "meanR", "long", "short"))
    for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 7), (7, 1e9)):
        g = [t for t in tr if lo <= t["_age"] < hi]
        if not g:
            continue
        gr = [float(x["r_multiple"]) for x in g]
        L = [float(x["r_multiple"]) for x in g if x["dir"] == "long"]
        S = [float(x["r_multiple"]) for x in g if x["dir"] == "short"]
        lbl = "%g-%g d" % (lo, hi if hi < 1e8 else 999)
        print("     %-12s %6d %+10.3f %10.3f %10.3f"
              % (lbl, len(gr), meanR(gr), meanR(L), meanR(S)))

    print("\n  C. THE SAME RULE, BUT ONLY WHEN THE LEGS ARE FRESH")
    print("     (if the measured buying legs are stale, do not block)")
    print("     %-12s %6s %10s %10s %10s"
          % ("age cap", "n", "net", "dNet", "dNet vs B"))
    for cap in AGE_CAPS:
        sel = [t for t in tr if not (t["_u"] >= 0.75 and t["_age"] <= cap)]
        rs = [float(x["r_multiple"]) for x in sel]
        net = net_r(sel)
        c1 = ("stale" if cap > 1e8 else "%gd" % cap)
        print("     %-12s %6d %+10.1fR %+10.1fR"
              % (c1, len(sel), net, net - nb))
    print("\n  Nothing adopted.")


if __name__ == "__main__":
    main()