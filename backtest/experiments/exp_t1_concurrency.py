"""T1 - is the k-th concurrent position a different bet from the first?

WHY THIS THESIS
---------------
Every experiment run so far asked WHICH signal to take: 27 regime modes, the ATR
threshold sweep, the stability harness, the entry-break study. All of them pick
signals.

The bare base says that is the wrong question. base_book.establish measures:

                     n     net R     R/trade    win %
    IS              503    +105.18     0.2091     22.1%
    OOS             278     -33.68    -0.1212     21.6%

Bare - no cooldown, no streak halt, no position cap, no partial exit, causal SL -
it LOSES out of sample at 22% win rate. And when a position cap was imposed on
the same book family it got worse, not better. So the book is not short of
signals; something about WHICH SLOT a trade occupies is doing the work.

THE AXIS IS NEW. It has never been swept. Not the mode, not the threshold, not
the entry kind: the position in the concurrent sequence.

  slot 1   first position opened, nothing else running
  slot 2   one already open
  ...
  slot 6+  the book peaks at six concurrent positions

If late slots are systematically worse, then the base is not six independent
bets, it is one good bet plus five that dilute it - and the fix is not a better
signal but a cap, a size, or a rule about when the book is already full.

WHAT IS MEASURED
----------------
Per slot, on the base, both eras: n, net, R/trade, win rate, max drawdown, plus
how long a slot stays open. Then a max_positions sweep so the cap can be set
from the curve rather than guessed.

Causality: concurrency is reconstructed from entry_ts and exit_ts of completed
trades only. No future information enters the classification - a trade's slot is
the count of trades that were open at its entry bar and close no later than it.

Output: t1_concurrency_results.json
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
RESULTS = HERE / "t1_concurrency_results.json"

import base_book as bb                                           # noqa: E402

SLOTS = ["1", "2", "3", "4", "5", "6+"]
MAXPOS = [1, 2, 3, 4, 5, 6, 8, 0]

# max_positions is NOT an N-cap. unified.py:357-363: it is a 1/0 serial gate -
# 1 means serial, 0 means unlimited - because it uses one busy_until timestamp
# and cannot express "at most N open". The real N-cap is exp_max_concurrent.
#
# The first run of this harness swept max_positions and got byte-identical
# results for 1, 2, 3, 4, 5, 6 and 8 - 356 trades, +58.11R IS, every time. That
# is not a finding about the cap, it is the serial gate switching on. Both
# knobs are swept below so the distinction is on the record.

_T = 2 * (len(MAXPOS) + 1)
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


def slot_of(trades):
    """Label each trade with how many positions were already open at its entry.

    Strictly causal: the count is made from entry_ts / exit_ts alone, and a
    trade that closes on the same bar it opened does not occupy a slot against
    the trade that opened after it.
    """
    ordered = sorted(trades, key=lambda t: (t["entry_ts"], t["trade_no"]))
    opens = []
    for t in ordered:
        while opens and opens[0] <= t["entry_ts"]:
            opens.pop(0)
        t["_slot"] = len(opens) + 1
        opens.append(t["exit_ts"])
    return ordered


def bucket(t):
    return "6+" if t["_slot"] >= 6 else str(t["_slot"])


def stats(tr):
    if not tr:
        return {"n": 0, "net": 0.0, "r_trade": 0.0, "wr": 0.0, "dd": 0.0,
                "avg_bars": 0.0}
    nets = [bb.net_r(x) for x in tr]
    n = len(nets)
    total = sum(nets)
    cum = peak = dd = 0.0
    for x in nets:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    bars = sum(x.get("bars_held", 0) or 0 for x in tr) / float(n)
    return {"n": n, "net": round(total, 2), "r_trade": round(total / n, 4),
            "wr": round(100.0 * sum(1 for x in nets if x > 0) / n, 1),
            "dd": round(dd, 2), "avg_bars": round(bars, 1)}


def main() -> int:
    print("T1 - THE CONCURRENT-SLOT THESIS")
    print("bare base, no cooldown / no halt / no cap / no partial, causal SL")
    print()
    t0 = time.time()
    sim, eras = bb.load()
    print("loaded (%.0fs)\n" % (time.time() - t0))

    out = {"slots": {}, "maxpos": {}, "era": {}}

    # ---------- per-slot breakdown -------------------------------------
    for era in ("is", "oos"):
        step("base " + era)
        tr = slot_of(bb.trades_of(sim, eras[era], bb.base_cfg(1)))
        out["era"][era] = stats(tr)
        print("=" * 94)
        print("BASE, %s   n=%d   net=%+.2fR   R/trade=%.4f   win=%.1f%%"
              % (era.upper(), out["era"][era]["n"], out["era"][era]["net"],
                 out["era"][era]["r_trade"], out["era"][era]["wr"]))
        print("=" * 94)
        print("  %-6s %6s %10s %10s %8s %8s %10s"
              % ("slot", "n", "net R", "R/trade", "win %", "dd R", "avg bars"))
        print("  " + "-" * 74)
        rows = {}
        for s in SLOTS:
            sub = [t for t in tr if bucket(t) == s]
            st = stats(sub)
            rows[s] = st
            share = 100.0 * st["n"] / len(tr) if tr else 0.0
            print("  %-6s %6d %+10.2f %10.4f %7.1f%% %8.2f %10.1f   %4.1f%% of trades"
                  % (s, st["n"], st["net"], st["r_trade"], st["wr"], st["dd"],
                     st["avg_bars"], share))
        out["slots"][era] = rows
        print()

    # ---------- does the slot effect hold in both eras? -----------------
    print("=" * 94)
    print("THE CLAIM: later slots are a different bet from the first")
    print("=" * 94)
    verdict = []
    for era in ("is", "oos"):
        r = out["slots"][era]
        first, later = r["1"], [r[s] for s in SLOTS[1:] if r[s]["n"]]
        allr = sum(x["r_trade"] * x["n"] for x in later) / max(sum(x["n"] for x in later), 1)
        print("  %-4s slot 1        R/trade %.4f   (n=%d)" % (era.upper(), first["r_trade"], first["n"]))
        print("  %-4s slots 2..6+   R/trade %.4f   (n=%d)"
              % (era.upper(), allr, sum(x["n"] for x in later)))
        gap = first["r_trade"] - allr
        print("  %-4s gap %+.4f R per trade in favour of the first slot" % (era.upper(), gap))
        verdict.append(gap)
    consistent = (verdict[0] > 0 and verdict[1] > 0) or (verdict[0] < 0 and verdict[1] < 0)
    print()
    print("  same direction in both eras: %s" % ("YES" if consistent else "NO"))
    if consistent:
        print("  -> The slot the trade takes is part of the bet. A cap set from the")
        print("     curve below is a structural change, not a filter.")
    else:
        print("  -> The slot effect does not survive both eras. It is an in-sample")
        print("     pattern and the base's edge is NOT about sequence position.")

    # ---------- the two different caps ---------------------------------
    for knob in ("max_positions", "exp_max_concurrent"):
        print()
        print("=" * 94)
        if knob == "max_positions":
            print("max_positions  - THE SERIAL 1/0 GATE (not an N-cap)")
        else:
            print("exp_max_concurrent  - the real N-cap on simultaneously open positions")
        print("=" * 94)
        print("  %-6s %8s %8s %8s %9s %9s" % ("cap", "IS n", "IS net", "IS R/tr", "OOS n", "OOS net"))
        print("  " + "-" * 56)
        for cap in MAXPOS:
            row = {}
            for era in ("is", "oos"):
                step("%s=%d %s" % (knob, cap, era))
                c = bb.base_cfg(1)
                c["params"][knob] = cap
                if knob == "max_positions":
                    c["params"]["exp_max_concurrent"] = 0
                tr = bb.trades_of(sim, eras[era], c)
                row[era] = stats(tr)
            out.setdefault(knob, {})[str(cap)] = row
            lbl = "none" if cap == 0 else str(cap)
            print("  %-6s %8d %+8.2f %8.4f %9d %+9.2f"
                  % (lbl, row["is"]["n"], row["is"]["net"], row["is"]["r_trade"],
                     row["oos"]["n"], row["oos"]["net"]))
        print()
        if knob == "max_positions":
            print("  Every value above 1 matches 1. max_positions>0 is the serial gate,")
            print("  so there is no cap curve in it - only two states.")

    print()
    print("  Reading the N-cap curve: a cap helps only if it raises R-per-trade in")
    print("  BOTH eras. Raising net by dropping trades is the union mistake again,")
    print("  and the owner rejected that book on exactly that point.")

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())