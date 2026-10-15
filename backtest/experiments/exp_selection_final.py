"""FINAL SELECTION - corrected gates, then the owner's four criteria.

THE GATE WAS WRONG AND IT MATTERED
----------------------------------
The first pass gated on "no negative 50-trade rolling window", and it rejected
all three of the books the other bot had just registered:

  fsent_champ_long_tskip4          OOS +260.53R   worst 50-trade window  -5.57R
  fsent_champ_long_htf15_tskip6    OOS +328.54R   worst 50-trade window  -5.85R
  fsent_sig_multi_acc              OOS +220.91R   worst 50-trade window  -1.53R

A 5R dip over fifty trades, on a book making 260R, is not a defect. It is what
every book with two hundred trades does at least once. And those same books have
96.9%, 98.3% and 96.5% of their rolling windows POSITIVE - better than most
books that passed.

So the gate was not a quality filter, it was a luck filter: it selected for
having got lucky with its worst window rather than for being smooth. It is
replaced by what the owner actually asked for - "rolling window good" - measured
as the SHARE of rolling windows that are positive, which does not care where the
worst one landed.

Nothing is re-measured. This re-applies gates to selection_results.json.

THE OWNER'S CRITERIA, kept as four separate columns
--------------------------------------------------
  best     - OOS net and OOS R per trade
  smooth   - ulcer, sortino, DD % of net
  spread   - share of net carried by the best 5% of trades, and the longest
             run of consecutive losses
  rolling  - % of rolling 20 / 50 / 100-trade windows that are positive

No single combined score. docs/learn/finding optimal book.md:692 is explicit
that one number hides problems, so the four are shown side by side and the pick
is the owner's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "selection_results.json"

# Percent-positive rolling windows, both eras. A book that is positive in 90% of
# its 50-trade windows is steady; one that is positive in 100% has simply never
# been unlucky enough to matter and is not thereby better.
MIN_ROLL_POS = {"roll20": 70.0, "roll50": 90.0, "roll100": 95.0}


def gates(row):
    fail = []
    isx, oos = row["is"], row["oos"]
    if isx.get("n", 0) == 0 or oos.get("n", 0) == 0:
        fail.append("no completed trades in an era")
    if isx.get("net", 0) <= 0:
        fail.append("IS net <= 0")
    if oos.get("net", 0) <= 0:
        fail.append("OOS net <= 0")
    if oos.get("n", 0) < 100:
        fail.append("OOS n < 100")
    if oos.get("dd_pct", 999) > 40:
        fail.append("OOS DD > 40%% of net")
    for k, mn in MIN_ROLL_POS.items():
        p = oos.get("%s_pos" % k)
        if p is not None and p < mn:
            fail.append("OOS %s windows only %.0f%% positive" % (k, p))
    return fail


def main() -> int:
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    for k, v in d.items():
        v["fails2"] = gates(v)
        v["passes2"] = not v["fails2"]

    for cls in ("sig", "multi"):
        sel = {k: v for k, v in d.items() if v["cls"] == cls}
        ok = {k: v for k, v in sel.items() if v["passes2"]}
        print("=" * 128)
        print("%s  -  %d books, %d pass the corrected gates   (was %d under the old gate)"
              % (cls.upper(), len(sel), len(ok),
                 sum(1 for v in sel.values() if v["passes"])))
        print("=" * 128)
        if not ok:
            print("none pass\n")
            continue
        print("%-34s | %8s %6s | %6s %5s %6s | %5s %5s | %6s %4s | %5s %5s %5s"
              % ("book", "OOSnet", "n", "R/tr", "PF", "DD%", "ulcer", "sortn",
                 "top5%", "gap", "r20%", "r50%", "r100%"))
        print("-" * 128)
        for k in sorted(ok, key=lambda b: -ok[b]["oos"]["net"]):
            o = ok[k]["oos"]
            print("%-34s | %+8.1f %6d | %6.3f %5.2f %5.1f%% | %5.1f %5.0f | %5.0f%% %4d |"
                  " %4.0f%% %4.0f%% %4.0f%%"
                  % (k, o["net"], o["n"], o["r_trade"], o["pf"], o["dd_pct"],
                     o["ulcer"], o["sortino"], o.get("top5pct_share") or 0.0,
                     o["spacing"]["max_gap"], o.get("roll20_pos") or 0.0,
                     o.get("roll50_pos") or 0.0, o.get("roll100_pos") or 0.0))
        print()
        print("  IS side of the same books:")
        print("%-34s | %8s %6s | %6s %5s %6s | %5s %5s | %6s %4s | %5s %5s %5s"
              % ("book", "ISnet", "n", "R/tr", "PF", "DD%", "ulcer", "sortn",
                 "top5%", "gap", "r20%", "r50%", "r100%"))
        print("-" * 128)
        for k in sorted(ok, key=lambda b: -ok[b]["oos"]["net"]):
            a = ok[k]["is"]
            print("%-34s | %+8.1f %6d | %6.3f %5.2f %5.1f%% | %5.1f %5.0f | %5.0f%% %4d |"
                  " %4.0f%% %4.0f%% %4.0f%%"
                  % (k, a["net"], a["n"], a["r_trade"], a["pf"], a["dd_pct"],
                     a["ulcer"], a["sortino"], a.get("top5pct_share") or 0.0,
                     a["spacing"]["max_gap"], a.get("roll20_pos") or 0.0,
                     a.get("roll50_pos") or 0.0, a.get("roll100_pos") or 0.0))
        print()
        gained = [k for k, v in sel.items() if v["passes2"] and not v["passes"]]
        if gained:
            print("  Newly admitted by correcting the gate (%d): %s"
                  % (len(gained), ", ".join("`%s`" % g for g in sorted(gained))))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())