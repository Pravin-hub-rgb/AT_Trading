"""P35 - the decay mirror, run cleanly on ONE cost basis.

THE THEORY
    decay = of the last 4 CONFIRMED 15m BUYING legs, the fraction whose
    start LOW is broken by 1m price at or before entry. 0.25 / 0.5 / 0.75
    are just how many of the four gave way. decay >= 0.75 means three or
    four supports are gone and the trade is refused.

THE OBJECTION (the user's, and it is right)
    The rule is built ONLY from buying legs, yet it is applied to BOTH
    sides. A short taken while four buying supports are breaking is being
    judged by a fact about the other side. The mirror is the honest
    construction:

        one-sided   long  -> buying decay       short -> buying decay
        mirror      long  -> selling decay      short -> selling decay

WHY THIS FILE EXISTS
    The mirror was run before (P24 arm C, P31 arms M1/M2) but on mixed
    cost bases and with a gross control in some arms, so the numbers
    could not be compared with each other. This runs every variant from
    ONE engine run per cell and scores them all the same way, so the only
    difference between rows is the rule.

COST BASIS
    net_r() is used for the control and for every arm, and the dNet is
    always against the same NET control. That is the discipline P15's
    docs broke - its champion is quoted at +356.9R because it subtracts a
    fixed per-trade cost, while net_r() gives +325.8R.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import legs_by_dir, decay_pair

THR = 0.75
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def main():
    print("=" * 100)
    print("  P35  THE DECAY MIRROR - one cost basis, one engine run per cell")
    print("=" * 100)
    print("  buying decay  = broken lows of the last 4 BUYING legs")
    print("  selling decay = broken highs of the last 4 SELLING legs")
    print("  one-sided: buying decay refuses BOTH sides (the incumbent)")
    print("  mirror   : each side judged by its OWN side's decay\n")
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            if scope == "oos":
                (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
                a1 = _compute_swings(f1h, "continuous", min_bars=10)
                a2 = _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"])
                a3 = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
                args = (c1h, a1, c15, a2, a3)
            else:
                d = get_data()
                identity_gate(d, tc.build_module())
                args = (d["c1h"], d[swtag], d["c15"], d[sw15], d["fine"])
            sim = tc.build_module()
            r = sim(*args, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR want %s -- STOPPING"
                      % (scope, n0, nb, pin))
                return
            up, dn = legs_by_dir(args[3])
            fts = [int(c["ts"]) for c in args[4]]
            flo = [float(c["low"]) for c in args[4]]
            fhi = [float(c["high"]) for c in args[4]]
            U, V = {}, {}
            for t in tr:
                a, b = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi,
                                  fts, n=4)
                U[int(t["entry_ts"])] = 0.5 if a is None else a
                V[int(t["entry_ts"])] = 0.5 if b is None else b
            print("    [%s] control %dt %+.1fR  (PIN ok)"
                  % (scope.upper(), n0, nb))
            print("      %-30s %5s %9s %8s %6s %6s"
                  % ("rule", "n", "net", "dNet", "PF", "DD"))
            arms = {
                "A no filter": lambda lng: True,
                "B one-sided (buying, both)": lambda lng: U < THR,
                "C mirror (own side)": lambda lng: (U if lng else V) < THR,
                "D mirror only on SHORT": lambda lng: (V if not lng else 1.0) < THR,
                "E mirror only on LONG": lambda lng: (U if lng else 1.0) < THR,
            }
            for lbl, fn in arms.items():
                sel, U, V2 = [], U, V
                for t in tr:
                    k = int(t["entry_ts"])
                    if (U[k] if t["dir"] == "long" else V2[k]) is None:
                        pass
                    if fn(t["dir"] == "long"):
                        sel.append(t)
                rs = [float(x["r_multiple"]) for x in sel]
                net = net_r(sel)
                print("      %-30s %5d %+9.1fR %+8.1fR %6.2f %6.1f"
                      % (lbl, len(sel), net, net - nb, pf(rs), dd(rs)))
            print()


if __name__ == "__main__":
    main()