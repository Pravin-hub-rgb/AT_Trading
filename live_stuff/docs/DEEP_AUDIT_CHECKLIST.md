# Deep Audit Checklist — Live Engine Fixes (Post-Backtest)

Use this checklist when building the live bot. Each item has severity, location, and fix.

---

## CRITICAL — Fix Before Going Live

### 1. SWING ENGINE MISMATCH: backtester vs live use DIFFERENT engines
- **Backtester:** `compute_btc_swings` (btc_swing.py) — 87 swings on 40-day 15m slice
- **Live engine:** `PersistentSwingEngine` (persistent_swing.py) — 69 swings on SAME data (20% fewer)
- **Impact:** After the first swing, every subsequent swing diverges. Different prices, directions, break counts. The live engine produces entirely different trades. Backtest numbers (+325.8R) cannot be directly applied.
- **Replay harness result:** 0/180 trades reproduce through the live window pipeline
- **Fix:** Either (a) make PersistentSwingEngine produce identical chains to compute_btc_swings, or (b) rebuild the backtester to use PersistentSwingEngine, or (c) accept different numbers and re-optimize for the live engine
- **Priority:** THIS IS THE SINGLE MOST IMPORTANT FIX. Everything else is secondary.

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

### 10. Rolling 30-day window causes trade loss
- **File:** `live_loop.py:716` (`WINDOW_DAYS_15M=30`)
- **Issue:** Live uses a rolling 30-day window of 15m data. Backtest uses full 3+ year history.
- **Note:** Secondary to Issue #1 (swing engine mismatch). Fix the swing engine first.
- **Fix options:**
  1. Increase `WINDOW_DAYS_15M` to 60-90 days
  2. Persist swing chain endpoints to DB and reload on boot
  3. Accept the loss as cost of live deployment

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
