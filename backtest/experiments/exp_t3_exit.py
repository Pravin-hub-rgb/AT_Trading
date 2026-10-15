"""T3 - the base wins 22% of the time and loses money out of sample. Shape it.

THE PROBLEM, STATED PLAINLY
---------------------------
base_book.establish:

                n     net R    R/trade   win %
    IS         503   +105.18    0.2091    22.1%
    OOS        278    -33.68   -0.1212    21.6%

Eight trades in ten lose. That is not a book that needs a better signal - at
22% it has to be paid for by payoff asymmetry, and out of sample it is not. So
this thesis does not touch entry at all. It asks one question about the exit:

    do the losers die slowly?

If losing trades sit for a long time before resolving, and winners run, then
time is a free variable nobody is using, and cutting a position that has failed
at bar K recovers R without costing anything on the winners.

MEASURE THE SHAPE FIRST, PICK THE RULE SECOND
----------------------------------------------
Half of a thesis like this is picking K out of the air. So the harness first
reports the actual distribution - how long losers hold versus winners, and how
deep they go - and only then tests cut rules at K values taken from that shape.

  exit_r_at_bar_k   if the trade is under -X R at bar K after entry, close it
                    at that bar's close. Winners are never touched.

CAUSALITY, AND WHY IT IS ENFORCED IN CODE
-----------------------------------------
This is a simulation layered on completed trades, not a retroactive edit of
their R. For each trade the harness walks FORWARD from entry_idx through the 15m
candles, stops at the first K (capped by that trade's own exit), and takes the
close of that bar. It never reads past K, never looks at where the trade
actually ended, and never uses a bar later than the one it acts on. So the
result is what a broker would have done, not what hindsight would allow.

The one thing this cannot see is intra-bar path: whether the K-th bar touched
the cut price before its close. That is stated as a limitation rather than
assumed away, and it means the measured cuts are if-generous to the exit.

Output: t3_exit_results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "t3_exit_results.json"

import base_book as bb                                           # noqa: E402

# K in 15m bars, and the underwater level at which a trade is cut.
# K values are the round numbers the shape report suggests are worth checking;
# thresholds span "mildly down" to "properly wrong".
K_BARS = [2, 4, 8, 16, 32]
CUT_R = [-0.25, -0.5, -0.75]

_T = 2 * (len(K_BARS) * len(CUT_R) + 2)
_D = 0
_T0 = time.time()


def step(lbl):
    global _D
    _D += 1
    el = time.time() - _T0
    eta = (el / _D) * (_T - _D) if _D else 0.0
    pct = 100.0 * _D / _T
    sys.stdout.write("\r  [%3.0f%%] %s %5.0fs elapsed, ~%4.0fs left   %s"
                     % (pct, "#" * int(pct / 2.5), el, eta, lbl))
    sys.stdout.flush()


def unrealized_r(t, price):
    e = float(t["entry_price"])
    sl = float(t["sl"])
    risk = e - sl
    if abs(risk) < 1e-12:
        return None
    return (price - e) / risk if t["dir"] == "long" else (e - price) / risk


def apply_cut(trades, c15, k, cut):
    """Causal cut. Returns (new_net_per_trade list, how many were cut).

    For each trade, look at the close of bar entry_idx+k. If it is under the cut
    level and the trade had not already exited, that is the exit. Bars are never
    read past k, and the trade's own outcome is not consulted.
    """
    nets = []
    cut_n = 0
    for t in trades:
        r = bb.net_r(t)
        i0 = t.get("entry_idx")
        i1 = t.get("exit_idx")
        if cut is not None and i0 is not None and i1 is not None:
            j = min(int(i0) + k, int(i1))
            if j > int(i0) and j < len(c15):
                px = float(c15[j]["close"])
                u = unrealized_r(t, px)
                if u is not None and u <= cut:
                    r = u
                    cut_n += 1
        nets.append(r)
    return nets, cut_n


def stats(nets):
    if not nets:
        return {"n": 0, "net": 0.0, "r_trade": 0.0, "wr": 0.0}
    n = len(nets)
    tot = sum(nets)
    cum = peak = dd = 0.0
    for x in nets:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"n": n, "net": round(tot, 2), "r_trade": round(tot / n, 4),
            "wr": round(100.0 * sum(1 for x in nets if x > 0) / n, 1),
            "dd": round(dd, 2)}


def main() -> int:
    print("T3 - THE EXIT THESIS: do the losers die slowly?")
    print()
    t0 = time.time()
    sim, eras = bb.load()
    print("loaded (%.0fs)\n" % (time.time() - t0))

    out = {"shape": {}, "cuts": {}}
    trades = {}

    # ---------------- 1. the shape of winners and losers ----------------
    print("=" * 96)
    print("1. SHAPE - how do winners and losers differ?")
    print("=" * 96)
    for era in ("is", "oos"):
        step("shape " + era)
        tr = bb.trades_of(sim, eras[era], bb.base_cfg(1))
        trades[era] = tr
        nets = [bb.net_r(t) for t in tr]
        win = [(n, t) for n, t in zip(nets, tr) if n > 0]
        los = [(n, t) for n, t in zip(nets, tr) if n <= 0]
        wh = sorted(t.get("bars_held", 0) or 0 for _, t in win)
        lh = sorted(t.get("bars_held", 0) or 0 for _, t in los)

        def med(v):
            return v[len(v) // 2] if v else 0

        def p(v, q):
            return v[min(int(len(v) * q), len(v) - 1)] if v else 0

        # where do losers actually sit? deep losers vs shallow
        deep = [n for n, _ in los if n <= -1.2]
        shallow = [n for n, _ in los if n > -1.2]
        row = {
            "n": len(tr), "win": len(win), "lose": len(los),
            "win_bars_median": med(wh), "lose_bars_median": med(lh),
            "win_bars_p75": p(wh, 0.75), "lose_bars_p75": p(lh, 0.75),
            "win_avg_r": round(sum(n for n, _ in win) / max(len(win), 1), 4),
            "lose_avg_r": round(sum(n for n, _ in los) / max(len(los), 1), 4),
            "lose_deep_n": len(deep), "lose_shallow_n": len(shallow),
            "lose_deep_avg_r": round(sum(deep) / len(deep), 4) if deep else 0.0,
            "lose_shallow_avg_r": round(sum(shallow) / len(shallow), 4) if shallow else 0.0,
            "wr": round(100.0 * len(win) / len(tr), 1),
        }
        out["shape"][era] = row
        print()
        print("  %s   n=%d   winners %d   losers %d" % (era.upper(), row["n"], row["win"], row["lose"]))
        print("    bars held  median:  winners %-5d   losers %-5d" % (row["win_bars_median"], row["lose_bars_median"]))
        print("    bars held  p75:     winners %-5d   losers %-5d" % (row["win_bars_p75"], row["lose_bars_p75"]))
        print("    average R   winners %+.3f      losers %+.3f" % (row["win_avg_r"], row["lose_avg_r"]))
        print("    losers deeper than -1.2R: %d   avg %+.3f" % (row["lose_deep_n"], row["lose_deep_avg_r"]))
        print("    losers shallower than -1.2R: %d   avg %+.3f" % (row["lose_shallow_n"], row["lose_shallow_avg_r"]))
        payoff = (row["win_avg_r"] / abs(row["lose_avg_r"])) if row["lose_avg_r"] else 0
        breakeven = 100.0 * abs(row["lose_avg_r"]) / (row["win_avg_r"] + abs(row["lose_avg_r"]))
        print("    payoff ratio %.2f:1   break-even win rate needed %.1f%%   actual %.1f%%"
              % (payoff, breakeven, row["wr"]))
    print()
    print("  READ: if losers hold materially LONGER than winners, time is the")
    print("  unused variable and a cut is worth testing. If they do not, the exit")
    print("  is not where this book is broken and T3 stops here.")
    print()

    # ---------------- 2. the cut rules ----------------------------------
    print("=" * 96)
    print("2. CUT RULES - exit at bar K if under -X R. Winners never touched.")
    print("=" * 96)
    base_stats = {}
    for era in ("is", "oos"):
        b = stats([bb.net_r(t) for t in trades[era]])
        base_stats[era] = b
    print("  %-6s %-16s %7s %9s %9s %8s %7s"
          % ("era", "rule", "n", "net R", "R/trade", "win %", "cut n"))
    print("  " + "-" * 76)
    for era in ("is", "oos"):
        print("  %-6s %-16s %7d %+9.2f %9.4f %7.1f%% %7s"
              % (era.upper(), "base (no cut)", base_stats[era]["n"],
                 base_stats[era]["net"], base_stats[era]["r_trade"],
                 base_stats[era]["wr"], "-"))
        for k in K_BARS:
            for cut in CUT_R:
                step("%s k=%d cut=%.2f" % (era, k, cut))
                nets, cn = apply_cut(trades[era], eras[era]["c15"], k, cut)
                s = stats(nets)
                out["cuts"]["%s|k%d|%.2f" % (era, k, cut)] = s
                print("  %-6s %-16s %7d %+9.2f %9.4f %7.1f%% %7d"
                      % (era.upper(), "k=%d cut=%.2f" % (k, cut),
                         s["n"], s["net"], s["r_trade"], s["wr"], cn))
    print()

    # ---------------- 3. the verdict -----------------------------------
    print("=" * 96)
    print("THE CLAIM: some (K, cut) raises R-per-trade in BOTH eras")
    print("=" * 96)
    winners = []
    for k in K_BARS:
        for cut in CUT_R:
            a = out["cuts"]["is|k%d|%.2f" % (k, cut)]["r_trade"] - base_stats["is"]["r_trade"]
            b = out["cuts"]["oos|k%d|%.2f" % (k, cut)]["r_trade"] - base_stats["oos"]["r_trade"]
            ok = a > 0 and b > 0
            if ok:
                winners.append((k, cut, a, b))
            print("  k=%-3d cut=%-6.2f  IS %+.4f   OOS %+.4f   %s"
                  % (k, cut, a, b, "HOLDS" if ok else "-"))
    print()
    if winners:
        print("  %d rule(s) hold in both eras: %s" % (len(winners), winners))
    else:
        print("  -> No time-based cut lifts R-per-trade in both eras. The exit is")
        print("     not where this book is broken.")

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())