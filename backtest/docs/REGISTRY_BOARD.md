# Registry books - full measured board

Every book in `experiment_registry.py`, re-measured on `unified.py` through
`run_experiment.py` on 2026-10-02.

`net` is after costs (55bp fee/side, 2x, 5bp slippage, 1bp funding, 1bp cost).
`dd` is max drawdown in R on the net equity curve. `wr` is win rate.

`champion` is a book name, not a claim of highest net R.

Books whose pins also carry `oos_*` were additionally measured on true OOS
(2021-22). Everything else is IS only.

## Top 25 by net R (IS)

| # | book | n | net R | gross R | dd R | wr % | OOS net R |
|---|------|--:|------:|--------:|-----:|----:|----------:|
| 1 | `trail_half_delay1_skipn4` | 424 | +556.62 | +679.02 | 44.47 | 23.1 | +104.98 |
| 2 | `dirmatch_multi_sw10` | 389 | +444.21 | +533.97 | 24.01 | 38.8 | - |
| 3 | `dirmatch_single_sw10` | 392 | +442.72 | +532.64 | 31.02 | 39.5 | - |
| 4 | `age10_dirmatch_multi_sw10` | 150 | +417.68 | +462.24 | 13.45 | 51.3 | - |
| 5 | `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | +457.69 | 12.90 | 53.7 | - |
| 6 | `trail_half_delay1` | 465 | +385.92 | +507.75 | 51.39 | 27.3 | +88.74 |
| 7 | `trail_half` | 468 | +384.99 | +508.78 | 51.10 | 26.9 | +71.73 |
| 8 | `cap32d` | 522 | +375.53 | +499.86 | 48.39 | 30.5 | - |
| 9 | `cap999_nocap` | 592 | +360.87 | +501.26 | 54.25 | 30.1 | - |
| 10 | `utcsat_entry_minus_1` | 454 | +358.92 | +466.44 | 21.18 | 30.8 | - |
| 11 | `trail_skipn4` | 439 | +357.15 | +472.87 | 43.96 | 23.9 | +61.05 |
| 12 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | +416.47 | 21.47 | 43.5 | - |
| 13 | `cap48d` | 556 | +351.27 | +480.85 | 54.25 | 29.9 | - |
| 14 | `lb30_w24_ext2.0` | 380 | +344.61 | +441.61 | 36.58 | 35.8 | - |
| 15 | `utcsat_cap999_nocap` | 537 | +336.98 | +462.55 | 42.82 | 30.0 | - |
| 16 | `lb30_w24_ext1.5` | 337 | +336.67 | +425.66 | 35.92 | 36.8 | - |
| 17 | `champion_multi_sw10` | 500 | +325.78 | +445.22 | 27.72 | 30.0 | - |
| 18 | `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | +445.19 | 27.72 | 30.0 | - |
| 19 | `champion_multi_sw10_entry1` | 500 | +325.75 | +445.19 | 27.72 | 30.0 | - |
| 20 | `age25_multi_sw10` | 293 | +319.22 | +392.64 | 25.86 | 37.2 | - |
| 21 | `fullstack_wage10_cd0_single_sw10` | 234 | +316.64 | +372.69 | 23.96 | 34.6 | - |
| 22 | `utcsat_chopband_multi_sw10` | 392 | +315.45 | +407.37 | 36.41 | 31.6 | - |
| 23 | `lb30_w24_ext2.5` | 405 | +315.08 | +419.56 | 42.82 | 35.3 | - |
| 24 | `lb30_w24_ext3.0` | 415 | +314.51 | +420.18 | 42.27 | 35.4 | - |
| 25 | `wage10_swingpause_wskip_single_sw10` | 330 | +308.65 | +385.19 | 26.27 | 32.4 | - |

## Bottom 12 by net R

| # | book | n | net R | dd R | wr % |
|---|------|--:|------:|-----:|----:|
| 121 | `partial1_multi_sw10` | 553 | +50.19 | 43.84 | 41.4 |
| 122 | `skipwinhalt_single_sw10` | 328 | +29.64 | 60.09 | 27.4 |
| 123 | `skipwinhalt_multi_sw10` | 323 | +28.35 | 45.34 | 26.9 |
| 124 | `cap4d` | 385 | -35.21 | 57.45 | 26.8 |
| 125 | `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 126 | `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 127 | `skipwin1_single_sw10` | 148 | -38.88 | 53.91 | 20.3 |
| 128 | `cap1d` | 236 | -49.73 | 84.28 | 19.5 |
| 129 | `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 | 13.9 |
| 130 | `trail10_multi` | 246 | -247.51 | 248.22 | 17.8 |
| 131 | `trail06_swingpause_single` | 233 | -276.56 | 276.56 | 14.9 |
| 132 | `trail10_swingpause_single` | 328 | -311.27 | 313.38 | 22.5 |

## Books with negative net

| book | n | net R | dd R |
|------|--:|------:|-----:|
| `cap4d` | 385 | -35.21 | 57.45 |
| `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 |
| `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 |
| `skipwin1_single_sw10` | 148 | -38.88 | 53.91 |
| `cap1d` | 236 | -49.73 | 84.28 |
| `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 |
| `trail10_multi` | 246 | -247.51 | 248.22 |
| `trail06_swingpause_single` | 233 | -276.56 | 276.56 |
| `trail10_swingpause_single` | 328 | -311.27 | 313.38 |

## Reproducing

```
cd backtest/tests
python run_experiment.py <book_key>
```

Raw `unified.simulate_htf_ltf_streak_halt()` calls are not interchangeable with
this: the harness injects `exp_partial_r` and patches the `exp_causal_sl`
branch. Always go through the harness.
