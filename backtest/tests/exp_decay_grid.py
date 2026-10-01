"""P36 - THE DECAY GATE GRID. Every variant, one engine run, one cost basis.

WHAT THE FEATURE IS
    buying decay  = of the last 4 CONFIRMED 15m BUYING legs, the fraction
                    whose start LOW price has broken.  Breaking that low
                    means the buyers who entered there were stopped out.
    selling decay = the mirror: of the last 4 CONFIRMED 15m SELLING legs,
                    the fraction whose start HIGH price has broken.
                    Breaking that high means the sellers there were
                    stopped out.
    thr 0.75 = three or four of the four gave way.

THE HONEST OPENING
    A BUYING swing can only be a long-side fact and a SELLING swing can
    only be a short-side fact, so using one of them to refuse the other
    side is wrong on its face. That objection is correct and it has never
    been answered on a single cost basis, because P24, P31 and P30 each
    moved the basis between arms. This file runs every variant from ONE
    engine run per cell and scores them all with net_r(), so the only
    thing that differs between rows is the rule.

BLOCK vs ALLOW
    BLOCK  the signal is refused when decay is high. This is what the
           champion does today, and it refuses both sides on buying decay.
    ALLOW  the signal is only taken when decay is high - decay is read as
           confirmation rather than veto. The user asked for this too.

ARMS
    A  no filter
    B  BLOCK both sides on BUYING decay      (the incumbent)
    C  BLOCK both sides on SELLING decay
    D  BLOCK mirror, long<-buying, short<-selling   (each side by its own)
    E  BLOCK mirror, long<-selling, short<-buying   (sides crossed)
    F  ALLOW mirror, long<-selling, short<-buying   (decay confirms)
    G  ALLOW mirror, long<-buying, short<-selling
    H  ALLOW either side broken
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
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
    ("age10_dirmatch_swingpause_single_sw10", "sw10", (130, 435.7),
     (76, 43.2)),
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


def get(scope, swtag, key):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


ARMS = [
    ("A no filter", None),
    ("B BLOCK both <- buying", "b"),
    ("C BLOCK both <- selling", "s"),
    ("D BLOCK own side", "d"),
    ("E BLOCK crossed", "e"),
    ("F ALLOW crossed", "f"),
    ("G ALLOW own side", "g"),
    ("H ALLOW either broken", "h"),
]


def keep(rule, lng, u, v):
    if rule is None:
        return True
    hi = u >= THR          # buyers stopped out
    lo = v >= THR          # sellers stopped out
    if rule == "b":
        return not hi
    if rule == "s":
        return not lo
    if rule == "d":
        return not (hi if lng else lo)
    if rule == "e":
        return not (lo if lng else hi)
    if rule == "f":
        return (lo if lng else hi)
    if rule == "g":
        return (hi if lng else lo)
    if rule == "h":
        return hi or lo
    return True


def main():
    print("=" * 104)
    print("  P36  THE DECAY GATE GRID - one engine run, one cost basis")
    print("=" * 104)
    print("  buying decay high  = the last 4 buying legs' lows broke"
          " = buyers stopped out")
    print("  selling decay high = the last 4 selling legs' highs broke"
          " = sellers stopped out")
    print("  thr = 0.75 (three of four)\n")
    for key, swtag, ispin, oospin in LANES:
        if key not in EXPERIMENTS:
            continue
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag, key)
            sim = tc.build_module()
            r = sim(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR want %s -- STOP"
                      % (scope, n0, nb, pin))
                return
            up, dn = legs_by_dir(a[3])
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            U, V = {}, {}
            for t in tr:
                x, y = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi,
                                  fts, n=4)
                U[int(t["entry_ts"])] = 0.5 if x is None else x
                V[int(t["entry_ts"])] = 0.5 if y is None else y
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), n0, nb))
            print("      %-28s %5s %9s %8s %6s %6s"
                  % ("rule", "n", "net", "dNet", "PF", "DD"))
            for lbl, rule in ARMS:
                sel = [t for t in tr
                       if keep(rule, t["dir"] == "long",
                               U[int(t["entry_ts"])], V[int(t["entry_ts"])])]
                if len(sel) < 20:
                    print("      %-28s %5d   (too few)" % (lbl, len(sel)))
                    continue
                rs = [float(x["r_multiple"]) for x in sel]
                net = net_r(sel)
                print("      %-28s %5d %+9.1fR %+8.1fR %6.2f %6.1f"
                      % (lbl, len(sel), net, net - nb, pf(rs), dd(rs)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()