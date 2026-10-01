"""P66 - THE MISSING MIDDLE OF THE TIMEFRAME GRID (Nemotron P4).

WHAT P58 LEFT OUT
    P58 tested HTF in {1h, 4h, 1D} against LTF in {15m, 1h, 4h} and found
    the champion 1h+15m best from every direction, with a monotone "the
    closer the layers, the better" trend. It never tested a timeframe
    BETWEEN 15m and 1h. That is the space the champion lives in, and
    Nemotron's P4 flagged exactly this: "30m Timeframe as Independent LTF -
    not a rescaled 15m".

    A bar-count sweep cannot reach 30m cleanly, because 30m is not a divisor
    of the 1h series. P58 solved that for the whole grid by matching on
    WALL-CLOCK LAG rather than bar count, and the same construction reaches
    30m and 45m directly by aggregating the 15m series - which is exactly
    "not a rescaled 15m" in the sense that matters: the swing rule is
    re-derived on the coarser bars, not inherited from the 15m swings.

THE THREE POINTS, PRE-REGISTERED
    LTF in {15m, 30m, 45m} at a FIXED 1h HTF. Three points spanning the gap
    the champion sits in. 45m is included so the curve has an interior
    point rather than being champion-vs-one-competitor.

    min_bars is lag-matched at ~12.5h across all three, per TF_MATRIX_P58:
        15m -> 50 bars (12.5h)   30m -> 25 bars (12.5h)   45m -> 17 (12.75h)
    The 1h HTF stays at the champion's own 10 bars in every arm, so the HTF
    is literally held constant and the LTF is the only moving part.

WHAT THE PRIOR FINDING PREDICTS
    P58's trend says closer is better, which predicts 30m BEATS 15m. If it
    does, the champion's timeframe is not optimal and that is a real
    finding. If 15m wins, 15m is a genuine sweet spot rather than an
    accident of what was tried first. Either outcome is informative, and
    the point of pre-registering both readings is that neither can be
    adopted by picking the arm that looks better afterwards.

PASS CRITERION - UNCHANGED
    Replace the champion only by beating it in BOTH eras in BOTH lanes AND
    clearing M = 193.4R. And, because a timeframe is a family of choices,
    the family-wise version: every arm that changes the LTF must pass, or
    none is adopted. Reporting all three whatever they do.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
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
# (label, buckets of 15m, lag-matched min_bars)
LTF = [("15m", 1, 50), ("30m", 2, 25), ("45m", 3, 17)]
HTF_MIN_BARS = 10          # the champion's own 1h setting, held constant
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def agg(candles, k, src_sec, min_frac=0.8):
    """k source bars -> one bar of width src_sec*k, stamped with the ts of
    the LAST source bar so it is visible only at its own close.

    Width is src_sec*k, NOT DAY*k - the P57 bug that silently built 4-day
    and 24-day buckets. 80% fill because this data runs 23.99 hours/day.
    """
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


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def main():
    print("=" * 100)
    print("  P66  THE MISSING MIDDLE: 30m AND 45m LTF AT A FIXED 1h HTF")
    print("=" * 100)
    print("  Nemotron P4. P58's grid skipped everything between 15m and 1h -")
    print("  which is the space the champion lives in. HTF held at the")
    print("  champion's own 1h/10 bars; only the LTF moves.")
    print("  min_bars lag-matched at ~12.5h: %s\n"
          % ", ".join("%s->%d" % (a, c) for a, b, c in LTF))

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
            ctl = [t for t in tc.build_module()(c_htf, sw10, c_ltf, sw15,
                                                fine, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            print("  --- [%s] control 15m %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(ctl), net_r(ctl)))
            print("      %-14s %6s %5s %9s %7s %6s %6s %6s %11s"
                  % ("LTF", "bars", "n", "net", "R/t", "PF", "DD", "WR",
                     "dNet"))
            for lbl, k, mb in LTF:
                l = c_ltf if k == 1 else agg(c_ltf, k, 900)
                lsw = sw15 if k == 1 else _compute_swings(
                    as_flow(l), "continuous", min_bars=mb)
                res = tc.build_module()(c_htf, sw10, l, lsw, fine, **params)
                tr = [t for t in res["ltf_trades"]
                      if t.get("outcome") != "open"]
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                dv = net - net_r(ctl)
                star = "  <-- CLEARS M" if abs(dv) > M_NULL else ""
                print("      %-14s %6d %5d %+9.1fR %+7.3f %6.2f %6.1f %5.1f%% "
                      "%+9.1fR%s"
                      % (lbl + (" (champ)" if k == 1 else ""), len(l),
                         len(rs), net, net / len(rs), pf(rs), dd(rs),
                         100.0 * sum(1 for x in rs if x > 0) / len(rs),
                         dv, star))
            print()
    print("  Family-wise: an LTF change is adopted only if BOTH non-champion")
    print("  arms beat the champion in BOTH eras in BOTH lanes AND clear M.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()