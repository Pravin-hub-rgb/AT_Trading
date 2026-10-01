"""P33 - decay: GRAY vs SKIP. Minimal patch, computed OUTSIDE the engine.

decay = of the last 4 CONFIRMED 15m BUYING legs, the fraction whose
start LOW is broken by 1m price at or before entry.  decay<0.75 keeps.

GRAY  no order, slot held  -> n stays 500, grayed at r=0, no cost
SKIP  no order, slot free  -> engine never sees that signal, next one
      is taken.  Implemented by dropping the signal from `filtered`
      BEFORE the LTF loop, which is the same place the engine drops a
      signal for its own gates.  One line of injected text, no decay
      arithmetic inside the engine at all.

CONTROL IS CHECKED FIRST; the run stops if the pin does not match.
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
KEY = "champion_multi_sw10"
PIN = {"is": (500, 325.8), "oos": (279, 70.1)}


def patched():
    cap = {}
    orig = tc._load_module
    tc._load_module = lambda t, n: (cap.__setitem__("s", t), orig(t, n))[1]
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["s"]
    t1 = "    *,\n"
    assert s.count(t1) == 1
    s = s.replace(t1, t1 + "    exp_drop_bars=None,\n")
    a = "    for sig, use in filtered:\n"
    assert s.count(a) == 1, "loop anchor"
    return s.replace(a, a + (
        "        if exp_drop_bars and sig[\"bar\"] in exp_drop_bars:\n"
        "            continue\n"
    ))


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
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def streak(rs):
    c = m = 0
    for x in rs:
        c = c + 1 if x < 0 else 0
        m = max(m, c)
    return m


def main():
    print("=" * 96)
    print("  P33  decay GRAY vs SKIP   (buying decay < 0.75, last 4 legs)")
    print("=" * 96)
    print("  A control n=500 NET - run stops if the pin does not match")
    print("  B GRAY    n=500, grayed at r=0, no cost")
    print("  C SKIP    signal dropped before the LTF loop, slot freed\n")
    sim = tc._load_module(patched(), "p33")
    sim = sim[0] if isinstance(sim, tuple) else sim
    sim = getattr(sim, "simulate_htf_ltf_streak_halt", sim)
    params = {**BP, **EXPERIMENTS[KEY]["params"]}
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)

        def run(extra):
            r = sim(c1h, sw10, c15, sw15, fine, **params, **extra)
            return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]

        base = run({})
        nb, n0 = net_r(base), len(base)
        pin = PIN[scope]
        if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
            print("  [%s] CONTROL FAILED %dt %+.1fR want %s -- STOPPING"
                  % (scope, n0, nb, pin))
            return
        print("  --- %s  control %dt %+.1fR  (PIN ok)"
              % (scope.upper(), n0, nb))
        up, _dn = legs_by_dir(sw15)
        fts = [int(c["ts"]) for c in fine]
        flo = [float(c["low"]) for c in fine]
        fhi = [float(c["high"]) for c in fine]
        drop = set()
        grayed = []
        for t in base:
            v, _ = decay_pair(up, _dn, int(t["entry_ts"]), flo, fhi, fts, n=4)
            if v is not None and v >= THR:
                drop.add(t["entry_date"])
                grayed.append(t)
        kept = [t for t in base if t["entry_date"] not in drop]
        per = (sum(float(x["r_multiple"]) for x in base) - nb) / n0
        gnet = (sum(float(x["r_multiple"]) for x in kept) - per * len(kept))
        c = run({"exp_drop_bars": drop})
        nc = net_r(c)
        kc = [float(x["r_multiple"]) for x in c]
        print("      GRAY  n=%4d net=%+8.1fR dNet=%+7.1fR   %d grayed at r=0"
              % (n0, gnet, gnet - nb, len(grayed)))
        print("      SKIP  n=%4d net=%+8.1fR dNet=%+7.1fR  PF=%4.2f DD=%5.1f strk=%2d"
              % (len(c), nc, nc - nb, pf(kc), dd(kc), streak(kc)))
        print("      SKIP - GRAY (value of freeing the slot) %+7.1fR   n %+d\n"
              % (nc - gnet, len(c) - n0))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()