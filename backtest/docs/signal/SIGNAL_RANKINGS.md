# SIGNAL PLANE — two rankings

Generated from `backtest/tests/_signal_metrics.json` by
`backtest/tests/_gen_rankings_doc.py`. Signal plane only
(`max_positions == 1`), both eras, quarantined look-ahead books excluded,
books under 30 trades in either era excluded.

`n` counts CLOSED trades: the registry's net pins exclude positions still
open at the era boundary (mark-to-market r), so `n` here can sit under the
board's n while `net` matches its pin. `n_open` in the source JSON holds
the difference.

## Why two lists

| ranking | favours | hides |
|---|---|---|
| **by total net R** | books that trade often | how good each trade was |
| **by R per trade** | books whose trades are worth more | how many there were |

Both are correct and they disagree, which is the point. Total R rewards
frequency; R per trade rewards quality.

| | count |
|---|---|
| books in both eras, n >= 30 | 12 |
| positive in both eras | 11 |

## 1. Ranked by out-of-sample total net R

`t5%` share of net from the best 5% of trades. `med` median R. `strk` longest losing run.

| # | book | OOSn | **OOS net** | R/trd | wr% | PF | DD | t5% | med | strk | ISn | IS net | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_full` | 155 | **+170.6** | +1.101 | 45.2% | 3.00 | 7.8 | 70 | -0.46 | 5 | 248 | +340.7 | +1.374 |
| 2 | `fsent_sig_trail_delay1` | 125 | **+161.4** | +1.291 | 40.8% | 3.10 | 8.4 | 84 | -1.03 | 6 | 214 | +435.1 | +2.033 |
| 3 | `fsent_sig_fs_mom` | 152 | **+154.3** | +1.016 | 39.5% | 3.17 | 9.5 | 76 | -0.22 | 11 | 249 | +291.2 | +1.170 |
| 4 | `fsent_sig_wk_pause_short` | 182 | **+140.1** | +0.770 | 36.3% | 2.55 | 9.5 | 71 | -0.31 | 8 | 304 | +214.2 | +0.705 |
| 5 | `fsent_sig_half_crossed` | 64 | **+123.9** | +1.937 | 40.6% | 4.26 | 8.1 | 65 | -0.75 | 8 | 98 | +368.6 | +3.762 |
| 6 | `fsent_sig_decay_crossed` | 69 | **+113.1** | +1.639 | 47.8% | 4.01 | 7.1 | 57 | -0.36 | 5 | 103 | +219.5 | +2.131 |
| 7 | `fsent_sig_sw10_short` | 248 | **+107.3** | +0.433 | 29.4% | 1.73 | 12.8 | 113 | -0.61 | 14 | 372 | +184.9 | +0.497 |
| 8 | `fsent_sig_sw20_short` | 205 | **+95.1** | +0.464 | 30.2% | 1.80 | 12.1 | 106 | -0.53 | 13 | 347 | +207.0 | +0.597 |
| 9 | `fsent_sig_sw20_short_wr` | 205 | **+95.1** | +0.464 | 30.2% | 1.80 | 12.1 | 106 | -0.53 | 13 | 347 | +207.0 | +0.597 |
| 10 | `fsent_sig_sw10_long` | 228 | **+86.2** | +0.378 | 30.3% | 1.66 | 12.0 | 105 | -0.49 | 12 | 355 | +118.2 | +0.333 |
| 11 | `fsent_both_trail_half` | 145 | **+68.5** | +0.472 | 29.7% | 1.74 | 13.2 | 156 | -1.03 | 10 | 258 | +75.8 | +0.294 |
| 12 | `skipwin1_sig_sw10` | 91 | **-2.9** | -0.031 | 23.1% | 0.96 | 24.7 | 0 | -1.06 | 13 | 142 | -49.1 | -0.346 |

## 2. Ranked by out-of-sample R per trade

Same books, same eras, re-sorted. A book here may have far less total R
than the book above it and still be worth more — it just needs fewer
trades to earn it.

| # | book | OOSn | **OOS R/trd** | OOS net | wr% | PF | DD | t5% | med | strk | ISn | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_half_crossed` | 64 | **+1.937** | +123.9 | 40.6% | 4.26 | 8.1 | 65 | -0.75 | 8 | 98 | +3.762 |
| 2 | `fsent_sig_decay_crossed` | 69 | **+1.639** | +113.1 | 47.8% | 4.01 | 7.1 | 57 | -0.36 | 5 | 103 | +2.131 |
| 3 | `fsent_sig_trail_delay1` | 125 | **+1.291** | +161.4 | 40.8% | 3.10 | 8.4 | 84 | -1.03 | 6 | 214 | +2.033 |
| 4 | `fsent_sig_full` | 155 | **+1.101** | +170.6 | 45.2% | 3.00 | 7.8 | 70 | -0.46 | 5 | 248 | +1.374 |
| 5 | `fsent_sig_fs_mom` | 152 | **+1.016** | +154.3 | 39.5% | 3.17 | 9.5 | 76 | -0.22 | 11 | 249 | +1.170 |
| 6 | `fsent_sig_wk_pause_short` | 182 | **+0.770** | +140.1 | 36.3% | 2.55 | 9.5 | 71 | -0.31 | 8 | 304 | +0.705 |
| 7 | `fsent_both_trail_half` | 145 | **+0.472** | +68.5 | 29.7% | 1.74 | 13.2 | 156 | -1.03 | 10 | 258 | +0.294 |
| 8 | `fsent_sig_sw20_short` | 205 | **+0.464** | +95.1 | 30.2% | 1.80 | 12.1 | 106 | -0.53 | 13 | 347 | +0.597 |
| 9 | `fsent_sig_sw20_short_wr` | 205 | **+0.464** | +95.1 | 30.2% | 1.80 | 12.1 | 106 | -0.53 | 13 | 347 | +0.597 |
| 10 | `fsent_sig_sw10_short` | 248 | **+0.433** | +107.3 | 29.4% | 1.73 | 12.8 | 113 | -0.61 | 14 | 372 | +0.497 |
| 11 | `fsent_sig_sw10_long` | 228 | **+0.378** | +86.2 | 30.3% | 1.66 | 12.0 | 105 | -0.49 | 12 | 355 | +0.333 |
| 12 | `skipwin1_sig_sw10` | 91 | **-0.031** | -2.9 | 23.1% | 0.96 | 24.7 | 0 | -1.06 | 13 | 142 | -0.346 |

## Where the two rankings disagree

| | books |
|---|---|
| top 10 by net only | `fsent_sig_sw10_long` |
| top 10 by R/trade only | `fsent_both_trail_half` |
| in both | `fsent_sig_full`, `fsent_sig_trail_delay1`, `fsent_sig_fs_mom`, `fsent_sig_wk_pause_short`, `fsent_sig_half_crossed`, `fsent_sig_decay_crossed`, `fsent_sig_sw10_short`, `fsent_sig_sw20_short`, `fsent_sig_sw20_short_wr` |

Anything in the second row earns its R with far less trading. Anything in
the first earns its R by trading more, at a lower rate per trade.

## Rank movement, total net to R per trade

| book | rank by net | rank by R/trd | move |
|---|--:|--:|--:|
| `fsent_both_trail_half` | 11 | 7 | +4 |
| `fsent_sig_decay_crossed` | 6 | 2 | +4 |
| `fsent_sig_half_crossed` | 5 | 1 | +4 |
| `fsent_sig_sw20_short` | 8 | 8 | 0 |
| `fsent_sig_sw20_short_wr` | 9 | 9 | 0 |
| `skipwin1_sig_sw10` | 12 | 12 | 0 |
| `fsent_sig_sw10_long` | 10 | 11 | -1 |
| `fsent_sig_trail_delay1` | 2 | 3 | -1 |
| `fsent_sig_fs_mom` | 3 | 5 | -2 |
| `fsent_sig_wk_pause_short` | 4 | 6 | -2 |
| `fsent_sig_full` | 1 | 4 | -3 |
| `fsent_sig_sw10_short` | 7 | 10 | -3 |

A positive move means the book looks better when you ask what each trade
is worth than when you ask what the book made in total.

