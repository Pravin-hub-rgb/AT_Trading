# Three candidates, every number the repo keeps

**IS** = 2023-01-01..2026-09-13. **OOS** = 2021-01-01..2022-12-31 (separate file).
**Forward** = after 2026-09-13 10:03, never searched. Tiny sample - it is a
tie-breaker, not a verdict.

## Size and shape

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| class (0=multi, 1=serial) | 0 | 0 | 0 |
| positions held | 0 | 0 | 0 |
| trades | 1142 | 837 | 778 |
| peak concurrent | 8 | 6 | not measured |
| mean concurrent | 0.86 | 0.69 | not measured |

## IS era (where the books were chosen)

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| trades | 753 | 535 | 497 |
| net R | +757.99 | +539.77 | +466.92 |
| R per trade | +1.0066 | +1.0089 | +0.9395 |

## OOS era (2021-22, the crash period)

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| trades | 389 | 302 | 281 |
| net R | +313.35 | +270.17 | +215.32 |
| R per trade | +0.8055 | +0.8946 | +0.7663 |

## Both eras

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| net R | +1071.34 | +809.94 | +682.24 |
| R per trade | +0.9381 | +0.9677 | +0.8769 |
| win rate | 39.1 | 41.2 | 39.5 |
| profit factor | 2.934 | 3.106 | 2.813 |
| payoff ratio | 2.93 | 3.11 | 2.81 |
| avg win R | +3.636 | +3.462 | +3.448 |
| avg loss R | -0.797 | -0.782 | -0.799 |
| t-stat | 7.44 | 7.28 | 6.37 |
| retention OOS/IS | 41 | 50 | 46 |

## Risk

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| max drawdown R | 22.45 | 28.38 | 25.08 |
| drawdown % of peak | 2.09 | 3.50 | 3.66 |
| net / drawdown | 47.7 | 28.5 | 27.2 |
| days under water | 123 | 82 | 91 |
| recovery days | 9 | 140 | 6 |
| p90 recovery days | 14 | 12 | 21 |
| still underwater? | 0 | 1 | 0 |
| worst 3 months | -8.42 | -2.37 | -2.57 |
| worst 12 months | -2.48 | -4.67 | -4.67 |

## How dependent on the best few trades

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| top 10% of trades carry | 83 | 73 | 80 |
| net after removing best 10 | +718.53 | +615.22 | +501.10 |
| survives that cut? | 1 | 1 | 1 |

## Consistency

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| negative half-years | 1 | 0 | 0 |
| half-years tested | 12 | 12 | 12 |
| 50-trade windows positive | 89 | 96 | 92 |
| p value, OOS | 0.3927 | 0.0112 | 1.0000 |
| significant at 5%? | 0 | 1 | 0 |

## Capital actually deployed

| metric | htffs | mcloff_htf15 | champ_long |
|---|---|---|---|
| DD per peak-capital R | 1.84 | 1.84 | not measured |
| DD per mean-concurrent R | 17.2 | 15.9 | not measured |
| net per mean-concurrent R | 366.3 | 389.0 | not measured |

## Forward window - after the hard cutoff, never searched

| book | trades | net R | win rate | profit factor | max DD | months positive |
|---|---:|---:|---:|---:|---:|---:|
| `htffs` | 13 | +2.04 | 38.5% | 2.19 | 3.0R | 2/2 |
| `mcloff_htf15` | 8 | +1.72 | 37.5% | 1.78 | 3.8R | 1/1 |
| `champ_long` | 8 | +1.72 | 37.5% | 1.78 | 3.8R | 1/1 |

Sample is 3 to 13 trades. It cannot settle anything on its own. It is
listed because it is the only data nobody has searched.

---

Legend for risk band: 0 = no band recorded or recovered, 1 = serious,
major or unresolved.

`payoff ratio` is derived from PF and win rate and is approximate; the
authoritative pair is `avg win R` and `avg loss R` above it.