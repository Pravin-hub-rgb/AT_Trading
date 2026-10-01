# Pure-v18 Geometry Path-True Report

> **SUPERSEDED CORRECTION HISTORY — DO NOT USE THE OLD NUMBERS BELOW.**
> The first implementation selected the first B1/B2 mark in a swing rather than
> the nearest preceding B1 and exact current-signal-bar B2. The corrected audit
> completed with zero unmatched candidates. Use the canonical corrected report:
> `backtest/docs/PURE_V18_GEOMETRY_REPORT_CORRECTED.md`.
> This file remains only as audit history.

**Date:** 2026-09-25  
**Instrument:** BTCUSDT, Bybit linear perpetual only  
**Periods:** IS 2023–2026; reused validation/OOS 2021–2022  
**Production changes:** none

## Executive conclusion

Two positive descriptive leads from Stages 24–25 were moved to path-true sweeps:

1. Reject candidates whose current-swing B1 is stale.
2. Distinguish B2 fired immediately after B1 from delayed B2.

The stale-B1 sweep produced an active IS band but failed its frozen cross-period promotion rule. The B1→B2 sweep produced a narrower result: the only active “immediate” cohort was B2 fired **exactly two 15m bars after B1**. Rejecting that age-2 B2 improved literal-default v18 in both position styles and both periods. It also improved champion multi in both periods, but was mixed on current fullstack-single and UTC-Saturday multi.

The age-2 rule is an **open architecture-specific research candidate**, not a universal filter and not a production change.

## Controls

| Control | Parameters | Style |
|---|---|---|
| `pure_v18_single` | low-filter Bybit BASE | single |
| `pure_v18_multi` | low-filter Bybit BASE | multi |
| `literal_v18_single` | literal v18 defaults | single |
| `literal_v18_multi` | literal v18 defaults | multi |

Support checks used the current fullstack-single, champion-multi, and UTC-Saturday-multi references.

All runs used the test-only superset in `backtest/tests/test_experiments_craze.py`. Default-off identity passed exactly:

```text
Shipped:     340 trades / +225.3R
Patched-off: 340 trades / +225.3R
IDENTICAL
```

## Fixed geometry probe

Fresh current B1 (`0–1` bars after swing start) was destructive when used as the only allowed state:

| Control | Scope | Baseline net | Fresh-only net | Delta |
|---|---|---:|---:|---:|
| Pure single | IS | +140.9R | +70.2R | -70.7R |
| Pure multi | IS | +236.7R | +85.1R | -151.6R |
| Pure single | OOS | -4.3R | -61.5R | -57.2R |
| Pure multi | OOS | +43.6R | -32.8R | -76.4R |

Large-swing `4+ ATR` had only 19 IS and 7 OOS trades. Near-current-start `≤1 ATR` lost substantial P&L and was period-dependent.

A fixed stale-B1 `96+` probe improved both IS singles but did nothing in OOS and slightly hurt multi:

| Control | IS delta | OOS delta |
|---|---:|---:|
| Pure single | +25.8R | 0.0R |
| Literal single | +16.7R | 0.0R |
| Pure multi | -8.3R | 0.0R |
| Literal multi | -8.0R | 0.0R |

## Stale-B1 age sweep

Frozen thresholds: `8 / 16 / 32 / 48 / 64 / 96 / 128 / 192` bars.

### IS deltas

| Threshold | Pure single | Literal single | Blocked |
|---:|---:|---:|---:|
| 8 | +7.4R | -10.4R | 62 |
| 16 | -2.9R | +3.7R | 35 |
| 32 | +12.6R | +30.1R | 13 |
| 48 | +16.6R | +27.8R | 7 |
| 64 | +30.7R | +17.5R | 4 |
| 96 | +25.8R | +16.7R | 2 |
| 128/192 | 0.0R | 0.0R | 0 |

### OOS deltas

| Threshold | Pure single | Literal single | Blocked |
|---:|---:|---:|---:|
| 8 | -29.8R | -27.7R | 20 |
| 16 | -11.4R | -12.8R | 10 |
| 32 | -0.8R | +0.4R | 3 |
| 48 | -0.8R | -0.7R | 1 |
| 64–192 | 0.0R | 0.0R | 0 |

The 32–64-bar IS band did not reproduce. No stale-B1 threshold passed the frozen requirement of improving both single controls in both periods.

## B1→B2 timing test

Two fixed policies were tested:

1. `block_immediate`: block B2 when B1→B2 age was 0–2 bars.
2. `only_delayed_3_8`: allow B2 only at 3–8 bars.

`only_delayed_3_8` was destructive almost everywhere and was rejected.

### Literal-default `block_immediate`

| Control | Scope | Baseline net | Candidate net | Delta | Blocked |
|---|---|---:|---:|---:|---:|
| Literal single | IS | +94.4R | +99.7R | **+5.2R** | 21 |
| Literal single | OOS | +19.1R | +23.6R | **+4.6R** | 11 |
| Literal multi | IS | +129.3R | +163.6R | **+34.3R** | 21 |
| Literal multi | OOS | +34.3R | +40.0R | **+5.7R** | 11 |

Literal-single IS changed from 353 to 340 trades, net R/trade `+0.268 → +0.293`, gross PF `1.75 → 1.78`, and max net DD `33.4R → 31.9R`.

Literal-multi IS changed from 429 to 416 trades, net R/trade `+0.301 → +0.393`, gross PF `1.84 → 2.10`, and max net DD `32.7R → 30.5R`.

### Exact age decomposition

| B1→B2 age | IS blocked | OOS blocked |
|---:|---:|---:|
| 0 | 0 | 0 |
| 1 | 0 | 0 |
| 2 | 21 | 11 |
| 0–1 | 0 | 0 |
| 0–2 | 21 | 11 |

The exact mechanism is:

> **Reject B2 when B2 fires exactly two 15m bars after B1.**

No age-0 or age-1 candidates existed in these ledgers.

## Current-reference support

| Current reference | IS delta | OOS delta |
|---|---:|---:|
| Fullstack wage10 single | -3.3R | +14.9R |
| Champion multi | +5.9R | +5.6R |
| UTC-Saturday multi | -16.8R | +25.1R |

Champion multi is the strongest current support cell: IS net `+325.8R → +331.7R`, OOS net `+70.2R → +75.8R`, with OOS DD improving `53.2R → 43.9R`; IS DD worsened `27.7R → 34.6R`. Ten-R-plus survivors stayed at 6 in OOS.

Later Bybit tuning changes how age-2 B2 interacts with the trade stream. The rule is positive for literal-default and champion multi, but mixed for fullstack single and UTC-Saturday multi. This is an architecture/parameter interaction, not a universal v18 law.

## Prefix/causality audit

The gate reads only marks with `mark.idx <= current signal bar`; it does not intentionally read a future mark.

A stricter audit recomputed 15m and 1h swing chains on histories truncated at 70% and 85%. Both baseline and candidate failed exact prefix invariance at every tested cutoff. Examples:

- IS literal single at 85%: baseline had 93 full-only and 95 prefix-only completed trades; candidate had 87 full-only and 91 prefix-only.
- OOS literal multi at 85%: baseline had 47 full-only and 65 prefix-only; candidate had 43 full-only and 61 prefix-only.

This is the already-documented full-history swing-chain boundary caveat, not evidence that this gate uniquely introduced lookahead. Because baseline also fails, the prefix audit cannot independently validate the full replay as live-identical.

- Gate-level mark selection: causal by construction.
- Full-history swing-chain prefix invariance: fails for baseline and candidate; shared caveat remains.
- Production adoption: not justified from this audit alone.

## Final status

### Open candidate

```text
Reject B2 when B2 occurs exactly two 15m bars after B1.
```

- Positive in all four literal-default v18 style/period cells.
- Positive in champion multi IS and OOS.
- Mixed in current fullstack single and UTC-Saturday multi.
- Reduces trade count and preserves champion OOS 10R+ runners.

### Rejected sibling

`only_delayed_3_8` was destructive across nearly all cells.

### Rejected sweep family

Stale-B1 thresholds `8–192` were an IS-only active band; no threshold passed the frozen cross-period rule.

No production change. All new kwargs remain test-only and default-off.

## Canonical files

### Harnesses

```text
backtest/tests/exp_geom_pure_v18_sweep.py
backtest/tests/exp_geom_stale_b1_sweep.py
backtest/tests/exp_geom_b1_b2_sweep.py
backtest/tests/exp_geom_b1_b2_support.py
backtest/tests/exp_geom_b1_b2_age_decomp.py
backtest/tests/exp_geom_b1_b2_prefix_audit.py
```

### Results

```text
backtest/tests/_geom_pure_v18_results_is.json
backtest/tests/_geom_pure_v18_results_oos.json
backtest/tests/_geom_stale_b1_sweep_results_is.json
backtest/tests/_geom_stale_b1_sweep_results_oos.json
backtest/tests/_geom_b1_b2_results_is.json
backtest/tests/_geom_b1_b2_results_oos.json
backtest/tests/_geom_b1_b2_support_results_is.json
backtest/tests/_geom_b1_b2_support_results_oos.json
backtest/tests/_geom_b1_b2_age_decomp_is.json
backtest/tests/_geom_b1_b2_age_decomp_oos.json
backtest/tests/_geom_b1_b2_prefix_audit_is.json
backtest/tests/_geom_b1_b2_prefix_audit_oos.json
```

