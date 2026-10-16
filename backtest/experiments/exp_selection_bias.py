"""E5-B  SELECTION BIAS - is the shortlist better than picking at random?

THE WARNING THAT PROMPTED THIS
-----------------------------
> "Agar tune already bahut saare filters, cooldowns aur parameter combinations
>  test karke best book select ki hai, to usi selected book ki p-value selection
>  bias ko automatically fix nahi karti."

Correct, and it applies to the shortlist as much as to any single p-value. Ten
books were chosen by reading the metrics. Whatever they score is a score AFTER
selection, and the question is whether they are actually unusual or whether I
picked the best-looking of a set where everything looks mediocre.

THE TEST
--------
1. Score EVERY book with a full lens, not just the ten. 26 books have one.
2. Report where each shortlisted book sits among all 26. A shortlist that is
   genuinely good sits high; a shortlist that is the best of a bad field does not.
3. Monte Carlo the actual decision. Draw 10 books at random from the 26, split by
   class, take the best of each, and see how often random picking lands at or
   above the real shortlist. That is the number that answers the question:
   "if I had just picked at random, would I have done this well?"

WHAT IT CANNOT DO
-----------------
This tests the selection against the field the lens can measure. It does not
correct for the searches that produced the registry itself - 97 books each built
by trying knobs - and it does not touch the fact that the out-of-sample era is
reused old data rather than a holdout (OOS_IS_NOT_A_HOLDOUT.md). No test here
can correct for those. They are stated, not solved.

Output: selection_bias.json
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backtest/tests/_results.json"
HERE = Path(__file__).resolve().parent
OUT = HERE / "selection_bias.json"

SIG = ["fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
       "fsent_sig_full", "fsent_sig_fs_mom"]
MULTI = ["fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
         "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff_htf15"]

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

# Missing significance is not a zero and not a neutral 50. It is genuinely worse
# than a tested book: nobody has shown the out-of-sample result is not luck.
UNTESTED_SIGNIFICANCE = 0.15


def axis_scores(books):
    """0-100 per axis by rank across the WHOLE field, not within a class."""
    per = {}
    for label, get, higher, w in AXES:
        vals = {}
        for n, b in books.items():
            try:
                v = get(b)
            except (KeyError, TypeError):
                v = None
            vals[n] = None if isinstance(v, str) else v
        present = {n: v for n, v in vals.items() if v is not None}
        order = sorted(present, key=lambda x: (vals[x] if higher else -vals[x]))
        n = len(order)
        per[label] = {nm: (100.0 * (i + 1) / n if nm in present else 0.0)
                      for i, nm in enumerate(order)}
    return per


def score_of(per, name):
    tot = sum(a[3] for a in AXES)
    return round(sum(per[l][name] * per[l + "_w"] if False else per[l][name] * next(
        w for lb, _g, _h, w in AXES if lb == l) for l in per) / tot, 1)


def main() -> int:
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    B = {b["name"]: b for b in d["books"]}
    field = dict(B)
    per = axis_scores(field)
    wt = {lb: w for lb, _g, _h, w in AXES}
    tot = sum(wt.values())
    score = {n: round(sum(per[l][n] * wt[l] for l, _g, _h, _w in AXES) / tot, 1)
             for n in field}

    sig_names = [n for n, b in field.items() if b.get("position_mode") == "single"]
    multi_names = [n for n, b in field.items() if b.get("position_mode") == "multi"]
    for n, b in field.items():
        mp = (b.get("position_mode"))
        if mp not in ("single", "multi"):
            print("  WARNING unclassified book:", n, mp)

    print("=" * 104)
    print("1. WHERE THE SHORTLIST SITS AMONG ALL %d BOOKS" % len(field))
    print("=" * 104)
    ranked = sorted(field, key=lambda k: -score[k])
    posn = {n: i + 1 for i, n in enumerate(ranked)}
    print("  %-36s %8s %8s  %s" % ("book", "SCORE", "rank/26", "in shortlist"))
    print("  " + "-" * 74)
    for cls, names in (("SIG", SIG), ("MULTI", MULTI)):
        print("  --- %s ---" % cls)
        for n in names:
            print("  %-36s %8.1f %6d/%-3d  %s"
                  % (n, score[n], posn[n], len(field),
                     "yes" if n in names else ""))
    print()

    print("=" * 104)
    print("2. MONTE CARLO - pick 5 per class AT RANDOM, how often do you match the real shortlist?")
    print("=" * 104)
    import random
    rnd = random.Random(20261015)
    N = 20000
    real_sig = max(score[n] for n in SIG)
    real_mul = max(score[n] for n in MULTI)
    beat_sig = 0
    beat_mul = 0
    for _ in range(N):
        s = rnd.sample(sig_names, 5) if len(sig_names) >= 5 else sig_names
        m = rnd.sample(multi_names, 5) if len(multi_names) >= 5 else multi_names
        if max(score[x] for x in s) >= real_sig:
            beat_sig += 1
        if max(score[x] for x in m) >= real_mul:
            beat_mul += 1
    print("  SIG   best shortlisted = %.1f (%s)"
          % (real_sig, max(SIG, key=lambda n: score[n])))
    print("        random 5 of %d matched or beat it in %d of %d draws  -> p = %.4f"
          % (len(sig_names), beat_sig, N, beat_sig / N))
    print("  MULTI best shortlisted = %.1f (%s)"
          % (real_mul, max(MULTI, key=lambda n: score[n])))
    print("        random 5 of %d matched or beat it in %d of %d draws  -> p = %.4f"
          % (len(multi_names), beat_mul, N, beat_mul / N))
    print()
    print("  p = 1.00 would mean random picking does just as well, and the shortlist")
    print("  is the best of a mediocre field. p well under 0.05 means the selection")
    print("  found something the field does not usually contain.")

    out = {"score": score, "rank": posn, "n_books": len(field),
           "monte_carlo": {"draws": N, "sig": {"real_best": real_sig, "p": beat_sig / N},
                           "multi": {"real_best": real_mul, "p": beat_mul / N}},
           "untested_significance_score": UNTESTED_SIGNIFICANCE}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=float))
    print()
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())