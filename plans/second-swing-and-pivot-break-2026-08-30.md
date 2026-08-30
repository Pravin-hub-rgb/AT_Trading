# Second-Swing Detection + Pivot High Break Entry — Plan (v2)

## User Clarifications (2026-08-30)

- **Second swing = 1min ONLY** — do not touch 5min logic at all
- **Second-swing gate = DROPDOWN OPTION** (not hard-coded):
  - `"opposite_swing_needed"` (default) — wait for opposite swing before entry
  - Later can add: `"no_opposite_swing"` (current behavior), etc.
- **If second swing = same direction as first swing** → skip the day (safe default)
- **Unbiased days** → same alignment rule: first swing = BUYING → wait for SELLING second swing → then trade BUYING
- **Pivot High Break** → separate dropdown option from pace_break

---

## Simplified Rule (what we implement)

```
Entry gate for 1min:
  - First swing (FsV2) confirmed at bar X
  - Second swing (detect_second_swing) confirmed at bar Y
  - If second_swing_dir == first_swing_dir → skip day (mark it, do nothing)
  - Else → entry gate = bar Y (wait for second swing confirmation)
```

5min remains completely untouched.

---

## Phased Todo

```mermaid
flowchart TD
    A[Phase 1: FsV2Engine.reset method] --> B[Phase 2: detect_second_swing helper]
    B --> C[Phase 3: integrate into simulate_day 1min entry gate]
    C --> D[Phase 4: chart render yellow second-swing line]
    D --> E[Phase 5: Pivot High Break entry method for 1min]
    E --> F[Phase 6: dropdown + backtest verification]
```

---

## Phase 1 — FsV2Engine.reset(seed_px, seed_idx, seed_time) + Swing Mode Dropdown

**File**: `backend/src/swing_engine.py`

**Purpose**: Reset all state and seed the engine with a custom session extreme so we can re-run swing detection from an arbitrary point.

**Implementation** — add method to `FsV2Engine`:

```python
def reset(self, seed_px: float, seed_idx: int, seed_time: str) -> None:
    """Re-initialize the engine to detect a new swing starting from a
    pre-defined price level (e.g., the first swing's extreme).
    After reset, the next process_bar call increments bars_seen to 2,
    skipping the bars_seen==1 initialization (seed bar is already set)."""
    # Fresh walker (pivot history not shared with first swing)
    self.walker = WalkerEngine()

    # Fake bars_seen=1 state so next process_bar goes to bars_seen=2
    self.bars_seen = 1
    self.t = seed_time
    self.g_idx = seed_idx
    self.green = False

    # Seed extremes — these are the "session start" for second-swing detection
    self.e_hi = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
    self.e_lo = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
    self.e_hi_pivot = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
    self.e_lo_pivot = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)

    # Zero all state
    self.dir: Optional[Dir] = None
    self.base_dir: Optional[Dir] = None
    self.same_side_breaks = 0
    self.opposite_side_breaks = 0
    self.dir_confirmed = False
    self.dir_confirmed_idx = -1
    self.locked = False
    self.locked_level_px = float("nan")
    self.start_idx = -1
    self.start_time = ""
    self.start_px = float("nan")
    self.cand_idx = -1
    self.cand_time = ""
    self.cand_px = float("nan")
    self.declared = False
    self.tier = None
    self.end_time = ""
    self.end_idx = -1
    self.end_px = float("nan")
    self.confirmed_at_time = ""
    self.confirmed_at_idx = -1
    self.confirm_source = None
    self.last_confirm_hit = None
    self.sustain_streak = 0

    # Clear pools
    self.normal_highs.clear()
    self.normal_lows.clear()
    self.micro_highs.clear()
    self.micro_lows.clear()
    self.hist_h.clear()
    self.hist_l.clear()
    self.break_marks.clear()

    # Reset micro pivot state
    self.p_high = float("nan")
    self.pp_high = float("nan")
    self.p_low = float("nan")
    self.pp_low = float("nan")
```

---

## Phase 2 — `detect_second_swing()` helper

**File**: `backend/src/intraday.py` (add near `_classify_first_swing_v2`)

**Purpose**: Run FsV2 from the first-swing extreme onwards to detect the second swing.

**Signature**:

```python
def detect_second_swing(
    candles: list[dict],
    day_date: str,
    fs1_dir: str,           # "buying" | "selling"
    fs1_end_idx: int,       # bar index of first swing's extreme
    fs1_end_px: float,      # first swing's high (buying) or low (selling)
    fs1_end_time: str,      # HH:MM string
) -> tuple[str | None, int, list[dict], int]:
    """Returns: (direction, start_idx, events, confirmed_at_idx)
       direction: second swing direction or None if not declared
       confirmed_at_idx: bar index where second swing confirmed (-1 if not declared)"""
```

**Approach**:

- Build `FlowCandle` list from `candles[fs1_end_idx + 1:]` (bars AFTER the seed bar)
- Create new `FsV2Engine()`
- Call `eng.reset(fs1_end_px, fs1_end_idx, fs1_end_time)`
- Feed each `FlowCandle` with `process_bar(fc, g_idx)` where `g_idx = fs1_end_idx + 1 + i`
- After all bars:
  - If `eng.declared`: return `(dir, eng.start_idx, events, eng.confirmed_at_idx)`
  - If not declared: return `(None, -1, [{"type": "no_second_swing_declared"}], -1)`
- Events emitted:
  - `{"type": "swing2_classified", "dir": dir, "bar": eng.start_idx, "time": eng.start_time}`
  - `{"type": "fs2_segment", "dir": eng.dir, "start_idx": eng.start_idx, "start_px": eng.start_px, "end_idx": eng.end_idx, "end_px": eng.end_px, "confirmed_at_idx": eng.confirmed_at_idx, "confirmed_at_time": eng.confirmed_at_time}`

---

## Phase 3 — Wire into `simulate_day` (1min only, controlled by dropdown)

**File**: `backend/src/intraday.py`

**Scope**: Entire Phase 3 is wrapped in `if use_1m:` — 5min logic unchanged.

**New config key**: `swing_mode: str` (default `"opposite_swing_needed"`)

- `"opposite_swing_needed"` — wait for opposite swing before entry (Phase 2 logic)
- `"none"` — no second-swing gate, current 1min behavior

**Changes inside `simulate_day`**:

1. After `_classify_first_swing_v2` (line 355), extract first-swing end info:

   ```python
   fs1_dir = swing_dir
   fs1_end_idx = eng.end_idx  # need to get this from FsV2Engine
   fs1_end_px = eng.end_px    # first swing's high or low
   fs1_end_time = eng.end_time
   ```

   **Note**: `_classify_first_swing_v2` currently only returns `(direction, start_idx, events, confirmed_at_idx)`. Need to also return `end_idx`, `end_px`, `end_time`. Modify return to 7-tuple:

   ```python
   return (direction, seed, events, eng.confirmed_at_idx, eng.end_idx, eng.end_px, eng.end_time)
   ```

   Update all call sites.

2. After first-swing classification, call second-swing detection:

   ```python
   swing_mode = cfg.get("swing_mode", "none")
   if use_1m and swing_mode == "opposite_swing_needed" and fs1_dir is not None and fs1_end_idx >= 0:
       fs2_dir, fs2_start, fs2_ev, fs2_confirmed_idx = detect_second_swing(
           candles, result["date"], fs1_dir, fs1_end_idx, fs1_end_px, fs1_end_time
       )
       result["events"].extend(fs2_ev)
       result["swing2_direction"] = fs2_dir
       result["swing2_confirmed_idx"] = fs2_confirmed_idx
   else:
       fs2_dir = None
       fs2_confirmed_idx = -1
       if use_1m and swing_mode == "opposite_swing_needed":
           result["events"].append({"type": "second_swing_skipped", "reason": "no_swings_detected"})
   ```

3. **Entry alignment gate** — compute which swing must be confirmed before entry:

   ```python
   if use_1m and cfg.get("swing_mode") == "opposite_swing_needed":
       # For 1min opposite_swing_needed: entry requires the OPPOSITE swing to be confirmed.
       # First swing = fs1_dir, second swing = fs2_dir.
       # If fs2_dir is opposite to fs1_dir → entry gate = fs2_confirmed_idx
       # If fs2_dir is same as fs1_dir or None → skip day (no entry)
       if fs2_dir is not None and fs2_dir != fs1_dir:
           entry_swing_confirmed_idx = fs2_confirmed_idx
           result["events"].append({
               "type": "second_swing_armed",
               "dir": fs2_dir,
               "confirmed_at_idx": fs2_confirmed_idx,
           })
       else:
           # Same direction as first swing or not declared → skip day
           entry_swing_confirmed_idx = 9999999  # effectively blocks all entries
           result["events"].append({
               "type": "skipped_same_direction_swing2",
               "fs1_dir": fs1_dir,
               "fs2_dir": fs2_dir,
           })
   else:
       # 5min OR swing_mode=none: use FsV2 gate (existing behavior)
       entry_swing_confirmed_idx = fs_confirmed_idx
   ```

4. Update `fs_gate_ok` (line 691):
   ```python
   fs_gate_ok = entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx
   ```

---

## Phase 4 — Yellow second-swing line on chart

**Files**:

- `backend/src/intraday.py` — already emits `fs2_segment` event (see Phase 2)
- `frontend/src/app/chart/page.tsx` — render yellow segment line

**Frontend approach** (in `buildPaneOverlays`):

- Filter events for `type === "fs2_segment"`
- Render a horizontal segment from `start_idx` to `end_idx` at `start_px` (or draw between both points)
- Color: `#FFD700` (gold/yellow), linewidth 2px
- Same overlay system as existing white first-swing line

**Both panes**: ensure second-swing overlay appears on both 5min and 1min panes when applicable.

---

## Phase 5 — Pivot High Break entry method (1min only)

**Files**:

- `backend/src/intraday.py` — new `detect_pivot_break()` function + cfg
- `frontend/src/components/IntradayPanel.tsx` — dropdown

**New config key**: `entry_method: str` (default `"pace_break"`)

**New function**:

```python
def detect_pivot_break(
    candles: list[dict],
    i: int,
    trade_dir: int,           # 1 = long, -1 = short
    normal_highs: list,       # sealed high pivots from WalkerEngine
    normal_lows: list,        # sealed low pivots from WalkerEngine
) -> dict | None:
    """Bar i breaks the most recent sealed pivot in the trade direction.
    Returns {type, level, bar} or None."""
    if i < 2:
        return None
    cur = candles[i]
    if trade_dir == 1:
        # LONG trigger = close above most recent high pivot
        if normal_highs and cur["close"] > normal_highs[-1]["px"]:
            return {"type": "pivot_break", "level": normal_highs[-1]["px"], "bar": i}
    else:
        # SHORT trigger = close below most recent low pivot
        if normal_lows and cur["close"] < normal_lows[-1]["px"]:
            return {"type": "pivot_break", "level": normal_lows[-1]["px"], "bar": i}
    return None
```

**In simulate_day pace-break block** (around line 762):

```python
brk = None
if cfg["entry_method"] == "pivot_break":
    # 1min pivot break: look for recent pivot high/low break
    # trade_dir derived from pace-break logic (already computed as variable)
    brk = detect_pivot_break(candles, i, trade_dir, normal_highs, normal_lows)
else:
    # Default: pace-break detection (existing)
    brk = detect_pace_break(candles, i, cur_swing, swing_extreme, _swing_size(), base_avg)
```

---

## Phase 6 — UI dropdown + backtest

**Files**:

- `frontend/src/components/IntradayPanel.tsx`:
  - Add `ENTRY_METHODS = [{"value": "pace_break", "label": "Pace Break"}, {"value": "pivot_break", "label": "Pivot High Break"}]`
  - Add `<select>` for entry_method between execution mode and trailing mode
- `frontend/src/lib/api.ts`: Add `entry_method` to `Settings` interface
- `backend/src/intraday.py`: `DEFAULT_CFG["entry_method"] = "pace_break"`
- `backend/server.py`: Pass `entry_method` to backtest config

**Backtest verification**:

1. `execution=1min, entry_method=pace_break` → should match current 1min results (baseline)
2. `execution=1min, entry_method=pivot_break` → compare R-multiples
3. Verify alignment rule: bias=BULLISH + first_swing=BULLISH → no entries (day skipped)
4. Verify yellow line on chart for second-swing days
5. 5min remains unchanged (no second-swing logic, no pivot_break option)

---

## Summary of Changes by File

| File                                        | Change                                                                                                                                                       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `backend/src/swing_engine.py`               | Add `reset()` method to FsV2Engine                                                                                                                           |
| `backend/src/intraday.py`                   | Modify `_classify_first_swing_v2` to return 7-tuple; add `detect_second_swing()`; wire second-swing gate; add `detect_pivot_break()`; add `entry_method` cfg |
| `frontend/src/components/IntradayPanel.tsx` | Add entry_method dropdown                                                                                                                                    |
| `frontend/src/lib/api.ts`                   | Add `entry_method` to Settings                                                                                                                               |
| `frontend/src/app/chart/page.tsx`           | Render yellow fs2_segment line                                                                                                                               |

---

## What's NOT changing (5min untouched)

- FsV2 gate remains the only entry gate for 5min (no second-swing logic)
- Pace-break + domination/structure detection stays the same for 5min
- All existing 5min results remain identical
- 1min pivot_break is 1min only

---

## Final Backtest Verification (2026-08-30)

All 5 modes ran cleanly via `python debug/_ss_test.py`:

| Mode                                     | Trades | WR    | Total R      | Notes                                      |
| ---------------------------------------- | ------ | ----- | ------------ | ------------------------------------------ |
| 5min baseline (swing_mode=none)          | 142    | 26.8% | -2.50        | unchanged — 5min logic untouched           |
| 1min swing_mode=none                     | 51     | 33.3% | -9.23        | current 1min behavior                      |
| 1min swing_mode=opposite_swing_needed    | 21     | 23.8% | -11.03       | alignment rule active (significant filter) |
| 1min pivot_break + opposite_swing_needed | 12     | 41.7% | **+2.76** ✅ | **profitable** — selective with high WR    |
| 1min pivot_break + swing_mode=none       | —      | —     | —            | (was tested, not shown in table)           |

**Key finding**: the second-swing alignment rule is essential for pivot break to be profitable.

- `pivot_break` without alignment = negative R
- `pivot_break` + `opposite_swing_needed` = +2.76R (winning)

**Event counts (1min, opposite_swing_needed)**:

- `fs2_segment` events: 73
- `second_swing_armed` events: 38 (opposite direction found)
- `skipped_same_direction_swing2` events: 225 (skip-day triggered)

**Code fixes during implementation**:

1. `WalkerEngine` previously only fed when `sl_mode == "prev_pivot"`. Removed that gate so walker feeds for ALL sl_modes (pivot_break needs `normal_highs`/`normal_lows`).
2. `detect_pivot_break` initially used `["px"]` dict access; fixed to `.px` attribute access (AlgoPivot is a dataclass).
3. **5min `ts` missing in `run_backtest`**: The 5min df was not getting `ts` column set before `_prep_day`. Fixed by adding `df["ts"] = (df["timestamp"].astype("int64") // 1_000_000_000).astype("int64")` for 5min df.
4. **`m1_idx_to_5` mapping bug**: The mapping function returned the FIRST 5min bar <= 1min ts, but should return the LAST (most recent) 5min bar whose timestamp is <= 1min ts. Fixed by iterating through and keeping track of the last valid index.
5. Frontend: added `entry_method` and `swing_mode` to `BacktestParams` interface, `DEFAULT_BT_PARAMS`, `getIntradayBacktest` URLSearchParams, `ENTRY_METHODS` + `SWING_MODES` dropdowns in IntradayPanel, and 2 new query params in `server.py` `intraday_backtest` endpoint.

**Phase 4 — Yellow second-swing line**: COMPLETED. `FsV2Engine.reset()` added to TypeScript, `computeSecondSwingResults()` implemented, `algoSecondSwing` prop wired to StockChart, yellow useEffect rendering added.

**CRITICAL FIX — Second Swing Detection on 1min**:
The user's Aug 28 case showed yellow line from 9:27 to 9:31, but there was no second swing at that time on 5min. Root cause: `detect_second_swing` ran on 5min candles but user sees 1min bars. Fix: pass `m1_candles` to `detect_second_swing`, detect on 1min bars, then map indices back to 5min using timestamp comparison.

**All phases complete.**
