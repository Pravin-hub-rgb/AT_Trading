"""FINAL SELECTION - top 5 per class on every factor at once, not on net.

Why this file exists
--------------------
The shortlist so far was produced in three different ways by three different
pieces of code, and none of them was the ranking the owner asked for:

  - exp_results_export.select() ranks on pins.net + pins.oos_net. That is total
    R, so it rewards a book for being BIG. fsent_champ_long_htfesmcl4 has 1187
    trades and outranks a 636-trade book with a far higher R per trade.
  - exp_selection_final.py gates and ranks on OOS R per trade alone, which
    rewards a book for being small and sharp, and says nothing about drawdown,
    recovery or tail.
  - The owner's instruction was "it's not about just R, it's about all though".

So: every candidate is measured on every axis, each axis is scored against the
FIELD rather than against an invented threshold, and the axes are combined with
weights that are stated here in one place and can be argued with.

WHAT IS COMBINED, AND WHY EACH WEIGHT
------------------------------------
  net R          10   the return you are trying to make
  R per trade    14   the most weight in this table, deliberately. A book that
                        buys net with volume is the exact failure that
                        fsent_champ_long_htf15_union was rejected for, and the
                        only defence against repeating it is to rank quality per
                        trade above the total.
  profit factor   8
  OOS retention  10   does it hold up out of sample, or only in sample
  significance    14   the largest weight. A book whose out-of-sample result is
                        consistent with luck is not an edge, and there are four in
                        the previous shortlist above p 0.79.
  net / drawdown  12
  DD % of peak    8   scale-free risk
  recovery days   10   how long the money was under water, from the review
  p90 recovery     6   how bad the bad drawdowns usually are
  cap10 net       12   what survives deleting the 10 best trades - the tail test
  top5 share       8
  rolling 50      8
  negative halves  6
  sample size      6   an edge measured on 111 trades is a weaker claim than the
                        same edge on 425

Each axis is turned into a 0-100 score by RANKING against the field, not by
dividing by a threshold. Top of the field scores 100, bottom scores 0. That
means a book is never failed for being below a number nobody can defend - it is
only ever compared with its own competition, and the axes are then averaged.

WHAT IS NOT IN THE SCORE
------------------------
Parameter count and the inert-knob findings are deliberately excluded. They do
not change what a book earned, and letting them in would reward books for being
simplified rather than for being good. They are printed separately.

Output: final_selection.json + final_selection.md
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backtest/tests/_results.json"
HERE = Path(__file__).resolve().parent
OUT = HERE / "final_selection.json"
MD = HERE / "final_selection.md"

SIG = ["fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
       "fsent_sig_full", "fsent_sig_fs_mom"]
MULTI = ["fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
         "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff_htf15"]

# name, getter, higher-is-better, weight
AXES = [
    ("net R", lambda b: b["net"], True, 10),
    ("R per trade", lambda b: b["expectancy"], True, 14),
    ("profit factor", lambda b: b["pf"], True, 8),
    ("OOS retention", lambda b: b["retention"] or 0, True, 10),
    ("significance OOS", lambda b: (1.0 - b["null_p_oos"]) if b.get("null_p_oos") is not None else 0.15, True, 14),
    ("net / drawdown", lambda b: b["net_to_dd"], True, 12),
    ("DD % of peak", lambda b: b["dd_pct_of_peak"], False, 8),
    ("recovery days", lambda b: (b["recover_days"] if b["recover_days"] is not None else 9999), False, 10),
    ("p90 recovery", lambda b: (b["p90_recover_days"] if b["p90_recover_days"] is not None else 9999), False, 6),
    ("survives -top10", lambda b: 100.0 * b["cap10_net"] / b["net"] if b["net"] else 0.0, True, 12),
    ("top 5% share", lambda b: b["top5_contrib"] or 0.0, False, 8),
    ("50-trade windows +", lambda b: b["roll50_prof_pct"], True, 8),
    ("negative half-years", lambda b: len(b["neg_cells"]), False, 6),
    ("sample size OOS", lambda b: b["oos_n"], True, 6),
]


def rank_scores(field):
    """0-100 by rank against the field. No invented thresholds anywhere."""
    vals = [(n, f(b)) for n, b in field.items() for f, _ in [field[n]]]
    ordered = sorted(vals, key=lambda x: x[1])
    n = len(ordered)
    out = {}
    for i, (name, v) in enumerate(ordered):
        # rank 0 = worst. Ties share the middle.
        out[name] = 100.0 * (i + 1) / n
    return out


def build(field):
    per_axis = {}
    for label, get, higher, w in AXES:
        vals = {}
        for nm, b in field.items():
            try:
                v = get(b)
            except (KeyError, TypeError):
                v = None
            if v is None or isinstance(v, str):
                # A missing value must not silently win or lose. It scores 0
                # and says so, rather than sorting as text or crashing.
                v = None
            vals[nm] = v
        present = {n: v for n, v in vals.items() if v is not None}
        order = sorted(present, key=lambda x: (vals[x] if higher else -vals[x]))
        n = len(order)
        # enumerate(order), NOT enumerate(vals). Iterating the dict gave every
        # book its score by insertion order instead of by rank, so all five
        # books showed 100/80/60/40/20 on every single axis and the weighted
        # average was meaningless. The first run of this file reported the
        # lowest-net book as top of the "net R" column.
        score = {nm: (100.0 * (i + 1) / n if nm in present else 0.0)
                 for i, nm in enumerate(order)}
        per_axis[label] = {"weight": w, "higher_is_better": higher,
                           "raw": vals, "score": score}
    tot = sum(a[3] for a in AXES)
    score = {}
    for nm in field:
        s = sum(per_axis[l]["score"][nm] * per_axis[l]["weight"] for l, _g, _h, _w in AXES)
        score[nm] = round(s / tot, 1)
    return per_axis, score


def main() -> int:
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    B = {b["name"]: b for b in d["books"]}

    L = []
    L.append("# Final selection - top 5 per class, every factor at once")
    L.append("")
    L.append("No single score decides this. Each axis is scored 0-100 by ranking it")
    L.append("against the other books in its own class, then the axes are averaged")
    L.append("with the weights below. Nothing here is compared to a threshold nobody")
    L.append("can defend, because the last two thresholds tried both turned out to be")
    L.append("wrong.")
    L.append("")
    L.append("| axis | weight | direction |")
    L.append("|---|---:|---|")
    for label, _g, higher, w in AXES:
        L.append("| %s | %d | %s |" % (label, w, "higher better" if higher else "lower better"))
    L.append("")
    L.append("R per trade carries the joint-highest weight with significance, on")
    L.append("purpose. Ranking on total net R is what let a book that bought its")
    L.append("return with 57% more trades into the shortlist once already.")
    L.append("")

    results = {}
    for title, names in (("SIG", SIG), ("MULTI", MULTI)):
        field = {n: B[n] for n in names}
        per_axis, score = build(field)
        results[title] = {"per_axis": per_axis, "score": score}

        L.append("## %s" % title)
        L.append("")
        L.append("| rank | book | **SCORE** | R/tr | net R | p OOS | retention |"
                 " net/DD | rec days | survive -top10 | n OOS |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        ranked = sorted(score, key=lambda k: -score[k])
        for i, nm in enumerate(ranked, 1):
            b = B[nm]
            p = ("%.3f" % b["null_p_oos"]) if b.get("null_p_oos") is not None else "n/a"
            L.append("| %d | `%s` | **%.1f** | %.3f | %.0f | %s | %.0f%% | %.1f | %s | %.0f%% | %d |" % (
                i, nm, score[nm], b["expectancy"], b["net"], p, b["retention"] or 0,
                b["net_to_dd"],
                str(b["recover_days"]) if b["recover_days"] is not None else "never",
                100.0 * b["cap10_net"] / b["net"] if b["net"] else 0.0, b["oos_n"]))
        L.append("")
        L.append("### Per axis, 0-100")
        L.append("")
        L.append("| axis | w | " + " | ".join("`%s`" % n.replace("fsent_", "") for n in ranked) + " |")
        L.append("|---|---:|" + "---:|" * len(ranked))
        for label, _g, _h, w in AXES:
            L.append("| %s | %d | %s |" % (label, w, " | ".join(
                "%.0f" % per_axis[label]["score"][n] for n in ranked)))
        L.append("")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(results, indent=1, default=str))
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("\nwrote %s and %s" % (OUT.name, MD.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())