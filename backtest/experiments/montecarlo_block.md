# Monte Carlo done properly — survivability of 107 and 110

2026-10-16. Technique 4 from
`4 backtesting techniques behind winning strategies.md`,
run as the research standard rather than the textbook illustration.

## Why this was redone

The first pass shuffled the trade list 2000 times. That is the weakest
of three ways to do this:

| run | method |
|---|---|
| first pass | `rng.shuffle(rs)` — permutation, N=2000 |
| standard | `rng.sample(rs, n)` — resample **with replacement**, N=10000 |
| stricter still | **moving-block bootstrap**, block=20 |

Both differences push the tail the same way. A permutation reuses every
trade exactly once, so a losing streak cannot be worse than the one
history happened to contain. A bootstrap can draw the same bad run three
times. And a block bootstrap keeps consecutive trades together — losing
streaks are the mechanism that *makes* drawdown, and an i.i.d. shuffle
dissolves them.

`backtest/tests/exp_montecarlo_dd.py` already implemented both correctly
and said so in its own comment. It had been run on `baseline`,
`champion`, `utcsat` and `age10` — all retired — on 2026-09-25, before
the causal-stop fix. So the strict version had never run on a live
candidate. This runs it on both, reusing that harness's own `sim_metrics`
and `run_block` verbatim so the numbers are comparable with its prior art.

N=10000 per method, block=20, seed=20261016.

---

## 107 `fsent_champ_long_mcloff_htf15`

### IS — 525 trades, observed DD 28.38R, observed streak 22

| metric | i.i.d. bootstrap | moving-block B20 |
|---|---:|---:|
| DD p50 | 12.6 | 22.3 |
| DD p95 | 19.1 | 38.9 |
| DD p99 | 22.9 | 49.5 |
| DD worst | 33.6 | 74.1 |
| streak p99 | 18 | 31 |
| streak worst | 29 | 52 |
| underwater worst (trades) | 117 | 334 |
| observed DD sits at percentile | 99.9 | 77.1 |
| paths ending flat or worse | 0.00% | 0.00% |

**Drawdown exceeded, out of 10000 paths**

| over | i.i.d. | block |
|---:|---:|---:|
| 10R | 87.53% | 99.74% |
| 20R | 3.34% | 63.10% |
| 25R | 0.39% | 35.82% |
| 35R | 0.00% | 8.67% |
| 50R | 0.00% | 0.92% |
| 75R | 0.00% | 0.00% |
| 100R | 0.00% | 0.00% |

Worst path inflates the observed drawdown by **1.2x under i.i.d.** and **2.6x under the block bootstrap**.

### OOS — 295 trades, observed DD 11.05R, observed streak 8

| metric | i.i.d. bootstrap | moving-block B20 |
|---|---:|---:|
| DD p50 | 9.7 | 11.7 |
| DD p95 | 14.8 | 17.3 |
| DD p99 | 18.1 | 21.1 |
| DD worst | 31.0 | 30.4 |
| streak p99 | 16 | 12 |
| streak worst | 25 | 15 |
| underwater worst (trades) | 102 | 126 |
| observed DD sits at percentile | 70.3 | 40.0 |
| paths ending flat or worse | 0.00% | 0.00% |

**Drawdown exceeded, out of 10000 paths**

| over | i.i.d. | block |
|---:|---:|---:|
| 10R | 44.78% | 77.51% |
| 20R | 0.35% | 1.62% |
| 25R | 0.03% | 0.17% |
| 35R | 0.00% | 0.00% |
| 50R | 0.00% | 0.00% |
| 75R | 0.00% | 0.00% |
| 100R | 0.00% | 0.00% |

Worst path inflates the observed drawdown by **2.8x under i.i.d.** and **2.8x under the block bootstrap**.

---

## 110 `fsent_champ_long_htf15_tskip6`

### IS — 395 trades, observed DD 23.93R, observed streak 13

| metric | i.i.d. bootstrap | moving-block B20 |
|---|---:|---:|
| DD p50 | 15.2 | 22.2 |
| DD p95 | 23.1 | 37.2 |
| DD p99 | 27.9 | 47.6 |
| DD worst | 53.7 | 73.7 |
| streak p99 | 17 | 21 |
| streak worst | 29 | 26 |
| underwater worst (trades) | 119 | 253 |
| observed DD sits at percentile | 96.1 | 60.4 |
| paths ending flat or worse | 0.00% | 0.00% |

**Drawdown exceeded, out of 10000 paths**

| over | i.i.d. | block |
|---:|---:|---:|
| 10R | 98.53% | 99.96% |
| 20R | 13.42% | 63.69% |
| 25R | 2.68% | 33.53% |
| 35R | 0.15% | 6.97% |
| 50R | 0.01% | 0.64% |
| 75R | 0.00% | 0.00% |
| 100R | 0.00% | 0.00% |

Worst path inflates the observed drawdown by **2.2x under i.i.d.** and **3.1x under the block bootstrap**.

### OOS — 216 trades, observed DD 14.90R, observed streak 9

| metric | i.i.d. bootstrap | moving-block B20 |
|---|---:|---:|
| DD p50 | 13.4 | 16.4 |
| DD p95 | 21.0 | 26.5 |
| DD p99 | 25.7 | 32.4 |
| DD worst | 40.4 | 49.4 |
| streak p99 | 17 | 16 |
| streak worst | 29 | 23 |
| underwater worst (trades) | 97 | 169 |
| observed DD sits at percentile | 66.6 | 31.4 |
| paths ending flat or worse | 0.00% | 0.00% |

**Drawdown exceeded, out of 10000 paths**

| over | i.i.d. | block |
|---:|---:|---:|
| 10R | 91.24% | 96.69% |
| 20R | 6.99% | 24.56% |
| 25R | 1.35% | 7.33% |
| 35R | 0.03% | 0.50% |
| 50R | 0.00% | 0.00% |
| 75R | 0.00% | 0.00% |
| 100R | 0.00% | 0.00% |

Worst path inflates the observed drawdown by **2.7x under i.i.d.** and **3.3x under the block bootstrap**.

---

## How to read this

The doc's survivability question is whether the account and the sizing
survive the worst ordering. The kill-line it suggests is the P99 —
position so that the 99th-percentile drawdown is survivable rather than
the one history happened to produce.

Two things worth carrying away. First, **the observed drawdown is not
the number to size against** — for 107 on IS it sits in the top
half-percentile of its own shuffles, so the history was arranged
unluckily and the median ordering is far gentler. Second, **block
bootstrap is the honest one to quote**, because an i.i.d. resample
dissolves losing streaks and a losing streak is what a drawdown *is*.
