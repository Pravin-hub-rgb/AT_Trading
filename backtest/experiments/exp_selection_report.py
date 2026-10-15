"""Report the selection scorecard from selection_results.json.

Split from exp_selection.py because that harness spent 48 minutes measuring 96
books and then died in its own reporting section - sorted(ok, key=key) passes
each ELEMENT of the iterable to key, so key received a book NAME where it
expected a row. The measurements were already on disk; re-running them to fix
four lines of formatting would have been the expensive way to learn that.

Usage:  python exp_selection_report.py
Output: selection_scorecard.md  (printed)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "selection_results.json"
CARD = HERE / "selection_scorecard.md"


def by_oos_r(row):
    return -(row["oos"]["net"] / max(row["oos"]["n"], 1))


def by_oos_pf(row):
    return -(row["oos"]["pf"])


def main() -> int:
    if not RESULTS.exists():
        print("run exp_selection.py first - no results on disk")
        return 1
    d = json.loads(RESULTS.read_text(encoding="utf-8"))

    L = []
    L.append("# Selection scorecard")
    L.append("")
    L.append("Built %s from `selection_results.json`. Per `docs/learn/finding optimal book.md`:698"
             % time.strftime("%Y-%m-%d"))
    L.append("- gates first, then a scorecard, deliberately not one combined score.")
    L.append("")
    L.append("**sig and multi are never mixed.** `BASELINE.md:63` - \"a signal book cannot be")
    L.append("compared against a multi-position book\", they are different objects.")
    L.append("")
    L.append("Classification is by the `max_positions` param, NOT by name. `fsent_sig_multi_acc`")
    L.append("is filed under multi: its name says sig, its params say 0, and the other bot's own")
    L.append("note records it running up to 7 concurrent positions.")
    L.append("")
    L.append("Gates: IS net > 0, OOS net > 0, OOS n >= 100, OOS DD <= 40% of net, no negative")
    L.append("50-trade rolling window in OOS.")
    L.append("")
    L.append("`roll20/50/100` are the WORST rolling sum over that window - negative means the")
    L.append("book had a stretch of N consecutive trades in the red. `top5%` is the share of net")
    L.append("carried by the best 5% of trades. `max gap` is the longest run of consecutive")
    L.append("losing trades.")
    L.append("")

    for cls in ("sig", "multi"):
        sel = {k: v for k, v in d.items() if v["cls"] == cls}
        ok = {k: v for k, v in sel.items() if v["passes"]}
        L.append("## %s - %d books, %d pass the gates" % (cls.upper(), len(sel), len(ok)))
        L.append("")
        if not ok:
            L.append("none pass.")
            L.append("")
            continue
        L.append("| book | OOS net | OOS n | OOS R/tr | OOS PF | DD | DD% | ulcer | sortino |"
                 " roll20 | roll50 | roll100 | %mo+ | worst yr | top5% | max gap | params |")
        L.append("|" + "---|" * 17)
        for k in sorted(ok, key=lambda b: by_oos_r(ok[b])):
            a, b = ok[k]["is"], ok[k]["oos"]
            L.append("| `%s` | %+.1f | %d | %.3f | %.2f | %.1f | %.1f%% | %.1f | %.0f |"
                     " %+.1f | %+.1f | %+.1f | %.0f%% | %+.1f | %.0f%% | %d | %d |" % (
                         k, b["net"], b["n"], b["r_trade"], b["pf"], b["max_dd"], b["dd_pct"],
                         b["ulcer"], b["sortino"],
                         b.get("roll20_worst") or 0.0, b.get("roll50_worst") or 0.0,
                         b.get("roll100_worst") or 0.0, b["pos_month_pct"], b["worst_year"],
                         b.get("top5pct_share") or 0.0, b["spacing"]["max_gap"],
                         ok[k]["n_params"]))
        L.append("")
        L.append("Same books, IS side:")
        L.append("")
        L.append("| book | IS net | IS n | IS R/tr | IS PF | DD | DD% | ulcer |"
                 " roll20 | roll50 | roll100 | %mo+ | worst yr | top5% |")
        L.append("|" + "---|" * 15)
        for k in sorted(ok, key=lambda b: by_oos_r(ok[b])):
            a = ok[k]["is"]
            L.append("| `%s` | %+.1f | %d | %.3f | %.2f | %.1f | %.1f%% | %.1f |"
                     " %+.1f | %+.1f | %+.1f | %.0f%% | %+.1f | %.0f%% |" % (
                         k, a["net"], a["n"], a["r_trade"], a["pf"], a["max_dd"], a["dd_pct"],
                         a["ulcer"], a.get("roll20_worst") or 0.0,
                         a.get("roll50_worst") or 0.0, a.get("roll100_worst") or 0.0,
                         a["pos_month_pct"], a["worst_year"], a.get("top5pct_share") or 0.0))
        L.append("")
        failed = {k: v for k, v in sel.items() if not v["passes"]}
        if failed:
            from collections import Counter
            c = Counter(f for v in failed.values() for f in v["fails"])
            L.append("Failed the gates, %d books. Reasons:" % len(failed))
            for reason, k in c.most_common():
                L.append("- %s - %d books" % (reason, k))
            L.append("")

    CARD.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print()
    print("wrote %s" % CARD.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())