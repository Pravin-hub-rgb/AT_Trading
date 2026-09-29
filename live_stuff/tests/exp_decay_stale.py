"""P38 - STALE BUYING LEGS. Gray them, or stop blocking on them?

WHY THIS IS A REAL QUESTION
    decay_pair filters to BUYING legs and then takes the last 4 of them.
    A 15m buying leg is roughly 2.5h (min_bars 50), so four of them are
    about ten hours of buying structure - but SELLING legs can occur
    between them, so the calendar span is longer than ten hours and is
    not capped anywhere. The user is right that this needs measuring, and
    that a leg from four days ago is describing a regime that has since
    been replaced by new players.

THE TWO OPPOSITE USES OF THE SAME FACT
    GRAY   the legs are stale, so the decay reading is meaningless -
           refuse those trades outright.
    CAP    the legs are stale, so the decay reading is meaningless -
           do NOT apply the rule there. This KEEPS the trades.
    They are opposite. P37 tested CAP and it was better (+56.6R vs
    +34.2R). This tests GRAY as well, and both together, on both eras.

Also reported: the raw age distribution, because 415 of 500 entries
having fresh legs and only 14 being stale is the reason this is a
small-population question and not a main one.
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
    print("  P38  STALE BUYING LEGS - gray them, or stop blocking on them?")
    print("=" * 100)
    print("  a 15m buying leg is ~2.5h, so 4 are ~10h, but selling legs")
    print("  fall between them and the span is uncapped.\n")
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
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
            for t in tr:
                ts = int(t["entry_ts"])
                x, _ = decay_pair(up, dn, ts, flo, fhi, fts, n=4)
                t["_u"] = 0.5 if x is None else x
                vis = [L for L in up if L["cts"] <= ts][-4:]
                t["_age"] = ((ts - vis[-1]["cts"]) / 86400.0) if vis else 99.0
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), n0, nb))
            fresh = [t for t in tr if t["_age"] < 1.0]
            stale = [t for t in tr if t["_age"] >= 1.0]
            sr = [float(x["r_multiple"]) for x in stale]
            print("      legs fresh(<1d) %d   stale(>=1d) %d"
                  "   stale meanR %+.3f  stale net %+.1fR"
                  % (len(fresh), len(stale),
                     (sum(sr) / len(sr)) if sr else 0.0, sum(sr)))
            print("      %-34s %5s %9s %8s %6s %6s"
                  % ("rule", "n", "net", "dNet", "PF", "DD"))
            arms = [
                ("A no filter", lambda t: True),
                ("B current (block if u>=0.75)", lambda t: t["_u"] < THR),
                ("G GRAY stale (drop age>=1d)", lambda t: t["_age"] < 1.0),
                ("C CAP 1d (block only if fresh)",
                 lambda t: not (t["_u"] >= THR and t["_age"] < 1.0)),
                ("D CAP1d + GRAY stale",
                 lambda t: t["_age"] < 1.0 and not (t["_u"] >= THR
                                                   and t["_age"] < 1.0)),
                ("E CAP2d", lambda t: not (t["_u"] >= THR and t["_age"] < 2.0)),
            ]
            for lbl, fn in arms:
                sel = [t for t in tr if fn(t)]
                if len(sel) < 20:
                    print("      %-34s %5d  (too few)" % (lbl, len(sel)))
                    continue
                rs = [float(x["r_multiple"]) for x in sel]
                net = net_r(sel)
                print("      %-34s %5d %+9.1fR %+8.1fR %6.2f %6.1f"
                      % (lbl, len(sel), net, net - nb, pf(rs), dd(rs)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()