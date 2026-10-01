"""P61 - IS THE QUALITY ADVANTAGE STABLE, AND WHAT DOES FORWARD DATA SAY?

PART A - THE STABILITY TEST (b)
    The open question after P60: cand_4h1h is BETTER than the champion on
    every quality measure in BOTH eras - R/trade, PF and win rate - and
    still nets 113R less in IS. The obvious reading is "smaller book, same
    quality, fewer bets". The worrying reading is "the quality advantage is
    concentrated in a few lucky months and will not survive".

    Those are separated by splitting each era into calendar periods and
    asking how OFTEN the candidate's R/trade beats the champion's. If it
    wins in most periods in BOTH eras, the advantage is a property of the
    architecture. If it wins in one or two, the IS gap is a coincidence of
    weighting and cand_4h1h is not a stable book at all.

    PARTITIONED BY TIME, NOT BY OUTCOME. A period is a date range, fixed
    before looking. Trades are never grouped by r_multiple, outcome or pnl -
    that is the P52 lookahead and it has burned this programme before.

    No threshold is searched. Half-years, reported in full, both eras.

PART B - THE FORWARD PASS (a)
    data/forward/bybit holds 12.5 days: 2026-09-13 -> 2026-09-25, 1203 x
    15m, 301 x 1h, 18049 x 1m, unseen by any prior experiment.

    STATED UP FRONT, BECAUSE IT GOVERNS HOW THIS MAY BE READ: 12.5 days
    cannot clear M = 193.4R and cannot settle a 500-trade question. With
    a 10h swing confirmation on the HTF and a 12h one on the LTF, a
    12.5-day window contains roughly one swing of each. Whatever comes out
    is a SMOKE TEST - it can catch a broken port, a crash, an empty book
    or a sign error, and it can do nothing else. A negative forward result
    here is not evidence against cand_4h1h; a positive one is not evidence
    for it. It is reported as what it is.

    Both books run on identical forward data with identical params and the
    same lag-matched construction as P58, so the two columns are comparable
    even if neither is conclusive.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

import pandas as pd
from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, IST_OFFSET_SEC
from test_experiments_craze import _compute_swings
from src.walker import FlowCandle

M_NULL = 193.4
HTF = {"1h": (1, 10), "4h": (4, 3)}     # lag-matched, per TF_MATRIX_P58.md
LTF = {"15m": (1, 50), "1h": (4, 12)}
FWD = ROOT / "data" / "forward" / "bybit"


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def agg(candles, k, src_sec, min_frac=0.8):
    """k source bars -> one bar of width src_sec*k, stamped with the ts of
    the LAST source bar so it is visible only at its own close. 80% fill."""
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


def books_for(c_htf, c_ltf, fine, params, sw10, sw15):
    out = {}
    for hlab, (hb, hmb) in HTF.items():
        for llab, (lb, lmb) in LTF.items():
            h = c_htf if hb == 1 else agg(c_htf, hb, 3600)
            hsw = sw10 if hb == 1 else _compute_swings(
                as_flow(h), "continuous", min_bars=hmb)
            l = c_ltf if lb == 1 else agg(c_ltf, lb, 900)
            lsw = sw15 if lb == 1 else _compute_swings(
                as_flow(l), "continuous", min_bars=lmb)
            res = tc.build_module()(h, hsw, l, lsw, fine, **params)
            out[(hlab, llab)] = [t for t in res["ltf_trades"]
                                 if t.get("outcome") != "open"]
    return out


def period(ts):
    """Half-year label from a unix ts. Time-based, never outcome-based."""
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def load_fwd(tf):
    df = pd.read_csv(FWD / ("BTCUSDT_%s.csv" % tf))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(
        subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    c = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
          "open": float(r.open), "high": float(r.high),
          "low": float(r.low), "close": float(r.close)} for r in df.itertuples()]
    return c


def main():
    print("=" * 100)
    print("  P61  STABILITY OF THE QUALITY GAP, AND THE FORWARD PASS")
    print("=" * 100)
    print("  Part A partitions by CALENDAR PERIOD, never by outcome.")
    print("  Part B is 12.5 days of unseen data - a smoke test, and")
    print("  explicitly NOT able to clear M = %.1fR.\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = [c for c in
                __import__("test_4_new_concepts").load_fine_1m(
                    oc15[0]["ts"], oc15[-1]["ts"])]
    src = {
        "is": (d["c1h"], d["c15"], d["fine"], d["sw10"], d["sw15"]),
        "oos": (oc1h, oc15, oos_fine,
                _compute_swings(as_flow(oc1h), "continuous", min_bars=10),
                _compute_swings(as_flow(oc15), "continuous", min_bars=50)),
    }

    runs = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for scope in ("is", "oos"):
            c_h, c_l, fn_, s10, s15 = src[scope]
            bk = books_for(c_h, c_l, fn_, params, s10, s15)
            runs[(name, scope)] = (bk[("1h", "15m")], bk[("4h", "1h")])
        print("  " + "=" * 98)
        print("  PART A  LANE: %s   (R/trade per half-year)" % name)
        print("  " + "=" * 98)
        for scope in ("is", "oos"):
            A, B = runs[(name, scope)]
            pa, pb = {}, {}
            for t in A:
                pa.setdefault(period(t["entry_ts"]), []).append(
                    float(t["r_multiple"]))
            for t in B:
                pb.setdefault(period(t["entry_ts"]), []).append(
                    float(t["r_multiple"]))
            keys = sorted(set(pa) | set(pb))
            print("  --- [%s]" % scope.upper())
            print("      %-8s %5s %8s %8s   %5s %8s %8s   %s"
                  % ("period", "nA", "R/tA", "PFA", "nB", "R/tB", "PFB",
                     "cand wins?"))
            w = l = t_ = 0
            for k in keys:
                a, b = pa.get(k, []), pb.get(k, [])
                rta = sum(a) / len(a) if a else 0.0
                rtb = sum(b) / len(b) if b else 0.0
                if a and b:
                    if rtb > rta:
                        w += 1
                        mark = "YES"
                    elif rtb < rta:
                        l += 1
                        mark = "no"
                    else:
                        t_ += 1
                        mark = "="
                else:
                    mark = "one side empty"
                print("      %-8s %5d %+8.3f %8.2f   %5d %+8.3f %8.2f   %s"
                      % (k, len(a), rta, pf(a) if a else 0.0,
                         len(b), rtb, pf(b) if b else 0.0, mark))
            print("      cand R/trade wins %d, loses %d, ties %d of %d "
                  "comparable periods" % (w, l, t_, w + l + t_))
            print()

    print("  " + "=" * 98)
    print("  PART B  FORWARD PASS - 12.5 days, SMOKE TEST ONLY")
    print("  " + "=" * 98)
    fc15, fc1h = load_fwd("15m"), load_fwd("1h")
    ffine = load_fwd("1m")
    print("  forward bars: 15m %d  1h %d  1m %d   %s -> %s"
          % (len(fc15), len(fc1h), len(ffine), fc15[0]["date"],
             fc15[-1]["date"]))
    fsw10 = _compute_swings(as_flow(fc1h), "continuous", min_bars=10)
    fsw15 = _compute_swings(as_flow(fc15), "continuous", min_bars=50)
    print("  swings: 1h %d, 15m %d  (a 12.5-day window cannot hold many)"
          % (len(fsw10), len(fsw15)))
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        bk = books_for(fc1h, fc15, ffine, params, fsw10, fsw15)
        print("  --- %s" % name)
        for lab in (("1h", "15m"), ("4h", "1h")):
            tr = bk[lab]
            rs = [float(t["r_multiple"]) for t in tr]
            n = len(rs)
            print("      %-12s %3dt  net %+7.1fR  R/t %+6.3f  PF %5.2f  WR %4.1f%%"
                  % ("%s+%s" % lab, n, net_r(tr), net_r(tr) / max(1, n),
                     pf(rs) if rs else 0.0,
                     100.0 * sum(1 for x in rs if x > 0) / max(1, n)))
        print()

    print("  A forward result here cannot clear M and cannot settle a")
    print("  500-trade question. Read it as a smoke test only.")
    print("  Nothing adopted. Champion unchanged.")


if __name__ == "__main__":
    main()