# Registry books - full measured board

Every book in `experiment_registry.py`, re-measured on `unified.py` through
`run_experiment.py` on 2026-10-02.

`net` is after costs (55bp fee/side, 2x, 5bp slippage, 1bp funding, 1bp cost).
`dd` is max drawdown in R on the net equity curve. `wr` is win rate.

`champion` is a book name, not a claim of highest net R.

OOS column is true out-of-sample 2021-22, measured only for the trail family.
It is the column that matters: several books with high IS do not survive it.

## Top 25 by IS net R

| # | book | IS n | IS net R | IS dd R | OOS n | OOS net R | OOS dd R |
|---|------|------:|---------:|-------:|------:|----------:|---------:|
| 1 | `trail_half_skipn6_dr3` | 373 | +615.15 | 46.15 | 208 | +118.86 | 45.50 |
| 2 | `trail_half_skipn8_nodelay` | 383 | +588.76 | 45.46 | 211 | +113.28 | 49.56 |
| 3 | `trail_half_skipn8_dr1` | 383 | +588.76 | 45.46 | 216 | +103.96 | 58.88 |
| 4 | `trail_half_skipn3_nodelay` | 449 | +561.98 | 43.30 | 253 | +98.60 | 61.40 |
| 5 | `trail_half_delay1_skipn4` | 424 | +556.62 | 44.47 | 234 | +104.98 | 52.50 |
| 6 | `dirmatch_multi_sw10` | 389 | +444.21 | 24.01 | - | - | - |
| 7 | `dirmatch_single_sw10` | 392 | +442.72 | 31.02 | - | - | - |
| 8 | `age10_dirmatch_multi_sw10` | 150 | +417.68 | 13.45 | - | - | - |
| 9 | `trail_half_dr3_nodelay` | 412 | +416.92 | 44.80 | 232 | +123.60 | 32.16 |
| 10 | `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | 12.90 | - | - | - |
| 11 | `trail_half_delay1` | 465 | +385.92 | 51.39 | 272 | +88.74 | 51.72 |
| 12 | `trail_half` | 468 | +384.99 | 51.10 | 269 | +71.73 | 52.08 |
| 13 | `cap32d` | 522 | +375.53 | 48.39 | - | - | - |
| 14 | `cap999_nocap` | 592 | +360.87 | 54.25 | - | - | - |
| 15 | `utcsat_entry_minus_1` | 454 | +358.92 | 21.18 | - | - | - |
| 16 | `trail_skipn4` | 439 | +357.15 | 43.96 | 243 | +61.05 | 75.60 |
| 17 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | 21.47 | - | - | - |
| 18 | `cap48d` | 556 | +351.27 | 54.25 | - | - | - |
| 19 | `lb30_w24_ext2.0` | 380 | +344.61 | 36.58 | - | - | - |
| 20 | `utcsat_cap999_nocap` | 537 | +336.98 | 42.82 | - | - | - |
| 21 | `lb30_w24_ext1.5` | 337 | +336.67 | 35.92 | - | - | - |
| 22 | `champion_multi_sw10` | 500 | +325.78 | 27.72 | - | - | - |
| 23 | `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | 27.72 | - | - | - |
| 24 | `champion_multi_sw10_entry1` | 500 | +325.75 | 27.72 | - | - | - |
| 25 | `age25_multi_sw10` | 293 | +319.22 | 25.86 | - | - | - |

## Bottom 12 by IS net R

| # | book | n | net R | dd R | wr % |
|---|------|--:|------:|-----:|----:|
| 126 | `partial1_multi_sw10` | 553 | +50.19 | 43.84 | 41.4 |
| 127 | `skipwinhalt_single_sw10` | 328 | +29.64 | 60.09 | 27.4 |
| 128 | `skipwinhalt_multi_sw10` | 323 | +28.35 | 45.34 | 26.9 |
| 129 | `cap4d` | 385 | -35.21 | 57.45 | 26.8 |
| 130 | `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 131 | `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 132 | `skipwin1_single_sw10` | 148 | -38.88 | 53.91 | 20.3 |
| 133 | `cap1d` | 236 | -49.73 | 84.28 | 19.5 |
| 134 | `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 | 13.9 |
| 135 | `trail10_multi` | 246 | -247.51 | 248.22 | 17.8 |
| 136 | `trail06_swingpause_single` | 233 | -276.56 | 276.56 | 14.9 |
| 137 | `trail10_swingpause_single` | 328 | -311.27 | 313.38 | 22.5 |

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
