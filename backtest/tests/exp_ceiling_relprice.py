"""P69 - THE TWO CORRECTED DIRECTIONS: VOLATILITY CEILING, RELATIVE PRICE.

P68 left exactly two things queued, both of them corrections of P68's own
mistakes, and both of them stated there as new pre-registrations rather
than fixes. This runs them.

PART A - VOLATILITY CEILING, CORRECT SIGN
    P67 found the book works in the CALM third of its volatility
    distribution. P68 built a FLOOR - trade when volatility is high - and
    duly lost money, monotonically from PF 0.78 down to 0.49. That was a
    pre-registration error on my part and it is corrected here, not
    re-tuned: the rule is a CEILING, and the grid is fixed here, now,
    before running.

    Grid, pre-registered: keep trades whose trailing ATR% is at or BELOW
    0.30 / 0.40 / 0.50 / 0.60 percent. Lower ceilings keep less of the book
    and should keep the calmest part of it.

PART B - RELATIVE PRICE, THE ONLY FORM THAT IS NOT A CLOCK
    P68 found low price beats high price in 4 of 4 cells, and then found
    the reason it cannot be used as a level: a fixed price floor is monotone
    in time, so it trades in 2021 and stops in 2026. That is a clock, not a
    regime detector.

    So the feature is made scale-free:

        REL = price at entry / median(close over the trailing 30 days)

    Both terms are read from bars at or before the trade's own entry_ts, so
    the feature is causal and available at decision time from data the live
    system already holds. 30 days of 15m bars is 2880 - long enough that the
    median is a stable reference rather than a recent-price echo.

    Grid, pre-registered: keep trades with REL at or below
    0.85 / 0.90 / 0.95 / 1.00. REL <= 1.00 means "at or below where this
    market has been trading for the last month", which is the form an owner
    could actually act on.

FAMILY-WISE, FOR BOTH PARTS
    Every level in a grid must beat the control in BOTH eras in BOTH lanes
    AND clear M = 193.4R, or NONE is adopted. P68's two grids failed
    spectacularly in the negative direction and this programme's history
    with post-hoc thresholds is bad enough that the rule has to bind in
    advance. No level is selected for looking best.

THE HONEST PRIOR
    P68's most important caveat applies to both parts: the LOW-price half was
    +207.5R of the champion's +325.8R in IS and +41.7R of +70.1R in OOS. Both
    halves were profitable, so removing the other half removes positive
    money. These tests are therefore most likely to fail by being smaller
    books, and a result of "smaller and slightly better" should be read as
    the same trade it has been every other time - not as progress toward a
    free gain.

WHAT WOULD ACTUALLY SETTLE EITHER
    Per P63, a forward slice of 40-70 trades can RULE OUT and never confirm.
    A volatility ceiling and a relative-price floor are both rules that
    could be killed on that slice, and both are far better uses of it than
    anything else currently queued.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos
import test_experiments_craze as tc

M_NULL = 193.4
ATR_BARS = 96            # 24h of 15m, unchanged from P67/P68
REL_DAYS = 30
REL_BARS = REL_DAYS * 96  # 2880 x 15m
CEILINGS = (0.30, 0.40, 0.50, 0.60)
RELS = (0.85, 0.90, 0.95, 1.00)
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def net_of(tr):
    """Net of costs on the pins' own basis (P60's gross-vs-net lesson)."""
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def as_flow(c):
    from src.walker import FlowCandle
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def series(c15):
    ts, cl, tr = [], [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    return ts, cl, tr


def feats_at(ts, cl, tr, entry_ts):
    """(ATR%%, REL) at a trade's entry, from bars <= entry only.

    ATR% is P68's FIXED version - divided by close - not P67's dollar
    version. REL divides the entry-bar close by the median of the trailing
    REL_BARS closes, so both terms are historical.
    """
    j = bs.bisect_left(ts, int(entry_ts))
    if j <= 0:
        return None, None
    lo_a = max(0, j - ATR_BARS)
    seg_a = tr[lo_a:j]
    px = cl[j - 1]
    if not seg_a or px <= 0:
        return None, None
    atr_pct = (sum(seg_a) / len(seg_a)) / px * 100.0
    lo_r = max(0, j - REL_BARS)
    seg_r = cl[lo_r:j]
    if len(seg_r) < REL_BARS // 4:
        return atr_pct, None
    s = sorted(seg_r)
    med = s[len(s) // 2]
    return atr_pct, (px / med if med > 0 else None)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def main():
    print("=" * 100)
    print("  P69  VOLATILITY CEILING (CORRECT SIGN) AND RELATIVE PRICE")
    print("=" * 100)
    print("  A  keep trailing ATR%% <= %s   (P68 ran the FLOOR by mistake)"
          % (CEILINGS,))
    print("  B  keep REL = price / median(%d x 15m close) <= %s"
          % (REL_BARS, RELS))
    print("  Family-wise per grid: every level must beat control in BOTH")
    print("  eras in BOTH lanes AND clear M. No level selected afterwards.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"], d["sw10"], d["sw15"]),
           "oos": (oc1h, oc15, oos_fine,
                   tc._compute_swings(as_flow(oc1h), "continuous", min_bars=10),
                   tc._compute_swings(as_flow(oc15), "continuous", min_bars=50))}

    res = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine, sw10, sw15 = src[scope]
            all_tr = [t for t in tc.build_module()(
                c_htf, sw10, c_ltf, sw15, fine, **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(all_tr) - pin[i][0]) > 2
                    or abs(net_of(all_tr) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(all_tr), net_of(all_tr), *pin[i]))
                return
            ts, cl, tr = series(c_ltf)
            rows = []
            for t in all_tr:
                a, r = feats_at(ts, cl, tr, t["entry_ts"])
                if a is not None and r is not None:
                    rows.append((t, a, r))
            base = net_of(all_tr)
            print("  --- [%s] control %dt %+.1fR (PIN ok) | featurised %d"
                  % (scope.upper(), len(all_tr), base, len(rows)))
            print("      ATR%% %.3f-%.3f   REL %.3f-%.3f"
                  % (min(r[1] for r in rows), max(r[1] for r in rows),
                     min(r[2] for r in rows), max(r[2] for r in rows)))
            print("      --- A: volatility CEILING (keep ATR%% <= x) ---")
            print("      %-8s %6s %9s %8s %6s %11s"
                  % ("ceil%", "n", "net", "R/t", "PF", "dNet"))
            for cv in CEILINGS:
                sub = [r[0] for r in rows if r[1] <= cv]
                if not sub:
                    print("      %-8.2f %6d   (no trades)" % cv)
                    continue
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                dv = net - base
                res.setdefault(("ceil", cv), []).append(dv)
                print("      %-8.2f %6d %+9.1fR %+8.3f %6.2f %+9.1fR%s"
                      % (cv, len(rs), net, net / len(rs), pf(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print("      --- B: RELATIVE PRICE (keep REL <= x) ---")
            print("      %-8s %6s %9s %8s %6s %11s"
                  % ("rel<=", "n", "net", "R/t", "PF", "dNet"))
            for rv in RELS:
                sub = [r[0] for r in rows if r[2] <= rv]
                if not sub:
                    print("      %-8.2f %6d   (no trades)" % rv)
                    continue
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                dv = net - base
                res.setdefault(("rel", rv), []).append(dv)
                print("      %-8.2f %6d %+9.1fR %+8.3f %6.2f %+9.1fR%s"
                      % (rv, len(rs), net, net / len(rs), pf(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print()

    print("  " + "=" * 98)
    print("  FAMILY-WISE VERDICT")
    print("  " + "=" * 98)
    for key in sorted(res, key=lambda k: (k[0], k[1])):
        v = res[key]
        ok = all(x > 0 for x in v) and all(abs(x) > M_NULL for x in v)
        lbl = ("ceiling %.2f%%" % key[1]) if key[0] == "ceil" \
            else ("REL <= %.2f" % key[1])
        print("    %-16s cells %-34s %s"
              % (lbl, " ".join("%+8.1fR" % x for x in v),
                 "PASSES" if ok else "fails"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()