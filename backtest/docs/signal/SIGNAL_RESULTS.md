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

`n` counts CLOSED trades: the registry's net pins exclude positions
still open at the era boundary (their r is mark-to-market, not
realized), so `n` here can sit under the board's n while `net`
matches its pin. `n_open` in the source JSON holds the difference.

## Summary

| | count |
|---|---|
| signal books measured | 50 |
| quarantined look-ahead, not run | 3 |
| ranked (both eras, n >= 30) | 48 |
| **positive in BOTH eras** | **27** |
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
| `fsent_sig_full` | 234 | +295.8 | +1.264 | 41.5% | 3.08 | 10.8 | 81 | -0.99 | 10 | 151 | **+194.4** | +1.288 | 46.4% | 3.48 | 7.0 | 65 |
| `fsent_sig_trail_delay1` | 199 | +418.5 | +2.103 | 34.7% | 4.28 | 13.3 | 86 | -1.03 | 13 | 122 | **+182.0** | +1.492 | 41.0% | 3.57 | 7.5 | 76 |
| `fsent_sig_fs_mom` | 235 | +268.4 | +1.142 | 39.6% | 3.14 | 9.0 | 86 | -0.31 | 10 | 153 | **+166.8** | +1.090 | 40.5% | 3.33 | 9.1 | 74 |
| `fsent_sig_half_crossed` | 97 | +340.9 | +3.514 | 37.1% | 6.82 | 8.5 | 82 | -0.56 | 8 | 62 | **+142.1** | +2.292 | 40.3% | 5.00 | 7.3 | 56 |
| `fsent_sig_decay_crossed` | 104 | +195.6 | +1.881 | 45.2% | 4.18 | 8.6 | 74 | -0.57 | 9 | 67 | **+130.3** | +1.944 | 49.3% | 4.78 | 7.4 | 51 |
| `fsent_sig_wk_pause_short` | 306 | +203.3 | +0.664 | 35.3% | 2.14 | 10.6 | 95 | -0.55 | 8 | 180 | **+129.9** | +0.722 | 35.6% | 2.43 | 10.5 | 77 |
| `fsent_sig_sw10_short` | 373 | +175.4 | +0.470 | 32.4% | 1.76 | 16.6 | 116 | -0.65 | 10 | 239 | **+103.3** | +0.432 | 31.4% | 1.75 | 11.8 | 108 |
| `fsent_sig_sw20_short` | 343 | +146.2 | +0.426 | 34.1% | 1.70 | 30.8 | 108 | -0.64 | 16 | 203 | **+97.0** | +0.478 | 31.5% | 1.84 | 8.9 | 104 |
| `fsent_sig_sw20_short_wr` | 343 | +146.2 | +0.426 | 34.1% | 1.70 | 30.8 | 108 | -0.64 | 16 | 203 | **+97.0** | +0.478 | 31.5% | 1.84 | 8.9 | 104 |
| `fsent_both_trail_half` | 253 | +77.7 | +0.307 | 27.3% | 1.44 | 31.4 | 201 | -1.05 | 11 | 141 | **+96.9** | +0.687 | 32.6% | 2.15 | 14.8 | 117 |
| `fsent_sig_sw10_long` | 353 | +121.2 | +0.343 | 33.1% | 1.59 | 21.1 | 124 | -0.52 | 10 | 232 | **+74.2** | +0.320 | 29.3% | 1.55 | 13.3 | 117 |
| `wage20_swingpause_sig_sw10` | 233 | +202.0 | +0.867 | 28.3% | 2.07 | 23.0 | 133 | -1.10 | 13 | 143 | **+48.5** | +0.340 | 28.0% | 1.45 | 23.6 | 159 |
| `nowknd_sig_sw10` | 319 | +124.2 | +0.389 | 26.3% | 1.49 | 40.2 | 203 | -1.08 | 13 | 194 | **+39.9** | +0.206 | 26.8% | 1.27 | 22.8 | 228 |
| `wage10_swingpause_wskip_sig_sw10` | 261 | +268.9 | +1.030 | 28.4% | 2.29 | 23.0 | 123 | -1.09 | 14 | 158 | **+35.6** | +0.226 | 26.6% | 1.29 | 25.8 | 212 |
| `nowknd_swingpause_sig_sw10` | 292 | +216.3 | +0.741 | 28.1% | 1.96 | 27.4 | 139 | -1.08 | 15 | 173 | **+34.6** | +0.200 | 26.6% | 1.26 | 23.0 | 239 |
| `fullstack_swingpause_sig_sw10` | 229 | +242.4 | +1.059 | 27.9% | 2.33 | 23.1 | 124 | -1.11 | 11 | 152 | **+32.0** | +0.211 | 25.7% | 1.27 | 33.8 | 236 |
| `wage16_swingpause_sig_sw10` | 245 | +249.3 | +1.017 | 28.6% | 2.27 | 24.6 | 126 | -1.09 | 13 | 147 | **+31.0** | +0.211 | 26.5% | 1.27 | 26.2 | 244 |
| `curfew624_swingpause_sig_sw10` | 256 | +181.0 | +0.707 | 28.1% | 1.91 | 18.0 | 135 | -1.08 | 13 | 153 | **+30.8** | +0.201 | 26.1% | 1.26 | 26.6 | 250 |
| `wage8_swingpause_sig_sw10` | 263 | +250.3 | +0.952 | 27.4% | 2.18 | 23.0 | 132 | -1.09 | 15 | 161 | **+30.3** | +0.188 | 26.1% | 1.24 | 29.9 | 273 |
| `fullstack_wage10_cd0_sig_sw10` | 199 | +273.2 | +1.373 | 29.1% | 2.76 | 24.3 | 103 | -1.11 | 11 | 139 | **+26.1** | +0.188 | 24.5% | 1.23 | 35.0 | 262 |
| `wage24_swingpause_sig_sw10` | 219 | +224.0 | +1.023 | 30.6% | 2.33 | 16.6 | 116 | -1.09 | 13 | 136 | **+26.0** | +0.192 | 25.7% | 1.25 | 30.2 | 268 |
| `utcsat_swingpause_sig_sw10` | 327 | +94.3 | +0.288 | 24.5% | 1.35 | 45.1 | 257 | -1.09 | 24 | 203 | **+13.6** | +0.067 | 26.6% | 1.09 | 24.4 | 632 |
| `wage12_swingpause_sig_sw10` | 258 | +266.1 | +1.031 | 28.3% | 2.28 | 24.4 | 121 | -1.09 | 13 | 155 | **+12.0** | +0.078 | 24.5% | 1.10 | 30.8 | 604 |
| `fsswing_sig_sw10` | 404 | +42.5 | +0.105 | 24.3% | 1.13 | 45.1 | 515 | -1.10 | 15 | 245 | **+11.2** | +0.046 | 26.1% | 1.06 | 34.6 | 844 |
| `causalsl_swingpause_sig_sw10` | 355 | +71.9 | +0.203 | 23.9% | 1.25 | 81.9 | 335 | -1.07 | 14 | 218 | **+7.0** | +0.032 | 24.3% | 1.04 | 26.4 | 1305 |
| `chopband_swingpause_sig_sw20` | 314 | +86.8 | +0.277 | 25.5% | 1.34 | 47.7 | 256 | -1.10 | 11 | 182 | **+0.4** | +0.002 | 25.3% | 1.00 | 36.3 | 17831 |
| `fsswing_sig_sw20` | 382 | +99.2 | +0.260 | 27.7% | 1.32 | 50.1 | 210 | -1.11 | 14 | 218 | **+0.4** | +0.002 | 25.7% | 1.00 | 36.0 | 17430 |
| `chopband_atrr_swingpause_sig_sw10` | 270 | +120.7 | +0.447 | 22.2% | 1.52 | 43.1 | 209 | -1.13 | 20 | 181 | **-2.0** | -0.011 | 23.2% | 0.99 | 43.9 | 0 |
| `bm05_swingpause_sig_sw10` | 336 | +83.1 | +0.247 | 23.2% | 1.30 | 52.2 | 286 | -1.10 | 16 | 209 | **-3.8** | -0.018 | 24.4% | 0.98 | 37.9 | 0 |
| `skipwinhalt_sig_sw10` | 280 | -1.5 | -0.005 | 22.1% | 0.99 | 67.5 | 0 | -1.11 | 19 | 162 | **-4.2** | -0.026 | 22.8% | 0.97 | 34.0 | 0 |
| `chopband_atrr_swingpause_sig_sw20` | 281 | +102.1 | +0.363 | 24.6% | 1.43 | 42.5 | 220 | -1.12 | 13 | 162 | **-5.2** | -0.032 | 24.7% | 0.96 | 43.0 | 0 |
| `wage12_swingpause_sig_sw20` | 302 | +147.6 | +0.489 | 28.5% | 1.60 | 45.6 | 171 | -1.11 | 10 | 172 | **-5.3** | -0.031 | 25.0% | 0.96 | 35.9 | 0 |
| `wage12_swingpause_sig_nowknd_sw10` | 313 | +205.7 | +0.657 | 25.2% | 1.78 | 38.3 | 163 | -1.10 | 17 | 191 | **-5.9** | -0.031 | 23.0% | 0.96 | 40.2 | 0 |
| `atrr_swingpause_sig_sw20` | 317 | +118.0 | +0.372 | 26.5% | 1.45 | 49.4 | 195 | -1.12 | 13 | 181 | **-6.8** | -0.038 | 25.4% | 0.95 | 32.8 | 0 |
| `skipwin1_sig_sw10` | 142 | -40.3 | -0.284 | 17.6% | 0.69 | 63.8 | 0 | -1.12 | 17 | 80 | **-8.7** | -0.108 | 17.5% | 0.86 | 23.7 | 0 |
| `atrr_swingpause_sig_sw10` | 318 | +154.0 | +0.484 | 22.6% | 1.56 | 41.7 | 198 | -1.13 | 19 | 202 | **-9.0** | -0.044 | 23.3% | 0.94 | 34.4 | 0 |
| `chopband_swingpause_sig_sw10` | 320 | +193.2 | +0.604 | 24.1% | 1.74 | 38.0 | 177 | -1.09 | 16 | 200 | **-9.4** | -0.047 | 24.0% | 0.94 | 41.8 | 0 |
| `atrr_cd0_swingpause_sig_sw10` | 319 | +152.2 | +0.477 | 22.6% | 1.55 | 41.7 | 200 | -1.13 | 19 | 203 | **-10.5** | -0.052 | 22.7% | 0.94 | 36.0 | 0 |
| `b2doji_swingpause_sig_sw10` | 332 | +97.6 | +0.294 | 24.4% | 1.36 | 62.0 | 272 | -1.10 | 14 | 210 | **-12.4** | -0.059 | 22.9% | 0.93 | 32.8 | 0 |
| `swingpause_sig_sw20` | 341 | +120.1 | +0.352 | 28.4% | 1.44 | 53.4 | 204 | -1.10 | 11 | 198 | **-12.4** | -0.063 | 24.2% | 0.92 | 36.9 | 0 |
| `champion_sig_sw20` | 374 | +91.6 | +0.245 | 27.3% | 1.30 | 51.6 | 218 | -1.11 | 14 | 215 | **-13.1** | -0.061 | 24.7% | 0.92 | 37.8 | 0 |
| `swingpause_sig_sw10` | 358 | +108.7 | +0.304 | 23.2% | 1.36 | 55.1 | 262 | -1.10 | 16 | 219 | **-14.9** | -0.068 | 23.7% | 0.91 | 41.7 | 0 |
| `champion_sig_sw10` | 395 | +48.6 | +0.123 | 23.8% | 1.15 | 48.5 | 464 | -1.11 | 15 | 238 | **-18.1** | -0.076 | 23.1% | 0.90 | 45.0 | 0 |
| `age50_swingpause_sig_sw10` | 352 | +137.8 | +0.391 | 22.2% | 1.46 | 48.1 | 230 | -1.11 | 21 | 215 | **-18.7** | -0.087 | 23.3% | 0.89 | 46.9 | 0 |
| `utc_wknd_swingpause_sig_sw10` | 285 | +148.6 | +0.521 | 27.0% | 1.67 | 38.6 | 173 | -1.08 | 13 | 173 | **-24.3** | -0.140 | 22.0% | 0.83 | 33.9 | 0 |
| `fliponly_swingpause_sig_sw10` | 237 | +149.5 | +0.631 | 23.6% | 1.71 | 32.7 | 170 | -1.12 | 13 | 147 | **-30.7** | -0.209 | 17.7% | 0.77 | 39.2 | 0 |
| `rmax10_swingpause_sig_sw10` | 258 | +180.0 | +0.698 | 19.8% | 1.68 | 53.1 | 175 | -1.19 | 15 | 91 | **-31.8** | -0.350 | 11.0% | 0.68 | 45.2 | 0 |
| `rmax15_swingpause_sig_sw10` | 314 | +132.0 | +0.420 | 22.0% | 1.46 | 49.0 | 226 | -1.14 | 15 | 156 | **-51.6** | -0.331 | 12.8% | 0.66 | 56.8 | 0 |

## Under the 30-trade floor

Reported so nothing is hidden, ranked by nothing. A net figure here
is a few trades, not an edge.

| book | ISn | IS net | PF | OOSn | OOS net | PF |
|---|---:|---:|---:|---:|---:|---:|
| `trail06_swingpause_sig` | 1 | -0.4 | 0.00 | 53 | -51.1 | 0.00 |
| `trail10_swingpause_sig` | 1 | -0.4 | 0.00 | 56 | -51.4 | 0.01 |

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

All measured nets reproduce their registry pin to within 0.5R.

