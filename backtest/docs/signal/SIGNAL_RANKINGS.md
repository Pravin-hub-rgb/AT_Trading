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
| books in both eras, n >= 30 | 48 |
| positive in both eras | 27 |

## 1. Ranked by out-of-sample total net R

`t5%` share of net from the best 5% of trades. `med` median R. `strk` longest losing run.

| # | book | OOSn | **OOS net** | R/trd | wr% | PF | DD | t5% | med | strk | ISn | IS net | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_full` | 151 | **+194.4** | +1.288 | 46.4% | 3.48 | 7.0 | 65 | -0.29 | 5 | 234 | +295.8 | +1.264 |
| 2 | `fsent_sig_trail_delay1` | 122 | **+182.0** | +1.492 | 41.0% | 3.57 | 7.5 | 76 | -0.86 | 6 | 199 | +418.5 | +2.103 |
| 3 | `fsent_sig_fs_mom` | 153 | **+166.8** | +1.090 | 40.5% | 3.33 | 9.1 | 74 | -0.19 | 7 | 235 | +268.4 | +1.142 |
| 4 | `fsent_sig_half_crossed` | 62 | **+142.1** | +2.292 | 40.3% | 5.00 | 7.3 | 56 | -0.59 | 8 | 97 | +340.9 | +3.514 |
| 5 | `fsent_sig_decay_crossed` | 67 | **+130.3** | +1.944 | 49.3% | 4.78 | 7.4 | 51 | -0.19 | 5 | 104 | +195.6 | +1.881 |
| 6 | `fsent_sig_wk_pause_short` | 180 | **+129.9** | +0.722 | 35.6% | 2.43 | 10.5 | 77 | -0.31 | 12 | 306 | +203.3 | +0.664 |
| 7 | `fsent_sig_sw10_short` | 239 | **+103.3** | +0.432 | 31.4% | 1.75 | 11.8 | 108 | -0.55 | 10 | 373 | +175.4 | +0.470 |
| 8 | `fsent_sig_sw20_short` | 203 | **+97.0** | +0.478 | 31.5% | 1.84 | 8.9 | 104 | -0.53 | 10 | 343 | +146.2 | +0.426 |
| 9 | `fsent_sig_sw20_short_wr` | 203 | **+97.0** | +0.478 | 31.5% | 1.84 | 8.9 | 104 | -0.53 | 10 | 343 | +146.2 | +0.426 |
| 10 | `fsent_both_trail_half` | 141 | **+96.9** | +0.687 | 32.6% | 2.15 | 14.8 | 117 | -0.78 | 7 | 253 | +77.7 | +0.307 |
| 11 | `fsent_sig_sw10_long` | 232 | **+74.2** | +0.320 | 29.3% | 1.55 | 13.3 | 117 | -0.52 | 10 | 353 | +121.2 | +0.343 |
| 12 | `wage20_swingpause_sig_sw10` | 143 | **+48.5** | +0.340 | 28.0% | 1.45 | 23.6 | 159 | -1.06 | 12 | 233 | +202.0 | +0.867 |
| 13 | `nowknd_sig_sw10` | 194 | **+39.9** | +0.206 | 26.8% | 1.27 | 22.8 | 228 | -1.06 | 11 | 319 | +124.2 | +0.389 |
| 14 | `wage10_swingpause_wskip_sig_sw10` | 158 | **+35.6** | +0.226 | 26.6% | 1.29 | 25.8 | 212 | -1.07 | 12 | 261 | +268.9 | +1.030 |
| 15 | `nowknd_swingpause_sig_sw10` | 173 | **+34.6** | +0.200 | 26.6% | 1.26 | 23.0 | 239 | -1.06 | 12 | 292 | +216.3 | +0.741 |
| 16 | `fullstack_swingpause_sig_sw10` | 152 | **+32.0** | +0.211 | 25.7% | 1.27 | 33.8 | 236 | -1.08 | 13 | 229 | +242.4 | +1.059 |
| 17 | `wage16_swingpause_sig_sw10` | 147 | **+31.0** | +0.211 | 26.5% | 1.27 | 26.2 | 244 | -1.07 | 15 | 245 | +249.3 | +1.017 |
| 18 | `curfew624_swingpause_sig_sw10` | 153 | **+30.8** | +0.201 | 26.1% | 1.26 | 26.6 | 250 | -1.06 | 12 | 256 | +181.0 | +0.707 |
| 19 | `wage8_swingpause_sig_sw10` | 161 | **+30.3** | +0.188 | 26.1% | 1.24 | 29.9 | 273 | -1.07 | 12 | 263 | +250.3 | +0.952 |
| 20 | `fullstack_wage10_cd0_sig_sw10` | 139 | **+26.1** | +0.188 | 24.5% | 1.23 | 35.0 | 262 | -1.09 | 13 | 199 | +273.2 | +1.373 |
| 21 | `wage24_swingpause_sig_sw10` | 136 | **+26.0** | +0.192 | 25.7% | 1.25 | 30.2 | 268 | -1.07 | 12 | 219 | +224.0 | +1.023 |
| 22 | `utcsat_swingpause_sig_sw10` | 203 | **+13.6** | +0.067 | 26.6% | 1.09 | 24.4 | 632 | -1.07 | 10 | 327 | +94.3 | +0.288 |
| 23 | `wage12_swingpause_sig_sw10` | 155 | **+12.0** | +0.078 | 24.5% | 1.10 | 30.8 | 604 | -1.07 | 15 | 258 | +266.1 | +1.031 |
| 24 | `fsswing_sig_sw10` | 245 | **+11.2** | +0.046 | 26.1% | 1.06 | 34.6 | 844 | -1.06 | 11 | 404 | +42.5 | +0.105 |
| 25 | `causalsl_swingpause_sig_sw10` | 218 | **+7.0** | +0.032 | 24.3% | 1.04 | 26.4 | 1305 | -1.01 | 11 | 355 | +71.9 | +0.203 |
| 26 | `chopband_swingpause_sig_sw20` | 182 | **+0.4** | +0.002 | 25.3% | 1.00 | 36.3 | 17831 | -1.05 | 15 | 314 | +86.8 | +0.277 |
| 27 | `fsswing_sig_sw20` | 218 | **+0.4** | +0.002 | 25.7% | 1.00 | 36.0 | 17430 | -1.06 | 11 | 382 | +99.2 | +0.260 |
| 28 | `chopband_atrr_swingpause_sig_sw10` | 181 | **-2.0** | -0.011 | 23.2% | 0.99 | 43.9 | 0 | -1.08 | 24 | 270 | +120.7 | +0.447 |
| 29 | `bm05_swingpause_sig_sw10` | 209 | **-3.8** | -0.018 | 24.4% | 0.98 | 37.9 | 0 | -1.06 | 15 | 336 | +83.1 | +0.247 |
| 30 | `skipwinhalt_sig_sw10` | 162 | **-4.2** | -0.026 | 22.8% | 0.97 | 34.0 | 0 | -1.07 | 13 | 280 | -1.5 | -0.005 |
| 31 | `chopband_atrr_swingpause_sig_sw20` | 162 | **-5.2** | -0.032 | 24.7% | 0.96 | 43.0 | 0 | -1.07 | 24 | 281 | +102.1 | +0.363 |
| 32 | `wage12_swingpause_sig_sw20` | 172 | **-5.3** | -0.031 | 25.0% | 0.96 | 35.9 | 0 | -1.08 | 15 | 302 | +147.6 | +0.489 |
| 33 | `wage12_swingpause_sig_nowknd_sw10` | 191 | **-5.9** | -0.031 | 23.0% | 0.96 | 40.2 | 0 | -1.08 | 15 | 313 | +205.7 | +0.657 |
| 34 | `atrr_swingpause_sig_sw20` | 181 | **-6.8** | -0.038 | 25.4% | 0.95 | 32.8 | 0 | -1.07 | 14 | 317 | +118.0 | +0.372 |
| 35 | `skipwin1_sig_sw10` | 80 | **-8.7** | -0.108 | 17.5% | 0.86 | 23.7 | 0 | -1.07 | 13 | 142 | -40.3 | -0.284 |
| 36 | `atrr_swingpause_sig_sw10` | 202 | **-9.0** | -0.044 | 23.3% | 0.94 | 34.4 | 0 | -1.08 | 13 | 318 | +154.0 | +0.484 |
| 37 | `chopband_swingpause_sig_sw10` | 200 | **-9.4** | -0.047 | 24.0% | 0.94 | 41.8 | 0 | -1.06 | 17 | 320 | +193.2 | +0.604 |
| 38 | `atrr_cd0_swingpause_sig_sw10` | 203 | **-10.5** | -0.052 | 22.7% | 0.94 | 36.0 | 0 | -1.08 | 14 | 319 | +152.2 | +0.477 |
| 39 | `b2doji_swingpause_sig_sw10` | 210 | **-12.4** | -0.059 | 22.9% | 0.93 | 32.8 | 0 | -1.06 | 17 | 332 | +97.6 | +0.294 |
| 40 | `swingpause_sig_sw20` | 198 | **-12.4** | -0.063 | 24.2% | 0.92 | 36.9 | 0 | -1.06 | 14 | 341 | +120.1 | +0.352 |
| 41 | `champion_sig_sw20` | 215 | **-13.1** | -0.061 | 24.7% | 0.92 | 37.8 | 0 | -1.06 | 13 | 374 | +91.6 | +0.245 |
| 42 | `swingpause_sig_sw10` | 219 | **-14.9** | -0.068 | 23.7% | 0.91 | 41.7 | 0 | -1.07 | 13 | 358 | +108.7 | +0.304 |
| 43 | `champion_sig_sw10` | 238 | **-18.1** | -0.076 | 23.1% | 0.90 | 45.0 | 0 | -1.06 | 11 | 395 | +48.6 | +0.123 |
| 44 | `age50_swingpause_sig_sw10` | 215 | **-18.7** | -0.087 | 23.3% | 0.89 | 46.9 | 0 | -1.08 | 14 | 352 | +137.8 | +0.391 |
| 45 | `utc_wknd_swingpause_sig_sw10` | 173 | **-24.3** | -0.140 | 22.0% | 0.83 | 33.9 | 0 | -1.07 | 13 | 285 | +148.6 | +0.521 |
| 46 | `fliponly_swingpause_sig_sw10` | 147 | **-30.7** | -0.209 | 17.7% | 0.77 | 39.2 | 0 | -1.09 | 13 | 237 | +149.5 | +0.631 |
| 47 | `rmax10_swingpause_sig_sw10` | 91 | **-31.8** | -0.350 | 11.0% | 0.68 | 45.2 | 0 | -1.20 | 35 | 258 | +180.0 | +0.698 |
| 48 | `rmax15_swingpause_sig_sw10` | 156 | **-51.6** | -0.331 | 12.8% | 0.66 | 56.8 | 0 | -1.12 | 19 | 314 | +132.0 | +0.420 |

## 2. Ranked by out-of-sample R per trade

Same books, same eras, re-sorted. A book here may have far less total R
than the book above it and still be worth more — it just needs fewer
trades to earn it.

| # | book | OOSn | **OOS R/trd** | OOS net | wr% | PF | DD | t5% | med | strk | ISn | IS R/trd |
|--:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fsent_sig_half_crossed` | 62 | **+2.292** | +142.1 | 40.3% | 5.00 | 7.3 | 56 | -0.59 | 8 | 97 | +3.514 |
| 2 | `fsent_sig_decay_crossed` | 67 | **+1.944** | +130.3 | 49.3% | 4.78 | 7.4 | 51 | -0.19 | 5 | 104 | +1.881 |
| 3 | `fsent_sig_trail_delay1` | 122 | **+1.492** | +182.0 | 41.0% | 3.57 | 7.5 | 76 | -0.86 | 6 | 199 | +2.103 |
| 4 | `fsent_sig_full` | 151 | **+1.288** | +194.4 | 46.4% | 3.48 | 7.0 | 65 | -0.29 | 5 | 234 | +1.264 |
| 5 | `fsent_sig_fs_mom` | 153 | **+1.090** | +166.8 | 40.5% | 3.33 | 9.1 | 74 | -0.19 | 7 | 235 | +1.142 |
| 6 | `fsent_sig_wk_pause_short` | 180 | **+0.722** | +129.9 | 35.6% | 2.43 | 10.5 | 77 | -0.31 | 12 | 306 | +0.664 |
| 7 | `fsent_both_trail_half` | 141 | **+0.687** | +96.9 | 32.6% | 2.15 | 14.8 | 117 | -0.78 | 7 | 253 | +0.307 |
| 8 | `fsent_sig_sw20_short` | 203 | **+0.478** | +97.0 | 31.5% | 1.84 | 8.9 | 104 | -0.53 | 10 | 343 | +0.426 |
| 9 | `fsent_sig_sw20_short_wr` | 203 | **+0.478** | +97.0 | 31.5% | 1.84 | 8.9 | 104 | -0.53 | 10 | 343 | +0.426 |
| 10 | `fsent_sig_sw10_short` | 239 | **+0.432** | +103.3 | 31.4% | 1.75 | 11.8 | 108 | -0.55 | 10 | 373 | +0.470 |
| 11 | `wage20_swingpause_sig_sw10` | 143 | **+0.340** | +48.5 | 28.0% | 1.45 | 23.6 | 159 | -1.06 | 12 | 233 | +0.867 |
| 12 | `fsent_sig_sw10_long` | 232 | **+0.320** | +74.2 | 29.3% | 1.55 | 13.3 | 117 | -0.52 | 10 | 353 | +0.343 |
| 13 | `wage10_swingpause_wskip_sig_sw10` | 158 | **+0.226** | +35.6 | 26.6% | 1.29 | 25.8 | 212 | -1.07 | 12 | 261 | +1.030 |
| 14 | `wage16_swingpause_sig_sw10` | 147 | **+0.211** | +31.0 | 26.5% | 1.27 | 26.2 | 244 | -1.07 | 15 | 245 | +1.017 |
| 15 | `fullstack_swingpause_sig_sw10` | 152 | **+0.211** | +32.0 | 25.7% | 1.27 | 33.8 | 236 | -1.08 | 13 | 229 | +1.059 |
| 16 | `nowknd_sig_sw10` | 194 | **+0.206** | +39.9 | 26.8% | 1.27 | 22.8 | 228 | -1.06 | 11 | 319 | +0.389 |
| 17 | `curfew624_swingpause_sig_sw10` | 153 | **+0.201** | +30.8 | 26.1% | 1.26 | 26.6 | 250 | -1.06 | 12 | 256 | +0.707 |
| 18 | `nowknd_swingpause_sig_sw10` | 173 | **+0.200** | +34.6 | 26.6% | 1.26 | 23.0 | 239 | -1.06 | 12 | 292 | +0.741 |
| 19 | `wage24_swingpause_sig_sw10` | 136 | **+0.192** | +26.0 | 25.7% | 1.25 | 30.2 | 268 | -1.07 | 12 | 219 | +1.023 |
| 20 | `fullstack_wage10_cd0_sig_sw10` | 139 | **+0.188** | +26.1 | 24.5% | 1.23 | 35.0 | 262 | -1.09 | 13 | 199 | +1.373 |
| 21 | `wage8_swingpause_sig_sw10` | 161 | **+0.188** | +30.3 | 26.1% | 1.24 | 29.9 | 273 | -1.07 | 12 | 263 | +0.952 |
| 22 | `wage12_swingpause_sig_sw10` | 155 | **+0.078** | +12.0 | 24.5% | 1.10 | 30.8 | 604 | -1.07 | 15 | 258 | +1.031 |
| 23 | `utcsat_swingpause_sig_sw10` | 203 | **+0.067** | +13.6 | 26.6% | 1.09 | 24.4 | 632 | -1.07 | 10 | 327 | +0.288 |
| 24 | `fsswing_sig_sw10` | 245 | **+0.046** | +11.2 | 26.1% | 1.06 | 34.6 | 844 | -1.06 | 11 | 404 | +0.105 |
| 25 | `causalsl_swingpause_sig_sw10` | 218 | **+0.032** | +7.0 | 24.3% | 1.04 | 26.4 | 1305 | -1.01 | 11 | 355 | +0.203 |
| 26 | `chopband_swingpause_sig_sw20` | 182 | **+0.002** | +0.4 | 25.3% | 1.00 | 36.3 | 17831 | -1.05 | 15 | 314 | +0.277 |
| 27 | `fsswing_sig_sw20` | 218 | **+0.002** | +0.4 | 25.7% | 1.00 | 36.0 | 17430 | -1.06 | 11 | 382 | +0.260 |
| 28 | `chopband_atrr_swingpause_sig_sw10` | 181 | **-0.011** | -2.0 | 23.2% | 0.99 | 43.9 | 0 | -1.08 | 24 | 270 | +0.447 |
| 29 | `bm05_swingpause_sig_sw10` | 209 | **-0.018** | -3.8 | 24.4% | 0.98 | 37.9 | 0 | -1.06 | 15 | 336 | +0.247 |
| 30 | `skipwinhalt_sig_sw10` | 162 | **-0.026** | -4.2 | 22.8% | 0.97 | 34.0 | 0 | -1.07 | 13 | 280 | -0.005 |
| 31 | `wage12_swingpause_sig_sw20` | 172 | **-0.031** | -5.3 | 25.0% | 0.96 | 35.9 | 0 | -1.08 | 15 | 302 | +0.489 |
| 32 | `wage12_swingpause_sig_nowknd_sw10` | 191 | **-0.031** | -5.9 | 23.0% | 0.96 | 40.2 | 0 | -1.08 | 15 | 313 | +0.657 |
| 33 | `chopband_atrr_swingpause_sig_sw20` | 162 | **-0.032** | -5.2 | 24.7% | 0.96 | 43.0 | 0 | -1.07 | 24 | 281 | +0.363 |
| 34 | `atrr_swingpause_sig_sw20` | 181 | **-0.038** | -6.8 | 25.4% | 0.95 | 32.8 | 0 | -1.07 | 14 | 317 | +0.372 |
| 35 | `atrr_swingpause_sig_sw10` | 202 | **-0.044** | -9.0 | 23.3% | 0.94 | 34.4 | 0 | -1.08 | 13 | 318 | +0.484 |
| 36 | `chopband_swingpause_sig_sw10` | 200 | **-0.047** | -9.4 | 24.0% | 0.94 | 41.8 | 0 | -1.06 | 17 | 320 | +0.604 |
| 37 | `atrr_cd0_swingpause_sig_sw10` | 203 | **-0.052** | -10.5 | 22.7% | 0.94 | 36.0 | 0 | -1.08 | 14 | 319 | +0.477 |
| 38 | `b2doji_swingpause_sig_sw10` | 210 | **-0.059** | -12.4 | 22.9% | 0.93 | 32.8 | 0 | -1.06 | 17 | 332 | +0.294 |
| 39 | `champion_sig_sw20` | 215 | **-0.061** | -13.1 | 24.7% | 0.92 | 37.8 | 0 | -1.06 | 13 | 374 | +0.245 |
| 40 | `swingpause_sig_sw20` | 198 | **-0.063** | -12.4 | 24.2% | 0.92 | 36.9 | 0 | -1.06 | 14 | 341 | +0.352 |
| 41 | `swingpause_sig_sw10` | 219 | **-0.068** | -14.9 | 23.7% | 0.91 | 41.7 | 0 | -1.07 | 13 | 358 | +0.304 |
| 42 | `champion_sig_sw10` | 238 | **-0.076** | -18.1 | 23.1% | 0.90 | 45.0 | 0 | -1.06 | 11 | 395 | +0.123 |
| 43 | `age50_swingpause_sig_sw10` | 215 | **-0.087** | -18.7 | 23.3% | 0.89 | 46.9 | 0 | -1.08 | 14 | 352 | +0.391 |
| 44 | `skipwin1_sig_sw10` | 80 | **-0.108** | -8.7 | 17.5% | 0.86 | 23.7 | 0 | -1.07 | 13 | 142 | -0.284 |
| 45 | `utc_wknd_swingpause_sig_sw10` | 173 | **-0.140** | -24.3 | 22.0% | 0.83 | 33.9 | 0 | -1.07 | 13 | 285 | +0.521 |
| 46 | `fliponly_swingpause_sig_sw10` | 147 | **-0.209** | -30.7 | 17.7% | 0.77 | 39.2 | 0 | -1.09 | 13 | 237 | +0.631 |
| 47 | `rmax15_swingpause_sig_sw10` | 156 | **-0.331** | -51.6 | 12.8% | 0.66 | 56.8 | 0 | -1.12 | 19 | 314 | +0.420 |
| 48 | `rmax10_swingpause_sig_sw10` | 91 | **-0.350** | -31.8 | 11.0% | 0.68 | 45.2 | 0 | -1.20 | 35 | 258 | +0.698 |

## Where the two rankings disagree

| | books |
|---|---|
| top 10 by net only | - |
| top 10 by R/trade only | - |
| in both | `fsent_sig_full`, `fsent_sig_trail_delay1`, `fsent_sig_fs_mom`, `fsent_sig_half_crossed`, `fsent_sig_decay_crossed`, `fsent_sig_wk_pause_short`, `fsent_sig_sw10_short`, `fsent_sig_sw20_short`, `fsent_sig_sw20_short_wr`, `fsent_both_trail_half` |

Anything in the second row earns its R with far less trading. Anything in
the first earns its R by trading more, at a lower rate per trade.

## Rank movement, total net to R per trade

| book | rank by net | rank by R/trd | move |
|---|--:|--:|--:|
| `fsent_both_trail_half` | 10 | 7 | +3 |
| `fsent_sig_decay_crossed` | 5 | 2 | +3 |
| `fsent_sig_half_crossed` | 4 | 1 | +3 |
| `wage16_swingpause_sig_sw10` | 17 | 14 | +3 |
| `champion_sig_sw20` | 41 | 39 | +2 |
| `wage24_swingpause_sig_sw10` | 21 | 19 | +2 |
| `age50_swingpause_sig_sw10` | 44 | 43 | +1 |
| `atrr_cd0_swingpause_sig_sw10` | 38 | 37 | +1 |
| `atrr_swingpause_sig_sw10` | 36 | 35 | +1 |
| `b2doji_swingpause_sig_sw10` | 39 | 38 | +1 |
| `champion_sig_sw10` | 43 | 42 | +1 |
| `chopband_swingpause_sig_sw10` | 37 | 36 | +1 |

A positive move means the book looks better when you ask what each trade
is worth than when you ask what the book made in total.

