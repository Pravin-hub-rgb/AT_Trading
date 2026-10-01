"""P42 - THE WHOLE LINE, CLOSED OUT. Three things at once.

P39  15m score as a side gate        0/32 arms positive
P40  5 rewrites of that score        0/11 arms positive
P41  the same score read on 1h       GATE / FLIP / STR, only N=8 STR
                                     ever went positive, and only in IS
                                     and only on two lanes out of four

N=8 STR is the last live wire. So this file asks the three questions that
were still open, and then stops.

  PART 1  COMBO      does the 1h conviction read stack on top of the 15m
                     decay read, or do the two fight each other? Both are
                     already documented individually (+15.1R and +34.2R in
                     champion IS), which is exactly the setup where the
                     combination is usually worthless.

  PART 2  RE-DECIDE  the hardest version of the user's original thesis.
                     Stop respecting the 1h window completely. Take the
                     side the rolling character says is strong, no matter
                     what the window believes. If direction is the whole
                     edge and the character can read direction, this is
                     the only construction that would show it. If this
                     fails, the feature is finished - not the filter
                     version, not the strength version, this one.

  PART 3  GRAY/SKIP  the same reads, but keep the losing trade in the
                     book marked untradeable instead of deleting it, which
                     is the GRAY labelling that beat SKIP in P33.

Both eras, both lanes, pins verified before anything is printed.
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
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import legs_by_dir, decay_pair, _dt

NS1H = (6, 8, 10, 12)
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


def row(lbl, sel, nb):
    if len(sel) < 20:
        print("      %-34s %5d   (too few)" % (lbl, len(sel)))
        return None
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    print("      %-34s %5d %+9.1fR %+8.1fR %6.2f %6.1f %7.1f%%"
          % (lbl, len(sel), net, net - nb, pf(rs), dd(rs), hit))
    return net - nb


def main():
    print("=" * 100)
    print("  P42  THE WHOLE CHARACTER-SCORE LINE, CLOSED OUT")
    print("=" * 100)
    verdict = {}
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
            lg1h = legs_all(a[1])
            t1h = [int(c["ts"]) for c in a[0]]
            l1h = [float(c["low"]) for c in a[0]]
            h1h = [float(c["high"]) for c in a[0]]
            up, dn = legs_by_dir(a[3])
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            for t in tr:
                ts = int(t["entry_ts"])
                t["_u"] = 0.5
                dv, _ = decay_pair(up, dn, ts, flo, fhi, fts, n=4)
                if dv is not None:
                    t["_u"] = dv
                for n in NS1H:
                    t["_h%d" % n] = score(lg1h, t1h, l1h, h1h, ts, n)
            print("    [%s] control %dt %+.1fR (PIN ok)" % (scope.upper(),
                                                            n0, nb))
            print("      PART 1  1h conviction x 15m decay")
            row("A no filter", tr, nb)
            for n in NS1H:
                k = "_h%d" % n
                row("1h |s|>0.10 only (N=%d)" % n,
                    [t for t in tr if abs(t[k] or 0) > 0.10], nb)
                row("1h |s|>0.10 AND decay<0.75",
                    [t for t in tr if abs(t[k] or 0) > 0.10
                     and t["_u"] < 0.75], nb)
                row("decay<0.75 AND 1h AGREES (N=%d)" % n,
                    [t for t in tr if t["_u"] < 0.75
                     and ((t[k] or 0) > 0) == (t["dir"] == "long")], nb)

            print("      PART 2  ignore the window, trade the character")
            for n in NS1H:
                k = "_h%d" % n
                sel = [t for t in tr
                       if (t[k] or 0) > 0 and t["dir"] == "short"]
                sel += [t for t in tr
                        if (t[k] or 0) < 0 and t["dir"] == "long"]
                row("N=%d INVERT on disagree" % n, sel, nb)
                for thr in (0.10, 0.20):
                    sel = [t for t in tr
                           if (t[k] or 0) < -thr and t["dir"] == "long"]
                    sel += [t for t in tr
                            if (t[k] or 0) > thr and t["dir"] == "short"]
                    row("N=%d INVERT |s|>%.2f" % (n, thr), sel, nb)

            print("      PART 3  GRAY keeps the loser, SKIP deletes it")
            for n in (8,):
                k = "_h%d" % n
                lost = [t for t in tr
                        if abs(t[k] or 0) > 0.10
                        and float(t["r_multiple"]) < 0]
                row("N=8 SKIP 1h-weak losers", [t for t in tr
                     if t not in lost], nb)
                g = [dict(t) for t in tr if t not in lost]
                for t in g:
                    t["r_multiple"] = 0.0
                row("N=8 GRAY 1h-weak losers", g, nb)
                row("N=8 decay SKIP", [t for t in tr if t["_u"] < 0.75], nb)
                g2 = [dict(t) for t in tr]
                for t in g2:
                    if t["_u"] >= 0.75:
                        t["r_multiple"] = 0.0
                row("N=8 decay GRAY", g2, nb)
            print()
    print("  Nothing adopted. This closes the character-score line.")


if __name__ == "__main__":
    main()