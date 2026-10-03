"""P41 - THE SAME CHARACTER SCORE, BUT READ ON THE 1h CHAIN.

THE USER'S POINT, WHICH IS THE RIGHT ONE
    P39/P40 built the rolling character score on 15m and it lost 76/76
    arms. I explained why as "the 1h window already decides direction, so
    a 15m second opinion is redundant." That explanation is only true of
    the 15m read. It is not true of a 1h read.

    The window's own direction comes from 1h B1/B2/FLIP marks. A rolling
    character score built from 1h swings is a DIFFERENT reading of the
    same timeframe, and it is available while the window is still open -
    so it can question the window rather than filter trades inside it.

    That is the first construction in this whole line that can add
    information instead of only removing trades.

THREE USES, ALL ON 1h
  1  GATE the window   take a trade only when the 1h character AGREES
                       with the window direction
  2  FLIP the window  when the 1h character strongly disagrees, take the
                       other side. This is the only place a direction
                       override has ever been tested at the HTF level.
  3  STRENGTH         take only when |score| is large, whichever side

1h legs, 1h candles for the break test (each 1h leg's own high/low against
1h closes at or before the entry). N swept 4, 8, 12, 16, 24.
"""
import bisect as bs
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
from exp_decay_switch import _dt

NS = (4, 8, 12, 16, 24)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (453, 279.5), (254, 66.9)),
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


def legs_all(sw):
    out = []
    for s in sw:
        ct = s.get("confirmed_at_time") or ""
        if not isinstance(ct, str) or len(ct) < 19:
            continue
        try:
            cts = _dt(ct)
        except Exception:
            continue
        px = float((s.get("seg") or {}).get("start_px", 0) or 0)
        if px > 0:
            out.append((cts, 1 if s.get("dir") in ("up", "B") else 0, px))
    out.sort(key=lambda x: x[0])
    return out


def score(legs, ts, lo, hi, t, n):
    vis = [L for L in legs if L[0] <= t][-n:]
    if len(vis) < 2:
        return None
    bull = 0
    j = bs.bisect_right(ts, t) - 1
    for cts, isup, px in vis:
        a = bs.bisect_left(ts, cts)
        if j < a:
            continue
        if isup:
            seg = lo[a:j + 1]
            if seg and min(seg) >= px:
                bull += 1
        else:
            seg = hi[a:j + 1]
            if seg and max(seg) > px:
                bull += 1
    return bull / float(len(vis)) - 0.5


def main():
    print("=" * 100)
    print("  P41  THE CHARACTER SCORE READ ON THE 1h CHAIN")
    print("=" * 100)
    print("  GATE = only when 1h character agrees with the window")
    print("  FLIP = take the other side when it strongly disagrees")
    print("  STR  = only when |score| is large\n")
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
            legs = legs_all(a[1])
            ts = [int(c["ts"]) for c in a[0]]
            lo = [float(c["low"]) for c in a[0]]
            hi = [float(c["high"]) for c in a[0]]
            for n in NS:
                for t in tr:
                    t["_s%d" % n] = score(legs, ts, lo, hi,
                                           int(t["entry_ts"]), n)
            print("    [%s] control %dt %+.1fR (PIN ok)   %d 1h legs"
                  % (scope.upper(), n0, nb, len(legs)))
            print("      %-26s %5s %9s %8s %6s %6s"
                  % ("idea", "n", "net", "dNet", "PF", "DD"))
            for n in NS:
                k = "_s%d" % n
                arms = [
                    ("N=%d GATE agree" % n,
                     lambda t: (t[k] or 0) > 0 if t["dir"] == "long"
                     else (t[k] or 0) < 0),
                    ("N=%d FLIP disagree" % n,
                     lambda t: (t[k] or 0) < 0 if t["dir"] == "long"
                     else (t[k] or 0) > 0),
                    ("N=%d STR |s|>0.1" % n, lambda t: abs(t[k] or 0) > 0.10),
                    ("N=%d STR |s|>0.2" % n, lambda t: abs(t[k] or 0) > 0.20),
                ]
                for lbl, fn in arms:
                    sel = [t for t in tr if fn(t)]
                    if len(sel) < 20:
                        continue
                    rs = [float(x["r_multiple"]) for x in sel]
                    net = net_r(sel)
                    print("      %-26s %5d %+9.1fR %+8.1fR %6.2f %6.1f"
                          % (lbl, len(sel), net, net - nb, pf(rs), dd(rs)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()