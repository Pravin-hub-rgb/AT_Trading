"""Risk-adjusted scorecard for the shortlisted books.

Built from the owner's risk-adjustment review, which set out eight numbers a
strategy should be judged on rather than one ceiling:

    1. Net R                2. Max DD in R          3. Max DD in %
    4. Net R / Max DD       5. Max DD duration      6. Recovery time
    7. Worst rolling 50/100 8. Worst 3/6/12 months

and, in the review's own words, "koi universal number nahi hai" for acceptable
drawdown - so this file prints columns and applies no gate at all. The old
fixed 29R ceiling and the 5% percentage I invented to replace it are both gone
from exp_results_export.py.

THE RISK UNIT IS FIXED 1R, NOT A SHARE OF EQUITY
-----------------------------------------------
unified.py computes r_multiple = move/risk, so every trade risks the same fixed
amount and R IS the account unit. Two consequences, and they matter for reading
this table:

  - max_dd in R is the primary and most honest measure. It needs no assumption.
  - dd_pct_of_peak is scale-free and comparable across books of any size.
    dd_pct_1 and dd_pct_2 convert the same drawdown to a share of account at 1%
    and 2% risk per R, and are only meaningful once a position size is chosen.

WHAT TO READ, IN THE REVIEW'S TERMS
-----------------------------------
"A strategy 5% historical DD ke saath bhi unsuitable ho sakti hai agar uska
worst drawdown 8 mahine tak recover na ho. Doosri 12% DD ke saath manageable ho
sakti hai agar returns robust hon."

So dd_days and recover_days are not footnotes. A book with a small dd_pct_of_peak
and a four-figure recover_days is the case the review is describing.

Output: risk_scorecard.md
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backtest/tests/_results.json"
CARD = Path(__file__).resolve().parent / "risk_scorecard.md"

SIG = ["fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
       "fsent_sig_full", "fsent_sig_fs_mom"]
MULTI = ["fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
         "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff_htf15"]

# What "good" looks like on each axis, stated once so every book is read against
# the SAME yardstick and no book is compared to another by eye. These are
# descriptors of the field's own range, not pass/fail gates - the review was
# explicit that a universal drawdown limit does not exist.
AXES = [
    # (label, key, getter, better, note)
    ("net R", "net", lambda b: b["net"], "high", "total return, both eras"),
    ("R/trade", "exp", lambda b: b["expectancy"], "high", "quality per trade"),
    ("net/DD", "nd", lambda b: b["net_to_dd"], "high", "return per unit of drawdown"),
    ("maxDD R", "dd", lambda b: b["max_dd"], "low", "R is the account unit here"),
    ("DD %peak", "ddp", lambda b: b["dd_pct_of_peak"], "low", "scale-free"),
    ("DD days", "ddd", lambda b: b["dd_days"], "low", "how long under water"),
    ("recover d", "rec", lambda b: b["recover_days"], "low", "peak to flat again"),
    ("worst 3m", "w3", lambda b: b["worst_3m"], "high", "bad quarter"),
    ("worst 6m", "w6", lambda b: b["worst_6m"], "high", "bad half"),
    ("worst 12m", "w12", lambda b: b["worst_12m"], "high", "bad year"),
    ("roll20 %", "r20", lambda b: b["roll20_prof_pct"], "high", "trade windows"),
    ("roll50 %", "r50", lambda b: b["roll50_prof_pct"], "high", "trade windows"),
    ("worstR50", "wr50", lambda b: b["worst_roll50"], "high", "deepest 50-trade hole"),
    ("cap10 %", "cap", lambda b: 100.0 * b["cap10_net"] / b["net"] if b["net"] else 0.0,
     "high", "net left after dropping the 10 best trades"),
    ("top5 %", "t5", lambda b: b["top5_contrib"], "high", "share of net from best 5%"),
    ("retention", "ret", lambda b: b["retention"], "high", "IS expectancy -> OOS"),
    ("neg half", "neg", lambda b: len(b["neg_cells"]), "low", "complete half-years"),
    ("p OOS", "poos", lambda b: b["null_p_oos"], "low", "chance of being this good by luck"),
]


def main() -> int:
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    B = {b["name"]: b for b in d["books"]}
    L = []
    L.append("# Risk-adjusted scorecard - the shortlist")
    L.append("")
    L.append("No gate. No pass/fail. Columns only, per the risk-adjustment review:")
    L.append('"koi universal number nahi hai" for acceptable drawdown. The fixed 29R')
    L.append("ceiling is gone and so is the 5% percentage I put in its place.")
    L.append("")
    L.append("**Risk is FIXED 1R per trade** (`r_multiple = move/risk` in unified.py),")
    L.append("so R is the account unit and `maxDD R` is the primary measure.")
    L.append("")
    L.append("`recover d` is the number the review says decides things: *\"ek strategy")
    L.append("5% historical DD ke saath bhi unsuitable ho sakti hai agar uska worst")
    L.append("drawdown 8 mahine tak recover na ho.\"*")
    L.append("")

    for title, names in (("SIG", SIG), ("MULTI", MULTI)):
        L.append("## %s" % title)
        L.append("")
        L.append("| book | " + " | ".join(a[0] for a in AXES) + " |")
        L.append("|" + "---|" * (len(AXES) + 1))
        for n in names:
            b = B[n]
            cells = []
            for _lab, _k, f, better, _note in AXES:
                try:
                    v = f(b)
                except (KeyError, TypeError):
                    cells.append("-")
                    continue
                if v is None:
                    cells.append("n/a")
                elif isinstance(v, float):
                    cells.append("%.2f" % v)
                else:
                    cells.append("%d" % v)
            L.append("| `%s` | %s |" % (n, " | ".join(cells)))
        L.append("")

    # per-axis best/worst, so the eye does not have to scan twelve columns
    L.append("## Best on each axis")
    L.append("")
    L.append("| axis | better | SIG best | MULTI best |")
    L.append("|---|---|---|---|")
    for lab, k, f, better, note in AXES:
        row = {}
        for title, names in (("SIG", SIG), ("MULTI", MULTI)):
            vals = []
            for n in names:
                try:
                    v = f(B[n])
                except (KeyError, TypeError):
                    v = None
                if v is not None:
                    vals.append((n, v))
            if not vals:
                row[title] = "-"
                continue
            pick = (max if better == "high" else min)(vals, key=lambda x: x[1])
            row[title] = "%s (%s)" % (pick[0].replace("fsent_", ""),
                                      ("%.2f" % pick[1]) if isinstance(pick[1], float) else pick[1])
        L.append("| %s | %s | %s | %s |" % (lab, better, row["SIG"], row["MULTI"]))
    L.append("")

    L.append("## Axis notes")
    L.append("")
    for lab, k, f, better, note in AXES:
        L.append("- **%s** (%s) - %s" % (lab, better, note))
    L.append("")
    L.append("`neg half` counts only COMPLETE half-years. A period the data has not")
    L.append("finished is excluded and listed in `partial_cells`; without that, four")
    L.append("of the five SIG books carried their only negative half-year in a")
    L.append("2026-H2 the data has barely lived through.")

    io.open(CARD, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("\nwrote %s" % CARD.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())