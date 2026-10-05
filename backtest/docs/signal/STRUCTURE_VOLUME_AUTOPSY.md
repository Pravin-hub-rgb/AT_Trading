# Structure + Volume Autopsy — Bybit BTCUSDT Perp

## Scope

- Instrument: BTCUSDT Bybit perpetual
- References: `fullstack_wage10_cd0_single_sw10`, `champion_multi_sw10`, `utcsat_multi_sw10`
- Periods: IS 2023–2026 and reused OOS 2021–2022
- Production changes: none
- Real CSV volume was used; it was not hardcoded to zero

## Harness and artifacts

- Harness: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\exp_thesis_structure_volume.py`
- IS result: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_structure_volume_results_is.json`
- OOS result: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_structure_volume_results_oos.json`
- Checklist: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/method/CHECKLIST.md`
- Full log: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/method/EXPERIMENT_LOG.md`

## Baselines

| Reference | IS trades | IS gross | IS net | OOS trades | OOS gross | OOS net |
|---|---:|---:|---:|---:|---:|---:|
| Single king | 200 | +360.6R | +310.7R | 140 | +38.0R | +16.9R |
| Champion multi | 500 | +445.2R | +325.8R | 279 | +105.7R | +70.2R |
| UTC-Saturday multi | 454 | +466.5R | +358.9R | 253 | +92.6R | +60.2R |

Identity gate passed exactly before descriptive rows were produced.

## Findings

### B1 → B2 timing

- `0–2` bars: weak or negative in all tested reference/period combinations.
- `3–8` bars: positive in IS and the two multi OOS ledgers, but the single OOS cell contained only 9 trades.
- `9–24` bars: small and inconsistent.

This is descriptive, not a filter. The sample is too small and the B1/B2 cohort is not a complete prospective decision rule.

### Current swing magnitude

The `4+ ATR` current-swing magnitude cohort was the strongest recurring geometric relationship, but its net result still depended on period and reference. Large current swings appear to carry the runner profile; that does not prove that a magnitude threshold should gate entries.

### Current-start distance

Entries near the current swing start (`0–1 ATR`) were generally the strongest cohort in IS, but the direction/metric was not uniform in every OOS cell. It is a structural description, not a validated gate.

### Volume

Relative-volume buckets were not stable across eras. Some 1h/15m volume states looked strong in one period and weak in another. The prior volume path-true families were already tested, so no additional volume filter was adopted.

### Routing conflicts

Signal-versus-chop conflict was weak in IS but positive OOS for several cohorts. Actual-versus-ATR route conflicts were small and inconsistent. These are not stable rejection rules.

## Verdict

The autopsy found real structural information, especially around current-swing geometry, but no robust new gate. Do not add a volume threshold, route-conflict skip, or B1/B2 timing filter from this study alone.
