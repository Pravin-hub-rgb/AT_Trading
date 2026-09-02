# Claude Analysis Report: Double FLIP on Swing 2 (Aug 17)

## Problem
Swing 2 on Aug 17 produces **3 break marks** (B1 + 2 FLIPs). The user sees two orange `FLIP-2` markers on the chart and is confused — the engine appears to flip direction twice in rapid succession. The user wants to understand what these FLIPs represent and whether they are correct.

## What the user sees on the chart
- `B1-2` at 10:14 — grey arrow (initial lock)
- `FLIP-2` at 10:16 — orange arrow (flip to UP)
- `FLIP-2` at 10:17 — orange arrow (flip back to DOWN)

The final swing direction is **down**, confirmed by chop at 10:28 (`fs_at`).

## Engine trace for Swing 2

### Candle data around the critical bars (Aug 17, local index in day's bars):
```
pos  time   high     low      close
58   10:13  24282.35 24277.55 24280.75   <-- S2 seed (bars_seen=1)
59   10:14  24283.80 24277.40 24281.45   <-- B1 lock (down)
60   10:15  24283.80 24280.05 24281.70   <-- No break
61   10:16  24283.90 24280.15 24281.20   <-- FLIP up
62   10:17  24282.65 24263.80 24266.25   <-- FLIP down (massive drop)
```

### Step-by-step state transitions:

| Bar | Time | Dir | dir_confirmed | Event |
|-----|------|-----|---------------|-------|
| 58 | 10:13 | down | False | B1 lock: locked_level=24277.55 |
| 59 | 10:14 | down | False | B1 recorded (px=24277.55) |
| 60 | 10:15 | down | False | No break (high=24283.8 equals e_hi_prev, not strictly >) |
| 61 | 10:16 | **up** | **True** | FLIP up: high=24283.9 > e_hi_prev=24283.8 → _flip("up") |
| 62 | 10:17 | **down** | True | FLIP down: low=24263.8 < e_lo_prev=24280.15 → _flip("down") |

### Root cause of the double FLIP:

1. **B1 lock at 10:14**: Engine locks DOWN. `dir_confirmed=False`. `locked_level=e_lo_prev.px=24277.55`.

2. **FLIP UP at 10:16**: Candle high=24283.9 > e_hi_prev=24283.8 (by 0.1). Since dir_confirmed=False, the engine takes the pre-confirmation path (line 263): `elif up_break: self._flip("up")`. Records FLIP(up) with locked_level=e_hi_prev.px=24283.8.

3. **FLIP DOWN at 10:17**: Candle crashes, low=24263.8 < e_lo_prev=24280.15. Since dir_confirmed=True now, takes the confirmed path (line 247): `if self.dir == "up" and down_break and not up_break: self._flip("down")`. Records FLIP(down) with locked_level=e_lo_prev.px=24277.4.

4. **Final state**: dir=down, confirmed by chop at 10:28.

## Key question for Claude

1. **Is the double FLIP correct behavior?** Both FLIPs are real market events. The market tried to reverse up at 10:16, then crashed back at 10:17. Or is this noise?

2. **Should the pre-confirmation FLIP be suppressed?** The first FLIP happens while dir_confirmed=False (B1 just locked). Direction changes before confirmation could be noise. The engine allows _flip() in the pre-confirmation path (lines 253-264 of firstswing.py).

3. **Should the chart collapse rapid consecutive FLIPs?** Perhaps the engine correctly tracks history, but the chart should only show the final FLIP.

4. **What is the recommended fix?** Suppress the pre-confirmation flip, or collapse FLIPs in the chart, or leave as-is?

## Code reference

- `_step()` at firstswing.py:235 — main state machine
- `_flip()` at firstswing.py:312 — flip handler, sets dir_confirmed=True, appends to break_marks
- `_lock()` at firstswing.py:280 — initial lock, does NOT set dir_confirmed
- Break detection at firstswing.py:210-213: up_break = c.high > e_hi_prev.px, down_break = c.low < e_lo_prev.px
- Chart rendering at StockChart.tsx:831-847 — renders ALL breaks from s.breaks array

## Files to send to Claude
- backend/src/firstswing.py
- frontend/src/components/StockChart.tsx
