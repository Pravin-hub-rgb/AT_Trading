# Risk-adjusted scorecard - the shortlist

No gate. No pass/fail. Columns only, per the risk-adjustment review:
"koi universal number nahi hai" for acceptable drawdown. The fixed 29R
ceiling is gone and so is the 5% percentage I put in its place.

**Risk is FIXED 1R per trade** (`r_multiple = move/risk` in unified.py),
so R is the account unit and `maxDD R` is the primary measure.

`recover d` is the number the review says decides things: *"ek strategy
5% historical DD ke saath bhi unsuitable ho sakti hai agar uska worst
drawdown 8 mahine tak recover na ho."*

## SIG

| book | net R | R/trade | net/DD | maxDD R | DD %peak | DD days | recover d | worst 3m | worst 6m | worst 12m | roll20 % | roll50 % | worstR50 | cap10 % | top5 % | retention | neg half | p OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fsent_sig_sw20_short` | 397.25 | 0.75 | 23.48 | 16.92 | 4.25 | 88.10 | 73 | -2.33 | -1.08 | -8.99 | 90.00 | 100.00 | 0.06 | 81.93 | 81.10 | 110.30 | 0 | 0.16 |
| `fsent_sig_wk_pause_short` | 339.41 | 0.79 | 25.29 | 13.42 | 3.88 | 154.00 | 65 | -3.86 | -3.46 | -4.00 | 91.00 | 99.70 | -0.26 | 87.91 | 68.60 | 110.30 | 0 | 0.44 |
| `fsent_sig_trail_delay1` | 288.12 | 0.97 | 17.96 | 16.05 | 5.42 | 149.60 | 58 | -2.26 | -1.08 | -0.81 | 87.10 | 100.00 | 7.00 | 59.69 | 91.20 | 147.60 | 0 | 0.93 |
| `fsent_sig_full` | 342.86 | 0.99 | 24.48 | 14.01 | 4.00 | 154.00 | 54 | -2.07 | -3.01 | -3.48 | 88.40 | 100.00 | 16.65 | 69.66 | 77.40 | 105.20 | 0 | 0.92 |
| `fsent_sig_fs_mom` | 334.34 | 0.95 | 23.49 | 14.24 | 4.15 | 154.00 | 103 | -2.26 | -1.37 | -4.00 | 87.70 | 98.70 | -3.42 | 66.53 | 84.30 | 99.00 | 0 | 0.80 |

## MULTI

| book | net R | R/trade | net/DD | maxDD R | DD %peak | DD days | recover d | worst 3m | worst 6m | worst 12m | roll20 % | roll50 % | worstR50 | cap10 % | top5 % | retention | neg half | p OOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fsent_champ_long_htf15_htffs` | 1111.93 | 0.97 | 37.36 | 29.76 | 2.66 | 242.30 | 9 | -8.42 | -3.01 | -2.48 | 73.80 | 89.80 | -20.53 | 68.19 | 81.50 | 86.30 | 1 | 0.49 |
| `fsent_champ_long_htfesmcl4` | 1109.61 | 0.93 | 55.42 | 20.02 | 1.80 | 87.80 | 50 | -8.38 | -6.32 | -2.48 | 73.60 | 89.80 | -20.02 | 67.23 | 83.80 | 78.90 | 1 | 0.53 |
| `fsent_champ_long_htf15_tskip6` | 968.38 | 1.52 | 42.46 | 22.81 | 2.35 | 112.70 | 39 | -6.82 | -1.03 | -4.33 | 84.90 | 98.50 | -5.85 | 62.50 | 69.80 | 94.40 | 0 | n/a |
| `fsent_champ_long_htffs` | 1071.34 | 0.94 | 47.72 | 22.45 | 2.09 | 242.30 | 9 | -8.42 | -1.00 | -2.48 | 74.10 | 89.30 | -20.41 | 67.07 | 83.30 | 80.00 | 1 | 0.60 |
| `fsent_champ_long_mcloff_htf15` | 809.94 | 0.97 | 28.54 | 28.38 | 3.50 | 126.40 | 140 | -2.37 | -0.11 | -4.67 | 81.70 | 95.60 | -20.20 | 75.96 | 73.40 | 88.70 | 0 | 0.14 |

## Best on each axis

| axis | better | SIG best | MULTI best |
|---|---|---|---|
| net R | high | sig_sw20_short (397.25) | champ_long_htf15_htffs (1111.93) |
| R/trade | high | sig_full (0.99) | champ_long_htf15_tskip6 (1.52) |
| net/DD | high | sig_wk_pause_short (25.29) | champ_long_htfesmcl4 (55.42) |
| maxDD R | low | sig_wk_pause_short (13.42) | champ_long_htfesmcl4 (20.02) |
| DD %peak | low | sig_wk_pause_short (3.88) | champ_long_htfesmcl4 (1.80) |
| DD days | low | sig_sw20_short (88.10) | champ_long_htfesmcl4 (87.80) |
| recover d | low | sig_full (54) | champ_long_htf15_htffs (9) |
| worst 3m | high | sig_full (-2.07) | champ_long_mcloff_htf15 (-2.37) |
| worst 6m | high | sig_sw20_short (-1.08) | champ_long_mcloff_htf15 (-0.11) |
| worst 12m | high | sig_trail_delay1 (-0.81) | champ_long_htf15_htffs (-2.48) |
| roll20 % | high | sig_wk_pause_short (91.00) | champ_long_htf15_tskip6 (84.90) |
| roll50 % | high | sig_sw20_short (100.00) | champ_long_htf15_tskip6 (98.50) |
| worstR50 | high | sig_full (16.65) | champ_long_htf15_tskip6 (-5.85) |
| cap10 % | high | sig_wk_pause_short (87.91) | champ_long_mcloff_htf15 (75.96) |
| top5 % | high | sig_trail_delay1 (91.20) | champ_long_htfesmcl4 (83.80) |
| retention | high | sig_trail_delay1 (147.60) | champ_long_htf15_tskip6 (94.40) |
| neg half | low | sig_sw20_short (0) | champ_long_htf15_tskip6 (0) |
| p OOS | low | sig_sw20_short (0.16) | champ_long_mcloff_htf15 (0.14) |

## Axis notes

- **net R** (high) - total return, both eras
- **R/trade** (high) - quality per trade
- **net/DD** (high) - return per unit of drawdown
- **maxDD R** (low) - R is the account unit here
- **DD %peak** (low) - scale-free
- **DD days** (low) - how long under water
- **recover d** (low) - peak to flat again
- **worst 3m** (high) - bad quarter
- **worst 6m** (high) - bad half
- **worst 12m** (high) - bad year
- **roll20 %** (high) - trade windows
- **roll50 %** (high) - trade windows
- **worstR50** (high) - deepest 50-trade hole
- **cap10 %** (high) - net left after dropping the 10 best trades
- **top5 %** (high) - share of net from best 5%
- **retention** (high) - IS expectancy -> OOS
- **neg half** (low) - complete half-years
- **p OOS** (low) - chance of being this good by luck

`neg half` counts only COMPLETE half-years. A period the data has not
finished is excluded and listed in `partial_cells`; without that, four
of the five SIG books carried their only negative half-year in a
2026-H2 the data has barely lived through.