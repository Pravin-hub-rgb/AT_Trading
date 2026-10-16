# Three candidates, every number the repo keeps

**IS** = 2023-01-01..2026-09-13. **OOS** = 2021-01-01..2022-12-31 (separate file).
**Forward** = after 2026-09-13 10:03, never searched. Tiny sample - it is a
tie-breaker, not a verdict.

## Size and shape

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| class (0=multi, 1=serial) | 0 | 0 | 0 | 0 | 0 |
| positions held | 0 | 0 | 0 | 0 | 0 |
| trades | 837 | 636 | 1152 | 1187 | 1142 |
| peak concurrent | 6 | 7 | 9 | 8 | 8 |
| mean concurrent | 0.69 | 1.05 | 0.89 | 0.91 | 0.86 |

## IS era (where the books were chosen)

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| trades | 535 | 412 | 756 | 762 | 753 |
| net R | +539.77 | +639.84 | +765.86 | +770.53 | +757.99 |
| R per trade | +1.0089 | +1.5530 | +1.0130 | +1.0112 | +1.0066 |

## OOS era (2021-22, the crash period)

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| trades | 302 | 224 | 396 | 425 | 389 |
| net R | +270.17 | +328.54 | +346.07 | +339.08 | +313.35 |
| R per trade | +0.8946 | +1.4667 | +0.8739 | +0.7978 | +0.8055 |

## Both eras

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| net R | +809.94 | +968.38 | +1111.93 | +1109.61 | +1071.34 |
| R per trade | +0.9677 | +1.5226 | +0.9652 | +0.9348 | +0.9381 |
| win rate | 41.2 | 39.3 | 39.7 | 38.7 | 39.1 |
| profit factor | 3.106 | 3.197 | 2.974 | 2.917 | 2.934 |
| payoff ratio | 3.11 | 3.20 | 2.97 | 2.92 | 2.93 |
| avg win R | +3.462 | +5.636 | +3.666 | +3.679 | +3.636 |
| avg loss R | -0.782 | -1.142 | -0.811 | -0.795 | -0.797 |
| t-stat | 7.28 | 6.85 | 7.66 | 7.57 | 7.44 |
| retention OOS/IS | 50 | 51 | 45 | 44 | 41 |

## Risk

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| max drawdown R | 28.38 | 22.81 | 29.76 | 20.02 | 22.45 |
| drawdown % of peak | 3.50 | 2.35 | 2.66 | 1.80 | 2.09 |
| net / drawdown | 28.5 | 42.5 | 37.4 | 55.4 | 47.7 |
| days under water | 82 | 35 | 124 | 79 | 123 |
| recovery days | 140 | 39 | 9 | 50 | 9 |
| p90 recovery days | 12 | 19 | 14 | 15 | 14 |
| still underwater? | 1 | 0 | 0 | 0 | 0 |
| worst 3 months | -2.37 | -6.82 | -8.42 | -8.38 | -8.42 |
| worst 12 months | -4.67 | -4.33 | -2.48 | -2.48 | -2.48 |

## How dependent on the best few trades

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| top 10% of trades carry | 73 | 70 | 82 | 84 | 83 |
| net after removing best 10 | +615.22 | +605.20 | +758.27 | +745.97 | +718.53 |
| survives that cut? | 1 | 1 | 1 | 1 | 1 |

## Consistency

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| negative half-years | 0 | 0 | 1 | 1 | 1 |
| half-years tested | 12 | 12 | 12 | 12 | 12 |
| 50-trade windows positive | 96 | 98 | 90 | 90 | 89 |
| p value, OOS | 0.0112 | 0.3824 | 0.2319 | 0.3794 | 0.3927 |
| significant at 5%? | 1 | 0 | 0 | 0 | 0 |

## Capital actually deployed

| metric | 107 mcloff_htf15 | 110 tskip6 | 109 htf15_htffs | 108 htfesmcl4 | 106 htffs |
|---|---|---|---|---|---|
| DD per peak-capital R | 1.84 | 2.13 | 1.64 | 1.88 | 1.84 |
| DD per mean-concurrent R | 15.9 | 14.1 | 16.6 | 16.6 | 17.2 |
| net per mean-concurrent R | 389.0 | 311.6 | 390.2 | 373.3 | 366.3 |

## Forward window - after the hard cutoff, never searched

| book | trades | net R | win rate | profit factor | max DD | months positive |
|---|---:|---:|---:|---:|---:|---:|
| `107 mcloff_htf15` | 8 | +1.72 | 37.5% | 1.78 | 3.8R | 1/1 |
| `110 tskip6` | 3 | -3.61 | 0.0% | 0.00 | 3.6R | 0/1 |
| `109 htf15_htffs` | 13 | +2.04 | 38.5% | 2.19 | 3.0R | 2/2 |
| `108 htfesmcl4` | 15 | +3.27 | 33.3% | 2.12 | 4.1R | 2/2 |
| `106 htffs` | 13 | +2.04 | 38.5% | 2.19 | 3.0R | 2/2 |

Sample is 3 to 13 trades. It cannot settle anything on its own. It is
listed because it is the only data nobody has searched.

---

Legend for risk band: 0 = no band recorded or recovered, 1 = serious,
major or unresolved.

`payoff ratio` is derived from PF and win rate and is approximate; the
authoritative pair is `avg win R` and `avg loss R` above it.