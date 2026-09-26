# Stage 32 — 5m-confirmed entry and first-loss fresh-swing cohort

**Scope:** BTCUSDT Bybit perpetual only. IS 2023–2026; true OOS 2021–2022 using the downloaded `data/unseen/bybit/BTCUSDT_5m.csv`. No production engine or live-trading change.

## Purpose

This stage tested two user-proposed mechanisms:

1. **5m-confirmed entry:** keep the 15m structural stop/trail, but delay entry until a completed 5m close confirms through the prior three completed 5m bars in the trade direction. The original 15m swing stop must remain alive; maximum wait is 240 minutes.
2. **First-loss fresh-swing wait:** after the first loss while a multi cohort remains open, block additional entries until a newly confirmed 15m swing appears after that loss. A two-loss freeze was included as a control.

## References and controls

Seven references were run:

- `pure_v18_single`
- `pure_v18_multi`
- `literal_v18_single`
- `literal_v18_multi`
- `fullstack_single`
- `champion_multi`
- `utcsat_multi`

The identity gate passed:

```text
shipped:      340 trades / +225.3R
patched-off:  340 trades / +225.3R
IDENTICAL
```

## Results

The 5m confirmation arm is strongly trade-reducing and not universal. The table below shows net-R delta from baseline for `five_m_confirm`:

| Reference | IS delta | OOS delta |
|---|---:|---:|
| Pure single | -18.7R | +12.4R |
| Pure multi | -125.0R | -35.4R |
| Literal single | +4.8R | -11.3R |
| Literal multi | -75.0R | -26.6R |
| Fullstack single | -37.8R | +28.6R |
| Champion multi | -151.2R | -33.5R |
| UTC-Saturday multi | -103.8R | -2.6R |

Example trade-count changes under `five_m_confirm`:

- Champion multi: IS `502 → 351`; OOS `263 → 204`.
- Fullstack single: IS `194 → 178`; OOS `115 → 106`.
- Pure single: IS `339 → 316`; OOS `172 → 167`.

The arm helped the weak OOS fullstack-single baseline and pure-single OOS, but materially harmed the multi references and most IS references. It is therefore a selective sub-strategy effect, not a universal v18 improvement.

The first-loss and two-loss cohort arms produced zero blocked entries. They recorded loss triggers and fresh-swing rearms, but the next eligible add-on signal already occurred after a fresh swing confirmation. Their P&L was identical to baseline in every tested reference/period.

## Verdict

- **5m confirmation:** rejected as a universal gate; keep only as a research observation that a later 5m confirmation changes trade mix substantially.
- **First-loss fresh-swing wait:** no-op in this engine/data; the existing signal chain already provides the fresh structure before the next add-on opportunity.
- **Two-loss freeze:** no-op for the same reason.
- **5m + cohort combination:** no incremental effect because the cohort arm blocks nothing.
- **Production:** unchanged.

## Files

### Harness

```text
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\exp_thesis_5m_confirm_cohort.py
```

### Results

```text
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_5m_confirm_cohort_results_is.json
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_5m_confirm_cohort_results_oos.json
```

### Data and downloader

```text
C:\Users\Pravin\Desktop\main\AT_Trading\data\unseen\bybit\BTCUSDT_5m.csv
C:\Users\Pravin\Desktop\main\AT_Trading\scripts\download_bybit_unseen.py
```

### Documentation

```text
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\docs\CHECKLIST.md
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\docs\EXPERIMENT_LOG.md
```

## Validation

- Both JSON artifacts parse.
- The harness and test-only superset compile.
- IS identity gate passed.
- OOS 5m data covers 2021-01-01 through 2023-01-01 with 210,241 rows.
- Temporary run logs were removed after validation.
- No production engine/live files were edited.
