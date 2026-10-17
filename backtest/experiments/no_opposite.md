# exp_no_opposite, re-measured on the current engine

The previous figures were measured on 2026-10-08, before the causal-stop
fix and before the mark corrections. Everything from that date or earlier
in this repo is stale and this is no exception.

This knob is NOT being adopted for its R. A long and a short on one
symbol net to roughly zero exposure while paying fees twice and holding
margin twice, and on a book that may hold eight positions that is a
sizing bug rather than a rounding error. The numbers below answer whether
it is free, not whether it is profitable.

## The two forward candidates

| book | era | fires | % of trades | net off | net on | d net | DD off | DD on | streak off/on | R/trade off/on |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `fsent_champ_long_mcloff_htf15` | IS | 10 | 1.87% | +539.77 | +538.40 | **-1.37** | 28.38 | 28.38 | 22 / 22 | +1.0089 / +1.0255 |
| `fsent_champ_long_mcloff_htf15` | OOS | 7 | 2.32% | +270.17 | +272.92 | **+2.75** | 11.05 | 11.05 | 8 / 8 | +0.8946 / +0.9252 |
| `fsent_champ_long_htf15_tskip6` | IS | 17 | 4.13% | +639.84 | +644.04 | **+4.20** | 22.81 | 23.93 | 13 / 13 | +1.5530 / +1.6305 |
| `fsent_champ_long_htf15_tskip6` | OOS | 8 | 3.57% | +328.54 | +336.16 | **+7.62** | 14.90 | 14.90 | 11 / 9 | +1.4667 / +1.5563 |

## Across every book

| measure | value |
|---|---:|
| book-eras measured | 108 |
| trades before the lock | 35078 |
| trades the lock refused | 476 (1.36%) |
| net better with the lock on | 43 |
| net worse | 30 |
| net unchanged | 35 |
| sum of all net changes | +266.91R |
| drawdown better | 19 |
| drawdown worse | 6 |
| errors | 0 |

## Per-book detail

| book | era | fires | net off | net on | d net | DD off | DD on | streak off/on |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `bm08_multi_sw10` | IS | 0 | +150.16 | +150.16 | +0.00 | 44.76 | 44.76 | 23 / 23 |
| `bm08_multi_sw10` | OOS | 0 | +9.94 | +9.94 | +0.00 | 30.95 | 30.95 | 10 / 10 |
| `bm08_utcsat_multi_sw10` | IS | 0 | +167.44 | +167.44 | +0.00 | 46.23 | 46.23 | 23 / 23 |
| `bm08_utcsat_multi_sw10` | OOS | 0 | +12.53 | +12.53 | +0.00 | 22.36 | 22.36 | 7 / 7 |
| `cap999_nocap` | IS | 1 | +218.56 | +223.42 | +4.86 | 45.98 | 45.98 | 18 / 18 |
| `cap999_nocap` | OOS | 3 | +16.73 | +14.24 | -2.49 | 52.83 | 56.42 | 18 / 18 |
| `decayD_u` | IS | 0 | +84.27 | +84.27 | +0.00 | 58.40 | 58.40 | 14 / 14 |
| `decayD_u` | OOS | 0 | +3.49 | +3.49 | +0.00 | 29.01 | 29.01 | 17 / 17 |
| `fsent_both_trail_half` | IS | 0 | +35.73 | +35.73 | +0.00 | 26.13 | 26.13 | 13 / 13 |
| `fsent_both_trail_half` | OOS | 0 | +30.55 | +30.55 | +0.00 | 13.87 | 13.87 | 6 / 6 |
| `fsent_champ_long` | IS | 10 | +466.92 | +459.41 | -7.51 | 25.08 | 25.08 | 12 / 12 |
| `fsent_champ_long` | OOS | 6 | +215.32 | +221.05 | +5.73 | 11.20 | 10.16 | 7 / 7 |
| `fsent_champ_long_biasmom05` | IS | 6 | +460.72 | +459.33 | -1.39 | 22.78 | 22.78 | 11 / 11 |
| `fsent_champ_long_biasmom05` | OOS | 4 | +182.27 | +182.78 | +0.51 | 8.91 | 7.87 | 7 / 7 |
| `fsent_champ_long_causalfloor` | IS | 8 | +466.98 | +458.55 | -8.43 | 24.47 | 24.47 | 14 / 14 |
| `fsent_champ_long_causalfloor` | OOS | 7 | +216.05 | +220.15 | +4.10 | 11.20 | 10.16 | 7 / 7 |
| `fsent_champ_long_htf15` | IS | 10 | +505.24 | +502.76 | -2.48 | 26.26 | 26.26 | 22 / 22 |
| `fsent_champ_long_htf15` | OOS | 7 | +254.81 | +256.61 | +1.80 | 11.28 | 10.32 | 11 / 11 |
| `fsent_champ_long_htf15_htffs` | IS | 2 | +765.86 | +764.85 | -1.01 | 29.76 | 29.76 | 13 / 13 |
| `fsent_champ_long_htf15_htffs` | OOS | 1 | +346.07 | +346.08 | +0.01 | 14.74 | 14.74 | 10 / 10 |
| `fsent_champ_long_htf15_tskip6` | IS | 17 | +639.84 | +644.04 | +4.20 | 22.81 | 23.93 | 13 / 13 |
| `fsent_champ_long_htf15_tskip6` | OOS | 8 | +328.54 | +336.16 | +7.62 | 14.90 | 14.90 | 11 / 9 |
| `fsent_champ_long_htfesmcl4` | IS | 0 | +770.53 | +771.87 | +1.34 | 20.02 | 20.02 | 17 / 17 |
| `fsent_champ_long_htfesmcl4` | OOS | 0 | +339.08 | +339.08 | +0.00 | 15.04 | 15.04 | 11 / 11 |
| `fsent_champ_long_htffs` | IS | 2 | +757.99 | +756.98 | -1.01 | 22.45 | 22.45 | 13 / 13 |
| `fsent_champ_long_htffs` | OOS | 1 | +313.35 | +313.35 | +0.00 | 14.74 | 14.74 | 10 / 10 |
| `fsent_champ_long_mcloff` | IS | 9 | +504.12 | +502.69 | -1.43 | 23.30 | 23.30 | 13 / 13 |
| `fsent_champ_long_mcloff` | OOS | 7 | +213.27 | +216.03 | +2.76 | 11.05 | 11.05 | 8 / 8 |
| `fsent_champ_long_mcloff_htf15` | IS | 10 | +539.77 | +538.40 | -1.37 | 28.38 | 28.38 | 22 / 22 |
| `fsent_champ_long_mcloff_htf15` | OOS | 7 | +270.17 | +272.92 | +2.75 | 11.05 | 11.05 | 8 / 8 |
| `fsent_champ_long_mode_atr_low` | IS | 13 | +515.49 | +517.64 | +2.15 | 48.76 | 48.01 | 13 / 13 |
| `fsent_champ_long_mode_atr_low` | OOS | 8 | +192.64 | +187.96 | -4.68 | 14.16 | 14.47 | 9 / 9 |
| `fsent_champ_long_mode_chop` | IS | 10 | +462.58 | +455.08 | -7.50 | 25.08 | 25.08 | 12 / 12 |
| `fsent_champ_long_mode_chop` | OOS | 6 | +186.82 | +190.92 | +4.10 | 11.20 | 10.16 | 8 / 8 |
| `fsent_champ_long_mode_fd` | IS | 7 | +447.88 | +439.67 | -8.21 | 25.94 | 25.94 | 12 / 12 |
| `fsent_champ_long_mode_fd` | OOS | 6 | +191.21 | +203.08 | +11.87 | 13.92 | 13.92 | 10 / 10 |
| `fsent_champ_long_mode_flip_quality` | IS | 10 | +461.66 | +454.16 | -7.50 | 25.08 | 25.08 | 12 / 12 |
| `fsent_champ_long_mode_flip_quality` | OOS | 6 | +186.82 | +190.92 | +4.10 | 11.20 | 10.16 | 8 / 8 |
| `fsent_champ_long_mode_union` | IS | 25 | +495.69 | +641.03 | +145.34 | 47.61 | 44.15 | 22 / 22 |
| `fsent_champ_long_mode_union` | OOS | 14 | +196.03 | +204.05 | +8.02 | 17.95 | 16.13 | 10 / 10 |
| `fsent_champ_long_nohalt` | IS | 9 | +504.12 | +502.69 | -1.43 | 23.30 | 23.30 | 13 / 13 |
| `fsent_champ_long_nohalt` | OOS | 7 | +213.27 | +216.03 | +2.76 | 11.05 | 11.05 | 8 / 8 |
| `fsent_champ_long_tskip4` | IS | 8 | +530.42 | +578.96 | +48.54 | 23.66 | 23.77 | 13 / 13 |
| `fsent_champ_long_tskip4` | OOS | 5 | +260.53 | +269.27 | +8.74 | 15.49 | 15.90 | 10 / 10 |
| `fsent_champ_short` | IS | 4 | +569.33 | +562.70 | -6.63 | 12.67 | 12.67 | 10 / 10 |
| `fsent_champ_short` | OOS | 3 | +195.01 | +196.85 | +1.84 | 12.75 | 12.35 | 10 / 10 |
| `fsent_champ_short_session` | IS | 6 | +589.36 | +582.58 | -6.78 | 18.71 | 18.71 | 14 / 14 |
| `fsent_champ_short_session` | OOS | 3 | +267.30 | +269.46 | +2.16 | 19.46 | 18.41 | 10 / 13 |
| `fsent_champ_trailhalf` | IS | 16 | +416.35 | +396.90 | -19.45 | 29.38 | 29.38 | 16 / 16 |
| `fsent_champ_trailhalf` | OOS | 5 | +242.71 | +244.86 | +2.15 | 15.13 | 15.13 | 12 / 12 |
| `fsent_sig_decay_crossed` | IS | 0 | +131.96 | +131.96 | +0.00 | 8.62 | 8.62 | 7 / 7 |
| `fsent_sig_decay_crossed` | OOS | 0 | +52.58 | +52.58 | +0.00 | 9.07 | 9.07 | 6 / 6 |
| `fsent_sig_fs_mom` | IS | 0 | +206.87 | +206.87 | +0.00 | 14.24 | 14.24 | 14 / 14 |
| `fsent_sig_fs_mom` | OOS | 0 | +127.47 | +127.47 | +0.00 | 4.41 | 4.41 | 5 / 5 |
| `fsent_sig_full` | IS | 0 | +208.96 | +208.96 | +0.00 | 14.01 | 14.01 | 7 / 7 |
| `fsent_sig_full` | OOS | 0 | +133.91 | +133.91 | +0.00 | 4.99 | 4.99 | 4 / 4 |
| `fsent_sig_half_crossed` | IS | 0 | +132.00 | +132.00 | +0.00 | 8.59 | 8.59 | 8 / 8 |
| `fsent_sig_half_crossed` | OOS | 0 | +86.79 | +86.79 | +0.00 | 10.75 | 10.75 | 9 / 9 |
| `fsent_sig_multi` | IS | 1 | +372.96 | +366.04 | -6.92 | 13.43 | 13.43 | 10 / 10 |
| `fsent_sig_multi` | OOS | 0 | +182.77 | +184.86 | +2.09 | 7.61 | 5.81 | 7 / 7 |
| `fsent_sig_multi_acc` | IS | 5 | +448.37 | +441.93 | -6.44 | 12.67 | 12.67 | 12 / 12 |
| `fsent_sig_multi_acc` | OOS | 4 | +220.91 | +226.33 | +5.42 | 12.17 | 12.17 | 11 / 11 |
| `fsent_sig_multi_htffs` | IS | 2 | +511.52 | +505.72 | -5.80 | 19.40 | 19.40 | 10 / 10 |
| `fsent_sig_multi_htffs` | OOS | 0 | +197.73 | +201.65 | +3.92 | 8.98 | 7.33 | 8 / 7 |
| `fsent_sig_sw10_long` | IS | 0 | +133.10 | +133.10 | +0.00 | 18.09 | 18.09 | 11 / 11 |
| `fsent_sig_sw10_long` | OOS | 0 | +106.76 | +106.76 | +0.00 | 8.08 | 8.08 | 9 / 9 |
| `fsent_sig_sw10_short` | IS | 0 | +167.14 | +167.14 | +0.00 | 17.58 | 17.58 | 9 / 9 |
| `fsent_sig_sw10_short` | OOS | 0 | +118.71 | +118.71 | +0.00 | 14.39 | 14.39 | 11 / 11 |
| `fsent_sig_sw20_short` | IS | 0 | +246.02 | +246.02 | +0.00 | 16.92 | 16.92 | 9 / 9 |
| `fsent_sig_sw20_short` | OOS | 0 | +151.23 | +151.23 | +0.00 | 12.91 | 12.91 | 12 / 12 |
| `fsent_sig_trail_delay1` | IS | 0 | +153.55 | +153.55 | +0.00 | 16.05 | 16.05 | 8 / 8 |
| `fsent_sig_trail_delay1` | OOS | 0 | +134.57 | +134.57 | +0.00 | 6.49 | 6.49 | 7 / 7 |
| `fsent_sig_wk_pause_short` | IS | 0 | +203.02 | +203.02 | +0.00 | 13.42 | 13.42 | 12 / 12 |
| `fsent_sig_wk_pause_short` | OOS | 0 | +136.39 | +136.39 | +0.00 | 6.91 | 6.91 | 8 / 8 |
| `fsent_utcsat_long` | IS | 10 | +470.03 | +462.52 | -7.51 | 23.81 | 23.81 | 12 / 12 |
| `fsent_utcsat_long` | OOS | 6 | +212.94 | +218.67 | +5.73 | 11.20 | 10.16 | 8 / 7 |
| `fsent_utcsat_short` | IS | 4 | +547.82 | +541.19 | -6.63 | 12.67 | 12.67 | 10 / 10 |
| `fsent_utcsat_short` | OOS | 3 | +209.67 | +211.52 | +1.85 | 15.38 | 15.38 | 10 / 10 |
| `fsent_utcsat_trailhalf` | IS | 14 | +419.14 | +405.10 | -14.04 | 23.49 | 23.49 | 16 / 16 |
| `fsent_utcsat_trailhalf` | OOS | 5 | +241.94 | +246.26 | +4.32 | 15.90 | 13.74 | 12 / 8 |
| `gap_bm_min06` | IS | 1 | +161.73 | +161.79 | +0.06 | 50.14 | 50.08 | 15 / 15 |
| `gap_bm_min06` | OOS | 0 | +4.64 | +4.64 | +0.00 | 35.26 | 35.26 | 12 / 12 |
| `gap_bm_min07` | IS | 0 | +116.85 | +116.85 | +0.00 | 49.03 | 49.03 | 20 / 20 |
| `gap_bm_min07` | OOS | 0 | +10.52 | +10.52 | +0.00 | 28.30 | 28.30 | 12 / 12 |
| `gap_bm_min09` | IS | 0 | +165.01 | +165.01 | +0.00 | 39.39 | 39.39 | 23 / 23 |
| `gap_bm_min09` | OOS | 0 | +8.08 | +8.08 | +0.00 | 28.19 | 28.19 | 10 / 10 |
| `gap_cooldown20` | IS | 2 | +124.34 | +109.72 | -14.62 | 55.77 | 55.77 | 18 / 18 |
| `gap_cooldown20` | OOS | 3 | +22.24 | +19.75 | -2.49 | 41.05 | 44.62 | 14 / 14 |
| `gap_slbuf025` | IS | 1 | +140.16 | +144.83 | +4.67 | 39.47 | 39.47 | 23 / 23 |
| `gap_slbuf025` | OOS | 3 | +2.04 | -0.34 | -2.38 | 42.09 | 42.09 | 17 / 17 |
| `gap_wage32` | IS | 0 | +129.72 | +129.72 | +0.00 | 60.27 | 60.27 | 15 / 15 |
| `gap_wage32` | OOS | 0 | +0.84 | +0.84 | +0.00 | 54.42 | 54.42 | 20 / 20 |
| `swingpause_multi_sw10` | IS | 3 | +144.23 | +128.28 | -15.95 | 56.35 | 56.35 | 12 / 11 |
| `swingpause_multi_sw10` | OOS | 3 | +19.29 | +24.14 | +4.85 | 47.73 | 45.14 | 14 / 14 |
| `trail_half_delay1_skipn4` | IS | 9 | +256.64 | +262.36 | +5.72 | 69.62 | 69.62 | 26 / 24 |
| `trail_half_delay1_skipn4` | OOS | 8 | +24.19 | +41.93 | +17.74 | 37.59 | 37.59 | 19 / 19 |
| `trail_half_dr3_nodelay` | IS | 16 | +144.07 | +173.57 | +29.50 | 70.47 | 67.91 | 23 / 21 |
| `trail_half_dr3_nodelay` | OOS | 3 | +66.08 | +53.20 | -12.88 | 50.41 | 50.41 | 17 / 17 |
| `trail_half_skipn3_nodelay` | IS | 6 | +213.59 | +210.38 | -3.21 | 69.84 | 69.84 | 24 / 24 |
| `trail_half_skipn3_nodelay` | OOS | 5 | +30.13 | +43.97 | +13.84 | 44.29 | 44.29 | 15 / 15 |
| `trail_half_skipn6_dr3` | IS | 17 | +291.76 | +320.32 | +28.56 | 70.39 | 68.89 | 27 / 24 |
| `trail_half_skipn6_dr3` | OOS | 9 | +11.58 | +30.25 | +18.67 | 40.29 | 40.29 | 19 / 19 |
| `trail_half_skipn8_dr1` | IS | 10 | +238.39 | +250.87 | +12.48 | 70.22 | 70.22 | 30 / 24 |
| `trail_half_skipn8_dr1` | OOS | 6 | +21.00 | +27.67 | +6.67 | 37.98 | 37.98 | 19 / 19 |
| `trail_half_skipn8_nodelay` | IS | 10 | +238.39 | +250.87 | +12.48 | 70.22 | 70.22 | 30 / 24 |
| `trail_half_skipn8_nodelay` | OOS | 6 | +21.62 | +28.28 | +6.66 | 37.37 | 37.37 | 19 / 19 |
| `utcsat_cap999_nocap` | IS | 1 | +145.45 | +145.50 | +0.05 | 45.28 | 45.28 | 14 / 14 |
| `utcsat_cap999_nocap` | OOS | 3 | +12.74 | +5.09 | -7.65 | 48.12 | 48.12 | 14 / 14 |
