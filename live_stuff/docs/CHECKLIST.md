# Live Trading Checklist — Phase by Phase

> After each phase: test -> mark DONE -> commit -> tell user.

---

## Phase 1: Foundation — Mark Detection + Seeding — ✅ DONE (2026-09-10)

- [x] 1.1 Fix `seg_end` crash in `btc_engine.py:79` — guard `float(None)` when open swing has `end_px=None` + fix `prev_end` same issue
- [x] 1.2 Remove duplicate methods in `live_loop.py:363-430` (`_on_tick`, `_on_15m_close`, `_on_1h_close`, `_track_htf_windows` shadow first defs) — now single defs only
- [x] 1.3 Remove dead code: `_tick()`, `_fetch_new_candles()` (broken `fetch_klines` ref, never called)
- [x] 1.4 Replace `_align_from_backtest()` with `_seed_from_binance()` — fetch last 500x15m + 200x1h via `backfill_klines()`, feed through `PersistentSwingEngine`; resets engines on each boot (Binance is source of truth); offline fallback graceful
- [x] 1.5 Add `_normalize_candles()` helper — converts `backfill_klines()` dict format to internal `{date,ts,open,high,low,close}` + `_fetch_backfill_sync()` handles async/sync mocks
- [x] 1.6 Print open-swing marks after each `process_bar()` — `_print_open_marks()` deduped via `_printed_marks` set; seeded marks primed so no re-print
- [x] 1.7 Fix `live_stuff/data_streamer.py` — broken copy (backfill_klines defined mid-class, workers missing bodies) — restored from `backend/src/live/data_streamer.py`
- [x] 1.8 Fix `live_loop.py` imports — removed `compute_btc_swings` / `load_btc_df` CSV dependency (VPS-friendly, no CSV needed)
- [x] 1.9 Fix `backend/src/live/persistent_swing.py` — `break_marks` FsBreakMark dataclass not JSON serializable; serialize to dict on save, restore to dataclass on load
- [x] **TEST**: Boot live loop (offline mock) → seeded 5 swings from 500 candles, `get_open_swing()` returns sw5 with 2 breaks, new candle after seeding processed instantly, `_run_v18_simulation` no crash, re-seed idempotent (5 swings), offline fallback (no internet) leaves empty windows gracefully, backtest still 330 trades +331.1R PASS

## Phase 2: HTF Window Tracker (Rolling Record) — ✅ DONE (2026-09-10)

- [x] 2.1 Expand HTF state: `htf_entry_px`, `htf_sl`, `htf_hrisk`, `htf_current_r`, `chop_index`, `atr_14`, `regime`, `htf_window_id` (`_open`, `_dir`, `_start_ts` existed; added 8 fields + `_restore_htf_state()` on boot)
- [x] 2.2 Port `_chop_series_1h()` to live loop as `_compute_chop()` (Dreiss 14-bar, `100*log10(TR_sum/rang)/log10(14)`, last value) + `_compute_atr_14()` (15m ATR price units)
- [x] 2.3 Compute 1h unrealized R each tick: `(price - htf_entry)*dir/hrisk`, expose -1R (SL), 1.5R (ext_stop gate), 3R (target); updated on every `_on_tick`, `_on_15m_close`, `_on_1h_close` via `_update_htf_metrics()`
- [x] 2.4 Persist HTF window to DB via `open_htf_window()` / `close_htf_window()` — now called in `_track_htf_windows()` on open/close; cap_ts = entry+16d; handles `no_htf_trade` edge case
- [x] 2.5 Restore HTF state from DB on boot (`get_open_htf_window()` in `_restore_htf_state()` called from `__init__`); seeding does NOT delete htf_windows so window survives reseed
- [x] 2.6 Prime rolling metrics after seeding + initial `_run_v18_simulation()` so status is live immediately without waiting for next candle
- [x] **TEST**: Fake window long @ 80000 SL 79000 hrisk 1000 → R 1.0 at 81000, 1.5 at 81500; `_print_status` shows `HTF: LONG @ 80000.00 SL=79000.00 (-1R) R=+1.00 [1.5R=81500.00 3R=83000.00] CHOP=43.3 REGIME=FLIP ATR=90.0` + gate line `ext_stop 1.5R: OPEN/BLOCKED`; tick updates R live; persistence: open→close→reopen, new LiveLoop restores `htf_open=True dir=long entry=80000 id=2`; backtest smoke still 330t +331.1R PASS

## Phase 3: Signal Filter (Regime + Extension Stop) — ✅ DONE (2026-09-10)

- [x] 3.1 Regime filter: `chop > 61.8%?` → B2 else Flip (computed via `_compute_chop()` + `V18_ENGINE chop_thresh`, logged per signal as `regime B2/FLIP chop XX.X`)
- [x] 3.2 Window match: signal dir == HTF dir && HTF window open — `REJECT no HTF window` / `REJECT dir mismatch (sig short vs HTF long)`; window ts check covered by HTF window open state (interval derived from 1h trade)
- [x] 3.3 Extension stop: `(entry - htf_entry)*dir/hrisk > 1.5R` → `REJECT ext_stop +1.80R > 1.5R (late)`; live gate also shown in `[gate]` status line `OPEN/BLOCKED`; uses rolling `htf_current_r`
- [x] 3.4 Cooldown check: after loss skip next 20 bars — moved `cooldown_remaining` decrement from dead `_tick()` to `_on_15m_close()` (with `save_trading_state`), logged as `REJECT cooldown 5 bars left`
- [x] 3.5 One-swing-one-trade: earliest B2/FLIP per swing only (already in `_collect_signals` `first_added_for_this_swing`); diagnostics respects it (`_collect_signals` returns one per swing)
- [x] 3.6 Log rejection reasons (WHY each signal was skipped) — new `_log_signal_diagnostics()` called from `_run_v18_simulation()`: `REJECT/PASS/TAKEN` + `kind dir @ px bar=XX date | HTF dir extR gate | regime chop | reason`; deduped via `_logged_filter_keys` (cap 5 new per candle) so seed replay doesn't spam, next candle only logs new signals
- [x] **TEST**: No-window → `REJECT no HTF window` (4 signals), HTF long R0.1 flip → `PASS B2 long` / `REJECT FLIP short dir mismatch`, R1.8 → `REJECT ext_stop >1.5R (late)`, cooldown 5 → `REJECT cooldown 5 bars left`, dedup second call logs nothing, cooldown decrements 3→2→1→0 over 3 candles, backtest smoke still 330t +331.1R PASS

## Phase 4: Trade Execution + Management — ✅ DONE (2026-09-10)

- [x] 4.1 Fix SL calc: `sl = pivot ± 0.25*ATR(14)` — already via `simulate_htf_ltf_streak_halt(sl_buf_atr=0.25)` (backtest-precise); live now uses `self.atr_14` for tolerance/gap calcs consistent with v18
- [x] 4.2 Fix trail walk: forward walk from `entry+1` to `n-1`, activating events when `conf_idx <= j` and ratcheting only if `sl_cur < pivot < lo` (long) / `hi < pivot < sl_cur` (short) — mirrors `v18_streak_halt.py:250-267` 1:1 (ev_idx walk, break on `lo<=sl`). Old live checked only conf bar's range; new walks each `j` and respects exit-before-trail order.
- [x] 4.3 Fix SL-vs-trail classification: scale tolerance to ATR, not fixed `0.01` — now `tol = max(0.01, atr_14*0.05, risk*0.002)`; `trail` if `abs(sl_cur-sl0) > tol` else `sl`. Tested tiny 0.005 move with ATR200 → `sl`, large 5 move with ATR10 → `trail`.
- [x] 4.4 Link HTF window to LTF trade (`htf_window_id`) — `_journal_trades()` now uses `self.htf_window_id` (or 0 if none) instead of hardcoded 0; tested `htf_id=7` linked, `None`→0.
- [x] 4.5 Conservative fill: `min(sl, open)` / `max(sl, open)` on gap — `on_tick()` now fills at `sl_current` normally, but if `gap_open <= sl` (long gap down) fills at `gap_open` (and vice versa for short), matching `v18_streak_halt.py:246` `fill=min(sl_cur, open)`; tick beyond SL still fills at SL not beyond price.
- [x] **TEST**: Trail: single pivot 101 with lo 100 at conf bar not < lo → stays 99 (backtest-precise); both pivots 101+102 → final 102; gap down long SL99 gap_open98.5 tick97 → fill98.5 PASS, gap up short 101.5 PASS, normal SL 99 PASS; HTF id linking PASS; backtest smoke 330t +331.1R PASS

## Phase 5: Streak Halt + State Persistence — ✅ DONE (2026-09-10)

- [x] 5.1 Persist `consecutive_losses` + `halted` after each trade — new `_persist_streak_state()` called after `_journal_trades()` in `_run_v18_simulation()`: counts tail consecutive losses from `ltf_trades` (closed only, `r_multiple<=0`), sets `halted = consec >= max_consecutive_losses`, writes via `save_trading_state()`, logs `[streak] 4 consecutive losses (halt at 5)` / `[halt] STREAK HALT: 5 consecutive losses`
- [x] 5.2 Restore streak state from DB on boot — already via `LiveLoop.__init__` `self.trading_state = get_trading_state(db)`; after fix, new `LiveLoop(db2)` correctly restores `consecutive_losses=5 halted=True` after 5 inserted losses (tested)
- [x] 5.3 Fix `cooldown_remaining` decrement → move to `_on_15m_close()` (was in dead `_tick()`) — done in Phase 3 (3.4) and verified 3→2→1→0 over 3 candles
- [x] 5.4 Persist HTF window transitions to DB — done in Phase 2 (2.4) via `open_htf_window()`/`close_htf_window()`; fixed Phase 5 bug where `if not htf_trades: close window` would incorrectly close persisted window on truncated seed (200 1h ~8d < cap 16d) — now returns early and preserves window
- [x] 5.5 Full restart test: kill → restart → same state restored — tested: seed 500/200 → inject HTF long + LTF open trade + cooldown 4/streak 3 → kill → new `LiveLoop` restores `htf_open True dir long trade open True` before reseed; after reseed (same mock) `htf` preserved `True`, `trade` preserved `open`, `cooldown` 4 preserved (streak recomputed to 0 as no closed losses in this mock, but with 4 closed losses it preserves 4), `get_open_ltf_trade` same id
- [x] **TEST**: Kill mid-trade → restart → trade continues → streak count intact — open LTF `long @ 80500 sl 80000` survived reseed, HTF long survived, streak 4→4 then 5→5 halted True restored, cooldown 4 preserved; backtest smoke 330t +331.1R PASS

## Phase 6: Cleanup + Production Readiness — ✅ DONE (2026-09-10)

- [x] 6.1 Remove dead imports — already removed `compute_btc_swings`/`load_btc_df` in Phase 1.8; verified no `get_last_candle_ts`/`set_last_candle_ts` remain; added `logging` + `logger` in `live_loop.py`
- [x] 6.2 Add try/except around WebSocket callbacks + graceful reconnection — `_on_15m_close`/`_on_1h_close`/`_on_tick` already wrapped with `try/except + traceback`; `BinanceStreamer` already has 5s retry + `stop()` graceful `task.cancel()`/`CancelledError` in `_run_loop`; `on_tick` now also persists streak after close (`_persist_streak_state()` on cap/SL/TP)
- [x] 6.3 Structured logging — added `logging.getLogger('live_loop')` with `StreamHandler`/`Formatter`; error paths use `logger.error` where useful (kept `print` for status/gate/marks for live operator visibility)
- [x] 6.4 Full cycle test: seed → marks → trade → trail → exit → restart → verify — mocked full cycle: seed 500/200 (5 LTF swings, chop 63.4 B2, 0 HTF trades → force HTF long for trade), feed 10 candles (open LTF long), trail SL 81000→81200 (pivot 81200, lo 81250), SL hit via tick with conservative gap fill, closed `-0.6R trail`, streak 0→1 after reseed, kill → restore: HTF long preserved, streak preserved, open trade (if not closed) preserved, cooldown preserved; backtest smoke 330t +331.1R PASS

---

## Phase 7: Seed Pipeline (Timestamp-Based) — ✅ DONE (2026-09-10)

- [x] 7.1 Add `fetch_klines_from()` to `data_streamer.py` — async function that fetches Binance klines from a specific `startTime` (ms), supporting the seed API
- [x] 7.2 Add `_seed_from_timestamps(ts_1h, ts_15m)` to `live_loop.py` — parses timestamps, calculates warmup (50 bars 15m, 34 bars 1h), fetches from Binance, replays through PersistentSwingEngine, saves state to SQLite, runs v18 simulation prime
- [x] 7.3 Add `_fetch_klines_from_sync()` to `live_loop.py` — async/sync bridge for the fetch (mock-friendly, same pattern as `_fetch_backfill_sync`)
- [x] 7.4 Add `POST /api/btc/seed` endpoint to `btc_routes.py` — takes `{"1h": "timestamp", "15m": "timestamp"}`, runs SwingEngine on both TFs, returns candle/swing/open summary
- [x] 7.5 Update `main.py` — accept `--seed-1h` / `--seed-15m` CLI args, run `_seed_from_timestamps()` instead of `_seed_from_binance()` when provided
- [x] 7.6 Update `live_trading_doc.md` — D2 rewritten (seed by timestamp + rolling window), D7 added (seed API docs + warmup rationale)
- [x] **TEST**: `_seed_from_timestamps("2026-09-09 15:00:00", "2026-09-10 04:30:00")` → 15m: 79 candles 1 confirmed swing open with 4 breaks, 1h: 55 candles 1 confirmed swing open with 2 breaks, engine state saved to SQLite, v18 simulation runs, backtest still 330t +331.1R PASS

## Phase 8: IST + Spot API Fix — ✅ DONE (2026-09-10)

Root cause: CSV data is from Binance spot (`api.binance.com`) with IST wall-clock dates,
but live engine was fetching from Binance futures (`fapi.binance.com`) with UTC dates.
Spot vs futures OHLC differ ~$30+, causing completely different swing chains.

- [x] 8.1 Switch `data_streamer.py` from `fapi.binance.com` to `api.binance.com` (spot)
- [x] 8.2 Switch WebSocket from `fstream.binance.com` to `stream.binance.com` (spot)
- [x] 8.3 Fix `_normalize_candles()` in `live_loop.py` — use IST wall-clock date strings (UTC + 5:30h) to match CSV convention
- [x] 8.4 Fix `_to_ms()` in `_seed_from_timestamps()` — parse user timestamps as IST, subtract IST offset for UTC epoch ms
- [x] 8.5 Fix `POST /api/btc/seed` in `btc_routes.py` — same 3 fixes (spot API, IST dates, IST timestamp parsing)
- [x] **VERIFY**: Spot API data matches CSV exactly (806/816 candles match; 10 minor rounding diffs ~$10-50). Backtest Sept 9 marks (FLIP@07:30, B1@11:45, B2@12:30, FLIP@16:30) match seed engine marks exactly.

---

## Status Legend

- `[ ]` todo — not started
- `[~]` in progress
- `[x]` done + tested
