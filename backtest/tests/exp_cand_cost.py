"""P59 - WHERE DOES THE 4h+1h IS COST COME FROM?

THE CANDIDATE
    P58 found the only architecture in the programme that beats the
    champion in OOS, in both lanes:

        champion 1h+15m  IS 500t +325.8R R/t 0.652 | OOS 279t +70.1R R/t 0.251
        4h + 1h          IS 286t +212.8R R/t 0.744 | OOS 189t +98.0R R/t 0.519

    Every quality measure is better in both eras; the price is 214 fewer
    IS trades and -113.0R. It does not pass the criterion, and it does not
    need to pass to be worth understanding. A candidate whose weakness has
    an identified cause is decidable on the forward pass; a candidate whose
    weakness is a shrug is not.

THE QUESTION THIS ANSWERS
    The two books differ ~2x in trade count and ~2x in R per trade, in
    OPPOSITE directions in the two eras. That is only explicable if they
    are not the same set of trades. Two possibilities, opposite decisions:

      SUBSET     4h+1h keeps the champion's good trades and drops its bad
                 ones. The champion's extra resolution is buying quantity
                 at a worse average, the fix is a trade-count reduction,
                 and the candidate is a quality overlay on the existing
                 book rather than a new architecture.
      DIFFERENT  4h+1h is a separate bet with its own edge and the
                 champion's extra trades are the problem. Then the two
                 cannot be blended and the choice is a real architectural
                 decision for the forward pass to arbitrate.

    Trades are matched on (4h bucket, direction) - the coarsest bar the 4h
    layer trades, and direction is what determines a trade, not its exact
    entry minute. A same-bucket same-direction pair is one bet taken at two
    resolutions.

MATCHED ON PATH-TRUE FIELDS ONLY
    (time bucket, direction). NOT r_multiple, NOT outcome, NOT exit_ts,
    NOT pnl. This is a grouping of two live books, not a post-hoc split of
    realised results - partitioning trades by a realised field is the move
    that produced the P52 lookahead.

READING IT
    SHARED / CHAMP-ONLY / CAND-ONLY per era. The sign pattern of the two
    exclusive groups settles subset-vs-different. A CHAMP-ONLY group that
    is negative in IS and positive in OOS would mean the champion's extra
    resolution is era-dependent noise - the same IS-fitted story P56 and
    P58 have now found twice.
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
BUCKET = 4 * 3600          # the 4h layer's own bar
CHAMP = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
         "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}
# (htf label, buckets of 1h, min_bars) / (ltf label, buckets of 15m, min_bars)
HTF = {"1h": (1, 10), "4h": (4, 3)}
LTF = {"15m": (1, 50), "1h": (4, 12)}


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def agg(candles, k, src_sec, min_frac=0.8):
    """k source bars -> one bar of width src_sec*k, stamped with the ts of
    the LAST source bar so it is visible only at its own close. 80% fill:
    this data runs 23.99 hours per day."""
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

def key_of(t):
    """(4h bucket, direction) - the only fields used to match a trade
    between the two books. Deliberately NOT r_multiple, outcome, exit_ts
    or pnl: matching on a realised field is the P52 lookahead."""
    return (int(t["entry_ts"]) // BUCKET, 1 if t["dir"] == "long" else -1)




def main():
    print("=" * 100)
    print("  P59  WHERE THE 4h+1h IS COST COMES FROM")
    print("=" * 100)
    print("  Trades matched on (4h bucket, direction) only - never on")
    print("  r_multiple, outcome or pnl. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"]),
           "oos": (oc1h, oc15, oos_fine)}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = CHAMP[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine = src[scope]
            books = {}
            for hlab, (hb, hmb) in HTF.items():
                for llab, (lb, lmb) in LTF.items():
                    h = c_htf if hb == 1 else agg(c_htf, hb, 3600)
                    hsw = d["sw10"] if (hb == 1 and scope == "is") else \
                        _compute_swings(as_flow(h), "continuous", min_bars=hmb)
                    l = c_ltf if lb == 1 else agg(c_ltf, lb, 900)
                    lsw = d["sw15"] if (lb == 1 and scope == "is") else \
                        _compute_swings(as_flow(l), "continuous", min_bars=lmb)
                    res = tc.build_module()(h, hsw, l, lsw, fine, **params)
                    books[(hlab, llab)] = [t for t in res["ltf_trades"]
                                          if t.get("outcome") != "open"]
            A, B = books[("1h", "15m")], books[("4h", "1h")]
            if (abs(len(A) - pin[i][0]) > 2
                    or abs(net_r(A) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(A), net_r(A), *pin[i]))
                return
            ka = {key_of(t): float(t["r_multiple"]) for t in A}
            kb = {key_of(t): float(t["r_multiple"]) for t in B}
            both = sorted(set(ka) & set(kb))
            only_a = sorted(set(ka) - set(kb))
            only_b = sorted(set(kb) - set(ka))
            print("  --- [%s] champion %dt %+.1fR | 4h+1h %dt %+.1fR"
                  % (scope.upper(), len(A), net_r(A), len(B), net_r(B)))
            print("      %-24s %5s %9s %7s %6s %6s"
                  % ("group", "n", "net", "R/t", "PF", "share"))
            for glbl, keys, m_ in (("SHARED (both took)", both, ka),
                                   ("CHAMP-ONLY", only_a, ka),
                                   ("CAND-ONLY (4h+1h)", only_b, kb)):
                rs = [m_[k] for k in keys]
                if not rs:
                    print("      %-24s %5d %9s" % (glbl, 0, "-"))
                    continue
                print("      %-24s %5d %+9.1fR %+7.3f %6.2f %5.0f%%"
                      % (glbl, len(rs), sum(rs), sum(rs) / len(rs), pf(rs),
                         100.0 * len(rs) / len(ka)))
            print("      %-24s %+9.1fR   <- cost if it is the whole story"
                  % ("CHAMP-ONLY contribution",
                     sum(ka[k] for k in only_a)))
            print("      %-24s %+9.1fR      gain"
                  % ("CAND-ONLY contribution", sum(kb[k] for k in only_b)))
            print()
    print("  Nothing adopted. Champion unchanged.")


if __name__ == "__main__":
    main()