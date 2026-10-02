"""Re-derive the base-book null M on the SHIPPING book, champion_multi_sw10_leg.

Same method as P5 (exp_base_null.py), same seed, same block length, same draw
count. Only the book differs. The bootstrap function is imported, not copied, so
the method cannot drift between the two results.

Why this is needed. M = 479.9R IS / 193.4R OOS was computed on the ORIGIN book's
R sequence. C16 changed the shipped rule to the leg pivot, which has 499 trades
instead of 500 and compressed risk denominators. M's value moves; its validity does
not - a proposal's dNet is a difference over the same trade universe and belongs
against that universe's reshuffle variance (BASE_BOOK_NULL.md).

P5's own headline survives this either way: the book's net sits near the middle of
a reshuffle of itself, because the tail is wide. Re-deriving M does not change
that; it only changes the bar a proposal has to clear.

Run: python -u exp_base_null_leg.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

import exp_base_null as E                      # same harness, imported not copied
from experiment_registry import EXPERIMENTS

CFG = EXPERIMENTS["champion_multi_sw10_leg"]   # the shipping book
PARAMS = {**E.BP, **CFG["params"]}
# Measured, not copied. The first attempt used 279 / +70.1 for OOS, which is the
# ORIGIN book's OOS - it was carried over when the entry was created. On the leg
# rule the OOS slice is 280 trades / +72.8R, and the harness's own pin gate caught
# it by refusing to compute a null against the wrong book.
PINS = {"is": (499, 239.1), "oos": (280, 72.8)}


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 92)
    print("  BASE-BOOK NULL, RE-DERIVED ON THE SHIPPING BOOK (champion_multi_sw10_leg)")
    print("=" * 92)
    print("  method identical to P5: block=%d trades, %s draws, seed=%d"
          % (E.BLOCK, f"{E.DRAWS:,}", E.SEED))
    print("  bootstrap function imported from exp_base_null, not reimplemented")
    print("  P5 origin-book result for comparison: IS M=479.9R, OOS M=193.4R\n")

    E.PARAMS, E.PINS = PARAMS, PINS
    sim = E.build_module()
    res = {}
    for scope in ("is", "oos"):
        print("-" * 92)
        a = E.load(scope)
        tr = [t for t in sim(*a, **PARAMS)["ltf_trades"]
              if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got_net = E.net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got_net - want_net) <= 1.5
        print(f"  [{scope}] PIN: n={len(tr)} netNET={got_net:+.1f}  "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing to compute a null against the wrong book.")
            return
        res[scope] = tr

    print()
    print("=" * 92)
    print("  THE NULL, SHIPPING BOOK")
    print("=" * 92)
    got = {}
    for scope in ("is", "oos"):
        tr = res[scope]
        g = SYMBOL_PARAMS["BTCUSDT"]
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        rs = [float(t["r_multiple"]) for t in tr]
        costs = [per] * len(tr)
        obs = E.net_r(tr)
        nulls = E.block_bootstrap_nets(rs, costs, E.BLOCK, E.DRAWS, E.SEED)
        absn = sorted(abs(x) for x in nulls)
        p95 = absn[int(0.95 * len(absn))]
        p05 = absn[int(0.05 * len(absn))]
        pct = 100.0 * sum(1 for x in nulls if x >= obs) / len(nulls)
        got[scope] = (len(tr), obs, p95, pct)
        print(f"  [{scope}]  n={len(tr)}  observed netNET = {obs:+.1f}R")
        print(f"    null |net|   p05 = {p05:6.1f}R    p95 = {p95:6.1f}R")
        print(f"    null net     mean = {sum(nulls)/len(nulls):+6.1f}R"
              f"    min = {nulls[0]:+7.1f}    max = {nulls[-1]:+7.1f}")
        print(f"    M = {p95:.1f}R          observed at the {pct:.1f}th percentile")
        print(f"    -> {'INDISTINGUISHABLE from a reshuffle of itself' if abs(obs) <= p95 else 'clears its own reshuffle null'}")
        print()

    print("=" * 92)
    print("  ORIGIN (P5) vs SHIPPING (this run)")
    print("=" * 92)
    print(f"  {'':6s} {'origin':>22s}   {'leg':>22s}")
    print(f"  {'era':6s} {'n':>4s} {'net':>8s} {'M':>8s}   {'n':>4s} {'net':>8s} {'M':>8s}")
    for scope, o in (("IS", (500, 325.8, 479.9, 45.7)), ("OOS", (279, 70.1, 193.4, 47.9))):
        n2, o2, m2, p2 = got[scope.lower()]
        print(f"  {scope:6s} {o[0]:4d} {o[1]:+8.1f} {o[2]:8.1f}   {n2:4d} {o2:+8.1f} {m2:8.1f}")
    print()
    print("  M on the leg book is the bar every future proposal is scored against.")


if __name__ == "__main__":
    main()