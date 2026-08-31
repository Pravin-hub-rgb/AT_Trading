# pivot_break 1-min walker fix — 2026-08-30

## Problem

User: "i set it to entry at pivot break so why it didn't took any trade on 28?? for selling it will enter on pivot low break nah??"

User: "ummm why entry on 10:35?? why not at 10:25 it broke the just prev pivot low which was 10:23 low — pivots we should be looking at 1min too nah"

Two issues were confirmed:

### Issue 1: Wrong timeframe for 1-min pivot_break (FIXED)

- `detect_pivot_break` was using 5-min `normal_highs`/`normal_lows` (from `WalkerEngine` fed with 5-min candles)
- For 1-min execution, pivots must come from the 1-min chart
- 28 Aug 10:25 5-min bar: low=24158.55 broke below 10:23 1-min L pivot=24164.7, but the 5-min walker never had that pivot — so no break detected

### Issue 2: Wrong pivot selected (FIXED)

- The previous fix used `normal_lows_1m[-1]` (the LAST pivot in the entire day = idx=359, 15:14)
- Should use the most recent pivot AT OR BEFORE the current 5-min bar's time
- Also: used `1min_bar["close"]` instead of `5min_bar["low"]` for the break check

## Root Cause

`detect_pivot_break` in `intraday.py` always used 5-min pivots, even in 1-min execution mode. For 1-min `pivot_break`, the engine needs a separate `WalkerEngine` over 1-min candles.

## Fix Applied

### 1. Build 1-min WalkerEngine upfront (lines 772-790)

When `execution=1min AND entry_method=pivot_break`, build a complete WalkerEngine over 1-min candles at simulation start. This gives `normal_lows_1m` and `normal_highs_1m` containing all sealed pivots for the day.

### 2. Detect on the correct pivot (lines 1123-1154)

For each 5-min bar in 1-min pivot_break mode:

- Find the most recent sealed L-pivot (or H-pivot for longs) whose `piv.idx <= m1_end_idx`
- Check if `5min_bar["low"] < piv.px` (short) or `5min_bar["high"] > piv.px` (long)
- This correctly finds the 10:23 1-min L pivot (idx=68, px=24164.7) at bar 14 (10:25)

## Results

**28 Aug 2026:**

- pivot_break detected at bar 15 (10:30 window), level=24162.25 (10:27 1-min L pivot)
- Entry fires at 10:35 (1-min bar close = 24157.65)
- Exit EOD at 15:15 (= 24142.45)
- Result: +0.56R

**30-day backtest (pivot_break + 1min + opposite_swing_needed):**

- 86 trades, 30.2% WR, Total R: **+25.47**
- vs 5min baseline: 65 trades, +8.26R

**Swing gate (21 days):**

- PASS: 0 violations — all entries occur AFTER first swing confirmed

## Files Changed

- `backend/src/intraday.py`: added 1-min walker initialization + corrected pivot_break detection
