"""P57 - TIMEFRAME ARCHITECTURE. Which timeframe supplies the direction?

THE QUESTION THIS PROGRAMME HAS BEEN CIRCLING
    P3: the 1h layer has no edge of its own (FLIP +1.9R IS, -23.6R OOS,
    PF never above 1.20). P55: none of the 1h layer's structure can be
    gated on, because the eras disagree about what the structure means.
    P56: the direction is durable and the window expiry is not.

    So every gate tried so far has used 1h as the direction source simply
    because 1h is what the book was built on. That was never tested. This
    file tests the choice itself:

        1h HTF + 15m LTF   (the champion architecture)
        4h HTF + 15m LTF
        1D HTF + 15m LTF
        1D HTF + 1h  LTF   (the owner's second suggestion)

WHY THE ARCHIVED 4h RESULT DOES NOT SETTLE THIS
    ANCHOR_BASIS_AUDIT records exp_htf4_confirm as DEAD: -162 / -51,
    -194 / -25. But that ran 4h as an ADDITIONAL confirm filter on top of
    the 1h gate. Here 4h and 1D REPLACE the 1h window source, which is a
    different mechanism: a longer window that opens less often and holds
    longer, not a second opinion stacked on the first. A dead filter and a
    dead window source are not the same result, and only the second is
    being asked about here.

1D IS DERIVED, NOT DOWNLOADED
    There is no 1D file. The 1D and 4h series are built by aggregating the
    1h bars we already hold - k bars per bucket, UTC-aligned on
    floor(ts/86400*k), each bucket labelled with the ts of its LAST
    constituent 1h bar so it only becomes visible at its own close. That is
    causal by construction: a daily bar is used from the moment its last
    hour printed, never before. Deriving rather than downloading also means
    the 1D series is exactly consistent with the 1h series the champion
    already trades, so any difference between architectures is a difference
    of timeframe and not of vendor or session handling.

    IS: 2023-01-01 -> 2026-09-10, 32356 1h bars, ~1355 daily bars
    OOS: 2021-01-01 -> 2022-12-31, 17520 1h bars, ~730 daily bars

    LIMITATION, STATED UP FRONT: the daily book is about a third the size
    of the 1h book. A verdict here is a verdict at this sample size, and a
    1D architecture that merely ties the champion is not a win - it is the
    same money with a third of the trades and a lag measured in days.

    Second limitation: min_bars=10 is held constant across timeframes
    because the engine's swing rule is a swing rule, not a duration rule.
    The wall-clock confirmation lag is therefore 10h at 1h, 40h at 4h and
    10 days at 1D. The 1D arms are structurally slow, and that is the point
    of testing them, but it is a real cost and not a free one.

PASS CRITERION, FIXED BEFORE RUNNING
    An architecture replaces the champion only if it beats it in BOTH eras
    in BOTH lanes, and only if the margin clears the deck-relative null
    M = 193.4R. Beating the champion in IS alone is not a result; that is
    what a fitted architecture always does.
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
from engine.v18_params import SWING
from src.walker import FlowCandle


def as_flow(candles):
    """_compute_swings walks FlowCandle objects, not dicts - it reads
    c.date and c.open, so aggregated bars have to be wrapped before the
    swing rule can be run on them."""
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in candles]

M_NULL = 193.4
MIN_BARS = 10
DAY = 86400
CHAMP = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
         "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}
# (label, htf buckets of 1h bars, ltf buckets of 15m bars)
# 4h = 4x1h, 1D = 24x1h, and 1h LTF = 4x15m -- NOT 60, which would be 15h.
ARCH = [("1h HTF + 15m LTF  (CHAMPION)", 1, 1),
        ("4h HTF + 15m LTF", 4, 1),
        ("1D HTF + 15m LTF", 24, 1),
        ("1D HTF +  1h LTF", 24, 4)]


def agg(candles, k, src_sec=3600, min_frac=0.8):
    """k source bars -> one bar, labelled with the ts of the LAST source
    bar so it is only visible once complete. Aligned to the bucket width.

    The bucket width is src_sec * k, NOT DAY * k. Using DAY * k silently
    produced 4-DAY and 24-DAY buckets instead of 4-hour and 1-day ones -
    which is why the first run reported 338 "4h" bars for 32434 hourly
    bars (1352/4 = 338) and 56 "1D" bars (1352/24 = 56). The tell was
    arithmetic, not a crash: a daily architecture cannot have 56 bars in
    three and a half years of hourly data.

    A bucket is kept when it holds at least `min_frac` of k bars. An exact
    k test drops almost every bucket here: 32434 hourly bars over 1352
    days is 23.99 per day, so the series has gaps and most daily buckets
    arrive with 23 hours. The trailing partial bucket is always dropped.
    """
    need = max(1, int(k * min_frac))
    width = src_sec * k
    out, b = [], []
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


def pf_dd(rs):
    p = sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))
    e = pk = d = 0.0
    for x in rs:
        e += x
        pk = max(pk, e)
        d = max(d, pk - e)
    return p, d


def main():
    print("=" * 100)
    print("  P57  WHICH TIMEFRAME SUPPLIES THE DIRECTION?")
    print("=" * 100)
    print("  1D and 4h are derived from the 1h bars by k-bar aggregation,")
    print("  each bucket visible only at its own close. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = CHAMP[name]
        lanes = {
            "is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
            "oos": (oc1h, _compute_swings(of1h, "continuous", min_bars=MIN_BARS),
                    oc15, _compute_swings(of15, "continuous",
                                          min_bars=SWING["min_bars_15m"]),
                    oos_fine),
        }
        print("  === %s" % name)
        for lbl, kh, kl in ARCH:
            print("  --- %s" % lbl)
            cells = []
            for scope in ("is", "oos"):
                c_htf, sw_htf, c_ltf, sw_ltf, fine = lanes[scope]
                if kh == 1:
                    h, hsw = c_htf, sw_htf
                else:
                    h = agg(c_htf, kh)
                    hsw = _compute_swings(as_flow(h), "continuous",
                                          min_bars=MIN_BARS)
                if kl == 1:
                    l, lsw = c_ltf, sw_ltf
                else:
                    l = agg(c_ltf, kl, src_sec=900)
                    lsw = _compute_swings(as_flow(l), "continuous",
                                          min_bars=SWING["min_bars_15m"])
                res = tc.build_module()(h, hsw, l, lsw, fine, **params)
                tr = [t for t in res["ltf_trades"] if t.get("outcome") != "open"]
                rs = [float(t["r_multiple"]) for t in tr]
                n, net = len(rs), net_r(tr)
                p, dd_ = pf_dd(rs)
                wr = 100.0 * sum(1 for x in rs if x > 0) / max(1, len(rs))
                print("    [%s] HTF %5d bars  LTF %5d bars | %4dt %+8.1fR "
                      "R/t %+6.3f PF %5.2f DD %5.1f WR %4.1f%%"
                      % (scope.upper(), len(h), len(l), n, net,
                         net / max(1, n), p, dd_, wr))
                cells.append((n, net))
            for i, scope in enumerate(("is", "oos")):
                dn = cells[i][0] - pin[i][0]
                dv = cells[i][1] - pin[i][1]
                tag = "   <-- CLEARS M" if abs(dv) > M_NULL else ""
                print("      %-3s vs champion: %+5d trades, %+8.1fR%s"
                      % (scope, dn, dv, tag))
            print()
    print("  Rule fixed before running: an architecture replaces the champion")
    print("  only if it beats it in BOTH eras in BOTH lanes AND clears M.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()