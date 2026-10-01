"""P9 - DOES THE EDGE LIVE IN THE TRENDING PART OF THE MARKET?

THE USER'S QUESTION, which is the right one
==========================================
"this strategy is built on momentum and trend, and trends are rare - most
of the time the market is NOT trending. So: when a trend WAS there, did
the bias window actually support it? And were the profits ridden during
trending periods, or somewhere else?"

That is a decomposition P8 did NOT try, and it is the one that matters
most. P8 split the book by time (year), by the book's own routing
(htf_regime) and by the book's own tail (ex-best-5). All three are
properties OF THE BOOK. None of them is a property of the MARKET.

If the book is genuinely a momentum/trend book, then a market-state label
- trending vs ranging, computed from price alone with no reference to the
strategy - should concentrate the P&L. If instead the P&L is spread
evenly across trending and ranging tape, then "momentum and trend" is a
description of the entries, not a description of where the money is made,
and the whole premise needs re-examining.

WHAT IS MEASURED, causally, at each trade's entry
=================================================
  ER (Kaufman efficiency ratio, 1h closes, lookback 48h):
      ER = |P_t - P_{t-n}| / sum_{i} |P_i - P_{i-1}|
  ER near 1.0 = price went one way in a straight line (trending).
  ER near 0.0 = price went nowhere (ranging). Fully causal: uses only
  closes at or before t, and is a standard published measure, not one
  invented here. Several lookbacks are swept so the result cannot be an
  artefact of one choice.

  drift_agree: does the trade's direction match the market's own drift
  over the trailing window? THIS IS THE USER'S DIRECT QUESTION - "did
  the bias window support the trend?" - asked of each trade.

SPLITS TESTED, each against its OWN reshuffle null
==================================================
  - by ER tercile (ranging / mixed / trending)
  - by drift agreement (with the market's drift / against it)
  - the interaction: trending AND agreeing

The pre-registered bar is P5's M, recomputed per split from that split's
own trades. A split of 150 trades has a much smaller M than the whole
500-trade book, so a trending subset CAN clear the null even though the
total cannot. That is the whole reason to ask this question: the total
being inside its null says nothing about its parts having tighter nulls
of their own.

Pins reproduced first. Reported whatever they say.
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}
BLOCK, DRAWS, SEED = 20, 10_000, 20260928
LOOKBACKS = (24, 48, 96)


def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, build_module())
    return (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])


def er_series(closes, n):
    """Kaufman efficiency ratio at each index, causal, lookback n."""
    out = [0.0] * len(closes)
    for i in range(n, len(closes)):
        path = 0.0
        for k in range(i - n + 1, i + 1):
            path += abs(closes[k] - closes[k - 1])
        net = abs(closes[i] - closes[i - n])
        out[i] = (net / path) if path > 0 else 0.0
    return out


def drift_series(closes, n):
    """Signed net move over the trailing n bars. Causal."""
    out = [0.0] * len(closes)
    for i in range(n, len(closes)):
        out[i] = closes[i] - closes[i - n]
    return out


def M_of(rs, per_cost, block=BLOCK, draws=DRAWS, seed=SEED):
    n = len(rs)
    if n < 10:
        return float("nan")
    nb = max(1, n // block)
    span = max(1, n - block + 1)
    rng = random.Random(seed)
    nets = []
    for _ in range(draws):
        tot = 0.0
        for _ in range(nb):
            s = rng.randrange(0, span) if n > block else 0
            for i in range(s, s + block):
                tot += rs[i] - per_cost
        nets.append(tot)
    absn = sorted(abs(x) for x in nets)
    return absn[int(0.95 * len(absn))], sum(nets) / len(nets)


def report(name, rows, per, winners, tag):
    if len(rows) < 10:
        return
    rs = [x["r"] for x in rows]
    obs = sum(rs) - per * len(rs)
    M, nmean = M_of(rs, per)
    if M != M:
        return
    wr = 100.0 * sum(1 for z in rs if z > 0) / len(rs)
    ok = abs(obs) > M
    if ok:
        winners.append(f"{tag} {name}")
    print(f"    {name:<24} n={len(rs):<4} net={obs:+8.1f}R WR={wr:>5.1f}%  "
          f"M={M:>7.1f}R  nullmean={nmean:+8.1f}R  "
          f"{'*** CLEARS ***' if ok else 'inside null'}")


def main():
    import bisect as bs
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 96)
    print("  P9  DOES THE EDGE LIVE IN THE TRENDING PART OF THE MARKET?")
    print("=" * 96)
    print("  Kaufman efficiency ratio on 1h closes, causal. ER~1 = trending,")
    print("  ER~0 = ranging. Market state only - no reference to the strategy.")
    print("  Pins reproduced first.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    winners = []
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        eng = sim(c1h, sw10, c15, sw15, fine, **PARAMS)
        tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got = net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got - want_net) <= 1.0
        print(f"  [{scope}] PIN n={len(tr)} netNET={got:+.1f} "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing to compute.")
            return
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        hts = [int(c["ts"]) for c in c1h]
        hcl = [float(c["close"]) for c in c1h]

        for lb in LOOKBACKS:
            er = er_series(hcl, lb)
            dr = drift_series(hcl, lb)
            rows = []
            for t in tr:
                k = bs.bisect_right(hts, int(t["entry_ts"])) - 1
                if k < lb:
                    continue
                d = 1 if t["dir"] == "long" else -1
                rows.append({"r": float(t["r_multiple"]), "er": er[k],
                             "agree": (d * dr[k] > 0)})
            if not rows:
                continue
            ev = sorted(x["er"] for x in rows)
            q1, q2 = ev[len(ev) // 3], ev[2 * len(ev) // 3]
            print(f"\n  [{scope}] LOOKBACK {lb}h   "
                  f"ER p10={ev[len(ev)//10]:.3f} p50={ev[len(ev)//2]:.3f} "
                  f"p90={ev[9*len(ev)//10]:.3f}")
            print("    BY EFFICIENCY RATIO (market state, independent of the book)")
            report("ranging  (ER low)", [x for x in rows if x["er"] <= q1],
                   per, winners, f"{scope}/lb{lb}")
            report("mixed", [x for x in rows if q1 < x["er"] <= q2],
                   per, winners, f"{scope}/lb{lb}")
            report("trending (ER high)", [x for x in rows if x["er"] > q2],
                   per, winners, f"{scope}/lb{lb}")
            print("    BY DRIFT AGREEMENT (did the bias window back the trend?)")
            report("with the drift", [x for x in rows if x["agree"]],
                   per, winners, f"{scope}/lb{lb}")
            report("against the drift", [x for x in rows if not x["agree"]],
                   per, winners, f"{scope}/lb{lb}")
            print("    TRENDING AND AGREEING  (the ideal state)")
            report("trend+agree", [x for x in rows
                                   if x["er"] > q2 and x["agree"]],
                   per, winners, f"{scope}/lb{lb}")
            print("    EVERYTHING ELSE")
            report("all the rest", [x for x in rows
                                    if not (x["er"] > q2 and x["agree"])],
                   per, winners, f"{scope}/lb{lb}")
        print()

    print("=" * 96)
    print("  SPLITS THAT CLEAR THEIR OWN NULL")
    print("=" * 96)
    if winners:
        for w in winners:
            print(f"    {w}")
    else:
        print("    NONE. The P&L is not concentrated in trending tape.")
    print("=" * 96)


if __name__ == "__main__":
    main()
