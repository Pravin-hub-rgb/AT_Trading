"""P53 - THE 1h LOSING-STREAK GATE, MADE STRICTLY CAUSAL.

WHY THIS FILE EXISTS
    P52 found that gating the 15m book on the 1h layer's own losing streak
    gives +180.9R / +94.8R / +164.3R / +77.6R across the four cells, PF up
    to 5.69. That is the largest dNet in the whole session. It was not
    accepted, because the way P52 counted the streak was
    `leg.entry_ts <= window_start` - and a leg that has STARTED but not
    CLOSED when the window opens does not have a known outcome yet. That is
    a lookahead and the number was not trustworthy.

    This file rebuilds the same rule with the only defensible definition: a
    leg counts toward the streak only if it had CLOSED before the window
    opened. Nothing about a window's own leg, or any leg still open, is read.

THE CAUSALITY PROBE IS THE POINT
    The probe recomputes the arm with the window's start moved 1 hour
    earlier, which gives the gate strictly more information. If the rule
    were leaking, moving the cutoff EARLIER can only make it better in a way
    a causal rule cannot be, and the arm would inflate. A causal arm must
    get WORSE or stay flat when it is handed the future. The harness prints
    the delta so this is visible rather than assumed.

ALSO NOT REPRODUCIBLE AS SHIPPED
    P52's A1 cooldown printed byte-identical books at every setting from 1
    to 13 days. That was a harness bug, not an inert parameter: the loop
    computed `last_bad` once from the whole book and then reused it, so
    every window saw the same single value. A1 is dropped here rather than
    reported as inert.

A4 IS DELIBERATELY NOT CARRIED FORWARD
    "the window's 1h leg reached 3R" is only knowable at the window's end.
    It scored 4/4 positive in P52 (+112.0R / +82.3R / +80.9R / +72.1R) and
    it is hindsight. It is recorded as a measurement of what the window
    turned out to be worth, not as a rule, and it must not be shipped.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING

M_NULL = 193.4
STREAKS = (1, 2, 3, 4, 5, 6)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def main():
    print("=" * 100)
    print("  P53  THE 1h LOSING-STREAK GATE, STRICTLY CAUSAL")
    print("=" * 100)
    print("  A leg counts toward the streak only if it CLOSED before the")
    print("  window opened. M = %.1fR" % M_NULL)
    print("  PROBE: cutoff moved 1h earlier hands the gate MORE information;")
    print("  a causal rule must get worse or stay flat when given the")
    print("  future. An arm that improves under the probe is leaking.\n")
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, n0, nb))
                return
            ivs = sorted(r.get("intervals") or [], key=lambda v: v[0])
            legs = list(r.get("htf_trades") or []) + \
                list(r.get("htf_trades_b2") or [])
            legs = [L for L in legs if L.get("outcome") != "open"]
            legs.sort(key=lambda L: int(L["exit_ts"]))
            for t in tr:
                ts = int(t["entry_ts"])
                td = 1 if t["dir"] == "long" else -1
                bi = None
                for ix, v in enumerate(ivs):
                    if v[0] < ts <= v[1] and v[2] == td:
                        if bi is None or v[0] > ivs[bi][0]:
                            bi = ix
                t["_ix"] = bi
            print("    [%s] control %dt %+.1fR (PIN ok)   %d windows, "
                  "%d closed 1h legs" % (scope.upper(), n0, nb, len(ivs),
                                         len(legs)))
            print("      %-30s %5s %9s %8s %6s" % ("rule", "n", "net",
                                                   "dNet", "PF"))
            base = [t for t in tr if t["_ix"] is not None]
            for ns in STREAKS:
                for shift, tag in ((0, ""), (3600, " [PROBE -1h]")):
                    keep = set()
                    streak = 0
                    li = 0
                    for k, v in enumerate(ivs):
                        cut = v[0] - shift
                        while li < len(legs) and \
                                int(legs[li]["exit_ts"]) <= cut:
                            streak = streak + 1 if \
                                float(legs[li].get("r_multiple", 0) or 0) \
                                <= 0 else 0
                            li += 1
                        if streak < ns:
                            keep.add(k)
                    sel = [t for t in base if t["_ix"] in keep]
                    if len(sel) < 15:
                        continue
                    rs = [float(x["r_multiple"]) for x in sel]
                    net = net_r(sel)
                    d = net - nb
                    flag = " *" if abs(d) > M_NULL else ""
                    print("      %-30s %5d %+9.1fR %+8.1fR %6.2f%s"
                          % ("skip while 1h streak >= %d%s" % (ns, tag),
                             len(sel), net, d, pf(rs), flag))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()