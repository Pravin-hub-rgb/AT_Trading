# Registry books - measured board, IS and true OOS

Generated FROM the registry, so it cannot drift. 2026-10-02.

Shipped champion: **IS +239.12 / OOS +72.79** (`champion_multi_sw10_leg`).

`net` is after costs. `dd` is max drawdown in R on the **NET** equity curve
(r_multiple minus cost_r). The runner prints a GROSS-basis drawdown under the
label `DD`; the two differ by ~10R per book. Pins name the net one `dd_net`.

`champion` is a book name, not a claim of highest net R.

---

## The 205 books, split three ways

| | count | meaning |
|---|---:|---|
| **Candidates** | 39 | positive net on BOTH eras |
| In-sample only | 136 | wins IS, does not win OOS |
| Reference | 30 | negative net or a knob that provably does nothing |

**A registry book means a thing worth acting on.** The reference rows are kept
because the measurement is real and `exp_pinverify` still checks them, but they
are not candidates and do not count as anything.

---

## Candidates - beat the champion on BOTH eras

Ranked by OOS net, because that is the column that decides whether a result is
real. Read the OOS drawdown column too: some of these buy their R with risk
and some do not.

| # | book | IS n | IS net | IS dd | OOS n | OOS net | OOS dd |
|---|------|------:|-------:|------:|------:|--------:|--------:|
| 1 | `dirmatch_multi_sw10` | 389 | +444.21 | 24.01 | 222 | +172.06 | 15.36 |
| 2 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | 21.47 | 167 | +165.92 | 9.25 |
| 3 | `dirmatch_single_sw10` | 392 | +442.72 | 31.02 | 235 | +140.64 | 18.19 |
| 4 | `utcsat_cap999_nocap` | 537 | +336.98 | 42.82 | 284 | +138.68 | 26.17 |
| 5 | `dirmatch_swingpause_single_sw10` | 362 | +273.84 | 30.04 | 215 | +133.90 | 15.96 |
| 6 | `age25_multi_sw10` | 293 | +319.22 | 25.86 | 194 | +130.15 | 12.42 |
| 7 | `cap999_nocap` | 592 | +360.87 | 54.25 | 314 | +130.11 | 33.87 |
| 8 | `trail_half_dr3_nodelay` | 412 | +416.92 | 44.80 | 232 | +123.60 | 32.16 |
| 9 | `trail_half_skipn6_dr3` | 373 | +615.15 | 46.15 | 208 | +118.86 | 45.50 |
| 10 | `trail_half_skipn8_nodelay` | 383 | +588.76 | 45.46 | 211 | +113.28 | 49.56 |
| 11 | `gap_bm_min09` | 370 | +328.26 | 29.02 | 196 | +106.62 | 21.41 |
| 12 | `trail_half_delay1_skipn4` | 424 | +556.62 | 44.47 | 234 | +104.98 | 52.50 |
| 13 | `trail_half_skipn8_dr1` | 383 | +588.76 | 45.46 | 216 | +103.96 | 58.88 |
| 14 | `bm08_multi_sw10` | 391 | +248.81 | 38.30 | 210 | +100.42 | 28.22 |
| 15 | `trail_half_skipn3_nodelay` | 449 | +561.98 | 43.30 | 253 | +98.60 | 61.40 |
| 16 | `decayE_c` | 245 | +254.21 | 28.76 | 139 | +95.96 | 15.13 |
| 17 | `cap32d` | 522 | +375.53 | 48.39 | 292 | +94.61 | 30.46 |
| 18 | `decayE_u` | 217 | +250.36 | 25.90 | 118 | +94.53 | 17.18 |
| 19 | `utcsat_chopband_multi_sw10` | 392 | +315.45 | 36.41 | 235 | +91.73 | 22.94 |
| 20 | `wage12_utcsat_multi_sw10` | 391 | +273.70 | 31.66 | 227 | +91.60 | 23.33 |
| 21 | `bm08_utcsat_multi_sw10` | 359 | +264.66 | 29.71 | 192 | +91.58 | 19.02 |
| 22 | `trail_half_delay1` | 465 | +385.92 | 51.39 | 272 | +88.74 | 51.72 |
| 23 | `bm05_multi_sw10` | 456 | +277.86 | 46.63 | 261 | +87.84 | 38.73 |
| 24 | `cap48d` | 556 | +351.27 | 54.25 | 302 | +87.68 | 33.00 |
| 25 | `cap20d` | 498 | +269.60 | 46.03 | 286 | +87.42 | 35.27 |
| 26 | `gap_cooldown20` | 484 | +278.45 | 46.85 | 270 | +87.36 | 38.17 |
| 27 | `chopband_multi_sw10` | 432 | +268.79 | 41.70 | 257 | +85.94 | 42.74 |
| 28 | `utcsat_swingpause_single_sw10` | 406 | +245.70 | 36.47 | 245 | +85.04 | 18.54 |
| 29 | `gap_bm_min07` | 414 | +266.50 | 41.29 | 224 | +84.81 | 32.89 |
| 30 | `gap_bm_min06` | 445 | +284.52 | 43.68 | 245 | +82.81 | 32.65 |
| 31 | `ext2_utcsat_multi_sw10` | 417 | +301.86 | 41.77 | 237 | +80.50 | 24.30 |
| 32 | `bm05_utcsat_multi_sw10` | 420 | +298.15 | 35.33 | 237 | +77.76 | 24.64 |
| 33 | `swingpause_multi_sw10` | 444 | +241.06 | 41.60 | 249 | +76.69 | 35.70 |
| 34 | `gap_wage24` | 364 | +240.58 | 31.33 | 218 | +76.29 | 34.05 |
| 35 | `wage24_multi_sw10` | 364 | +240.58 | 31.33 | 218 | +76.29 | 34.05 |
| 36 | `swingpause_single_sw10` | 451 | +242.55 | 48.67 | 269 | +76.02 | 37.64 |
| 37 | `chopband_swingpause_single_sw10` | 395 | +241.65 | 38.57 | 238 | +75.51 | 46.11 |
| 38 | `ext25_utcsat_multi_sw10` | 442 | +281.30 | 36.18 | 249 | +75.35 | 24.64 |
| 39 | `gap_cd15` | 488 | +298.14 | 46.85 | 273 | +74.67 | 46.67 |

## In-sample only - do not ship on these

Positive in sample, no better than champion out of sample. The gap between this
table and the one above is the whole reason the OOS column exists.

| book | IS n | IS net | OOS net | vs champion OOS |
|------|------:|-------:|--------:|---:|
| `age10_dirmatch_multi_sw10` | 150 | +417.68 | +61.11 | -11.68 |
| `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | +63.65 | -9.14 |
| `trail_half` | 468 | +384.99 | +71.73 | -1.06 |
| `utcsat_entry_minus_1` | 454 | +358.92 | +60.21 | -12.58 |
| `trail_skipn4` | 439 | +357.15 | +61.05 | -11.74 |
| `lb30_w24_ext2.0` | 380 | +344.61 | +32.84 | -39.95 |
| `lb30_w24_ext1.5` | 337 | +336.67 | +15.01 | -57.78 |
| `champion_multi_sw10` | 500 | +325.78 | +70.15 | -2.64 |
| `champion_multi_sw10_entry1` | 500 | +325.75 | +70.15 | -2.64 |
| `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | +70.15 | -2.64 |
| `fullstack_wage10_cd0_single_sw10` | 234 | +316.64 | +28.72 | -44.07 |
| `lb30_w24_ext2.5` | 405 | +315.08 | +43.34 | -29.45 |
| `lb30_w24_ext3.0` | 415 | +314.51 | +36.09 | -36.70 |
| `wage10_swingpause_wskip_single_sw10` | 330 | +308.65 | +25.00 | -47.79 |
| `curfew624_utcsat_multi_sw10` | 377 | +304.72 | +51.72 | -21.07 |
| `nowknd_multi_sw10` | 403 | +301.39 | +24.76 | -48.03 |
| `b2doji_utcsat_multi_sw10` | 422 | +295.70 | +63.18 | -9.61 |
| `fullstack_atrr_utcsat_multi_sw10` | 311 | +295.46 | +36.07 | -36.72 |
| `htfrr2_multi_sw10` | 423 | +292.86 | +45.93 | -26.86 |
| `decayA_u` | 453 | +279.47 | +66.90 | -5.89 |
| `utcsat_cap16d` | 453 | +279.47 | +66.90 | -5.89 |
| `utcsat_multi_sw10` | 453 | +279.47 | +66.90 | -5.89 |
| `ext35_utcsat_multi_sw10` | 454 | +279.16 | +70.25 | -2.54 |
| `ext4_utcsat_multi_sw10` | 454 | +279.16 | +70.25 | -2.54 |
| `nowknd_single_sw10` | 401 | +278.06 | +31.29 | -41.50 |
| `lb30_halt0` | 484 | +276.86 | +44.88 | -27.91 |
| `wage24_utcsat_multi_sw10` | 332 | +273.80 | +63.75 | -9.04 |
| `fullstack_swingpause_single_sw10` | 262 | +268.27 | +24.93 | -47.86 |
| `lb30_persist5` | 410 | +267.30 | +6.55 | -66.24 |
| `combined_b2age_utcsat_multi_sw10` | 407 | +265.38 | +67.87 | -4.92 |
| `chopband_atrr_swingpause_single_sw10` | 321 | +264.45 | +35.66 | -37.13 |
| `decayB_c` | 303 | +263.90 | +70.97 | -1.82 |
| `trail_delay1` | 501 | +263.62 | +69.65 | -3.14 |
| `gap_trail_prevbar` | 501 | +263.62 | +69.65 | -3.14 |
| `wage12_swingpause_single_sw10` | 323 | +262.31 | +2.28 | -70.51 |
| `age50_utcsat_multi_sw10` | 434 | +261.40 | +71.71 | -1.08 |
| `bm05_multi_sw20` | 458 | +259.80 | +17.03 | -55.76 |
| `rmax15_multi_sw10` | 407 | +255.56 | +2.95 | -69.84 |
| `cap24d` | 510 | +248.83 | +0.49 | -72.30 |
| `wage8_swingpause_single_sw10` | 329 | +247.85 | +22.87 | -49.92 |
| `lb30_chop55_persist2` | 429 | +247.51 | +28.95 | -43.84 |
| `union_multi` | 137 | +245.39 | +54.03 | -18.76 |
| `wage16_swingpause_single_sw10` | 302 | +244.80 | +20.16 | -52.63 |
| `bm05_swingpause_single_sw10` | 425 | +243.81 | +71.34 | -1.45 |
| `atrr_swingpause_single_sw10` | 381 | +241.57 | +26.97 | -45.82 |
| `atrr_cd0_swingpause_single_sw10` | 385 | +240.56 | +20.89 | -51.90 |
| `gap_mcl5` | 523 | +240.02 | +72.73 | -0.06 |
| `gap_skip_decisive` | 499 | +239.12 | +104.12 | +31.33 |
| `decayA_c` | 499 | +239.12 | +72.79 | +0.00 |
| `cap16d` | 499 | +239.12 | +72.79 | +0.00 |
| `champion_multi_sw10_leg` | 499 | +239.12 | +72.79 | +0.00 |
| `persist6_multi_sw10` | 499 | +239.12 | +79.99 | +7.20 |
| `persist8_multi_sw10` | 499 | +239.12 | +37.31 | -35.48 |
| `persist5_multi_sw10` | 498 | +239.00 | +79.62 | +6.83 |
| `gap_cd5` | 502 | +238.56 | +68.59 | -4.20 |
| `gap_cooldown4` | 502 | +238.56 | +70.69 | -2.10 |
| `gap_persist1` | 502 | +238.45 | +78.35 | +5.56 |
| `baseline_no_partial_sw10` | 502 | +238.45 | +78.35 | +5.56 |
| `causalsl_utcsat_multi_sw10` | 448 | +237.43 | +79.48 | +6.69 |
| `legskip2_multi_sw10` | 269 | +235.96 | +15.67 | -57.12 |
| `baseline_no_partial_sw20` | 496 | +232.38 | -7.56 | -80.35 |
| `persist4_multi_sw10` | 501 | +231.70 | +90.09 | +17.30 |
| `gap_curfew_16_20` | 470 | +231.33 | +61.84 | -10.95 |
| `persist3_multi_sw10` | 495 | +229.45 | +83.87 | +11.08 |
| `rmax10_swingpause_single_sw10` | 294 | +228.59 | +14.67 | -58.12 |
| `wage24_swingpause_single_sw10` | 269 | +228.40 | +33.80 | -38.99 |
| `nowknd_swingpause_single_sw10` | 365 | +228.26 | +20.30 | -52.49 |
| `gap_wage28` | 341 | +223.08 | +87.58 | +14.79 |
| `htfrr4_multi_sw10` | 397 | +222.36 | +69.94 | -2.85 |
| `htfrr25_multi_sw10` | 419 | +221.11 | +75.51 | +2.72 |
| `decayB_u` | 270 | +220.96 | +91.62 | +18.83 |
| `opt_ml_cd0_mb10` | 510 | +215.50 | -6.29 | -79.08 |
| `champion_multi_sw10_entry_both` | 495 | +215.09 | +82.63 | +9.84 |
| `gap_wage32` | 331 | +214.48 | +76.96 | +4.17 |
| `gap_slbuf010` | 497 | +214.36 | +62.66 | -10.13 |
| `champion_multi_sw20` | 493 | +213.33 | +8.43 | -64.36 |
| `fliponly_swingpause_single_sw10` | 268 | +211.34 | +0.15 | -72.64 |
| `gap_curfew_a4_b8` | 470 | +209.93 | +81.76 | +8.97 |
| `wage20_swingpause_single_sw10` | 283 | +205.35 | +47.56 | -25.23 |
| `fliponly_multi_sw10` | 286 | +202.45 | -10.70 | -83.49 |
| `htfrr35_multi_sw10` | 406 | +202.29 | +51.62 | -21.17 |
| `dualunion_multi` | 90 | +201.70 | +39.74 | -33.05 |
| `curfew624_swingpause_single_sw10` | 300 | +198.91 | +38.02 | -34.77 |
| `gap_r_cap3` | 459 | +198.53 | +80.16 | +7.37 |
| `opt_ml_cd10_mb10` | 446 | +198.09 | +3.24 | -69.55 |
| `wage12_swingpause_single_nowknd_sw10` | 392 | +196.94 | +58.09 | -14.70 |
| `champion_single_sw20` | 496 | +196.28 | +6.73 | -66.06 |
| `causalsl_swingpause_single_sw10` | 446 | +195.67 | +82.76 | +9.97 |
| `decayD_c` | 353 | +194.24 | +45.26 | -27.53 |
| `b2doji_swingpause_single_sw10` | 414 | +188.71 | +17.68 | -55.11 |
| `gap_slbuf025` | 497 | +188.41 | +82.53 | +9.74 |
| `rmax15_swingpause_single_sw10` | 376 | +187.78 | -5.83 | -78.62 |
| `cap8d` | 472 | +185.83 | +52.45 | -20.34 |
| `causalsl_multi_sw10` | 493 | +185.08 | +82.65 | +9.86 |
| `chopband_atrr_swingpause_single_sw20` | 329 | +175.90 | +12.34 | -60.45 |
| `decayC_u` | 273 | +173.31 | +55.52 | -17.27 |
| `atrr_swingpause_single_sw20` | 390 | +171.57 | -8.48 | -81.27 |
| `champion_single_sw10` | 503 | +170.91 | +78.57 | +5.78 |
| `gap_window_r_cap2` | 449 | +163.31 | +77.92 | +5.13 |
| `gap_r_cap1` | 448 | +162.70 | +66.10 | -6.69 |
| `decayC_c` | 299 | +154.64 | +58.98 | -13.81 |
| `swingpause_single_sw20` | 444 | +154.08 | +6.80 | -65.99 |
| `cap12d` | 471 | +153.72 | +71.16 | -1.63 |
| `wage12_swingpause_single_sw20` | 394 | +153.32 | +24.50 | -48.29 |
| `decayD_u` | 324 | +150.08 | +70.77 | -2.02 |
| `chopband_swingpause_single_sw20` | 388 | +146.42 | +22.17 | -50.62 |
| `a4_w24_ext1.5` | 300 | +144.13 | +12.70 | -60.09 |
| `opt_cd10_w24` | 300 | +144.13 | +12.70 | -60.09 |
| `lb30_halt6_cd0` | 538 | +140.96 | +15.37 | -57.42 |
| `age50_swingpause_single_sw10` | 429 | +137.14 | +68.19 | -4.60 |
| `gap_pivot_trail` | 514 | +133.69 | -4.57 | -77.36 |
| `a4_w24_ext3.0` | 368 | +133.69 | +28.37 | -44.42 |
| `partial5_multi_sw10` | 501 | +131.63 | +43.50 | -29.29 |
| `utc_wknd_swingpause_single_sw10` | 350 | +121.03 | -15.69 | -88.48 |
| `partial4_multi_sw10` | 506 | +106.70 | +36.04 | -36.75 |
| `gap_campaign4` | 369 | +100.55 | +109.33 | +36.54 |
| `partial3_multi_sw10` | 513 | +92.55 | +23.41 | -49.38 |
| `partial2_multi_sw10` | 528 | +72.28 | +15.25 | -57.54 |
| `gap_b3k4` | 207 | +67.39 | +14.21 | -58.58 |
| `gap_b3k10` | 241 | +65.65 | +20.27 | -52.52 |
| `gap_b3k6` | 220 | +62.40 | +19.81 | -52.98 |
| `gap_b3k8` | 233 | +55.36 | +18.60 | -54.19 |
| `gap_profit_stage5` | 501 | +53.68 | +15.29 | -57.50 |
| `decayG_u` | 138 | +50.72 | +13.34 | -59.45 |
| `partial1_multi_sw10` | 553 | +50.19 | +7.78 | -65.01 |
| `gap_b3k2` | 167 | +41.78 | +25.70 | -47.09 |
| `decayG_c` | 148 | +40.92 | -5.13 | -77.92 |
| `decayH_u` | 246 | +32.19 | -33.67 | -106.46 |
| `gap_campaign3` | 328 | +30.12 | +105.95 | +33.16 |
| `skipwinhalt_single_sw10` | 328 | +29.64 | +106.37 | +33.58 |
| `skipwinhalt_multi_sw10` | 323 | +28.35 | +73.56 | +0.77 |
| `gap_entry_cap3` | 330 | +27.63 | +110.07 | +37.28 |
| `decayH_c` | 261 | +17.03 | -21.82 | -94.61 |
| `gap_campaign_max2` | 272 | +7.48 | +80.52 | +7.73 |
| `gap_campaign_markneg` | 273 | +6.43 | +83.41 | +10.62 |
| `gap_entry_cap2` | 273 | +6.43 | +83.41 | +10.62 |

## Reference - measured, and it does not pay

| book | IS net | OOS net | why |
|------|-------:|--------:|-----|
| `gap_inert_event_shift` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_chop52` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_chop61` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_lb50` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_lb60` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_htfrr3` | +239.12 | +72.79 | knob does not bind |
| `gap_campaign1` | -34.78 | +16.28 | negative net |
| `gap_inert_cohort1` | +239.12 | +72.79 | knob does not bind |
| `gap_campaign_mark05` | -4.69 | +47.93 | negative net |
| `gap_inert_winkill2` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_winkill3` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_lossstreak` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_cohort2` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_curfew44` | +239.12 | +72.79 | knob does not bind |
| `gap_loss_kill1` | -29.83 | +113.16 | negative net |
| `gap_ma_trail` | -67.38 | -52.02 | negative net |
| `gap_window_entry_cap1` | -33.79 | +17.29 | negative net |
| `gap_inert_geom` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_kill` | +239.12 | +72.79 | knob does not bind |
| `gap_inert_chop65` | +239.12 | +72.79 | knob does not bind |
| `decayF_c` | -43.62 | -29.30 | negative net |
| `decayF_u` | -21.96 | -23.87 | negative net |
| `cap1d` | -49.73 | -41.47 | negative net |
| `cap4d` | -35.21 | +91.99 | negative net |
| `skipwin1_multi_sw10` | -38.54 | +17.06 | negative net |
| `skipwin2_multi_sw10` | -65.33 | +58.90 | negative net |
| `skipwin1_single_sw10` | -38.88 | +17.15 | negative net |
| `trail10_swingpause_single` | -311.27 | -112.82 | negative net |
| `trail06_swingpause_single` | -276.56 | -108.77 | negative net |
| `trail10_multi` | -247.51 | -118.33 | negative net |

---

## Things worth knowing that the table does not say

- **Direction match is the strongest family here** and none of it ships.
  `dirmatch_multi_sw10` is +172.06R out of sample against the champion's
  +72.79R, at a third of the drawdown.
- **Age 10 and age 25 disagree about which era they are for.** `age10_dirmatch`
  is the 4th best book in sample and mid-table out of sample; `age25_dirmatch`
  is lower in sample and 2nd best out of sample. Taking age 10 because it wins
  IS is exactly the mistake `cap24d` and `skip_decisive` both make.
- **`sl_buf_atr = 0.25` is better out of sample** (+82.53R at dd 31.78 against the
  shipped 0.01 at +72.79R / dd 50.55) and worse in sample. A value the project
  has treated as settled since the start.
- **`chop_thresh` does not bind on any book here.** Every book is mode=atr_high,
  which picks the HTF interval set by ATR; chop_thresh is read only in mode=chop.
  The sweep that 'confirmed' the 55-61 band was reading a knob that never fired.
- **The decay signal is directional.** Its best rule (E, crossed) wins on both
  books out of sample; every ALLOW rule is badly negative and F is E's exact
  mirror. It says which side not to take.

## Verifying

```
cd backtest/tests
python exp_pinverify.py          # re-derive every pin from the engine
python exp_pinverify.py <key>   # or just one
```

A pin written by the same pass that measured it proves nothing. `exp_pinverify`
re-runs the engine; it is the only check that has caught a wrong number here.

See backtest/docs/EXPERIMENT_INVENTORY.md for what is not covered and why.
