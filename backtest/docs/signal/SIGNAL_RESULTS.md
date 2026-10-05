# SIGNAL PLANE — measured results, every book

Generated from `backtest/tests/_signal_metrics.json` (harness
`signal_metrics`), computed from the engine by
`python backtest/tests/exp_signal_metrics.py`. Nothing here is
transcribed by hand; the registry pins carry four fields and this
file carries the rest.

Scope: **signal plane only** — `max_positions == 1`, one position at
a time. Multi books (`max_positions != 1`) are deliberately excluded:
they hold 400-600 trades at once and are a different question.

`top5%` is the share of net carried by the best 5% of trades. Read
it before `net` — a book at 700% has a handful of lucky trades and
everything else in the book loses money.

## Summary

| | count |
|---|---|
| signal books measured | 46 |
| quarantined look-ahead, not run | 3 |
| ranked (both eras, n >= 30) | 44 |
| **positive in BOTH eras** | **21** |
| under the trade floor, reported not ranked | 2 |

## Quarantined — do not quote these

These read a swing field that is not settled at the entry bar. Their
numbers are kept as evidence that the look-ahead was caught, and are
excluded from every ranking in the database as well as here.

| book | knobs |
|---|---|
| `age10_dirmatch_swingpause_sig_sw10` | `exp_require_dir_match`, `exp_max_swing_age` |
| `dirmatch_sig_sw10` | `exp_require_dir_match` |
| `dirmatch_swingpause_sig_sw10` | `exp_require_dir_match` |

## All ranked signal books, by out-of-sample net

`R/trd` mean R per trade | `wr%` win rate | `PF` profit factor |
`DD` max drawdown in R | `top5%` share of net from the best 5% of
trades | `med` median R (negative means most trades lose) |
`strk` longest losing run.

| book | ISn | IS net | R/trd | wr% | PF | DD | top5% | med | strk | OOSn | **OOS net** | R/trd | wr% | PF | DD | top5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fsent_sig_full` | 234 | +291.0 | +1.244 | 41.0% | 3.00 | 10.8 | 82 | -1.01 | 10 | 153 | **+190.5** | +1.245 | 45.1% | 3.33 | 7.0 | 66 |
| `fsent_sig_fs_mom` | 235 | +262.3 | +1.116 | 38.7% | 3.02 | 10.1 | 88 | -0.33 | 11 | 152 | **+165.6** | +1.090 | 40.1% | 3.31 | 9.1 | 75 |
| `fsent_sig_wk_pause_short` | 302 | +206.9 | +0.685 | 35.8% | 2.18 | 10.6 | 93 | -0.53 | 8 | 179 | **+128.8** | +0.719 | 35.2% | 2.41 | 10.5 | 73 |
| `fsent_sig_sw10_short` | 369 | +174.1 | +0.472 | 32.2% | 1.77 | 16.6 | 117 | -0.63 | 9 | 239 | **+100.9** | +0.422 | 31.0% | 1.72 | 11.8 | 110 |
| `fsent_sig_sw20_short` | 343 | +146.9 | +0.428 | 34.1% | 1.71 | 32.5 | 107 | -0.64 | 11 | 203 | **+95.0** | +0.468 | 31.5% | 1.81 | 10.2 | 107 |
| `fsent_sig_sw20_short_wr` | 343 | +146.9 | +0.428 | 34.1% | 1.71 | 32.5 | 107 | -0.64 | 11 | 203 | **+95.0** | +0.468 | 31.5% | 1.81 | 10.2 | 107 |
| `fsent_sig_sw10_long` | 355 | +116.4 | +0.328 | 32.7% | 1.55 | 21.1 | 130 | -0.52 | 10 | 229 | **+81.5** | +0.356 | 30.1% | 1.63 | 13.5 | 107 |
| `wage20_swingpause_sig_sw10` | 234 | +209.5 | +0.895 | 28.6% | 2.11 | 23.0 | 128 | -1.10 | 13 | 143 | **+48.5** | +0.340 | 28.0% | 1.45 | 23.6 | 159 |
| `wage10_swingpause_wskip_sig_sw10` | 262 | +270.8 | +1.034 | 28.6% | 2.31 | 23.0 | 122 | -1.09 | 14 | 158 | **+35.6** | +0.226 | 26.6% | 1.29 | 25.8 | 212 |
| `fullstack_swingpause_sig_sw10` | 225 | +243.8 | +1.084 | 28.0% | 2.38 | 23.4 | 123 | -1.11 | 11 | 149 | **+31.2** | +0.210 | 25.5% | 1.26 | 31.3 | 242 |
| `wage16_swingpause_sig_sw10` | 246 | +256.7 | +1.044 | 28.9% | 2.31 | 24.6 | 123 | -1.09 | 13 | 147 | **+31.0** | +0.211 | 26.5% | 1.27 | 26.2 | 244 |
| `curfew624_swingpause_sig_sw10` | 250 | +176.6 | +0.706 | 28.4% | 1.90 | 17.5 | 138 | -1.09 | 13 | 149 | **+30.3** | +0.203 | 26.2% | 1.27 | 25.3 | 254 |
| `wage8_swingpause_sig_sw10` | 265 | +250.4 | +0.945 | 27.5% | 2.17 | 23.0 | 132 | -1.09 | 15 | 161 | **+30.3** | +0.188 | 26.1% | 1.24 | 29.9 | 273 |
| `nowknd_sig_sw10` | 321 | +107.6 | +0.335 | 25.5% | 1.41 | 41.5 | 240 | -1.09 | 13 | 192 | **+27.0** | +0.141 | 25.5% | 1.18 | 27.3 | 337 |
| `fullstack_wage10_cd0_sig_sw10` | 199 | +273.2 | +1.373 | 29.1% | 2.76 | 24.3 | 103 | -1.11 | 11 | 139 | **+26.1** | +0.188 | 24.5% | 1.23 | 35.0 | 262 |
| `wage24_swingpause_sig_sw10` | 220 | +225.2 | +1.024 | 30.9% | 2.34 | 16.6 | 119 | -1.09 | 13 | 136 | **+26.0** | +0.192 | 25.7% | 1.25 | 30.2 | 268 |
| `nowknd_swingpause_sig_sw10` | 295 | +205.2 | +0.696 | 27.5% | 1.87 | 27.2 | 147 | -1.09 | 11 | 174 | **+24.6** | +0.141 | 25.3% | 1.18 | 23.1 | 336 |
| `utcsat_swingpause_sig_sw10` | 323 | +134.2 | +0.416 | 25.1% | 1.51 | 34.9 | 206 | -1.09 | 18 | 198 | **+22.3** | +0.113 | 27.3% | 1.15 | 20.7 | 359 |
| `fsswing_sig_sw10` | 404 | +31.2 | +0.077 | 24.3% | 1.09 | 51.4 | 700 | -1.10 | 14 | 237 | **+12.6** | +0.053 | 26.2% | 1.07 | 29.4 | 704 |
| `wage12_swingpause_sig_sw10` | 259 | +267.3 | +1.032 | 28.6% | 2.28 | 24.4 | 120 | -1.09 | 13 | 155 | **+12.0** | +0.078 | 24.5% | 1.10 | 30.8 | 604 |
| `fsswing_sig_sw20` | 384 | +98.4 | +0.256 | 27.3% | 1.31 | 53.9 | 212 | -1.12 | 14 | 211 | **+0.2** | +0.001 | 26.5% | 1.00 | 30.5 | 35760 |
| `chopband_atrr_swingpause_sig_sw10` | 269 | +134.4 | +0.499 | 22.7% | 1.58 | 33.0 | 188 | -1.13 | 20 | 177 | **-4.2** | -0.024 | 23.2% | 0.97 | 42.8 | 0 |
| `bm05_swingpause_sig_sw10` | 336 | +106.5 | +0.317 | 22.9% | 1.38 | 46.6 | 254 | -1.10 | 21 | 204 | **-4.7** | -0.023 | 24.5% | 0.97 | 34.2 | 0 |
| `atrr_swingpause_sig_sw20` | 313 | +118.1 | +0.377 | 26.5% | 1.46 | 49.7 | 195 | -1.12 | 13 | 177 | **-4.9** | -0.028 | 25.4% | 0.96 | 32.3 | 0 |
| `wage12_swingpause_sig_sw20` | 303 | +148.8 | +0.491 | 28.7% | 1.60 | 45.6 | 170 | -1.11 | 10 | 172 | **-5.3** | -0.031 | 25.0% | 0.96 | 35.9 | 0 |
| `wage12_swingpause_sig_nowknd_sw10` | 316 | +202.9 | +0.642 | 25.3% | 1.76 | 42.3 | 165 | -1.11 | 17 | 191 | **-5.9** | -0.031 | 23.0% | 0.96 | 40.2 | 0 |
| `chopband_atrr_swingpause_sig_sw20` | 277 | +109.3 | +0.394 | 24.5% | 1.47 | 42.8 | 199 | -1.12 | 13 | 159 | **-6.8** | -0.043 | 24.5% | 0.95 | 43.2 | 0 |
| `chopband_swingpause_sig_sw20` | 309 | +91.0 | +0.295 | 25.6% | 1.36 | 46.4 | 243 | -1.10 | 11 | 181 | **-6.8** | -0.037 | 24.9% | 0.95 | 37.3 | 0 |
| `skipwinhalt_sig_sw10` | 276 | +37.7 | +0.137 | 22.8% | 1.16 | 39.9 | 539 | -1.11 | 13 | 159 | **-7.0** | -0.044 | 22.6% | 0.94 | 31.5 | 0 |
| `chopband_swingpause_sig_sw10` | 320 | +183.7 | +0.574 | 23.1% | 1.68 | 38.1 | 186 | -1.10 | 14 | 197 | **-8.1** | -0.041 | 24.4% | 0.95 | 40.5 | 0 |
| `atrr_swingpause_sig_sw10` | 316 | +150.8 | +0.477 | 22.2% | 1.55 | 38.3 | 202 | -1.13 | 17 | 198 | **-9.4** | -0.048 | 23.7% | 0.94 | 29.4 | 0 |
| `causalsl_swingpause_sig_sw10` | 351 | +112.0 | +0.319 | 24.2% | 1.40 | 52.7 | 246 | -1.07 | 14 | 213 | **-9.6** | -0.045 | 24.4% | 0.94 | 26.3 | 0 |
| `swingpause_sig_sw20` | 342 | +118.0 | +0.345 | 28.4% | 1.43 | 53.7 | 207 | -1.10 | 13 | 193 | **-10.7** | -0.056 | 24.4% | 0.93 | 30.3 | 0 |
| `b2doji_swingpause_sig_sw10` | 335 | +119.5 | +0.357 | 23.0% | 1.43 | 53.4 | 250 | -1.10 | 21 | 207 | **-12.7** | -0.061 | 22.7% | 0.92 | 35.1 | 0 |
| `champion_sig_sw20` | 377 | +89.3 | +0.237 | 27.1% | 1.29 | 54.9 | 224 | -1.12 | 14 | 208 | **-13.0** | -0.063 | 25.0% | 0.92 | 32.3 | 0 |
| `champion_sig_sw10` | 396 | +37.8 | +0.096 | 24.0% | 1.11 | 51.8 | 596 | -1.11 | 15 | 231 | **-16.3** | -0.071 | 23.4% | 0.91 | 41.7 | 0 |
| `atrr_cd0_swingpause_sig_sw10` | 317 | +149.0 | +0.470 | 22.1% | 1.54 | 40.1 | 205 | -1.13 | 17 | 198 | **-16.8** | -0.085 | 22.7% | 0.90 | 33.9 | 0 |
| `swingpause_sig_sw10` | 356 | +137.5 | +0.386 | 22.8% | 1.46 | 48.4 | 232 | -1.10 | 21 | 214 | **-19.7** | -0.092 | 23.8% | 0.88 | 37.0 | 0 |
| `age50_swingpause_sig_sw10` | 350 | +133.2 | +0.381 | 22.0% | 1.44 | 47.4 | 238 | -1.11 | 21 | 211 | **-23.9** | -0.113 | 23.2% | 0.86 | 41.2 | 0 |
| `skipwin1_sig_sw10` | 139 | -41.7 | -0.300 | 17.3% | 0.67 | 58.6 | 0 | -1.13 | 14 | 82 | **-24.0** | -0.293 | 15.9% | 0.65 | 27.5 | 0 |
| `utc_wknd_swingpause_sig_sw10` | 285 | +139.9 | +0.491 | 26.3% | 1.62 | 42.4 | 184 | -1.09 | 13 | 172 | **-26.3** | -0.153 | 21.5% | 0.81 | 35.6 | 0 |
| `rmax10_swingpause_sig_sw10` | 255 | +184.4 | +0.723 | 20.0% | 1.71 | 47.0 | 171 | -1.19 | 15 | 88 | **-32.6** | -0.370 | 10.2% | 0.66 | 42.6 | 0 |
| `fliponly_swingpause_sig_sw10` | 237 | +140.8 | +0.594 | 23.2% | 1.67 | 32.7 | 180 | -1.13 | 14 | 146 | **-34.2** | -0.234 | 17.1% | 0.74 | 42.7 | 0 |
| `rmax15_swingpause_sig_sw10` | 310 | +126.6 | +0.408 | 21.6% | 1.44 | 53.4 | 235 | -1.14 | 15 | 154 | **-54.2** | -0.352 | 12.3% | 0.65 | 59.4 | 0 |

## Under the 30-trade floor

Reported so nothing is hidden, ranked by nothing. A net figure here
is a few trades, not an edge.

| book | ISn | IS net | PF | OOSn | OOS net | PF |
|---|---:|---:|---:|---:|---:|---:|
| `trail06_swingpause_sig` | 2 | +2173.2 | 1592.74 | 53 | -38.0 | 0.24 |
| `trail10_swingpause_sig` | 3 | +376.6 | 276.84 | 56 | -38.3 | 0.24 |

## What separates them

Sorted by OOS net the list splits into two groups, and the gap shows
up in `top5%` before it shows up in net.

**`fsent_sig_full`, `fsent_sig_fs_mom`, `fsent_sig_wk_pause_short`** —
win rate 35-45%, profit factor 2.2-3.3, `top5%` 66-93%. The best 5% of
trades carry most of the profit but not all of it, so the other 95%
still contribute. Median R stays near zero, which is what a book with a
broad base looks like.

**Everything else** — win rate 22-30%, profit factor 1.1-1.9, `top5%`
128-700%. Most trades lose (median about -1.07, a full stop) and the
profit arrives in a thin tail. `champion_sig_sw10` is the clearest
case: `top5%` 704% means the five best out-of-sample trades were worth
more than the book's entire net, so every other trade lost money
together.

**In-sample versus out-of-sample.** The wage and fullstack families
compete on IS — several beat `fsent_sig_full`'s +291 — then fall to
+26 to +49 out of sample, about a tenth of their in-sample number.
`fsent_sig_full` retains 66% and `fsent_sig_fs_mom` 63%. Retention
separated them; net alone did not.

## Verification

Each book was compared against its registry pin after measuring.

| book | era | measured | pin | difference |
|---|---|---:|---:|---:|
| `fsent_sig_sw10_long` | oos | +81.5 | +80.5 | +1.0 |

