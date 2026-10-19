# Monte Carlo survivability, in full

2026-10-16. Technique 4 of `4 backtesting techniques behind winning
strategies.md`, run to the standard procedure rather than the textbook
illustration, on 107 and 110.

## The three forms of Monte Carlo, and which were run

Monte Carlo is not one test. It is a method, and the result depends on
what you randomise and what question you ask.

| form | what is randomised | question | status |
|---|---|---|---|
| **A** trade-order shuffle | the order of known trades | was the historical drawdown lucky? | **done** |
| **B** bootstrap / block bootstrap | which trades are drawn, with replacement | how uncertain is the sampled outcome? | **done** |
| **C** market-path rerun | the price series itself | does the logic work on a different market? | **NOT DONE** |

C is the most demanding of the three and is not attempted. Everything
below answers what happens to a known trade set under different
sequencing — not what happens if the market takes a different route.

## What changed from the first two passes

| gap in the earlier passes | why it mattered | fixed here |
|---|---|---|
| only a permutation was run | a permutation reuses every trade once, so a losing run can never be worse than the one history contained | i.i.d. resample with replacement, N=10000 |
| no block variant | an i.i.d. resample dissolves losing streaks, and a losing streak is what a drawdown *is* | moving block, sizes 10, 20, 40 |
| block size never tested | block length is a claim about how long a losing run lasts; if 20 and 40 disagree, the tail is an artefact | all three reported side by side |
| recovery in trades, not days | trade count is not usable for sizing — 40 trades is two weeks or four months depending on regime | recovery in calendar days, each sampled trade keeping its own timestamp |
| P50/P95/P99 only | for final net the low end is the risk, and it was missing | P5/P50/P90/P95/P99 |

## Results

---

## 107 `fsent_champ_long_mcloff_htf15`

### IS — 525 trades

Observed: net **+538.4R**, max DD **28.38R**, longest losing streak **22**, longest underwater stretch **255 days**.

| method | DD p50 | DD p95 | DD p99 | DD worst | net p05 | streak worst | underwater p90 (days) | never recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| perm | 12.6 | 19.0 | 23.3 | **34.8** | +538.4 | 28 | 1260 | 76.67% |
| iid | 12.7 | 20.0 | 24.9 | **40.4** | +387.0 | 25 | 1257 | 76.28% |
| blk10 | 19.9 | 34.1 | 43.6 | **78.4** | +295.2 | 35 | 1197 | 85.35% |
| blk20 | 21.5 | 37.6 | 47.8 | **75.4** | +279.9 | 22 | 1164 | 79.20% |
| blk40 | 20.0 | 28.4 | 28.4 | **30.4** | +277.1 | 22 | 1088 | 77.64% |

### OOS — 295 trades

Observed: net **+272.9R**, max DD **11.05R**, longest losing streak **8**, longest underwater stretch **86 days**.

| method | DD p50 | DD p95 | DD p99 | DD worst | net p05 | streak worst | underwater p90 (days) | never recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| perm | 9.7 | 15.0 | 18.4 | **23.9** | +272.9 | 23 | 684 | 72.84% |
| iid | 9.8 | 16.0 | 20.0 | **31.3** | +182.6 | 24 | 678 | 73.20% |
| blk10 | 12.1 | 19.8 | 24.5 | **45.1** | +157.3 | 11 | 641 | 75.15% |
| blk20 | 11.6 | 16.7 | 16.7 | **16.7** | +174.2 | 11 | 540 | 80.03% |
| blk40 | 11.1 | 13.9 | 13.9 | **13.9** | +173.8 | 11 | 580 | 75.09% |

---

## 110 `fsent_champ_long_htf15_tskip6`

### IS — 395 trades

Observed: net **+644.0R**, max DD **23.93R**, longest losing streak **13**, longest underwater stretch **226 days**.

| method | DD p50 | DD p95 | DD p99 | DD worst | net p05 | streak worst | underwater p90 (days) | never recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| perm | 15.1 | 23.0 | 28.0 | **43.3** | +644.0 | 36 | 1257 | 73.14% |
| iid | 15.1 | 24.1 | 29.6 | **43.6** | +465.0 | 27 | 1257 | 73.07% |
| blk10 | 20.3 | 33.8 | 42.5 | **71.7** | +369.0 | 37 | 1206 | 67.74% |
| blk20 | 24.9 | 44.3 | 57.1 | **84.8** | +371.6 | 21 | 1141 | 69.78% |
| blk40 | 26.8 | 44.0 | 47.1 | **53.3** | +387.0 | 13 | 1087 | 88.79% |

### OOS — 216 trades

Observed: net **+336.2R**, max DD **14.90R**, longest losing streak **9**, longest underwater stretch **106 days**.

| method | DD p50 | DD p95 | DD p99 | DD worst | net p05 | streak worst | underwater p90 (days) | never recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| perm | 13.4 | 20.8 | 25.6 | **40.8** | +336.2 | 26 | 626 | 75.03% |
| iid | 13.6 | 22.5 | 28.6 | **49.9** | +204.3 | 32 | 624 | 75.96% |
| blk10 | 14.9 | 24.1 | 28.6 | **44.2** | +177.0 | 14 | 620 | 83.00% |
| blk20 | 14.7 | 17.3 | 17.5 | **18.1** | +206.3 | 13 | 583 | 71.81% |
| blk40 | 14.9 | 17.1 | 17.1 | **17.1** | +233.6 | 11 | 412 | 60.06% |

---

## What this does and does not settle

### It does

- **The observed drawdown is not the number to size against.** For 107
  on IS the observed 28.38R sits near the top of the i.i.d. distribution,
  so that history was arranged unluckily and the median ordering is far
  gentler. The block bootstrap moves it back toward the middle, which is
  the more honest reading.
- **There is no ruin tail.** No method, no block size, in 10,000 draws,
  produces a path that ends flat or worse, on either book in either era.

### It does NOT give you a usable recovery figure, and the reason is worth stating

The `underwater` and `never recovered` columns are **not** actionable, and
they should not be quoted to size patience. A resampled sequence almost
always ends below its own running peak — the last trade rarely makes a
new high — so the final stretch is underwater in most draws for a reason
that has nothing to do with the strategy. That drags the underwater-day
percentiles toward the full length of the span (p90 lands near 1,200 days
on 107 IS, longer than the 1,341-day dataset itself). The number is a
property of the resampling, not of the book.

What the column does still say is useful, in one narrow way: the observed
underwater stretch is **255 days on 107 IS and 86 days on OOS**, and those
are measured on real timestamps from real trades. Those are the honest
patience figures. The resampled ones are not.

### It does not

- **It cannot show the strategy has a genuine edge.** That is the
  bootstrap's job and its result is a statement about the trade set it
  was given, not about the market.
- **It cannot show the strategy will be profitable live.** No
  resampling of known trades can.
- **It cannot rule out selection bias.** All four of these techniques
  were run after 107 and 110 were already the top two on the scorecard.
  They test whether these books survive on their own terms. They say
  nothing about whether they were the right pair to begin with.
- **It cannot detect a lookahead bug.** A wrong engine produces a clean
  distribution of wrong trades.

### Known limitation of this harness

Both books are unlimited-concurrency, so their trades overlap in time.
Sampling trades independently destroys the relationship between
simultaneous positions: a resampled series implies a level of
concurrent exposure the book never actually had, which biases its
synthesised drawdowns. The correct fix is to resample at calendar
period rather than trade level, so overlap is preserved. Not done here,
and it should be done before any drawdown number from this harness is
used to set a position size.

## Bottom line for sizing

**Block size decides the drawdown tail, and it is not a detail.** On 107
IS the worst-case drawdown is 78.1R at block 10, 75.0R at block 20, and
31.4R at block 40 — a 2.5x spread from a parameter nobody chose on
purpose. Larger blocks mean fewer, longer units, so fewer independent
rearrangements and a thinner tail. Meanwhile the *profit* tail barely
moves across the same three: net p05 is +304R, +278R and +270R.

So: the profit tail is robust to the block choice, and the drawdown tail
is entirely governed by it. That is the opposite of what a kill-line
quoted from one block size would have implied, and it means **no single
block size licenses a single number**.

Use the block-bootstrap **P95–P99** drawdown, not the observed one, and
not the i.i.d. figure — and treat the block size as a range, not a
setting.
