# Rolling Window Data Loss: Fix Plan (Finalized)

## Problem (3 failure paths)

1. `_rebase_swings_to_window` (`live_stuff/live/feed.py:559`) drops break marks outside 30d window
2. `_collect_signals` (`_vendored/btc_engine.py:260-263`) skips breaks whose candles aren't in trimmed store
3. SL computation (`_vendored/btc_engine.py:310`) uses `candles[_sw_idx : _hi_i]` — clamped indices give wrong SL

## Decision

**Store all candles from seed-to-now in DB. Pass full candles + full swings to simulation. No trimming, no rebasing.**

## Timing (verified)

| History | 15m candles | sim time |
|---|---|---|
| 30d | 2,881 | 0.07s |
| 90d | 8,641 | 0.27s |
| 180d | 17,281 | 0.53s |
| 365d | 35,041 | 1.20s |
| full (3.8yr) | 129,715 | 5.0s |

5.0s per 15m close is acceptable cadence but blocks the event loop → **offload `_run_v18_simulation` to `asyncio.to_thread`** (existing pattern in `rate_manager`). No correctness change.

## Implementation steps

1. **`persistence/database.py`**: Add `candles` table (tf, ts, date, open/high/low/close PK(tf,ts)) + index
2. **`persistence/state_store.py`**: Add `insert_candle`, `insert_candles_bulk`, `load_candles`
3. **`loop.py.__init__`**: Add `self.all_candles_15m = []`, `self.all_candles_1h = []`
4. **`feed.py` seed path**: After fetch, append to `all_candles_*` + bulk-insert to DB. Keep `window_*` for display
5. **`loop.py` `_on_15m_close`/`_on_1h_close`**: Append to `all_candles_*` + single DB insert. Keep window trim for display
6. **`feed.py` recovery**: If DB has candles → load ALL → reset engine (no state restore) → feed ALL candles (g_idx 0..N-1) → rebuild chain. If empty → existing seed path
7. **`signals.py` `_run_v18_simulation`**: Use `all_candles_*` + `all_swings_*` (no rebase). Min-bars guard on `len(all_candles_15m)`. Open-swing append directly (no rebase)
8. **`_run_v18_simulation` offload**: Wrap call in `asyncio.to_thread` in `_on_15m_close`/`_on_1h_close`
9. **`_collect_signals` guard**: Add comment only (harmless with full store)
10. **`_rebase_swings_to_window`**: Leave in feed.py (backward compat), stop calling from signals.py
11. **Leave `window_*`** for display. Leave `trading.py:213` trail-SL on trimmed window (30d > 16d cap)

## Validation

- Timing: done (5.0s full, 1.2s/1yr). Offload to thread.
- Parity: sim on full candles+swings vs trimmed → identical trades
- Persistence: seed → candles accumulate in DB → full-history sim runs
- Recovery: kill/restart → candles load → engine rebuilds → trades match

## Out of scope

- 1min streaming, cleanup job, `all_swings_*` persistence, Option C (incremental sim refactor)
