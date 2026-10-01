# New Bugs â€” Deep Audit (Pre-Production)

**Date:** 2026-09-15 (updated 2026-09-26)
**Status:** SPLIT â€” see the correction banner below. **Backtest integrity is CLEAN; live-execution items are still OPEN.**
**Scope:** Full live execution path audit (trade execution, backtest-live gaps, persistence, order management)

> ## âš ï¸ STATUS CORRECTION (2026-09-26) â€” READ BEFORE TRUSTING ANY "OPEN" LABEL BELOW
>
> This file was written 2026-09-15/17. Several `OPEN` labels are **stale** and were
> re-verified against the source and the executed regression on 2026-09-26.
>
> **BACKTEST-INTEGRITY ITEMS ARE ALL FIXED.** Verified by reading the current code
> and running `backend/tests/test_v18_causal_integrity.py`:
>
> | Item | Doc label | VERIFIED STATUS (2026-09-26) | Source evidence |
> |---|---|---|---|
> | C12 streak lookahead | was OPEN | **FIXED** (commit `375d9c4`, ancestor of HEAD) | `v18_streak_halt.py` L570 `halt_skip_next`; L579-583 skip consumed BEFORE the trade is built; L710-722 counter updated after `r_multiple`; L723 appends unconditionally. No `skip_trade` path exists. |
> | C13a pre-FS abandon | was "OPEN, needs USER RULING" | **FIXED** (commit `6b14494`, ancestor of HEAD) | `btc_engine.py` L280-282 pre-FS path `continue`s WITHOUT setting `swing_done`, so the swing survives for post-FS marks. |
> | C14 chop gate lookahead | was OPEN | **FIXED** | `v18_streak_halt.py` L269 `candle_ts_htf_close=[t+3600 ...]`, L272 `bisect_right(candle_ts_htf_close, ts+900)-1` â€” only a CLOSED 1h candle sets the regime. |
> | C15 HTF window gate | was OPEN | **FIXED** | `v18_streak_halt.py` L539 `if not (s + 2700 < bar_ts <= e + 2700): continue` and the union branch L513 `(s+2700<bar_ts<=e+2700)`. |
> | C13b store-miss abandon | was OPEN (minor) | **FIXED** | same `6b14494` change; store-miss no longer sets `swing_done`. |
>
> **Regression result:** `test_streak_books_losses_and_skips_next` PASS,
> `test_c14_c15_gates_present` PASS, `test_c15_count_band` PASS (351 trades in
> [346,356]). `test_baseline` FAILS **only** on a stale `assert n >= 150.0`
> threshold â€” see the REBASELINE note at the bottom of this file. Every causality
> assertion passes.
>
> **CONCLUSION: no backtest lookahead bug remains. Do not report C12/C13a/C13b/C14/C15
> as open.** The remaining OPEN items (C1, C2, C3, C4, C5, C7, C11, H3â€“H11,
> L1â€“L8, M1â€“M11, P1, P2) are **live-execution / operational** concerns. They carry
> real capital risk but **zero effect on backtest numbers**.
>
> **C10 is CLOSED** (fixed 2026-09-23). The five-layer stack shipped: L1 keeps
> open HTF windows in `to_intervals`, L2 is the PSE re-feed stitch, L3 is
> `_rebase_swings_to_window`, L5 appends the forming swing's marks. Verified
> 87/87 + 118/118 swing parity and 83.3% trade reproduction under a 30d window.
> The C10 sections further down this file are kept as the original
> 2026-09-17 root-cause analysis and use the old baseline â€” read them as history,
> not as current status.
>
> **ENVIRONMENT NOTE (bites repeatedly):** the default `python` on PATH is
> `C:\Program Files\Python310\python.exe` which has **no pandas**. Python 3.12
> (pandas 2.2.0) and 3.13 (2.3.3) are installed. Any harness reaching
> `btc_config.py` must use the 3.12/3.13 interpreter explicitly, or it fails with a
> misleading `ModuleNotFoundError: No module named 'pandas'`.
>
> Original 2026-09-15/17 content follows, retained for history.

### STREAK FIX APPLIED (2026-09-17)
- **Commit:** `375d9c4` â€” streak halt books every trade, skips NEXT entry after Nth loss
- **Verified:** Smoke test 375t/+305.5R gross/+216.9R net/PF 2.29/29.6% WR
- **Old numbers (261t/+470.5R/PF 4.71/45% WR) are INVALID** â€” from broken engine that deleted losses
- **C10 analysis below uses old baseline** â€” diagnostic only, not current live numbers

---

## CRITICAL â€” Must Fix Before Real Money

### C1. Exit orders have ZERO retry (stuck position risk)
- **Files:** `bybit_order.py:290-303`, `live_loop.py:1655`
- **Bug:** `close_position()` calls `place_market_order()` (single attempt), NOT `place_market_order_retry()`. If a transient network error, rate limit, or 10006 error hits during exit, the close fails. The DB trade is already closed (line 1870), the cache is cleared, but the Bybit position stays open with no SL monitoring.
- **Impact:** Stuck position with no protection. If a new signal arrives, bot enters a NEW trade while the old position is still live â†’ DOUBLE position with only one trade tracked.
- **Fix:** Add retry loop to `close_position()` matching `place_market_order_retry()` (3 attempts, exponential backoff + jitter). On failure, do NOT close DB trade or clear cache.

### C2. Exit failure = permanent DB/Exchange desync
- **Files:** `live_loop.py:1870-1880`
- **Bug:** DB trade is ALWAYS closed BEFORE the exchange close is attempted. If `close_position()` fails, DB says "closed" but Bybit says "open". Next tick sees no open trade in cache. If a new signal arrives, bot enters a NEW trade while the old position is still live.
- **Impact:** Double position with no proper risk tracking. Worst case: 2x leverage, only 1x tracked.
- **Fix:** Reverse the order â€” attempt exchange close FIRST, only close DB on success. On failure, keep trade "open" in DB/cache and retry on next tick.

### C3. Stale-entry execution on first boot / fresh DB
- **Files:** `live_loop.py:1536` (`_journal_trades`)
- **Bug:** `_journal_trades` executes ANY new sim trade with `outcome=="open"` â€” no seeding guard, no recency check. On fresh deploy or crash recovery, the sim produces historically-open trades. These are "new" to the DB â†’ `_execute_entry` fires a REAL market order at CURRENT price with SL/TP computed from an entry hours ago. If price moved 2R+ since sim entry, you enter a trade the engine would never take (past the 1.5R ext_stop), with R-accounting anchored to a stale price.
- **Impact:** Bad entry at wrong price, wrong R-accounting, potential loss.
- **Fix:** Skip execution when `_seeding` OR trade `entry_ts` older than 2 LTF bars. Journal as DB-only (`exit_reason="stale_skip"` or leave open-paper).

### C4. Stale `_open_ltf_trade` cache causes double-close in DB
- **Files:** `live_loop.py:1492-1533`
- **Bug:** When v18 simulation detects a trade is closed (cap/SL), `_journal_trades` closes it in DB. But `_open_ltf_trade` cache is NOT cleared for simulation-closed trades. Next tick, `on_tick` sees the stale cache, checks SL/TP/cap again, and closes the DB trade a SECOND time with potentially different exit values.
- **Impact:** Wrong R-multiple recorded. Streak/halt calculations corrupted. Daily PnL wrong.
- **Fix:** After `_journal_trades` processes a closed trade, clear the cache: `if self._open_ltf_trade and self._open_ltf_trade["id"] == trade_id: self._cache_ltf_trade_close()`

### C5. Daily halt reset is event-driven, not time-driven
- **Files:** `live_loop.py:1318-1322`
- **Bug:** `_daily_halted = False` only resets when `_check_daily_loss_limit()` is called, which only happens on trade close. If no trade closes after midnight IST, the bot stays halted ALL NEXT DAY. The first trade opportunity after midnight is incorrectly blocked until the next trade closes.
- **Impact:** Missed trades for potentially hours after midnight. Lost profits.
- **Fix:** Add time-based reset at top of `_on_tick` or `_on_15m_close`: `if current_ist_date != self._last_trade_date: self._daily_halted = False; self._daily_pnl_r = 0.0`

### C6. IST/UTC epoch mismatch in `_trail_events_ts` â€” trail delayed ~5.5 hours
- **Files:** `btc_engine.py:310`
- **Bug:** `_trail_events_ts()` converts IST wall-clock strings to epoch by treating them as UTC:
  ```python
  ts = int(datetime.strptime(conf_time, "%Y-%m-%d %H:%M:%S")
              .replace(tzinfo=timezone.utc).timestamp())
  ```
  The event epoch is ~5.5 hours (19800s) AHEAD of reality. In `_trail_sl`, pivot activation is delayed because `event_epoch > bar_epoch` for the same moment.
- **Impact:** Trail SL ratchets late. Long trades: SL stays at lower level too long. Short trades: SL stays at higher level too long. Estimated 0.1-0.5R per trailed trade, compounding over hundreds of trades. This is the single largest source of live underperformance vs backtest.
- **Fix:** Parse IST string as IST, not UTC:
  ```python
  from zoneinfo import ZoneInfo
  IST = ZoneInfo("Asia/Kolkata")
  ts = int(datetime.strptime(conf_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST).timestamp())
  ```
- **Verified:** 2026-09-15, empirically â€” swing `confirmed_at_time="2025-01-01 12:00:00"` â†’ `_trail_events_ts` returns epoch 1735732800; the live candle for that same moment has ts 1735713000; **diff = 19800s = exactly 5.5h**. Backtest trail is index-based (immune) and the v18-sim rebuild inside live uses stringâ†’position lookup (immune) â€” only `_trail_sl` is affected.

### C7. Duplicate-orderLinkId retry â†’ orphan live position with no DB trade
- **Files:** `bybit_order.py:245-288`, `live_loop.py` `_execute_entry`
- **Bug:** `place_market_order_retry()` reuses ONE `orderLinkId` across retries (correct for idempotency). But if the FIRST attempt **lands on the exchange** while its HTTP response is lost (timeout / connection reset â†’ `retCode: -1, retMsg: exception string`), the retry is rejected by Bybit as a duplicate orderLinkId â†’ `retCode != 0` â†’ `_execute_entry` treats it as failure â†’ closes the DB trade as `order_failed`. The real market order already filled â†’ **live exchange position exists with NO DB trade and NO cached trade**. `on_tick` ignores it (no cached trade), no SL monitoring beyond the exchange-attached SL, and the next signal can stack exposure on top.
- **Impact:** Untracked live position. Books wrong until restart (`_reconcile_bybit_position` fixes it only at boot).
- **Fix:** In `_execute_entry`, on order failure: query Bybit for the order by `orderLinkId` (`session.get_open_orders` / order history) or poll position â€” if filled, ADOPT the position (keep DB trade, record real fill); only close as `order_failed` when confirmed the order never landed. Related to H4 (fill polling) but distinct: H4 handles slow fills, C7 handles lost-response retries.
- **Status:** FIXED 2026-09-15 - `get_order_by_link_id()` + `verify_entry_order()` added in `bybit_order.py` (position-first, order-history tie-breaker, side-mismatch -> unknown). `place_market_order_retry` accepts/returns `order_link_id`. `_execute_entry` failure path: verify -> ADOPT (qty update + alert) / confirm-flat (order_failed) / unknown (DB held open + loud alert, bounded by exchange SL). Success path: 3x position poll (H4 folded). Tests: `backtest/tests/test_entry_verify.py` (7 checks).

### C8. Live attaches 3R TP to every LTF order â€” caps winners at 3R, backtest rides to +5.02R
- **Files:** `live_loop.py:1647,1676`
- **Bug:** `_execute_entry` passes `take_profit=tp_str` (3R target) to Bybit. But v18's LTF uses `trailing="swing"` â†’ the sim NEVER exits at target. Zero target exits in backtest. Winners ride the MB50 trail to avg +5.02R (186 trail exits, 0 target exits). The live exchange TP caps every winner at +3R, chopping 33% of runner edge.
- **Impact:** Every runner â€” the trades that make the strategy's entire edge â€” gets capped at 3R on live while backtest rides them to +5R+. Direct, massive divergence from the +470.5R deploying on. Also: if TP fires during downtime, reconcile books exit at `sl_current` (~-1R) instead of +3R, causing false streak halt.
- **Fix:** Remove `take_profit=tp_str` â†’ pass `None`. SL stays attached (downtime protection unchanged). Winners ride the trail. DB `tp_price` field stays for audit context only. Reconcile concern dissolves (exchange SL is the only exit â†’ `sl_current` is correct by construction).
- **Status:** FIXED 2026-09-15 - `take_profit=None` in `_execute_entry` (SL stays
  attached for downtime protection; DB `tp_price` kept for audit). Regression test
  asserts no TP on LTF orders (`test_entry_verify.py` PASS 4). With TP gone, the C8
  reconcile scenario dissolves: the only exchange-side exit is the SL, so the
  reconcile `sl_current` assumption is correct by construction.


---

## HIGH â€” Should Fix Before Live

### H1. ~~Streak-halt never enforced on executor~~ **FALSE POSITIVE â€” DROPPED**
- **Reason:** v18 streak halt has resume-on-winner semantics: the sim deliberately produces the resume trade (processes it hypothetically; if it wins, halt lifts and the trade IS taken). A `trading_state["halted"]` gate in `_execute_entry` would block the resume trade â†’ PERMANENT streak halt with no escape.
- **Status:** Never a bug. The sim already handles streak halt correctly. Adding a gate would break it.

- **Files:** `live_loop.py:1287, 1541`
- **Bug:** `trading_state["halted"]` is computed and persisted but never read as an entry gate. `_execute_entry` checks only `_daily_halted`. Currently safe because the sim applies halt within its rolling window, but if the streak ever straddles the window edge (or state diverges), a trade executes that the strategy says shouldn't.
- **Impact:** Safety net missing. Maintenance trap.
- **Fix:** Add gate in `_execute_entry`: `if self.trading_state.get("halted"): print("..."); return`

### H2. ~~`_execute_exit` has no retry~~ **FIXED by C1/C2** (doc entry was stale)
- **Files:** `live_loop.py:1829`
- **Bug:** (originally) `close_position()` called with zero retries.
- **Status:** FIXED â€” C1/C2 replaced `close_position()` with `close_position_retry()` (3Ã—3 retries, position re-checked each attempt). `_execute_exit` returns bool; callers keep DB open + retry on next tick. This doc entry was stale.

### H3. Bybit SL sync failure leaves exchange SL stale
- **Files:** `live_loop.py:1791-1810`
- **Bug:** When trailing SL, DB is updated first, then synced to Bybit. If both Bybit sync attempts fail, DB is updated but exchange SL stays at old level. Log says "DB only" but no retry beyond 2 attempts, no alarm, no halt.
- **Impact:** Exchange SL could be at initial level while DB SL is trailed to breakeven+. If Bybit's SL is hit, actual fill is worse than bot expects.
- **Fix:** Increase retry count to 5 with exponential backoff. Add Telegram alert on sync failure. Periodic reconciliation comparing DB `sl_current` with Bybit's actual conditional SL.
- **Status:** FIXED 2026-09-15 â€” retries increased from 2 to 5 with exponential backoff (0.5sâ†’8s), Telegram alert on final failure.

### H4. Fill verification uses `sleep(0.3)` â€” false order_failed
- **Files:** `live_loop.py:1582-1586`
- **Bug:** After placing order, sleeps 0.3s then queries position. If Bybit hasn't processed fill in 300ms (network latency, exchange load), `actual_qty` = 0 â†’ triggers false "order_failed" â†’ DB trade closed â†’ orphan position on Bybit.
- **Impact:** Good entry reported as failed, position orphaned.
- **Fix:** Replace `sleep(0.3)` with polling loop: query position every 100ms for up to 2 seconds, break as soon as `actual_qty > 0`.

### H5. `qty` column never set for full fills
- **Files:** `live_loop.py:1608-1609`
- **Bug:** `update_trade_qty()` only called for partial fills. For normal happy path (full fill), `qty` stays at default 0 forever.
- **Impact:** Any post-trade analysis or P&L calculation using `qty` sees zero.
- **Fix:** Add `update_trade_qty(self.db, trade_id, actual_qty)` after full fill confirmation.
- **Status:** FIXED 2026-09-15 â€” `update_trade_qty` called unconditionally on both partial and full fill paths, including the C7 adopt path.

### H6. No session health monitoring â€” dead session reports connected
- **Files:** `bybit_order.py:152`
- **Bug:** `is_connected` returns `self.session is not None`. Session object exists even if TCP connection is dead. No heartbeat check, no periodic reconnect, no health monitoring.
- **Impact:** All order operations fail with exceptions. Trade in bad state.
- **Fix:** Add periodic health check (e.g., `get_wallet_balance()` every 5 min). On failure, reconnect session.
- **Status:** FIXED 2026-09-15 â€” `_probe()` / `_reconnect()` methods in BybitTrader, per-order self-heal in `place_market_order_retry`, `_session_watch()` background task (30s probe + Telegram alert), `self.logger` â†’ `logger` bug fixed. Tests: `test_session_health.py` (7 checks).

### H7. No DB backup, WAL checkpoint, or integrity check
- **Files:** `database.py`
- **Bug:** Zero backup mechanisms. No `PRAGMA wal_checkpoint()`. No `PRAGMA integrity_check`. WAL file grows unbounded. If DB corrupts (power loss, disk full), total loss.
- **Fix:** On startup: `PRAGMA wal_checkpoint(TRUNCATE)` + `PRAGMA integrity_check`. Add backup mechanism (copy DB daily).
- **Status:** FIXED 2026-09-15 â€” WAL checkpoint(TRUNCATE) + integrity_check added to `Database.connect()`. Non-critical errors logged, do not block startup.

### H8. `close_position` succeeds when `get_position` fails
- **Files:** `bybit_order.py:290-303`
- **Bug:** If `get_position()` fails (network error), returns `None`. `close_position()` interprets this as "no position" â†’ returns `retCode: 0` (SUCCESS). Caller thinks position was closed when it's still open.
- **Impact:** False "position closed" state.
- **Fix:** Distinguish between "no position" (empty result) and "query failed" (exception). Return different sentinel values.
- **Status:** FIXED 2026-09-15 â€” `close_position_retry()` (C1/C2 fix) uses `get_position_checked()` which returns `(False, None)` on query failure. Caller keeps retrying until genuinely flat.

### H9. Funding rate not tracked anywhere
- **Files:** N/A â€” not implemented
- **Bug:** Bybit charges/receives funding every 8h (0.01%/8h typical). Live system has NO funding tracking. R-multiples overestimated. Cost summary underestimates true cost.
- **Impact:** 0.01-0.05R per trade on multi-day holds. Compounds over hundreds of trades.
- **Fix:** New module or add to cost tracking. Deduct funding from R on each settlement.

### H10. `is_connected` probe at exit time re-introduces C2 desync **[CRITICAL]**
- **Files:** `bybit_order.py:152`, `live_loop.py:2058, 2090`
- **Bug:** H6 changed `is_connected` from `self.session is not None` to `self._probe()` (real HTTP `get_wallet_balance()` call). Exit guards in `on_tick` used `if self.trader and self.trader.is_connected:` â€” a transient probe failure (network blip, rate-limit, wallet endpoint hiccup) makes the guard False â†’ `_execute_exit` never runs â†’ `close_ltf_trade` fires â†’ DB says closed, exchange position stays open with no bot-side monitoring. This is C2 re-introduced through a new door.
- **Impact:** Untracked live position during SL/cap event. Rate-limited probe = money-losing path.
- **Fix:** Revert `is_connected` to cheap local check (`self.session is not None`). Add `_healthy()` property returning cached probe result (updated by `_session_watch` every 30s). Exit guards changed to `if self.trader:` (no network-dependent skip). Live `_probe()` kept only in low-frequency paths: `place_market_order_retry`, `close_position_retry`, `_session_watch`.
- **Status:** FIXED 2026-09-15

### H11. `is_connected` probe-per-call = API storm + blocking tick thread **[HIGH]**
- **Files:** `bybit_order.py:152`, `live_loop.py` (7 sites), `bybit_order.py` (11 sites)
- **Bug:** `is_connected` making synchronous HTTP request on every call. Called on every trade print (tick handler), plus nested inside `get_position_checked()`, `place_market_order_retry()`, `close_position_retry()`. Consequences: Bybit rate-limit exposure (retCode 10006 â†’ temporary ban), blocking HTTP call inside tick handler (tick backlog while streaming), `_execute_exit` becomes slow right when you need it fast.
- **Impact:** Rate-limit risk, tick handler latency, possible WebSocket disconnect.
- **Fix:** Same as H10 â€” `is_connected` reverted to cheap check. `_probe()` only called in low-frequency paths (retry loops, session watch). `_healthy()` provides liveness signal without per-call cost.
- **Status:** FIXED 2026-09-15 (merged with H10 fix)

---

## MEDIUM â€” Should Fix Eventually

### M1. `htf_window_id = 0` stored when no window is open
- **Files:** `live_loop.py:1480-1481`
- **Bug:** When both HTF windows are closed, `htf_id` defaults to `0`. Since `htf_windows.id` starts at 1 (AUTOINCREMENT), `0` is an invalid FK. Reporting queries joining on this field miss these trades.
- **Fix:** Use NULL instead of 0, or handle in queries.

### M2. `close_ltf_trade` lacks `AND status='open'` guard  [RETIRED - merged into C4]
- **Files:** `trade_store.py:139-144`
- **Bug:** No guard against double-close. Calling `close_ltf_trade` on an already-closed trade silently overwrites exit values.
- **Fix:** Add `AND status = 'open'` to WHERE clause.

### M3. Multiple open windows for same regime â€” `LIMIT 1` abandons older
- **Files:** `trade_store.py:66-75`
- **Bug:** If crash occurs after `open_htf_window` but before `close_htf_window`, and then a NEW window opens for same regime, there are two open windows. `LIMIT 1` returns only newest. Older window leaks forever.
- **Fix:** On startup, close any stale open windows for a regime before opening new one.

### M4. Missing indexes on frequently-queried columns
- **Files:** `database.py:22-57`
- **Bug:** No indexes on `htf_windows(status, regime)`, `ltf_trades(status)`, `marks(tf, ts)`. Full table scans on every 15m candle close.
- **Fix:** Add indexes.

### M5. `_execute_exit` bare market close â€” no SL/TP protection during close
- **Files:** `bybit_order.py:290-303`
- **Bug:** `close_position()` places bare market close without SL/TP. If close accepted but not filled instantly (extreme volatility, wide spreads), position briefly exposed.
- **Impact:** Brief exposure window during close.
- **Fix:** Pass current SL as conditional stop on close order.

### M6. Window trimming loses signals near boundary
- **Files:** `live_loop.py:621-622`
- **Bug:** When `window_15m` is trimmed (30 days), break marks referencing trimmed candles cause signals to be skipped in `_collect_signals`. Backtest has no window trimming.
- **Impact:** Live systematically misses signals near window boundary.
- **Fix:** Extend window or use marks-only signal detection.

### M7. Boundary sync timeout can cause stale chop
- **Files:** `live_loop.py:561-592`
- **Bug:** 2.5s timeout forces simulation even if 1h candle is delayed. Chop index and regime can be wrong for one cycle.
- **Impact:** Wrong regime for one simulation cycle.
- **Fix:** Increase timeout or skip simulation when 1h data is stale.

### M8. Cooldown bar count discrepancy (backtest vs live)
- **Files:** `v18_streak_halt.py:221`, `live_loop.py:624-629`
- **Bug:** Backtest uses bar INDEX distance. Live uses COUNTDOWN. Equivalent only if every 15m bar fires a simulation. Boundary sync can skip bars, making live cooldown effectively longer.
- **Impact:** Live cooldown slightly longer than backtest.
- **Fix:** Use same mechanism (index-based or countdown, pick one).

### M9. Rate manager blocks event loop during entry
- **Files:** `live_loop.py:1677`, `rate_manager.py:100-127`
- **Bug:** `rate_manager.update()` makes synchronous HTTP calls (10s timeout each) to CoinGecko + ExchangeRate-API. Happens during `_calculate_qty` â†’ `_execute_entry` â†’ `_journal_trades` â†’ `_on_15m_close`. Blocks event loop up to 20s.
- **Impact:** Missed ticks, WebSocket disconnect during entry.
- **Fix:** Make rate fetch async, or pre-fetch in background.

### M10. `min_qty` can silently exceed risk
- **Files:** `live_loop.py:1692`
- **Bug:** `qty = max(min_qty, computed)` â€” when computed qty < exchange minimum, risk becomes `min_qty Ã— stop_distance`, possibly several Ã— your `risk_inr`.
- **Impact:** Forced over-risk on tight SL distances.
- **Fix:** Reject instead of force. Log actual risk.

### M11. Reconciliation uses 0.0R for direction mismatches
- **Files:** `live_loop.py:384-389`
- **Bug:** On direction mismatch (DB=long, Bybit=short), DB closed with `r_multiple=0.0`. Actual PnL unknown.
- **Impact:** Incorrect PnL recording affects streak/halt calculations.
- **Fix:** Query actual position price from Bybit if possible.

---

## LOW â€” Nice to Fix

### L1. Dead columns in `ltf_trades`
- **Files:** `database.py:54-56`
- `trail_next_pivot`, `trail_activation_idx`, `trail_confirmed` never used.

### L2. `_get_existing_marks_set` loads ALL marks into memory
- **Files:** `live_loop.py:1717-1720`
- No time filter. Grows unbounded.

### L3. `_get_existing_trades_set` loads ALL trades into memory
- **Files:** `live_loop.py:1714`
- No time filter. Grows unbounded.

### L4. Dedup key `(entry_ts, direction)` missing `htf_window_id`
- **Files:** `live_loop.py:1713-1715`
- Two trades at same bar from different HTF windows would collide. Unlikely but possible with b2+flip coexistence.

### L5. SL/TP price format hardcoded to 2dp
- **Files:** `live_loop.py:1559-1560`
- Works for BTCUSDT but not instrument-portable.

### L6. Kill switch has minimal retry (2 attempts, no backoff)
- **Files:** `kill_switch.py:70-91`
- Emergency tool. Operator can retry manually.

### L7. No tick-level TP monitoring
- **Files:** `live_loop.py:1819-1880`
- TP handled by Bybit server-side + sim on candle close. Brief desync window (up to 15 min).

### L8. Uses `walletBalance` instead of `availableBalance`
- **Files:** `bybit_order.py:164-165`
- Slight over-sizing possible with unrealized loss.

---

## Verified Safe (confirmed by both audits)

- âœ… All 261 trades execute â€” no window gate blocks them
- âœ… v18 engine logic â€” backtest matches live
- âœ… Swing detection â€” same engines, same params
- âœ… Cooldown/streak â€” survives restart via DB
- âœ… Dedup â€” works correctly
- âœ… B2 bookkeeping fix â€” zero execution-path changes
- âœ… on_tick SL/cap fills mirror v18's conservative fills
- âœ… Retry idempotency via orderLinkId
- âœ… Partial-fill handling
- âœ… Balance-safety + leverage cap in `_calculate_qty`
- âœ… Crash reconcile on boot
- âœ… Paper mode correctly gates the trader object

---

## Key Design Rule (established by H10/H11)

**Guards use cheap state; only retry/submit/watch paths may probe.**

- `is_connected` = `self.session is not None` (local, no network)

### C10 (refined 2026-09-17). HTF window state gates LTF entries on engine DECLARATIONS, not on the real-time flip marks â€” live rejects trades the backtest takes

- **Files:** `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` (LTF filter consumes HTF intervals), `backend/src/btc/engines/v7_timecap.py` (HTF walk builds windows from DECLARED swings), `backend/src/live/persistent_swing.py` (live hands only declared swings to the sim)
- **Bug:** The v18 LTF filter requires the entry bar to sit inside an HTF window (flip/b2) whose direction matches the signal. Those HTF windows are built from swings as the ENGINE declares them â€” i.e. only after the chop/sustain confirmation completes (`confirmed_at_time`), which can lag the actual flip/B1 mark by hours. The backtest, running over full history, sees all swings as already declared and therefore treats the window as open from the flip candle (retro). Live, running causally, cannot see a swing that has not declared yet â€” so during the declaration gap live keeps the OLD window (possibly opposite direction) and rejects the signal ("signal dir != window dir").
- **Worked example â€” trade #31 of 261 (09-Jun-2023, LONG):**
  | Time (IST) | Event |
  |---|---|
  | 09-Jun 07:00 | 1h up-structure level broken (B1 @ 26393) |
  | 09-Jun 18:15 | 1h candle breaks UP through 26718 â†’ FLIP mark. Per the design rule (FS and flip/b2 may share a candle) the HTF flips to LONG here |
  | 09-Jun 18:45 | 15m FLIP long signal, bar closes ~26672 â†’ backtest books trade #31 LONG |
  | 10-Jun 06:00 | The 1h swing finally DECLARES (engine chop/sustain) â€” ~11.75h after the flip |
  At 18:45 the causal state was: chop(1h)=73.1 â†’ b2 regime â†’ the covering b2 window was the OLD SHORT (opened 31-May) â†’ **long signal rejected, dir mismatch**. The backtest allowed it only because swing #151 was retro-declared and its flip had already opened a long b2 window.
- **Measured declaration lag (1h swings, correct TZ):** median ~1.25h after the break mark, fat tail up to ~40h. Most entries would shift ~1h in a causal run; tail cases are blocked/misdirected exactly as above.
- **Impact:** With causal (live-faithful) evaluation the replay is 0/32 vs baseline 261/261. The +470.5R backtest assumes knowledge of HTF window flips up to ~40h before the engine would confirm them in real time.
- **A/B proof so far:** C11 timeCap fix alone does NOT resolve it (replay with `--timecap 00:00` still 0/32). The blocker is the HTF window availability, not the LTF timeCap.
- **Fix direction (not yet implemented):** live must flip HTF windows on the real-time flip/B2 mark of the forming swing (same candle as FS allowed â€” the established design rule), not wait for the engine declaration. Then replay the full 3.8y history through this causal rule to get the honest live-expected numbers (they will differ from +470.5R).
- **Status:** OPEN â€” root cause diagnosed & verified by gate-by-gate trace (2026-09-17). Fix pending decision on causal HTF window design.

- `_healthy` = cached probe result (updated by `_session_watch` every 30s)
- `_probe()` = live HTTP call (only in low-frequency paths: retry loops, session watch)
- Exit guards use `if self.trader:` (never skip exchange close based on network state)

---

## Pre-Flight Ritual (before real money)

1. Fix C1-C8 + H2-H11 (H1 dropped, H2 fixed by C1/C2) â€” **DONE 2026-09-15 except H9 (deferred)**
2. Paper mode for â‰¥2 weeks with daily backtest-parity diff
3. One full live cycle at minimum risk (entry â†’ SL sync â†’ trail â†’ exit â†’ Telegram)
4. Kill-9 mid-position restart drill
5. Confirm one-way mode / `positionIdx=0` on Bybit account
6. Verify Telegram alerts work for: entry, exit, error, kill switch

---

## Fix Plan (merged from both audits â€” every item code-verified 2026-09-15)

### CRITICAL (C1-C7) â€” ~75 lines across 4 files

| # | Fix | Where | Effort | Status |
|---|-----|-------|--------|--------|
| C1 | Exit retry + DB/Exchange order reversal | `_execute_exit`, `bybit_order.py:close_position` | ~40 lines | **FIXED 2026-09-15** |
| C2 | (included in C1 â€” reverse order) | `live_loop.py:1870-1880` | â€” | **FIXED 2026-09-15** |
| C3 | Stale-entry guard (in-trade + seeding + recency, streak skip-list, boot SL sync) | `_journal_trades`, `_is_stale_entry`, `_persist_streak_state`, `_boot_sync_sl` | ~25 lines | **FIXED 2026-09-15** |
| C4 | Close guard: status-filter + rowcount + cache sync + no double accounting | `trade_store.py:close_ltf_trade`, `_journal_trades`, `on_tick` | ~15 lines | **FIXED 2026-09-15 (merges M2)** |
| C5 | Daily halt time-based reset + halted_skip journaling (no phantoms) | `_maybe_reset_daily` (boot + 15m/1h close), `_journal_trades`, `_persist_streak_state` | ~35 lines | **FIXED 2026-09-15** |
| C6 | IST/UTC epoch fix | `btc_engine.py:310` | ~5 lines + test | âœ… FIXED |
| C7 | Adopt-or-verify on duplicate orderLinkId | `_execute_entry` + `bybit_order.py` | ~70 lines + test | **FIXED 2026-09-15** |
| C8 | Remove 3R TP attachment from LTF orders (caps runners; sim is trail-only) | `_execute_entry` take_profit=None | ~1 line + test | **FIXED 2026-09-15** |

### HIGH (H1-H11) â€” ~50 lines across 5 files

| # | Fix | Where | Effort | Status |
|---|-----|-------|--------|--------|
| H1 | ~~Streak-halt executor gate~~ FALSE POSITIVE | ~~`_execute_entry`~~ | ~~3~~ | **DROPPED â€” never a bug** |
| H2 | ~~Exit retry~~ FIXED by C1/C2 | `_execute_exit` | ~15 lines | **FIXED by C1/C2** |
| H3 | Trail SL sync retry + alert | `_trail_sl` | ~10 lines | **FIXED 2026-09-15** |
| H4 | Fill verification polling | `_execute_entry` | ~10 lines | **FIXED - folded into C7** |
| H5 | Set qty on full fill | `_execute_entry` | ~2 lines | **FIXED 2026-09-15** |
| H6 | Session health check | `bybit_order.py` | ~10 lines | **FIXED 2026-09-15** |
| H7 | WAL checkpoint + integrity check | `database.py` | ~5 lines | **FIXED 2026-09-15** |
| H8 | Distinguish no-position vs query-fail | `bybit_order.py` | ~5 lines | **FIXED 2026-09-15** |
| H9 | Funding rate tracking | New module | ~50 lines | DEFERRED |
| H10 | is_connected probe at exit = C2 desync | `bybit_order.py`, `live_loop.py` | ~10 lines | **FIXED 2026-09-15** |
| H11 | is_connected probe-per-call = API storm | `bybit_order.py`, `live_loop.py` | merged w/ H10 | **FIXED 2026-09-15** |

### MEDIUM (M1-M11) â€” ~80 lines across 6 files

| # | Fix | Where | Effort |
|---|-----|-------|--------|
| M1 | Use NULL for missing window id | `live_loop.py` | ~3 lines | **FIXED 2026-09-16 â€” journal writes NULL (not 0); schema migration rebuilds ltf_trades to drop the NOT NULL on htf_window_id (transactional, idempotent)** |
| M2 | Add `AND status='open'` guard | `trade_store.py` | ~2 lines | **RETIRED 2026-09-15 - merged into C4** |
| M3 | Close stale windows on startup | `live_loop.py` | ~5 lines | **FIXED 2026-09-16 â€” root cause was the tracker's missing branch: sim-latest open + our window open with a DIFFERENT entry_ts silently kept the dead window (and never persisted the new one). Now: old window closed with real sim exit data (matched by entry_ts) or stale_cap when its lifecycle fell outside the sim slice; boot sweep closes any open window whose 16d cap passed while down** |
| M4 | DB indexes | `database.py` | ~5 lines | **FIXED 2026-09-16 â€” idx_ltf_entry_ts, idx_ltf_status_entry, idx_htf_status_regime, idx_marks_tf_ts (created post-migration)** |
| M5 | Pass SL on close order | `bybit_order.py` | ~5 lines | **FIXED 2026-09-16 â€” close orders re-attach the position's exchange SL; unprotected orphans get a wide panic SL at Â±PANIC_SL_PCT (5%) from entry; get_position now exposes stop_loss** |
| M6 | Extend window or marks-only signals | `live_loop.py` | ~10 lines |
| M7 | Increase boundary timeout | `live_loop.py` | ~1 line |
| M8 | Unified cooldown mechanism | Both files | ~10 lines |
| M9 | Async rate fetch | `rate_manager.py` | ~20 lines | **FIXED 2026-09-15 â€” `update()` moved off tick path into `_session_watch` via `asyncio.to_thread`; `_calculate_qty` sizes from cache + warns when stale (`is_stale()`/`age_min()` added)** |
| M10 | Reject when qty < min | `_calculate_qty` | ~5 lines | **FIXED 2026-09-15 â€” both paths (risk-sized + balance-sized); rejects return 0.0 â†’ caller skips** |
| M11 | Query actual price on mismatch | `live_loop.py` | ~5 lines |

### C11. Live swing engine inherits the Nifty session gate (`timeCap="09:29"`) â€” BTC declarations blocked before 09:29 IST

- **Files:** `backend/src/firstswing.py:73` (default), `backend/src/live/persistent_swing.py:17` (live passes no timeCap), `backend/src/btc/btc_swing.py:54` (backtest forces "00:00")
- **Bug:** `SwingEngine` defaults `timeCap="09:29"` â€” a Nifty (Indian market hours) session gate. The backtest overrides it to `"00:00"` for 24/7 BTC. The live `PersistentSwingEngine` does NOT override it, so live inherits "09:29": `_confirm` returns early (`firstswing.py:589` â€” `if self.t[11:16] < self.time_cap`) â†’ **no swing can declare between 00:00 and 09:28 IST in live**.
- **Impact:** Live's entire swing chain diverges from the backtest's (proof: replay harness 0/32 with live defaults vs baseline 261/261). Swings forming overnight never declare on time; every downstream mark/entry shifts.
- **Fix:** Force `timeCap="00:00"` in `PersistentSwingEngine` opts (match the backtest). Test first: replay harness A/B (`--timecap 00:00` vs default).

### C10 FINAL ROOT-CAUSE STACK + MEASURED RESULTS (2026-09-17, causal replay test `causal_replay.py`)

C10 is not one bug â€” it is a STACK of five independent layers, each verified by A/B replay of the 261-trade baseline through truncated (causal, live-style) windows:

| # | Layer | Where | Proof |
|---|-------|-------|-------|
| L1 | Still-open HTF windows are DROPPED from the LTF gate | `v18_streak_halt.py:106` `to_intervals()`: `if t["outcome"]=="open": continue` | Every baseline trade sits INSIDE its governing HTF window by construction; a truncated slice always ends with that window open -> dropped -> no covering window -> gate rejects. Fix (open window = active bias, end=+inf) restores it. User rule confirmed: window closes only on -1R / 3R / 16d cap; new window never opens while the previous is alive (verified per-track: flip and b2 tracks are each strictly sequential, they run in PARALLEL) |
| L2 | Live PSE chains swings FORWARD-ONLY; the backtest re-chains from the previous swing's END EXTREME | `persistent_swing.py:157-163` vs `btc_swing.py:148-154` | On identical data, live PSE 1h chain diverges from the backtest `continuous` chain from swing #1 onward (20 vs 27 swings, different pivots/marks). FIX VERIFIED: on each declaration, replay the overlap candles `[end_idx+1..now]` into the fresh engine (recursively) -> chain becomes 27/27 IDENTICAL (0 diffs). ReplayPSE vs continuous over the full 261 replay: IDENTICAL results (209/253 both) |
| L3 | INDEX-SPACE MISMATCH: swings carry indices from one candle list, the sim gets a DIFFERENT (trimmed) list | LIVE: `live_loop.py:_run_v18_simulation` passes `c15 = self.window_15m` (trimmed, positions restart) with `sw15 = self.all_swings_15m` (g_idx = monotonic counters, never reset). HARNESS: same pattern (swings over 35d/25d warmup fetch, sim on 30d/20d trim) | With mismatched lists: `_collect_signals` index fallbacks (`store.pos(b_time)` vs `start_idx_fb` / `prev_confirmed_idx_fb` / `candles[_pe_idx.._b_idx]` slices) compare two spaces -> ALL signals silently dropped -> 0 LTF signals, 0 HTF walk trades on EVERY window. Fix: sim candles must be the SAME list the swings were built on |
| L4 | Signal at the slice's LAST bar is dropped | engine walk: `if i >= n-1: continue` | The entry bar E is the last candle of a `[..E]` slice -> trade never taken in that rerun; live discovers it on the NEXT sim rerun (15m later). Replay must pad the slice (+2 bars = next rerun) |
| L5 | FORMING swing's real-time marks are invisible to the batch chain (user's original hypothesis â€” CONFIRMED) | batch `compute_btc_swings` attaches marks only to DECLARED swings; live PSE exposes them via `get_open_swing()` | Worked example trade #10 (06-Apr-2023 00:45 IST LONG B2): truncated chain's swing 77 marks end 19:30; the 00:45 B2-up mark belongs to the still-forming swing -> batch list has no such signal. Fix: append the forming swing's marks (the live-open swing) to the chain before `_collect_signals` |
| C11 | timeCap 09:29 (separate, already documented) | `persistent_swing.py` | Real bug, orthogonal â€” include in the fix |

**MEASURED CAUSAL REPLAY (all 261 baseline trades, live-style truncated windows, causal engine + fixes):**

| Setup | Reproduced |
|-------|-----------|
| Harness as-is (current live procedure) | 0/32 |
| L1 only (causal engine, mismatched lists) | 0/253 |
| L1 + L3 (consistent) | 0/253 (walk stops early) |
| L1 + L3 + L4 (pad 2) + L5 (open-swing marks) | **209/253 (82.6%)** within 2 bars |
| same + pad 12 (3h discovery) | 219/253 (86.6%) |
| same + pad 48 (12h discovery) | 230/253 (90.9%) |

- ReplayPSE (L2 fix) vs continuous chain: **identical 209/253** â€” the live chain fix is validated.
- Baseline sanity: causal engine on FULL history = 261/261 exact match (patch touches only the open-window line).
- Remaining ~9% (23 trades) blocked even at 12h discovery â€” dominated by HTF window timing (1h flip candle closes up to 1h after the mark â€” user's candle-close point) and chop-regime timing at the gate. These are the honest live gaps to quantify next.
- R/outcome parity of reproduced trades not yet compared (entry bar + direction matched only). Next step: net-R comparison of the causal pipeline vs +470.5R.

### C10 NET-R MEASURED (2026-09-17, `causal_net_r.py`, same-fill convention fine_ltf=[], Bybit costs 0.055% + 5bp/10bp slip)

| Pipeline | Trades | Gross R | Net R |
|----------|--------|---------|-------|
| Baseline (retro, full history) | 261 | +445.60R | **+399.57R** |
| Causal pipeline (2-bar discovery, fixes L1-L5) | 209 | +338.79R | **+301.03R** |
| Delta | -52 | | **-98.53R (-24.6%)** |

- All 209 matched at dts=0 (same entry bar) -> their R is EXACT (walk for a given entry bar depends only on that bar's close + global trail events, not on other trades).
- 44 backtest trades are NOT taken causally (the honest live gap).
- IMPORTANT FINDING: the causal slices also produce **304 unique EXTRA entries not in the backtest** (causal chain state differs -> different signals fire). These are excluded from the +301R above. Whether they add or subtract R requires the single sequential causal pass (the true live pipeline study). The honest live expectation is therefore BETWEEN +301R (extras ignored) and higher (extras included) â€” must be measured with a one-pass sequential simulation before going live.
- W/L: causal 85/124 vs baseline 119/142.
- Next: (1) sequential one-pass causal simulator for the true trade set incl. extras; (2) code fixes L1-L5 + C11 (all now specified with proofs); (3) parity_report integration.

### C10 BLOCKER GROUPS (2026-09-17) â€” why 44 of 261 trades are not taken causally

Group-1/2/3 lists derived by diffing the pad=2 miss list (44) against the pad=12 miss list (34):

**GROUP 1 â€” Walk-state latency: 16 trades** `#17, 23, 61, 68, 72, 75, 92, 112, 115, 133, 141, 147, 184, 215, 220, 227`
- Signal EXISTS at the entry bar (forming-swing mark fired, window + regime + direction all correct). The blocker is the LTF walk itself: the PREVIOUS trade is still open / its trail exit lands within bars of the new entry bar, so `busy_until` blocks the new signal.
- Worked example â€” REF trade #17 (16-May-2023 00:45 IST SHORT B2 @ 27380.8):
  - pad=2: signal present (B2-down 00:45 from forming swing 78: B1 23:45, B2 00:45); chop 59.7 -> b2 regime; b2 window SHORT open since 10-May covering the bar. NOT taken â€” the 14-May short (FLIP, r=-0.981, trail) was still unwinding; its trail exit lands at/after the entry bar -> busy_until blocks.
  - pad=12 (3h discovery): taken. dts=0, entry price 27380.8 == baseline entry price EXACTLY -> R parity holds.
- Live handling: these are taken a few bars late (sim rerun discovers them once the previous trade unwinds). Entry price identical to baseline in this sample, so R is not lost â€” only the execution is later. Current live stale guard (2 bars) must be reviewed against this class.

**GROUP 2 â€” HTF candle-close timing: the hard core of the remaining 34**
- A 1h flip/B2 mark is stamped at the mark candle, but the window legitimately opens when the 1h candle CLOSES (up to 1h later). Same for the chop-regime value at the LTF gate (the containing 1h bar finalizes only at its close). The retro backtest uses the final values; live at the entry bar may still see the OLD window/regime -> direction or regime check fails.
- This is the designed cost of trading on a candle-close basis (user flagged it upfront). Partial recovery is possible by entering when the 1h candle closes (late entry, slightly different price); the rest is genuinely untakeable in real time.

**GROUP 3 â€” Walk-state divergence (minor, overlaps Group 2's remainder)**
- The causal chain's earlier trades differ slightly from the retro chain (different busy_until/cooldown/streak sequence). Occasionally a signal falls inside a busy window causally but was free retroactively. Small count; resolves only via the sequential one-pass study.

Trade #17 note: signal, window, regime, direction all correct; only the walk's busy state differed. This is why Group 1 trades keep their exact R when recovered.

### C12. STREAK SEMANTICS â€” the engine's streak rule uses outcome-lookahead (measured 2026-09-17, `reexam.py` + `user_streak_r.py`)

- **The rule as coded** (`v18_streak_halt.py:344-356`): simulate the trade first, get its R, count it into `consecutive_losses`, and if it lands as the Nth consecutive loss â†’ **delete the trade itself** (`skip_trade`). Two impossible-in-live behaviors: (a) the decision needs the trade's OUTCOME before entry; (b) at slice edges an OPEN trade's provisional R is counted as a loss.
- **User's rule (spec):** count CLOSED trades only (the walk is sequential so prior trades are always closed at the next signal). After 3 consecutive CLOSED losses â†’ **take the 3rd loss, book it, then skip exactly the NEXT signal, then resume.** Fully causal.

**Measured, full history (same engine otherwise, net of Bybit costs):**

| Streak semantics | Trades | Gross | Net | W/L |
|---|---|---|---|---|
| Engine as-is (lookahead) | 261 | +445.6R | **+399.6R** | â€” |
| No streak at all (`max_consecutive_losses=0`) | 407 | +313.8R | **+235.2R** | 119/288 |
| **User rule exactly (closed-only, skip-one)** | **333** | +216.1R | **+152.0R** | 97/236 (29%) |

**Diff decomposition of the engine's 147 lookahead deletions (reexam.py):**
- **43 trades had closedStreak==2** at entry â†’ user rule says TAKE (book the 3rd loss). Engine deleted them all. Group total: **-37.13R** (they're losses â€” the engine's advantage was never booking them).
- **104 trades had closedStreak>=3** â†’ user rule skips these anyway (skip-one) â†’ engine deletion roughly aligned with the user design.
- Reverse violations (engine KEPT a trade the user rule would skip): **1 only** â€” 2024-12-24 19:00 long, closedStreak=3, +1.497R (the engine kept it because lookahead saw a winner; a causal rule skips it).
- Correction of earlier claims: earlier "Type A = 45" was wrong (real count: 1); earlier example timestamps quoted from slice runs (00:45/12:30 IST) were artifacts of the fresh-PSE chain mismatch â€” the full-history continuous chain's trades (02:00 timestamps) are the authoritative ones.
- Worked examples (full-history chain): 2023-03-31 02:00 LONG @ 28093.2 (B2-up first tradeable mark of swing#185, regime=flip, closedStreak=2 â†’ user: TAKE, book -0.959R; engine deleted). 2023-02-01 02:00 SHORT @ 23089.5 (swing#60, closedStreak=2 â†’ user: TAKE; engine deleted; but see C13 â€” under the abandon-swing rule this swing yields no trade anyway).

### C13. FCFS / ABANDON-SWING â€” engine takes later marks from a swing whose first tradeable mark was filtered out (measured, `reexam.py` section [6])

- **Engine behavior** (`btc_engine.py:170-283` signal collection): `first_added_for_this_swing` is set ONLY when a mark passes ALL filters. A mark rejected by the HTF window-direction filter does NOT consume the swing's first-come slot â†’ a LATER mark on the same swing (opposite direction, matching the window) still gets traded.
- **User's design:** the first tradeable mark (B2/FLIP) decides the swing's fate â€” if it mismatches the HTF bias, the swing is abandoned; later marks from the same swing are NOT traded.
- **Correction of the other bot's claim:** it said the flag blocks the flip after a window-mismatched B2 ("live and backtest agree, no trade"). Wrong mechanism â€” the flag never fires on filtered marks; the streak-OFF run DID trade the 02:00 flip short on swing#60. But its conclusion is right **for the user's design**: swing#60 yields no trade under abandon-swing.
- **Measured impact (streak-OFF run):** **93 of 407 trades (+26.06R)** come from swings where an EARLIER tradeable mark existed (and was filtered out). Under abandon-swing these would not be taken. Caveat: the earlier mark may have failed ext_stop or cooldown rather than window-mismatch â€” user must rule whether ANY failed first mark abandons the swing, or only window-mismatch.
- **Spec question (user):** (a) abandon on window-mismatch only, or on any failed first tradeable mark? (b) does a filtered B1 (arm-only, not tradeable) count toward abandonment? (Default assumption: B1 never abandons â€” it is not an entry signal.)

### C12/C13 STATUS:
- **C12**: âœ… FIXED (commit `375d9c4`). Every trade booked, including Nth loss. After N losses â†’ `halt_skip_next=True`, skip next entry, reset. Verified: internal counter never exceeds halt. Smoke + integrity tests pass.
- **C13**: OPEN â€” partially landed (`6b14494` for pre-FS skip). FCFS scope ruling still needed.
- Re-measure the full-history net-R with C13 ruling + rebuild sequential one-pass study for final live-expected number.

---

## LIVE_STUFF PENDING CHANGES (do AFTER backtest is fully fixed)

**Date:** 2026-09-17

### LIVE-1: Streak halt logic (backtest fix DONE, live needs update)

- **Backtest fix applied:** `v18_streak_halt.py` â€” streak logic now correctly: (a) BOOKS every trade including Nth loss, (b) sets `halt_skip_next=True` after Nth loss, (c) skips NEXT entry before resetting. Internal `consecutive_losses` never exceeds halt. Verified with assertion test.
- **Live params need update:** `backtest/engine/v18_params.py` line 45 â€” `max_consecutive_losses: 3` for BYBIT. Sweep shows **halt=5 gives +128.1R vs +114.1R with halt=0 (best PF 1.29)**. Change after backtest is final.
- **Live_loop.py:** the streak logic in `live_loop.py` is separate from `v18_streak_halt.py`. The live loop does NOT use `v18_streak_halt.py` directly â€” it has its own trade tracking. Need to check if live_loop has the same bug. (Deferred.)

### LIVE-2: timeCap="09:29" Nifty leftover in PersistentSwingEngine

- **Bug:** `backend/src/firstswing.py:73` defaults `timeCap="09:29"` (Nifty session gate). BTC is 24/7.
- **Backtest override:** `btc_swing.py:54` forces `timeCap="00:00"` â€” backtest is correct.
- **Live does NOT override:** `live_loop.py:94-95` creates PersistentSwingEngine without `timeCap` â†’ gets "09:29" â†’ blocks swing declarations before 09:29 IST.
- **Fix needed in live_stuff:** pass `"timeCap": "00:00"` in opts dict for PersistentSwingEngine.
- **Also affected:** `parity_report.py:77` (same missing override).

### LIVE-3: Backtest numbers changed with streak fix âœ… FIXED (2026-09-17)

- **Verified numbers (fixed streak, halt=3, slbuf=0.10):** 375t, +305.5R gross, +216.9R net (after costs), PF 2.29, 29.6% WR
- **Per year:** 2023: +48.4R net, 2024: +63.4R net, 2025: +38.8R net, 2026: +66.3R net
- **Old numbers (broken streak):** halt=0 â†’ 261t +470.5R, PF 4.71 (INVALID â€” deleted losses)
- **Smoke test:** All checks pass (375t/+305.5R assertions)
- **Commit:** `375d9c4`

---

## NEW OPEN ISSUES FROM C13 FCFS REVIEW (2026-09-17 â€” code review of the abandon-swing implementation)

**C13 implementation status:** landed in working tree (uncommitted) â€” `btc_engine.py` `_collect_signals`: `first_added_for_this_swing` â†’ `swing_done`, set on EVERY exit path of a tradeable mark (pass or fail). B1 never abandons. Smoke updated: **301t / +292.6R gross (fine fills, cd=10), PF 2.55, WR 29.9%, all years positive â€” PASS.** Mechanics verified correct for: window-mismatch FCFS (1-Feb swing#60 case now yields no trade âœ“), dedup-consumed marks âœ“, B1 exemption âœ“, HTF windows unaffected (v7/v18 use `selection="stream"`) âœ“.

### C13a. Pre-FS first mark abandons the swing â€” **FIXED 2026-09-17 (`6b14494`), re-verified 2026-09-26** ~~OPEN, needs USER RULING~~
- **RULING MADE:** a pre-FS first tradeable mark (a) does NOT abandon the swing â€” it is **skipped**, and the swing stays alive for later post-FS marks.
- **Status:** FIXED and committed (`6b14494`, ancestor of HEAD). Verified in source: `btc_engine.py` L280-282 `continue`s without setting `swing_done`.
- **The "+45.9R cost" figure below is HISTORICAL** â€” it described the pre-fix abandon behaviour and is superseded.

- **The implementation** abandons the swing when the FIRST tradeable mark fails ANY check â€” including the pre-FS filter (`b_time < prev_confirmed_time` â†’ `swing_done=True`).
- **The problem:** per the user's own strict rule ("each trade only when prev swing FS is there"), a mark that fires BEFORE prev-FS is not tradeable live â€” but if the FS confirms in between, a LATER mark on the same swing (post-FS) IS tradeable live. The implementation kills the whole swing at the pre-FS mark â†’ the engine skips FLIPs the user could actually have taken live.
- **User's literal words only cover both-before-FS:** "if b2 and flip are before fs of prev swing then we don't trade the opportunity is already gone... we skip that swing." The mixed case (B2 pre-FS, FLIP post-FS) is unstated.
- **Cost measured:** the FCFS removal set is net **+45.9R** (365â†’301 trades, +338.5â†’+292.6R gross on the cd=10 fine-fill chain) â€” the rule as implemented COSTS R; it is design-fidelity, not profit. If pre-FS should only SKIP the mark (not abandon), some of that comes back.
- **RULING NEEDED:** does a pre-FS first tradeable mark (a) abandon the swing (current impl), or (b) just be skipped, swing stays alive for post-FS marks?

### C13b. Data-infrastructure failures also abandon the swing â€” **FIXED 2026-09-17 (`6b14494`), re-verified 2026-09-26** ~~OPEN (minor)~~

- `not b_time`, trimmed-candle `store.by_date()` miss, missing store data â†’ `swing_done=True`. These are data artifacts, not trading decisions.
- Impact â‰ˆ 0 on the full-history baseline (data complete, store holds everything). BUT the replay/parity slices (rolling 30d windows) will over-abandon at window edges â€” the parity harness must not inherit this behavior blindly.
- **Action when we get to it:** in slice/replay contexts, only abandon on real filter failures; treat store-miss as "cannot evaluate" (skip mark, keep swing alive) or pre-pad windows.

### C13c. Legacy `selection="final"` breaks under abandon â€” OPEN (legacy-only)

- For `selection="final"`, marks whose kind â‰  the swing's final break_kind are rejected â†’ now they ABANDON the swing â†’ the swing's intended final mark is never collected. That inversion breaks "final" selection entirely.
- **Our pipeline is unaffected** (v18 line 141 and v7 line 29 both use `selection="stream"`; v7's `entry_selection` defaults to "stream"). Only legacy engines (v1â€“v13 with `entry_selection="final"`) would break if ever reused.
- **Action when we get to it:** for `selection="final"`, non-matching-kind marks should `continue` WITHOUT setting swing_done (restore old behavior for that branch only).

### C14. ext_stop_r uses future HTF entry price (backtest only) â€” **PARTIALLY FIXED; known-acceptable residual, re-verified 2026-09-26** ~~OPEN (minor)~~
- **Resolved for the regime gate:** the C14 chop-regime lookahead (bottom of this file) IS fixed. This entry is a *different, narrower* residual: `pe` is the HTF window's stored entry price, used only to normalise the ext-stop distance. It remains the current, deliberate behaviour and is consistent across engine versions.
- **Status:** accepted-as-is. It is a signal *filter*, not a trade trigger, and does not change realized trade outcomes in any measured way.

- **File:** `v18_streak_halt.py:184-188`
- **Bug:** `ext_stop_r` check compares 15m bar close against `pe` (1h bar's close price). For 15m bars within the same 1h bar as the HTF entry, the 1h close hasn't happened yet â€” it's future data. v7_timecap uses the 1h bar's `close` as `entry_price` (v7:65), which is the 1h close. 15m bars inside that same 1h window trade on this unknowable value.
- **Impact:** Low. Affects first 3-4 fifteen-minute bars after an HTF entry fires. The ext_stop is a filter (skips signals), not a trade trigger. The 1h intrabar move is small relative to 1.5R threshold. Measured: ~0.5-2% of 15m bars affected per HTF entry.
- **Fix options:**
  1. Shift interval start to next 1h bar (like v13 does) â€” most conservative
  2. Use `candles_htf[j]["open"]` as proxy for HTF entry at signal time
  3. Accept as negligible (current behavior â€” consistent across 7+ engine versions)
- **Severity:** Low â€” doesn't change trade outcomes in any measurable way.

### P1. cooldown_bars 0â†’10 committed as a strategy param change â€” OPEN, needs USER RATIFICATION

- Commit `d25113f` ("feat: Bybit Perp cooldown_bars=10 (+33R improvement)") changed the user's tuned Bybit param set (cd=0 â†’ cd=10) in `v18_params.py` + `btc_routes.py`, based on the bot's own sweep (`sweep_halt_cooldown.py`, untracked).
- The user's tuned set had cd=0 (explicitly swept earlier). A param change of this size is a strategy decision â€” verify the sweep was run on the baseline chain (`_compute_swings continuous`, same as smoke) and ratify explicitly, or revert to the tuned set.
- Note: cd also interacts with the LIVE loop's own cooldown logic (LIVE-1) â€” both must move together.

### P2. Process hygiene â€” OPEN

- Untracked files to review/clean before the next commit: `sweep_halt_cooldown.py`, `verify_abandon.py`, `.kilo/plans/1789638356895-v18-streak-repainting-fix.md`.
- The C13a/C13b/C13c/P1 resolutions must land with regression tests (abandon-reason attribution test â€” which filter killed which swing â€” currently missing from `verify_abandon.py`, which only counts multi-mark swings).
- After rulings: re-measure full history (fine fills) â†’ new baseline â†’ re-run causal/parity measurement against it â†’ sequential one-pass study â†’ final live-expected number.


---

## DEEP-DIVE AUDIT FINDINGS #2 (2026-09-17, full gate-path lookahead hunt) â€” ~~ALL OPEN~~ ALL THREE NOW FIXED (re-verified 2026-09-26)

Audit scope: every place the backtest touches data. Verified CAUSAL (clean): LTF walk (SL-before-ratchet ordering, gap fills at bar open), trail events (activate at confirmed_at_idx/time, pivot known at confirm), fine 1m fills (chronological, conservative intra-bar rules, gap realism), ATR (trailing window), entry price (signal bar close), v7 HTF walk, pre-FS filter, dedup, streak fix. The three findings below are all in the HTF GATE path.

### C14. Chop regime gate looks ahead up to 45 minutes â€” **FIXED, re-verified in source 2026-09-26** ~~OPEN~~
- **Fix APPLIED (not pending):** `v18_streak_halt.py` L269 builds `candle_ts_htf_close=[t+3600 for t in candle_ts_htf]`; L272 selects with `bisect_right(candle_ts_htf_close, ts+900)-1`. Only a **closed** 1h candle can set the regime. The 'PENDING user go-ahead' line at the bottom of this file is **stale and superseded** â€” the code landed.
- **Regression:** `test_c14_c15_gates_present` PASS.

- **Code:** `v18_streak_halt.py:134-137` â€” `j = bisect_right(candle_ts_htf, ts) - 1` where `ts` is the LTF bar's OPEN label; candle labels are bar OPEN times (flip at 18:30 is knowable at 19:30).
- **Bug:** the selected 1h bar may still be RUNNING at the LTF entry instant. `_chop_series_1h` computes chop[i] from bar i's FULL OHLC â€” knowable only at its close (label + 60 min). For LTF bars in the first 45 min of each hour, the regime gate (flip vs b2) uses the running 1h candle's FINAL chop = up to 45 min of future data. Only the last 15m bar of each hour has a completed 1h candle.
- **Fix:** bisect on 1h CLOSE times (open + 3600) against the LTF bar's close instant (ts + 900).
- **Measured (full history, fine fills, slbuf=0.01):** retro gate 367t gross +340.0R / net +265.5R (coarse cost model) vs C14-fixed 361t / gross +368.4R / **net +296.3R** â€” the fix is +30.8R net AND causal (the retro gate was misclassifying the regime at hour boundaries and taking bad trades). Pure win â€” adopt unconditionally.

### C15. HTF window gate looks ahead up to 60 minutes â€” **FIXED, re-verified in source 2026-09-26** ~~OPEN~~
- **Fix APPLIED (not pending):** `v18_streak_halt.py` L539 gates in knowable-instant space â€” `if not (s + 2700 < bar_ts <= e + 2700): continue` â€” and the union branch L513 uses `(s+2700<bar_ts<=e+2700)`. LTF signals inside the flip candle's own hour are correctly rejected.
- **Regression:** `test_c14_c15_gates_present` PASS, `test_c15_count_band` PASS (351 trades within [346,356]).

- **Code:** `to_intervals` builds windows `[entry_ts, exit_ts]` where `entry_ts` = the HTF flip bar's OPEN label; the LTF gate (`if not (s < bar_ts <= e): continue`) admits LTF bars inside the flip candle's own hour â€” but the flip is only knowable at that candle's CLOSE (entry_ts + 60 min for 1h).
- **Fix (measured):** gate in knowable-instant space â€” window covers LTF bars whose CLOSE instant is within [flip_close, exit_close]: `if not (s + 2700 < bar_ts <= e + 2700): continue` (2700 = 3600 - 900).
- **Measured (slbuf=0.01):** C14+C15 = **335t / gross +285.3R / net +216.3R (coarse cost model)** vs C14-only 361t / +296.3R net. The causal window-availability rule costs ~80R net â€” this is the honest price of the user's design (window opens at the flip candle close; signals inside the flip hour are genuinely not takeable live; user anticipated: "so many trades we might not take them").
- **Note:** the window END is causal already (the HTF trade's exit happens in real time). Only the start was retro.

### L1 re-measured: open-window drop has ZERO impact on the batch backtest â€” note (no action)

- The `to_intervals` open-window drop (line 106) was re-tested on the full-history continuous chain: results IDENTICAL to the current engine (the 1-Feb 02:00 case is gated by a CLOSED window on this chain â€” the 31-Jan 00:30 short exits 02-01 03:30; the earlier slice-based finding was a fresh-PSE chain artifact).
- The open-window = active-bias rule (user's model) still matters for the CAUSAL/sequential pipeline (live walk-state differs) â€” keep it in the sequential-study spec, no batch change.

### New honest baseline (pending C14+C15 adoption, slbuf=0.01): ~335t / +285.3R gross / ~+216.3R net (coarse) / ~+240R net (fine-fill estimate) â€” **SUPERSEDED 2026-09-26, see REBASELINE below**
- sl_buf_atr=0.01 confirmed already applied in committed params (v18 default A-run = 0.01 signature).
- Decision recorded: adopt C14 (pure win) + C15 (causality cost accepted). **STATUS 2026-09-26: BOTH LANDED.** The `+285.3R / +216.3R` figure above is the historical pre-adoption measurement and is superseded by the current default-basis run of `351t / +211.72R gross / +137.33R net`.


---

## REBASELINE NOTE (2026-09-26) â€” `test_v18_causal_integrity.py` threshold

`backend/tests/test_v18_causal_integrity.py::test_baseline` currently FAILS on
`assert n >= 150.0`. This is a **stale threshold**, not a causality regression.

Measured on the current tree, default `V18_ENGINE` basis
(`mode=b2_vs_flip_chop`, `chop_thresh=58`, `cooldown_bars=10`,
`max_consecutive_losses=3`, `sl_buf_atr=0.01`, `window_end=exit`):

| Metric | Value |
|---|---|
| Trades | 351 (asserted band [346,356] - PASS) |
| Gross | +211.72R |
| **Net** | **+137.33R** (bar now re-anchored to `>= 120.0` - PASS) |
| **Profit factor** | **1.907** (bar re-anchored from `>= 2.0` to `>= 1.80` - PASS) |
| Win rate | 27.6% (97W / 254L) |
| Profit factor | 1.91 |
| Outcomes | sl 147 / trail 204 |
| Yearly | 2023 +38.8 / 2024 +81.1 / 2025 +37.6 / 2026 +54.2 - **all positive** |

### ROOT CAUSE ? PROVEN, NOT A DATA PROBLEM

The bar was calibrated on **2026-09-19** (`a329ff3`, which recorded
`351t/+238.0 gross/+163.7 net` and set `assert n >= 150.0`).

**Two days later, on 2026-09-21, `ee574f9` landed a deliberate correctness fix:**

> TRAIL-EVENT ORDERING FIX: ratchet before SL check ? all numbers updated
> The trail ratchet now fires BEFORE the SL check on the same bar, matching
> live-faithful behavior (stop armed at activation instant). Coarse identity
> anchor unchanged (340t/+225.3R). **Fine-fill experiments shift ~-26R.**

The test threshold was **never re-anchored** after that fix ? confirmed by
`git log d19a854..HEAD -- backend/tests/test_v18_causal_integrity.py`, which shows
only `a329ff3` (dated 2026-09-19, *before* the fix).

**Data was ruled out.** The Bybit CSVs are gitignored, so a git diff is impossible,
but a direct inspection shows they are pristine and unchanged in extent:

| tf | rows | gaps | dup timestamps | NaN OHLC | span |
|---|---:|---:|---:|---:|---|
| 1m | 1,946,042 | 0 | 0 | 0 | 60..60 |
| 15m | 129,736 | 0 | 0 | 0 | 900..900 |
| 1h | 32,434 | 0 | 0 | 0 | 3600..3600 |

Range is still `2023-01-01` -> `2026-09-13 10:02`, identical to the pre-fix period.

**Direct proof by running the PRE-FIX engine against TODAY's data:**

| Engine | Data | Trades | Gross | Net |
|---|---|---:|---:|---:|
| `ee574f9^` (pre-fix) | today | 351 | +238.03 | **+163.66** |
| `ee574f9` / HEAD (post-fix) | today | 351 | +211.72 | **+137.33** |
| **delta** | identical | **0** | **-26.31** | **-26.33** |

Same data, same trade count, -26.3R. This exactly matches the commit message's
predicted "~-26R" and reproduces `a329ff3`'s recorded pre-fix anchor
(+238.0 gross / +163.7 net) to the decimal.

**Interpretation: the fix made the backtest MORE honest, not less.** Pre-fix, the
trail ratcheted *after* the SL check, so a trade whose structural stop tightened on
a given bar got one extra bar of slack before being enforced ? slack that does not
exist live, where the stop is armed at the activation instant. The pre-fix +163.66R
was therefore optimistic by ~26R. **+137.33R is the correct post-fix number**, and
the `>= 150.0` bar is simply a pre-fix leftover.

| Metric | PRE-FIX (`ee574f9^`) | POST-FIX (HEAD) | old bar | new bar |
|---|---:|---:|---|---|
| Trades | 351 | 351 | [346,356] | [346,356] (unchanged) |
| Gross | +238.03 | +211.72 | - | - |
| Net | +163.66 | +137.33 | `>= 150.0` | **`>= 120.0`** |
| Profit factor | 2.020 | 1.907 | `>= 2.0` | **`>= 1.80`** |
| Win rate | 27.6% | 27.6% | 25-40 band | unchanged |

**RESOLVED 2026-09-26.** BOTH bars were pre-fix leftovers. The old `>= 2.0` PF bar
cleared the pre-fix 2.020 by only **0.02** - it was never a robust alarm. Both bars
were re-anchored with the user's approval: net `150.0 -> 120.0` (~13% headroom below
the correct +137.33) and PF `2.0 -> 1.80` (~5.6% headroom below the correct 1.907).
The rationale is in-code at `backend/tests/test_v18_causal_integrity.py:90-108`.

**Suite result after re-anchoring: ALL 5 TESTS PASS**
```
PASS: 5 losers booked, 6th skipped, winner resumes
PASS: C14+2700 gates present in source
PASS: trade count 351 within [346,356]
PASS: 351t gross +211.7 net +137.3 WR 27.6% PF 1.91
PASS: sl=147 trail=204 WR=27.6% (broken was 45%)
ALL v18 BACKTEST INTEGRITY TESTS PASSED.
```
Note win rate is **identical** pre- and post-fix at 27.6% - the trail-ordering fix
changed only exit *magnitude* on runners, not the win/loss split. That is exactly
the expected signature of a correctness fix rather than a behaviour regression.

**Interpreter note:** the default `python` (3.10) lacks pandas. Run this suite with
`C:\Users\Pravin\AppData\Local\Programs\Python\Python312\python.exe`.
