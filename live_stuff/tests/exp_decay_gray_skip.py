"""P33 - decay, GRAY vs SKIP, from the committed rule.
decay = of the last 4 CONFIRMED 15m BUYING legs, the fraction whose
start-price LOW is broken by 1m price at or before the entry.
GRAY = no order, slot held, n stays 500, r=0, no cost.
SKIP = no order, slot free, next signal taken.
CONTROL IS CHECKED FIRST; the run stops if the pin does not match.
"""
import bisect as bs
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
from exp_decay_switch import legs_by_dir

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
    s = s.replace(t1, t1 + "    _pdthr=0.0,\n    _pdlog=None,\n    _pdup=None,\n"
                          "    _pdts=None,\n    _pdlo=None,\n")
    a = ("        if (not exp_mltf) and busy_until and "
         "bar_time <= busy_until:\n"
         "            if exp_shadow_book: _sr[\"reason\"]=\"busy\"\n")
    assert s.count(a) == 1, "anchor"
    inj = (
        "        if _pdup is not None and _pdlo is not None:\n"
        "            _t = int(candles_ltf[i][\"ts\"])\n"
        "            _j = bs.bisect_right(_pdts, _t) - 1\n"
        "            _v = 0.5\n"
        "            if _j >= 0:\n"
        "                _QQ = [L for L in _pdup if L['cts'] <= _t][-4:]\n"
        "                if _QQ:\n"
        "                    _b = 0\n"
        "                    for _L in _QQ:\n"
        "                        _p = _L['px']\n"
        "                        if _p <= 0:\n"
        "                            continue\n"
        "                        _x = bs.bisect_left(_pdts, _L['cts'])\n"
        "                        if _j < _x:\n"
        "                            continue\n"
        "                        _GG = _pdlo[_x:_j + 1]\n"
        "                        if _GG and min(_GG) < _p:\n"
        "                            _b += 1\n"
        "                    _v = _b / float(len(_QQ))\n"
        "            if _pdlog is not None:\n"
        "                _pdlog.append((_t, _v))\n"
        "            if _pdthr > 0 and _v >= _pdthr:\n"
        "                continue\n"
    )
    return s.replace(a, a + inj)


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
    print("  A control n=500 NET; run stops if the pin does not match")
    print("  B GRAY    n=500, grayed at r=0, no cost")
    print("  C SKIP    pre-slot reject, slot free, next signal taken\n")
    sim = tc._load_module(patched(), "p33")
    sim = sim[0] if isinstance(sim, tuple) else sim
    sim = getattr(sim, "simulate_htf_ltf_streak_halt", sim)
    params = {**BP, **EXPERIMENTS[KEY]["params"]}
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)

        def run(extra):
            r = sim(c1h, sw10, c15, sw15, fine, **params, **extra)
            return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]

        up0, _ = legs_by_dir(sw15)
        fts0 = [int(c["ts"]) for c in fine]
        flo0 = [float(c["low"]) for c in fine]
        log = []
        base = run({"_pdlog": log, "_pdup": up0, "_pdts": fts0, "_pdlo": flo0})
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
        g = dict((e[0], e[1]) for e in log)
        kept = [t for t in base
                if g.get(int(t["entry_ts"]), 0.5) < THR]
        per = (sum(float(t["r_multiple"]) for t in base) - nb) / n0
        gnet = sum(float(t["r_multiple"]) for t in kept) - per * len(kept)
        c = run({"_pdthr": THR, "_pdup": up, "_pdts": fts, "_pdlo": flo})
        nc = net_r(c)
        kc = [float(t["r_multiple"]) for t in c]
        print("      GRAY  n=%4d net=%+8.1fR dNet=%+7.1fR   %d grayed at r=0"
              % (n0, gnet, gnet - nb, n0 - len(kept)))
        print("      SKIP  n=%4d net=%+8.1fR dNet=%+7.1fR  PF=%4.2f DD=%5.1f strk=%2d"
              % (len(c), nc, nc - nb, pf(kc), dd(kc), streak(kc)))
        print("      SKIP - GRAY (value of freeing the slot) %+7.1fR   n %+d\n"
              % (nc - gnet, len(c) - n0))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()