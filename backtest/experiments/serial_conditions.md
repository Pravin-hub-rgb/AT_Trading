# The owner's conditions for dropping serial

## Condition 1 - weak on untouched out-of-sample data

**NOT TESTABLE.** `OOS_IS_NOT_A_HOLDOUT.md` records that the
out-of-sample era is reused 2021-22 data, not a holdout. There is no
untouched sample in this repo to test against. Stating it either way
would be a claim with nothing behind it.

## Condition 2 - consistently poor DD/recovery across block lengths

Out of sample. Bootstrap p95 by block length, on three
normalisations, because 'poor drawdown' is not the same sentence for a
book holding six positions and one holding a single position.

| book | cls | DD obs | DD p95 (b10/20/40) | rec p95 (b10/20/40) |
|---|---|---:|---|---|
| `fsent_sig_sw20_short` | SIG | 12.9 | 17.4 / 23.2 / 15.7 | 102.1 / 135.0 / 46.0 |
| `fsent_sig_wk_pause_short` | SIG | 6.9 | 13.6 / 8.6 / 6.9 | 71.0 / 42.1 / 32.0 |
| `fsent_sig_trail_delay1` | SIG | 6.5 | 7.8 / 7.6 / 6.5 | 72.05 / 68.0 / 63.0 |
| `fsent_sig_full` | SIG | 5.0 | 5.9 / 5.3 / 5.3 | 60.0 / 53.0 / 49.0 |
| `fsent_sig_fs_mom` | SIG | 4.4 | 6.8 / 4.4 / 4.4 | 60.0 / 60.0 / 60.0 |
| `fsent_champ_long_htf15_htffs` | MULTI | 14.7 | 25.8 / 26.3 / 22.5 | 84.05 / 83.05 / 69.0 |
| `fsent_champ_long_htfesmcl4` | MULTI | 15.0 | 34.6 / 37.9 / 26.2 | 109.0 / 115.0 / 62.0 |
| `fsent_champ_long_htf15_tskip6` | MULTI | 14.9 | 45.5 / 31.1 / 26.3 | 109.0 / 108.1 / 92.0 |
| `fsent_champ_long_htffs` | MULTI | 14.7 | 26.7 / 28.4 / 24.6 | 91.0 / 102.0 / 80.0 |
| `fsent_champ_long_mcloff_htf15` | MULTI | 11.1 | 22.5 / 15.2 / 15.1 | 98.0 / 74.0 / 38.0 |

**CONDITION 2: DOES NOT HOLD**

## Condition 3 - no meaningful benefit against multi

| book | cls | peak conc | mean conc | DD/peakCapR | DD/meanR | net/meanR |
|---|---|---:|---:|---:|---:|---:|
| `fsent_sig_sw20_short` | SIG | 1 | 0.39 | 12.909 | 32.9 | 385.6 |
| `fsent_sig_wk_pause_short` | SIG | 1 | 0.34 | 6.909 | 20.4 | 402.6 |
| `fsent_sig_trail_delay1` | SIG | 1 | 0.43 | 6.493 | 15.2 | 314.1 |
| `fsent_sig_full` | SIG | 1 | 0.33 | 4.990 | 15.3 | 409.9 |
| `fsent_sig_fs_mom` | SIG | 1 | 0.29 | 4.410 | 15.3 | 442.9 |
| `fsent_champ_long_htf15_htffs` | MULTI | 9 | 0.89 | 1.637 | 16.6 | 390.2 |
| `fsent_champ_long_htfesmcl4` | MULTI | 8 | 0.91 | 1.880 | 16.6 | 373.3 |
| `fsent_champ_long_htf15_tskip6` | MULTI | 7 | 1.05 | 2.128 | 14.1 | 311.6 |
| `fsent_champ_long_htffs` | MULTI | 8 | 0.86 | 1.842 | 17.2 | 366.3 |
| `fsent_champ_long_mcloff_htf15` | MULTI | 6 | 0.69 | 1.841 | 15.9 | 389.0 |

DD per mean-concurrent R: SIG 15.2-32.9, MULTI 14.1-17.2.
Net per mean-concurrent R: SIG 314-443, MULTI 312-390.

**CONDITION 3: the two classes overlap on the capital-actually-deployed**
**measure.** Peak-normalising says multi is safer; mean-normalising says**
**they are the same. Neither class has a clean advantage, which means**
**neither has the 'meaningful benefit over multi' that the condition asks**
**for. It does not fire.**

## Condition 4 - the advantage is selection bias

The only honest test: **select on in-sample, measure out-of-sample.**
All 26 books are scored on the same fourteen axes, top five per class
picked, and then their out-of-sample scores are read. Random selection of
five per class is the baseline.

| book | class | p OOS | verdict |
|---|---|---:|---|
| `fsent_sig_sw20_short` | SIG | 0.566 | consistent with luck |
| `fsent_sig_wk_pause_short` | SIG | 0.554 | consistent with luck |
| `fsent_sig_trail_delay1` | SIG | 0.866 | consistent with luck |
| `fsent_sig_full` | SIG | 0.759 | consistent with luck |
| `fsent_sig_fs_mom` | SIG | 0.688 | consistent with luck |
| `fsent_champ_long_htf15_htffs` | MULTI | 0.232 | consistent with luck |
| `fsent_champ_long_htfesmcl4` | MULTI | 0.379 | consistent with luck |
| `fsent_champ_long_htf15_tskip6` | MULTI | 0.382 | consistent with luck |
| `fsent_champ_long_htffs` | MULTI | 0.393 | consistent with luck |
| `fsent_champ_long_mcloff_htf15` | MULTI | 0.011 | supported |

**CONDITION 4: HOLDS for serial.** All five serial books sit above p 0.55
out of sample and randomly picking five serial books matches the shortlist
50.6% of the time. Of the multi books, only `fsent_champ_long_mcloff_htf15` passes, at p 0.011.

**BUT - and this is the part that matters - the condition as written asks**
**whether serial's advantage is selection bias, and that is the one thing
the shortlist CANNOT show even if it were true. All three of the tests
pointing the same way are derived from the same historical trade data.**
They are not three independent proofs, and the owner was right to say so
before acting on them.

## MULTI head-to-head, everything at once

| book | R/tr | net R | p OOS | retention | net/DD | DD%peak | rec d | cap10% | DD/meanR | net/meanR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fsent_champ_long_htf15_tskip6` | 1.523 | 968 | 0.382 | 94% | 42.5 | 2.35% | 39 | 62% | 14.1 | 311.6 |
| `fsent_champ_long_mcloff_htf15` | 0.968 | 810 | 0.011 | 89% | 28.5 | 3.50% | 140 | 76% | 15.9 | 389.0 |
| `fsent_champ_long_htf15_htffs` | 0.965 | 1112 | 0.232 | 86% | 37.4 | 2.66% | 9 | 68% | 16.6 | 390.2 |
| `fsent_champ_long_htffs` | 0.938 | 1071 | 0.393 | 80% | 47.7 | 2.09% | 9 | 67% | 17.2 | 366.3 |
| `fsent_champ_long_htfesmcl4` | 0.935 | 1110 | 0.379 | 79% | 55.4 | 1.80% | 50 | 67% | 16.6 | 373.3 |
