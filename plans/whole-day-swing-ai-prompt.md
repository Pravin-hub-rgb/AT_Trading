# Whole-Day Swing Loop — AI Prompt

## Context

This is an AT_Trading project (Next frontend + FastAPI backend). The codebase already has **working first-swing and second-swing detection** on the 1min chart. The user wants to **extend this same detection to show all swings throughout the entire trading day** (9:15 AM to last bar) as a zigzag with alternating cyan/yellow colors.

## Existing Working System

### Backend

- **File**: `backend/src/swing_engine.py`
- **`FsV2Engine`** class (line ~82): State machine for first-swing detection. Key methods:
  - `process_bar(c: FlowCandle, g_idx: int)`: feed one bar
  - `get_result(day: str) -> Optional[FsV2Result]`: returns declared swing or None
  - `reset(seed_px: float, seed_idx: int, seed_time: str)`: reinitialize engine with a starting price level
- **`FsV2Result`** (line 61): Result with `day`, `outcome`, `seg: FlowSegment`, `source` ("chop"/"sustain"), `dir` ("up"/"down"), `breaks: list[FsBreakMark]`
- **`FlowSegment`** (line 51): `dir` ("B"/"S"), `start_idx`, `start_px`, `end_idx`, `end_px`
- **`FsBreakMark`** (line 41): `idx`, `time`, `kind: Literal["B1", "B2", "FLIP"]`, `dir`, `px`
- **Server endpoint**: `backend/server.py` line 427 — `/api/swings/whole_day` calls `compute_whole_day_swings()`

### Frontend

- **File**: `frontend/src/components/StockChart.tsx`
- Existing marker pipeline uses `createSeriesMarkers` with these shapes (lines 747-821):
  - `fsBreaks` (lines 748-765): `shape: "arrowUp"`, `position: "belowBar"`, color orange/blue/grey + text "FLIP"/"B2"/"B1"
  - `fsMarkers` (lines 767-782): `shape: "arrowDown"`, `position: "aboveBar"`, color purple/cyan + text "SUS"/"FS"
  - Same pattern for second-swing: `algoSecondSwingBreaks` (orange/yellow palette), `algoSecondSwingMarkers` (orange/yellow palette)

## What Already Exists

### Backend

- **`compute_whole_day_swings()`** function already exists (line 606). It:
  - Groups candles by day
  - For each day, creates a fresh `FsV2Engine`, seeds it, feeds bars until a swing is declared
  - Creates a NEW engine, seeds with previous swing's end-candle close, feeds remaining bars
  - Repeats until no more swings found
  - Returns list of swings with `day`, `swing_index` (0,1,2,...), `seg`, `source`, `dir`
  - Has a bug: `seed_idx = g_idx` (confirmation bar) instead of the swing's end bar, so `swing_N.start_idx != swing_(N-1).end_idx`

### Frontend

- **`WholeDaySwingPrimitive.ts`** (NEW file at `frontend/src/components/WholeDaySwingPrimitive.ts`): Draws zigzag lines between swings. Already exists. Interface:
  ```typescript
  export interface WholeDaySwingPoint {
    dir: "B" | "S";
    start_idx: number;
    start_px: number;
    end_idx: number;
    end_px: number;
    swing_index: number;
    kind: string; // "SUS" or "FS"
    break_kind: "B1" | "B2" | "FLIP" | null;
  }
  ```
- **`api.ts`** (line 192): `WholeDaySwing` interface already has `kind` and `break_kind` fields
- **`page.tsx`** (line 279): `wholeDaySwings` state already populated with `kind` and `break_kind`
- **`StockChart.tsx`** (line 844): New useEffect that creates `createSeriesMarkers` for whole-day swings (swing_index >= 2 only), using identical shape/color/text as fsBreaks/fsMarkers

## The Problem

The current `compute_whole_day_swings()` has a bug that causes **overlapping zigzag segments**. Specifically:

- `seed_idx = g_idx` uses the **confirmation bar index** (after sustain window closed the swing), not the **extreme bar index** (where the swing actually ended)
- This means `swing_N.start_idx != swing_(N-1).end_idx`
- Result: the zigzag has gaps or overlaps at turning points

Example the user reported:

- Swing 0: 9:15-area low → 10:07 high (cyan)
- Swing 1: Should be 10:07 high → 10:24 low (yellow, correct endpoint)
- But due to the bug: the engine produces a segment from 10:07 high → 10:20 low (wrong) AND another from 10:07 → 10:24

## What Needs to Be Fixed

### 1. Fix the backend engine seeding (CRITICAL)

In `backend/src/swing_engine.py`, function `compute_whole_day_swings()`, around lines 684-689:

**Current broken code:**

```python
seed_idx = g_idx  # ← WRONG: uses confirmation bar
seed_t = c.date[11:16]
seed_px = c.close  # ← WRONG: uses confirmation bar's close
last_seg_end_idx = g_idx
```

**What it should be:**
The next swing should start from the PREVIOUS swing's end extreme bar (not the confirmation bar). The `result.seg.end_idx` is the extreme bar where the swing ended. Use that to seed the next engine.

**Important note**: The `reset()` method at line 492 sets BOTH `e_hi` and `e_lo` to the same `seed_px` value. This means the next engine will have `e_hi.px == e_lo.px == seed_px`. When `process_bar` runs, the FIRST bar processed will likely trigger `_initiate()` because the bar's high/low breaks both extremes (since they start equal). This creates the correct counter-extreme start for the next swing.

### 2. Verify the zigzag is continuous

After fixing the seed, each swing's `start_idx` should equal the previous swing's `end_idx`. Verify this by printing the first few swings and confirming continuity.

### 3. Post-processing safety net (optional but recommended)

Even after fixing the seed, add a post-processing step as a safety net — if `swing_N.start_idx != swing_(N-1).end_idx` for any pair, forcibly set `swing_N.start_idx = swing_(N-1).end_idx` and `swing_N.start_px = swing_(N-1).end_px`.

### 4. Day boundary handling

The loop iterates per-day in `by_day.items()`. Make sure swings do NOT carry over between days — each day's first swing starts fresh. The current code does this correctly because it processes each day separately.

## Files to Modify

1. **`backend/src/swing_engine.py`** — Fix the seed logic in `compute_whole_day_swings()`
2. **Optional**: Add post-processing stitching as safety net

## How to Test

1. Start the backend server: `cd backend && python -m uvicorn server:app --reload --port 8003`
2. Request: `GET http://127.0.0.1:8003/api/swings/whole_day?interval=1min&sustain_bars=7`
3. Check the response: for each swing, verify `swing[N].seg.start_idx == swing[N-1].seg.end_idx`
4. Print the first 5 swings to verify:
   ```python
   out = compute_whole_day_swings(candles)
   for s in out[:5]:
       print(s['day'], s['swing_index'], s['seg']['dir'],
             'start:', s['seg']['start_idx'], 'end:', s['seg']['end_idx'])
   ```
5. Verify continuity: each swing's start_idx should equal previous swing's end_idx

## Key Insight

The user said "we already have 2 swing working". The first-swing and second-swing detection work correctly. The `FsV2Engine` with `reset()` works correctly — it just needs the right seed values. Use `result.seg.end_idx` and `result.seg.end_px` from the declared swing to seed the next engine.

## DO NOT

- Do NOT modify the existing `FsV2Engine` class behavior — it works correctly
- Do NOT change how swings are declared — the engine's declaration logic is correct
- Do NOT modify `WholeDaySwingPrimitive.ts` — the frontend drawing is already working
- Do NOT change the marker rendering in `StockChart.tsx` — those are already correct
- Do NOT touch `server.py` — the endpoint is already correct
- Do NOT add new files — just fix the existing `compute_whole_day_swings()` function

## Color Convention

- Even `swing_index` (0, 2, 4, ...): cyan `#22d3ee`
- Odd `swing_index` (1, 3, 5, ...): yellow `#facc15`

This is already implemented in `WholeDaySwingPrimitive.ts` — no changes needed.
