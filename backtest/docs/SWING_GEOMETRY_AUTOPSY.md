# Deep Swing Geometry Autopsy — Bybit BTCUSDT Perp

## Scope

This is a read-only cross-swing autopsy. It explicitly joins:

- previous swing FS and final B1/B2/FLIP mark;
- current swing start;
- current swing B1;
- current B2/FLIP signal;
- entry timestamp.

References: single king, champion multi, UTC-Saturday multi. Periods: IS 2023–2026 and reused OOS 2021–2022.

## Artifacts

- Harness: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\exp_thesis_swing_geometry_deep.py`
- IS JSON: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_swing_geometry_deep_results_is.json`
- OOS JSON: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/tests\_thesis_swing_geometry_deep_results_oos.json`
- Checklist: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/CHECKLIST.md`
- Full log: `C:\Users\Pravin\Desktop\main\AT_Trading\backtest/docs/EXPERIMENT_LOG.md`

## Main result: current B1 freshness

The strongest cross-era relationship was not previous-swing FS distance. It was the age of the current swing’s B1 relative to the current swing start.

### Current B1 age 0–1 bars

| Reference | IS net | OOS net |
|---|---:|---:|
| Single king | +275.2R / 30 trades | +29.2R / 19 trades |
| Champion multi | +336.3R / 70 trades | +39.9R / 21 trades |
| UTC-Saturday multi | +319.7R / 60 trades | +45.4R / 24 trades |

The cohort was positive in all six reference/period combinations.

### Current B1 age 96+ bars

| Reference | IS net | OOS net |
|---|---:|---:|
| Single king | -16.2R / 133 trades | -65.9R / 91 trades |
| Champion multi | -98.5R / 319 trades | -66.0R / 176 trades |
| UTC-Saturday multi | -60.9R / 285 trades | -57.0R / 158 trades |

The cohort was negative in all six combinations.

This is a lead for a future causal study, not an adopted filter. B1 age may be affected by retrospective swing-chain construction, and this study did not prove that the age is live-actionable.

## Other relationships

### B1 → signal timing

`0–1` and `2–7` bar B1-to-signal cohorts were generally positive in IS. Their OOS behavior was weaker and configuration-dependent. No single timing threshold repeated cleanly.

### Previous final mark → current signal

The `8–23` bar cohort was positive in IS for the multi references, but OOS was mixed. Previous-swing FS distance did not provide a stable discriminator.

### Current mark sequence

`B1→FLIP` was strong in IS but weak or negative in OOS. It is regime-dependent, not a robust gate.

### Direction agreement

Signals aligned with the current swing direction were strongly positive; opposite-to-current-swing signals were strongly negative. This is already encoded in the engine’s direction logic and is not a novel improvement.

## Verdict

Stage 25 found a useful descriptive lead—fresh current B1 structure versus stale current B1 structure—but no new strategy rule was adopted. No production change was made.

The next safe follow-up, if pursued, is a separate live-feasibility audit of B1 age—not a threshold sweep.

## W/L × distance matrix (Stage F, 2026-09-25)

Descriptive re-cut: winner/loser × distance-bucket cells (n, win%, gross R,
R-per-n, 3R+ count) for `prev_fs→signal`, `prev_final→signal`, `B1→signal`,
`cur_start→B1` (bars + ATR), configs fullstack_wage10_cd0_single_sw10 /
champion_multi_sw10 / utcsat_multi_sw10, IS + OOS.
Harness `exp_wl_distance_matrix.py`; JSON `_wl_distance_matrix_results.json`.

Era-consistent cells (both IS and OOS positive in all three configs):

- `cur_start_to_b1_bars = 0-1`: R/n fullstack +9.60/+1.69, champion +5.17/+2.06,
  utcsat +5.74/+2.04 (IS/OOS). Corresponding `96+` bucket flat-to-negative
  (champion -0.07/-0.24, utcsat +0.01/-0.23, fullstack +0.11/-0.56).
  NOTE: descriptive only — does NOT reopen the stale-B1 family, which was
  closed path-true at 24.33 (8-192 stale band IS-only, fresh-B1-only
  destructive).
- `b1_to_signal_bars = 0-1`: positive both eras but n = 14-21 only.

Era flips (do NOT use as filters):

- `prev_fs_to_signal_bars = 0-1`: IS strong (champion +2.78, fullstack +4.33,
  utcsat +2.89 R/n) but OOS negative in all three (-0.40 / -0.22 / -0.20).
- `prev_final_to_signal_atr = 1-2`: IS positive, OOS negative in all three.

Config-dependent:

- `prev_final_to_signal_bars = 48-95`: champion +1.40/+0.32 but fullstack
  +2.62/-0.08 (OOS flips).

No gate, no production change.

