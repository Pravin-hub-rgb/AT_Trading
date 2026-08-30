# 1min Precision Entry — Plan

## Context

The intraday engine has two execution modes:

- **`5min`** (default, "Conservative 5-Min") — entry fires at the **5-min bar close**; trade management uses bar H/L/C (SL-first)
- **`1min`** — currently only affects **trade management** via `_manage_1m_chunk` (color-aware fills on real 1-min candles for SL/target). **Entry timing itself is still on 5-min bar close** — same as 5min mode.

User wants a true **1min precision entry** — when the 5-min structure says "go", actually time the entry on 1-min price action (not blindly market-on-close at the 5-min bar end). Same engine, same bias, same setup detection — just refine the entry moment to a 1-min confirmation. Positions stay visible on both 5-min and 1-min charts (already wired via `entry_ts` / `entry_time`).

## What "precision entry" means here

The 5-min engine detects a setup (M2 pattern break, M3 level test, or the direct M1/M2 entry) at the close of a 5-min bar. In `5min` mode, that close is the fill price. In **`1min` mode**, after the 5-min setup is detected, we look at the **next 1–3 closed 1-min bars** for a precise entry confirmation and fill at a 1-min level. This is the "course recipe" — entry is at the _domination candle close on 1-min_, not the 5-min bar close.

Specifically, the precision flow is:

1. 5-min engine detects a setup (pace break / level test / direct break) and creates a 1-min **armed hunt** (like the existing `armed` dict, but tracking the entry-bar ts)
2. The 1-min entry engine scans the next ≤ 3 closed 1-min bars for a **1-min confirmation candle**:
   - **LONG entry**: 1-min bar prints a low that touches/re-tests the level, then closes in the upper half (close-q ≥ 0.50) — the wick + body pattern of a precision buy at the level
   - **SHORT entry**: mirror — 1-min bar touches the level, closes in the lower half
3. Fill at the **1-min candle's close** (not 5-min close)
4. If no 1-min confirmation within **3 bars** (3 minutes), enter at the 5-min close anyway (fallback) — this prevents missed setups

## Data flow (already in place, just needs expansion)

- `m1_map: dict[str, pd.DataFrame]` is already built in `run_backtest` when `cfg['execution'] == '1min'`
- `m1_day` is already passed to `simulate_day`
- `_manage_1m_chunk(trade, upto_ts)` is already used for **exit** management (color-aware fills)
- We extend this to also handle **entry** confirmation

The `entry_ts` / `entry_time` fields are already on the trade object — they'll naturally show the 1-min entry time on both charts without any frontend changes.

## Architecture

### Entry detection (existing — 5-min path)

- `simulate_day` loop on 5-min bars detects pace breaks, sets `armed` / `day_setup`
- On direct flow-favor entry (5-min break bar), `_open_trade(i, ...)` is called immediately at 5-min bar close
- This is the path we refine in 1min mode

### Entry refinement (new — 1-min precision path)

- New function: `_try_1min_entry(sim_ctx, m1_day, armed, day_setup, open_trade, entries_done, ...) -> bool`
- Called inside `simulate_day` on each 5-min bar, when `use_1m` is True and there is an `armed` setup waiting
- Scans `m1_day` between `armed["armed_ts"]` and `cur["ts"]` for the confirmation candle
- If found, calls `_open_trade` with the 1-min bar's index/ts/close (and the 1-min `dbar` for the `dom_*` fields)
- If not found within timeout (3 bars / 3 minutes from armed_ts), `_open_trade` at 5-min close as fallback

### Two flavors of 1-min entry

There are **two ways** the 1min refinement can fire:

**A. Direct-entry refinement** (M1/M2 pace break already detected as "direct go"):

- 5-min: `cur["close"]` is a domination candle (consume ≥60%, big ≥1.5×avg, close-q ≥50%) → `_open_trade` fires immediately
- 1-min: same 5-min signal sets `armed["direct"] = True`; we DON'T fire immediately; we hunt 1-min confirmation within the next 3 1-min bars (the same 5-min window contains 5 × 1-min bars; the 1-min hunt happens among them)
- If 1-min confirms → entry at 1-min close (often 1–2 minutes later, at a better price)
- If no 1-min confirm → fall back to 5-min close (don't lose the trade)

**B. Retest/refinement path** (already armed hunt exists):

- 5-min: structure break detected → `armed` set, waiting for retest + domination
- The 5-min confirmation (`detect_domination_at_level` in the existing code) is already based on 5-min bars
- In 1min mode, we replace that 5-min confirmation with a 1-min confirmation scan (same logic, just on 1-min data)

For V1 we focus on path **A** (direct-entry refinement) because it gives the clearest "entry timing" win and is easier to verify. Path B can be a follow-up.

## Implementation steps

### Step 1: Add 1-min entry-trigger helper (`backend/src/intraday.py`)

- New function `_1min_entry_trigger(m1_day: pd.DataFrame, armed_ts: int, trade_dir: int, level: float, avg: float) -> dict | None`
- Returns `{ts, open, high, low, close, time, idx}` of the first 1-min candle that meets the confirmation rule, or None
- Rule: within `[armed_ts, armed_ts + 3*60s]`, the first 1-min bar where
  - LONG: bar's low is within `LEVEL_TOL_MULT * avg` of `level` AND close in upper half (close-q ≥ 0.50) AND bar is green
  - SHORT: bar's high within tol of `level` AND close in lower half AND bar is red
- Cached per `armed_ts` to avoid re-scanning on every 5-min bar (use `armed` dict to store the resolved 1-min entry)

### Step 2: Refactor `_open_trade` to accept arbitrary entry bar

- Already takes `bar_idx: int` — but `bar_idx` is the **5-min** bar index and `candles` is the 5-min list
- Add an optional `dbar` override so 1-min mode can pass a 1-min candle as the `dbar` (used for `dom_low`, `dom_high`, `domination_time`, `entry_price`, `entry_ts`, `entry_bar`)
- The 5-min `candles[i]` is still passed for the SL reference and other 5-min context

### Step 3: Insert 1-min entry hunt in `simulate_day` (`backend/src/intraday.py` line ~879)

- In the `brk["type"] in ("domination", "candle-size")` block, when `use_1m` is True:
  - DON'T call `_open_trade` immediately
  - Set `armed = {level, trade_dir, break_type, armed_at, age: 0, direct: True, armed_ts: cur["ts"]}`
- The existing 1-min management loop (`_manage_1m_chunk`) is currently only called when `open_trade is not None`
- Add a new block: after `_manage_1m_chunk` call, if `open_trade is None and armed is not None and armed.get("direct") and use_1m`, call `_try_1min_entry` to resolve armed → entry
- If no 1-min trigger found and we've passed `armed_ts + 3*60s` AND the 5-min bar has closed, fall back to 5-min entry at `cur["close"]`

### Step 4: Add cfg flag for the 1-min wait (optional)

- Add `"1min_entry_timeout_bars": 3` to `DEFAULT_CFG` (number of 1-min bars to wait for confirmation)
- If 0, the 1min engine behaves like 5min (no refinement) — useful for A/B testing

### Step 5: Frontend — execution mode already has the `1min` option

- `EXECUTION_MODES` in `IntradayPanel.tsx` already has the `1min` option (line 39+)
- Just confirm the `1min` label is descriptive enough — maybe rename to "Exec: 1-Min Precision" for clarity
- No new UI controls needed (toggles would just complicate — same pattern as FsV2 gate: hard-coded defaults, no UI)

### Step 6: Diagnostics + backtest verification

- Create `backend/debug/_precision_compare.py` — runs the backtest with `execution='5min'` vs `execution='1min'`, prints stats + per-trade diff
- Run `python -c "from src.intraday import run_backtest, DEFAULT_CFG; r = run_backtest(None, {**DEFAULT_CFG, 'execution':'1min'})"` to make sure it doesn't crash
- Verify the diagnostic `_check_fs_timing.py` still passes (0 trades before FsV2)
- Sample 1 trade and inspect the 1-min entry: `entry_ts` should be 1–3 minutes after the 5-min pace break `ts`, `entry_price` should be the 1-min close

## Files to change

1. **`backend/src/intraday.py`** — main changes
   - Add `_1min_entry_trigger()` helper (new function, ~30 lines)
   - Modify `_open_trade` to accept `dbar` override (~5 lines)
   - Modify the direct-entry block in `simulate_day` (lines ~879-892) to defer entry in 1min mode (~10 lines)
   - Add the 1min-entry hunt block in `simulate_day` after `_manage_1m_chunk` (~15 lines)
   - Add `1min_entry_timeout_bars` to `DEFAULT_CFG` (1 line)

2. **`frontend/src/components/IntradayPanel.tsx`** — cosmetic
   - Rename `1min` option label to "Exec: 1-Min Precision" (1 line)
   - No other UI changes

3. **`backend/debug/_precision_compare.py`** — new diagnostic
   - 5min vs 1min backtest compare (~60 lines)

## Out of scope (follow-up)

- Path B (1min refinement of retest/level-test setups)
- Wick-domination detection on 1min (M3 wick variant from `docs/base condition.md` item 4)
- 1min-derived SL (using 1min micro-pivots instead of 5min ref-extreme)
- Volume doubling on 1min (out of scope — spot volume = 0 in dataset)
- Multi-day flow-age exhaustion (item 13 in `docs/base condition.md`)

## Verification checklist

- [ ] `python -c "from src.intraday import run_backtest, DEFAULT_CFG"` imports cleanly
- [ ] `python debug/_precision_compare.py` runs and prints both 5min/1min stats
- [ ] `python debug/_check_fs_timing.py` still shows 0 trades before FsV2
- [ ] Pick 1 sample trade, confirm `entry_ts` is 1–3 minutes after `armed_ts`
- [ ] Pick 1 sample trade with no 1min confirm, confirm fallback to 5min close
- [ ] Frontend `IntradayPanel` shows the `1min` exec option with new label
- [ ] No new TypeScript errors in chart page or IntradayPanel
