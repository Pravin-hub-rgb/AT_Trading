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
| books in both eras, n >= 30 | 44 |
| positive in both eras | 21 |

## 1. Ranked by out-of-sample total net R

`t5%` share of net from the best 5% of trades. `med` median R. `strk` longest losing run.

| # | book | OOSn | **OOS net** | R/trd | wr% | PF | DD | t5% | med | strk | ISn | IS net | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_full` | 152 | **+190.9** | +1.256 | 45.4% | 3.35 | 7.0 | 66 | -0.34 | 5 | 234 | +291.0 | +1.244 |
| 2 | `fsent_sig_fs_mom` | 152 | **+165.6** | +1.090 | 40.1% | 3.31 | 9.1 | 75 | -0.20 | 7 | 235 | +262.3 | +1.116 |
| 3 | `fsent_sig_wk_pause_short` | 179 | **+128.8** | +0.719 | 35.2% | 2.41 | 10.5 | 73 | -0.32 | 12 | 302 | +206.9 | +0.685 |
| 4 | `fsent_sig_sw10_short` | 239 | **+100.9** | +0.422 | 31.0% | 1.72 | 11.8 | 110 | -0.61 | 10 | 368 | +174.3 | +0.474 |
| 5 | `fsent_sig_sw20_short` | 203 | **+95.0** | +0.468 | 31.5% | 1.81 | 10.2 | 107 | -0.53 | 10 | 343 | +146.9 | +0.428 |
| 6 | `fsent_sig_sw20_short_wr` | 203 | **+95.0** | +0.468 | 31.5% | 1.81 | 10.2 | 107 | -0.53 | 10 | 343 | +146.9 | +0.428 |
| 7 | `fsent_sig_sw10_long` | 229 | **+81.5** | +0.356 | 30.1% | 1.63 | 13.5 | 107 | -0.50 | 10 | 355 | +116.4 | +0.328 |
| 8 | `wage20_swingpause_sig_sw10` | 143 | **+48.5** | +0.340 | 28.0% | 1.45 | 23.6 | 159 | -1.06 | 12 | 234 | +209.5 | +0.895 |
| 9 | `wage10_swingpause_wskip_sig_sw10` | 158 | **+35.6** | +0.226 | 26.6% | 1.29 | 25.8 | 212 | -1.07 | 12 | 262 | +270.8 | +1.034 |
| 10 | `fullstack_swingpause_sig_sw10` | 149 | **+31.2** | +0.210 | 25.5% | 1.26 | 31.3 | 242 | -1.08 | 13 | 225 | +243.8 | +1.084 |
| 11 | `wage16_swingpause_sig_sw10` | 147 | **+31.0** | +0.211 | 26.5% | 1.27 | 26.2 | 244 | -1.07 | 15 | 246 | +256.7 | +1.044 |
| 12 | `curfew624_swingpause_sig_sw10` | 149 | **+30.3** | +0.203 | 26.2% | 1.27 | 25.3 | 254 | -1.06 | 12 | 250 | +176.6 | +0.706 |
| 13 | `wage8_swingpause_sig_sw10` | 161 | **+30.3** | +0.188 | 26.1% | 1.24 | 29.9 | 273 | -1.07 | 12 | 265 | +250.4 | +0.945 |
| 14 | `nowknd_sig_sw10` | 192 | **+27.0** | +0.141 | 25.5% | 1.18 | 27.3 | 337 | -1.06 | 12 | 321 | +107.6 | +0.335 |
| 15 | `fullstack_wage10_cd0_sig_sw10` | 139 | **+26.1** | +0.188 | 24.5% | 1.23 | 35.0 | 262 | -1.09 | 13 | 199 | +273.2 | +1.373 |
| 16 | `wage24_swingpause_sig_sw10` | 136 | **+26.0** | +0.192 | 25.7% | 1.25 | 30.2 | 268 | -1.07 | 12 | 220 | +225.2 | +1.024 |
| 17 | `nowknd_swingpause_sig_sw10` | 174 | **+24.6** | +0.141 | 25.3% | 1.18 | 23.1 | 336 | -1.06 | 12 | 295 | +205.2 | +0.696 |
| 18 | `utcsat_swingpause_sig_sw10` | 198 | **+22.3** | +0.113 | 27.3% | 1.15 | 20.7 | 359 | -1.07 | 10 | 323 | +134.2 | +0.416 |
| 19 | `fsswing_sig_sw10` | 237 | **+12.6** | +0.053 | 26.2% | 1.07 | 29.4 | 704 | -1.06 | 11 | 404 | +31.2 | +0.077 |
| 20 | `wage12_swingpause_sig_sw10` | 155 | **+12.0** | +0.078 | 24.5% | 1.10 | 30.8 | 604 | -1.07 | 15 | 259 | +267.3 | +1.032 |
| 21 | `fsswing_sig_sw20` | 211 | **+0.2** | +0.001 | 26.5% | 1.00 | 30.5 | 35760 | -1.05 | 10 | 384 | +98.4 | +0.256 |
| 22 | `chopband_atrr_swingpause_sig_sw10` | 177 | **-4.2** | -0.024 | 23.2% | 0.97 | 42.8 | 0 | -1.08 | 23 | 269 | +134.4 | +0.499 |
| 23 | `bm05_swingpause_sig_sw10` | 204 | **-4.7** | -0.023 | 24.5% | 0.97 | 34.2 | 0 | -1.06 | 15 | 336 | +106.5 | +0.317 |
| 24 | `atrr_swingpause_sig_sw20` | 177 | **-4.9** | -0.028 | 25.4% | 0.96 | 32.3 | 0 | -1.08 | 13 | 313 | +118.1 | +0.377 |
| 25 | `wage12_swingpause_sig_sw20` | 172 | **-5.3** | -0.031 | 25.0% | 0.96 | 35.9 | 0 | -1.08 | 15 | 303 | +148.8 | +0.491 |
| 26 | `wage12_swingpause_sig_nowknd_sw10` | 191 | **-5.9** | -0.031 | 23.0% | 0.96 | 40.2 | 0 | -1.08 | 15 | 316 | +202.9 | +0.642 |
| 27 | `chopband_atrr_swingpause_sig_sw20` | 159 | **-6.8** | -0.043 | 24.5% | 0.95 | 43.2 | 0 | -1.08 | 24 | 277 | +109.3 | +0.394 |
| 28 | `chopband_swingpause_sig_sw20` | 181 | **-6.8** | -0.037 | 24.9% | 0.95 | 37.3 | 0 | -1.06 | 15 | 309 | +91.0 | +0.295 |
| 29 | `skipwinhalt_sig_sw10` | 159 | **-7.0** | -0.044 | 22.6% | 0.94 | 31.5 | 0 | -1.06 | 13 | 276 | +37.7 | +0.137 |
| 30 | `chopband_swingpause_sig_sw10` | 197 | **-8.1** | -0.041 | 24.4% | 0.95 | 40.5 | 0 | -1.06 | 16 | 320 | +183.7 | +0.574 |
| 31 | `atrr_swingpause_sig_sw10` | 198 | **-9.4** | -0.048 | 23.7% | 0.94 | 29.4 | 0 | -1.08 | 13 | 316 | +150.8 | +0.477 |
| 32 | `causalsl_swingpause_sig_sw10` | 213 | **-9.6** | -0.045 | 24.4% | 0.94 | 26.3 | 0 | -1.03 | 11 | 351 | +112.0 | +0.319 |
| 33 | `swingpause_sig_sw20` | 193 | **-10.7** | -0.056 | 24.4% | 0.93 | 30.3 | 0 | -1.06 | 13 | 342 | +118.0 | +0.345 |
| 34 | `b2doji_swingpause_sig_sw10` | 207 | **-12.7** | -0.061 | 22.7% | 0.92 | 35.1 | 0 | -1.06 | 15 | 335 | +119.5 | +0.357 |
| 35 | `champion_sig_sw20` | 208 | **-13.0** | -0.063 | 25.0% | 0.92 | 32.3 | 0 | -1.06 | 13 | 377 | +89.3 | +0.237 |
| 36 | `champion_sig_sw10` | 231 | **-16.3** | -0.071 | 23.4% | 0.91 | 41.7 | 0 | -1.06 | 11 | 396 | +37.8 | +0.096 |
| 37 | `atrr_cd0_swingpause_sig_sw10` | 198 | **-16.8** | -0.085 | 22.7% | 0.90 | 33.9 | 0 | -1.08 | 13 | 317 | +149.0 | +0.470 |
| 38 | `swingpause_sig_sw10` | 214 | **-19.7** | -0.092 | 23.8% | 0.88 | 37.0 | 0 | -1.07 | 12 | 356 | +137.5 | +0.386 |
| 39 | `age50_swingpause_sig_sw10` | 211 | **-23.9** | -0.113 | 23.2% | 0.86 | 41.2 | 0 | -1.08 | 14 | 350 | +133.2 | +0.381 |
| 40 | `skipwin1_sig_sw10` | 82 | **-24.0** | -0.293 | 15.9% | 0.65 | 27.5 | 0 | -1.07 | 13 | 139 | -41.7 | -0.300 |
| 41 | `utc_wknd_swingpause_sig_sw10` | 172 | **-26.3** | -0.153 | 21.5% | 0.81 | 35.6 | 0 | -1.07 | 13 | 285 | +139.9 | +0.491 |
| 42 | `rmax10_swingpause_sig_sw10` | 88 | **-32.6** | -0.370 | 10.2% | 0.66 | 42.6 | 0 | -1.20 | 33 | 255 | +184.4 | +0.723 |
| 43 | `fliponly_swingpause_sig_sw10` | 146 | **-34.2** | -0.234 | 17.1% | 0.74 | 42.7 | 0 | -1.09 | 12 | 237 | +140.8 | +0.594 |
| 44 | `rmax15_swingpause_sig_sw10` | 154 | **-54.2** | -0.352 | 12.3% | 0.65 | 59.4 | 0 | -1.12 | 19 | 310 | +126.6 | +0.408 |

## 2. Ranked by out-of-sample R per trade

Same books, same eras, re-sorted. A book here may have far less total R
than the book above it and still be worth more — it just needs fewer
trades to earn it.

| # | book | OOSn | **OOS R/trd** | OOS net | wr% | PF | DD | t5% | med | strk | ISn | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_full` | 152 | **+1.256** | +190.9 | 45.4% | 3.35 | 7.0 | 66 | -0.34 | 5 | 234 | +1.244 |
| 2 | `fsent_sig_fs_mom` | 152 | **+1.090** | +165.6 | 40.1% | 3.31 | 9.1 | 75 | -0.20 | 7 | 235 | +1.116 |
| 3 | `fsent_sig_wk_pause_short` | 179 | **+0.719** | +128.8 | 35.2% | 2.41 | 10.5 | 73 | -0.32 | 12 | 302 | +0.685 |
| 4 | `fsent_sig_sw20_short` | 203 | **+0.468** | +95.0 | 31.5% | 1.81 | 10.2 | 107 | -0.53 | 10 | 343 | +0.428 |
| 5 | `fsent_sig_sw20_short_wr` | 203 | **+0.468** | +95.0 | 31.5% | 1.81 | 10.2 | 107 | -0.53 | 10 | 343 | +0.428 |
| 6 | `fsent_sig_sw10_short` | 239 | **+0.422** | +100.9 | 31.0% | 1.72 | 11.8 | 110 | -0.61 | 10 | 368 | +0.474 |
| 7 | `fsent_sig_sw10_long` | 229 | **+0.356** | +81.5 | 30.1% | 1.63 | 13.5 | 107 | -0.50 | 10 | 355 | +0.328 |
| 8 | `wage20_swingpause_sig_sw10` | 143 | **+0.340** | +48.5 | 28.0% | 1.45 | 23.6 | 159 | -1.06 | 12 | 234 | +0.895 |
| 9 | `wage10_swingpause_wskip_sig_sw10` | 158 | **+0.226** | +35.6 | 26.6% | 1.29 | 25.8 | 212 | -1.07 | 12 | 262 | +1.034 |
| 10 | `wage16_swingpause_sig_sw10` | 147 | **+0.211** | +31.0 | 26.5% | 1.27 | 26.2 | 244 | -1.07 | 15 | 246 | +1.044 |
| 11 | `fullstack_swingpause_sig_sw10` | 149 | **+0.210** | +31.2 | 25.5% | 1.26 | 31.3 | 242 | -1.08 | 13 | 225 | +1.084 |
| 12 | `curfew624_swingpause_sig_sw10` | 149 | **+0.203** | +30.3 | 26.2% | 1.27 | 25.3 | 254 | -1.06 | 12 | 250 | +0.706 |
| 13 | `wage24_swingpause_sig_sw10` | 136 | **+0.192** | +26.0 | 25.7% | 1.25 | 30.2 | 268 | -1.07 | 12 | 220 | +1.024 |
| 14 | `fullstack_wage10_cd0_sig_sw10` | 139 | **+0.188** | +26.1 | 24.5% | 1.23 | 35.0 | 262 | -1.09 | 13 | 199 | +1.373 |
| 15 | `wage8_swingpause_sig_sw10` | 161 | **+0.188** | +30.3 | 26.1% | 1.24 | 29.9 | 273 | -1.07 | 12 | 265 | +0.945 |
| 16 | `nowknd_swingpause_sig_sw10` | 174 | **+0.141** | +24.6 | 25.3% | 1.18 | 23.1 | 336 | -1.06 | 12 | 295 | +0.696 |
| 17 | `nowknd_sig_sw10` | 192 | **+0.141** | +27.0 | 25.5% | 1.18 | 27.3 | 337 | -1.06 | 12 | 321 | +0.335 |
| 18 | `utcsat_swingpause_sig_sw10` | 198 | **+0.113** | +22.3 | 27.3% | 1.15 | 20.7 | 359 | -1.07 | 10 | 323 | +0.416 |
| 19 | `wage12_swingpause_sig_sw10` | 155 | **+0.078** | +12.0 | 24.5% | 1.10 | 30.8 | 604 | -1.07 | 15 | 259 | +1.032 |
| 20 | `fsswing_sig_sw10` | 237 | **+0.053** | +12.6 | 26.2% | 1.07 | 29.4 | 704 | -1.06 | 11 | 404 | +0.077 |
| 21 | `fsswing_sig_sw20` | 211 | **+0.001** | +0.2 | 26.5% | 1.00 | 30.5 | 35760 | -1.05 | 10 | 384 | +0.256 |
| 22 | `bm05_swingpause_sig_sw10` | 204 | **-0.023** | -4.7 | 24.5% | 0.97 | 34.2 | 0 | -1.06 | 15 | 336 | +0.317 |
| 23 | `chopband_atrr_swingpause_sig_sw10` | 177 | **-0.024** | -4.2 | 23.2% | 0.97 | 42.8 | 0 | -1.08 | 23 | 269 | +0.499 |
| 24 | `atrr_swingpause_sig_sw20` | 177 | **-0.028** | -4.9 | 25.4% | 0.96 | 32.3 | 0 | -1.08 | 13 | 313 | +0.377 |
| 25 | `wage12_swingpause_sig_sw20` | 172 | **-0.031** | -5.3 | 25.0% | 0.96 | 35.9 | 0 | -1.08 | 15 | 303 | +0.491 |
| 26 | `wage12_swingpause_sig_nowknd_sw10` | 191 | **-0.031** | -5.9 | 23.0% | 0.96 | 40.2 | 0 | -1.08 | 15 | 316 | +0.642 |
| 27 | `chopband_swingpause_sig_sw20` | 181 | **-0.037** | -6.8 | 24.9% | 0.95 | 37.3 | 0 | -1.06 | 15 | 309 | +0.295 |
| 28 | `chopband_swingpause_sig_sw10` | 197 | **-0.041** | -8.1 | 24.4% | 0.95 | 40.5 | 0 | -1.06 | 16 | 320 | +0.574 |
| 29 | `chopband_atrr_swingpause_sig_sw20` | 159 | **-0.043** | -6.8 | 24.5% | 0.95 | 43.2 | 0 | -1.08 | 24 | 277 | +0.394 |
| 30 | `skipwinhalt_sig_sw10` | 159 | **-0.044** | -7.0 | 22.6% | 0.94 | 31.5 | 0 | -1.06 | 13 | 276 | +0.137 |
| 31 | `causalsl_swingpause_sig_sw10` | 213 | **-0.045** | -9.6 | 24.4% | 0.94 | 26.3 | 0 | -1.03 | 11 | 351 | +0.319 |
| 32 | `atrr_swingpause_sig_sw10` | 198 | **-0.048** | -9.4 | 23.7% | 0.94 | 29.4 | 0 | -1.08 | 13 | 316 | +0.477 |
| 33 | `swingpause_sig_sw20` | 193 | **-0.056** | -10.7 | 24.4% | 0.93 | 30.3 | 0 | -1.06 | 13 | 342 | +0.345 |
| 34 | `b2doji_swingpause_sig_sw10` | 207 | **-0.061** | -12.7 | 22.7% | 0.92 | 35.1 | 0 | -1.06 | 15 | 335 | +0.357 |
| 35 | `champion_sig_sw20` | 208 | **-0.063** | -13.0 | 25.0% | 0.92 | 32.3 | 0 | -1.06 | 13 | 377 | +0.237 |
| 36 | `champion_sig_sw10` | 231 | **-0.071** | -16.3 | 23.4% | 0.91 | 41.7 | 0 | -1.06 | 11 | 396 | +0.096 |
| 37 | `atrr_cd0_swingpause_sig_sw10` | 198 | **-0.085** | -16.8 | 22.7% | 0.90 | 33.9 | 0 | -1.08 | 13 | 317 | +0.470 |
| 38 | `swingpause_sig_sw10` | 214 | **-0.092** | -19.7 | 23.8% | 0.88 | 37.0 | 0 | -1.07 | 12 | 356 | +0.386 |
| 39 | `age50_swingpause_sig_sw10` | 211 | **-0.113** | -23.9 | 23.2% | 0.86 | 41.2 | 0 | -1.08 | 14 | 350 | +0.381 |
| 40 | `utc_wknd_swingpause_sig_sw10` | 172 | **-0.153** | -26.3 | 21.5% | 0.81 | 35.6 | 0 | -1.07 | 13 | 285 | +0.491 |
| 41 | `fliponly_swingpause_sig_sw10` | 146 | **-0.234** | -34.2 | 17.1% | 0.74 | 42.7 | 0 | -1.09 | 12 | 237 | +0.594 |
| 42 | `skipwin1_sig_sw10` | 82 | **-0.293** | -24.0 | 15.9% | 0.65 | 27.5 | 0 | -1.07 | 13 | 139 | -0.300 |
| 43 | `rmax15_swingpause_sig_sw10` | 154 | **-0.352** | -54.2 | 12.3% | 0.65 | 59.4 | 0 | -1.12 | 19 | 310 | +0.408 |
| 44 | `rmax10_swingpause_sig_sw10` | 88 | **-0.370** | -32.6 | 10.2% | 0.66 | 42.6 | 0 | -1.20 | 33 | 255 | +0.723 |

## Where the two rankings disagree

| | books |
|---|---|
| top 10 by net only | `fullstack_swingpause_sig_sw10` |
| top 10 by R/trade only | `wage16_swingpause_sig_sw10` |
| in both | `fsent_sig_full`, `fsent_sig_fs_mom`, `fsent_sig_wk_pause_short`, `fsent_sig_sw10_short`, `fsent_sig_sw20_short`, `fsent_sig_sw20_short_wr`, `fsent_sig_sw10_long`, `wage20_swingpause_sig_sw10`, `wage10_swingpause_wskip_sig_sw10` |

Anything in the second row earns its R with far less trading. Anything in
the first earns its R by trading more, at a lower rate per trade.

## Rank movement, total net to R per trade

| book | rank by net | rank by R/trd | move |
|---|--:|--:|--:|
| `wage24_swingpause_sig_sw10` | 16 | 13 | +3 |
| `chopband_swingpause_sig_sw10` | 30 | 28 | +2 |
| `fliponly_swingpause_sig_sw10` | 43 | 41 | +2 |
| `bm05_swingpause_sig_sw10` | 23 | 22 | +1 |
| `causalsl_swingpause_sig_sw10` | 32 | 31 | +1 |
| `chopband_swingpause_sig_sw20` | 28 | 27 | +1 |
| `fsent_sig_sw20_short` | 5 | 4 | +1 |
| `fsent_sig_sw20_short_wr` | 6 | 5 | +1 |
| `fullstack_wage10_cd0_sig_sw10` | 15 | 14 | +1 |
| `nowknd_swingpause_sig_sw10` | 17 | 16 | +1 |
| `rmax15_swingpause_sig_sw10` | 44 | 43 | +1 |
| `utc_wknd_swingpause_sig_sw10` | 41 | 40 | +1 |

A positive move means the book looks better when you ask what each trade
is worth than when you ask what the book made in total.

