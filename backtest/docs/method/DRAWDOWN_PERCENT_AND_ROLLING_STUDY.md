# DRAWDOWN AS A PERCENTAGE, ONE CONTINUOUS TIMELINE, AND THE P-VALUE

**RE-RUN 2026-10-14 on the corrected chain (2,840 swings / 7,734 marks).**
The version this replaces was measured 2026-10-10, before the B1 arming fix
(`77711a6`), V13 (`88ecd00`) and the volatile-B1 / same-bar pivot work
(`5d6cab2`, `d71304f`).

Harness `exp_full_study.py`, artifact `_full_study.json`, 33 books.
Net R after costs (55bp fee/side, 2×, 5bp entry slippage, 1bp exit).

---

## Why express drawdown as a percentage of the account at all

Because **the same R drawdown is a different event depending on how much the
account made first.** A 25R drawdown taken from a peak of 9R is a catastrophe.
The same 25R taken from a peak of 685R is a 3.7% wobble.

`fsent_champ_long` makes the point cleanly: its max drawdown is **25.08R**, but
the peak it fell from was **685.30R**, so the account went from 685R to 660R —
**a 3.7% move on a book that then tripled.**

Reporting only "max DD = 25.08R" makes that book look identical to one that drew
down 25R from a 9R peak, which is why the old ranking sorted on R alone and why
it sorted wrong.

## Drawdown against the account, both risk levels

| book | n | net | maxDD (R) | account @1% | account @2% | DD as % of net | peak at DD | trades in DD |
|---|---|---|---|---|---|---|---|---|
| `fsent_champ_long_mode_atr_low` | 881 | 708.13 | 48.76 | **48.76%** | 97.51% | 6.9% | — | — |
| `fsent_champ_long_mode_union` | 1210 | 691.72 | 47.61 | **47.61%** | 95.22% | 6.9% | — | — |
| `fsent_champ_long_htf15_htffs` | 1152 | 1111.93 | 29.76 | 29.76% | 59.52% | 2.7% | — | — |
| `fsent_champ_trailhalf` | 701 | 659.06 | 29.38 | 29.38% | 58.76% | 4.5% | — | — |
| `fsent_champ_long_mcloff_htf15` | 837 | 809.94 | 28.38 | 28.38% | 56.76% | 3.5% | — | — |
| `fsent_champ_long_htf15` | 781 | 760.06 | 26.26 | 26.26% | 52.52% | 3.5% | — | — |
| `fsent_champ_long_mode_fd` | 763 | 648.48 | 25.94 | 25.94% | 51.88% | 4.0% | — | — |
| `fsent_champ_long` | 778 | 682.24 | 25.08 | 25.08% | 50.17% | **3.7%** | 685.30 | 778 |
| `fsent_champ_long_causalfloor` | 760 | 683.02 | 24.47 | 24.47% | 48.94% | 3.6% | — | — |
| `fsent_utcsat_long` | 773 | 682.97 | 23.81 | 23.81% | 47.61% | 3.5% | — | — |
| `fsent_champ_long_mcloff` | 833 | 717.39 | 23.30 | 23.30% | 46.61% | 3.2% | — | — |
| `fsent_sig_multi` | 477 | 555.73 | 13.43 | 13.43% | 26.86% | — | — | — |
| `fsent_sig_full` | 346 | 342.86 | 14.01 | 14.01% | 28.02% | — | — | — |

## THE OWNER'S 29R BUDGET, AND WHICH BOOKS BUST IT

**Four books are at or past 29R at 1% risk:**

| book | account DD @1% | over budget by |
|---|---|---|
| `fsent_champ_long_mode_atr_low` | 48.76% | **+68%** |
| `fsent_champ_long_mode_union` | 47.61% | **+64%** |
| `fsent_champ_long_htf15_htffs` | 29.76% | +3% |
| `fsent_champ_trailhalf` | 29.38% | +1% |

**At 2% risk, every book in the table busts 29R** except the two serial signal
books, and both are then close to a 50% account drawdown. **The 29R budget is
only meaningful at 1% risk, and that should be stated whenever it is quoted.**

## WHAT CHANGED AGAINST THE 2026-10-10 RUN

Every net is 100-250R lower on the high books and every drawdown is 1-4R smaller.
The ranking is largely preserved — `mode_atr_low` and `mode_union` were the
deepest books then and are the deepest now — but the *gap* narrowed: `atr_low`
was 28.88% in the old run and is 48.76% now, while `htf15_htffs` went 29.62% to
29.76%. **The `mode_*` books got materially worse relative to the field, not
better**, which strengthens rather than weakens their existing block.

## What this study does not settle

- **The p-value column is unchanged in shape but is not reproduced here.** It is
  per-book and lives in the registry pins and `_results.json`, both re-pinned on
  the corrected chain (`dd02cf1`). Read those, not this table, for significance.
- **One continuous timeline** — the whole point of the study — means these
  numbers are not comparable to a single-period backtest. Do not read
  `net` in this table as a per-year figure.
- **A drawdown as a percentage of the account is not the same as a drawdown a
  new deployer would experience.** For that see `ANY_START_WORST_CASE.md`, where
  the worst start date on `mode_atr_low` is 48.76% too — but on `champ_long` the
  worst start is 25.08% against a median start of 10.69%.

Nothing adopted. Shipping book unchanged.