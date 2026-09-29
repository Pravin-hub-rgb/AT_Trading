"""P39 - WHICH SIDE, NOT WHETHER. A character read over a rolling window.

THE THESIS (the user's, new today)
    "prev n swing judge karenge rolling like 10, 20... jyada recent utna
     acha... agar clearly buying swing ke lows break nahi hue hain toh
     bullish ka sign hai, ya phir selling swing bhi hai aur uske high
     break hai toh bhi bullish... vice versa"

So: take the last N swings of BOTH kinds, mixed in time order, and ask
for each one whether its own defence held.
    buying leg  -> its LOW broken?   intact = bullish
    selling leg -> its HIGH broken?  broken = bullish
Both facts point the same way: buyers holding their supports, or sellers
being taken out. Either is bullish. The mirror is bearish.

    score = (buying intact + selling broken) / N - 0.5      in [-0.5, +0.5]

This is NOT the decay feature. Decay counts broken BUYING legs and
answers "sit out". This counts both sides over a rolling window of any N
swings and answers "which way".

WHY IT IS WORTH BUILDING EVEN THOUGH THE PARTS EXIST
    decay_pair() already returns (broken_up_frac, broken_dn_frac) and
    every caller in the repo throws the second away:
        v, _ = decay_pair(...)
    P18 used that difference as a score, but only across buying legs
    inside the 4-leg decay window. The rolling-window-over-both-sides
    version has never been run.

CAUSALITY
    Only legs confirmed at or before the entry, only 1m bars up to the
    entry. The window is chronological, so no future swing can enter it.
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
from exp_decay_switch import legs_by_dir, _dt

WINDOWS = (4, 8, 12, 16, 24, 32)
THRS = (0.0, 0.10, 0.20, 0.30)
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


def build_legs(sw15):
    """All legs in time order: (confirm_ts, is_buying, price_to_defend)."""
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
        if px <= 0:
            continue
        out.append((cts, 1 if s.get("dir") in ("up", "B") else 0, px))
    out.sort(key=lambda x: x[0])
    return out


def score_at(legs, fts, flo, fhi, t, n):
    vis = [L for L in legs if L[0] <= t][-n:]
    if len(vis) < 2:
        return None
    bull = 0
    for cts, isup, px in vis:
        a = bs.bisect_left(fts, cts)
        j = bs.bisect_right(fts, t) - 1
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
    return bull / float(len(vis)) - 0.5


import bisect as bs


def main():
    print("=" * 100)
    print("  P39  WHICH SIDE TO TRADE - a rolling character read over N swings")
    print("=" * 100)
    print("  score = (buying intact + selling broken)/N - 0.5   in [-0.5,+0.5]")
    print("  + = bullish   - = bearish   0 = no character\n")
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
            legs = build_legs(a[3])
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            print("    [%s] control %dt %+.1fR (PIN ok)   %d 15m legs"
                  % (scope.upper(), n0, nb, len(legs)))
            print("      %-16s %5s %9s %8s %6s %6s %8s"
                  % ("N / thr", "n", "net", "dNet", "PF", "DD", "hit%"))
            for n in WINDOWS:
                sc = {}
                for t in tr:
                    s = score_at(legs, fts, flo, fhi, int(t["entry_ts"]), n)
                    sc[int(t["entry_ts"])] = s
                for thr in THRS:
                    sel = []
                    for t in tr:
                        s = sc[int(t["entry_ts"])]
                        if s is None:
                            continue
                        if (t["dir"] == "long" and s > thr) or \
                           (t["dir"] == "short" and s < -thr):
                            sel.append(t)
                    if len(sel) < 20:
                        continue
                    rs = [float(x["r_multiple"]) for x in sel]
                    net = net_r(sel)
                    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
                    print("      %-16s %5d %+9.1fR %+8.1fR %6.2f %6.1f %7.1f%%"
                          % ("N=%d thr=%.2f" % (n, thr), len(sel), net,
                             net - nb, pf(rs), dd(rs), hit))
            print()


if __name__ == "__main__":
    main()