# Live Sync Fix Plan — v3

## Problem Statement
Freshly seeded live bot produces different marks/trades than the backtest.
Three P0 bugs cause the divergence.

## Design Context (confirmed from docs)

**Handoff approach is correct by design.**
- `live_trading_doc.md:139-143`: User gives a handoff timestamp where they've
  verified the marks on the chart. Swing engine starts FROM that timestamp.
- `live_engine_design_challenge.md:148-152`: Swing chain is path-dependent —
  different start dates produce different chains **initially**, but after
  **3-5 days** of running, both chains converge to the same swings.
- `live_engine_design_challenge.md:160-170`: Minimum convergence window:
  **300 15m bars (~3 days)** / **150 1h bars (~6 days)**. Safe: 500+ 15m / 200 1h.
- The engine does NOT need 2023 full history. A handoff 7+ days back is safe.
- 1h fetches 14 bars before seed **only for ATR/chop warmup**. These must stay
  separate from the candle list used for swing indexing.

## Root Causes

### P0a. 1h lookback bars contaminate `all_candles_1h`
**File:** `live_stuff/live/feed.py:258-313`

14 pre-seed bars go into `all_candles_1h` (line 279), but the swing engine
processes from `engine_start` with `g_idx=0` at the seed bar (line 282-298).
So `all_candles_1h[0]` = 14th lookback bar, but swing `idx=0` = seed bar.

Downstream, `simulate_htf_ltf_streak_halt` (unified.py:755-757) does:
```python
for _s in swings_htf:
    _fi = int(_s.get("fs_at_idx", -1))
    if 0 <= _fi < len(candles_htf):
        fs_up_ts.append(int(candles_htf[_fi]["ts"]))  # ❌ candles_htf[0] = lookback, not seed
```

And `_collect_signals` (btc_engine.py:303-313) slices:
```python
_lo_leg = [c["low"] for c in candles[_sw_idx : _hi_i]]  # ❌ 14 bars too early
```

15m has no lookback → indices aligned. This is why 15m works but 1h doesn't.

### P0b. Seeding trips the daily-loss halt
**File:** `live_stuff/live/signals.py:568`

`_journal_trades` replays ALL historical closed trades during seeding. Closed
trades call `_check_daily_loss_limit(r_mult)` (risk.py:177) — always, no
`_seeding` guard. Historical losses accumulate into `_daily_pnl_r`; if they
breach the 5R daily limit (config.py:59 `DAILY_LOSS_MULTIPLIER=5`),
`_daily_halted=True` persists to DB → blocks all live entries until midnight.

The `_seeding` guard (signals.py:526) only protects `outcome == "open"`.

**Open question:** Does any single day in the 107 backtest produce 5+ consecutive
losses or 5R+ of daily loss? If yes, every fresh seed triggers a halt.

### P0c. No candle dedupe/gap integrity
**File:** `live_stuff/live/loop.py:254-359`

`_on_15m_close`/`_on_1h_close` append candles unconditionally. Reconnect
backfill or restart can duplicate/stale candles, corrupting swing indices.

## Plan

### 1. Fix 1h index alignment (P0a)
**File:** `live_stuff/live/feed.py`

- The 14 lookback bars are for ATR/chop warmup ONLY.
- Do NOT add them to `all_candles_1h`.
- Build `all_candles_1h` from the seed bar onward (same as 15m).
- Keep lookback bars in a transient `_lookback_1h` list for chop calculation.
- On the next 1h close, the ATR window naturally rolls forward — the lookback
  candles stay in memory only during the current bar's chop calculation.

```python
# feed.py:276-313 (1h path)
self.all_candles_1h = candles_1h[engine_start:]  # seed bar onward only ✓
self._lookback_1h = candles_1h[:engine_start]     # ATR warmup, transient
# Don't persist _lookback_1h to DB
```

### 2. Isolate seed accounting (P0b)
**Files:** `live_stuff/live/signals.py`, `live_stuff/live/feed.py`

- In `_journal_trades` (signals.py:546-579): when `_seeding=True` and trade is
  closed, skip `_check_daily_loss_limit` + cost calc. Tag DB `origin="seed_history"`.
- In `_seed_from_timestamps` (feed.py, after line 177 reset): force-reset daily
  state before running `_run_v18_simulation`:
  ```python
  self._daily_pnl_r = 0.0
  self._daily_halted = False
  self._last_trade_date = today
  ```

### 3. Candle dedupe/gap integrity (P0c)
**File:** `live_stuff/live/loop.py`

- Before appending to `all_candles_*`: check `ts` vs last candle.
- If `ts <= last_ts`: replace (stale candle).
- If `ts > last_ts + interval`: backfill gap via REST.
- Reject incomplete candles (`close_time > now`).

### 4. DB/restart policy
- **Fresh seed** (CLI/API with timestamps): clear `swing_state_*` and
  `trading_state.daily_*` from DB. Rebuild from seed point.
- **Crash restart** (DB has state): load `all_candles_*` + swings from DB,
  fetch gap to now, replay. Do NOT reload the 14 lookback bars — they were never
  persisted (per fix #1). The chop window naturally has the last 15 live bars.
- **No auto-delete of entire DB** — only clear swing/daily-state metadata.

### 5. Cleanup
- Delete `live_stuff/docs/seed_marks.json` (dead code, stale Sep 9 Binance data).

### 6. Verification
- Handoff test: seed from `2026-09-26 10:00:00` (15m) / `2026-09-26 16:30:00` (1h).
  1h swings (1441 total) match backtest chain — zero mismatches.
- Daily-halt test: seed with historical trades, verify `_daily_halted=False`.
- Gap/dedup test: inject duplicate + stale candles, verify dedup.
- Restart test: seed → stop mid-stream → restart → same swing chain + open trades.
- Fix `verify_oct24_marks.py` minBars: 50/15.

## Decisions
1. ✅ Handoff timestamps from chart — no 2023 full history needed.
2. ✅ 1h lookback: transient in-memory only, NOT in `all_candles_1h`, NOT in DB.
3. ✅ Seeded history: excluded from daily P&L; tagged `seed_history`.
4. ✅ No full DB wipe on restart — only clear swing/daily-state metadata on fresh seed.
5. ✅ `seed_marks.json`: deleted.
6. ✅ `pivot_rule="leg"` for FS: left as-is (matches pins; re-pinning out of scope).

## Open question
- Does any single day in the 107 backtest (IS + OOS) produce a 5R+ daily loss
  that would trigger the halt during seeding? Needs a backtest run with daily
  P&L tracking.
