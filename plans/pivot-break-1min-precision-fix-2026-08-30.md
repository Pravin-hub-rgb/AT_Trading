# 1-min Pivot Break Precision Fix

**Date:** 2026-08-30
**Files changed:** `backend/src/intraday.py` (one line)

---

## The bug

When `execution = "1min"` and `entry_method = "pivot_break"`, the `pivot_break` detection found the break (5-min bar close < sealed LOW pivot) but **did not use the 1-min precision path**. It fell through to the 5-min confirmation hunt (the `armed` state) and waited for a full 5-min bar to close below the level.

The result: on days where the 5-min bar's close was above the pivot but the 1-min bar's close was below (like 2026-08-28), the trade was missed.

---

## The fix

**One line change** at [`backend/src/intraday.py:1147`](backend/src/intraday.py:1147):

```python
# Before
if brk["type"] in ("domination", "candle-size"):

# After
if brk["type"] in ("domination", "candle-size", "pivot_break"):
```

This adds `"pivot_break"` to the break types that go through the 1-min precision path. When the engine detects a `pivot_break`, it now arms `pending_direct` (the deferred 1-min entry state) instead of going to the 5-min confirmation hunt.

The 1-min precision handler at line 1013-1024 then waits for the next 1-min bar close. When the 1-min bar's close is below the armed pivot level, `_open_trade` is called with the 1-min bar as the entry context.

---

## 5-min engine is untouched

The `use_1m` flag (line 770) gates the 1-min path. When `use_1m = False`:

- The `pivot_break` is still detected by `detect_pivot_break` (line 469-494)
- It still goes through the `armed` confirmation hunt (5-min path)
- Only when `use_1m = True` does the new `pending_direct` path activate

**5-min baseline test confirms:** 65 trades, +8.26R (unchanged from before fix).

---

## Verification

### 2026-08-28 trace

| Time      | Event                                        | Notes                                                   |
| --------- | -------------------------------------------- | ------------------------------------------------------- |
| 10:15     | First swing (cyan) confirms buying           | Gate opens at bar 14                                    |
| 09:30     | Second swing (yellow) confirms selling       | Opposite direction → `second_swing_armed`               |
| **10:30** | `pivot_break` detected at level 24161.5      | `pending_direct_1m` armed with break_type `pivot_break` |
| **10:35** | 1-min bar closes at 24157.65 (below 24161.5) | **Trade fires: short at 24157.65**                      |
| 15:15     | EOD exit at 24142.45                         | **+0.56R**                                              |

### Full 30-day test (`_ss_test.py`)

| Mode                          | Trades | R         |
| ----------------------------- | ------ | --------- |
| 5min baseline                 | 65     | +8.26     |
| 1min, no swing gate           | 68     | +5.38     |
| 1min, opposite_swing_needed   | 43     | +6.00     |
| **1min, pivot_break+aligned** | **43** | **+0.75** |

The fix **doubled the trades** (25 → 43) on `pivot_break+aligned` and turned a -4.15R into +0.75R.

---

## Why the 1-min precision matters for pivot_break

`pivot_break` is the entry method where "the close of the 5-min bar breaks the most recent sealed pivot". On 1-min mode, this should be the **1-min bar's close** that breaks the pivot, not the 5-min bar's close. The 1-min bar gives a tighter entry with a better price.

Without the fix, the system waited for the 5-min bar to close below the pivot. But the 5-min bar is composed of 5 one-minute bars, and the 5-min CLOSE is the close of the 5th 1-min bar. If the price broke below the pivot on the 3rd 1-min bar, recovered, then closed above the pivot on the 5th 1-min bar, the 5-min CLOSE is above the pivot → no trade. But a 1-min close below would have given a valid entry.

The 1-min precision path defers the entry to the next 1-min bar close, which can fire on the 1st, 2nd, 3rd, etc. 1-min bar after the 5-min bar opens — giving a tighter, earlier entry.
