# Registry books - measured board, IS and true OOS

Every book in `experiment_registry.py`, re-measured on `unified.py` on
2026-10-02 through `run_experiment.py`.

- **IS** = 2023-26 in sample.
- **OOS** = 2021-22, never used to choose anything.

`net` is after costs (55bp fee/side, 2x, 5bp slippage, 1bp funding, 1bp cost).
`dd` is max drawdown in R on the net equity curve.

**Read the OOS column.** A book that wins IS and loses OOS has been fitted to
the sample. Several books here do exactly that and none of them should ship.

`champion` is a book name, not a claim of highest net R.

## Ranked by IS net R

| # | book | IS n | IS net | IS dd | OOS n | OOS net | OOS dd | both>champ |
|---|------|------:|-------:|------:|------:|--------:|--------:|---:|
| 1 | `trail_half_skipn6_dr3` | 373 | +615.15 | 46.15 | 208 | +118.86 | 45.50 | yes |
| 2 | `trail_half_skipn8_nodelay` | 383 | +588.76 | 45.46 | 211 | +113.28 | 49.56 | yes |
| 3 | `trail_half_skipn8_dr1` | 383 | +588.76 | 45.46 | 216 | +103.96 | 58.88 | yes |
| 4 | `trail_half_skipn3_nodelay` | 449 | +561.98 | 43.30 | 253 | +98.60 | 61.40 | yes |
| 5 | `trail_half_delay1_skipn4` | 424 | +556.62 | 44.47 | 234 | +104.98 | 52.50 | yes |
| 6 | `dirmatch_multi_sw10` | 389 | +444.21 | 24.01 | 222 | +172.06 | 15.36 | yes |
| 7 | `dirmatch_single_sw10` | 392 | +442.72 | 31.02 | 235 | +140.64 | 18.19 | yes |
| 8 | `age10_dirmatch_multi_sw10` | 150 | +417.68 | 13.45 | 77 | +61.11 | 7.51 | **no** |
| 9 | `trail_half_dr3_nodelay` | 412 | +416.92 | 44.80 | 232 | +123.60 | 32.16 | yes |
| 10 | `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | 12.90 | 83 | +63.65 | 8.50 | **no** |
| 11 | `trail_half_delay1` | 465 | +385.92 | 51.39 | 272 | +88.74 | 51.72 | yes |
| 12 | `trail_half` | 468 | +384.99 | 51.10 | 269 | +71.73 | 52.08 | **no** |
| 13 | `cap32d` | 522 | +375.53 | 48.39 | 292 | +94.61 | 30.46 | yes |
| 14 | `cap999_nocap` | 592 | +360.87 | 54.25 | 314 | +130.11 | 33.87 | yes |
| 15 | `utcsat_entry_minus_1` | 454 | +358.92 | 21.18 | 253 | +60.21 | 29.38 | **no** |
| 16 | `trail_skipn4` | 439 | +357.15 | 43.96 | 243 | +61.05 | 75.60 | **no** |
| 17 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | 21.47 | 167 | +165.92 | 9.25 | yes |
| 18 | `cap48d` | 556 | +351.27 | 54.25 | 302 | +87.68 | 33.00 | yes |
| 19 | `lb30_w24_ext2.0` | 380 | +344.61 | 36.58 | 176 | +32.84 | 41.00 | **no** |
| 20 | `utcsat_cap999_nocap` | 537 | +336.98 | 42.82 | 284 | +138.68 | 26.17 | yes |
| 21 | `lb30_w24_ext1.5` | 337 | +336.67 | 35.92 | 143 | +15.01 | 40.73 | **no** |
| 22 | `champion_multi_sw10` | 500 | +325.78 | 27.72 | 279 | +70.15 | 53.19 | **no** |
| 23 | `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | 27.72 | 279 | +70.15 | 53.19 | **no** |
| 24 | `champion_multi_sw10_entry1` | 500 | +325.75 | 27.72 | 279 | +70.15 | 53.19 | **no** |
| 25 | `age25_multi_sw10` | 293 | +319.22 | 25.86 | 194 | +130.15 | 12.42 | yes |
| 26 | `fullstack_wage10_cd0_single_sw10` | 234 | +316.64 | 23.96 | 158 | +28.72 | 29.45 | **no** |
| 27 | `utcsat_chopband_multi_sw10` | 392 | +315.45 | 36.41 | 235 | +91.73 | 22.94 | yes |
| 28 | `lb30_w24_ext2.5` | 405 | +315.08 | 42.82 | 178 | +43.34 | 41.06 | **no** |
| 29 | `lb30_w24_ext3.0` | 415 | +314.51 | 42.27 | 183 | +36.09 | 45.09 | **no** |
| 30 | `wage10_swingpause_wskip_single_sw10` | 330 | +308.65 | 26.27 | 190 | +25.00 | 27.59 | **no** |
| 31 | `curfew624_utcsat_multi_sw10` | 377 | +304.72 | 31.95 | 211 | +51.72 | 26.83 | **no** |
| 32 | `ext2_utcsat_multi_sw10` | 417 | +301.86 | 41.77 | 237 | +80.50 | 24.30 | yes |
| 33 | `nowknd_multi_sw10` | 403 | +301.39 | 25.88 | 219 | +24.76 | 29.76 | **no** |
| 34 | `bm05_utcsat_multi_sw10` | 420 | +298.15 | 35.33 | 237 | +77.76 | 24.64 | yes |
| 35 | `b2doji_utcsat_multi_sw10` | 422 | +295.70 | 36.16 | 229 | +63.18 | 28.56 | **no** |
| 36 | `fullstack_atrr_utcsat_multi_sw10` | 311 | +295.46 | 26.61 | 201 | +36.07 | 31.36 | **no** |
| 37 | `htfrr2_multi_sw10` | 423 | +292.86 | 35.68 | 230 | +45.93 | 41.00 | **no** |
| 38 | `ext25_utcsat_multi_sw10` | 442 | +281.30 | 36.18 | 249 | +75.35 | 24.64 | yes |
| 39 | `utcsat_multi_sw10` | 453 | +279.47 | 35.54 | 254 | +66.90 | 24.64 | **no** |
| 40 | `utcsat_cap16d` | 453 | +279.47 | 35.54 | 254 | +66.90 | 24.64 | **no** |
| 41 | `ext4_utcsat_multi_sw10` | 454 | +279.16 | 35.54 | 256 | +70.25 | 24.64 | **no** |
| 42 | `ext35_utcsat_multi_sw10` | 454 | +279.16 | 35.54 | 256 | +70.25 | 24.64 | **no** |
| 43 | `nowknd_single_sw10` | 401 | +278.06 | 32.28 | 230 | +31.29 | 31.31 | **no** |
| 44 | `bm05_multi_sw10` | 456 | +277.86 | 46.63 | 261 | +87.84 | 38.73 | yes |
| 45 | `lb30_halt0` | 484 | +276.86 | 60.28 | 234 | +44.88 | 48.33 | **no** |
| 46 | `dirmatch_swingpause_single_sw10` | 362 | +273.84 | 30.04 | 215 | +133.90 | 15.96 | yes |
| 47 | `wage24_utcsat_multi_sw10` | 332 | +273.80 | 21.70 | 199 | +63.75 | 28.74 | **no** |
| 48 | `wage12_utcsat_multi_sw10` | 391 | +273.70 | 31.66 | 227 | +91.60 | 23.33 | yes |
| 49 | `cap20d` | 498 | +269.60 | 46.03 | 286 | +87.42 | 35.27 | yes |
| 50 | `chopband_multi_sw10` | 432 | +268.79 | 41.70 | 257 | +85.94 | 42.74 | yes |
| 51 | `fullstack_swingpause_single_sw10` | 262 | +268.27 | 24.22 | 168 | +24.93 | 28.54 | **no** |
| 52 | `lb30_persist5` | 410 | +267.30 | 49.18 | 191 | +6.55 | 34.33 | **no** |
| 53 | `combined_b2age_utcsat_multi_sw10` | 407 | +265.38 | 36.00 | 221 | +67.87 | 25.80 | **no** |
| 54 | `bm08_utcsat_multi_sw10` | 359 | +264.66 | 29.71 | 192 | +91.58 | 19.02 | yes |
| 55 | `chopband_atrr_swingpause_single_sw10` | 321 | +264.45 | 35.77 | 211 | +35.66 | 37.85 | **no** |
| 56 | `trail_delay1` | 501 | +263.62 | 45.37 | 279 | +69.65 | 54.91 | **no** |
| 57 | `wage12_swingpause_single_sw10` | 323 | +262.31 | 27.48 | 183 | +2.28 | 34.44 | **no** |
| 58 | `age50_utcsat_multi_sw10` | 434 | +261.40 | 37.95 | 246 | +71.71 | 23.44 | **no** |
| 59 | `bm05_multi_sw20` | 458 | +259.80 | 51.69 | 248 | +17.03 | 41.93 | **no** |
| 60 | `rmax15_multi_sw10` | 407 | +255.56 | 50.19 | 166 | +2.95 | 41.46 | **no** |
| 61 | `cap24d` | 510 | +248.83 | 46.68 | 293 | +0.49 | 49.68 | **no** |
| 62 | `bm08_multi_sw10` | 391 | +248.81 | 38.30 | 210 | +100.42 | 28.22 | yes |
| 63 | `wage8_swingpause_single_sw10` | 329 | +247.85 | 29.39 | 192 | +22.87 | 27.65 | **no** |
| 64 | `lb30_chop55_persist2` | 429 | +247.51 | 46.17 | 222 | +28.95 | 42.93 | **no** |
| 65 | `utcsat_swingpause_single_sw10` | 406 | +245.70 | 36.47 | 245 | +85.04 | 18.54 | yes |
| 66 | `union_multi` | 137 | +245.39 | 16.45 | 53 | +54.03 | 6.11 | **no** |
| 67 | `wage16_swingpause_single_sw10` | 302 | +244.80 | 28.04 | 176 | +20.16 | 27.97 | **no** |
| 68 | `bm05_swingpause_single_sw10` | 425 | +243.81 | 49.00 | 253 | +71.34 | 37.92 | **no** |
| 69 | `swingpause_single_sw10` | 451 | +242.55 | 48.67 | 269 | +76.02 | 37.64 | yes |
| 70 | `swingpause_cd0_single_sw10` | 451 | +242.55 | 48.67 | 269 | +76.02 | 37.64 | yes |
| 71 | `chopband_swingpause_single_sw10` | 395 | +241.65 | 38.57 | 238 | +75.51 | 46.11 | yes |
| 72 | `atrr_swingpause_single_sw10` | 381 | +241.57 | 46.77 | 242 | +26.97 | 39.49 | **no** |
| 73 | `swingpause_multi_sw10` | 444 | +241.06 | 41.60 | 249 | +76.69 | 35.70 | yes |
| 74 | `wage24_multi_sw10` | 364 | +240.58 | 31.33 | 218 | +76.29 | 34.05 | yes |
| 75 | `atrr_cd0_swingpause_single_sw10` | 385 | +240.56 | 47.35 | 245 | +20.89 | 45.95 | **no** |
| 76 | `persist8_multi_sw10` | 499 | +239.12 | 46.85 | 282 | +37.31 | 50.39 | **no** |
| 77 | `persist6_multi_sw10` | 499 | +239.12 | 46.85 | 279 | +79.99 | 48.95 | OOS only |
| 78 | `champion_multi_sw10_leg` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 | **no** |
| 79 | `cap16d` | 499 | +239.12 | 46.85 | 280 | +72.79 | 50.55 | **no** |
| 80 | `persist5_multi_sw10` | 498 | +239.00 | 46.85 | 286 | +79.62 | 50.29 | OOS only |
| 81 | `baseline_no_partial_sw10` | 502 | +238.45 | 53.86 | 294 | +78.35 | 46.46 | OOS only |
| 82 | `causalsl_utcsat_multi_sw10` | 448 | +237.43 | 36.53 | 256 | +79.48 | 22.60 | OOS only |
| 83 | `legskip2_multi_sw10` | 269 | +235.96 | 29.15 | 162 | +15.67 | 35.65 | **no** |
| 84 | `baseline_no_partial_sw20` | 496 | +232.38 | 61.58 | 268 | -7.56 | 56.52 | **no** |
| 85 | `persist4_multi_sw10` | 501 | +231.70 | 46.85 | 286 | +90.09 | 35.74 | OOS only |
| 86 | `persist3_multi_sw10` | 495 | +229.45 | 53.26 | 284 | +83.87 | 36.29 | OOS only |
| 87 | `rmax10_swingpause_single_sw10` | 294 | +228.59 | 47.91 | 92 | +14.67 | 42.64 | **no** |
| 88 | `wage24_swingpause_single_sw10` | 269 | +228.40 | 20.87 | 163 | +33.80 | 30.46 | **no** |
| 89 | `nowknd_swingpause_single_sw10` | 365 | +228.26 | 30.31 | 205 | +20.30 | 27.28 | **no** |
| 90 | `htfrr4_multi_sw10` | 397 | +222.36 | 38.81 | 221 | +69.94 | 36.49 | **no** |
| 91 | `htfrr25_multi_sw10` | 419 | +221.11 | 34.27 | 223 | +75.51 | 31.27 | OOS only |
| 92 | `opt_ml_cd0_mb10` | 510 | +215.50 | 60.37 | 251 | -6.29 | 62.26 | **no** |
| 93 | `champion_multi_sw10_entry_both` | 495 | +215.09 | 34.72 | 281 | +82.63 | 45.26 | OOS only |
| 94 | `champion_multi_sw20` | 493 | +213.33 | 50.64 | 265 | +8.43 | 46.82 | **no** |
| 95 | `fliponly_swingpause_single_sw10` | 268 | +211.34 | 29.50 | 164 | +0.15 | 41.52 | **no** |
| 96 | `wage20_swingpause_single_sw10` | 283 | +205.35 | 26.45 | 170 | +47.56 | 23.87 | **no** |
| 97 | `fliponly_multi_sw10` | 286 | +202.45 | 35.43 | 155 | -10.70 | 52.55 | **no** |
| 98 | `htfrr35_multi_sw10` | 406 | +202.29 | 41.04 | 227 | +51.62 | 45.85 | **no** |
| 99 | `dualunion_multi` | 90 | +201.70 | 9.04 | 38 | +39.74 | 7.91 | **no** |
| 100 | `curfew624_swingpause_single_sw10` | 300 | +198.91 | 23.17 | 176 | +38.02 | 27.03 | **no** |
| 101 | `opt_ml_cd10_mb10` | 446 | +198.09 | 44.56 | 216 | +3.24 | 49.44 | **no** |
| 102 | `wage12_swingpause_single_nowknd_sw10` | 392 | +196.94 | 41.23 | 236 | +58.09 | 56.84 | **no** |
| 103 | `champion_single_sw20` | 496 | +196.28 | 58.21 | 269 | +6.73 | 48.49 | **no** |
| 104 | `causalsl_swingpause_single_sw10` | 446 | +195.67 | 45.42 | 266 | +82.76 | 27.83 | OOS only |
| 105 | `b2doji_swingpause_single_sw10` | 414 | +188.71 | 46.29 | 244 | +17.68 | 52.68 | **no** |
| 106 | `rmax15_swingpause_single_sw10` | 376 | +187.78 | 57.54 | 161 | -5.83 | 45.76 | **no** |
| 107 | `cap8d` | 472 | +185.83 | 47.32 | 273 | +52.45 | 54.05 | **no** |
| 108 | `causalsl_multi_sw10` | 493 | +185.08 | 47.70 | 283 | +82.65 | 43.92 | OOS only |
| 109 | `chopband_atrr_swingpause_single_sw20` | 329 | +175.90 | 44.83 | 202 | +12.34 | 42.67 | **no** |
| 110 | `atrr_swingpause_single_sw20` | 390 | +171.57 | 50.43 | 223 | -8.48 | 52.53 | **no** |
| 111 | `champion_single_sw10` | 503 | +170.91 | 50.48 | 295 | +78.57 | 38.11 | OOS only |
| 112 | `swingpause_single_sw20` | 444 | +154.08 | 57.93 | 248 | +6.80 | 52.53 | **no** |
| 113 | `cap12d` | 471 | +153.72 | 46.71 | 282 | +71.16 | 50.54 | **no** |
| 114 | `wage12_swingpause_single_sw20` | 394 | +153.32 | 43.96 | 215 | +24.50 | 37.07 | **no** |
| 115 | `chopband_swingpause_single_sw20` | 388 | +146.42 | 51.76 | 227 | +22.17 | 43.11 | **no** |
| 116 | `opt_cd10_w24` | 300 | +144.13 | 47.02 | 145 | +12.70 | 34.90 | **no** |
| 117 | `a4_w24_ext1.5` | 300 | +144.13 | 47.02 | 145 | +12.70 | 34.90 | **no** |
| 118 | `lb30_halt6_cd0` | 538 | +140.96 | 84.06 | 252 | +15.37 | 75.01 | **no** |
| 119 | `age50_swingpause_single_sw10` | 429 | +137.14 | 48.05 | 264 | +68.19 | 43.82 | **no** |
| 120 | `a4_w24_ext3.0` | 368 | +133.69 | 48.14 | 187 | +28.37 | 38.40 | **no** |
| 121 | `partial5_multi_sw10` | 501 | +131.63 | 46.01 | 282 | +43.50 | 47.16 | **no** |
| 122 | `utc_wknd_swingpause_single_sw10` | 350 | +121.03 | 40.49 | 197 | -15.69 | 30.82 | **no** |
| 123 | `partial4_multi_sw10` | 506 | +106.70 | 45.39 | 281 | +36.04 | 46.57 | **no** |
| 124 | `partial3_multi_sw10` | 513 | +92.55 | 39.75 | 283 | +23.41 | 46.85 | **no** |
| 125 | `partial2_multi_sw10` | 528 | +72.28 | 39.25 | 303 | +15.25 | 47.33 | **no** |
| 126 | `partial1_multi_sw10` | 553 | +50.19 | 43.84 | 322 | +7.78 | 46.24 | **no** |
| 127 | `skipwinhalt_single_sw10` | 328 | +29.64 | 60.09 | 203 | +106.37 | 22.57 | OOS only |
| 128 | `skipwinhalt_multi_sw10` | 323 | +28.35 | 45.34 | 198 | +73.56 | 44.34 | OOS only |
| 129 | `cap4d` | 385 | -35.21 | 57.45 | 238 | +91.99 | 24.47 | OOS only |
| 130 | `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 | 81 | +17.06 | 37.41 | **no** |
| 131 | `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 | 81 | +17.06 | 37.41 | **no** |
| 132 | `skipwin1_single_sw10` | 148 | -38.88 | 53.91 | 91 | +17.15 | 26.33 | **no** |
| 133 | `cap1d` | 236 | -49.73 | 84.28 | 130 | -41.47 | 58.65 | **no** |
| 134 | `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 | 72 | +58.90 | 14.74 | **no** |
| 135 | `trail10_multi` | 246 | -247.51 | 248.22 | 149 | -118.33 | 118.33 | **no** |
| 136 | `trail06_swingpause_single` | 233 | -276.56 | 276.56 | 116 | -108.77 | 108.77 | **no** |
| 137 | `trail10_swingpause_single` | 328 | -311.27 | 313.38 | 134 | -112.82 | 112.82 | **no** |

## What the OOS column says

- Shipped champion: IS +239.12 / OOS +72.79.
- 32 of 137 books beat the champion on BOTH eras.
- 46 of 137 books beat it out of sample at all, regardless of IS.

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
| 11 | `skipwinhalt_single_sw10` | 203 | +106.37 | 22.57 | +29.64 |
| 12 | `trail_half_delay1_skipn4` | 234 | +104.98 | 52.50 | +556.62 |
| 13 | `trail_half_skipn8_dr1` | 216 | +103.96 | 58.88 | +588.76 |
| 14 | `bm08_multi_sw10` | 210 | +100.42 | 28.22 | +248.81 |
| 15 | `trail_half_skipn3_nodelay` | 253 | +98.60 | 61.40 | +561.98 |

## Negative on IS

| book | IS net | OOS net |
|------|-------:|--------:|
| `cap4d` | -35.21 | +91.99 |
| `skipwin1_multi_sw10` | -38.54 | +17.06 |
| `skip1pause_multi_sw10` | -38.54 | +17.06 |
| `skipwin1_single_sw10` | -38.88 | +17.15 |
| `cap1d` | -49.73 | -41.47 |
| `skipwin2_multi_sw10` | -65.33 | +58.90 |
| `trail10_multi` | -247.51 | -118.33 |
| `trail06_swingpause_single` | -276.56 | -108.77 |
| `trail10_swingpause_single` | -311.27 | -112.82 |

## Reproducing

```
cd backtest/tests
python run_experiment.py <book_key>
```

OOS figures come from `exp_equity_quality.load_scope('oos')`, which uses
`load_unseen` - a different candle file from the in-sample scope.

Raw `unified.simulate_htf_ltf_streak_halt()` calls are not interchangeable with
the harness: it injects `exp_partial_r` and patches the `exp_causal_sl` branch.
Always go through the harness.
