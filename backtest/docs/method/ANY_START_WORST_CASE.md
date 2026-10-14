# ANY-START WORST CASE — what a deployer actually faces

**RE-RUN 2026-10-14 on the corrected chain (2,840 swings / 7,734 marks).**
The version this replaces was measured 2026-10-10, before the B1 arming fix
(`77711a6`), V13 (`88ecd00`) and the volatile-B1 / same-bar pivot work
(`5d6cab2`, `d71304f`).

Harnesses `exp_full_study.py` (per-trade series) then `exp_anystart.py`.
Artifact `_anystart.json`, 26 books.

---

## The flaw in the startup number

`exp_startup_yearly.py` reports startup drawdown from the beginning of the
record, 2021-01-01. For most books that is ~0 because the first trade is
profitable and the run happens to begin well.

**That is not a bound on what a deployer faces. It is one path's number.**

The peak-to-trough episode that shows as 29.76R for `htf15_htffs` happened over
months. Anyone who started inside it saw the whole thing. Anyone who started in
January 2021 saw nothing. Both are real and they are the same book.

So the question is not "what happened on day one of this particular backtest":

> **for EVERY possible start date, if money went in and was held for a year, what
> is the worst peak-to-trough I would have seen?**

## The answer

Every one of the ~950 possible start dates is evaluated over a 12-month window.

| book | worst DD | p10 | median | p90 | starts negative | worst net |
|---|---|---|---|---|---|---|
| `fsent_champ_long_mode_atr_low` | **48.76** | 13.16 | 17.37 | 43.74 | **2.2%** | **−19.96** |
| `fsent_champ_long_mode_union` | **47.61** | 15.04 | 19.51 | 47.61 | **2.1%** | **−15.65** |
| `fsent_champ_long_htf15_htffs` | 29.76 | 12.35 | 16.90 | 28.58 | 0.0% | 74.69 |
| `fsent_champ_trailhalf` | 29.38 | — | 13.73 | 29.38 | **1.2%** | **−8.96** |
| `fsent_champ_long_mcloff_htf15` | 28.38 | — | 11.59 | 28.38 | 0.0% | 24.73 |
| `fsent_champ_long_htf15` | 26.26 | — | 11.28 | 26.26 | 0.0% | 19.89 |
| `fsent_champ_long` | 25.08 | — | 10.69 | 25.08 | 0.0% | 4.51 |
| `fsent_champ_long_causalfloor` | 24.47 | — | 11.20 | 24.47 | 0.0% | 6.99 |
| `fsent_utcsat_long` | 23.81 | — | 11.20 | 23.81 | 0.0% | 10.39 |
| `fsent_champ_long_nohalt` | 23.30 | — | 11.05 | 23.30 | 0.0% | 10.09 |

## THREE THINGS THIS SAYS THAT THE STARTUP NUMBER DOES NOT

**1. The worst start date is roughly 2.4× the median start date.** For
`fsent_champ_long`: median start sees 10.69R of drawdown, worst start sees
25.08R. For `atr_low`: median 17.37R, worst 48.76R. Anyone planning around the
median is planning around the easy case.

**2. `fsent_champ_long` is the safest book to START, not the most profitable.**
It has the lowest worst-case drawdown of any multi book at 25.08R, and every one
of its ~950 possible start dates ends positive after 12 months. `htf15_htffs`
makes more money and its worst-case drawdown is higher.

**3. Four books have start dates that end NEGATIVE.** `atr_low` 2.2%,
`mode_union` 2.1%, `trailhalf` 1.2%, `utcsat_trailhalf` 0.7%. Small, but they
exist, and none of them would have been visible in the startup number.

## AGAINST THE OWNER'S 29R BUDGET

| book | worst-start DD | verdict |
|---|---|---|
| `fsent_champ_long` | 25.08R | **inside budget** |
| `fsent_champ_long_mcloff` | 23.30R | **inside budget** |
| `fsent_champ_long_htf15` | 26.26R | **inside budget** |
| `fsent_champ_long_htf15_htffs` | 29.76R | **at/over budget** |
| `fsent_champ_trailhalf` | 29.38R | **at/over budget** |
| `fsent_champ_long_mode_atr_low` | 48.76R | **well over** |
| `fsent_champ_long_mode_union` | 47.61R | **well over** |

**The two `mode` books are the clearest result in this document.** They were
blocked on drawdown against the owner's budget in the registry, and the any-start
measurement puts them at 48.76R and 47.61R — not 20% over, roughly 65% over.
They also have the most negative start dates in the set.

## What changed against the 2026-10-10 run

Same shape, smaller numbers across the board, because the corrected chain trades
less. The conclusion is unchanged and is now stronger: **the startup number is
the flawed measurement, and the budget should be checked against the any-start
number, not the calendar's opening day.**

Nothing adopted. Shipping book unchanged.