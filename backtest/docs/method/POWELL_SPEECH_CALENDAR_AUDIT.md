# Fed/Powell Speech Calendar Audit

**Date:** 2026-09-25  
**Instrument context:** BTCUSDT Bybit perpetual strategy study  
**Purpose:** determine whether Powell speech/testimony dates can be added to the pre-announced event experiment without hindsight.

## Sources

Official annual pages:

- `https://www.federalreserve.gov/newsevents/{2021..2026}-speeches.htm`
- `https://www.federalreserve.gov/newsevents/{2021..2025}-testimony.htm`

The 2026 testimony page currently returns 404 because the annual page has not yet been published.

## Extracted archive rows

62 Powell speech/testimony rows were found:

| Year | Speeches | Testimony |
|---|---:|---:|
| 2021 | 9 | 8 |
| 2022 | 6 | 3 |
| 2023 | 9 | 2 |
| 2024 | 6 | 2 |
| 2025 | 12 | 2 |
| 2026 | 3 | page not yet published |

Each row stores the official event page, source year page, date, title and speaker.

## Eligibility result

The annual pages expose the event date, but not a reliable historical advance-publication timestamp. The event detail pages generally do not expose a machine-readable scheduled time either.

Therefore:

```text
exact time available:             no
advance publication proof:        no
pre-announced exact rows:         0
```

These rows are **not** used in a minute-level or day-level backtest gate. Treating an archive date as if it were known before the speech would be retrospective and could inflate results.

## What is already covered

Stage 22 already includes:

- official BLS release timestamps;
- official FOMC monetary-policy statement timestamps;
- no surprise event labels;
- no bullish/bearish outcome labels.

FOMC press-conference pages were checked, but no separate exact press-conference release timestamp was exposed consistently. A guessed `2:30 p.m.` was not added.

## Verdict

Powell speech risk is real conceptually, but this archive does not provide enough advance-timing evidence for an honest historical event filter. The correct result is therefore:

```text
No Powell speech policy run.
No guessed times.
No retrospective day exclusions.
```

The archive audit is retained for future use if a source with advance-publication timestamps or an official pre-event calendar is found.

## Artifacts

- Builder: `scripts/build_fed_speech_archive_audit.py`
- Archive audit: `data/scheduled_events/official_fed_speech_archive_audit_2021_2026.json`
- Main scheduled-event study: `method/SCHEDULED_EVENTS_AUTOPSY.md`
- Main event harness: `backtest/tests/exp_thesis_scheduled_events.py`
