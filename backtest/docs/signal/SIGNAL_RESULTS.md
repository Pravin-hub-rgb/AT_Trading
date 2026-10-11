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
| signal books measured | 14 |
| quarantined look-ahead, not run | 3 |
| ranked (both eras, n >= 30) | 12 |
| **positive in BOTH eras** | **11** |
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
| `fsent_sig_full` | 248 | +340.7 | +1.374 | 39.5% | 3.15 | 12.3 | 88 | -1.03 | 10 | 155 | **+170.6** | +1.101 | 45.2% | 3.00 | 7.8 | 70 |
| `fsent_sig_trail_delay1` | 214 | +435.1 | +2.033 | 32.2% | 3.92 | 13.4 | 95 | -1.05 | 13 | 125 | **+161.4** | +1.291 | 40.8% | 3.10 | 8.4 | 84 |
| `fsent_sig_fs_mom` | 249 | +291.2 | +1.170 | 37.3% | 3.02 | 11.5 | 94 | -0.53 | 11 | 152 | **+154.3** | +1.016 | 39.5% | 3.17 | 9.5 | 76 |
| `fsent_sig_wk_pause_short` | 304 | +214.2 | +0.705 | 35.2% | 2.19 | 11.1 | 96 | -0.60 | 11 | 182 | **+140.1** | +0.770 | 36.3% | 2.55 | 9.5 | 71 |
| `fsent_sig_half_crossed` | 98 | +368.6 | +3.762 | 35.7% | 6.78 | 8.8 | 84 | -1.00 | 9 | 64 | **+123.9** | +1.937 | 40.6% | 4.26 | 8.1 | 65 |
| `fsent_sig_decay_crossed` | 103 | +219.5 | +2.131 | 44.7% | 4.41 | 8.6 | 84 | -1.04 | 8 | 69 | **+113.1** | +1.639 | 47.8% | 4.01 | 7.1 | 57 |
| `fsent_sig_sw10_short` | 372 | +184.9 | +0.497 | 32.5% | 1.82 | 17.2 | 106 | -0.60 | 12 | 248 | **+107.3** | +0.433 | 29.4% | 1.73 | 12.8 | 113 |
| `fsent_sig_sw20_short` | 347 | +207.0 | +0.597 | 35.2% | 2.02 | 20.5 | 84 | -0.55 | 15 | 205 | **+95.1** | +0.464 | 30.2% | 1.80 | 12.1 | 106 |
| `fsent_sig_sw20_short_wr` | 347 | +207.0 | +0.597 | 35.2% | 2.02 | 20.5 | 84 | -0.55 | 15 | 205 | **+95.1** | +0.464 | 30.2% | 1.80 | 12.1 | 106 |
| `fsent_sig_sw10_long` | 355 | +118.2 | +0.333 | 32.4% | 1.55 | 22.9 | 143 | -0.55 | 10 | 228 | **+86.2** | +0.378 | 30.3% | 1.66 | 12.0 | 105 |
| `fsent_both_trail_half` | 258 | +75.8 | +0.294 | 27.1% | 1.42 | 28.7 | 211 | -1.04 | 14 | 145 | **+68.5** | +0.472 | 29.7% | 1.74 | 13.2 | 156 |
| `skipwin1_sig_sw10` | 142 | -49.1 | -0.346 | 20.4% | 0.60 | 51.4 | 0 | -1.11 | 14 | 91 | **-2.9** | -0.031 | 23.1% | 0.96 | 24.7 | 0 |

## Under the 30-trade floor

Reported so nothing is hidden, ranked by nothing. A net figure here
is a few trades, not an edge.

| book | ISn | IS net | PF | OOSn | OOS net | PF |
|---|---:|---:|---:|---:|---:|---:|
| `trail06_swingpause_sig` | 1 | -0.4 | 0.00 | 38 | -36.5 | 0.01 |
| `trail10_swingpause_sig` | 1 | -0.4 | 0.00 | 41 | -37.2 | 0.02 |

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

