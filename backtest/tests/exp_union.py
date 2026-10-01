"""P60 - THE UNION OF champion_multi_sw10 AND cand_4h1h.

IN PLAIN TERMS
    Two books trade the same BTC data at different moments. The champion
    takes 500 trades, cand_4h1h takes 286, and only 19 of them happen in the
    same 4h window going the same way. P59 showed neither book's exclusive
    trades are bad - champion-only is +370.0R in IS, candidate-only
    +228.9R - so the candidate's -113.0R IS "cost" is 214 fewer trades,
    not worse ones. That makes this a union question, not a replacement.

    The obstacle: the engine holds ONE position at a time. Both books were
    each generated as if they owned the whole slot, so their trades collide
    in time even though the underlying bets rarely do.

THE RULES - FIXED BEFORE RUNNING, NOT CHOSEN BY LOOKING
      R1 ORDER    All signals from both books pooled, walked in entry_ts
                  order. Neither book is special.
      R2 CONFLICT If a position is open, a new signal is SKIPPED and the
                  slot stays with the incumbent. SKIP not GRAY, because a
                  closed slot gives later signals more freedom than a held
                  one, and the programme already defines SKIP that way.
      R3 TIE      Two signals at an identical entry_ts: champion first.
                  Arbitrary but fixed. If this tie rule turns out to
                  matter, that is a finding, not something to re-pick.
      R4 EXIT     A taken trade exits on its OWN recorded exit, and its
                  r_multiple is used unchanged. No re-scaling.
      R5 P&L      The union's net is the sum of taken trades' r_multiple.

WHAT THIS IS NOT, STATED BEFORE RUNNING
    This merges two INDEPENDENTLY GENERATED books. Each was simulated with
    its own cooldown and its own busy_until, so the union does not
    re-simulate shared gating: in a true union the HTF window state and
    the slot would be shared, and a suppressed champion signal might have
    changed the champion's own later gating. So this harness is a
    chronological merge with a one-slot constraint - the cheapest honest
    test of whether the two books can coexist at all - and it is not a
    simulation of a production union.

PASS CRITERION - FIXED BEFORE RUNNING
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R. A
    union that only wins in IS is the P57 1D trap again: better risk
    profile, destroyed return, fitted to the era it was measured in.
"""
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
from test_experiments_craze import _compute_swings
from src.walker import FlowCandle

M_NULL = 193.4
CHAMP = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
         "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}
HTF = {"1h": (1, 10), "4h": (4, 3)}    # lag-matched, per TF_MATRIX_P58.md
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


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def net_of(tr):
    """r_multiple minus this trade's own fees, slippage and funding.

    IMPORTANT: the pinned figures (+325.8R IS / +70.1R OOS) are NET of
    costs, via net_r() in run_experiment, which subtracts _trade_costs and
    fund(). A first version of this harness summed bare r_multiple and so
    compared a GROSS union against a NET champion - the union looked like
    +445.2R against +325.8R, a gap of 119.4R that is nothing but costs.
    Every number here is on the same net basis as the pins.
    """
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def union(A, B):
    """Pool both books' signals, walk entry_ts order, one position at a
    time. R1 order / R2 SKIP on conflict / R3 champion first on an exact
    tie / R4 exit and r_multiple used unchanged. Returns the taken trades
    so each can be costed on its own."""
    ev = []
    for t in A:
        ev.append((int(t["entry_ts"]), 0, t))
    for t in B:
        ev.append((int(t["entry_ts"]), 1, t))
    ev.sort(key=lambda x: (x[0], x[1]))
    taken, free_at, skipped = [], None, 0
    for ets, _src, t in ev:
        if free_at is not None and ets < free_at:
            skipped += 1
            continue
        taken.append(t)
        free_at = int(t["exit_ts"])
    return taken, skipped


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


def main():
    print("=" * 100)
    print("  P60  THE UNION OF THE CHAMPION AND cand_4h1h")
    print("=" * 100)
    print("  Rules fixed BEFORE running: one position at a time, SKIP on")
    print("  conflict, champion first on an exact tie, exits unchanged.")
    print("  Pass = beat champion in BOTH eras in BOTH lanes AND clear M.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    oos_sw10 = _compute_swings(as_flow(oc1h), "continuous", min_bars=10)
    oos_sw15 = _compute_swings(as_flow(oc15), "continuous", min_bars=50)
    src = {"is": (d["c1h"], d["c15"], d["fine"], d["sw10"], d["sw15"]),
           "oos": (oc1h, oc15, oos_fine, oos_sw10, oos_sw15)}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = CHAMP[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine, sw10, sw15 = src[scope]
            bk = books_for(c_htf, c_ltf, fine, params, sw10, sw15)
            A, B = bk[("1h", "15m")], bk[("4h", "1h")]
            if (abs(len(A) - pin[i][0]) > 2
                    or abs(net_r(A) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(A), net_r(A), *pin[i]))
                return
            ru, skipped = union(A, B)
            net_u = net_of(ru)
            print("  --- [%s]  champion %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(A), net_r(A)))
            print("      %-26s %5s %9s %7s %6s %6s %6s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "WR"))
            for lbl, tr_, netv in (
                    ("champion (1h+15m)", A, net_r(A)),
                    ("cand_4h1h (4h+1h)", B, net_r(B)),
                    ("UNION (both, 1 slot)", ru, net_u)):
                rs = [float(t["r_multiple"]) for t in tr_]
                print("      %-26s %5d %+9.1fR %+7.3f %6.2f %6.1f %5.1f%%"
                      % (lbl, len(rs), netv, netv / len(rs), pf(rs),
                         dd(rs), 100.0 * sum(1 for x in rs if x > 0)
                         / len(rs)))
            print("      %d of %d signals skipped by the one-slot rule"
                  % (skipped, len(A) + len(B)))
            dv = net_u - net_r(A)
            print("      %-26s %5d %+9.1fR%s"
                  % ("union vs champion", len(ru) - len(A), dv,
                     "   <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print()
    print("  Pass = beat the champion in BOTH eras in BOTH lanes AND clear M.")
    print("  Nothing adopted. Champion unchanged.")


if __name__ == "__main__":
    main()