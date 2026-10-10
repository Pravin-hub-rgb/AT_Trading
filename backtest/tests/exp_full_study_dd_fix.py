"""Recompute the peak-relative drawdown properly, from the saved series.

The first version reported "232% drawdown from peak", which is arithmetic working
correctly on a nonsense denominator. The peak here is the account's running high
in R, and at trade 12 that high might be 4R. A fall from 4R to 3R is then a 25%
drawdown - correctly computed, and completely meaningless, because no account is
ever 4% of notional in a way that makes 25% the headline risk.

So two replacements, both computed from `_full_study.json`'s saved series - no
backtests re-run.

  peak_pct_final    max DD in R divided by the FINAL peak R. Stable, no
                    degenerate early zone, and it answers the question that got
                    this started: how big is the dip relative to how big the book
                    turned out to be.

  peak_pct_running  the textbook (equity - peak) / peak, but only counted once
                    the account has reached 100R of peak, so the early period
                    where the denominator is tiny cannot win the maximum.

The account-level numbers from the main run are kept as they are; they were
correct and needed no change.
"""
import json
import sys

sys.path.insert(0, ".")

PEAK_FLOOR_R = 100.0


def main():
    d = json.load(open("_full_study.json", encoding="utf-8"))
    rows = []
    for key, rec in d.items():
        rs = rec.get("_series")
        if not rs:
            continue
        cum = pk = 0.0
        pk_r = 0.0
        mdd_r = 0.0
        best_running = 0.0
        for r in rs:
            cum += r
            if cum > pk:
                pk = cum
                pk_r = max(pk_r, cum)
            ddr = pk - cum
            if ddr > mdd_r:
                mdd_r = ddr
            if pk_r >= PEAK_FLOOR_R and pk > 0:
                p = (pk - cum) / pk * 100.0
                if p > best_running:
                    best_running = p
        final = mdd_r / pk_r * 100.0 if pk_r > 0 else 0.0
        rec["dd"]["peak_pct_final"] = round(final, 2)
        rec["dd"]["peak_pct_running_floor100"] = round(best_running, 2)
        rows.append((final, best_running, key, rec))

    rows.sort(key=lambda x: -x[2 - 2]["net"] if False else -d[x[2]]["net"])
    print()
    print("#" * 122)
    print("DRAWDOWN RELATIVE TO THE BOOK -  the owner's question: is 29R a lot, or")
    print("a lot only next to a book that made 295R?  peak floor %gR for the running form."
          % PEAK_FLOOR_R)
    print("#" * 122)
    print("  %-30s %9s %9s %11s %10s %12s %12s"
          % ("book", "net R", "DD R", "DD/peak%", "running%", "DD@1% acct", "recover%"))
    print("  " + "-" * 118)
    for final, running, key, rec in rows:
        dd = rec["dd"]["1%risk"]
        print("  %-30s %9s %9s %11s %10s %12s %12s"
              % (key[:30], "%9.2f" % rec["net"], "%9.2f" % dd["mdd_r"],
                 "%10.2f%%" % final, "%9.2f%%" % running,
                 "%.2f%%" % dd["acct_1pct"], "%.1f%%" % dd["recovery_pct_1pct"]))

    json.dump(d, open("_full_study.json", "w", encoding="utf-8"), indent=1)
    print("\n  _full_study.json updated with the corrected peak-relative figures")
    return 0


if __name__ == "__main__":
    sys.exit(main())