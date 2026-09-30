"""P68 - A REAL VOLATILITY FLOOR, PLUS THE PRICE QUESTION, DONE PROPERLY.

THE BUG IN P67, WHICH ALSO EXPLAINS THE OWNER'S PRICE INTUITION
    P67 defined trailing_atr_pct with a docstring saying "divided by the
    close at that point" and a body that did not divide by anything. The
    reported numbers - IS low-bound 151.8, OOS low-bound 140.2 - are ABSOLUTE
    true range in dollars, not a percentage.

    That is not a cosmetic bug. Absolute ATR is a product of price level and
    volatility, so P67 never tested volatility at all: it tested a variable
    that changes because BTC went from ~$40k in 2021-22 to ~$60k in 2023-26.
    P67's own observation that "the tertile bounds differ between eras" was
    therefore mostly a PRICE observation wearing a volatility label, and the
    conclusion drawn from it - that the eras' volatility distributions overlap
    - was not supported by the test that produced it.

    The owner was right that price was likely the shape of this. The fix is
    to normalise, and then to actually test price on its own terms.

TWO FEATURES, BOTH CAUSAL BY CONSTRUCTION
    VOL  trailing ATR% = mean(TR over last 96 x 15m) / close at that point.
         Only bars at or before the trade's own entry_ts. This is P67's
         stated feature, now actually implemented.
    PX   the price level itself, read at the trade's entry_ts.

    Both are computed outside the engine so they cannot collide with an
    engine-local name, and both are computed from bars the trade could
    plausibly have seen.

PART A - THE VOLATILITY FLOOR SWEEP, FAMILY-WISE
    Grid on VOL, pre-registered before running: 0.40, 0.60, 0.80, 1.00,
    1.20, 1.50 percent. The rule is "trade only when trailing ATR% is at or
    above the floor" - a floor, not a ceiling, because P67 found the book
    works in the calm third, and a floor is the only live-computable form
    of that: it says "stand aside when the market is unusually quiet for
    its own recent history".

    FAMILY-WISE, and stated before running: every floor must beat the
    control in BOTH eras in BOTH lanes AND clear M = 193.4R, or NONE is
    adopted. Six floors is six chances to look good; requiring all six is
    what stops this from being a disguised threshold search. No floor is
    selected for being the prettiest.

PART B - PRICE ON ITS OWN TERMS
    The owner's question that P67 accidentally failed to answer. Split each
    book at the median PRICE LEVEL of its own distribution and compare. If
    price is the separator, the champion should degrade in the high-price
    half in both eras, and the era effect should shrink once normalised.

WHAT WOULD MAKE ANY OF THIS ADOPTABLE
    Both parts are filters, and this programme's record on filters is poor.
    The one thing that distinguishes P67's volatility effect from the ones
    that failed was that it held in all four cells. These tests are run to
    find out whether that survives a floor the live system could actually
    apply, and the answer is reported whichever way it lands.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos
from run_experiment import _trade_costs, fund, _g

M_NULL = 193.4
ATR_BARS = 96
# percent, pre-registered before the run; family-wise: all six must pass
FLOORS = (0.40, 0.60, 0.80, 1.00, 1.20, 1.50)
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    """Net of costs, on the pins' own basis - see P60's gross-vs-net error."""
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def as_flow(c):
    from src.walker import FlowCandle
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def feats(c15):
    """(ts array, close array, tr array) for true range and close level."""
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


def feat_at(ts, cl, tr, t):
    """ATR% AND price at a trade's entry_ts, using only bars <= entry_ts.

    This is the function P67 got wrong: it returned mean(TR) in dollars. The
    division by close is the whole point and was missing.
    """
    i = bs.bisect_right(ts, int(t["entry_ts"]))
    if i <= 0:
        return None, None
    j = bs.bisect_left(ts, int(t["entry_ts"]))
    lo = max(0, j - ATR_BARS)
    seg = tr[lo:j] if j > 0 else tr[lo:i]
    if not seg or j == 0:
        return None, None
    px = cl[j - 1]
    if px <= 0:
        return None, None
    return (sum(seg) / len(seg)) / px * 100.0, px


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def main():
    print("=" * 100)
    print("  P68  A REAL VOLATILITY FLOOR, AND PRICE ON ITS OWN TERMS")
    print("=" * 100)
    print("  P67 returned mean(TR) in DOLLARS despite a docstring promising")
    print("  a percentage. Fixed here: ATR%% = mean(TR)/close. Absolute ATR is")
    print("  price x volatility, so P67 never tested volatility alone.")
    print("  Floors (%%, family-wise, all must pass): %s\n"
          % (FLOORS,))

    import test_experiments_craze as tc
    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"], d["sw10"], d["sw15"]),
           "oos": (oc1h, oc15, oos_fine,
                   tc._compute_swings(as_flow(oc1h), "continuous", min_bars=10),
                   tc._compute_swings(as_flow(oc15), "continuous", min_bars=50))}

    results = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine, sw10, sw15 = src[scope]
            tr_all = [t for t in tc.build_module()(
                c_htf, sw10, c_ltf, sw15, fine, **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr_all) - pin[i][0]) > 2
                    or abs(net_of(tr_all) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(tr_all), net_of(tr_all), *pin[i]))
                return
            ts, cl, tr = feats(c_ltf)
            rows = []
            for t in tr_all:
                v, px = feat_at(ts, cl, tr, t)
                if v is not None:
                    rows.append((t, v, px))
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(tr_all), net_of(tr_all)))
            print("      ATR%% range %.3f-%.3f  |  price range %,.0f-%,.0f"
                  % (min(r[1] for r in rows), max(r[1] for r in rows),
                     min(r[2] for r in rows), max(r[2] for r in rows))
                  if False else
                  "      ATR%% range %.3f - %.3f  |  price range %.0f - %.0f"
                  % (min(r[1] for r in rows), max(r[1] for r in rows),
                     min(r[2] for r in rows), max(r[2] for r in rows)))
            print("      %-8s %6s %9s %8s %6s   %s"
                  % ("floor%", "n", "net", "R/t", "PF", "dNet vs control"))
            for fl in FLOORS:
                sub = [r[0] for r in rows if r[1] >= fl]
                if not sub:
                    print("      %-8.2f %6d   (no trades at or above floor)"
                          % fl)
                    continue
                net = net_of(sub)
                rs = [float(t["r_multiple"]) for t in sub]
                dv = net - net_of(tr_all)
                results.setdefault((name, fl), []).append(dv)
                print("      %-8.2f %6d %+9.1fR %+8.3f %6.2f   %+9.1fR%s"
                      % (fl, len(rs), net, net / len(rs), pf(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            med = sorted(r[2] for r in rows)[len(rows) // 2]
            print("      --- price median %.0f ---" % med)
            for rlbl, keep in (("LOW px", lambda p: p <= med),
                               ("HIGH px", lambda p: p > med)):
                sub = [r[0] for r in rows if keep(r[2])]
                if not sub:
                    continue
                rs = [float(t["r_multiple"]) for t in sub]
                net = net_of(sub)
                print("      %-8s %6d %+9.1fR %+8.3f %6.2f   %+9.1fR"
                      % (rlbl, len(rs), net, net / len(rs), pf(rs),
                         net - net_of(tr_all)))
            print()
    print("  " + "=" * 98)
    print("  FAMILY-WISE VERDICT (all eras, both lanes, must beat AND clear M)")
    print("  " + "=" * 98)
    for (name, fl), v in sorted(results.items(),
                                key=lambda kv: (kv[0][0], kv[0][1])):
        if len(v) < 2:
            continue
        ok = all(x > 0 for x in v) and all(abs(x) > M_NULL for x in v)
        print("    %-22s floor %4.2f%%   cells %s   %s"
              % (name, fl, " ".join("%+.1fR" % x for x in v),
                 "PASSES" if ok else "fails"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()