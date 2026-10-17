# Position sizing, ruin and recovery - stated properly

2026-10-16. Replaces the ruin and recovery claims from
`MONTE_CARLO_SURVIVABILITY.md`,
both of which were reported as sound numbers and were not.

## What was wrong

| claim | why it was not sound |
|---|---|
| "0% ruin paths" | the harness counted paths with net R <= 0 and paths with drawdown over fixed R bands. Neither is ruin. A drawdown in R has **no meaning until position sizing is stated** - 50R is a 50% equity loss at 1% risk and a 250% loss at 5%. Zero of an undefined event is zero of nothing. |
| recovery durations | the earlier run measured an *underwater stretch*, not a peak-to-recovery. A stretch that has not recovered when the sample ends is **censored**, and reporting it as a completed duration overstates patience by the unfinished tail. That is why the resampled p90 came out near the full length of the dataset. |

## The sizing model

Fractional and compounding, because it is the only kind under which ruin
is a real event:

```
equity *= 1 + (equity * risk_pct/100 * R)
```

Swept at 0.5, 1, 2, 3, 5 percent of equity per trade. Ruin is equity at or below
**50% of starting equity** - the standard half-way wipe.

## Overlap, handled by construction

Both books are unlimited-concurrency, so resampling at TRADE level is
wrong for them - it draws each trade as though it happened alone. This
resamples **DAYS**, not trades. Every trade is booked into the day it
exited, so a day on which several positions lost together stays such a
day. Concurrency is preserved by the aggregation rather than assumed.

Booked on exit rather than entry, deliberately: P&L is not credited
until realised, so the equity path is bumpier than mark-to-market and
these drawdowns are an **upper bound** on what a marked-to-market book
would show. It is also what the account experiences.

## How much concurrency actually existed


| book | era | trades | trading days | max concurrent | avg concurrent | % time at 1-or-fewer |
|---|---|---:|---:|---:|---:|---:|
| 107 | IS | 525 | 338 | 10 | 1.17 | 74% |
| 107 | OOS | 295 | 196 | 6 | 0.99 | 79% |
| 110 | IS | 395 | 287 | 10 | 1.68 | 59% |
| 110 | OOS | 216 | 171 | 7 | 1.55 | 60% |

If the average concurrency is well above one, trade-level resampling
would have understated this badly, which is why it is not used here.

---

## 107 `fsent_champ_long_mcloff_htf15`

### IS — 525 trades over 338 days

**Observed path, by position size**

| risk/trade | final equity | max DD (equity) | ruin | completed recoveries | censored at end |
|---|---:|---:|---|---|---|
| 0.5% | x11.220 | 13.2% | no | 44 | 6 days, from day 20691 |
| 1.0% | x84.405 | 24.6% | no | 43 | 6 days, from day 20691 |
| 2.0% | x2207.372 | 43.4% | no | 40 | 6 days, from day 20691 |
| 3.0% | x28344.612 | 57.7% | no | 38 | 6 days, from day 20691 |
| 5.0% | x1129038.923 | 76.6% | no | 35 | 6 days, from day 20691 |

**Simulated, 5000 day-blocks** — ruin rate and drawdown, by position size

Block of 10 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 9.7% | 16.1% | 20.0% | 30.8% |
| 1.0% | **0.00%** | 18.6% | 29.7% | 36.3% | 52.5% |
| 2.0% | **0.42%** | 34.1% | 51.1% | 59.8% | 78.2% |
| 3.0% | **2.28%** | 47.1% | 66.2% | 74.8% | 90.3% |
| 5.0% | **12.10%** | 64.8% | 84.3% | 90.6% | 98.1% |

Block of 20 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 10.3% | 17.3% | 21.2% | 29.9% |
| 1.0% | **0.00%** | 19.6% | 31.7% | 38.3% | 51.0% |
| 2.0% | **0.78%** | 35.6% | 53.3% | 61.8% | 76.3% |
| 3.0% | **2.98%** | 48.5% | 68.2% | 76.5% | 88.8% |
| 5.0% | **10.26%** | 66.4% | 85.4% | 91.5% | 97.6% |

Block of 40 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 10.3% | 13.2% | 13.2% | 13.2% |
| 1.0% | **0.00%** | 19.6% | 24.6% | 24.6% | 24.6% |
| 2.0% | **0.00%** | 35.6% | 43.4% | 43.4% | 43.4% |
| 3.0% | **0.00%** | 48.5% | 57.7% | 57.7% | 57.7% |
| 5.0% | **0.00%** | 67.4% | 76.6% | 76.6% | 76.6% |

**Recovery, block of 20 days, at 1.0% risk/trade**

| | completed recovery (days) | censored at sample end (days) | paths with any completed recovery |
|---|---:|---:|---:|
| p50 | 11 | 29 | 3630% |
| p90 | 224 | 96 | |
| max | 1229 | 948 | |

Completed recoveries only. The censored column is the stretch still
open when the sample ends - it is **not** patience, and folding it
in is what made the earlier figure unreadable.

### OOS — 295 trades over 196 days

**Observed path, by position size**

| risk/trade | final equity | max DD (equity) | ruin | completed recoveries | censored at end |
|---|---:|---:|---|---|---|
| 0.5% | x3.627 | 5.4% | no | 25 | 14 days, from day 19344 |
| 1.0% | x11.531 | 10.6% | no | 25 | 14 days, from day 19344 |
| 2.0% | x85.834 | 20.3% | no | 25 | 14 days, from day 19344 |
| 3.0% | x466.213 | 29.2% | no | 25 | 14 days, from day 19344 |
| 5.0% | x6922.511 | 44.7% | no | 25 | 14 days, from day 19344 |

**Simulated, 5000 day-blocks** — ruin rate and drawdown, by position size

Block of 10 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 5.1% | 7.8% | 9.6% | 14.8% |
| 1.0% | **0.00%** | 10.0% | 15.1% | 18.3% | 27.5% |
| 2.0% | **0.00%** | 19.1% | 28.2% | 33.7% | 47.7% |
| 3.0% | **0.00%** | 27.6% | 39.6% | 46.6% | 62.5% |
| 5.0% | **1.46%** | 42.2% | 57.9% | 65.9% | 81.1% |

Block of 20 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 5.1% | 6.5% | 6.5% | 6.5% |
| 1.0% | **0.00%** | 10.0% | 12.7% | 12.7% | 12.7% |
| 2.0% | **0.00%** | 19.1% | 24.1% | 24.1% | 24.1% |
| 3.0% | **0.00%** | 27.5% | 34.3% | 34.3% | 34.3% |
| 5.0% | **0.00%** | 42.0% | 51.4% | 51.4% | 51.4% |

Block of 40 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 4.5% | 6.5% | 6.5% | 6.5% |
| 1.0% | **0.00%** | 8.9% | 12.7% | 12.7% | 12.7% |
| 2.0% | **0.00%** | 17.2% | 24.1% | 24.1% | 24.1% |
| 3.0% | **0.00%** | 25.0% | 34.3% | 34.3% | 34.3% |
| 5.0% | **0.00%** | 39.0% | 51.4% | 51.4% | 51.4% |

**Recovery, block of 20 days, at 1.0% risk/trade**

| | completed recovery (days) | censored at sample end (days) | paths with any completed recovery |
|---|---:|---:|---:|
| p50 | 7 | 3 | 2572% |
| p90 | 86 | 21 | |
| max | 586 | 348 | |

Completed recoveries only. The censored column is the stretch still
open when the sample ends - it is **not** patience, and folding it
in is what made the earlier figure unreadable.

---

## 110 `fsent_champ_long_htf15_tskip6`

### IS — 395 trades over 287 days

**Observed path, by position size**

| risk/trade | final equity | max DD (equity) | ruin | completed recoveries | censored at end |
|---|---:|---:|---|---|---|
| 0.5% | x18.155 | 10.9% | no | 34 | 8 days, from day 20695 |
| 1.0% | x203.585 | 20.7% | no | 34 | 8 days, from day 20695 |
| 2.0% | x9916.195 | 37.4% | no | 34 | 8 days, from day 20695 |
| 3.0% | x201598.554 | 50.8% | no | 34 | 8 days, from day 20695 |
| 5.0% | x14795881.557 | 70.2% | no | 33 | 8 days, from day 20695 |

**Simulated, 5000 day-blocks** — ruin rate and drawdown, by position size

Block of 10 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 11.5% | 18.8% | 22.8% | 33.8% |
| 1.0% | **0.00%** | 21.8% | 34.3% | 40.6% | 56.6% |
| 2.0% | **0.98%** | 39.3% | 57.0% | 65.2% | 80.4% |
| 3.0% | **4.50%** | 52.4% | 72.0% | 79.9% | 89.9% |
| 5.0% | **15.90%** | 70.2% | 88.2% | 93.6% | 98.2% |

Block of 20 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 10.9% | 12.6% | 12.6% | 13.5% |
| 1.0% | **0.00%** | 20.6% | 23.7% | 23.7% | 26.0% |
| 2.0% | **0.00%** | 37.3% | 41.9% | 42.3% | 47.7% |
| 3.0% | **0.00%** | 50.6% | 56.0% | 58.2% | 64.5% |
| 5.0% | **17.02%** | 68.8% | 75.1% | 78.9% | 85.5% |

Block of 40 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 10.9% | 12.3% | 12.3% | 12.3% |
| 1.0% | **0.00%** | 20.6% | 23.2% | 23.2% | 23.2% |
| 2.0% | **0.00%** | 37.3% | 41.2% | 41.2% | 41.2% |
| 3.0% | **0.00%** | 50.6% | 55.2% | 55.2% | 55.2% |
| 5.0% | **14.50%** | 69.8% | 74.3% | 74.3% | 74.3% |

**Recovery, block of 20 days, at 1.0% risk/trade**

| | completed recovery (days) | censored at sample end (days) | paths with any completed recovery |
|---|---:|---:|---:|
| p50 | 14 | 0 | 2809% |
| p90 | 293 | 77 | |
| max | 1209 | 727 | |

Completed recoveries only. The censored column is the stretch still
open when the sample ends - it is **not** patience, and folding it
in is what made the earlier figure unreadable.

### OOS — 216 trades over 171 days

**Observed path, by position size**

| risk/trade | final equity | max DD (equity) | ruin | completed recoveries | censored at end |
|---|---:|---:|---|---|---|
| 0.5% | x4.561 | 7.7% | no | 20 | 39 days, from day 19315 |
| 1.0% | x16.265 | 14.9% | no | 20 | 39 days, from day 19315 |
| 2.0% | x128.416 | 27.8% | no | 19 | 39 days, from day 19315 |
| 3.0% | x658.629 | 38.9% | no | 19 | 39 days, from day 19315 |
| 5.0% | x7418.636 | 56.4% | no | 19 | 39 days, from day 19315 |

**Simulated, 5000 day-blocks** — ruin rate and drawdown, by position size

Block of 10 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 7.4% | 11.4% | 14.0% | 25.6% |
| 1.0% | **0.00%** | 14.5% | 21.7% | 26.2% | 45.1% |
| 2.0% | **0.04%** | 27.3% | 39.2% | 46.3% | 66.4% |
| 3.0% | **0.38%** | 38.5% | 53.3% | 60.6% | 81.7% |
| 5.0% | **4.82%** | 56.3% | 72.4% | 80.1% | 95.1% |

Block of 20 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 7.4% | 9.4% | 9.4% | 9.4% |
| 1.0% | **0.00%** | 14.3% | 17.9% | 17.9% | 17.9% |
| 2.0% | **0.00%** | 26.8% | 32.8% | 32.8% | 32.8% |
| 3.0% | **0.00%** | 37.6% | 45.1% | 45.7% | 46.8% |
| 5.0% | **0.00%** | 55.2% | 63.8% | 66.0% | 70.0% |

Block of 40 trading days:

| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |
|---|---:|---:|---:|---:|---:|
| 0.5% | **0.00%** | 7.7% | 7.7% | 7.7% | 7.7% |
| 1.0% | **0.00%** | 14.9% | 14.9% | 14.9% | 14.9% |
| 2.0% | **0.00%** | 27.8% | 27.8% | 27.8% | 27.8% |
| 3.0% | **0.00%** | 38.9% | 38.9% | 38.9% | 38.9% |
| 5.0% | **0.00%** | 56.4% | 56.4% | 56.4% | 56.4% |

**Recovery, block of 20 days, at 1.0% risk/trade**

| | completed recovery (days) | censored at sample end (days) | paths with any completed recovery |
|---|---:|---:|---:|
| p50 | 14 | 0 | 1719% |
| p90 | 112 | 23 | |
| max | 581 | 415 | |

Completed recoveries only. The censored column is the stretch still
open when the sample ends - it is **not** patience, and folding it
in is what made the earlier figure unreadable.

---

## What this establishes, and what it does not

| claim | status |
|---|---|
| ruin happens before the sample ends on the observed path | answered per position size above |
| a percentage of paths ruin | answered, and it is a function of size rather than a property of the book |
| how long a recovery takes | answered for completed recoveries only |
| the block size decides the drawdown tail | unchanged from the previous pass, and it is why no single kill-line is quoted |
| 52 books were not tested | these two are **shortlisted candidates, not proven best** |
| 2021-22 is untouched out-of-sample | it is **not** - it has been used for filtering throughout |

Ruin is now defined, so the ruin numbers mean something. They are still
conditional on the resampling assumptions, on exit-day booking, and on
the two candidates being the ones we chose to measure.
