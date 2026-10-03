# Registry books - measured board, IS and true OOS

Every book in `experiment_registry.py`. Generated FROM the registry pins, so it
cannot drift from them. All were re-measured on `unified.py` on 2026-10-02 and
every pin re-derived from the engine, not copied from the pass that wrote it.

- **IS** = 2023-26 in sample.
- **OOS** = 2021-22, never used to choose anything.

`net` is after costs (55bp fee/side, 2x, 5bp slippage, 1bp funding, 1bp cost).
`dd` is max drawdown in R on the **NET** equity curve (r_multiple minus cost_r).
The runner prints a GROSS-basis drawdown under the label `DD`; the two differ by
roughly 10R per book and are not interchangeable. Pins name the net one
`dd_net` so a pin can never be read on the wrong basis.

**Read the OOS column.** A book that wins IS and loses OOS has been fitted to
the sample. Several books here do exactly that and none should ship.

`champion` is a book name, not a claim of highest net R.

## Ranked by IS net R

| # | book | IS n | IS net | IS dd | OOS n | OOS net | OOS dd |
|---|------|------:|-------:|------:|------:|--------:|--------:|
| 1 | `trail_half_skipn6_dr3` | 373 | +615.15 | 46.15 | 208 | +118.86 | 45.50 |
| 2 | `trail_half_skipn8_nodelay` | 383 | +588.76 | 45.46 | 211 | +113.28 | 49.56 |
| 3 | `trail_half_skipn8_dr1` | 383 | +588.76 | 45.46 | 216 | +103.96 | 58.88 |
| 4 | `trail_half_skipn3_nodelay` | 449 | +561.98 | 43.30 | 253 | +98.60 | 61.40 |
| 5 | `trail_half_delay1_skipn4` | 424 | +556.62 | 44.47 | 234 | +104.98 | 52.50 |
| 6 | `dirmatch_multi_sw10` | 389 | +444.21 | 24.01 | 222 | +172.06 | 15.36 |
| 7 | `dirmatch_single_sw10` | 392 | +442.72 | 31.02 | 235 | +140.64 | 18.19 |
| 8 | `age10_dirmatch_multi_sw10` | 150 | +417.68 | 13.45 | 77 | +61.11 | 7.51 |
| 9 | `trail_half_dr3_nodelay` | 412 | +416.92 | 44.80 | 232 | +123.60 | 32.16 |
| 10 | `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | 12.90 | 83 | +63.65 | 8.50 |
| 11 | `trail_half_delay1` | 465 | +385.92 | 51.39 | 272 | +88.74 | 51.72 |
| 12 | `trail_half` | 468 | +384.99 | 51.10 | 269 | +71.73 | 52.08 |
| 13 | `cap32d` | 522 | +375.53 | 48.39 | 292 | +94.61 | 30.46 |
| 14 | `cap999_nocap` | 592 | +360.87 | 54.25 | 314 | +130.11 | 33.87 |
| 15 | `utcsat_entry_minus_1` | 454 | +358.92 | 21.18 | 253 | +60.21 | 29.38 |
| 16 | `trail_skipn4` | 439 | +357.15 | 43.96 | 243 | +61.05 | 75.60 |
| 17 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | 21.47 | 167 | +165.92 | 9.25 |
| 18 | `cap48d` | 556 | +351.27 | 54.25 | 302 | +87.68 | 33.00 |
| 19 | `lb30_w24_ext2.0` | 380 | +344.61 | 36.58 | 176 | +32.84 | 41.00 |
| 20 | `utcsat_cap999_nocap` | 537 | +336.98 | 42.82 | 284 | +138.68 | 26.17 |
| 21 | `lb30_w24_ext1.5` | 337 | +336.67 | 35.92 | 143 | +15.01 | 40.73 |
| 22 | `gap_bm_min09` | 370 | +328.26 | 29.02 | 196 | +106.62 | 21.41 |
| 23 | `champion_multi_sw10` | 500 | +325.78 | 27.72 | 279 | +70.15 | 53.19 |
| 24 | `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | 27.72 | 279 | +70.15 | 53.19 |
| 25 | `champion_multi_sw10_entry1` | 500 | +325.75 | 27.72 | 279 | +70.15 | 53.19 |
| 26 | `age25_multi_sw10` | 293 | +319.22 | 25.86 | 194 | +130.15 | 12.42 |
| 27 | `fullstack_wage10_cd0_single_sw10` | 234 | +316.64 | 23.96 | 158 | +28.72 | 29.45 |
| 28 | `utcsat_chopband_multi_sw10` | 392 | +315.45 | 36.41 | 235 | +91.73 | 22.94 |
| 29 | `lb30_w24_ext2.5` | 405 | +315.08 | 42.82 | 178 | +43.34 | 41.06 |
| 30 | `lb30_w24_ext3.0` | 415 | +314.51 | 42.27 | 183 | +36.09 | 45.09 |
| 31 | `wage10_swingpause_wskip_single_sw10` | 330 | +308.65 | 26.27 | 190 | +25.00 | 27.59 |
| 32 | `curfew624_utcsat_multi_sw10` | 377 | +304.72 | 31.95 | 211 | +51.72 | 26.83 |
| 33 | `ext2_utcsat_multi_sw10` | 417 | +301.86 | 41.77 | 237 | +80.50 | 24.30 |
| 34 | `nowknd_multi_sw10` | 403 | +301.39 | 25.88 | 219 | +24.76 | 29.76 |
| 35 | `bm05_utcsat_multi_sw10` | 420 | +298.15 | 35.33 | 237 | +77.76 | 24.64 |
| 36 | `gap_cd15` | 488 | +298.14 | 46.85 | 273 | +74.67 | 46.67 |
| 37 | `b2doji_utcsat_multi_sw10` | 422 | +295.70 | 36.16 | 229 | +63.18 | 28.56 |
| 38 | `fullstack_atrr_utcsat_multi_sw10` | 311 | +295.46 | 26.61 | 201 | +36.07 | 31.36 |
| 39 | `htfrr2_multi_sw10` | 423 | +292.86 | 35.68 | 230 | +45.93 | 41.00 |
| 40 | `gap_bm_min06` | 445 | +284.52 | 43.68 | 245 | +82.81 | 32.65 |
| 41 | `ext25_utcsat_multi_sw10` | 442 | +281.30 | 36.18 | 249 | +75.35 | 24.64 |
| 42 | `utcsat_multi_sw10` | 453 | +279.47 | 35.54 | 254 | +66.90 | 24.64 |
| 43 | `utcsat_cap16d` | 453 | +279.47 | 35.54 | 254 | +66.90 | 24.64 |
| 44 | `decayA_u` | 453 | +279.47 | 35.54 | 254 | +66.90 | 24.64 |
| 45 | `ext4_utcsat_multi_sw10` | 454 | +279.16 | 35.54 | 256 | +70.25 | 24.64 |
| 46 | `ext35_utcsat_multi_sw10` | 454 | +279.16 | 35.54 | 256 | +70.25 | 24.64 |
| 47 | `gap_cooldown20` | 484 | +278.45 | 46.85 | 270 | +87.36 | 38.17 |
| 48 | `nowknd_single_sw10` | 401 | +278.06 | 32.28 | 230 | +31.29 | 31.31 |
| 49 | `bm05_multi_sw10` | 456 | +277.86 | 46.63 | 261 | +87.84 | 38.73 |
| 50 | `lb30_halt0` | 484 | +276.86 | 60.28 | 234 | +44.88 | 48.33 |
| 51 | `dirmatch_swingpause_single_sw10` | 362 | +273.84 | 30.04 | 215 | +133.90 | 15.96 |
| 52 | `wage24_utcsat_multi_sw10` | 332 | +273.80 | 21.70 | 199 | +63.75 | 28.74 |
| 53 | `wage12_utcsat_multi_sw10` | 391 | +273.70 | 31.66 | 227 | +91.60 | 23.33 |
| 54 | `cap20d` | 498 | +269.60 | 46.03 | 286 | +87.42 | 35.27 |
| 55 | `chopband_multi_sw10` | 432 | +268.79 | 41.70 | 257 | +85.94 | 42.74 |
| 56 | `fullstack_swingpause_single_sw10` | 262 | +268.27 | 24.22 | 168 | +24.93 | 28.54 |
| 57 | `lb30_persist5` | 410 | +267.30 | 49.18 | 191 | +6.55 | 34.33 |
| 58 | `gap_bm_min07` | 414 | +266.50 | 41.29 | 224 | +84.81 | 32.89 |
| 59 | `combined_b2age_utcsat_multi_sw10` | 407 | +265.38 | 36.00 | 221 | +67.87 | 25.80 |
| 60 | `bm08_utcsat_multi_sw10` | 359 | +264.66 | 29.71 | 192 | +91.58 | 19.02 |
| 61 | `chopband_atrr_swingpause_single_sw10` | 321 | +264.45 | 35.77 | 211 | +35.66 | 37.85 |
| 62 | `decayB_c` | 303 | +263.90 | 30.18 | 146 | +70.97 | 16.32 |
| 63 | `trail_delay1` | 501 | +263.62 | 45.37 | 279 | +69.65 | 54.91 |
| 64 | `gap_trail_prevbar` | 501 | +263.62 | 45.37 | 279 | +69.65 | 54.91 |
| 65 | `wage12_swingpause_single_sw10` | 323 | +262.31 | 27.48 | 183 | +2.28 | 34.44 |
| 66 | `age50_utcsat_multi_sw10` | 434 | +261.40 | 37.95 | 246 | +71.71 | 23.44 |
| 67 | `bm05_multi_sw20` | 458 | +259.80 | 51.69 | 248 | +17.03 | 41.93 |
| 68 | `rmax15_multi_sw10` | 407 | +255.56 | 50.19 | 166 | +2.95 | 41.46 |
| 69 | `decayE_c` | 245 | +254.21 | 28.76 | 139 | +95.96 | 15.13 |
| 70 | `decayE_u` | 217 | +250.36 | 25.90 | 118 | +94.53 | 17.18 |
| 71 | `cap24d` | 510 | +248.83 | 46.68 | 293 | +0.49 | 49.68 |
| 72 | `bm08_multi_sw10` | 391 | +248.81 | 38.30 | 210 | +100.42 | 28.22 |
| 73 | `wage8_swingpause_single_sw10` | 329 | +247.85 | 29.39 | 192 | +22.87 | 27.65 |
| 74 | `lb30_chop55_persist2` | 429 | +247.51 | 46.17 | 222 | +28.95 | 42.93 |
| 75 | `utcsat_swingpause_single_sw10` | 406 | +245.70 | 36.47 | 245 | +85.04 | 18.54 |
| 76 | `union_multi` | 137 | +245.39 | 16.45 | 53 | +54.03 | 6.11 |
| 77 | `wage16_swingpause_single_sw10` | 302 | +244.80 | 28.04 | 176 | +20.16 | 27.97 |
| 78 | `bm05_swingpause_single_sw10` | 425 | +243.81 | 49.00 | 253 | +71.34 | 37.92 |
| 79 | `swingpause_single_sw10` | 451 | +242.55 | 48.67 | 269 | +76.02 | 37.64 |
| 80 | `chopband_swingpause_single_sw10` | 395 | +241.65 | 38.57 | 238 | +75.51 | 46.11 |
| 81 | `atrr_swingpause_single_sw10` | 381 | +241.57 | 46.77 | 242 | +26.97 | 39.49 |
| 82 | `swingpause_multi_sw10` | 444 | +241.06 | 41.60 | 249 | +76.69 | 35.70 |
| 83 | `wage24_multi_sw10` | 364 | +240.58 | 31.33 | 218 | +76.29 | 34.05 |
| 84 | `gap_wage24` | 364 | +240.58 | 31.33 | 218 | +76.29 | 34.05 |
| 85 | `atrr_cd0_swingpause_single_sw10` | 385 | +240.56 | 47.35 | 245 | +20.89 | 45.95 |
| 86 | `gap_mcl5` | 523 | +240.02 | 43.35 | 302 | +72.73 | 54.16 |
| 87 | `persist8_multi_sw10` | 499 | +239.12 | 46.85 | 282 | +37.31 | 50.39 |
| 88 | `persist6_multi_sw10` | 499 | +239.12 | 46.85 | 279 | +79.99 | 48.95 |
| 89 | `gap_skip_decisive` | 499 | +239.12 | 46.85 | 223 | +104.12 | 29.03 |
| 90 | `gap_inert_winkill3` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 91 | `gap_inert_winkill2` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 92 | `gap_inert_lossstreak` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 93 | `gap_inert_lb60` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 94 | `gap_inert_lb50` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 95 | `gap_inert_kill` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 96 | `gap_inert_htfrr3` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 97 | `gap_inert_geom` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 98 | `gap_inert_event_shift` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 99 | `gap_inert_curfew44` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 100 | `gap_inert_cohort2` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 101 | `gap_inert_cohort1` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 102 | `gap_inert_chop65` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 103 | `gap_inert_chop61` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 104 | `gap_inert_chop52` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 105 | `decayA_c` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 106 | `champion_multi_sw10_leg` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 107 | `cap16d` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 |
| 108 | `persist5_multi_sw10` | 498 | +239.00 | 46.85 | 286 | +79.62 | 50.29 |
| 109 | `gap_cooldown4` | 502 | +238.56 | 46.47 | 285 | +70.69 | 50.73 |
| 110 | `gap_cd5` | 502 | +238.56 | 46.47 | 284 | +68.59 | 52.83 |
| 111 | `gap_persist1` | 502 | +238.45 | 53.86 | 294 | +78.35 | 46.46 |
| 112 | `baseline_no_partial_sw10` | 502 | +238.45 | 53.86 | 294 | +78.35 | 46.46 |
| 113 | `causalsl_utcsat_multi_sw10` | 448 | +237.43 | 36.53 | 256 | +79.48 | 22.60 |
| 114 | `legskip2_multi_sw10` | 269 | +235.96 | 29.15 | 162 | +15.67 | 35.65 |
| 115 | `baseline_no_partial_sw20` | 496 | +232.38 | 61.58 | 268 | -7.56 | 56.52 |
| 116 | `persist4_multi_sw10` | 501 | +231.70 | 46.85 | 286 | +90.09 | 35.74 |
| 117 | `gap_curfew_16_20` | 470 | +231.33 | 49.95 | 274 | +61.84 | 46.58 |
| 118 | `persist3_multi_sw10` | 495 | +229.45 | 53.26 | 284 | +83.87 | 36.29 |
| 119 | `rmax10_swingpause_single_sw10` | 294 | +228.59 | 47.91 | 92 | +14.67 | 42.64 |
| 120 | `wage24_swingpause_single_sw10` | 269 | +228.40 | 20.87 | 163 | +33.80 | 30.46 |
| 121 | `nowknd_swingpause_single_sw10` | 365 | +228.26 | 30.31 | 205 | +20.30 | 27.28 |
| 122 | `gap_wage28` | 341 | +223.08 | 30.47 | 208 | +87.58 | 26.23 |
| 123 | `htfrr4_multi_sw10` | 397 | +222.36 | 38.81 | 221 | +69.94 | 36.49 |
| 124 | `htfrr25_multi_sw10` | 419 | +221.11 | 34.27 | 223 | +75.51 | 31.27 |
| 125 | `decayB_u` | 270 | +220.96 | 26.91 | 128 | +91.62 | 16.86 |
| 126 | `opt_ml_cd0_mb10` | 510 | +215.50 | 60.37 | 251 | -6.29 | 62.26 |
| 127 | `champion_multi_sw10_entry_both` | 495 | +215.09 | 34.72 | 281 | +82.63 | 45.26 |
| 128 | `gap_wage32` | 331 | +214.48 | 31.77 | 202 | +76.96 | 26.04 |
| 129 | `gap_slbuf010` | 497 | +214.36 | 45.99 | 278 | +62.66 | 51.65 |
| 130 | `champion_multi_sw20` | 493 | +213.33 | 50.64 | 265 | +8.43 | 46.82 |
| 131 | `fliponly_swingpause_single_sw10` | 268 | +211.34 | 29.50 | 164 | +0.15 | 41.52 |
| 132 | `gap_curfew_a4_b8` | 470 | +209.93 | 45.74 | 269 | +81.76 | 48.07 |
| 133 | `wage20_swingpause_single_sw10` | 283 | +205.35 | 26.45 | 170 | +47.56 | 23.87 |
| 134 | `fliponly_multi_sw10` | 286 | +202.45 | 35.43 | 155 | -10.70 | 52.55 |
| 135 | `htfrr35_multi_sw10` | 406 | +202.29 | 41.04 | 227 | +51.62 | 45.85 |
| 136 | `dualunion_multi` | 90 | +201.70 | 9.04 | 38 | +39.74 | 7.91 |
| 137 | `curfew624_swingpause_single_sw10` | 300 | +198.91 | 23.17 | 176 | +38.02 | 27.03 |
| 138 | `gap_r_cap3` | 459 | +198.53 | 46.85 | 270 | +80.16 | 49.35 |
| 139 | `opt_ml_cd10_mb10` | 446 | +198.09 | 44.56 | 216 | +3.24 | 49.44 |
| 140 | `wage12_swingpause_single_nowknd_sw10` | 392 | +196.94 | 41.23 | 236 | +58.09 | 56.84 |
| 141 | `champion_single_sw20` | 496 | +196.28 | 58.21 | 269 | +6.73 | 48.49 |
| 142 | `causalsl_swingpause_single_sw10` | 446 | +195.67 | 45.42 | 266 | +82.76 | 27.83 |
| 143 | `decayD_c` | 353 | +194.24 | 33.05 | 176 | +45.26 | 48.53 |
| 144 | `b2doji_swingpause_single_sw10` | 414 | +188.71 | 46.29 | 244 | +17.68 | 52.68 |
| 145 | `gap_slbuf025` | 497 | +188.41 | 44.69 | 279 | +82.53 | 31.78 |
| 146 | `rmax15_swingpause_single_sw10` | 376 | +187.78 | 57.54 | 161 | -5.83 | 45.76 |
| 147 | `cap8d` | 472 | +185.83 | 47.32 | 273 | +52.45 | 54.05 |
| 148 | `causalsl_multi_sw10` | 493 | +185.08 | 47.70 | 283 | +82.65 | 43.92 |
| 149 | `chopband_atrr_swingpause_single_sw20` | 329 | +175.90 | 44.83 | 202 | +12.34 | 42.67 |
| 150 | `decayC_u` | 273 | +173.31 | 30.16 | 142 | +55.52 | 22.62 |
| 151 | `atrr_swingpause_single_sw20` | 390 | +171.57 | 50.43 | 223 | -8.48 | 52.53 |
| 152 | `champion_single_sw10` | 503 | +170.91 | 50.48 | 295 | +78.57 | 38.11 |
| 153 | `gap_window_r_cap2` | 449 | +163.31 | 46.85 | 256 | +77.92 | 50.33 |
| 154 | `gap_r_cap1` | 448 | +162.70 | 46.85 | 246 | +66.10 | 48.53 |
| 155 | `decayC_c` | 299 | +154.64 | 34.02 | 166 | +58.98 | 35.42 |
| 156 | `swingpause_single_sw20` | 444 | +154.08 | 57.93 | 248 | +6.80 | 52.53 |
| 157 | `cap12d` | 471 | +153.72 | 46.71 | 282 | +71.16 | 50.54 |
| 158 | `wage12_swingpause_single_sw20` | 394 | +153.32 | 43.96 | 215 | +24.50 | 37.07 |
| 159 | `decayD_u` | 324 | +150.08 | 32.45 | 159 | +70.77 | 19.73 |
| 160 | `chopband_swingpause_single_sw20` | 388 | +146.42 | 51.76 | 227 | +22.17 | 43.11 |
| 161 | `opt_cd10_w24` | 300 | +144.13 | 47.02 | 145 | +12.70 | 34.90 |
| 162 | `a4_w24_ext1.5` | 300 | +144.13 | 47.02 | 145 | +12.70 | 34.90 |
| 163 | `lb30_halt6_cd0` | 538 | +140.96 | 84.06 | 252 | +15.37 | 75.01 |
| 164 | `age50_swingpause_single_sw10` | 429 | +137.14 | 48.05 | 264 | +68.19 | 43.82 |
| 165 | `gap_pivot_trail` | 514 | +133.69 | 44.89 | 296 | -4.57 | 41.79 |
| 166 | `a4_w24_ext3.0` | 368 | +133.69 | 48.14 | 187 | +28.37 | 38.40 |
| 167 | `partial5_multi_sw10` | 501 | +131.63 | 46.01 | 282 | +43.50 | 47.16 |
| 168 | `utc_wknd_swingpause_single_sw10` | 350 | +121.03 | 40.49 | 197 | -15.69 | 30.82 |
| 169 | `partial4_multi_sw10` | 506 | +106.70 | 45.39 | 281 | +36.04 | 46.57 |
| 170 | `gap_campaign4` | 369 | +100.55 | 44.08 | 216 | +109.33 | 19.25 |
| 171 | `partial3_multi_sw10` | 513 | +92.55 | 39.75 | 283 | +23.41 | 46.85 |
| 172 | `partial2_multi_sw10` | 528 | +72.28 | 39.25 | 303 | +15.25 | 47.33 |
| 173 | `gap_b3k4` | 207 | +67.39 | 19.78 | 107 | +14.21 | 17.11 |
| 174 | `gap_b3k10` | 241 | +65.65 | 23.72 | 135 | +20.27 | 21.12 |
| 175 | `gap_b3k6` | 220 | +62.40 | 26.06 | 122 | +19.81 | 18.85 |
| 176 | `gap_b3k8` | 233 | +55.36 | 26.53 | 128 | +18.60 | 20.03 |
| 177 | `gap_profit_stage5` | 501 | +53.68 | 43.32 | 282 | +15.29 | 44.80 |
| 178 | `decayG_u` | 138 | +50.72 | 41.95 | 94 | +13.34 | 13.69 |
| 179 | `partial1_multi_sw10` | 553 | +50.19 | 43.84 | 322 | +7.78 | 46.24 |
| 180 | `gap_b3k2` | 167 | +41.78 | 19.07 | 79 | +25.70 | 15.92 |
| 181 | `decayG_c` | 148 | +40.92 | 57.57 | 108 | -5.13 | 22.61 |
| 182 | `decayH_u` | 246 | +32.19 | 53.69 | 132 | -33.67 | 36.79 |
| 183 | `gap_campaign3` | 328 | +30.12 | 37.79 | 188 | +105.95 | 20.23 |
| 184 | `skipwinhalt_single_sw10` | 328 | +29.64 | 60.09 | 203 | +106.37 | 22.57 |
| 185 | `skipwinhalt_multi_sw10` | 323 | +28.35 | 45.34 | 198 | +73.56 | 44.34 |
| 186 | `gap_entry_cap3` | 330 | +27.63 | 38.85 | 188 | +110.07 | 16.69 |
| 187 | `decayH_c` | 261 | +17.03 | 59.13 | 146 | -21.82 | 41.72 |
| 188 | `gap_campaign_max2` | 272 | +7.48 | 50.78 | 149 | +80.52 | 11.88 |
| 189 | `gap_entry_cap2` | 273 | +6.43 | 51.84 | 150 | +83.41 | 10.08 |
| 190 | `gap_campaign_markneg` | 273 | +6.43 | 51.84 | 150 | +83.41 | 10.08 |
| 191 | `gap_campaign_mark05` | 267 | -4.69 | 49.81 | 148 | +47.93 | 10.08 |
| 192 | `decayF_u` | 191 | -21.96 | 51.57 | 122 | -23.87 | 28.84 |
| 193 | `gap_loss_kill1` | 213 | -29.83 | 38.88 | 123 | +113.16 | 30.00 |
| 194 | `gap_window_entry_cap1` | 183 | -33.79 | 45.28 | 96 | +17.29 | 25.11 |
| 195 | `gap_campaign1` | 183 | -34.78 | 46.27 | 96 | +16.28 | 25.11 |
| 196 | `cap4d` | 385 | -35.21 | 57.45 | 238 | +91.99 | 24.47 |
| 197 | `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 | 81 | +17.06 | 37.41 |
| 198 | `skipwin1_single_sw10` | 148 | -38.88 | 53.91 | 91 | +17.15 | 26.33 |
| 199 | `decayF_c` | 206 | -43.62 | 66.80 | 135 | -29.30 | 37.55 |
| 200 | `cap1d` | 236 | -49.73 | 84.28 | 130 | -41.47 | 58.65 |
| 201 | `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 | 72 | +58.90 | 14.74 |
| 202 | `gap_ma_trail` | 554 | -67.38 | 105.97 | 313 | -52.02 | 53.65 |
| 203 | `trail10_multi` | 246 | -247.51 | 248.22 | 149 | -118.33 | 118.33 |
| 204 | `trail06_swingpause_single` | 233 | -276.56 | 276.56 | 116 | -108.77 | 108.77 |
| 205 | `trail10_swingpause_single` | 328 | -311.27 | 313.38 | 134 | -112.82 | 112.82 |

## What the OOS column says

- Shipped champion: IS +239.12 / OOS +72.79.
- 39 of 205 books beat the champion on BOTH eras.
- 69 of 205 books beat it out of sample at all.
- 15 have negative IS net.
- 15 are recorded as MEASURED INERT - wired into the engine but not binding.

## Top 15 by OOS net R - the honest ranking

| # | book | OOS n | OOS net | OOS dd | IS net |
|---|------|------:|--------:|--------:|-------:|
| 1 | `dirmatch_multi_sw10` | 222 | +172.06 | 15.36 | +444.21 |
| 2 | `age25_dirmatch_multi_sw10` | 167 | +165.92 | 9.25 | +357.01 |
| 3 | `dirmatch_single_sw10` | 235 | +140.64 | 18.19 | +442.72 |
| 4 | `utcsat_cap999_nocap` | 284 | +138.68 | 26.17 | +336.98 |
| 5 | `dirmatch_swingpause_single_sw10` | 215 | +133.90 | 15.96 | +273.84 |
| 6 | `age25_multi_sw10` | 194 | +130.15 | 12.42 | +319.22 |
| 7 | `cap999_nocap` | 314 | +130.11 | 33.87 | +360.87 |
| 8 | `trail_half_dr3_nodelay` | 232 | +123.60 | 32.16 | +416.92 |
| 9 | `trail_half_skipn6_dr3` | 208 | +118.86 | 45.50 | +615.15 |
| 10 | `trail_half_skipn8_nodelay` | 211 | +113.28 | 49.56 | +588.76 |
| 11 | `gap_loss_kill1` | 123 | +113.16 | 30.00 | -29.83 |
| 12 | `gap_entry_cap3` | 188 | +110.07 | 16.69 | +27.63 |
| 13 | `gap_campaign4` | 216 | +109.33 | 19.25 | +100.55 |
| 14 | `gap_bm_min09` | 196 | +106.62 | 21.41 | +328.26 |
| 15 | `skipwinhalt_single_sw10` | 203 | +106.37 | 22.57 | +29.64 |

## Books with negative net - dead

| book | IS net | OOS net |
|------|-------:|--------:|
| `gap_campaign_mark05` | -4.69 | +47.93 |
| `decayF_u` | -21.96 | -23.87 |
| `gap_loss_kill1` | -29.83 | +113.16 |
| `gap_window_entry_cap1` | -33.79 | +17.29 |
| `gap_campaign1` | -34.78 | +16.28 |
| `cap4d` | -35.21 | +91.99 |
| `skipwin1_multi_sw10` | -38.54 | +17.06 |
| `skipwin1_single_sw10` | -38.88 | +17.15 |
| `decayF_c` | -43.62 | -29.30 |
| `cap1d` | -49.73 | -41.47 |
| `skipwin2_multi_sw10` | -65.33 | +58.90 |
| `gap_ma_trail` | -67.38 | -52.02 |
| `trail10_multi` | -247.51 | -118.33 |
| `trail06_swingpause_single` | -276.56 | -108.77 |
| `trail10_swingpause_single` | -311.27 | -112.82 |

## What the three audits added today

The trail family, the P36 decay gate and the cap_days family were all
documented, measured elsewhere, and reachable from the engine - and none had a
registry book. They were found by accident. Three exhaustive audits followed:

1. knobs live in the engine, used by scripts, in no book      -> 41 knobs
2. (knob, value) pairs run by scripts, in no book            -> 39 pairs
3. plain engine parameters missed by the first filter       -> 18 pairs

Together 98 previously unmeasured configurations. The third one existed because
the first two filtered on the knob NAME PATTERN `exp_*` and so could not see
`b3_k`, `sl_buf_atr`, `cooldown_bars`, `chop_thresh`, `htf_rr`,
`max_consecutive_losses` or `exp31_lb`. Filtering on the patched engine's actual
signature instead of a regex is the only correct way to ask that question.

Two findings from the last pass worth naming:

- **sl_buf_atr = 0.25 is better out of sample** (+82.53R at dd 31.78 against the
  shipped 0.01 at +72.79 / dd 50.55) and worse in sample. A value the project has
  treated as settled, measured by one script, never pinned.
- **chop_thresh does not bind on any of these books.** Every book here is
  mode=atr_high, which picks the HTF interval set by ATR; chop_thresh is read
  only in mode=chop. It has been decorative across the whole registry.

See backtest/docs/EXPERIMENT_INVENTORY.md for what is not covered and why.

## Reproducing

```
cd backtest/tests
python run_experiment.py <book_key>
```

OOS comes from exp_equity_quality.load_scope('oos'), a different candle file.

Raw unified.simulate_htf_ltf_streak_halt() calls are not interchangeable with
the harness: it injects exp_partial_r and patches the exp_causal_sl branch.
Always go through the harness.
