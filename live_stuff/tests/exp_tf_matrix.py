"""P58 - THE FULL 3x3 MATRIX, AND A CONFOUND P57 GOT WRONG.

THE OWNER'S CELL
    P57 left 1D HTF + 4h LTF untested and, more importantly, left open a
    methodological hole. This file fills both.

THE CONFOUND, STATED PLAINLY
    P57 held min_bars=10 constant across every HTF timeframe. That is a
    swing COUNT, not a swing LAG. Its wall-clock confirmation lag is
    therefore 10h at 1h, 40h at 4h and 10 DAYS at 1D - so P57 was quietly
    charging the slow architectures a lag penalty of up to 24x. Every
    conclusion that the slower timeframes lose could be an artefact of
    that penalty rather than a property of the timeframe.

    Worse, P57 built the 1D + 1h LTF arm with min_bars=50, which is the
    15m constant. On 1h bars that is a FIFTY HOUR lag. That arm's 66 IS
    trades and 37 OOS trades are largely a lag artefact, and its verdict
    should not be trusted as it stands.

    The fix is to hold the WALL-CLOCK lag fixed instead, which is what the
    champion already does by accident: its 1h HTF uses 10 bars = 10h and
    its 15m LTF uses 50 bars = 12.5h. Both layers confirm a swing in about
    half a day, and that is the champion's design point:

        HTF  1h -> 10 bars (10.0h)   4h -> 3 bars (12.0h)   1D -> 1 (24h)
        LTF 15m -> 50 bars (12.5h)   1h -> 12 bars (12.0h)  4h -> 3 (12.0h)

    1D is pinned at 1 bar because that is the floor - one daily bar is one
    day, and no parameter makes a daily swing confirm faster than its own
    period. So the 1D arms still carry a 24h lag against the champion's
    10h, and that residual 2.4x is a real structural property of trading
    daily rather than a tuning failure. It is reported, not engineered away.

    IDENTITY CHECK BUILT IN: the 1h+15m cell under this convention uses
    exactly the champion's own parameters (10 and 50), so it must reproduce
    500t/+325.8R IS and 279t/+70.1R OOS. If it does not, the convention is
    wrong and nothing else in the table means anything.

THE HYPOTHESES THIS MATRIX SEPARATES
    P57 found a monotone trend and read it as "closer is better". That
    reading confounds two effects, and this grid separates them:

      H_ratio   only the HTF/LTF DISTANCE matters. Then 1D+4h (distance 6,
                near the champion's 4) should be roughly as good as the
                champion, even though its HTF is daily.
      H_speed   the HTF's own SPEED matters. Then 1D+4h should be dead,
                because every 1D arm in P57 was dead, whatever sits
                underneath it.

    1D + 4h discriminates because the two hypotheses predict opposite
    things for it. 1h + 4h is the control on the other side - same distance
    6, but no daily problem - so it should be healthy under both.

    Distance in timeframe multiples: 1h/15m=4, 4h/15m=16, 1D/15m=96,
    1D/1h=24, 1D/4h=6, 1h/1h=1, 4h/1h=4, 1h/4h=6, 4h/4h=1.

PASS CRITERION - UNCHANGED FROM P57
    Replace the champion only if it beats it in BOTH eras in BOTH lanes and
    clears the deck-relative null M = 193.4R.
"""


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
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
CHAMP = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
         "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}

# (htf label, htf buckets of 1h, htf min_bars)
HTF = [("1h", 1, 10), ("4h", 4, 3), ("1D", 24, 1)]
# (ltf label, ltf buckets of 15m, ltf min_bars)
LTF = [("15m", 1, 50), ("1h", 4, 12), ("4h", 16, 3)]


def as_flow(candles):
    """_compute_swings walks FlowCandle objects, not dicts - it reads
    c.date and c.open, so aggregated bars must be wrapped first."""
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in candles]


def agg(candles, k, src_sec, min_frac=0.8):
    """k source bars -> one bar of width src_sec*k, stamped with the ts of
    the LAST source bar so it is visible only at its own close.

    Bucket width is src_sec*k, NOT DAY*k - the P57 bug that silently built
    4-DAY and 24-DAY buckets. 80% fill because this data runs 23.99 hours
    per day, so an exact fill test drops nearly every bucket.
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



def main():
    print("=" * 104)
    print("  P58  FULL 3x3 MATRIX, WALL-CLOCK-LAG-MATCHED (P57's FIX)")
    print("=" * 104)
    print("  min_bars chosen so every arm confirms a swing in ~10-12h.")
    print("  1D is pinned at 1 bar - a daily swing cannot confirm faster")
    print("  than its own period. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"]),
           "oos": (oc1h, oc15, oos_fine)}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = CHAMP[name]
        cache = {}

        def series(role, scope, tf, mb):
            """(candles, swings) for one layer, memoised per lane.

            ROLE matters: "1h" is both an HTF and an LTF here, and they are
            built from different source series - the HTF ladder from the
            1h bars, the LTF ladder from the 15m bars. A first version
            keyed the cache on (scope, tf) only, and because the 15m IS arm
            matched no branch it silently fell through to the HTF series:
            32434 LTF bars instead of 129736, 320 trades instead of 500.
            The built-in identity check caught it before any cell was read.
            """
            key = (role, scope, tf)
            if key in cache:
                return cache[key]
            c_htf, c_ltf, _ = src[scope]
            if role == "htf":
                if tf == "1h":
                    c = c_htf
                    sw = d["sw10"] if scope == "is" else \
                        _compute_swings(as_flow(c_htf), "continuous",
                                        min_bars=mb)
                else:
                    c = agg(c_htf, 4 if tf == "4h" else 24, 3600)
                    sw = _compute_swings(as_flow(c), "continuous", min_bars=mb)
            else:
                if tf == "15m":
                    c = c_ltf
                    sw = d["sw15"] if scope == "is" else \
                        _compute_swings(as_flow(c_ltf), "continuous",
                                        min_bars=mb)
                else:
                    c = agg(c_ltf, 4 if tf == "1h" else 16, 900)
                    sw = _compute_swings(as_flow(c), "continuous", min_bars=mb)
            cache[key] = (c, sw)
            return cache[key]

        print("  " + "=" * 102)
        print("  LANE: %s" % name)
        print("  " + "=" * 102)
        for hlab, kh, hmb in HTF:
            for llab, kl, lmb in LTF:
                if hlab == llab:
                    continue
                tag = "   <-- OWNER'S CELL" if (hlab, llab) == ("1D", "4h") \
                    else ""
                if (hlab, llab) == ("1h", "15m"):
                    tag = "   (CHAMPION - identity check)"
                print("  --- %2s HTF + %2s LTF%s" % (hlab, llab, tag))
                cells = []
                for i, scope in enumerate(("is", "oos")):
                    h, hsw = series("htf", scope, hlab, hmb)
                    l, lsw = series("ltf", scope, llab, lmb)
                    res = tc.build_module()(h, hsw, l, lsw, src[scope][2],
                                            **params)
                    tr = [t for t in res["ltf_trades"]
                          if t.get("outcome") != "open"]
                    rs = [float(t["r_multiple"]) for t in tr]
                    n, net = len(rs), net_r(tr)
                    print("      [%s] HTF %5d bars  LTF %5d bars | %4dt "
                          "%+8.1fR R/t %+6.3f PF %5.2f WR %4.1f%%"
                          % (scope.upper(), len(h), len(l), n, net,
                             net / max(1, n), pf(rs), 100.0
                             * sum(1 for x in rs if x > 0) / max(1, len(rs))))
                    cells.append((n, net))
                    if (hlab, llab) == ("1h", "15m") and (
                            abs(n - pin[i][0]) > 2
                            or abs(net - pin[i][1]) > 1.5):
                        print("      *** IDENTITY CHECK FAILED (pin %dt "
                              "%+.1fR) - convention wrong, stop ***" % pin[i])
                        return
                for i, scope in enumerate(("is", "oos")):
                    dv = cells[i][1] - pin[i][1]
                    print("      %-3s vs champion: %+5d trades, %+8.1fR%s"
                          % (scope, cells[i][0] - pin[i][0], dv,
                             "   <-- CLEARS M" if abs(dv) > M_NULL else ""))
                print()
    print("  Rule: beat the champion in BOTH eras in BOTH lanes AND clear M.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()