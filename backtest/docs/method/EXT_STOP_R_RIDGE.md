# ext_stop_r: why 2.0 looked like an edge, and why it is not one

Date: 2026-10-07. Harness: `backtest/tests/exp_ext2_ridge.py`. Engine is post-C17.
Book: `fsent_champ_long`. Status: **closed, nothing adopted.**

## WHERE THE LEAD CAME FROM

A coarse sweep had IS +545.3 at `ext_stop_r=2.0` against +528.9 at the shipped
3.0, with 1.5 and 2.5 on either side of the grid and neither close. That reads as
a spike, and a spike between two lower neighbours is the standard overfit shape,
so it was worth walking the neighbourhood before spending a cohort autopsy on one
point.

## PART 1 - FINE SWEEP, BOTH ERAS

19 values, 0.0 to 4.0, against OFF:

| ext | IS n / net / PF / DD | OOS n / net / PF / DD | lift IS / OOS |
|---:|---|---|---|
| 0.0 | 528 / +533.4 / 3.09 / 13.4 | 311 / +239.6 / 2.69 / 11.9 | - / - |
| 1.5 | 477 / +502.2 / 3.16 / 27.7 | 275 / +178.6 / 2.38 / 16.5 | -31.2 / -61.0 |
| 1.8 | 497 / +524.4 / 3.23 / 27.7 | 289 / +221.8 / 2.66 / 16.6 | -9.0 / -17.8 |
| 1.9 | 503 / **+551.2** / 3.32 / 14.0 | 292 / +222.7 / 2.64 / 13.8 | +17.8 / **-16.9** |
| **2.0** | 509 / +549.4 / 3.27 / 15.4 | 300 / +238.7 / 2.73 / 14.9 | +16.0 / **-0.9** |
| 2.1 | 512 / +545.1 / 3.23 / 15.4 | 303 / +232.8 / 2.66 / 16.1 | +11.7 / -6.8 |
| 2.3 | 517 / +538.9 / 3.16 / 13.4 | 308 / +236.1 / 2.65 / 15.1 | +5.5 / -3.5 |
| 2.5 | 524 / +532.5 / 3.11 / 13.4 | 309 / +236.9 / 2.66 / 15.1 | -0.9 / -2.7 |
| 3.0 (shipped) | 528 / +533.4 / 3.09 / 13.4 | 311 / +239.6 / 2.69 / 11.9 | +0.0 / +0.0 |
| 4.0 | 528 / +533.4 / 3.09 / 13.4 | 311 / +239.6 / 2.69 / 11.9 | +0.0 / +0.0 |

**No value on the grid beats OFF in both eras.** The in-sample ridge is real in
shape - 1.9 through 2.3 all lift IS by +5 to +18 - but every point on it is
negative or flat out of sample, and 1.9, which the coarse grid had missed, is the
best IS point of all while being the worst of the ridge out of sample.

One structural read: IS drawdown sits at 26-27.7 for every value at or below 1.8
and drops to 13.4-15.4 from 1.9 up. So most of the ridge's in-sample appeal is
that the filter cuts trades which inflate drawdown without paying for them.

## PART 2 - COHORT AUTOPSY AT 2.0

| era | cohort | n | sumR | mean | median | win |
|---|---|---:|---:|---:|---:|---:|
| IS | OFF | 528 | +629.7 | +1.193 | -0.161 | 42.0% |
| IS | KEPT | 488 | +631.2 | +1.293 | -0.157 | 43.4% |
| IS | **REMOVED** | 40 | **-1.5** | -0.037 | -0.555 | 25.0% |
| IS | **ADDED** | 21 | **+11.9** | +0.566 | -0.029 | 47.6% |
| OOS | OFF | 311 | +275.1 | +0.884 | -0.181 | 37.6% |
| OOS | KEPT | 292 | +265.5 | +0.909 | -0.179 | 38.4% |
| OOS | **REMOVED** | 19 | **+9.6** | +0.506 | -0.279 | 26.3% |
| OOS | **ADDED** | 8 | **+8.3** | +1.043 | -0.139 | 25.0% |

Removed by side: IS 22 long / 18 short, OOS 15 long / 4 short.

**This is the part that settles it.**

- **IS**: the filter removes a cohort worth **-1.5R over 40 trades** - break-even
  at best. It is worth +1.5R on its own account. The book's +16R in-sample "gain"
  is therefore almost entirely the **21 trades that got ADDED** (+11.9R), not the
  filter choosing better trades.
- **OOS**: the filter removes a cohort worth **+9.6R over 19 trades**. Out of
  sample it deletes profitable trades.

Those ADDED trades are a path effect, not an edge. `cooldown_bars` and the streak
halt act on the *sequence* of booked trades, so removing trades admits different
later ones. That coupling is why an in-sample-only move can appear here at all,
and it is not a property of the market that would survive a fresh period.

A filter that removes a profitable cohort out of sample is not an edge in either
direction. It is an unpriced cut.

## VERDICT

`ext_stop_r=2.0` is not a candidate. The knob stays at 3.0.

Separately, and following from C17 rather than from this sweep: at 3.0 the knob
now blocks **zero** signals, and `ext_stop_r=3.0` and `ext_stop_r=0.0` produce
byte-identical trade lists on this book. So the threshold question is settled by
C17 alone - 3.0 is not "the value that was tuned", it is the top of a dead
plateau, and dropping it from the book's config costs nothing in behaviour.

Do not quote the IS +16R at 2.0 anywhere. It is a re-sequencing artifact on one
sample, and this file exists so the next person does not rediscover it on the
coarse grid and stop there.
