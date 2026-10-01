"""P90 - ENTRY FILL CONVENTION: IS +325.8R PARTLY A FILL ARTEFACT?

FROM THE NEXT-ROUND BRIEF, BIG PICKLE'S P90
    "A live trader cannot fill at the close of a bar whose breakout they
     only see at that close. The re-fill cost is an upper bound on
     deployable expectancy that nobody has measured."

CONFIRMED IN THE SHIPPED CODE, NOT ASSUMED
    v7_timecap.py:65      entry = float(candles[i]["close"])
    where i is the index of the bar the signal fired ON. The break mark
    carries the bar's own close; the fill is that same close. So the entry
    price is set at the extreme of the very bar whose close revealed the
    breakout.

    THE ASYMMETRY IS WORTH NAMING: the EXIT side already fills honestly.
        v7_timecap.py:167  fill = min(sl_cur_f, float(c["open"]))
        v7_timecap.py:182  fill = max(sl_cur_f, float(c["open"]))
    Exits use the NEXT bar's open. Only the entry uses the signal bar's
    close. So the book is not uniformly optimistic - it is optimistic in one
    specific place, and that place is the one a live system cannot copy.

WHAT THIS IS AND IS NOT
    This is a MEASUREMENT of an upper bound on deployable expectancy, not a
    candidate. It cannot be adopted even if it passes - there is no
    parameter here to ship. It is the number an owner needs before deciding
    whether +325.8R is a real expectation or a fill assumption.

    The brief is explicit that the corrected figure is what matters. A
    backtest that overstates by a known, measured, mechanical amount is
    still useful; one that overstates by an unknown amount is not.

THE THREE FILLS - ALL REPORTED, NONE SELECTED, PER R3
    (a) signal-bar close  [SHIPPED - the control, not a result]
    (b) next 15m bar's OPEN      - what a live system can actually get
    (c) next 15m bar's OPEN + the existing 5bp entry slip

    The re-fill is a post-process re-pricing of entry_price with the
    existing stop and trail HELD. No engine edit, no change to the exit
    machinery, no change to the cost model. The R-multiple is recomputed
    from the new entry against the unchanged stop and target, which is what
    a live system would face.

    (c) is reported because a trader who sees a breakout at a close and
    cannot act until the next open is, in the real world, also worse off by
    roughly the spread and a little slippage. 5bp is the repo's existing
    entry-slip assumption; it is used here rather than a new number.

EXPECTED SHAPE, STATED BEFORE RUNNING
    Negative. Concentrated in LONGS, because a long breakout is filled at a
    higher price than the close that signalled it. And it should LOAD ON
    VOLATILITY: a breakout bar's re-fill cost scales with that bar's range.
    **If (b)-(a) does not correlate with the P69 ATR% feature, the mechanism
    is wrong and the number should not be believed** - that correlation is
    the falsifier, not the dNet.

FALSIFIER
    |dNet(b) - dNet(a)| < M = 193.4R  ->  the fill convention is not
    load-bearing and the book survives on live fills. |dNet| >= M -> the
    headline number needs restating before anyone ships it.
"""
import bisect as bs
import sys
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
SLIP = 0.0005          # the repo's existing entry-slip assumption
ATR_BARS = 96
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def refill(tr, c15, mode):
    """Re-price the entry against the next 15m bar's open, stop and exit
    HELD - the exit_price is whatever the engine already booked, in price
    terms, and does NOT move when the entry moves.

    WHY THIS IS NOW CORRECT AND WAS NOT ON THE FIRST RUN
    Attempt 1 recomputed r from (exit_price - new_entry) / new_risk. That is
    wrong twice over, and it produced +6038.8R, which is not a result but
    an arithmetic explosion: it re-derived every trade's R from scratch
    instead of ADJUSTING the R the engine had already booked.

    The correct adjustment is a DELTA. If the entry moves from old to new
    while the exit and the stop stay put:

        old_gain = exit - old_entry      new_gain = exit - new_entry
        old_risk = |old_entry - sl|      new_risk = |new_entry - sl|
        new_R    = old_R + (new_gain - old_gain) / new_risk

    The engine's own r_multiple already contains (old_gain / old_risk), so
    replacing it with a fresh (new_gain / new_risk) double-counts the change
    and — because the two ratios diverge violently when the new risk is
    small — inflates without bound. Adding the delta term instead leaves
    the control arm (mode=None) exactly equal to the shipped number, which
    is the invariant this run asserts.
    """
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
        new_risk = abs(px - sl)
        if new_risk <= 0:
            out.append(t)
            continue
        old_gain = (exf - old) if t["dir"] == "long" else (old - exf)
        new_gain = (exf - px) if t["dir"] == "long" else (px - exf)
        new = dict(t)
        new["entry_price"] = px
        new["r_multiple"] = round(float(t["r_multiple"])
                                  + (new_gain - old_gain) / new_risk, 3)
        out.append(new)
    return out


def corr(a, b):
    if len(a) < 3:
        return float("nan")
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    na = sum((x - ma) ** 2 for x in a) ** 0.5
    nb = sum((x - mb) ** 2 for x in b) ** 0.5
    if na == 0 or nb == 0:
        return float("nan")
    return sum((a[i] - ma) * (b[i] - mb) for i in range(len(a))) / (na * nb)


def main():
    print("=" * 100)
    print("  P90  ENTRY FILL CONVENTION - IS +325.8R A FILL ARTEFACT?")
    print("=" * 100)
    print("  v7_timecap.py:65  entry = float(candles[i]['close'])  <- signal")
    print("  bar's own close.  Exits already fill at next OPEN (:167,:182).")
    print("  (a) signal-bar close [SHIPPED]  (b) next 15m open  "
          "(c) next open + %dbp slip" % (SLIP * 10000))
    print("  Mechanism falsifier: (b)-(a) must LOAD ON VOLATILITY.")
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
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            tr, c15 = books[(name, scope)]
            base = net_of(tr)
            ts = [int(c["ts"]) for c in c15]
            cl = [float(c["close"]) for c in c15]
            tr_ = [float(c["high"]) - float(c["low"]) for c in c15]
            print("  --- [%s] shipped %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(tr), base))
            print("      %-30s %6s %9s %8s %7s %11s"
                  % ("fill", "n", "net", "R/t", "PF", "dNet vs shipped"))
            res = {}
            for lbl, mode in (("(a) signal-bar close [shipped]", None),
                              ("(b) next 15m open", "open"),
                              ("(c) next open + slip", "slip")):
                sub = tr if mode is None else refill(tr, c15, mode)
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                res[mode] = (rs, net)
                print("      %-30s %6d %+9.1fR %+8.3f %7.2f %+9.1fR%s"
                      % (lbl, len(rs), net, net / len(rs), pf(rs),
                         net - base,
                         "  <-- EXCEEDS M" if abs(net - base) > M_NULL
                         else ""))
            # mechanism: does the refit cost load on volatility?
            rb, nb = res["open"]
            # cost per trade, signed, vs the bar's ATR%
            tsx = ts
            idx = []
            atr = []
            for t in tr:
                j = bs.bisect_left(tsx, int(t["entry_ts"]))
                if j <= 0:
                    continue
                lo = max(0, j - ATR_BARS)
                seg = tr_[lo:j]
                pxl = cl[j - 1]
                if not seg or pxl <= 0:
                    continue
                idx.append(j)
                atr.append((sum(seg) / len(seg)) / pxl * 100.0)
            # per-trade R delta (open - shipped)
            d_r = []
            for t, t2 in zip(tr, [x for x in refill(tr, c15, "open")]):
                d_r.append(float(t2["r_multiple"]) - float(t["r_multiple"]))
            # align lengths safely
            k = min(len(d_r), len(atr))
            if k > 3:
                c = corr(d_r[:k], atr[:k])
                print("      mechanism: corr(dR per trade, ATR%% of that bar) "
                      "= %+.3f  over %d trades" % (c, k))
                if c == c and abs(c) < 0.05:
                    print("      !! NO CORRELATION - the stated mechanism "
                          "(re-fill cost scales with the bar's range) is "
                          "NOT visible. Treat the dNet above with suspicion.")
            lng = [t for t in tr if t["dir"] == "long"]
            sht = [t for t in tr if t["dir"] != "long"]
            sub_o = refill(tr, c15, "open")
            ol = [t for t in sub_o if t["dir"] == "long"]
            os_ = [t for t in sub_o if t["dir"] != "long"]
            print("      split: longs %dt %+.1fR -> %+.1fR | shorts %dt "
                  "%+.1fR -> %+.1fR"
                  % (len(lng), net_of(lng), net_of(ol), len(sht),
                     net_of(sht), net_of(os_)))
            print()
    print("  This is a MEASUREMENT, not a candidate. Nothing adopted.")


if __name__ == "__main__":
    main()