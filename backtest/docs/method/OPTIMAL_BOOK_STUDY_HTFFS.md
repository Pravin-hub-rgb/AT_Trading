# OPTIMAL-BOOK STUDY — HTF-FS arms vs the old books, on the CORRECTED chain

**RE-RUN 2026-10-14. The version this replaces was measured 2026-10-10 and every
number in it was produced while B1, B2 and FLIP were landing on the wrong bars.**

The B1 arming fix landed 2026-10-11 (`77711a6`), V13 on 2026-10-12
(`88ecd00`), and the volatile-B1 colour rule plus the same-bar duplicate-pivot
fix on 2026-10-13 (`5d6cab2`, `d71304f`). The chain moved from **2,753 swings /
7,505 marks** to **2,840 swings / 7,734 marks**, and 43 B2s had become FLIPs,
35 FLIPs had become B2s and 51 B1 directions had flipped.

Harness `exp_optimalbook_study.py`, artifact `_optimalbook_study.json`,
framework `docs/learn/finding optimal book.md`.

---

## What this study is and is not

Applying the framework to the new arms alone would be useless. The question is
not "are the new books good" but **"are they better than what we already have,
on the same yardstick"** — so every book in the comparison goes through the same
measurement in one run, and the answer is a column next to the book it has to
beat.

**Covered:** tiers 1, 2, 3, 5, 6.
**Tier 4 (parameter plateau, cost sensitivity, cross-asset) was NOT faked here** —
it is now measured, in `docs/method/ENTRY_BREAK_AND_PLATEAU_TIER4.md`.
**Tier 0 (validity) is PASS/FAIL**, enforced by `exp_fastcheck` and the causality
audit, and no book in this table failed it.

---

## TIER 1 — profitability

| book | tag | n | net | expectancy | PF | WR |
|---|---|---|---|---|---|---|
| `fsent_champ_long_htfesmcl4` | OLD — htf_fs=all | 762 | **770.53** | 1.011 | 3.038 | 39.0% |
| `fsent_champ_long_htf15_htffs` | NEW — flip FS htf15 | 756 | **765.86** | 1.013 | 3.022 | 39.8% |
| `fsent_champ_long_htffs` | NEW — flip FS | 753 | **757.99** | 1.007 | 3.035 | 39.7% |
| `fsent_champ_long_htf15` | OLD | 500 | 505.24 | 1.010 | 3.128 | 39.6% |
| `fsent_champ_long_mcloff` | OLD — best evidence | 533 | 504.12 | 0.946 | 2.946 | 39.6% |
| `fsent_sig_multi` | OLD — best shape | 292 | 372.96 | 1.277 | 3.326 | 43.5% |
| `fsent_champ_long` | OLD — shipping | 497 | 466.92 | 0.940 | 2.886 | 38.6% |
| `fsent_sig_full` | OLD | 215 | 208.96 | 0.972 | 2.643 | 41.4% |

## TIER 2 — equity quality (in-sample)

| book | maxDD | net per DD | maxUW | ulcer | worst-50 |
|---|---|---|---|---|---|
| `fsent_champ_long_htffs` | 22.45 | **33.8** | 123 | 4.72 | −20.41 |
| `fsent_champ_long_htfesmcl4` | 20.02 | **38.5** | 79 | 4.60 | −20.02 |
| `fsent_champ_long_htf15_htffs` | 29.76 | 25.7 | 124 | 5.11 | −20.53 |
| `fsent_champ_long_htf15` | 26.26 | 19.2 | 75 | 3.61 | −8.81 |
| `fsent_champ_long` | 25.08 | 18.6 | 91 | 4.25 | −13.66 |
| `fsent_champ_long_mcloff` | 23.30 | 21.6 | 71 | 4.01 | −12.51 |
| `fsent_sig_multi` | 13.43 | 27.8 | 33 | 3.07 | **+0.95** |
| `fsent_sig_full` | 14.01 | 14.9 | 33 | 3.08 | **+16.65** |

## TIER 5 — the two that matter

| book | expRet | pfRet | wrRet | netRet | ddExp | sign | halves IS / OOS |
|---|---|---|---|---|---|---|---|
| `fsent_champ_long_htf15` | **89.7%** | **97.6%** | 106.1% | 50.4% | **0.43** | both + | **all + / all +** |
| `fsent_champ_long_htf15_htffs` | 86.3% | 95.2% | 99.0% | 45.2% | 0.50 | both + | 2026H2 / 2022H2 |
| `fsent_champ_long` | 81.6% | 92.6% | 106.0% | 46.1% | 0.45 | both + | **all + / all +** |
| `fsent_champ_long_htffs` | 80.0% | 89.9% | 95.7% | 41.3% | 0.66 | both + | 2026H2 / 2022H2 |
| `fsent_champ_long_htfesmcl4` | 78.9% | 88.5% | 97.7% | 44.0% | 0.75 | both + | 2026H2 / 2022H2 |
| `fsent_champ_long_mcloff` | 75.2% | 85.5% | 101.8% | 42.3% | 0.47 | both + | **all + / all +** |
| `fsent_sig_multi` | 77.3% | 89.7% | 116.8% | 49.0% | 0.57 | both + | 2026H2 / all + |
| `fsent_sig_full` | **105.2%** | **110.4%** | 114.3% | **64.1%** | **0.36** | both + | 2026H2 / all + |
| `fsent_sig_multi_htffs` | 72.0% | 82.0% | 103.6% | 38.7% | 0.46 | both + | **all + / all +** |

## TIER 3 — tail dependence, in-sample (net R remaining after removing the tail)

| book | top 1 | top 3 | top 5 | top 10 | top 5% | top 10% |
|---|---|---|---|---|---|---|
| `fsent_champ_long_htfesmcl4` | 727.06 | 647.64 | 586.85 | 469.69 | 126.13 | −86.15 |
| `fsent_champ_long_htf15_htffs` | 722.39 | 642.96 | 582.18 | 465.02 | 125.63 | −79.15 |
| `fsent_champ_long_htffs` | 714.52 | 635.10 | 574.32 | 457.16 | 121.26 | −77.79 |
| `fsent_champ_long_htf15` | 461.78 | 400.99 | 358.39 | 272.64 | 110.57 | −33.53 |
| `fsent_sig_multi_htffs` | 467.90 | 404.12 | 348.61 | 239.56 | 102.24 | −24.69 |
| `fsent_champ_long_mcloff` | 460.65 | 399.87 | 358.29 | 272.54 | 95.72 | −46.48 |
| `fsent_sig_multi` | 320.76 | 248.92 | 199.72 | 111.33 | 59.06 | −26.96 |
| `fsent_champ_long` | 423.45 | 362.67 | 321.09 | 235.34 | 74.88 | −63.33 |
| `fsent_sig_full` | 165.33 | 120.58 | 82.96 | 27.95 | 20.16 | −40.67 |

## TIER 6 — complexity (parameters differing from the shipping base)

| book | knobs | which |
|---|---|---|
| `fsent_champ_long` | 0 | none — shipping |
| `fsent_champ_long_mode_atr_low` | 11 | not in this study |
| `fsent_champ_long_htf15` | 4 | atr_low_thresh, chop_thresh, ext_stop_r, max_positions |
| `fsent_champ_long_htffs` | 5 | + exp_htf_fs_entry |
| `fsent_champ_long_htf15_htffs` | 5 | + exp_htf_fs_entry |
| `fsent_champ_long_mcloff` | 5 | atr_low_thresh, chop_thresh, ext_stop_r, max_consecutive_losses, max_positions |
| `fsent_champ_long_htfesmcl4` | 6 | + exp_htf_fs_entry |
| `fsent_sig_multi` / `fsent_sig_full` | 13 | serial stack |
| `fsent_sig_multi_htffs` | 14 | + exp_htf_fs_entry |

---

# WHAT CHANGED AGAINST THE 2026-10-10 RUN

Every book lost trades and net. That is the marking fix showing through, not a
new defect: the old numbers were measured while the marks were on the wrong bars,
so the swing set was wrong and every entry derived from it moved.

| book | OLD n / net (IS) | NEW n / net (IS) | OLD OOS | NEW OOS |
|---|---|---|---|---|
| `fsent_champ_long` | 528 / 533.37 | 497 / 466.92 | 239.59 | 215.32 |
| `fsent_champ_long_mcloff` | 575 / 566.59 | 533 / 504.12 | 270.91 | 213.27 |
| `fsent_champ_long_htf15` | 520 / 567.57 | 500 / 505.24 | 254.88 | 254.81 |
| `fsent_champ_long_htfesmcl4` | 793 / 917.80 | 762 / 770.53 | 326.22 | 339.08 |
| `fsent_sig_multi` | 329 / 484.59 | 292 / 372.96 | 219.82 | 182.77 |
| `fsent_sig_full` | 234 / 295.83 | 215 / 208.96 | 194.44 | 133.91 |
| `fsent_champ_long_htffs` | 770 / 897.94 | 753 / 757.99 | 300.43 | 313.35 |
| `fsent_champ_long_htf15_htffs` | 761 / 925.79 | 756 / 765.86 | 304.17 | 346.07 |
| `fsent_sig_multi_htffs` | 434 / 666.32 | 417 / 511.52 | 234.48 | 197.73 |

**Three books gained out of sample** — `htfesmcl4` (+12.86R), `htffs` (+12.92R),
`htf15_htffs` (+41.90R). The other six lost.

## THE VERDICT CHANGED, AND THIS IS THE PART THAT MATTERS

**The old run concluded `mcloff` was the recommendation and the HTF-FS arms were
not worth chasing.** On the corrected chain that reasoning does not hold, for
three specific reasons:

**1. `fsent_champ_long_htf15` now has the best retention of any multi book** —
89.7% expectancy, 97.6% PF, 0.43 DD expansion, and **all eight in-sample AND all
eight out-of-sample half-years positive**. On the old chain `htf15` was nowhere
near the top.

Note what is *not* claimed here: four books clear the half-year test in both
eras — `fsent_champ_long`, `fsent_champ_long_mcloff`,
`fsent_sig_multi_htffs` and `fsent_champ_long_htf15`. The half-year column is not
what separates them. What separates `htf15` is that it is the only one of those
four that also leads on expectancy retention.

**2. The old run's tail finding has inverted.** It said `htf15_htffs` "survives
deleting its top 10% and still shows +11.72R where mcloff shows −55.72R". On the
corrected chain `htf15_htffs` shows **−79.15R** after removing its top 10%, and
`mcloff` shows **−46.48R**. The specific claim is retired.

**3. What survives is a trade-off, not a hierarchy.** `htfesmcl4` and the two
htffs books have the highest net and the best tier-1 numbers, and the two htffs
books convert return to drawdown best (33.8 and 25.7 net per unit of DD against
`htf15`'s 19.2) — but their expectancy retention is the worst in the table
(78.9%, 80.0%, 86.3%) and each breaks a half-year in **each** era. `htf15` is the
mirror: mid-pack net, the best retention, the lowest DD expansion, and a clean
half-year record in both eras.

**4. On worst-rolling periods the picture inverts again.** `fsent_sig_full` has
the only strongly positive worst-50 in the table (+16.65) and
`fsent_sig_multi` is +0.95; every multi book is negative, `htf15` least of them
at −8.81. A book whose worst 50 trades are still positive is telling you
something the retention column does not.

## RECOMMENDATION — unchanged in direction, changed in the runner-up

**`fsent_champ_long_htf15` is now the strongest candidate to examine next**, ahead
of `mcloff`. It costs the same 4 knobs, it retains the most expectancy of any
multi book, it expands drawdown least, and it is the only high-net book with a
clean half-year record in both eras.

**This is a study, not an adoption.** Nothing here changes the shipping book.
`fsent_champ_long` remains the shipping entry, and the same rule applies as
before: a book that has not been looked at on the chart is not adopted.

## HONEST LIMITS

- **Tier 4 was not covered here.** It is covered now, separately, in
  `ENTRY_BREAK_AND_PLATEAU_TIER4.md` — and the entry-break result there is large
  enough that it should be read alongside this table.
- **Nine books is a small sample.** The retention ordering has moved by several
  points between runs, so a 2-3 point gap between two books is not a ranking.
  `htf15` leads `htf15_htffs` by 3.4 points of expectancy retention, which is
  inside that noise.
- **Cost sensitivity here is an approximation** and is labelled as one: the
  per-trade cost is re-applied to the same trade series, so it measures how much
  of the edge costs eat, but it cannot capture fills that would differ at a
  different fee level.
- **The half-year split is 8 cells per era.** "all positive" is 8/8 and means
  something; one negative cell is 1/8 and does not on its own retire a book.