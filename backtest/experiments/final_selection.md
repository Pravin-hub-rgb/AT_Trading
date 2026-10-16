# Final selection - top 5 per class, every factor at once

No single score decides this. Each axis is scored 0-100 by ranking it
against the other books in its own class, then the axes are averaged
with the weights below. Nothing here is compared to a threshold nobody
can defend, because the last two thresholds tried both turned out to be
wrong.

| axis | weight | direction |
|---|---:|---|
| net R | 10 | higher better |
| R per trade | 14 | higher better |
| profit factor | 8 | higher better |
| OOS retention | 10 | higher better |
| significance OOS | 14 | higher better |
| net / drawdown | 12 | higher better |
| DD % of peak | 8 | lower better |
| recovery days | 10 | lower better |
| p90 recovery | 6 | lower better |
| survives -top10 | 12 | higher better |
| top 5% share | 8 | lower better |
| 50-trade windows + | 8 | higher better |
| negative half-years | 6 | lower better |
| sample size OOS | 6 | higher better |

R per trade carries the joint-highest weight with significance, on
purpose. Ranking on total net R is what let a book that bought its
return with 57% more trades into the shortlist once already.

## SIG

| rank | book | **SCORE** | R/tr | net R | p OOS | retention | net/DD | rec days | survive -top10 | n OOS |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `fsent_sig_wk_pause_short` | **74.2** | 0.793 | 339 | 0.554 | 110% | 25.3 | 65 | 88% | 162 |
| 2 | `fsent_sig_full` | **73.0** | 0.991 | 343 | 0.759 | 105% | 24.5 | 54 | 70% | 131 |
| 3 | `fsent_sig_sw20_short` | **57.6** | 0.748 | 397 | 0.566 | 110% | 23.5 | 73 | 82% | 190 |
| 4 | `fsent_sig_fs_mom` | **50.3** | 0.950 | 334 | 0.688 | 99% | 23.5 | 103 | 67% | 135 |
| 5 | `fsent_sig_trail_delay1` | **44.8** | 0.967 | 288 | 0.866 | 148% | 18.0 | 58 | 60% | 111 |

### Per axis, 0-100

| axis | w | `sig_wk_pause_short` | `sig_full` | `sig_sw20_short` | `sig_fs_mom` | `sig_trail_delay1` |
|---|---:|---:|---:|---:|---:|---:|
| net R | 10 | 60 | 80 | 100 | 40 | 20 |
| R per trade | 14 | 40 | 100 | 20 | 60 | 80 |
| profit factor | 8 | 40 | 80 | 20 | 100 | 60 |
| OOS retention | 10 | 80 | 40 | 60 | 20 | 100 |
| significance OOS | 14 | 100 | 40 | 80 | 60 | 20 |
| net / drawdown | 12 | 100 | 80 | 40 | 60 | 20 |
| DD % of peak | 8 | 100 | 80 | 40 | 60 | 20 |
| recovery days | 10 | 60 | 100 | 40 | 20 | 80 |
| p90 recovery | 6 | 80 | 60 | 100 | 40 | 20 |
| survives -top10 | 12 | 100 | 60 | 80 | 40 | 20 |
| top 5% share | 8 | 100 | 80 | 60 | 40 | 20 |
| 50-trade windows + | 8 | 40 | 100 | 60 | 20 | 80 |
| negative half-years | 6 | 40 | 80 | 20 | 100 | 60 |
| sample size OOS | 6 | 80 | 40 | 100 | 60 | 20 |

## MULTI

| rank | book | **SCORE** | R/tr | net R | p OOS | retention | net/DD | rec days | survive -top10 | n OOS |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `fsent_champ_long_mcloff_htf15` | **65.8** | 0.968 | 810 | 0.011 | 89% | 28.5 | 140 | 76% | 302 |
| 2 | `fsent_champ_long_htf15_tskip6` | **64.5** | 1.523 | 968 | 0.382 | 94% | 42.5 | 39 | 62% | 224 |
| 3 | `fsent_champ_long_htf15_htffs` | **63.3** | 0.965 | 1112 | 0.232 | 86% | 37.4 | 9 | 68% | 396 |
| 4 | `fsent_champ_long_htfesmcl4` | **53.9** | 0.935 | 1110 | 0.379 | 79% | 55.4 | 50 | 67% | 425 |
| 5 | `fsent_champ_long_htffs` | **52.4** | 0.938 | 1071 | 0.393 | 80% | 47.7 | 9 | 67% | 389 |

### Per axis, 0-100

| axis | w | `champ_long_mcloff_htf15` | `champ_long_htf15_tskip6` | `champ_long_htf15_htffs` | `champ_long_htfesmcl4` | `champ_long_htffs` |
|---|---:|---:|---:|---:|---:|---:|
| net R | 10 | 20 | 40 | 100 | 80 | 60 |
| R per trade | 14 | 80 | 100 | 60 | 20 | 40 |
| profit factor | 8 | 80 | 100 | 60 | 20 | 40 |
| OOS retention | 10 | 80 | 100 | 60 | 20 | 40 |
| significance OOS | 14 | 100 | 40 | 80 | 60 | 20 |
| net / drawdown | 12 | 20 | 60 | 40 | 100 | 80 |
| DD % of peak | 8 | 20 | 60 | 40 | 100 | 80 |
| recovery days | 10 | 20 | 60 | 80 | 40 | 100 |
| p90 recovery | 6 | 100 | 20 | 60 | 40 | 80 |
| survives -top10 | 12 | 100 | 20 | 80 | 60 | 40 |
| top 5% share | 8 | 80 | 100 | 60 | 20 | 40 |
| 50-trade windows + | 8 | 80 | 100 | 40 | 60 | 20 |
| negative half-years | 6 | 100 | 80 | 20 | 40 | 60 |
| sample size OOS | 6 | 40 | 20 | 80 | 100 | 60 |
