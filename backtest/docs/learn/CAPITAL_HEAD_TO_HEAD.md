# 107 vs 110 under identical capital and identical risk constraints

2026-10-16. Every comparison so far has been in units of R, which is free
of capital and therefore free of the only question that matters to an owner:
how much money does each book need, and how much can I risk per trade on it.

## The question, in a form that can be answered

Live sizing is fixed against **initial** capital, not compounded, so

    equity_t / C = 1 + k * cumulative_R_t        k = risk per trade / C

and the account is ruined once `1 + k*cumulative_R <= RUIN_FRAC`, i.e. once
`k * |trough| > (1 - RUIN_FRAC)`. With ruin at 50 percent, the largest risk
that survives a path whose worst cumulative-R trough is T is simply

    k_safe = 0.5 / |T|

Taking that at a **percentile of the trough distribution** gives a confidence
statement that the extreme tail cannot hijack. This is the headline number,
and it is directly comparable between the two books in a way net R never was.

## Why not just count ruin

The first version counted ruined paths at each risk level and it was
meaningless. A block bootstrap chains together 20-trade blocks that never
occurred in that order, so its far tail reaches troughs of 100R and more
against an observed maximum drawdown of 28R. Counting ruin on that tail
measures the resampler's imagination rather than the book, and it made every
book look unsafe at every usable size. The distribution of the trough is the
robust statistic; the extreme of it is not.

Simulation is a moving-block bootstrap on TRADES (block 20 trades, N=5000),
with the daily portfolio series rebuilt afterwards, so trades that exit on
the same day are still summed into that day. Both books average more than
one position open at a time and peak at 10, so resampling without that
aggregation would understate concurrency.

---

## IS era

| book | loss cap | safe risk p50 | p90 | **p95** | p99 | trough R p50 | p95 | p99 | worst | observed | DD p95 at 1% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 107 | 0 | 10.0 | 1.4 | **1.06** | 0.81 | -0R | 47R | 62R | 105R | 28R | 49.5% |
| 107 | 1 | 2.16 | 0.98 | **0.83** | 0.64 | 23R | 60R | 79R | 120R | 30R | 63.7% |
| 107 | 3 | 10.0 | 1.23 | **0.98** | 0.72 | 5R | 51R | 69R | 113R | 26R | 56.3% |
| 110 | 0 | 10.0 | 1.32 | **1.12** | 0.82 | -0R | 45R | 61R | 102R | 28R | 46.6% |
| 110 | 1 | 10.0 | 1.54 | **1.54** | 1.02 | -0R | 33R | 49R | 96R | 29R | 41.2% |
| 110 | 3 | 10.0 | 1.28 | **1.22** | 0.83 | -0R | 41R | 60R | 117R | 23R | 41.9% |

Safe risk is capped at 10%% for display. A median trough of zero means half the
orderings never drew below their running peak at all, which makes the
median path effectively unbounded.

---

## OOS era

| book | loss cap | safe risk p50 | p90 | **p95** | p99 | trough R p50 | p95 | p99 | worst | observed | DD p95 at 1% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 107 | 0 | 10.0 | 10.0 | **10.0** | 10.0 | -0R | 2R | 3R | 25R | 11R | 17.9% |
| 107 | 1 | 10.0 | 6.75 | **4.5** | 3.38 | -0R | 11R | 15R | 27R | 10R | 17.0% |
| 107 | 3 | 10.0 | 5.22 | **4.99** | 2.61 | -0R | 10R | 19R | 50R | 10R | 21.0% |
| 110 | 0 | 10.0 | 4.06 | **3.45** | 2.3 | 5R | 14R | 22R | 36R | 18R | 20.7% |
| 110 | 1 | 8.74 | 3.42 | **3.42** | 2.28 | 6R | 15R | 22R | 37R | 13R | 20.8% |
| 110 | 3 | 10.0 | 4.15 | **3.67** | 2.75 | 4R | 14R | 18R | 35R | 16R | 18.8% |

Safe risk is capped at 10%% for display. A median trough of zero means half the
orderings never drew below their running peak at all, which makes the
median path effectively unbounded.

---

## Full trough distributions

| book | cap | era | p50 | p90 | p95 | p99 | worst | observed |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 107 | 0 | IS | -0R | 36R | 47R | 62R | 105R | 28R |
| 107 | 1 | IS | 23R | 51R | 60R | 79R | 120R | 30R |
| 107 | 3 | IS | 5R | 41R | 51R | 69R | 113R | 26R |
| 107 | 0 | OOS | -0R | -0R | 2R | 3R | 25R | 11R |
| 107 | 1 | OOS | -0R | 7R | 11R | 15R | 27R | 10R |
| 107 | 3 | OOS | -0R | 10R | 10R | 19R | 50R | 10R |
| 110 | 0 | IS | -0R | 38R | 45R | 61R | 102R | 28R |
| 110 | 1 | IS | -0R | 33R | 33R | 49R | 96R | 29R |
| 110 | 3 | IS | -0R | 39R | 41R | 60R | 117R | 23R |
| 110 | 0 | OOS | 5R | 12R | 14R | 22R | 36R | 18R |
| 110 | 1 | OOS | 6R | 15R | 15R | 22R | 37R | 13R |
| 110 | 3 | OOS | 4R | 12R | 14R | 18R | 35R | 16R |

---

## What this settles, and what it does not

| claim | status |
|---|---|
| a safe risk per trade exists for both books | answered |
| the two books differ on it | answered, see the p95 column |
| the loss cap changes it | answered across cap 0 / 1 / 3 |
| these are the best of 52 books | **no** - shortlisted candidates only |
| 2021-22 is untouched out-of-sample | **no** - used for filtering throughout |
| the live fill matches the backtest fill | **no** - exp_stop_slip_bps measures the gap, the bot has never traded |
| these troughs will occur live | **no** - they are resamplings of one known trade set |

Every figure is conditional on the resampling assumptions, on the block
length, and on these two being the books that were chosen to measure. None
of it speaks to whether the market will take a different route than this
history did, which is the one thing Monte Carlo on known trades cannot do.
