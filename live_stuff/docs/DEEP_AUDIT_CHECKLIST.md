# Deep Audit Checklist — Live Engine Fixes (Post-Backtest)

Use this checklist when building the live bot. Each item has severity, location, and fix.

---

## CRITICAL — Fix Before Going Live

### 1. SWING ENGINE MISMATCH: backtester vs live use DIFFERENT engines — **FIXED (2026-09-23)**
- **Backtester:** `compute_btc_swings` (btc_swing.py) — 87 swings on 40-day 15m slice
- **Live engine:** `PersistentSwingEngine` (persistent_swing.py) — WAS 69 swings (20% fewer)
- **Root cause:** After a swing declared, backtest starts the next engine at `end_idx+1` and RE-FEEDS every bar through the declaration bar; live jumped to `declaration_bar+1` and skipped that range. First divergence at swing 2 (56 bars skipped).
- **Fix applied:** `persistent_swing.py` now buffers candles and replays `end_idx+1..current` through the new engine (same stitch as `compute_btc_swings`). Also forces `timeCap="00:00"` when not given (C11). Extra swings queued and drained one-per-`process_bar` call.
- **Verified:** `exp_swing_parity_diag.py` — 15m 40d slice **87/87 PERFECT**, 1h 120d **118/118 PERFECT**. Identity gate green (340t/+225.3R).
- **Note:** `replay_harness.py` still fails (0/29) — that is Issue #10 (30d rolling window builds different chains than full-history), NOT this engine bug. Engine parity is closed.
- **Priority:** CLOSED for engine; Issue #10 remains for live windowing.

### 2. No position recheck after reconnect
- **File:** `live_loop.py:194-227` (`_session_watch`)
- **Issue:** After reconnecting HTTP session, the bot does NOT re-query the Bybit position. If exchange-side SL fired while offline, bot thinks position is still open.
- **Fix:** After successful `_reconnect()`, call `_reconcile_bybit_position()`.

### 3. SL sync failure leaves exchange SL stale
- **File:** `live_loop.py:2106-2125`
- **Issue:** If all 5 SL sync retries fail, exchange SL stays at old (wider) level. Flash crash can blow through DB's intended SL.
- **Fix:** After SL sync failure, Telegram alert + exponential backoff retry. Consider async SL sync off tick path.

### 4. No DB backup
- **File:** `database.py` (entire)
- **Issue:** Power loss corrupts SQLite. All state lost on reboot. Bot may be flat while position is live.
- **Fix:** Add daily `sqlite3.backup()` call. Or `wal_checkpoint(TRUNCATE)` + file copy on startup.

### 5. Rate-limited SL sync blocks tick path
- **File:** `live_loop.py:2106-2125`
- **Issue:** Synchronous sleep (up to 15s) on tick path during SL sync retries. Cannot process ticks during fast move.
- **Fix:** Move SL sync to async task or background thread.

---

## HIGH — Fix Before Going Live

### 6. Funding not in live cost tracking
- **File:** `live_loop.py:1734-1743`
- **Issue:** `cost_r = fee_r + slip_r` — no funding component. Live P&L overstated.
- **Fix:** Add `config.FUNDING_RATE_PCT` and compute `fund_r` in `_journal_trades()`.

### 7. Exit fill price uses sim estimate, not actual fill
- **File:** `live_loop.py:2205-2216`
- **Issue:** On timeout-retry exits, DB records bot's estimated fill (SL price), not actual exchange fill.
- **Fix:** Capture `avgPrice` from Bybit close response and use it.

### 8. Entry fill is market order (slippage varies)
- **File:** `live_loop.py:1811`
- **Issue:** Backtest assumes exact 15m close. Live fills at market price after close.
- **Fix:** Partially mitigated by cost model. Consider limit orders near 15m close.

### 9. Trail ratchet conservatism
- **File:** `live_loop.py:2093`
- **Issue:** Live requires `pivot < lo` (pivot below bar low) for ratchet. Backtester unconditionally ratchets.
- **Fix:** Align live ratchet logic to match backtester: ratchet FIRST, then check SL.
- **Status:** **FIXED** in backtester (commit ee574f9). Live still needs alignment.

### 10. Rolling 30-day window causes trade loss — **FIXED (2026-09-23)**
- **File:** `live_loop.py` (`WINDOW_DAYS_15M=30`), `v18_streak_halt.py` `to_intervals`, `_rebase_swings_to_window`
- **Issue:** Live uses a rolling 30-day window of 15m data. Backtest uses full 3+ year history. Root cause was a 5-layer C10 stack (L1 open-HTF dropped, L2 PSE stitch, L3 index-space mismatch, L4 last-bar drop, L5 forming-swing marks).
- **Fixes applied:**
  - **L1:** `to_intervals()` now keeps open HTF windows (`entry_ts → last_htf_ts+3600`) instead of `continue` — identity gate green (340t/+225.3R).
  - **L2:** PSE re-feed stitch (Issue #1) — 87/87 + 118/118 PERFECT parity.
  - **L3:** `_rebase_swings_to_window()` remaps swing indices into the trimmed window via time keys; called before every `_run_v18_simulation`.
  - **L5:** Open-swing marks appended via `get_open_swing()` (rebased) before `_collect_signals`.
  - **L4:** Replay-harness only (pad last-bar +2); production discovers entries on the next 15m sim rerun.
- **Verified:** `exp_issue10_window.py` — cold-start seed depth: 7d=100%, 30d=100%, live 20.8d seed=100% both TFs; continuous PSE vs full chain = 99.9% (2896/2899); windowed sim with rebased swings = 83.3% trade reproduction (was 0% naive); smoke 351t/+211.7R PASS.
- **Residual:** Replay harness cold-rebuilds swings per entry (worst case, not production) — remaining gap is structural chain divergence under truncated warmup, not index mismatch. Production uses seed-once + persistent PSE + rebase.
- **Priority:** CLOSED for live path; replay_harness.py adoption of L1/L3/L5 optional for diagnostics.

---

## MEDIUM — Fix During Paper Trading

### 11. Fine vs coarse fills
- **File:** `live_loop.py:1307` (`fine_ltf=[]`)
- **Issue:** Backtest optimizes on 1m fine fills; live runs on 15m coarse fills only.
- **Fix:** Stream 1m data and pass to simulation, or accept coarser exits.

### 12. No gap detection in CSV loading
- **File:** `btc_config.py` (load_btc_df)
- **Issue:** Missing candles silently alter swing chains.
- **Fix:** Add gap detection and warning. Forward-fill or re-download missing candles.

### 13. 1h boundary timeout
- **File:** `live_loop.py:662-686`
- **Issue:** If 15m candle hasn't arrived within 2.5s of 1h close, sim fires with stale data.
- **Fix:** Increase timeout or skip simulation at boundaries.

---

## LOW — Nice to Have

### 14. No liquidation price monitoring
- **File:** `bybit_order.py` (get_position returns liq_price but never used)
- **Fix:** Add Telegram alert when position approaches liquidation.

### 15. Clock skew >30min rejects fresh entries
- **File:** `live_loop.py:1649-1656`
- **Fix:** Use candle close time instead of system time for staleness check.

### 16. Daily halt not persisted before crash
- **File:** `live_loop.py:1418-1429`
- **Fix:** Persist halt state immediately when armed.

### 17. No global API rate limiter
- **File:** `bybit_order.py` (entire)
- **Fix:** Add token bucket for Bybit 10 req/s limit.

---

## ALREADY FIXED (Verified)

- M10: min qty forces instead of rejecting → FIXED (rejects)
- C4: double close guard → FIXED (WHERE status='open')
- C5: daily halt deadlock → FIXED (time-based reset)
- C6: IST/UTC trail delay → FIXED (subtracts IST_OFFSET_S)
- C7: lost entry response → FIXED (verify_entry_order)
- Stale entry guard → FIXED (2-bar threshold)
- Exit retry with close_position_retry → FIXED (3x3 attempts)

---

## ARCHITECTURE STRENGTHS

1. Exchange-side SL always armed (primary safety net)
2. Isolated margin + 3x leverage (liquidation ~33% away)
3. Kill switch exists (independent script)
4. Test coverage for critical paths (7 test files)
5. Identity gate ensures engine fidelity
6. Replay harness validates live-vs-backtest
