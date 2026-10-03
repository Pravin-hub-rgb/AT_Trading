# Registry books - full measured board

Every book in `experiment_registry.py`, re-measured on `unified.py` in one
pass on 2026-10-02 through `run_experiment.py`.

`net` is after costs (55bp fee/side, 2x, 5bp slippage, 1bp funding, 1bp
cost). `dd` is max drawdown in R on the net equity curve. `wr` is win rate.

`champion` is a book name, not a claim of highest net R.

## Top 20 by net R

| # | book | n | net R | gross R | dd R | wr % |
|---|------|--:|------:|--------:|-----:|----:|
| 1 | `dirmatch_multi_sw10` | 389 | +444.21 | +533.97 | 24.01 | 38.8 |
| 2 | `dirmatch_single_sw10` | 392 | +442.72 | +532.64 | 31.02 | 39.5 |
| 3 | `age10_dirmatch_multi_sw10` | 150 | +417.68 | +462.24 | 13.45 | 51.3 |
| 4 | `age10_dirmatch_swingpause_single_sw10` | 149 | +414.08 | +457.69 | 12.90 | 53.7 |
| 5 | `utcsat_entry_minus_1` | 454 | +358.92 | +466.44 | 21.18 | 30.8 |
| 6 | `age25_dirmatch_multi_sw10` | 248 | +357.01 | +416.47 | 21.47 | 43.5 |
| 7 | `lb30_w24_ext2.0` | 380 | +344.61 | +441.61 | 36.58 | 35.8 |
| 8 | `lb30_w24_ext1.5` | 337 | +336.67 | +425.66 | 35.92 | 36.8 |
| 9 | `champion_multi_sw10` | 500 | +325.78 | +445.22 | 27.72 | 30.0 |
| 10 | `champion_multi_sw10_leg_no_entry` | 500 | +325.75 | +445.19 | 27.72 | 30.0 |
| 11 | `champion_multi_sw10_entry1` | 500 | +325.75 | +445.19 | 27.72 | 30.0 |
| 12 | `age25_multi_sw10` | 293 | +319.22 | +392.64 | 25.86 | 37.2 |
| 13 | `fullstack_wage10_cd0_single_sw10` | 234 | +316.64 | +372.69 | 23.96 | 34.6 |
| 14 | `utcsat_chopband_multi_sw10` | 392 | +315.45 | +407.37 | 36.41 | 31.6 |
| 15 | `lb30_w24_ext2.5` | 405 | +315.08 | +419.56 | 42.82 | 35.3 |
| 16 | `lb30_w24_ext3.0` | 415 | +314.51 | +420.18 | 42.27 | 35.4 |
| 17 | `wage10_swingpause_wskip_single_sw10` | 330 | +308.65 | +385.19 | 26.27 | 32.4 |
| 18 | `curfew624_utcsat_multi_sw10` | 377 | +304.72 | +393.15 | 31.95 | 32.4 |
| 19 | `ext2_utcsat_multi_sw10` | 417 | +301.86 | +402.41 | 41.77 | 32.6 |
| 20 | `nowknd_multi_sw10` | 403 | +301.39 | +389.89 | 25.88 | 31.8 |

## Bottom 12 by net R

| # | book | n | net R | dd R | wr % |
|---|------|--:|------:|-----:|----:|
| 104 | `partial3_multi_sw10` | 513 | +92.55 | 39.75 | 33.5 |
| 105 | `partial2_multi_sw10` | 528 | +72.28 | 39.25 | 37.5 |
| 106 | `partial1_multi_sw10` | 553 | +50.19 | 43.84 | 41.4 |
| 107 | `skipwinhalt_single_sw10` | 328 | +29.64 | 60.09 | 27.4 |
| 108 | `skipwinhalt_multi_sw10` | 323 | +28.35 | 45.34 | 26.9 |
| 109 | `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 110 | `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 | 19.3 |
| 111 | `skipwin1_single_sw10` | 148 | -38.88 | 53.91 | 20.3 |
| 112 | `skipwin2_multi_sw10` | 101 | -65.33 | 66.47 | 13.9 |
| 113 | `trail10_multi` | 246 | -247.51 | 248.22 | 17.8 |
| 114 | `trail06_swingpause_single` | 233 | -276.56 | 276.56 | 14.9 |
| 115 | `trail10_swingpause_single` | 328 | -311.27 | 313.38 | 22.5 |

## Books with negative net

| book | n | net R | dd R |
|------|--:|------:|-----:|
| `skipwin1_multi_sw10` | 145 | -38.54 | 52.54 |
| `skip1pause_multi_sw10` | 145 | -38.54 | 52.54 |
| `skipwin1_single_sw10` | 148 | -38.88 | 53.91 |
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
