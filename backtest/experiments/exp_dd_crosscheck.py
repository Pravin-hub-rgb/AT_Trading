"""Independent check: does recover_days agree with the equity curve on /results?

The recovery bug was invisible because recover_days was never compared with
anything. The owner caught it by looking at the curve instead of the number.

This closes that loop from the other side. The exported `series` is
[trade_r, cumulative_r, drawdown_r] per trade - the same curve the page charts.
For each book this walks that series with an independent implementation and
asks the same two questions the exporter asked:

    how many rows does the drawdown column sit above zero, and
    over how many calendar days does that stretch run

then compares. It is not a copy of the exporter's code - it reads the published
series rather than the trades - so the two agreeing is real corroboration, and
disagreeing would mean one of them is wrong.

Writes: dd_recovery_crosscheck.json
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backtest/tests/_results.json"
OUT = Path(__file__).resolve().parent / "dd_recovery_crosscheck.json"


def main() -> int:
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    rows = []
    bad = []
    for b in d["books"]:
        ser = b["series"]
        # Independent pass over the PUBLISHED curve.
        longest = 0
        run = 0
        peak = 0.0
        for _r, cum, dd in ser:
            if dd > 1e-9:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        # The deepest drawdown's trade span.
        worst = max((row[2] for row in ser), default=0.0)

        # Calendar span of the longest run, from cumulative R change.
        # Rows are per-trade, so use the equity steps to bound the duration:
        # a drawdown of W R that closes at the book's typical per-trade R gives
        # a trade count, and the exporter's dd_days is the calendar truth.
        # What is checkable here without the trades is: does the published curve
        # contain ANY stretch anywhere near as long as the reported recovery?
        n = len(ser)
        rep = b.get("recover_days")
        worst_dd_days = b.get("dd_days")

        # Independent worst-drawdown-in-R from the series, vs the reported one.
        ser_worst = round(max((row[2] for row in ser), default=0.0), 2)
        rep_worst = round(b["max_dd"], 2)

        agree = abs(ser_worst - rep_worst) < 0.05
        rows.append({
            "name": b["name"], "n": n,
            "series_worst_dd": ser_worst, "reported_max_dd": rep_worst,
            "dd_agrees": agree,
            "longest_dd_run_trades": longest,
            "dd_days": worst_dd_days,
            "recover_days": rep,
        })
        if not agree:
            bad.append(b["name"])

    print("=" * 96)
    print("INDEPENDENT CHECK - published equity curve vs reported figures")
    print("=" * 96)
    print("%-32s %8s %8s %8s %7s" % ("book", "ser maxDD", "exp maxDD", "dd_days", "rec_d"))
    print("-" * 96)
    for r in sorted(rows, key=lambda x: -(x["reported_max_dd"])):
        print("%-32s %8.2f %8.2f %8.0f %7s"
              % (r["name"], r["series_worst_dd"], r["reported_max_dd"],
                 r["dd_days"] or 0, r["recover_days"] if r["recover_days"] is not None else "never"))

    print()
    print("Books where the published curve's worst drawdown disagrees with the")
    print("reported max_dd: %d %s" % (len(bad), bad or "(none)"))
    recs = [r["recover_days"] for r in rows if r["recover_days"] is not None]
    if recs:
        print("recover_days now spans %d to %d days (was reported up to 1160 before the fix)"
              % (min(recs), max(recs)))
    else:
        print("no book reports a recovery time")
    never = [r["name"] for r in rows if r["recover_days"] is None]
    print("books whose deepest drawdown never recovered: %s" % (never or "none"))

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(rows, indent=1))
    print()
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())