"""exp_mode_regime - what is chop actually BUYING, and can we route on it?

THE QUESTION THIS ANSWERS
=========================
fsent_champ_long runs mode="atr_high": it takes HTF "decisive" windows when the
15m ATR% is above a threshold, and "flip" windows below it. It never reads
chop_thresh. So the book routes on VOLATILITY MAGNITUDE and ignores DIRECTION
EFFICIENCY entirely.

That is not obviously right and not obviously wrong, because the two indicators
do not measure the same thing at all:

  chop (CHOP index, 1h, lb=14)  = 100*log10(sum TR / range) / log10(14)
      Choppiness Efficiency Ratio. High = one-directional travel (trend).
      Low  = wasted oscillation inside a range. Scale roughly 0-100.

  atr_high (ATR% of price, 15m, 14) = how BIG the bars are, as % of price.
      Says nothing about direction. A violent two-way market has a HIGH
      atr_pct AND a LOW chop. A slow grind up has a LOW atr_pct and a HIGH chop.

So "high volatility -> take decisive windows" and "high efficiency -> take
decisive windows" are genuinely different claims, and the current book has
picked one of them and is carrying the other one in a field it never reads.

THE MEASUREMENT, AND ITS HONEST LIMITS
======================================
There is no way to read the *value* of a regime filter off a backtest, because
a regime router only ever shows you the branch it took. Two books that take
opposite branches in the same bars can both look good for unrelated reasons.

So this does NOT try to prove one indicator is better. It does two things that
are actually knowable:

  PART 1 - what each indicator says about the same bars. The overlap table.
           How often do chop and atr_high disagree, and what does each one
           call a bar that the other calls calm? This is pure measurement with
           no book attached, and it is the part that decides whether the
           routing choice is even a real choice.

  PART 2 - what the book actually earns in each joint regime cell. Trades
           bucketed by (chop says X, atr says Y), with n, win rate, net R and
           mean R per cell, in BOTH eras separately.

Part 2 is the useful half. If the cell where they disagree is where the money
is, then routing on the wrong one of the two costs something specific and
measurable. If it is not, then the current book's choice is fine and the
simplest honest conclusion is "leave it alone".

WHAT THIS DELIBERATELY DOES NOT DO
==================================
It does not add a `mode="chop"` book and compare headline nets. That comparison
is available already - 13 books already inherit BP's chop-reading mode - and
its answer is confounded: those books differ in everything except the router.
Per-cell attribution on the SAME book is the comparison that isolates the
indicator, because the book, the entry logic, the swing and the risk knobs are
all held fixed and only the regime reading changes.

Run:  cd backtest/tests
      python -u exp_mode_regime.py
"""
from __future__ import annotations

import bisect as bs
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_mode_regime.json"
OUT_MD = Path(__file__).parent / "_mode_regime.md"

CHOP_LB = 14


def chop_series(candles_1h, lb=CHOP_LB):
    """The engine's own _chop_series_1h, copied not imported, so this harness
    cannot silently drift from the engine if that function is rewritten.
    Compared field-by-field against the engine's output in the self-test."""
    n = len(candles_1h)
    tr = [0.0] * n
    for i in range(n):
        hi = float(candles_1h[i]["high"])
        lo = float(candles_1h[i]["low"])
        if i == 0:
            tr[i] = hi - lo
        else:
            pc = float(candles_1h[i - 1]["close"])
            tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    out = [50.0] * n
    for i in range(lb, n):
        tr_sum = sum(tr[i - lb + 1:i + 1])
        hi_max = max(float(candles_1h[j]["high"]) for j in range(i - lb + 1, i + 1))
        lo_min = min(float(candles_1h[j]["low"]) for j in range(i - lb + 1, i + 1))
        rang = hi_max - lo_min
        if rang > 0 and tr_sum > 0:
            try:
                out[i] = 100 * math.log10(tr_sum / rang) / math.log10(lb)
            except ValueError:
                out[i] = 50.0
        else:
            out[i] = 50.0
    return out


def atr_pct_series(candles_15m):
    """The engine's _atr_pct_15m, same reason."""
    n = len(candles_15m)
    tr = [0.0] * n
    for i in range(n):
        hi = float(candles_15m[i]["high"])
        lo = float(candles_15m[i]["low"])
        if i == 0:
            tr[i] = hi - lo
        else:
            pc = float(candles_15m[i - 1]["close"])
            tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    atr = [0.0] * n
    for i in range(n):
        lo_i = max(0, i - 13)
        atr[i] = sum(tr[lo_i:i + 1]) / (i - lo_i + 1)
    return [atr[i] / float(candles_15m[i]["close"]) * 100
            if float(candles_15m[i]["close"]) != 0 else 0 for i in range(n)]


def joint_regime(data):
    """chop and atr_pct sampled at every 15m entry bar, the way the engine does:
    chop from the last 1h candle CLOSED by ts+900 (C14), atr_pct on the 15m bar.

    Returns (rows, chop_series, atr_series, ts_htf_close).
    """
    chop = chop_series(data["c1h"])
    atrp = atr_pct_series(data["c15"])
    ts_htf_close = [int(c["ts"]) + 3600 for c in data["c1h"]]
    rows = []
    for i, c in enumerate(data["c15"]):
        ts = int(c["ts"])
        j = bs.bisect_right(ts_htf_close, ts + 900) - 1
        ch = chop[max(0, j)] if 0 <= j < len(chop) else 50.0
        rows.append({"i": i, "ts": ts, "ch": ch, "atrp": atrp[i]})
    return rows, chop, atrp, ts_htf_close


def self_test(data):
    """Prove the copied series match the engine's, so a rewrite of the engine
    cannot leave this harness quietly measuring something else."""
    sys.path.insert(0, str(ROOT / "backend"))
    from src.btc.engines.htf_ltf import unified as U
    eng_chop = U._chop_series_1h(data["c1h"], lb=CHOP_LB)
    eng_atrp = U._atr_pct_15m(data["c15"])
    mine_chop = chop_series(data["c1h"])
    mine_atrp = atr_pct_series(data["c15"])
    n = min(len(eng_chop), len(mine_chop))
    worst_c = max(abs(eng_chop[i] - mine_chop[i]) for i in range(n))
    worst_a = max(abs(eng_atrp[i] - mine_atrp[i]) for i in range(len(eng_atrp)))
    return worst_c, worst_a


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)
    chop_thr = base["chop_thresh"]
    atr_thr = base["atr_high_thresh"]

    print("=" * 100)
    print("MODE / REGIME ATTRIBUTION - %s" % BOOK)
    print("=" * 100)
    print("current router : mode=%r  atr_high_thresh=%s  chop_thresh=%s (NOT read by this mode)"
          % (base["mode"], atr_thr, chop_thr))
    print("  chop says HIGH   when the 1h travelled efficiently (trend-like)")
    print("  chop says LOW    when the 1h oscillated inside a range (choppy)")
    print("  atr says HIGH    when 15m bars are big, regardless of direction")
    print()

    data = {e: load_era(e) for e in ("is", "oos")}
    for e in ("is", "oos"):
        wc, wa = self_test(data[e])
        print("self-test %s: copied vs engine series, max |diff| chop %.2e atr %.2e"
              % (e.upper(), wc, wa))

    # ---------------------------------------------------------------------
    # PART 1 - do the two indicators actually disagree?
    # ---------------------------------------------------------------------
    print()
    print("-" * 100)
    print("PART 1 - WHAT EACH INDICATOR SAYS ABOUT THE SAME BARS")
    print("-" * 100)
    overlap = {}
    for era in ("is", "oos"):
        rows, _, _, _ = joint_regime(data[era])
        cells = {}
        for r in rows:
            a = "atr_HIGH " if r["atrp"] > atr_thr else "atr_low  "
            c = "chop_HIGH" if r["ch"] > chop_thr else "chop_low "
            k = "%s / %s" % (c, a)
            cells[k] = cells.get(k, 0) + 1
        tot = len(rows)
        overlap[era] = {"total": tot, "cells": cells}
        print("\n%s (%d 15m bars)" % (era.upper(), tot))
        for k in sorted(cells, reverse=True):
            share = 100.0 * cells[k] / tot
            bar = "#" * int(share / 2)
            print("   %-22s %6d  %5.1f%%  %s" % (k, cells[k], share, bar))
        agree = sum(v for k, v in cells.items()
                    if (k.startswith("chop_HIGH") and k.startswith("chop_HIGH / atr_HIGH"))
                    or (k.startswith("chop_low") and k.startswith("chop_low  / atr_low")))
        print("   -> the two indicators agree on %.1f%% of bars and disagree on %.1f%%"
              % (100.0 * agree / tot, 100.0 * (tot - agree) / tot))

    # ---------------------------------------------------------------------
    # PART 2 - what does the book earn in each joint cell?
    # ---------------------------------------------------------------------
    print()
    print("-" * 100)
    print("PART 2 - WHAT THE BOOK EARNS IN EACH JOINT CELL (trades, not bars)")
    print("-" * 100)
    percell = {}
    for era in ("is", "oos"):
        d = data[era]
        sw = get_swings(d, cfg.get("swing") or "sw10")
        out = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **base)
        trades = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        by_ts, _, _, _ = joint_regime(d)
        lut = {r["ts"]: r for r in by_ts}

        cells = {}
        for t in trades:
            ts = int(t["entry_ts"]) - 900
            r = lut.get(ts)
            if r is None:
                continue
            a = "atr_HIGH " if r["atrp"] > atr_thr else "atr_low  "
            c = "chop_HIGH" if r["ch"] > chop_thr else "chop_low "
            k = "%s / %s" % (c, a)
            cells.setdefault(k, []).append(net_r([t]))

        print("\n%s" % era.upper())
        tot_n = sum(len(v) for v in cells.values())
        tot_r = sum(sum(v) for v in cells.values())
        print("   %-22s %5s %7s %8s %9s %9s" % ("cell", "n", "net R", "share R", "win %", "mean R"))
        for k in sorted(cells, key=lambda z: -sum(cells[z])):
            v = cells[k]
            wins = sum(1 for x in v if x > 0)
            print("   %-22s %5d %+7.1f %7.1f%% %8.1f%% %+9.2f"
                  % (k, len(v), sum(v), 100.0 * sum(v) / tot_r if tot_r else 0,
                     100.0 * wins / len(v), sum(v) / len(v)))
        if tot_n != len(trades):
            print("   (%d trades not attributed - entry bar not in the 15m index)" % (len(trades) - tot_n))
        print("   total %d trades, %+.1fR" % (tot_n, tot_r))
        percell[era] = {k: {"n": len(v), "net": round(sum(v), 2),
                            "mean": round(sum(v) / len(v), 3),
                            "win_pct": round(100.0 * sum(1 for x in v if x > 0) / len(v), 1)}
                       for k, v in cells.items()}

    # ---------------------------------------------------------------------
    # THE READ, kept mechanical: compare the two disagreement cells only.
    # ---------------------------------------------------------------------
    print()
    print("=" * 100)
    print("READ - the two cells where the indicators disagree, both eras")
    print("=" * 100)
    for era in ("is", "oos"):
        cc = percell[era]
        hi_atr = cc.get("chop_low  / atr_HIGH ", {})
        lo_atr = cc.get("chop_HIGH / atr_low  ", {})
        print("\n%s" % era.upper())
        print("   chop_low  / atr_HIGH  (book reads LOW vol -> flip)   n=%-4s net %+8s  mean %+6s"
              % (hi_atr.get("n"), hi_atr.get("net"), hi_atr.get("mean")))
        print("   chop_HIGH / atr_low   (book reads LOW vol -> flip)   n=%-4s net %+8s  mean %+6s"
              % (lo_atr.get("n"), lo_atr.get("net"), lo_atr.get("mean")))
        both_low = cc.get("chop_low  / atr_low  ", {})
        both_high = cc.get("chop_HIGH / atr_HIGH ", {})
        print("   -- agreement cells for reference --")
        print("   chop_low  / atr_low   n=%-4s net %+8s  mean %+6s"
              % (both_low.get("n"), both_low.get("net"), both_low.get("mean")))
        print("   chop_HIGH / atr_HIGH  n=%-4s net %+8s  mean %+6s"
              % (both_high.get("n"), both_high.get("net"), both_high.get("mean")))
        if hi_atr.get("n") and lo_atr.get("n"):
            print("   -> if the LOW-vol cells are where the money is, routing on atr")
            print("      high is leaving it in flip windows when chop says otherwise.")

    OUT_JSON.write_text(json.dumps(
        {"book": BOOK, "mode": base["mode"], "atr_high_thresh": atr_thr,
         "chop_thresh": chop_thr, "overlap": overlap, "percell": percell}, indent=2) + "\n",
        encoding="utf-8")
    print("\nwrote %s" % OUT_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())