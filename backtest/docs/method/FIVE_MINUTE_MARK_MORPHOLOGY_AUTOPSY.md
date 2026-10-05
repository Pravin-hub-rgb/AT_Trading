# Stage 39 — Bybit 5m Mark-Morphology Autopsy

**Date:** 2026-09-25  
**Instrument:** BTCUSDT, Bybit linear perpetual only  
**Periods:** IS 2023–2026; reused validation/OOS 2021–2022  
**Production changes:** none

## Purpose

This was the requested follow-up to the 5m opposition study. Instead of asking only whether the 5m direction was opposite, it classified the actual completed 5m FirstSwing events that occurred **after the 15m trade entry and before its real exit**.

Events covered:

- `B1`
- `B2`
- `FLIP`
- `FS` confirmation
- chronological pairs such as `B1→FLIP`, `FS→B2`, and `FS→FLIP`
- timing relative to the first `+0.5R` MFE

All timestamps use completed 5m closes. No future 5m candle was used at the 15m entry instant.

## Data and causality checks

The 5m chain used:

```text
min_bars = 14
Bybit 5m data only
```

Coverage:

| Scope | 5m swings/events | B1 | B2 | FLIP | FS |
|---|---:|---:|---:|---:|---:|
| IS | 17,951 | 17,951 | 12,360 | 11,040 | 17,951 |
| OOS | 9,914 | 9,914 | 6,832 | 5,981 | 9,914 |

The study is **descriptive post-entry classification**. It does not claim that a future event was knowable at entry.

## Main result: no post-entry 5m event is the bad cohort

For every reference and both periods, trades with no adverse 5m event after entry were strongly negative and had no large runners.

Representative IS results:

| Reference | Baseline n / net | `none` n / net | `none` avg net | `opposite_B1` n / net | `opposite_FLIP` n / net |
|---|---:|---:|---:|---:|---:|
| Pure single | 352 / +101.1R | 31 / -38.6R | -1.244R | 295 / +173.4R | 264 / +208.5R |
| Pure multi | 419 / +272.5R | 36 / -47.3R | -1.315R | 349 / +334.2R | 320 / +396.4R |
| Literal single | 356 / +196.8R | 26 / -29.2R | -1.122R | 302 / +261.8R | 277 / +282.1R |
| Literal multi | 443 / +279.4R | 34 / -40.0R | -1.178R | 373 / +344.7R | 348 / +378.5R |
| Fullstack single | 200 / +310.7R | 18 / -22.6R | -1.255R | 167 / +323.2R | 149 / +369.5R |
| Champion multi | 500 / +325.8R | 33 / -40.1R | -1.216R | 419 / +398.1R | 381 / +465.0R |
| UTC-Saturday multi | 454 / +358.9R | 31 / -37.8R | -1.219R | 383 / +418.5R | 352 / +476.9R |

Representative OOS results:

| Reference | Baseline n / net | `none` n / net | `none` avg net | `opposite_B1` n / net | `opposite_FLIP` n / net |
|---|---:|---:|---:|---:|---:|
| Pure single | 187 / +8.3R | 14 / -16.6R | -1.187R | 158 / +42.2R | 137 / +65.2R |
| Pure multi | 216 / +44.3R | 18 / -21.2R | -1.181R | 181 / +85.0R | 159 / +105.6R |
| Literal single | 188 / +4.2R | 11 / -13.6R | -1.240R | 163 / +33.7R | 141 / +56.9R |
| Literal multi | 228 / +72.3R | 14 / -17.0R | -1.214R | 199 / +105.9R | 173 / +130.7R |
| Fullstack single | 140 / +16.9R | 16 / -20.3R | -1.269R | 113 / +49.9R | 93 / +66.8R |
| Champion multi | 279 / +70.2R | 24 / -28.6R | -1.191R | 234 / +122.6R | 211 / +141.5R |
| UTC-Saturday multi | 253 / +60.2R | 23 / -27.9R | -1.215R | 209 / +111.9R | 186 / +131.7R |

The `none` cohorts had essentially no 3R/5R/10R runners. Event cohorts inherited the original strategy’s runner tail.

## Strongest sequence patterns

The `B1→FLIP` sequence was the strongest recurring descriptive sequence:

| Reference | IS n / net / avg net | OOS n / net / avg net |
|---|---:|---:|
| Pure single | 101 / +265.7R / +2.630R | 54 / +112.6R / +2.086R |
| Pure multi | 130 / +426.5R / +3.281R | 66 / +151.2R / +2.291R |
| Literal single | 108 / +353.5R / +3.273R | 57 / +99.8R / +1.751R |
| Literal multi | 144 / +469.6R / +3.261R | 73 / +173.6R / +2.378R |
| Fullstack single | 56 / +331.4R / +5.918R | 39 / +106.6R / +2.733R |
| Champion multi | 145 / +502.3R / +3.464R | 89 / +185.3R / +2.082R |
| UTC-Saturday multi | 130 / +511.0R / +3.931R | 79 / +169.8R / +2.150R |

`FS→B2` was also strong, but these are overlapping descriptive cohorts. They are not independent samples and must not be added together.

## Interpretation

The correct interpretation is:

> **A trade that remains open long enough to produce post-entry 5m structure has more opportunity to become a runner. A trade that never produces such structure is usually a short-duration stopout.**

Therefore:

- `none` is a useful failure description;
- it is not a prospective entry rejection signal;
- `opposite_B1/B2/FLIP/FS` is not proof that the strategy should enter against its 15m direction;
- the sequence patterns are post-entry outcome conditioning, not live entry information.

The earlier idea “cut when 5m opposition appears” is therefore rejected for now. The data does not support treating post-entry opposition as a harmful event; the cohort with more post-entry structure is the cohort that performs better.

## Canonical files

- Harness: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\exp_thesis_5m_mark_morphology.py`
- IS result: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_5m_mark_morphology_results_is.json`
- OOS result: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_5m_mark_morphology_results_oos.json`
- Checklist: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/method/CHECKLIST.md`
- Experiment log: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/method/EXPERIMENT_LOG.md`

## Verdict

**Complete, descriptive, and no production change.** The study found a strong post-entry duration/structure association, but it did not produce a valid causal entry or exit policy.
