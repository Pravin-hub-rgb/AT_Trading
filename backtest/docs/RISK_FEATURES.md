# Risk Features — Implementation & Decisions

**Date:** 2026-09-12
**Status:** Code-side risk features complete

---

## What We Implemented

### 1. Margin Mode — Isolated (DONE)

**What:** Each position has its own dedicated margin. If one position gets liquidation, only that margin is lost. Other positions and account balance are protected.

**Why:** Bybit UNIFIED accounts default to Cross Margin (all positions share margin pool). One bad liquidation could wipe the entire account. Isolated is the professional choice for risk-based bots.

**Files changed:**
- `config.py` — Added `MARGIN_MODE = "isolated"`
- `bybit_order.py` — Added `set_margin_mode()` method (calls Bybit API `switch_margin_mode`)
- `main.py` — Calls `set_margin_mode()` on startup after `set_leverage()`

**Verified:** pybit has `switch_margin_mode(**kwargs)` method. Parameters: `category`, `symbol`, `tradeMode` (0=Cross, 1=Isolated), `buyLeverage`, `sellLeverage`.

---

### 2. Daily Loss Limit (DONE)

**What:** Auto-halt trading if daily losses exceed `risk_inr × DAILY_LOSS_MULTIPLIER`. Resets at midnight UTC.

**Why:** The streak halt (5 consecutive losses) doesn't protect against losses spread across a day with wins in between. Daily limit catches bad days regardless of trade order.

**Multiplier choice: 5x**
- Matches the streak halt threshold (5L) but on a time basis
- With ₹250 risk: daily limit = ₹1250
- 2x would be too tight (triggers after 2 consecutive losses — normal variance)
- 5x allows natural strategy variance while catching genuinely bad days

**Files changed:**
- `config.py` — Added `DAILY_LOSS_MULTIPLIER = 5`
- `live_loop.py` — Added `_daily_pnl_r`, `_daily_halted`, `_last_trade_date` tracking variables
- `live_loop.py` — Added `_check_daily_loss_limit(r_mult)` method
- `live_loop.py` — Added check after every trade close (cap, SL/trail, TP, journal)
- `live_loop.py` — Added halt check in `_execute_entry()` (skip entries when halted)
- `telegram_alert.py` — Added `daily_halt()` alert method

**How it works:**
1. On each trade close, add R multiple to daily PnL (only counts losses)
2. If cumulative daily loss ≤ `-(risk_inr × 5)`, set `_daily_halted = True`
3. New entries skipped when halted
4. Resets automatically on new UTC day
5. Telegram alert sent when breached

---

## What We Rejected

### 1. Max Drawdown Kill-Switch — REJECTED

**What it would do:** Halt trading if total equity drops by a fixed percentage (e.g., -15%) from peak.

**Why rejected:**
- v18 has a **35% win rate** — drawdowns are a natural, expected part of the strategy
- Losing streaks of 5+ trades are normal and designed to be absorbed
- A -15% kill-switch would halt right **before** the recovery (the algo's edge IS absorbing drawdowns)
- Would cut the strategy's natural variance short
- Fights against the strategy's design rather than protecting it

**Conclusion:** Not suitable for low-win-rate, high-R:R strategies like v18. The daily loss limit + streak halt already provide time-based and consecutive-loss protection.

---

### 2. Rate Limit Handling — SKIPPED (not needed)

**What it would do:** Throttle API calls to stay under Bybit's 10 req/s limit.

**Why skipped:**
- Bot makes ~1-2 API calls per trade entry/exit
- Plus occasional status checks
- Would need 10+ trades per second to hit the limit
- Impossible with this algo (trades are 15m+ apart)

**Conclusion:** Not a real constraint for this strategy.

---

## Existing Protection (Already Built)

| Feature | Where | What it does |
|---|---|---|
| **Streak Halt 5L** | `live_loop.py:_persist_streak_halt()` | Halts after 5 consecutive losses, resumes on next winner |
| **Cooldown 20** | `live_loop.py` | 20-bar (5h) cooldown after every loss |
| **Max Leverage 3x** | `config.py` | Hard cap, rejects trades implying >3x leverage |
| **Balance Safety 95%** | `config.py` | Never uses more than 95% of available balance |
| **Position Sizing** | `live_loop.py:_calculate_qty()` | Risk-based sizing: `qty = risk_usdt / (|entry - sl| + fee_buffer)` |
| **Isolated Margin** | `bybit_order.py:set_margin_mode()` | Each position's margin is separate |
| **Daily Loss Limit** | `live_loop.py:_check_daily_loss_limit()` | Max 5R loss per UTC day |

---

## Summary

| Feature | Status | Reason |
|---|---|---|
| Margin mode (Isolated) | ✅ Implemented | Safety — prevents cascade liquidation |
| Daily loss limit (5x) | ✅ Implemented | Catches bad days, not just consecutive losses |
| Max drawdown kill-switch | ❌ Rejected | Fights strategy's natural variance (35% win rate) |
| Rate limit handling | ⏭️ Skipped | Not a constraint for this algo |

---

**Next steps:** Deploy to VPS, run on Bybit demo, forward test for weeks, daily parity check vs backtest.
