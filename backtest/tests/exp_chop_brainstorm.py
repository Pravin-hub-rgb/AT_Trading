"""P40 - FIVE WAYS TO USE THE CHARACTER SCORE, since using it as a plain
side filter already failed 32/32 in P39.

WHY THE PLAIN VERSION FAILED
    The gate was "take the long only when the rolling score says
    bullish". But the 1h window ALREADY decides direction and 100% of
    trades match it (P22 anatomy), so a second direction decision can only
    remove trades, never add information. Every one of the 32 arms was
    negative, and at N=32 thr=0.20 the survivor book had PF 3.70 against
    the champion's 2.38 - i.e. the filter was cutting good trades too.

THE FIVE IDEAS, and what each one actually changes
  1  STRENGTH      trade only when |score| is large. Not a direction
                   decision, a conviction one. Keeps the side the window
                   already picked and asks whether structure agrees.
  2  AGREEMENT     take only when the 15m character AGREES with the 1h
                   window. The window says long; is the 15m tape also
                   holding up? This is the one that is genuinely new -
                   it measures a disagreement the engine never looks at.
  3  DISAGREE      the inverse: trade only when they contradict. If
                   either of these two works it will show up here.
  4  SCORE x DECAY the two features are different animals - decay is a
                   no-trade detector over buying legs, score is a rolling
                   two-sided read. Combined rather than either alone.
  5  ASYMMETRY     the score's own balance: how many of the window's
                   legs were buying vs selling. A window made mostly of
                   buying legs is riding a different tape than one made
                   mostly of selling legs, and the engine treats them
                   identically.

N swept 8, 12, 16, 24, 32. Both eras, champion and utcsat, pins first.
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

NS = (8, 12, 16, 24, 32)
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


def streak(rs):
    c = m = 0
    for x in rs:
        c = c + 1 if x < 0 else 0
        m = max(m, c)
    return m


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


def legs_all(sw15):
    out = []
    for s in sw15:
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


def score(legs, fts, flo, fhi, t, n):
    vis = [L for L in legs if L[0] <= t][-n:]
    if len(vis) < 2:
        return None, 0.0
    bull = 0
    j = bs.bisect_right(fts, t) - 1
    for cts, isup, px in vis:
        a = bs.bisect_left(fts, cts)
        if j < a:
            continue
        if isup:
            seg = flo[a:j + 1]
            if seg and min(seg) >= px:
                bull += 1
        else:
            seg = fhi[a:j + 1]
            if seg and max(seg) > px:
                bull += 1
    return bull / float(len(vis)) - 0.5, \
        float(sum(1 for L in vis if L[1])) / len(vis)


def main():
    print("=" * 100)
    print("  P40  FIVE USES OF THE CHARACTER SCORE  (P39's plain use: 0/32)")
    print("=" * 100)
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
            legs = legs_all(a[3])
            up, dn = legs_by_dir(a[3])
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            for t in tr:
                ts = int(t["entry_ts"])
                t["_s"], t["_b"] = score(legs, fts, flo, fhi, ts, 16)
                dv, _ = decay_pair(up, dn, ts, flo, fhi, fts, n=4)
                t["_u"] = 0.5 if dv is None else dv
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), n0, nb))
            print("      %-30s %5s %9s %8s %6s %5s %5s"
                  % ("idea", "n", "net", "dNet", "PF", "DD", "strk"))
            base = lambda t: True
            arms = [
                ("A no filter", base),
                ("1 STRENGTH |s|>0.10", lambda t: abs(t["_s"]) > 0.10),
                ("1 STRENGTH |s|>0.20", lambda t: abs(t["_s"]) > 0.20),
                ("1 STRENGTH |s|>0.30", lambda t: abs(t["_s"]) > 0.30),
                ("2 AGREES with window", lambda t: (t["_s"] > 0) ==
                 (t["dir"] == "long")),
                ("2 AGREES, |s|>0.1", lambda t: (t["_s"] > 0) ==
                 (t["dir"] == "long") and abs(t["_s"]) > 0.10),
                ("3 DISAGREES with window", lambda t: (t["_s"] > 0) !=
                 (t["dir"] == "long")),
                ("4 score+s |s|>0.1 AND u<0.75",
                 lambda t: abs(t["_s"]) > 0.10 and t["_u"] < 0.75),
                ("4 decay alone u<0.75", lambda t: t["_u"] < 0.75),
                ("5 window mostly SELLING legs",
                 lambda t: t["_b"] < 0.5),
                ("5 window mostly BUYING legs", lambda t: t["_b"] >= 0.5),
            ]
            for lbl, fn in arms:
                sel = [t for t in tr if fn(t)]
                if len(sel) < 20:
                    print("      %-30s %5d  (too few)" % (lbl, len(sel)))
                    continue
                rs = [float(x["r_multiple"]) for x in sel]
                net = net_r(sel)
                print("      %-30s %5d %+9.1fR %+8.1fR %6.2f %5.1f %5d"
                      % (lbl, len(sel), net, net - nb, pf(rs), dd(rs),
                         streak(rs)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()