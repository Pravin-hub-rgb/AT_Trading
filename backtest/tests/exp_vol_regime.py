"""P67 - IS THE 30m/15m SPLIT A VOLATILITY REGIME THING?

THE OWNER'S HYPOTHESIS
    P66 found 30m roughly doubles the champion in OOS (+141.9R vs +70.1R,
    every quality measure better at once) and costs 188-239R in IS. The
    owner's explanation is price- and volatility-shaped: OOS is 2021-2022,
    when BTC spent most of its time in a far lower and calmer band than
    the 2023-2026 IS era. If that is what separates them, then the switch
    should be made on VOLATILITY - low vol wants 30m, high vol wants 15m.

WHY THIS IS NOT P55 AGAIN
    P55 failed to build an adaptive gate, but it failed on SWING GEOMETRY -
    travel/ATR over trailing K swings - whose IS and OOS distributions were
    indistinguishable (medians within 0.01-0.10 against an IQR of 0.75).
    Volatility is not that. It is directly observable at decision time, it
    needs no identification of anything latent, and 2022 versus 2024 is a
    difference no forward feature would have to guess at.

    If this test finds the two books separate cleanly on a causal vol
    feature, then unlike everything since P55 there is a live gate here.
    If it does not, then the 30m/15m split is an era artefact after all and
    the honest answer is the wall P55 already found.

THE FEATURE - CAUSAL BY CONSTRUCTION
    Trailing ATR% on the 15m series: mean true range over the last 96 bars
    (24 hours), divided by the close at that point, measured using ONLY
    bars at or before each trade's own entry_ts. No future bar is read, and
    the feature is computed OUTSIDE the engine so it cannot collide with
    an engine-local name.

    Split points are the tertiles of each book's OWN trailing-vol
    distribution - self-referencing, so no threshold is imported from a
    different era or fitted to the answer.

TESTS, ALL PRE-REGISTERED
    T1 Does R/trade separate between the books in the low-vol tercile, and
       again in the high-vol tercile, and do the two comparisons point in
       OPPOSITE directions? That is the whole hypothesis. Opposite signs is
       the finding; same sign kills it.
    T2 Where is the crossover? Reported as a vol quantile, not as a tuned
       threshold - a threshold chosen by looking would be a fitted gate.

PASS CRITERION - UNCHANGED AND STATED BEFORE RUNNING
    An adaptive LTF switch is only interesting if the low-vol comparison
    favours 30m AND the high-vol comparison favours 15m AND the gap in each
    is larger than the noise. Anything less is an era artefact with extra
    steps, and the answer is to keep the champion's 15m.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos
from test_experiments_craze import _compute_swings
from src.walker import FlowCandle

M_NULL = 193.4
ATR_BARS = 96            # 96 x 15m = 24 hours of trailing history
TERTILES = (0.33, 0.67)
LTF = [("15m", 1, 50), ("30m", 2, 25)]    # champion, and the challenger
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def agg(candles, k, src_sec, min_frac=0.8):
    """k source bars -> one bar of width src_sec*k, stamped with the ts of
    the LAST source bar so it is visible only at its own close. Width is
    src_sec*k, NOT DAY*k (the P57 bug). 80% fill, since this data runs
    23.99 hours per day."""
    need, width, out, b = max(1, int(k * min_frac)), src_sec * k, [], []
    for c in candles:
        if b and (int(b[0]["ts"]) // width) != (int(c["ts"]) // width):
            if len(b) >= need:
                out.append({"date": b[-1]["date"], "ts": int(b[-1]["ts"]),
                            "open": b[0]["open"],
                            "high": max(x["high"] for x in b),
                            "low": min(x["low"] for x in b),
                            "close": b[-1]["close"],
                            "volume": sum(x.get("volume", 0.0) for x in b)})
            b = []
        b.append(c)
    return out


def trailing_atr_pct(c15, atrs, ts):
    """ATR% measured at ts using ONLY bars at or before ts.

    Built as a sorted prefix so a lookup is a bisect, and the value returned
    is the mean of the last ATR_BARS true ranges strictly before `ts`.
    """
    import bisect as bs
    i = bs.bisect_left(atrs[0], ts)
    if i <= 0:
        return None
    lo = max(0, i - ATR_BARS)
    seg = atrs[1][lo:i]
    return (sum(seg) / len(seg)) if seg else None


def atr_series(c15):
    ts, tr = [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        tr.append(r)
        prev = float(c["close"])
    return (ts, tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def tercile_bounds(vals):
    s = sorted(vals)
    n = len(s)
    return s[int(n * TERTILES[0])], s[int(n * TERTILES[1])]


def main():
    print("=" * 100)
    print("  P67  IS THE 30m/15m SPLIT A VOLATILITY REGIME THING?")
    print("=" * 100)
    print("  Feature: trailing ATR%% over %d x 15m (24h), computed OUTSIDE the"
          % ATR_BARS)
    print("  engine from bars at or before each trade's own entry_ts.")
    print("  Split at each book's OWN tertiles - no imported threshold.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"], d["sw10"], d["sw15"]),
           "oos": (oc1h, oc15, oos_fine,
                   _compute_swings(as_flow(oc1h), "continuous", min_bars=10),
                   _compute_swings(as_flow(oc15), "continuous", min_bars=50))}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine, sw10, sw15 = src[scope]
            at = atr_series(c_ltf)
            ctl = [t for t in tc.build_module()(c_htf, sw10, c_ltf, sw15,
                                                fine, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            l30 = agg(c_ltf, 2, 900)
            b30 = [t for t in tc.build_module()(
                c_htf, sw10, l30,
                _compute_swings(as_flow(l30), "continuous", min_bars=25),
                fine, **params)["ltf_trades"] if t.get("outcome") != "open"]
            print("  --- [%s] control 15m %dt %+.1fR (PIN ok) | 30m %dt %+.1fR"
                  % (scope.upper(), len(ctl), net_r(ctl), len(b30), net_r(b30)))

            books = {}
            for lbl, tr in (("15m", ctl), ("30m", b30)):
                rows = []
                for t in tr:
                    v = trailing_atr_pct(c_ltf, at, int(t["entry_ts"]))
                    if v is not None:
                        rows.append((v, float(t["r_multiple"])))
                books[lbl] = rows
            lo, hi = tercile_bounds([v for v, _ in books["15m"]])
            print("      ATR%% tertiles from the 15m book: low<%.5f  "
                  "high>%.5f" % (lo, hi))
            print("      %-6s %-7s %6s %9s %8s %6s  %6s"
                  % ("book", "regime", "n", "net", "R/t", "PF", "WR"))
            res = {}
            for lbl in ("15m", "30m"):
                for rlbl, f in (("LOW", lambda v: v < lo),
                                ("HIGH", lambda v: v >= hi)):
                    rs = [r for v, r in books[lbl] if f(v)]
                    res[(lbl, rlbl)] = rs
                    if not rs:
                        continue
                    print("      %-6s %-7s %6d %+9.1fR %+8.3f %6.2f %5.1f%%"
                          % (lbl, rlbl, len(rs), sum(rs), sum(rs) / len(rs),
                             pf(rs),
                             100.0 * sum(1 for x in rs if x > 0) / len(rs)))
            a, b = res[("30m", "LOW")], res[("15m", "LOW")]
            c, e = res[("30m", "HIGH")], res[("15m", "HIGH")]
            print("      LOW  vol: 30m-15m R/trade = %+.3f  -> %s"
                  % (sum(a) / len(a) - sum(b) / len(b),
                     "30m better" if sum(a) / len(a) > sum(b) / len(b)
                     else "15m better"))
            print("      HIGH vol: 30m-15m R/trade = %+.3f  -> %s"
                  % (sum(c) / len(c) - sum(e) / len(e),
                     "30m better" if sum(c) / len(c) > sum(e) / len(e)
                     else "15m better"))
            print()
    print("  Hypothesis confirmed only if LOW favours 30m AND HIGH favours")
    print("  15m. Same sign in both means the split is an era artefact.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()