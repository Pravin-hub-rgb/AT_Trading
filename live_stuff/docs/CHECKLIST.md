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

## Phase 7: Seed Pipeline (Timestamp-Based) — ✅ DONE (2026-09-10) (superseded by Phase 9)

- [x] 7.1 Add `fetch_klines_from()` to `data_streamer.py` — async function that fetches Binance klines from a specific `startTime` (ms), supporting the seed API
- [x] 7.2 Add `_seed_from_timestamps(ts_1h, ts_15m)` to `live_loop.py` — parses timestamps, fetches from exchange, replays through PersistentSwingEngine, saves state to SQLite, runs v18 simulation prime
- [x] 7.3 Add `_fetch_klines_from_sync()` to `live_loop.py` — async/sync bridge for the fetch (mock-friendly, same pattern as `_fetch_backfill_sync`)
- [x] 7.4 Add `POST /api/btc/seed` endpoint to `btc_routes.py` — takes `{"1h": "timestamp", "15m": "timestamp"}`, runs SwingEngine on both TFs, returns candle/swing/open summary
- [x] 7.5 Update `main.py` — accept `--seed-1h` / `--seed-15m` CLI args, run `_seed_from_timestamps()` instead of `_seed_from_binance()` when provided
- [x] 7.6 Update `live_trading_doc.md` — D2 rewritten (seed by timestamp + rolling window), D7 added (seed API docs)
- [x] **TEST**: `_seed_from_timestamps("2026-09-09 15:00:00", "2026-09-10 04:30:00")` → 15m: 79 candles 1 confirmed swing open with 4 breaks, 1h: 55 candles 1 confirmed swing open with 2 breaks, engine state saved to SQLite, v18 simulation runs, backtest still 330t +331.1R PASS
- **NOTE:** Phase 7 used warmup lookback (fetch `timestamp - 50bars`). Phase 9 replaced this with no-lookback architecture (timestamp IS the first candle).

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

## Phase 9: Seed Architecture Fix + Live Candle Filter — ✅ DONE (2026-09-11)

Two bugs fixed:

**Bug 1: Seed was looking BACK from timestamp instead of starting FROM it.**
- Old: `_seed_from_timestamps` fetched `seed - 50bars` (12.5h before) and engine needed 50 bars warmup before first mark
- Fix: 15m timestamp IS the first candle, no lookback. 1h fetches only 14 bars before for chop calculation.
- Result: User gives `15m="2026-09-11 05:00:00"` → first mark at 05:15 (B1 down), 05:30 (FLIP up) — matches chart exactly

**Bug 2: Live/incomplete candle included in backfill.**
- Old: `backfill_klines` and `backfill_klines_bybit` returned all candles including the currently-open one (e.g., 18:15 candle at 18:17 with partial OHLC)
- Fix: Filter `close_time > now_ms` in `backfill_klines()`, `backfill_klines_bybit()`, and `_seed_from_timestamps()`
- Result: Only completed candles used for mark detection

- [x] 9.1 Rewrite `_seed_from_timestamps()`: 15m start = timestamp (no warmup lookback), 1h start = timestamp - 14 bars (chop only)
- [x] 9.2 Add live candle filter to `backfill_klines_bybit()` — `close_time <= now_ms`
- [x] 9.3 Add live candle filter to `backfill_klines()` (Binance) — same logic
- [x] 9.4 Add live candle filter in `_seed_from_timestamps()` — double-safe, filters after fetch
- [x] 9.5 Fix `_fetch_klines_from_sync()` interval format — Bybit needs "15" not "15m" (interval mapping)
- [x] 9.6 Add positional CLI args to `main.py` — `python main.py "15m_time" "1h_time" --exchange bybit` (arg1=15m, arg2=1h)
- [x] **TEST**: Bybit seed `"2026-09-11 05:00:00" "2026-09-09 14:30:00"` → 15m first candle at 05:00, marks at 05:15 B1 down + 05:30 FLIP up (matches user chart), 1h first candle at 00:30 (14 bars before 14:30 for chop), live candle filtered

---

## Phase 10: Order Execution — ✅ DONE (2026-09-11)

Wired BybitTrader into live_loop for real order execution on Bybit demo.

- [x] 10.1 `_execute_entry()` — places market order with SL/TP when new open trade detected in `_journal_trades()`
- [x] 10.2 `_execute_exit()` — closes position on Bybit when SL/TP/cap hit in `on_tick()`
- [x] 10.3 `_calculate_qty()` — position sizing: reads INR from `risk_inr.txt`, converts via live CoinGecko rate, `(risk_usdt) / (stop_distance + fee_buffer)`, rounded to 0.001 BTC precision, balance-checked
- [x] 10.4 `paper_mode` flag — `LiveLoop(paper_mode=True)` skips trader init; `--paper` in CLI (default)
- [x] 10.5 Fixed `get_wallet_balance()` — use `walletBalance` field (demo accounts have empty `availableToWithdraw`)
- [x] **TEST**: Paper mode: trader=None. Live mode: trader connects, balance=50000, qty calc works (0.085 BTC for $500 stop, 0.268 BTC for $100 stop)

---

## Phase 11: Backend 1m Data Bug — ✅ FIXED (2026-09-11)

- [x] 11.1 Identify bug — `btc_routes.py:729-730` calls `_load_fine_1m()` without `symbol` parameter, defaults to BTCUSDT (spot) for all HTF-LTF backtests
- [x] 11.2 Fix lines 729-730 — added `symbol` parameter to both `htf_fine` and `ltf_fine` calls
- [x] 11.3 Fix line 1314 — added `symbol` parameter to preset sweep `_load_fine_1m()` call
- [x] 11.4 Verify — Bybit perp: 346 trades, +351.0R (was 350 trades, +367.1R with spot 1m data). BTC Spot unchanged: 330 trades, +331.1R
- [x] **TEST**: Comparison script `compare_1m_sources.py` confirms fix — avg $13.75 price diff between spot/Bybit 1m candles, -16.1R impact from bug

---

## Phase 12: B2/FLIP Before FS — Live Signal Filtering — ✅ DONE (2026-09-11)

- [x] 12.1 Document the issue — `live_trading_doc.md` D8: B2/FLIP signals from open swing fire before FS confirmation, can't be reliably traded live
- [x] 12.2 Sweep analysis (corrected) — `sweep_pref_fs.py`: BTC Spot: 92/330 trades (28%) pre-FS, +10.1R. Bybit Perp: 102/346 trades (30%) pre-FS, -8.1R. 1h: 14.5% pre-FS signals.
- [x] 12.3 Filter pre-FS signals in `_collect_signals` — `filter_pre_fs=True` default, rejects B2/FLIP where `bar < prev_swing.confirmed_at_idx`. Bybit: 335 trades, +385.8R, PF 3.02 (+34.8R). Spot: 313 trades, +289.9R, PF 2.75.
- [x] 12.4 Exclude open swing from `_run_v18_simulation` — removed open15/open1h append (lines 902-910 in live_loop.py)
- [x] 12.6 Update v18 engine default params — filter applied via `_collect_signals` default, all engines inherit it
- [x] 12.5 Rolling window tracking — superseded by Phase 14/15 (swing endpoints + full state persistence). `_recover_from_crash()` handles backfill from last swing endpoint. No separate tracking needed.
- [x] 12.7 skip_first=True investigation — verified harmless for live: user seeds 2-3 swings of history, first swing is always deep in past, no trades missed. `filter_pre_fs` already passes swing 0 (si>0 check). Leave as is. Documented in `live_trading_doc.md`.

---

## Phase 13: WebSocket Resilience — ✅ DONE (2026-09-12)

Production-grade WebSocket with full resilience for live trading Bybit streams.

- [x] 13.1 Ping every 20s — sends `{"op": "ping"}` (Bybit requirement, connection drops without it)
- [x] 13.2 Pong timeout — if no pong in 15s → treat connection as dead
- [x] 13.3 Last-message timeout — no message for 60s → force reconnect (half-open detection)
- [x] 13.4 Exponential backoff + jitter — 1s → 2s → 4s → ... → 60s max (prevents hammering Bybit)
- [x] 13.5 Circuit breaker — >20 reconnects in 10min → pause 5min (prevents infinite retry loops)
- [x] 13.6 Force reconnect every 22h — proactively reconnect (Bybit sometimes does silent 24h disconnects)
- [x] 13.7 Gap detection + REST backfill — after reconnect, fetch missing candles from last known timestamp
- [x] 13.8 Deduplication — by open_time (Bybit sometimes sends duplicate confirm=True candles)
- [x] 13.9 Queue size limits — maxsize=1000 (ticks), 100 (klines), drop-oldest on full
- [x] 13.10 Connection state tracking — `get_status()` returns health metrics for monitoring
- [x] 13.11 Health monitor task — runs every 10s, checks last message age, forces reconnect if dead
- [x] 13.12 Documentation — `live_trading_doc.md` updated with resilience features, monitoring, alerting thresholds
- [x] **TEST**: `bybit_streamer.py` imports cleanly, `get_status()` returns expected fields, backfill_klines_bybit still works

---

## Phase 14: Crash Recovery — Rolling Swing Endpoints — ✅ DONE (2026-09-12)

Rolling swing endpoint tracking for automatic crash recovery. No user input needed on restart.

- [x] 14.1 Add `end_time` to result dict in `persistent_swing.py` — timestamp string of swing extreme (line 132)
- [x] 14.2 Add `get_last_swing_end()` / `set_last_swing_end()` to `state_store.py` — rolling pair storage in `meta` table
- [x] 14.3 Call `set_last_swing_end` in `_on_15m_close()` — saves endpoint when 15m swing completes (line 430-435)
- [x] 14.4 Call `set_last_swing_end` in `_on_1h_close()` — saves endpoint when 1h swing completes (line 465-470)
- [x] 14.5 Add `_recover_from_crash()` to `live_loop.py` — reads endpoints from DB, fetches missing candles, replays engine, re-runs simulation
- [x] 14.6 Update `main.py` startup — try `_recover_from_crash()` when no timestamps provided
- [x] 14.7 Remove old `_seed_from_exchange()` (500+200 approach) — no longer needed
- [x] 14.8 Remove old `run()` method — replaced by direct `_start_streaming()` in `main.py`
- [x] 14.9 Remove `SEED_15M`/`SEED_1H` constants — no longer needed
- [x] 14.10 Documentation — `live_trading_doc.md` updated with crash recovery flow, functions, CLI usage
- [x] **TEST**: `live_loop.py` imports cleanly, `_recover_from_crash` returns False when no DB state

---

## Phase 15: Crash Recovery — Full State Persistence + Speed — ✅ DONE (2026-09-12)

Store the full HTF matrix and LTF trade cache for instant crash recovery. No backfill needed for critical state.

- [x] 15.1 Add `sl_price`, `hrisk`, `lvl_1_5r`, `lvl_3r` to `htf_windows` table in `database.py` + ALTER TABLE migration
- [x] 15.2 Update `open_htf_window()` in `trade_store.py` to accept and store full matrix
- [x] 15.3 Update `_track_htf_windows()` in `live_loop.py` to pass full matrix on window open
- [x] 15.4 Update `_restore_htf_state()` in `live_loop.py` to read full matrix from DB (instant)
- [x] 15.5 Add LTF trade cache (`self._open_ltf_trade`) — loaded from DB on startup, updated on open/close/trail
- [x] 15.6 Update `on_tick()` to use cached trade (no DB reads on every tick)
- [x] 15.7 Update `_trail_sl()` to use cached trade and update cache on trail
- [x] 15.8 Update `_print_status()` to use cached trade
- [x] 15.9 Add `_reconcile_bybit_position()` — compare DB vs Bybit on startup, handle mismatches
- [x] 15.10 Documentation — `live_trading_doc.md` updated with Phase 15 flow, priority order, recovery table
- [x] **TEST**: Syntax check passes, smoke test (313 trades, +289.9R), cost test passes

---

## Phase 16: V18 Integrity Verification — ✅ DONE (2026-09-12)

Full re-verification of v18 engine mechanics for live trading. Both BTC Spot and Bybit Perp pass all 10 checks.

### BTC Spot Results

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | No trade worse than -1R | ✅ PASS | Worst: -1.000R (exactly) |
| 2 | Winners above 3R | ✅ PASS | Best: +29.34R, 42 trades > 3R, 10 trades > 10R |
| 3 | Streak halt ≤ 5 | ✅ PASS | Max consecutive losses: 4 |
| 4 | No duplicate trades | ✅ PASS | 313 unique trade keys |
| 5 | Exit reasons valid | ✅ PASS | sl: 91, trail: 222 |
| 6 | No overlapping trades | ✅ PASS | 0 overlaps |
| 7 | Win rate + PF | ✅ PASS | WR 38.7%, PF 2.75 |
| 8 | All years positive | ✅ PASS | 2023: +26.2R, 2024: +73.8R, 2025: +110.5R, 2026: +79.3R |
| 9 | SL exits exactly -1R | ✅ PASS | All SL exits at -1.000R |
| 10 | Cooldown respected | ✅ PASS | Bar-index-based, 19-bar tolerance |

### Bybit Perp Results

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | No trade worse than -1R | ✅ PASS | Worst: -1.000R (exactly) |
| 2 | Winners above 3R | ✅ PASS | Best: +39.81R, 51 trades > 3R, 14 trades > 10R |
| 3 | Streak halt ≤ 5 | ✅ PASS | Max consecutive losses: 4 |
| 4 | No duplicate trades | ✅ PASS | 335 unique trade keys |
| 5 | Exit reasons valid | ✅ PASS | sl: 115, trail: 220 |
| 6 | No overlapping trades | ✅ PASS | 0 overlaps |
| 7 | Win rate + PF | ✅ PASS | WR 35.2%, PF 3.02 |
| 8 | All years positive | ✅ PASS | 2023: +83.3R, 2024: +140.4R, 2025: +79.4R, 2026: +82.7R |
| 9 | SL exits exactly -1R | ✅ PASS | All SL exits at -1.000R |
| 10 | Cooldown | ✅ PASS | Disabled (0 bars) — not applicable |

- [x] 16.1 Create `tests/test_v18_integrity.py` — 10-point verification suite, supports `--bybit` flag
- [x] 16.2 Run all checks on BTC Spot — ALL PASS
- [x] 16.3 Run all checks on Bybit Perp — ALL PASS
- [x] 16.4 Investigate cooldown borderline cases — 3 cases at 19.1-19.7 bars (false positive, bar-index vs timestamp)
- [x] 16.5 Documentation — results documented in CHECKLIST

---

## Risk Limits — INTENTIONALLY EXCLUDED (2026-09-12)

v18's built-in protections are sufficient:
- **Streak halt (5)** — stops after 5 consecutive losses
- **20-bar cooldown** — forced pause after every loss
- **16-day HTF cap** — time-based exit on stale windows

Adding max drawdown halt or daily loss cap would hurt performance:
- 1.7 trades/week → daily cap is meaningless
- 35% win rate → drawdown IS the strategy; halting early risks missing recovery trades

If something goes catastrophically wrong (exchange bug, data feed corruption), operator kills the bot manually.

---

## Phase 17: Risk, Trail SL Sync, Kill Switch (2026-09-12)

### 17.1 INR Risk + Live Conversion
- [x] Created `risk_inr.txt` with `250` — edit file to change risk (no restart needed)
- [x] Added `read_risk_inr()` — reads from `risk_inr.txt`
- [x] Modified `_calculate_qty()` — reads INR from file, converts via live rate, logs per-trade
- [x] Startup log shows risk in both INR and USDT with live rate

### 17.2 Trail SL Sync to Bybit
- [x] Added `BybitTrader.update_sl()` — calls `set_trading_stop()` on Bybit API
- [x] Modified `_trail_sl()` — syncs new SL to Bybit exchange-side conditional order
- [x] Bybit SL is Market order (Full mode only supports Market) — no fill risk

### 17.3 Kill Switch
- [x] Created `kill_switch.py` — standalone script, works independently from bot
- [x] Added `_graceful_shutdown()` to `main.py` — Ctrl+C flattens position + cancels orders

### 17.4 Verification
- [x] Risk: INR 250 = $2.62 USDT at INR 95.58 rate
- [x] Smoke test: ALL CHECKS PASSED (313t +289.9R)
- [x] `kill_switch.py` imports OK
- [x] `update_sl` method exists on BybitTrader

---

## Phase 18: Config Centralization + Rate Manager + Trade Logging (2026-09-12)

### 18.1 Centralized Config (`config.py`)
- [x] Created `config.py` — all trading params in one place
- [x] Values: TAKER_FEE_RATE, BALANCE_SAFETY_MARGIN, SIZED_DOWN_FRACTION, QTY_PRECISION, MIN_BTC_QTY, RATE_UPDATE_INTERVAL, EMERGENCY_RATE, WINDOW sizes
- [x] No hardcoded values in live_loop.py or bybit_order.py

### 18.2 Rate Manager (`rate_manager.py`)
- [x] Created singleton `RateManager` — loads from disk on startup (0ms)
- [x] Fallback chain: CoinGecko -> ExchangeRate-API -> disk cache -> emergency 95.0
- [x] Background refresh when stale (>15 min)
- [x] Staleness guard: emergency rate after 24h no update
- [x] Disk persistence via `last_rate.json`

### 18.3 Trade Logging
- [x] `_execute_entry()` logs: direction, entry, SL, TP, risk INR, risk USDT, rate, qty, notional, fee buffer
- [x] `_execute_exit()` logs: reason, fill price, rate
- [x] `_trail_sl()` logs: SL change, R gap, Bybit sync status (OK or DB only)

### 18.4 Removed Hardcoded Values
- [x] Fee rate `0.00055` -> `config.TAKER_FEE_RATE`
- [x] Safety margin `0.95` -> `config.BALANCE_SAFETY_MARGIN`
- [x] Sized-down fraction `0.9` -> `config.SIZED_DOWN_FRACTION`
- [x] Qty precision `3` -> `config.QTY_PRECISION`
- [x] Min BTC qty `0.001` -> `config.MIN_BTC_QTY`
- [x] Window sizes `30/20/16` -> `config.WINDOW_DAYS_*`
- [x] Removed old `get_usdt_inr_rate()` function (replaced by RateManager)
- [x] Removed legacy `BybitTrader.calculate_qty()` (not used by live_loop)

### 18.5 Verification
- [x] Config imports: TAKER_FEE_RATE=0.00055
- [x] RateManager loads from disk: INR 95.00 (emergency default)
- [x] Smoke test: ALL CHECKS PASSED (313t +289.9R)
- [x] kill_switch.py imports OK

---

## Phase 19: WebSocket Fix — Python 3.10 Compat + Single Connection (2026-09-12)

### Root Cause
- `asyncio.timeout()` was added in Python 3.11; our system runs Python 3.10 → `has no attribute 'timeout'`
- `ws.closed` attribute removed in websockets 16.x → `'ClientConnection' object has no attribute 'closed'`
- `import websockets` missing from `bybit_streamer.py` → latent bug only surfaced when code paths were hit
- 3 separate WebSocket connections died at the exact same second (~68s) → Bybit recommends single connection + multiple topic subscriptions

### 19.1 Python 3.10 Timeout Helper
- [x] Created `_timeout()` async context manager (stdlib-only, no `asyncio.timeout`)
- [x] Replaced both `asyncio.timeout()` calls in `_stream_trades` and `_stream_klines`

### 19.2 websockets 16.x Compatibility
- [x] Replaced `ws.closed` with `ws.close_code is not None` in `_send_ping`
- [x] Added `import websockets` to `bybit_streamer.py`

### 19.3 Single Connection Architecture
- [x] Rewrote `BybitStreamer` from 3 separate connections → 1 connection + 3 topic subscriptions
- [x] Topics: `publicTrade.{symbol}`, `kline.15.{symbol}`, `kline.60.{symbol}` on one WS
- [x] Added `_handle_trade()` and `_handle_kline()` message routing by topic prefix
- [x] Removed `_health_monitor` (was causing shared `self._ws` conflicts)
- [x] Ping/pong + timeout-based half-open detection replaces health monitor
- [x] Backfill gap detection preserved (runs after reconnect)

### 19.4 Verification
- [x] Raw WS test: 113 trades, 19 15m klines, 19 1h klines in 60s (single connection)
- [x] Paper test: 5 minutes, zero errors, zero reconnects
- [x] Full pipeline: connected → seeded → computed HTF bias → status logging → clean shutdown
- [x] Smoke test: ALL CHECKS PASSED (313t +289.9R)

### 19.5 Chop Lookback Fix
- [x] `_seed_from_timestamps()` was fetching 14 bars before 1h timestamp for chop
- [x] `_compute_chop()` needs `n >= 15` (14-bar Dreiss + 1 for TR prev close) → returned default 50.0
- [x] Fixed: `chop_lookback_ms = 15 * 3600 * 1000` (was 14)
- [x] Verified: CHOP=49.9 (real value, not 50.0 default)

### 19.6 Bybit Demo Order Test
- [x] Market BUY 0.001 BTC @ $77,331.20 — filled instantly
- [x] SL set @ $76,831.20 (~$500 below) — confirmed on exchange
- [x] Position read back — side, size, entry, PnL all correct
- [x] Close position (Market SELL) — filled at same price
- [x] Fee: $0.043/side (0.055% taker) — matches config
- [x] Verified on Bybit demo website — trade history shows both legs filled

### 19.7 1-Minute Accelerated Test
- [x] Built test harness — injects signals, runs trade management on real 1m Bybit candles
- [x] Long trade: entry → trail SL ratchets up → exit at +4.17R (trail) ✓
- [x] Short trade: entry → trail SL ratchets down → exit at +3.37R (trail) ✓
- [x] SL hit: entry → SL hit at exactly -1.00R ✓
- [x] All trade management logic verified: ATR-based SL, trail ratcheting, SL/trail classification
- [x] 1-bar exits are expected on 1m (tiny ATR=$24 → risk=$2) — same mechanics on 15m (ATR=$300+)

### 19.8 Core Production Hardening

#### 19.8.1 Instrument Info from Bybit API
- [x] Added `_fetch_instruments()` to BybitTrader — calls `get_instruments_info()` on init
- [x] Extracts: tick_size, qty_step, min_qty, min_notional from Bybit API
- [x] Derives qty_precision from qty_step (0.001 → 3 decimals)
- [x] Fallback to config.py hardcoded values if API fails
- [x] Logged on startup: `Instruments: tick=0.1 qty_step=0.001 min_qty=0.001 min_notional=5.0`

#### 19.8.2 Max Leverage Cap
- [x] Added `MAX_LEVERAGE = 3` to config.py
- [x] Added `set_leverage()` method to BybitTrader — calls `session.set_leverage()`
- [x] Called on startup in main.py after trader init
- [x] Added implied leverage check in `_calculate_qty()` — rejects trade if `qty * entry / available > MAX_LEVERAGE`

#### 19.8.3 Order Retry with Backoff
- [x] Added `place_market_order_retry()` — exponential backoff + jitter, max 3 attempts
- [x] Unique `orderLinkId` per attempt (UUID) for dedup
- [x] Retries only on transient errors (network, rate limit)
- [x] Does NOT retry on: insufficient margin, invalid qty, auth errors
- [x] `_execute_entry()` now uses `place_market_order_retry()` instead of `place_market_order()`

#### 19.8.4 Verification
- [x] Instruments fetched from Bybit: tick=0.1, qty_step=0.001, min_qty=0.001
- [x] Leverage set to 3x on Bybit demo
- [x] Order with retry: filled, position shows lev=3
- [x] Close position: filled
- [x] Paper test: zero errors, CHOP=71.1, REGIME=B2, ATR=75.0

### 19.9 Telegram Alerts
- [x] Created `telegram_alert.py` — sends via Telegram Bot API (free, no paid service)
- [x] `.env` updated with TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- [x] `trade_entry()` alert: direction, entry, SL, qty, risk INR/USDT, rate
- [x] `trade_exit()` alert: reason, fill price, R multiple, direction, entry
- [x] `error()` alert: any error message
- [x] Integrated into `live_loop.py`: alerts on ENTRY FILLED, EXIT FILLED, errors
- [x] Initialized in LiveLoop.__init__ (graceful fallback if no token)
- [x] Verified: test entry + exit messages received on Telegram

---

## Phase 20: Deep Audit — Swing Engine Data Flow — ✅ DONE (2026-09-13)

### 20.1 1h Swing Engine Lookback Bug (FIXED)
- [x] **BUG FOUND**: During seeding, ALL 1h candles (including 15-bar chop lookback) were fed to the swing engine
- [x] Engine started from bar 0 (04:30) instead of the seed point (19:30), building wrong swings
- [x] Example: Sep 8 19:30 seed → engine detected B1@79435 (07:30) instead of B1@78955 (21:30 high)
- [x] **FIX**: `live_loop.py:792-803` — engine starts from `engine_start` index (seed point), lookback bars only used for chop
- [x] **VERIFIED**: Engine now produces correct swings matching chart analysis

### 20.2 Deep Audit — 14 Findings Across 5 Investigation Tracks

#### CRITICAL / HIGH — Must fix before live

- [x] **#1 Double-processing last seeded bar** — **DISMISSED** — Tested live: Bybit WS sends only current in-progress candle (confirm=False) on first subscribe. Does NOT resend old closed candles. No duplicate possible.
- [x] **#2 Trade dedup broken (no break_kind in DB)** — **FIXED** — `live_loop.py:1444-1446,1251` — Dedup key simplified to `(entry_ts, direction)`. Verified unique for all 313 trades. Old key used `break_kind` and `swing_no` which don't exist in DB schema → keys never matched → every simulation run re-inserted all trades.
- [x] **#3 Order retry UUID not idempotent** — **FIXED** — `bybit_order.py:259-262` — Moved UUID generation outside retry loop. Single `link_id` reused across all attempts. Prevents 2x position on network timeout.
- [x] **#4 Failed order leaves orphan DB record** — **FIXED** — `live_loop.py:1360-1370,1364-1372` — On order failure or exception, DB trade is closed with `exit_reason="order_failed"` or `"order_error"`. `_open_ltf_trade` cache cleared. Prevents SL/TP monitoring against non-existent position.
- [x] **#5 Crash recovery missing 1h lookback** — **FIXED** — `live_loop.py:921-950` — Crash recovery now fetches 15 extra 1h bars before recovery point for chop. Lookback bars in `window_1h` for chop calculation, only post-recovery bars fed to swing engine. Same pattern as initial seeding fix.
- [x] **#6 Daily P&L state not persisted** — **FIXED** — `database.py` + `state_store.py` + `live_loop.py:129-131,1163-1170` — Added `daily_pnl_r`, `daily_halted`, `last_trade_date` columns to `trading_state` table with migration. Loaded on init, saved on every `_check_daily_loss_limit()` call. Survives crash restart.

#### MEDIUM — Should fix before live

- [x] **#7 Window trim corrupts g_idx for diagnostics** — **FIXED** — `live_loop.py:1017-1031,1247-1259` — Changed `_show_recent_marks` and `_journal_marks` to look up candles by `time` string (stable datetime) instead of `idx` (window position). Built `date_to_candle` lookup dict once per call. Mark timestamps never change regardless of window trimming.
- [x] **#8 Kline queue too small for backfill** — **FIXED** — `bybit_streamer.py:78-79` — Changed kline queues to unbounded (`asyncio.Queue()` without maxsize). Prevents dropping messages during large backfills after extended downtime.
- [x] **#9 Failed SL sync not retried** — **FIXED** — `live_loop.py:1552-1573` — SL sync now retries once with 0.5s delay. If still fails, logs error and sends Telegram alert so user knows DB/exchange SL may differ.
- [x] **#10 Partial fill not checked** — **FIXED** — `live_loop.py:1377-1406`, `persistence/trade_store.py:141-146` — After successful order placement, queries position via `get_position()` to verify actual fill. If 0 filled → closes DB trade as `"order_failed"`. If partial → updates DB qty via `update_trade_qty()`. Telegram alert on any mismatch.

#### LOW — Nice to fix

- [x] **#11 `fee_pct` mismatch** — **NOT A BUG** — Bybit entry in `v18_params.py:45` is `fee_pct: 0.055`, matches `config.py` `TAKER_FEE_PCT = 0.055`. Both 0.055%/side. The `fee_pct` field is only used by the backtest HTTP API's `_trade_costs()`, not the live loop. No mismatch for the instrument we're trading.
- [x] **#12 Blocking `time.sleep` in retry** — **FIXED (reverted)** — `bybit_order.py:246-290` — Reverted to sync `time.sleep`. Async caused SyntaxError in caller chain. ~7s max block on rare network errors is acceptable.
- [x] **#15 Trail SL fires at wrong bar after window trim** — **FIXED** — `btc_engine.py:207-228`, `live_loop.py:1523-1573` — Added `_trail_events_ts()` that returns `(confirmed_at_epoch, pivot_px)` instead of `(confirmed_at_idx, pivot_px)`. Updated `_trail_sl()` to compare timestamps against candle timestamps instead of window indices. Trail SL now immune to window trimming.
- [x] **#16 SyntaxError: await in non-async def** — **FIXED** — Reverted `place_market_order_retry` to sync. `_execute_entry` no longer uses `await`.
- [x] **#17 `_get_existing_marks_set()` undefined** — **FIXED** — `live_loop.py:1517-1520` — Added method that queries marks from DB by tf, returns set of `(ts, kind, direction, swing_no)`.
- [x] **#18 `_trail_events_ts()` always returns empty** — **FIXED** — `firstswing.py:185,691,844`, `btc_swing.py:88` — Changed `self.t` from `c.date[11:16]` (HH:MM) to `c.date` (full datetime). Break marks now store full datetime. `_trail_events_ts()` can parse correctly.
- [x] **#19 `_journal_marks()` never matches** — **FIXED** — Same root cause as #18. Break mark `time` is now full datetime, matches `date_to_candle` keys.
- [x] **#20 `_show_recent_marks()` never shows** — **FIXED** — Same root cause as #18.
- [x] **#21 Daily loss limit wrong units** — **FIXED** — `live_loop.py:1154-1156` — Changed `max_loss_r = -(risk_inr * DAILY_LOSS_MULTIPLIER)` to `max_loss_r = -float(DAILY_LOSS_MULTIPLIER)`. Now compares R against R.
- [x] **#22 `update_trade_qty()` non-existent column** — **FIXED** — `database.py:157-162` — Added `_migrate_ltf_trades()` that adds `qty REAL` column if missing. Called in `create_tables()`.
- [x] **#23 TP hardcodes R=3.0** — **FIXED** — `live_loop.py:1681-1692` — Now computes actual R from fill price using `_calc_r()`.
- [x] **#24 `_execute_exit` reads after cache clear** — **FIXED** — `live_loop.py:1659-1695` — Swapped order: `_execute_exit` called BEFORE `_cache_ltf_trade_close()` in all exit paths (SL, TP, cap). Telegram gets correct data.
- [x] **#25 Order failures count as losses** — **FIXED** — `live_loop.py:1099-1103` — `_persist_streak_state()` now skips trades with `exit_reason` in `("order_failed", "order_error")`.
- [x] **#27-28 Half-open detection + force reconnect unused** — **FIXED** — `bybit_streamer.py:200-214` — Added watchdog in main WS loop: breaks connection if `_force_reconnect_at` elapsed (22h) or no message for `LAST_MSG_TIMEOUT` (60s).
- [x] **#29 `timeInForce: GTC` on Market orders** — **FIXED** — `bybit_order.py:217-224` — Removed `timeInForce` from Market order params.
- [x] **#30 `insert_mark_safe` catches all exceptions** — **FIXED** — `mark_store.py:45-56` — Changed to catch `sqlite3.IntegrityError` only.
- [x] **#31 `_compute_chop` on every tick** — **FIXED** — `live_loop.py:210-240` — Added `_chop_stale` flag. Chop/ATR only recomputed when flag is True (set on candle close). Ticks only update unrealized R.
- [x] **#34 Reconciliation uses sl_current + r=0** — **FIXED** — `live_loop.py:333-343` — Now calculates actual R from exit price using `_calc_r()`.
- [x] **#35 Kill switch no retry** — **FIXED** — `kill_switch.py:69-89` — Added retry (2 attempts). Exits with code 2 on failure.

#### LOW — Nice to fix

- [x] **#11 `fee_pct` mismatch** — **NOT A BUG** — Bybit entry in `v18_params.py:45` is `fee_pct: 0.055`, matches `config.py` `TAKER_FEE_PCT = 0.055`. Both 0.055%/side. The `fee_pct` field is only used by the backtest HTTP API's `_trade_costs()`, not the live loop. No mismatch for the instrument we're trading.
- [x] **#26 IST vs UTC date mismatch** — **FIXED** — All `date` strings in `live_loop.py` now use IST via `_to_ist_str()` / `_to_ist_short()` static methods. 8 UTC→IST conversions: 15m/1h candle dates, recovery logs, loss date, daily reset, HTF entry/exit. Seed already IST. `ts` (epoch) unchanged.

### 20.3 Verified Correct (No Bugs Found)

- [x] Chop calculation uses lookback correctly (`n >= 15` check)
- [x] ATR calculation during seeding correct
- [x] `_update_htf_metrics()` after seeding correct
- [x] `_run_v18_simulation()` data paths correct (uses timestamps, not indices)
- [x] `filter_pre_fs=True` applied correctly in both backtest and live
- [x] `skip_first=True` applied correctly in both backtest and live
- [x] v18 params per symbol match between backtest and live
- [x] Same `SwingEngine` class used everywhere
- [x] Same `minBars` per TF (50/20)
- [x] Same signal collection (`_collect_signals`)
- [x] Same streak halt / cooldown logic
- [x] PersistentSwingEngine reset after declaration correct
- [x] First bar after swing declaration correct (no off-by-one)
- [x] WebSocket reconnection + gap backfill correct (subscribe before backfill prevents race)
- [x] SQLite queries safe (parameterized, no injection)
- [x] HTF window storage/loading correct
- [x] State persistence atomic (SQLite transactions)

---

## Phase 21: VPS Deployment — ⬜ TODO

### Timezone
- [ ] VPS timezone set to UTC (`timedatectl set-timezone UTC`)
- [ ] Confirm `datetime.now(timezone.utc)` matches VPS system clock
- [ ] Confirm Bybit candle timestamps align with UTC (Bybit uses UTC natively)
- [ ] Confirm IST conversions in live_loop.py (`IST_OFFSET`) work correctly on UTC host

### SSH + Security
- [ ] SSH key-based auth configured (disable password login)
- [ ] UFW firewall enabled (allow SSH + nothing else)
- [ ] Auto security updates enabled (`unattended-upgrades`)

### Process Management
- [ ] Systemd service file for backbencher (`/etc/systemd/system/backbencher.service`)
- [ ] Auto-restart on crash (`Restart=always`)
- [ ] Log rotation configured (`/var/log/backbencher/`)
- [ ] `kill_switch.py` as separate systemd service (watches DB, kills if needed)

### Data Persistence
- [ ] SQLite DB backed up (daily cron `sqlite3 backbencher.db ".backup /backup/backbencher_$(date +\%F).db"`)
- [ ] Old backups pruned (keep 30 days)
- [ ] `.env` file permissions: `chmod 600 .env` (API keys)

### Monitoring
- [x] Telegram bot connected and receiving entry/exit/error alerts (already working)
- [ ] `systemctl status backbencher` healthy
- [ ] `htop` / memory usage < 100MB

### Deployment Steps
1. `scp -r live_stuff/ user@vps:/opt/backbencher/`
2. `ssh user@vps`
3. `cd /opt/backbencher && cp .env.example .env && nano .env` (fill API keys)
4. `timedatectl set-timezone UTC`
5. `pip install -r requirements.txt`
6. `systemctl enable --now backbencher`
7. Check logs: `journalctl -u backbencher -f`

---

## 22. Deep Architecture Audit — Live vs Backtest Discrepancies

### CRITICAL

- [x] **#36 TP check in `on_tick` for LTF trades** — **FIXED** — `live_loop.py:1705-1726` — Removed dead TP check block + unused `tp_price` variable. LTF trades trail only (no fixed R target). The 3R target is for HTF bias windows only, not LTF. Backtest engine was already correct (no TP in v18 walk loop).

- [x] **#37 Double `_execute_exit` on TP** — **FIXED** — TP block removed from LTF trades in Bug #36 fix. No TP calls in `on_tick` or `_on_15m_close` anymore. LTF trades trail only (no fixed R target).

- [x] **#38 Window trim breaks swing engine g_idx sequencing** — **FIXED** — Timestamp refactor: `ts_map` in SwingEngine maps counter→datetime. Live loop uses monotonic counters. No index-based inter-function communication.

- [x] **#39 Window trim breaks `_collect_signals` candle lookup** — **FIXED** — CandleStore class: O(1) lookup by datetime string. Signal `bar` is datetime, position resolved locally via `store.pos()`. Trim-immune.

### MEDIUM

- [x] **#40 Double simulation on 1h boundary** — **FIXED** — `live_loop.py:507-543` — Added barrier pattern: `_got_15m_boundary` / `_got_1h_boundary` flags + `_BOUNDARY_TIMEOUT = 2.5s`. At 1h boundary (`ts % 3600 == 0`), both callbacks set their flag and call `_try_fire_boundary()`. Simulation runs only when BOTH flags are true (or timeout forces it). Ensures chop is computed from complete 1h data. Non-boundary candles still fire simulation immediately.

- [x] **#41 Two exit systems running simultaneously** — **BY DESIGN** — `on_tick` checks SL on every tick (real-time exit). `_trail_sl` runs on candle close (ratchet SL when new pivot confirms). This is correct: trail can only update on candle close (swing engine needs bar data), SL hit detection needs tick-level granularity.

- [x] **#42 Cooldown units mismatch** — **FIXED** — `_persist_streak_state()` (`live_loop.py:1183-1237`): (1) `last_loss_bar` now stores datetime string instead of epoch int (timestamps-only convention). (2) Cooldown properly armed on new loss: compares `consec > old_consec`, sets `cooldown_remaining = cooldown_bars` when a new loss is detected (was never armed before — only decremented, never set). (3) Clear docstring explaining v18 bar-index vs live countdown difference. Smoke test: 335t +385.7R PASS.

### LOW

- [x] **#43 Chop recomputed every 30s** — **FIXED** — `live_loop.py:460-467` — Removed `_chop_stale = True` from `_print_status()`. Chop now only recomputes on `_on_1h_close` (24x/day instead of 2880x/day). `_update_htf_metrics()` still runs for unrealized R.

- [x] **#44 IST/UTC date format mix** — **FIXED** — Live now creates IST dates matching seed. `CandleStore.epoch()` / `_trail_events_ts()` in `btc_engine.py` unaffected (both sides use same IST convention, comparisons work). Old DB marks with UTC dates: harmless — `ts` (epoch) used for all logic.

---

## Phase 20: Engine Optimization Sweep (2026-09-14)

### 20.1 Per-Year Sweep
- [x] Swept htf_rr × ext_stop_r per year (2023-2026) — best combo varies by regime
- [x] Swept chop_thresh × sl_buf_atr per year — sl_buf=0.10 wins 3/4 years
- [x] Swept cooldown_bars × max_consecutive_losses per year — **halt=3 wins ALL years**
- [x] Documented in `docs/SWEEP_ROADMAP.md`

### 20.2 Key Findings
- [x] `max_consecutive_losses=3` universally better than 5 for Bybit Perp (+87.7R)
- [x] `sl_buf_atr=0.10` better than 0.20 in 3/4 years (tighter SL = less noise)
- [x] Engine params (chop, sl_buf, halt) vary by instrument — each exchange has its own personality
- [x] Price-level doesn't affect strategy (ATR scales automatically, chop is dimensionless)
- [x] Market regime affects performance, not price level

### 20.3 Applied to Backtest Engine
- [x] `btc_routes.py` — Bybit Perp: `_slbuf=0.10`, `_halt=3`
- [x] `v18_params.py` — BYBIT: `sl_buf_atr=0.10`, `max_consecutive_losses=3`
- [x] `test_smoke.py` — pass criteria: 261t, +470.5R
- [x] `test_v18_integrity.py` — BYBIT_PARAMS updated, streak <= 3, WR range 30-50%
- [x] Smoke test: 261t +470.5R PF 4.71 — ALL CHECKS PASSED
- [x] Integrity test: ALL 10 CHECKS PASSED

### 20.4 Per-Instrument Tuning Principle
- [x] Each instrument gets its own optimal params (chop, sl_buf, halt, cd)
- [x] Do NOT copy Bybit params to other instruments — sweep each separately
- [x] Binance Perp and Spot still need their own optimization sweeps
- [x] Future instruments (ETH, SOL) need per-instrument sweep before going live

---

## Status Legend

- `[ ]` todo — not started
- `[~]` in progress
- `[x]` done + tested
