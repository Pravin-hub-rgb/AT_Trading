"""P43 - PROVING THE +645.2R ARM WAS A BUG, BY REMOVING THE FEATURE.

P42 PART 3 printed  +645.2R / PF 12.27 / 69.4% hit  for
"SKIP 1h-weak losers" and I flagged it as label leakage. This file proves
the flag rather than asserting it.

The claim being tested: that number says nothing about the character score,
because it would still appear if the score were deleted.

    LEAK  select trades by float(t["r_multiple"]) < 0  -- no feature at all

If LEAK alone reproduces an absurd net, then the P42 number is a property
of the leak, not of the 1h character read. And the honest version of the
same idea - decide from the score alone, never from the outcome - is run
beside it so the two can be compared directly:

    CAUSAL SKIP   drop trades with 1h |score| <= 0.10   (score only)
    CAUSAL GRAY   keep them in the book with R forced to 0 (score only)

Pins verified first, both lanes, both eras.
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
from exp_decay_switch import _dt

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


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


def score(legs, ts, lo, hi, t, n=8):
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
    if len(sel) < 5:
        print("      %-38s %5d  (too few)" % (lbl, len(sel)))
        return
    rs = [float(x["r_multiple"]) for x in sel]
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    print("      %-38s %5d %+9.1fR %+9.1fR %7.2f %7.1f%%"
          % (lbl, len(sel), net_r(sel), net_r(sel) - nb, pf(rs), hit))


def main():
    print("=" * 100)
    print("  P43  IS THE +645.2R A SIGNAL, OR A BUG?  Remove the feature.")
    print("=" * 100)
    print("  If LEAK (no feature, just delete the losers) is also absurd,")
    print("  then the P42 number was a property of the leak.\n")
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
            lg = legs_all(a[1])
            ts = [int(c["ts"]) for c in a[0]]
            lo = [float(c["low"]) for c in a[0]]
            hi = [float(c["high"]) for c in a[0]]
            for t in tr:
                t["_s"] = score(lg, ts, lo, hi, int(t["entry_ts"])) or 0.0
            print("    [%s] control %dt %+.1fR (PIN ok)" % (scope.upper(),
                                                            n0, nb))
            row("A no filter", tr, nb)
            row("LEAK: delete r<0, NO feature",
                [t for t in tr if float(t["r_multiple"]) >= 0], nb)
            row("LEAK: keep r<0, NO feature",
                [t for t in tr if float(t["r_multiple"]) < 0], nb)
            weak = [t for t in tr if abs(t["_s"]) <= 0.10]
            row("CAUSAL SKIP  1h |s|<=0.10 weak",
                [t for t in tr if t not in weak], nb)
            g = [dict(t) for t in tr]
            for t in g:
                if t in weak:
                    t["r_multiple"] = 0.0
            row("CAUSAL GRAY  1h |s|<=0.10 weak", g, nb)
            print()
    print("  A leak is the defect. Not a result, not a hint. Discarded.")


if __name__ == "__main__":
    main()