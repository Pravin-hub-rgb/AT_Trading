# STARTUP RISK, CALENDAR YEARS AND ROLLING-WEIGHTED RANKING

**RE-RUN 2026-10-14 on the corrected chain (2,840 swings / 7,734 marks).**
The version this replaces was measured 2026-10-10, before the B1 arming fix
(`77711a6`), V13 (`88ecd00`) and the volatile-B1 / same-bar pivot work
(`5d6cab2`, `d71304f`).

Harness `exp_startup_yearly.py`, artifact `_startup_yearly.json`, 33 books.
Figures are NET R after costs (55bp fee/side, 2×, 5bp entry slippage, 1bp exit).

---

## 1. Startup — how much does it cost to begin at the top of the record?

The record starts 2021-01-01. For most books the first trade is profitable, so
startup drawdown is ~0 and `trades_to_first_profit` is 1.

**That is a property of the calendar, not of the book.** See
`ANY_START_WORST_CASE.md` for the number that actually bounds deployment.

| book | net | maxDD (R) | maxDD % @1% | 1st profit | worst first 50 | worst first 100 |
|---|---|---|---|---|---|---|
| `fsent_champ_trailhalf` | 659.1 | 45.15 | **29.38%** | 1 | 78.09 | 160.54 |
| `fsent_utcsat_trailhalf` | 661.1 | 34.61 | 23.49% | 1 | 78.09 | 160.54 |
| `fsent_sig_half_crossed` | 218.8 | 16.15 | 10.75% | 1 | 65.34 | 141.40 |
| `fsent_sig_trail_delay1` | 288.1 | 24.08 | 16.05% | 1 | 79.44 | 132.04 |
| `fsent_champ_long_htf15` | 760.1 | 26.26 | 26.26% | 1 | 52.91 | 105.71 |
| `fsent_champ_long_htf15_htffs` | 1111.9 | 29.76 | 29.76% | **2** | 28.74 | 102.06 |
| `fsent_champ_long` | 682.2 | 25.08 | 25.08% | 1 | 52.32 | 74.87 |
| `fsent_champ_long_mcloff` | 717.4 | 23.30 | 23.30% | 1 | 53.33 | 77.54 |
| `fsent_champ_long_causalfloor` | 683.0 | 24.47 | 24.47% | 1 | 50.11 | 97.95 |
| `fsent_sig_multi` | 555.7 | 13.43 | 13.43% | 1 | 42.47 | 100.46 |

**The owner's drawdown budget is 29R.** At 1% risk that is 29%, and on this
ranking **two books sit past it** — `fsent_champ_trailhalf` at 29.38% and
`fsent_champ_long_htf15_htffs` at 29.76%. `fsent_champ_long` at 25.08% is inside
it.

## 2. Calendar years — is profit actually spread through time?

| book | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | negative halves | negative years |
|---|---|---|---|---|---|---|---|---|
| `fsent_champ_long` | 116.85 | 98.47 | 154.41 | 88.51 | 91.02 | 132.97 | none | none |
| `fsent_champ_long_htf15` | 152.84 | 101.97 | 172.43 | 91.43 | 109.87 | 131.51 | none | none |
| `fsent_champ_long_mcloff` | 120.25 | 93.02 | 161.68 | 95.40 | 97.20 | 149.84 | none | none |
| `fsent_champ_long_htf15_htffs` | 151.39 | 194.69 | 314.29 | 201.37 | 134.35 | 115.84 | **2022H2** | none |

The doc's shape is the good one — `2023 +154 / 2024 +88 / 2025 +91 / 2026 +133`
is money arriving throughout the dataset, not one good year carrying the book.

## 3. Rolling windows

| book | worst 10 | worst 20 | worst 30 | worst 50 | worst 100 |
|---|---|---|---|---|---|
| `fsent_champ_long` | −12.14 | −19.43 | −23.06 | −13.66 | see json |
| `fsent_champ_long_htf15` | −11.75 | −19.92 | −24.91 | **−8.81** | see json |
| `fsent_champ_long_mcloff` | −10.65 | −18.07 | −20.60 | −12.51 | see json |
| `fsent_champ_long_htf15_htffs` | −10.39 | −13.56 | −15.89 | −20.53 | see json |

`htf15` has the shallowest worst-50 of the four. `htf15_htffs` has the shallowest
worst-20 but the deepest worst-50 — the trade-off is real, not a wash.

## 4. Tail dependence

| book | top-10% contributes | survives removing top 10% |
|---|---|---|
| `fsent_champ_long` | 110.9% | −74.68 |
| `fsent_champ_long_htf15` | **103.4%** | **−26.17** |
| `fsent_champ_long_mcloff` | 109.4% | −67.77 |
| `fsent_champ_long_htf15_htffs` | 108.6% | −95.15 |

**Every book in the table is tail-dependent** — top 10% contributes more than
100% of net in all four, so deleting the tail leaves a loss. Per the framework
this is a warning zone, not a failure, and it is normal for positive-skew trend
following.

**`fsent_champ_long_htf15` is the least tail-dependent of the four on both
measures** — the lowest top-10% contribution and the smallest loss when the tail
is deleted. That is the same conclusion the optimal-book study reaches from the
retention side, reached independently.

---

## What changed against the 2026-10-10 run

Every net is lower, by 100-250R on the high books. That is the marking fix
propagating: fewer swings, fewer entries, and the ones that remain are a
different set.

**The conclusion of the old run — that the startup drawdown number is the flaw,
not the book — still holds.** Startup DD is ~0 for most books because the record
happens to begin well, not because the book is safe to start at any date.

**Nothing here adopts anything.** Shipping book unchanged.