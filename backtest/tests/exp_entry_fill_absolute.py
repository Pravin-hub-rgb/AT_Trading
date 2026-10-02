"""P91 - THE ABSOLUTE-RETURN TEST ON THE ENTRY FILL. The one run that settles
P90 either way.

THE QUESTION P90 LEFT OPEN
    P90 re-filled the champion's entries at the next 15m bar's open and the
    book got BETTER in every cell: champion IS +325.8R -> +500.6R (PF 2.38 ->
    5.39), OOS +70.1R -> +214.1R (PF 1.59 -> 3.63), both lanes. If true,
    +325.8R is a pessimistic figure and shipping it is conservative.

    But P90's own caveat was that R-MULTIPLE IS A RATIO AND ITS DENOMINATOR
    MOVES. A later entry can shrink `risk` while barely moving `gain`, and
    R rises without the trade being any more profitable. The mechanism
    falsifier also failed - corr(dR, ATR%) was -0.05 to -0.08 in all four
    cells, where the prediction was a cost scaling with the bar's range.

    **So: is the gain real money, or is it the denominator?**

THE TEST - ABSOLUTE PRICE RETURN, NOT R-MULTIPLE
    For each trade, in price terms, with 1 unit of notional:

        long   return = (exit - entry) / entry
        short  return = (entry - exit) / entry      <-- SIGN-CORRECTED
                                                 for direction

    Then SUM the absolute returns across the book. This is what a fixed
    notional account earns, and it has no denominator that can move.

    **CORRECTED 2026-10-01.** This used to read
        short  return = (exit - entry) / entry   (signed the same way)
    which is the NEGATIVE of PnL for a short. `abs_return()` below did not
    check t["dir"] at all, so the short totals came out negative and were read
    as losses. They were profits. P91's central claim - "every short book loses
    money in absolute terms" - is retracted; see FILL_ABSOLUTE_P91.md and
    exp_p121_short_absolute.py.

    The old line also asserted that the two measures "can diverge arbitrarily
    and that divergence IS the finding". There is no divergence. Shorts are
    profitable in both metrics and the metrics agree: +0.4415 absolute against
    +105.7R IS, +0.7471 against +83.6R OOS. The divergence was manufactured by
    the convention, not found in the data.

    Both arms are recomputed the same way, so the comparison is like for
    like, and the shipped arm is the control that must reproduce its own
    pin in absolute terms.

WHAT DECIDES IT - PRE-REGISTERED
    absolute total RISES materially  -> the fill is genuinely better and
                                        P90's headline stands
    absolute total FALLS             -> the R-multiple rose only because
                                        the denominator shrank, P90's
                                        headline is retracted, and the
                                        shipped figure is the honest one

    "Materially" needs a scale and this run fixes one before looking: the
    absolute totals are also converted to an implied R at the book's OWN
    median risk, so the comparison sits on the same R axis as everything
    else in the programme, and compared against M = 193.4R.

WHAT ELSE IS REPORTED, BECAUSE ONE NUMBER IS NOT ENOUGH
    - the same per-side split as P90, since P89 made the long/short
      distinction load-bearing
    - the win rate and the mean absolute return per trade, so a shift
      driven by a few large winners is visible rather than hidden
    - the top-5%-removed book, because S3/P91 established this book's net
      is tail-concentrated and a mean can move on one trade

LIMITS, STATED FIRST
    This is a MEASUREMENT. It cannot be adopted and it changes no
    production code. It either validates a headline number or retracts one,
    and both outcomes are worth exactly one run each.
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
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
SLIP = 0.0005
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_r(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def refill(tr, c15, mode):
    """P90's CORRECTED delta version - exit and stop held."""
    ts = [int(c["ts"]) for c in c15]
    op = [float(c["open"]) for c in c15]
    out = []
    for t in tr:
        e = int(t["entry_ts"])
        j = bs.bisect_left(ts, e)
        if j <= 0 or j >= len(ts):
            out.append(t)
            continue
        old = float(t["entry_price"])
        px = op[j]
        if mode == "slip":
            px *= (1.0 + SLIP) if t["dir"] == "long" else (1.0 - SLIP)
        sl = float(t["sl"])
        ex = t.get("exit_price")
        if px == old or ex is None:
            out.append(t)
            continue
        exf = float(ex)
        nr = abs(px - sl)
        if nr <= 0:
            out.append(t)
            continue
        og = (exf - old) if t["dir"] == "long" else (old - exf)
        ng = (exf - px) if t["dir"] == "long" else (px - exf)
        new = dict(t)
        new["entry_price"] = px
        new["r_multiple"] = round(float(t["r_multiple"])
                                  + (ng - og) / nr, 3)
        out.append(new)
    return out


def abs_return(tr):
    """Sum of per-trade price return at ONE unit of notional. No
    denominator that can move.

    FIXED 2026-10-01. This used to ignore t["dir"] entirely and compute
    (exit-entry)/entry for every trade. For a SHORT that expression is the
    NEGATIVE of PnL: a profitable short exits below entry, so its raw change is
    negative. P91 tabulated -0.4415 IS / -0.7471 OOS for shorts from this
    function and read them as losses. They were profits.

    The direction is now applied. On the origin book this flips the short
    totals to +0.4415 IS / +0.7471 OOS - exact negations, confirmed by
    exp_p121_short_absolute.py, which prints both conventions side by side.
    """
    s = 0.0
    for t in tr:
        e = float(t["entry_price"])
        x = t.get("exit_price")
        if e <= 0 or x is None:
            continue
        raw = (float(x) - e) / e
        if str(t.get("dir", "")).lower().startswith("s"):
            raw = -raw
        s += raw
    return s


def mean_abs(tr):
    v = []
    for t in tr:
        e = float(t["entry_price"])
        x = t.get("exit_price")
        if e <= 0 or x is None:
            continue
        v.append((float(x) - e) / e)
    return (sum(v) / len(v), len(v)) if v else (0.0, 0)


def median_risk(tr, c15):
    ts = [int(c["ts"]) for c in c15]
    cl = [float(c["close"]) for c in c15]
    rk = []
    for t in tr:
        e = float(t["entry_price"])
        sl = float(t["sl"])
        px = t.get("exit_price")
        if px is None:
            continue
        j = bs.bisect_left(ts, int(t["entry_ts"]))
        ref = cl[min(j, len(cl) - 1)] if j < len(cl) else e
        if ref <= 0:
            continue
        rk.append(abs(e - sl) / ref)
    rk.sort()
    return rk[len(rk) // 2] if rk else 0.0


def main():
    print("=" * 100)
    print("  P91  ABSOLUTE-RETURN TEST ON THE ENTRY FILL")
    print("=" * 100)
    print("  P90 said the book IMPROVES on live fills (+500.6R IS) but could")
    print("  not tell whether that was money or a shrinking denominator.")
    print("  Absolute price return at 1 unit notional has no moving")
    print("  denominator. Same returns, same fills, comparable axis.")
    print("  M = %.1fR\n" % M_NULL)

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
            books[(name, scope)] = (tr, src[scope][2])

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            tr, c15 = books[(name, scope)]
            mrisk = median_risk(tr, c15) or 0.01
            base_r = net_r(tr)
            print("  --- [%s]  %d trades, shipped R-multiple net %+.1fR "
                  "(PIN ok), median risk %.4f"
                  % (scope.upper(), len(tr), base_r, mrisk))
            print("      %-28s %10s %10s %12s %9s %10s"
                  % ("fill", "abs total", "implied R", "mean/trade",
                     "win %", "ex-top5"))
            for lbl, mode in (("(a) shipped, signal-bar close", None),
                              ("(b) next 15m open", "open"),
                              ("(c) next open + 5bp slip", "slip")):
                sub = tr if mode is None else refill(tr, c15, mode)
                a = abs_return(sub)
                imp = a / mrisk
                m, n = mean_abs(sub)
                wr = 100.0 * sum(1 for t in sub
                                 if abs_return([t]) > 0) / max(1, len(sub))
                rr = sorted((float(t["r_multiple"]) for t in sub),
                            reverse=True)[:max(0, len(sub) - max(1,
                                                                 len(sub) // 20))]
                print("      %-28s %+10.4f %+10.1fR %+12.5f %8.1f%% %10.1fR"
                      % (lbl, a, imp, m, wr, sum(rr)))
            print("      --- per side, absolute total ---")
            for lbl, mode in (("shipped", None), ("next open", "open")):
                sub = tr if mode is None else refill(tr, c15, mode)
                lg = [t for t in sub if t["dir"] == "long"]
                sh = [t for t in sub if t["dir"] != "long"]
                print("        %-12s longs %+8.4f (%3dt) | shorts %+8.4f "
                      "(%3dt)" % (lbl, abs_return(lg), len(lg),
                                   abs_return(sh), len(sh)))
            print()
    print("  Nothing adopted. This is a measurement of a shipped number.")


if __name__ == "__main__":
    main()