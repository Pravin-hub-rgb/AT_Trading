# Swing Gate Fix — Use First Swing FS for Entry Gate — 2026-08-30

## User Report

Settings on 2026-08-28:

- `sl: avg x 1`
- `exec: precise 1min`
- `entry: pace break`
- `swing: opposite required`

Expected: no trade before the first swing is confirmed. First swing FS (FsV2 cyan line) confirmed at 10:21.

Observed: trades taken at 9:50 and 10:20, both before 10:21. Violates the gate.

## Root Cause

In [`backend/src/intraday.py:873-891`](backend/src/intraday.py:873), the entry-swing gate logic incorrectly used the **second swing's** confirmed index as the entry gate when `swing_mode="opposite_swing_needed"`. The second swing (yellow line) is only a **direction filter** (must be opposite of first swing to allow entries) — the **entry gate should be the first swing's FS** (cyan line), not the second swing.

On 28 Aug:

- Second swing (yellow) confirmed at 5-min idx=3 (09:30)
- First swing (cyan) confirmed at 5-min idx=14 (10:15, mapped to 10:21 on 1-min chart)
- Using fs2 as gate allowed trades from idx=4 onwards (9:35 onwards)
- 9:50 (idx=6) and 10:20 (idx=12) trades fired — both violate the first-swing FS gate

## Fix

In [`backend/src/intraday.py:873`](backend/src/intraday.py:873):

```python
# BEFORE (wrong — second swing as gate):
entry_swing_confirmed_idx = fs2_confirmed_idx

# AFTER (correct — first swing as gate):
entry_swing_confirmed_idx = fs_confirmed_idx  # cyan line FS, not yellow
```

Second swing still controls direction filtering (if fs2 is same direction as fs1, skip day).
First swing controls the entry gate (wait for cyan line FS before any trade).

Also exposed `first_swing_confirmed_idx` and `first_swing_end_time` on the result dict
so the chart can display the cyan line confirmation time.

## Verification

[`backend/debug/_ss_gate_aug28.py`](backend/debug/_ss_gate_aug28.py) — runs user settings on
2026-08-28 + last 21 trading days. Asserts entry_bar > first_swing_confirmed_idx.

### Results

| Mode                       | Before      | After      | Delta                   |
| -------------------------- | ----------- | ---------- | ----------------------- |
| 5min baseline              | 65 / +8.26  | 65 / +8.26 | unchanged               |
| 1min (no gate)             | 68 / +5.38  | 68 / +5.38 | unchanged               |
| 1min opposite_swing_needed | 129 / +2.97 | 43 / +6.00 | -86 trades, **R +3.03** |
| 1min pivot_break+aligned   | 25 / -4.15  | 10 / +2.32 | -15 trades, **R +6.47** |

### 28 Aug detail

- First swing FS: 5-min idx=14, time=10:15
- Pre-fix: 2 trades at bars 6 (09:50) and 12 (10:20) — violations
- Post-fix: 1 trade at bar 19 (10:55) — passes gate
- 0 violations across all 21 days

## Files Changed

| File                                                                 | Change                                                                            |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [`backend/src/intraday.py:873`](backend/src/intraday.py:873)         | Gate uses `fs_confirmed_idx` (first swing) not `fs2_confirmed_idx` (second swing) |
| [`backend/src/intraday.py:539`](backend/src/intraday.py:539)         | Store `first_swing_confirmed_idx` and `first_swing_end_time` on result            |
| [`backend/debug/_ss_gate_aug28.py`](backend/debug/_ss_gate_aug28.py) | Verification script — gate check against first_swing_confirmed_idx                |
