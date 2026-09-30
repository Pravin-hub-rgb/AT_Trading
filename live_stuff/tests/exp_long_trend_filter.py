"""P84 - LONG-SIDE TREND FILTER. The owner's question, and the most direct
answer this round has to one thing.

THE QUESTION
    "2021 was a breakdown - selling. How do we prevent the long side?"

    P78 located the defect precisely: the champion's OOS long side is not
    weak, it is ABSENT - 162 trades for +1.8R at PF 1.22, while its short
    side carried the entire OOS result. P83 showed the shape at yearly and
    quarterly granularity: 2021 is a whole losing year (-26.4R net, three
    of four quarters negative, worst quarter -19.3R at PF 0.41).

    BTC in that period fell from roughly $69k to $15k. It is a sustained
    DOWNTREND, and a long-only book with no trend filter buys every rally
    into it. That is a mechanical explanation with a mechanical candidate:
    take long entries only while price is above its trailing average.

THE FILTER
    TREND-MA on the 1h series, evaluated at each trade's own entry_ts:
        long entries kept only if the 1h close at entry is ABOVE its
        trailing M-bar mean
        short entries kept only if it is BELOW
    That is "trade with the trend" on both sides. The long side is the
    part that failed, and the short side arm exists so the filter is not
    hand-built for the answer - a filter that only fixes the side that
    needed fixing is not evidence.

    FOUR WINDOWS, PRE-REGISTERED, FAMILY-WISE
        M = 50, 100, 200, 400 hours  (2d, 4d, 8d, 16d)
    Every window must beat the champion in BOTH eras in BOTH lanes AND
    clear M = 193.4R AND survive the calendar half-year partition, or NONE
    is adopted. Four windows is four chances to look good; requiring all
    four is what stops this being a disguised parameter search.

WHY A MA AND NOT SOMETHING FANCIER
    Two reasons, both learned in this round. P55, P67 and P68 all failed to
    find a decision-time feature that separates the eras - swing geometry,
    absolute and relative volatility, and price level. **A trailing average
    is the simplest such feature there is, and if it does not separate,
    nothing simpler will.** And P79 established the chain is 100%
    prefix-invariant, so a bar-indexed MA is causal and replayable live by
    construction rather than by argument.

CAUSALITY
    The MA at entry_ts uses only 1h bars at or before that instant, and it
    is computed OUTSIDE the engine so it cannot collide with an
    engine-local name. Nothing is grouped by r_multiple, outcome or pnl:
    the filter is a function of price history only, and the trades are
    dropped, never scored differently.

PASS CRITERION - UNCHANGED AND STATED FIRST
    Beat the champion in both eras in both lanes, clear M = 193.4R, and
    survive the half-year partition. An arm that improves the risk profile
    while destroying the return is the signature that has killed eight
    candidates already this round.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

import bisect as bs
from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
MAS = (50, 100, 200, 400)      # hours on the 1h series
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def half(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def ma_series(ts, cl, m):
    """Trailing mean of closes over the last m bars, indexed like ts."""
    pre = [0.0]
    for c in cl:
        pre.append(pre[-1] + c)
    out = []
    for i in range(len(cl)):
        lo = max(0, i - m + 1)
        out.append((pre[i + 1] - pre[lo]) / (i + 1 - lo))
    return ts, out


def keep(tr, ts, mas, long_ma, short_ma):
    """long kept if close > its MA; short kept if close < its MA."""
    out = []
    for t in tr:
        j = bs.bisect_left(ts, int(t["entry_ts"]))
        if j <= 0 or j > len(ts):
            continue
        px = mas["px"][j - 1]
        m = long_ma if t["dir"] == "long" else short_ma
        if m <= 0:
            continue
        avg = mas["ma"][m][j - 1]
        if t["dir"] == "long" and px > avg:
            out.append(t)
        elif t["dir"] != "long" and px < avg:
            out.append(t)
    return out


def main():
    print("=" * 100)
    print("  P84  LONG-SIDE TREND FILTER - trade with the trend")
    print("=" * 100)
    print("  Long entries only while 1h close > trailing MA; shorts only")
    print("  while close < MA. MA windows (hours): %s" % (MAS,))
    print("  Family-wise: all four must beat in both eras both lanes, clear")
    print("  M = %.1fR, and survive the half-year partition.\n" % M_NULL)

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
            c_h, _, _, _, _ = src[scope]
            tr = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            ts = [int(c["ts"]) for c in c_h]
            cl = [float(c["close"]) for c in c_h]
            mas = {"ts": ts, "px": cl,
                   "ma": {m: ma_series(ts, cl, m)[1] for m in MAS}}
            books[(name, scope)] = (tr, mas)
    print("  controls pinned in all four cells\n")

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            tr, mas = books[(name, scope)]
            base = net_of(tr)
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(tr), base))
            print("      %-16s %5s %9s %8s %6s %6s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "dNet"))
            for m in MAS:
                sub = keep(tr, mas["ts"], mas, m, m)
                if not sub:
                    print("      %-16s %5d   (nothing kept)"
                          % ("MA%d" % m, 0))
                    continue
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                dv = net - base
                print("      %-16s %5d %+9.1fR %+8.3f %6.2f %6.1f %+9.1fR%s"
                      % ("MA%d" % m, len(rs), net, net / len(rs), pf(rs),
                         dd(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print("      -- period partition vs control --")
            import collections
            ph = collections.defaultdict(list)
            for t in tr:
                ph[half(t["entry_ts"])].append(float(t["r_multiple"]))
            for m in MAS:
                sub = keep(tr, mas["ts"], mas, m, m)
                pf_ = collections.defaultdict(list)
                for t in sub:
                    pf_[half(t["entry_ts"])].append(
                        float(t["r_multiple"]))
                w = l = t_ = 0
                for k in set(ph) | set(pf_):
                    a, b = ph.get(k, []), pf_.get(k, [])
                    if not (a and b):
                        continue
                    if sum(b) / len(b) > sum(a) / len(a):
                        w += 1
                    elif sum(b) / len(b) < sum(a) / len(a):
                        l += 1
                    else:
                        t_ += 1
                print("      %-16s wins %2d loses %2d ties %2d of %2d"
                      % ("MA%d" % m, w, l, t_, w + l + t_))
            # what the filter does to the 2021 long side specifically
            sub = keep(tr, mas["ts"], mas, 200, 200)
            for lbl, grp in (("control", tr), ("MA200", sub)):
                lng = [t for t in grp if t["dir"] == "long"]
                rs = [float(t["r_multiple"]) for t in lng]
                print("      %-8s ALL long: %4d trades %+8.1fR PF %5.2f"
                      % (lbl, len(rs), net_of(lng), pf(rs) if rs else 0.0))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()