"""P86 - ATR-NORMALISED TREND DISTANCE. One pre-registered form, not a sweep.

WHY ONE FORM ONLY
    P84 tested a raw trailing MA at four windows and failed all of them,
    but it also showed MA400 winning 7 of 8 IS half-years - the best
    conditional result anywhere in that run. Testing more MA variants now
    would be searching after seeing four windows, and the family-wise
    criterion exists precisely to stop that.

    So ONE form is fixed in advance, chosen for a stated reason rather than
    a grid: a raw MA compares price to an absolute average, so its
    behaviour changes as the price level changes - which is exactly the
    objection P68/P69 raised to absolute price and volatility features and
    why relative price died in 4 of 4 cells. **Measuring the distance in
    ATRs rather than in dollars removes the level dependence and is the one
    formulation that survives that earlier result.**

THE FEATURE
    dist = (close - MA_M) / ATR_M        at each trade's own entry_ts
        keep LONG  only if dist >= +D
        keep SHORT only if dist <= -D

    Both sides symmetrically, so it is "trade with the trend" and not a
    filter built for the failing side.

    M = 200 hours, matching P84's longest window and its best half-year
    split, chosen BEFORE looking at any result here.
    D in {0.5, 1.0, 2.0} ATRs, pre-registered, FAMILY-WISE.

PASS CRITERION - UNCHANGED
    Beat the champion in both eras in both lanes, clear M = 193.4R, and
    survive the calendar half-year partition.

WHAT THIS IS NOT
    It is not a search over D. Three values, all must pass, and if they
    disagree in sign the family fails and nothing is adopted - the same
    rule that closed the P85 ceiling's predecessor set and the P80 arms.

CAUSALITY
    dist uses only 1h bars at or before entry_ts, computed outside the
    engine, and P79 established prefix invariance at 100% on this chain.
"""
import bisect as bs
import collections
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
MA_BARS = 200          # hours, fixed before looking
DS = (0.5, 1.0, 2.0)  # ATRs, pre-registered, family-wise
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def feats(c1h):
    ts, cl, tr = [], [], []
    prev = None
    for c in c1h:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    pre = [0.0]
    for x in cl:
        pre.append(pre[-1] + x)
    n = len(cl)
    ma, atr = [], []
    for i in range(n):
        lo = max(0, i - MA_BARS + 1)
        cnt = i + 1 - lo
        ma.append((pre[i + 1] - pre[lo]) / cnt)
        seg = tr[lo:i + 1]
        atr.append(sum(seg) / len(seg) if seg else 0.0)
    return ts, cl, ma, atr


def dist_at(ts, cl, ma, atr, entry_ts):
    j = bs.bisect_left(ts, int(entry_ts))
    if j <= 0 or j >= len(ts) or atr[j - 1] <= 0:
        return None
    return (cl[j - 1] - ma[j - 1]) / atr[j - 1]


def keep(tr, ts, cl, ma, atr, d):
    out = []
    for t in tr:
        v = dist_at(ts, cl, ma, atr, t["entry_ts"])
        if v is None:
            continue
        if t["dir"] == "long" and v >= d:
            out.append(t)
        elif t["dir"] != "long" and v <= -d:
            out.append(t)
    return out


def half(t):
    x = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%dH%d" % (x.year, 1 if x.month <= 6 else 2)


def main():
    print("=" * 100)
    print("  P86  ATR-NORMALISED TREND DISTANCE (one form, pre-registered)")
    print("=" * 100)
    print("  dist = (close - MA%d) / ATR%d, in ATRs not dollars."
          % (MA_BARS, MA_BARS))
    print("  Long kept if dist >= +D, short if dist <= -D.  D in %s ATRs," % (DS,))
    print("  family-wise: all three must pass. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    books = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            tr = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = (tr, feats(src[scope][0]))
    print("  controls pinned in all four cells\n")

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            tr, (ts, cl, ma, atr) = books[(name, scope)]
            base = net_of(tr)
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(tr), base))
            print("      %-14s %5s %9s %8s %6s %11s %20s"
                  % ("arm", "n", "net", "R/t", "PF", "dNet", "period split"))
            pc = collections.defaultdict(list)
            for t in tr:
                pc[half(t["entry_ts"])].append(float(t["r_multiple"]))
            for dd_ in DS:
                sub = keep(tr, ts, cl, ma, atr, dd_)
                if not sub:
                    print("      %-14s %5d   (nothing kept)"
                          % ("D=%.1f" % dd_, 0))
                    continue
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                pp = collections.defaultdict(list)
                for t in sub:
                    pp[half(t["entry_ts"])].append(float(t["r_multiple"]))
                w = l = t_ = 0
                for k in set(pc) | set(pp):
                    a, b = pc.get(k, []), pp.get(k, [])
                    if not (a and b):
                        continue
                    if sum(b) / len(b) > sum(a) / len(a):
                        w += 1
                    elif sum(b) / len(b) < sum(a) / len(a):
                        l += 1
                    else:
                        t_ += 1
                print("      %-14s %5d %+9.1fR %+8.3f %6.2f %+9.1fR  "
                      "w%d l%d t%d of %d"
                      % ("D=%.1f" % dd_, len(rs), net, net / len(rs), pf(rs),
                         net - base, w, l, t_, w + l + t_))
            # what it does to each side
            for lbl, dd_ in (("control", None), ("D=1.0", 1.0)):
                grp = tr if dd_ is None else keep(tr, ts, cl, ma, atr, dd_)
                lng = [x for x in grp if x["dir"] == "long"]
                sh = [x for x in grp if x["dir"] != "long"]
                rl = [float(x["r_multiple"]) for x in lng]
                rsh = [float(x["r_multiple"]) for x in sh]
                print("      %-8s long %4dt %+8.1fR PF %5.2f | short %4dt "
                      "%+8.1fR PF %5.2f"
                      % (lbl, len(rl), net_of(lng), pf(rl) if rl else 0.0,
                         len(rsh), net_of(sh), pf(rsh) if rsh else 0.0))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()