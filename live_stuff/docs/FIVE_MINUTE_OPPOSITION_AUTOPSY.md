# Bybit 5m Opposition / Post-MFE Autopsy

## Scope

- Instrument: `BTCUSDT_BYBIT` only.
- Main 15m ledgers: `pure_v18_single`, `pure_v18_multi`, `fullstack_single`, `champion_multi`, `utcsat_multi`.
- 5m data: Bybit `data/bybit/BTCUSDT_5m.csv`, `178,204` completed candles, `2025-01-01` through `2026-09-11`; and downloaded OOS `data/unseen/bybit/BTCUSDT_5m.csv`, `210,241` completed candles, `2021-01-01` through `2023-01-01`.
- OOS integrity: zero duplicates, strictly sorted, zero 5-minute gaps; all `70,079` 15m start timestamps have a corresponding 5m start.
- 5m state uses the repository `WalkerEngine` on completed bars. No future 5m bar is used to classify the state at the 15m entry instant.

## Entry-time opposition

Opposition already present at 15m entry was not a negative signal. It was often stronger than entry-aligned trades in the overlap sample:

| Reference | Entry aligned | Entry opposed |
|---|---:|---:|
| Pure single | 114 trades / +66.4R | 39 / +35.1R |
| Pure multi | 145 / +95.9R | 51 / +101.0R |
| Fullstack single | 59 / +58.3R | 27 / +90.0R |
| Champion multi | 170 / +102.1R | 60 / +105.1R |
| UTC-Saturday multi | 153 / +104.8R | 55 / +109.1R |

The same result holds in true OOS:

| Reference | Entry aligned | Entry opposed |
|---|---:|---:|
| Pure single | 140 trades / -5.9R | 47 / +39.9R |
| Pure multi | 168 / +27.5R | 48 / +46.1R |
| Fullstack single | 111 / +37.3R | 29 / +0.7R |
| Champion multi | 215 / +53.6R | 64 / +52.1R |
| UTC-Saturday multi | 194 / +56.8R | 59 / +35.9R |

Therefore, an “opposition at entry = reject” rule is not supported by this study.

## Opposition after +0.5R MFE

The warning appears after the trade has already worked. The first 5m opposition after +0.5R was associated with:

| Reference | Opposition before +0.5R | Opposition after +0.5R |
|---|---:|---:|
| Pure single | 90 trades / +107.1R | 62 / -4.7R |
| Pure multi | 116 / +190.7R | 79 / +7.2R |
| Fullstack single | 48 / +136.7R | 37 / +12.5R |
| Champion multi | 137 / +214.3R | 93 / -7.0R |
| UTC-Saturday multi | 120 / +209.9R | 88 / +4.0R |

The post-MFE opposition cohort is descriptively weak, but the signal arrives after the trade has already moved. A direct exit is not automatically useful.

### True OOS confirmation

The downloaded 2021-2022 5m file reproduces the same descriptive separation:

| Reference | Opposition before +0.5R | Opposition after +0.5R |
|---|---:|---:|
| Pure single | 99 trades / +100.5R | 88 / -66.5R |
| Pure multi | 120 / +150.3R | 95 / -75.8R |
| Fullstack single | 69 / +98.0R | 69 / -57.9R |
| Champion multi | 154 / +192.5R | 120 / -81.8R |
| UTC-Saturday multi | 139 / +177.5R | 111 / -81.9R |

Thus the post-MFE warning itself is cross-era. The following counterfactual tests whether it is actionable.

## Post-MFE counterfactual

At the first completed 5m Walker opposition after cumulative MFE, the study tested frozen `+0.5R`, `+1R`, and `+2R` triggers. The table shows **gross-R deltas on the event cohort**; changing exit duration would require a separate full path-true net rebuild, so no synthetic net claim is made.

### IS full-exit / 50%-de-risk deltas

| Reference | +0.5R full / half | +1R full / half | +2R full / half |
|---|---:|---:|---:|
| Pure single | -83.6 / -41.8R | -78.7 / -39.4R | -86.0 / -43.0R |
| Pure multi | -164.7 / -82.3R | -154.6 / -77.3R | -151.2 / -75.6R |
| Fullstack single | -139.5 / -69.8R | -130.5 / -65.3R | -117.5 / -58.7R |
| Champion multi | -173.5 / -86.7R | -154.1 / -77.1R | -140.2 / -70.1R |
| UTC-Saturday multi | -184.1 / -92.1R | -167.2 / -83.6R | -148.3 / -74.1R |

### OOS full-exit / 50%-de-risk deltas

| Reference | +0.5R full / half | +1R full / half | +2R full / half |
|---|---:|---:|---:|
| Pure single | -36.5 / -18.3R | -23.1 / -11.6R | -36.8 / -18.4R |
| Pure multi | -72.2 / -36.1R | -57.3 / -28.7R | -66.5 / -33.2R |
| Fullstack single | -48.0 / -24.0R | -37.0 / -18.5R | -45.2 / -22.6R |
| Champion multi | -97.3 / -48.7R | -77.2 / -38.6R | -80.6 / -40.3R |
| UTC-Saturday multi | -88.6 / -44.3R | -68.9 / -34.5R | -65.7 / -32.9R |

All `30` threshold × reference × era counterfactual cells lose gross R. Full exit is worse than 50% de-risk, but neither is actionable. Runner survival collapses: for example, champion IS `+0.5R` loses all `8` event-cohort 10R runners under full exit and retains only `2` under 50% de-risk.

## Verdict

- **Reject the 5m opposition-at-entry filter:** entry-opposed trades were not worse.
- **Reject full 5m post-MFE exit:** it removed too much structural payoff.
- **Reject 50% 5m post-MFE de-risk:** still materially harmful.
- Keep the result as a descriptive observation only.
- No 5m production flag was added.

## Files

- Harness: `live_stuff/tests/exp_thesis_5m_opposition.py`
- Post-MFE harness: `live_stuff/tests/exp_thesis_5m_post_mfe_exit.py`
- Opposition JSON: `live_stuff/tests/_thesis_5m_opposition_results_is.json`
- OOS opposition JSON: `live_stuff/tests/_thesis_5m_opposition_results_oos.json`
- Post-MFE JSON: `live_stuff/tests/_thesis_5m_post_mfe_exit_results_is.json`
- OOS post-MFE JSON: `live_stuff/tests/_thesis_5m_post_mfe_exit_results_oos.json`
- Downloaded OOS 5m data: `data/unseen/bybit/BTCUSDT_5m.csv`
- OOS downloader: `scripts/download_bybit_unseen.py` (`--tf 5m`)
- Walker implementation: `backend/src/walker.py`
