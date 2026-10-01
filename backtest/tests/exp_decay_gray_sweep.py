"""P34 - IS GRAY REALLY BETTER THAN SKIP? Sweep it, do not assume it.

The user is right to make me prove it rather than trust one cell: an
earlier framing appeared to favour SKIP, and the two words were used
inconsistently across the session. This settles it by sweeping the
threshold and both lanes, so the answer does not rest on one number.

GRAY = decay high -> no order, slot stays HELD, trade stays in the book
       at r=0, no cost. n stays at the control's n.
SKIP = decay high -> signal dropped before the LTF loop, slot FREE,
       next signal taken. n falls.

The P&L difference between the two is entirely the slot question, so
the two arms share one rule and one decay computation and differ only in
where the signal is refused.

DECAY THRESHOLD SWEPT: 0.25 0.5 0.6 0.75 0.9
LANES: champion_multi_sw10 and utcsat_multi_sw10
Both eras. Control checked on every cell; the run stops if it fails.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import legs_by_dir, decay_pair

THRS = (0.5, 0.75, 0.9)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),

)


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
    assert s.count(a) == 1
    return s.replace(a, a + (
        "        if exp_drop_bars and sig[\"bar\"] in exp_drop_bars:\n"
        "            continue\n"
    ))


def load(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


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
    print("  P34  GRAY vs SKIP, swept. Is the gap structural?")
    print("=" * 100)
    print("  GRAY n = control n (slot held).  SKIP n = falls (slot free).")
    print("  Same rule, same decay, only the slot question differs.\n")
    sim = tc._load_module(patched(), "p34")
    sim = sim[0] if isinstance(sim, tuple) else sim
    sim = getattr(sim, "simulate_htf_ltf_streak_halt", sim)

    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print(f"  --- {key}")
        for scope, pin in (("is", ispin), ("oos", oospin)):
            c1h, s1, c15, s15, fine = load(scope, swtag)

            def run(extra):
                r = sim(c1h, s1, c15, s15, fine, **params, **extra)
                return [t for t in r["ltf_trades"]
                        if t.get("outcome") != "open"]

            base = run({})
            nb, n0 = net_r(base), len(base)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("  [%s] CONTROL FAILED %dt %+.1fR -- STOPPING"
                      % (scope, n0, nb))
                return
            up, dn = legs_by_dir(s15)
            fts = [int(c["ts"]) for c in fine]
            flo = [float(c["low"]) for c in fine]
            fhi = [float(c["high"]) for c in fine]
            per = (sum(float(t["r_multiple"]) for t in base) - nb) / n0
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), n0, nb))
            print("      thr  | GRAY n   net    dNet  | SKIP n    net"
                  "    dNet  | GRAY-SKIP")
            for thr in THRS:
                drop = set()
                for t in base:
                    v, _ = decay_pair(up, dn, int(t["entry_ts"]), flo, fhi,
                                      fts, n=4)
                    if v is not None and v >= thr:
                        drop.add(t["entry_date"])
                kept = [t for t in base if t["entry_date"] not in drop]
                gnet = (sum(float(x["r_multiple"]) for x in kept)
                        - per * len(kept))
                c = run({"exp_drop_bars": drop})
                nc = net_r(c)
                print("      %.2f | %5d %+8.1fR %+7.1fR | %5d %+8.1fR "
                      "%+7.1fR | %+7.1fR"
                      % (thr, n0, gnet, gnet - nb, len(c), nc, nc - nb,
                         gnet - nc))
            print()


if __name__ == "__main__":
    main()