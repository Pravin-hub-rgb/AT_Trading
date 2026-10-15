# Selection scorecard

Built 2026-10-15 from `selection_results.json`. Per `docs/learn/finding optimal book.md`:698
- gates first, then a scorecard, deliberately not one combined score.

**sig and multi are never mixed.** `BASELINE.md:63` - "a signal book cannot be
compared against a multi-position book", they are different objects.

Classification is by the `max_positions` param, NOT by name. `fsent_sig_multi_acc`
is filed under multi: its name says sig, its params say 0, and the other bot's own
note records it running up to 7 concurrent positions.

Gates: IS net > 0, OOS net > 0, OOS n >= 100, OOS DD <= 40% of net, no negative
50-trade rolling window in OOS.

`roll20/50/100` are the WORST rolling sum over that window - negative means the
book had a stretch of N consecutive trades in the red. `top5%` is the share of net
carried by the best 5% of trades. `max gap` is the longest run of consecutive
losing trades.

## SIG - 17 books, 7 pass the gates

| book | OOS net | OOS n | OOS R/tr | OOS PF | DD | DD% | ulcer | sortino | roll20 | roll50 | roll100 | %mo+ | worst yr | top5% | max gap | params |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fsent_sig_trail_delay1` | +134.6 | 111 | 1.212 | 3.17 | 6.5 | 4.8% | 19.5 | 171 | -1.6 | +27.1 | +98.0 | 75% | +60.3 | 69% | 7 | 18 |
| `fsent_sig_full` | +133.9 | 131 | 1.022 | 2.92 | 5.0 | 3.7% | 9.4 | 175 | +1.3 | +22.3 | +81.0 | 67% | +55.2 | 57% | 4 | 16 |
| `fsent_sig_fs_mom` | +127.5 | 135 | 0.944 | 2.94 | 4.4 | 3.5% | 5.7 | 180 | +2.1 | +26.4 | +79.1 | 75% | +61.5 | 54% | 5 | 14 |
| `fsent_sig_wk_pause_short` | +136.4 | 162 | 0.842 | 2.75 | 6.9 | 5.1% | 6.6 | 196 | -2.3 | +19.0 | +58.8 | 67% | +51.6 | 49% | 8 | 14 |
| `fsent_sig_sw20_short` | +151.2 | 190 | 0.796 | 2.43 | 12.9 | 8.5% | 8.5 | 198 | -10.6 | +18.2 | +40.9 | 71% | +60.5 | 71% | 12 | 12 |
| `fsent_sig_sw20_short_wr` | +151.2 | 190 | 0.796 | 2.43 | 12.9 | 8.5% | 8.5 | 198 | -10.6 | +18.2 | +40.9 | 71% | +60.5 | 71% | 12 | 12 |
| `dirmatch_swingpause_sig_sw10` | +83.4 | 150 | 0.556 | 1.83 | 12.2 | 14.6% | 14.4 | 98 | -7.5 | +3.9 | +57.7 | 54% | +9.2 | 123% | 9 | 13 |

Same books, IS side:

| book | IS net | IS n | IS R/tr | IS PF | DD | DD% | ulcer | roll20 | roll50 | roll100 | %mo+ | worst yr | top5% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fsent_sig_trail_delay1` | +153.6 | 187 | 0.821 | 2.25 | 16.1 | 10.4% | 15.6 | -12.8 | +7.0 | +77.8 | 62% | +1.0 | 101% |
| `fsent_sig_full` | +209.0 | 215 | 0.972 | 2.64 | 14.0 | 6.7% | 8.4 | -11.7 | +16.6 | +61.9 | 62% | +25.1 | 87% |
| `fsent_sig_fs_mom` | +206.9 | 217 | 0.953 | 2.77 | 14.2 | 6.9% | 4.9 | -11.9 | -3.4 | +35.0 | 56% | +10.3 | 96% |
| `fsent_sig_wk_pause_short` | +203.0 | 266 | 0.763 | 2.44 | 13.4 | 6.6% | 10.0 | -12.5 | -0.3 | +42.0 | 62% | +38.5 | 81% |
| `fsent_sig_sw20_short` | +246.0 | 341 | 0.722 | 2.21 | 16.9 | 6.9% | 12.7 | -13.5 | +0.1 | +20.7 | 64% | +42.1 | 84% |
| `fsent_sig_sw20_short_wr` | +246.0 | 341 | 0.722 | 2.21 | 16.9 | 6.9% | 12.7 | -13.5 | +0.1 | +20.7 | 64% | +42.1 | 84% |
| `dirmatch_swingpause_sig_sw10` | +106.9 | 243 | 0.440 | 1.63 | 26.8 | 25.0% | 19.5 | -16.5 | -25.2 | -13.3 | 44% | +11.6 | 149% |

Failed the gates, 10 books. Reasons:
- OOS n < 100 - 6 books
- OOS has a negative 50-trade window - 5 books
- IS net <= 0 - 3 books
- OOS net <= 0 - 3 books
- no completed trades in an era - 2 books
- OOS DD > 40%% of net - 1 books

## MULTI - 79 books, 10 pass the gates

| book | OOS net | OOS n | OOS R/tr | OOS PF | DD | DD% | ulcer | sortino | roll20 | roll50 | roll100 | %mo+ | worst yr | top5% | max gap | params |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `age25_dirmatch_multi_sw10` | +152.4 | 136 | 1.121 | 2.95 | 8.8 | 5.8% | 7.1 | 192 | -6.0 | +17.9 | +103.3 | 58% | +40.2 | 65% | 6 | 14 |
| `fsent_dirmatch_short` | +248.2 | 245 | 1.013 | 3.45 | 7.8 | 3.1% | 7.7 | 389 | -7.0 | +8.3 | +68.6 | 83% | +118.5 | 67% | 9 | 14 |
| `fsent_sig_multi` | +182.8 | 185 | 0.988 | 2.98 | 7.6 | 4.2% | 6.0 | 246 | -5.0 | +14.8 | +70.7 | 75% | +72.5 | 57% | 7 | 16 |
| `fsent_champ_long_htf15` | +254.8 | 281 | 0.907 | 3.05 | 11.3 | 4.4% | 6.0 | 373 | -9.9 | +6.3 | +56.5 | 83% | +102.0 | 68% | 11 | 14 |
| `fsent_champ_long_mcloff_htf15` | +270.2 | 302 | 0.895 | 3.01 | 11.1 | 4.1% | 6.8 | 393 | -10.0 | +8.1 | +51.9 | 79% | +112.9 | 67% | 8 | 14 |
| `fsent_sig_multi_htffs` | +197.7 | 224 | 0.883 | 2.61 | 9.0 | 4.5% | 6.4 | 255 | -6.1 | +11.8 | +60.4 | 83% | +90.7 | 71% | 8 | 17 |
| `fsent_champ_long_causalfloor` | +216.1 | 277 | 0.780 | 2.71 | 11.2 | 5.2% | 6.7 | 310 | -8.7 | +0.5 | +42.6 | 75% | +102.8 | 69% | 7 | 15 |
| `fsent_champ_long_mode_atr_low` | +192.6 | 269 | 0.716 | 2.49 | 14.2 | 7.3% | 7.9 | 271 | -11.1 | +5.2 | +39.2 | 50% | +95.3 | 81% | 9 | 11 |
| `fsent_champ_long_biasmom05` | +182.3 | 255 | 0.715 | 2.63 | 8.9 | 4.9% | 6.1 | 268 | -7.4 | +5.2 | +45.5 | 75% | +83.8 | 64% | 7 | 15 |
| `age25_multi_sw10` | +97.0 | 155 | 0.626 | 1.90 | 14.5 | 14.9% | 20.4 | 108 | -11.6 | +2.2 | +67.8 | 58% | +20.2 | 109% | 10 | 13 |

Same books, IS side:

| book | IS net | IS n | IS R/tr | IS PF | DD | DD% | ulcer | roll20 | roll50 | roll100 | %mo+ | worst yr | top5% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `age25_dirmatch_multi_sw10` | +333.3 | 235 | 1.418 | 3.41 | 15.7 | 4.7% | 7.3 | -14.9 | +3.1 | +78.9 | 56% | +52.5 | 73% |
| `fsent_dirmatch_short` | +566.2 | 370 | 1.530 | 4.47 | 10.7 | 1.9% | 2.9 | -7.7 | +8.5 | +80.4 | 67% | +74.1 | 73% |
| `fsent_sig_multi` | +373.0 | 292 | 1.277 | 3.33 | 13.4 | 3.6% | 4.3 | -11.1 | +0.9 | +52.4 | 53% | +31.3 | 82% |
| `fsent_champ_long_htf15` | +505.2 | 500 | 1.010 | 3.13 | 26.3 | 5.2% | 16.2 | -19.9 | -8.8 | +13.8 | 66% | +99.4 | 78% |
| `fsent_champ_long_mcloff_htf15` | +539.8 | 535 | 1.009 | 3.16 | 28.4 | 5.3% | 17.8 | -18.7 | -20.2 | +18.2 | 66% | +106.8 | 75% |
| `fsent_sig_multi_htffs` | +511.5 | 417 | 1.227 | 3.18 | 19.4 | 3.8% | 6.8 | -14.9 | -3.1 | +41.4 | 69% | +66.7 | 78% |
| `fsent_champ_long_causalfloor` | +467.0 | 483 | 0.967 | 2.93 | 24.5 | 5.2% | 16.6 | -20.3 | -13.6 | +3.9 | 58% | +89.4 | 82% |
| `fsent_champ_long_mode_atr_low` | +515.5 | 612 | 0.842 | 2.62 | 48.8 | 9.5% | 27.0 | -16.6 | -32.0 | -32.5 | 60% | +38.0 | 86% |
| `fsent_champ_long_biasmom05` | +460.7 | 462 | 0.997 | 3.00 | 22.8 | 4.9% | 12.3 | -17.6 | -6.5 | +5.4 | 58% | +61.1 | 80% |
| `age25_multi_sw10` | +260.2 | 269 | 0.967 | 2.40 | 18.0 | 6.9% | 9.1 | -16.7 | -12.0 | +6.1 | 51% | +41.0 | 98% |

Failed the gates, 69 books. Reasons:
- OOS has a negative 50-trade window - 65 books
- OOS DD > 40%% of net - 23 books
- OOS net <= 0 - 23 books
- IS net <= 0 - 12 books
- OOS n < 100 - 8 books
