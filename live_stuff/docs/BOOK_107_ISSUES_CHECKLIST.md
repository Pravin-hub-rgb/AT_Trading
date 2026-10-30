# Book 107 Issues Checklist (Incremental Sim / Live Engine)

**Path:** `live_stuff/docs/BOOK_107_ISSUES_CHECKLIST.md`  
**Purpose:** Single source of truth for all known issues, inconsistencies, and gaps found during review of the Book 107 live engine and its sim parity. Work from this list; do not rely on memory.  
**Status:** Open items marked `[ ]`. When resolved, mark `[x]` and add a short note + commit reference. Do not delete items.

---

## How to use this list

- Each item has a **severity** (`Critical` / `High` / `Medium` / `Low`) and a **category**.
- If resolved, change `[ ]` to `[x]` and append: `Resolved: <summary> (commit abc123)`.
- If something turns out to be a non-issue: `[x] Not an issue: <reason>`.

---

## Critical live vs backtest correctness (will cause real divergence)

### [ ] C1 Timestamp convention mismatch
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical  
**Summary:** `loop.py` / `feed.py` stamp live candles with `ts = close_time` (≈ next bar's open), while `date` is the open time. Backtest data has `ts` = bar open time. The oracle hard-codes `ts + 3600` for HTF close, `+900` for LTF close, and a 2700s window floor all assuming open time.  
**Impact:** Shifts window admission and exit by ~45 minutes in live; delays which HTF bar's chop/ATR an LTF bar sees. No parity test exercises live timestamps.  
**Experiment needed:** Run oracle on live-style candles vs same candles with open-time `ts`; diff trades.  
**Refs:** `live/loop.py`, `live/feed.py`, `_vendored/unified.py`

### [ ] C2 Trailing differs between live and sim
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical  
**Summary:** Live `_trail_trade_sl` ratchets only if `new_sl < pivot < bar low`. Sim's LTF walk ratchets to pivot unconditionally then tests `lo <= sl_cur` on the same bar. Live exits use tick price vs `sl_current`; sim uses bar OHLC.  
**Impact:** A trade that should exit in one may not in the other.  
**Refs:** `live/signals.py` (`_trail_trade_sl`), `_vendored/unified.py` (LTF walk), `live/execution.py` (tick path)

### [ ] C3 Live has a time exit the sim lacks
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical  
**Summary:** Live closes at market when `ts >= cap_ts` (16 days) with reason `cap`. The LTF sim has no such exit. A long-lived trade can end differently.  
**Refs:** `live/signals.py` (on_tick), `_vendored/unified.py`

### [ ] C4 No take-profit order in live
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical  
**Summary:** `on_tick` checks only stop/trail and time cap. `execution.py` has no take-profit order. `tp_price` is only a label. Problem statement §2.4 (TP exit → "target") is wrong for live.  
**Impact:** TP exits never fire live; trades run to SL or time cap instead.  
**Refs:** `live/signals.py` (on_tick), `live/execution.py`

### [ ] C5 Non-causal cooldown in oracle
**Category:** Correctness / Logic  
**Severity:** Critical  
**Summary:** The oracle looks forward: an earlier-booked trade that later loses can block entries made during its life (cooldown set at `exit_idx`, applied backwards). A bar-by-bar / streaming engine cannot do this cooldown would have to be "after a realized loss" going forward.  
**Impact:** Redefining cooldown moves pinned results (+508R pin). Need to decide rule up front and re-pin.  
**Refs:** `_vendored/unified.py` lines ~1486, ~1857 (`if cooldown_bars > 0 and r_multiple < 0`)

## High retention / trim correctness (90-day slice dependence)

### [ ] H1 Start-point dependence
**Category:** Retention / Trim  
**Severity:** High  
**Summary:** Three things inside the sim are running totals over history, not windowed:
- Regime hysteresis counter (`exp_persist=7`) starts from first signal in slice.
- v7 `busy_until` chain depends on trades before slice.
- Cooldown and `last_loss_bar` set by earlier trades.  
**Impact:** Trimming at different points gives different entries near old edge. Tests only check one 14-day trim on one window; production keeps 90 days.  
**Refs:** `live/retention.py`, `_vendored/unified.py`, `config.py` (`exp_persist`)

### [ ] H2 Indicator warmup after trim
**Category:** Retention / Trim  
**Severity:** High  
**Summary:** ATR(14)%, chop, and regime router need lookback. First N bars of trimmed window have different values than full history; these gate trades.  
**Impact:** Entries near trim boundary can change.  
**Refs:** `live/regime.py` (`RollingATR`), `_vendored/unified.py`

### [ ] H3 Time-cap vs window-length boundary
**Category:** Retention / Trim  
**Severity:** High  
**Summary:** 15m window is 30 days; `cap_days` is 30. A trade opened near the oldest edge can hit its cap exactly at the boundary. 1h window is 20 days with 16-day HTF cap.  
**Impact:** HTF trade whose entry precedes cutoff needs its `busy_until` and trailing state preserved, not re-derived.  
**Refs:** `_vendored/v7_timecap.py` (`cap_days`), `config.py`

### [ ] H4 Swing chain must never be re-derived from trimmed candles
**Category:** Retention / Trim  
**Severity:** High  
**Summary:** Swing engine can't cold-start mid-chain (path-dependent). Retention only safe if chain is never re-derived from trimmed candles. After crash, "rebuild from last completed swing" has same weakness.  
**Refs:** `live/retention.py`, `live/loop.py` (`PersistentSwingEngine`), §8 of theory doc

### [ ] H5 filter_pre_fs looks at previous swing
**Category:** Retention / Trim  
**Severity:** High  
**Summary:** Trim must never drop the swing before the oldest one still in use.  
**Refs:** `_vendored/btc_engine.py` (`_collect_signals`), `live/retention.py`

### [ ] H6 Forming swing's start can shift when it flips
**Category:** Retention / Trim  
**Severity:** Medium  
**Summary:** `_flip()` re-anchors `start_idx`/`start_px` mid-swing. `_collect_signals` computes a mark's SL from swing's current start, so an earlier mark's SL can change after a later flip. New engine should freeze a mark's SL at the bar it fires.  
**Impact:** Short-side mark entries affected (not FS-long ones).  
**Refs:** `live/feed.py` (`_flip`), `_vendored/btc_engine.py` (`_collect_signals`)


## Medium IncrementalSim / architecture

### [ ] M1 IncrementalSim is a gate, not an engine
**Category:** Architecture  
**Severity:** Medium  
**Summary:** Any change in structural signature triggers full batch run. Non-structural bar resumes via `run_ltf_walk(state=…)` which advances open trades but never walks new signals; trail events frozen at entry. Only handles pending last-bar signal case.  
**Impact:** Neither path reproduces cooldown retro-removal when open trade later closes as loser.  
**Refs:** `live/incremental.py` (`IncrementalSim.on_bar`), `live/ltf_walk.py`

---

## Medium Testing gaps

### [ ] T1 No prefix stability test
**Category:** Testing  
**Severity:** Medium  
**Summary:** Need to compare `run(prefix_n)` entries at bar n−1 with `run(full)` entries at that bar, count differences. End-of-history batch list ≠ live list because final list retroactively adds/removes entries.  
**Refs:** `live/parity.py`, `_vendored/unified.py`

### [ ] T2 No timestamp shift test
**Category:** Testing  
**Severity:** Medium  
**Summary:** No parity test exercises live timestamps (close_time vs open time).  
**Refs:** `tests/test_real_data_parity.py`, `_vendored/unified.py`

### [ ] T3 test_incremental_parity is tautological
**Category:** Testing  
**Severity:** Medium  
**Summary:** Calls `on_bar(force=True)` once → runs same batch function. Idempotency check is real but parity is trivial.  
**Refs:** `tests/test_incremental_parity.py`

### [ ] T4 test_retention_parity weak
**Category:** Testing  
**Severity:** Medium  
**Summary:** Uses uniform-random candles, 5-day trims, filters trades before cutoff. Mid-swing test only asserts `start_idx >= 0`, not trade equality. Real-data test is one 2000-bar (~21 day) window trimmed to 14 days; production keeps 90.  
**Refs:** `tests/test_retention_parity.py`, `tests/test_real_data_parity.py`

### [ ] T5 Missing test coverage
**Category:** Testing  
**Severity:** Medium  
**Summary:** Nothing tests: prefix stability, unlimited concurrency with cooldown, hysteresis warm-up, live timestamps, differential full-vs-retained with randomized cutoffs/restarts.  
**Refs:** `tests/`

---

## Medium Inconsistencies between docs / config

### [ ] I1 Cooldown trigger inconsistent
**Category:** Docs / Config  
**Severity:** Medium  
**Summary:** Problem statement says cooldown follows a *losing* trade. Theory doc says *any* trade close including gray legs. Code (line 1857) says `if cooldown_bars > 0 and r_multiple < 0` → losing trade only. Decide and document one rule.  
**Refs:** `docs/PROBLEM_STATEMENT_FOR_REVIEW.md`, `docs/working theory of 107.md`, `_vendored/unified.py` line 1857

### [ ] I2 Age rule missing from problem statement
**Category:** Docs  
**Severity:** Medium  
**Summary:** Theory doc has "signal can't be more than 2 bars old" gate; missing from problem statement's gate list.  
**Refs:** `docs/working theory of 107.md`, `docs/PROBLEM_STATEMENT_FOR_REVIEW.md`

### [ ] I3 Position cap mismatch
**Category:** Config  
**Severity:** Medium  
**Summary:** Sim has `max_positions=0` (unlimited). Live config has `LIVE_MAX_LEGS = 10`. If cap binds, live diverges from sim.  
**Refs:** `config.py` (`LIVE_MAX_LEGS`), `book.py` / `BOOK_PARAMS` (`max_positions`)

### [ ] I4 525 vs 526 trade gap unexplained
**Category:** Data / Parity  
**Severity:** Medium  
**Summary:** Pinned backtest is 525 trades; live basis is 526. One-trade difference should be explained, not accepted.  
**Refs:** `docs/working theory of 107.md`, `docs/PROBLEM_STATEMENT_FOR_REVIEW.md`

### [ ] I5 16-day HTF window cap only in theory doc
**Category:** Docs / Config  
**Severity:** Medium  
**Summary:** 16-day HTF window cap appears only in theory doc but affects retention math (H3).  
**Refs:** `docs/working theory of 107.md`, `live/retention.py`

---

## Low Oracle / pinned data

### [ ] L1 Oracle is unpinned
**Category:** Data / Parity  
**Severity:** Low  
**Summary:** `unified.py` hands off to `live/ltf_walk.py`; three mismatching hashes remain unexplained.  
**Refs:** `_vendored/unified.py`, `live/ltf_walk.py`


## P1 — Performance / datastructure (from .kilo rolling-window plan)

### [ ] P1.1 —" Full re-simulation from seed on every 15m close (datastructure / walker recreation)
**Category:** Performance / Datastructure  
**Severity:** High (blocks live entry timing)  
**Summary:** Each 15m candle close re-runs `_run_v18_simulation` over the entire stored history from the seed bar: re-creates the swing/walker chain, re-computes pivots, re-walks all candles. Cost grows with history: ~0.07s at 30d, 1.20s at 1yr, **~5.0s at 3.8yr (129,715 candles)**. The whole thing blocks the event loop on every 15m close, so a live entry can be delayed by seconds —" unacceptable for taking entries. Data also keeps piling up unbounded in `all_candles_*`.  
**Impact:** Entry latency up to ~5s on production history; event-loop stall; unbounded memory growth.  
**Refs:** `live/loop.py` (`_on_15m_close`/`_on_1h_close`), `live/signals.py` (`_run_v18_simulation`), `live/feed.py`, `_vendored/unified.py` (`simulate_htf_ltf_streak_halt`), `live/incremental.py` (Step C pending)  
**Plan:** Offload `_run_v18_simulation` to `asyncio.to_thread` (immediate), then incremental O(1) driver (Step C/E of `INCREMENTAL_REFACTOR_PLAN.md`) so only the new bar is processed.

### [ ] P1.2 —" Rolling-window data loss (trim drops marks outside 30d window)
**Category:** Correctness / Retention  
**Severity:** High  
**Summary:** `_rebase_swings_to_window` drops break marks outside the 30d window; `_collect_signals` skips breaks whose candles aren't in the trimmed store; SL slice `candles[_sw_idx:_hi_i]` clamps to wrong indices. Fix: store all candles from seed-to-now in DB, pass full candles + full swings to sim, no trim/rebase.  
**Refs:** `live/feed.py:559` (`_rebase_swings_to_window`), `_vendored/btc_engine.py:260-310`, `live/loop.py`, `live/signals.py`  
**Plan:** rolling-window-data-loss plan steps 1-11 (`.kilo/plans/1792658668907-rolling-window-data-loss-plan.md`).

### [ ] P1.3 —" Incremental sim Step C/E pending (O(1) driver + cutover)
**Category:** Architecture  
**Severity:** Medium  
**Summary:** `IncrementalSim.on_bar` only advances open trades; never walks new signals; trail events frozen at entry; signature gate skips via structural hash. True O(1) rewrite + cutover pending parity history (Step D done).  
**Refs:** `live/incremental.py`, `live/ltf_walk.py`, `live/parity.py`, `docs/INCREMENTAL_REFACTOR_PLAN.md`

### [x] P0a —" 1h lookback bars contaminated `all_candles_1h` (resolved)
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical (was)  
**Summary:** 14 pre-seed 1h bars went into `all_candles_1h` while swing indexing started at the seed bar, misaligning HTF indices.  
**Resolved:** per `.kilo/plans/1792658668907-live-sync-fix-plan.md` (P0a) —" lookback bars kept transient, `all_candles_1h` built from seed bar onward.

### [x] P0b —" Seeding trips the daily-loss halt (resolved)
**Category:** Correctness / Logic  
**Severity:** Critical (was)  
**Summary:** `_journal_trades` replayed all historical closed trades during seeding, accumulating daily loss into `_daily_pnl_r` and tripping the 5R halt.  
**Resolved:** per `.kilo/plans/1792658668907-live-sync-fix-plan.md` (P0b) —" seeded history excluded from daily P&L, tagged `seed_history`.

### [x] P0c —" No candle dedupe/gap integrity (resolved)
**Category:** Correctness / Live-vs-backtest  
**Severity:** Critical (was)  
**Summary:** `_on_15m_close`/`_on_1h_close` appended candles unconditionally; reconnect backfill/restart could duplicate or stale candles, corrupting swing indices.  
**Resolved:** per `.kilo/plans/1792658668907-live-sync-fix-plan.md` (P0c) —" dedupe/gap handling added.

---

## Suggested work order

0. **Tackle P1.1 first** —" offload/full-rebuild datastructure issue: full re-sim from seed on every 15m close (~5s at 3yr) blocks entry timing. Offload to `asyncio.to_thread`, then incremental O(1) driver.
1. **Run the two experiments first** (prefix stability + timestamp shift) to quantify actual divergence.
2. **Decide cooldown rule** (losing trade only vs any close) and **timestamp convention** (open time) these are spec decisions that block everything else.
3. **Add differential retention test** (full-history vs retained, randomized cutoffs/restarts) locks in trim correctness without a rewrite.
4. **Fix timestamp convention** in live feed/loop to match oracle (open time) one-line change, high impact.
5. **Decide on rewrite vs checkpointing** (see PROBLEM_STATEMENT_FOR_REVIEW.md Q5: probably not needed for speed; only if correctness demands it).

---

## Related docs

- `INCREMENTAL_REFACTOR_PLAN.md` original refactor plan (P1b done, C–E pending)
- `PROBLEM_STATEMENT_FOR_REVIEW.md` full problem statement sent to external reviewer
- `working theory of 107.md` Book 107 strategy theory (source of several inconsistencies above)

