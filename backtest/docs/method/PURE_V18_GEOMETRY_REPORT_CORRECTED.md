# Pure-v18 Geometry Path-True Report — Corrected Final

**Date:** 2026-09-25  
**Instrument:** BTCUSDT, Bybit linear perpetual only  
**Periods:** IS 2023–2026; reused validation/OOS 2021–2022  
**Production changes:** none

## Executive conclusion

The corrected mark-selection audit passed:

- exact current-bar B2 match: `286/286` IS and `135/135` OOS;
- nearest preceding B1 was uniquely resolved for every matched B2;
- no unmatched B2 candidates;
- default-off identity: `340 trades / +225.3R`, exact match to shipped.

The original first-B1/first-B2 implementation is superseded. The corrected results do not support a universal pure-v18 geometry filter.

The only surviving narrow candidate is:

> **Reject B2 when B2 fires exactly two 15m bars after the nearest preceding B1.**

This is architecture-specific:

- positive on literal-default v18 in all four style/period cells;
- positive on champion multi in IS and reused OOS;
- positive on current fullstack single in OOS but negative in IS;
- positive on UTC-Saturday multi in OOS but negative in IS;
- negative on low-filter pure-v18 single/multi in IS, while positive in OOS.

It remains a research candidate, not a production change.

## Pure-v18 controls

| Control | IS trades | IS gross R | IS net R | IS avg net R | IS WR | IS net DD |
|---|---:|---:|---:|---:|---:|---:|
| pure single | 340 | +225.3 | +140.9 | +0.414 | 30.0% | 38.1R |
| pure multi | 410 | +340.7 | +236.7 | +0.577 | 31.5% | 41.6R |
| literal single | 353 | +170.6 | +94.4 | +0.268 | 28.0% | 33.4R |
| literal multi | 429 | +220.9 | +129.3 | +0.301 | 31.5% | 32.7R |

| Control | OOS trades | OOS gross R | OOS net R | OOS avg net R | OOS WR | OOS net DD |
|---|---:|---:|---:|---:|---:|---:|
| pure single | 172 | +19.4 | -4.3 | -0.025 | 25.6% | 22.2R |
| pure multi | 198 | +70.5 | +43.6 | +0.220 | 26.8% | 27.9R |
| literal single | 179 | +42.4 | +19.1 | +0.106 | 25.1% | 24.1R |
| literal multi | 204 | +60.9 | +34.3 | +0.168 | 27.0% | 31.3R |

## Geometry arms

### Fresh B1 `0–1` bars

Destructive on pure and literal controls:

| Control | IS delta | OOS delta |
|---|---:|---:|
| pure single | -70.7R | -57.2R |
| pure multi | -151.6R | -76.4R |
| literal single | -57.3R | -47.6R |
| literal multi | -66.1R | -52.9R |

A fresh B1 is descriptive context, not a valid “only trade fresh” gate.

### Large current swing `4+ ATR`

Positive but underpowered: 19–21 IS trades and only 7 OOS trades. It remains a possible sub-strategy research idea, not a validated v18 filter.

### Stale-B1 sweep

Thresholds were `8/16/32/48/64/96/128/192` bars. The IS improvement did not reproduce in OOS.

| Threshold | Pure single IS | Literal single IS | Pure single OOS | Literal single OOS |
|---:|---:|---:|---:|---:|
| 8 | +7.4R | -10.4R | -29.8R | -27.7R |
| 16 | -2.9R | +3.7R | -11.4R | -12.8R |
| 32 | +12.6R | +30.1R | -0.8R | +0.4R |
| 48 | +16.6R | +27.8R | -0.8R | -0.7R |

## Current-reference support

| Reference | IS delta | OOS delta |
|---|---:|---:|
| fullstack wage10 single | -3.3R | +14.9R |
| champion multi | +5.9R | +5.6R |
| UTC-Saturday multi | -16.8R | +25.1R |

Champion multi is the strongest current support cell:

- IS net: `+325.8R → +331.7R`;
- OOS net: `+70.2R → +75.8R`;
- OOS net DD: `53.2R → 43.9R`;
- 10R+ OOS runners: `6 → 6`.

This is a positive research interaction, not a universal v18 law.

## Prefix/causality audit

The gate itself is causal: it reads marks only at or before the current signal bar. However, the full-history swing-chain prefix audit failed for both baseline and candidate at every tested cutoff.

Examples:

- IS literal single at 85%: baseline full-only/prefix-only `93/95`; candidate `87/91`;
- OOS literal multi at 85%: baseline `47/65`; candidate `43/61`.

This is the existing full-history swing-chain boundary caveat, not proof that the age-2 gate uniquely introduced lookahead. It does mean the full replay is not yet proven prefix/live-identical.

## Final status

### Retained research candidate

```text
Reject B2 exactly two 15m bars after the nearest preceding B1.
```

Evidence:

- positive on all four literal-default style/period cells;
- positive on champion multi IS/OOS;
- mixed on current fullstack and UTC-Saturday configurations;
- no age-0/age-1 candidates in these ledgers;
- `only_delayed_3_8` rejected;
- stale-B1 sweep rejected as non-robust;
- prefix caveat remains.

### Closed/rejected

- fresh B1 `0–1` only;
- stale-B1 thresholds `8–192`;
- `only_delayed_3_8`;
- large-swing `4+ ATR` as a universal filter;
- any production change.

No new test-only keyword is adopted into production.

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

### Corrected results

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

The previous version of `method/PURE_V18_GEOMETRY_REPORT.md` is retained only as superseded audit history; this corrected report is the canonical interpretation.

| 64 | +30.7R | +17.5R | 0.0R | 0.0R |
| 96 | +25.8R | +16.7R | 0.0R | 0.0R |
| 128/192 | 0.0R | 0.0R | 0.0R | 0.0R |

No threshold improved both single controls in both periods. This family is closed as a robust rule.

## Corrected B1→B2 age-2 rule

The B2 signal must be the exact B2 mark on the signal bar and direction. The nearest B1 must be strictly before that B2.

| Control | IS baseline | IS age-2 | IS delta | OOS baseline | OOS age-2 | OOS delta |
|---|---:|---:|---:|---:|---:|---:|
| pure single | +140.9R | +130.7R | -10.2R | -4.3R | -1.7R | +2.6R |
| pure multi | +236.7R | +232.1R | -4.6R | +43.6R | +47.5R | +3.9R |
| literal single | +94.4R | +99.7R | +5.2R | +19.1R | +23.6R | +4.6R |
| literal multi | +129.3R | +163.6R | +34.3R | +34.3R | +40.0R | +5.7R |

Age decomposition:

- age 0: zero candidates;
- age 1: zero candidates;
- age 2: `21` blocked in IS and `11` blocked in OOS;
- `0–1`: zero candidates;
- `0–2` is identical to age-2 in this data.

Therefore the exact rule is:

```text
Reject B2 exactly two 15m bars after B1.
```

The broader `only_delayed_3_8` policy was destructive and is closed.
