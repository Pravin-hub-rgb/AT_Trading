# Problem Statement — Incremental Sim for Live Trading Bot (for external review)

**Prepared for:** external reviewer / guide
**Project:** `AT_Trading` -> `live_stuff/` (Book 107 live engine)
**Status:** refactor partially complete; seeking guidance on the remaining true O(1)-per-bar work
**Date:** 2026

---

## 1. What this system is

A live trading bot for BTCUSDT running a strategy called **"Book 107"**
(`fsent_champ_long_mcloff_htf15`). It streams 15m and 1h candles from
Binance/Bybit, detects swings on both timeframes, runs a deterministic
simulation over the accumulated history on every 15m close, and journals
trades to SQLite. The bot also places real orders on the exchange.

The simulation is the **authoritative source of truth** for what trades should
exist right now. The live engine re-derives the full trade list from history
each bar, then diffs it against what is already journaled in the DB, opening
new trades and closing finished ones. So every 15m close re-runs the entire
strategy over all accumulated history.

---

## 2. Strategy theory (how we trade)

### 2.1 Timeframes
- **HTF = 1h**, **LTF = 15m**.
- Swings detected on both via a persistent swing engine
  (`PersistentSwingEngine`, zigzag-style, min bars per TF).

### 2.2 HTF side — three independent "regime windows"
On the 1h swings, three independent HTF strategies run (via
`simulate_btc_trades_v7`), each with a different entry-break condition:
- **flip** — trend flip break
- **b2** — second-break (continuation)
- **decisive** — decisive break (used by atr_high books)

Each produces HTF trades. Each trade defines a **window**: `entry_ts .. exit_ts`,
with `dir` (long/short), `entry_px`, `sl`, `hrisk` (risk distance). A window
being "open" means the 1h leg is in the market and LTF entries may follow it.

### 2.3 LTF side — entry detection
On the 15m swings, break marks are collected (`_collect_signals`): kinds B1,
B2, FLIP. Each mark is a candidate LTF entry. Gates applied in order:
1. **Window gate** — open HTF window whose `dir` matches signal dir (window
   selection driven by regime/chop).
2. **Ext-stop gate** — `ext_r` (how far price moved beyond the swing) must be
   `<= ext_stop_r` (default 3.0R), else "late" and skipped.
3. **Regime gate** — chop index vs `chop_thresh` (default 58.0); mode
   `atr_high` routes volatile buckets to the decisive window.
4. **Cooldown gate** — after a losing trade, no new entry for `cooldown_bars`
   (default 8) bars.
5. **Daily halt** — if daily P&L drops below a threshold, halt for the day.
6. **Position limit** — `max_positions` (0 = unlimited in this book).
7. **Consecutive-loss streak halt** — `max_consecutive_losses`.

On pass, an LTF trade opens with SL and TP (`rr_target`, default 3.0R, with
separate `rr_target_short`).

### 2.4 Exits
Each open LTF trade evaluated bar-by-bar against OHLC:
- SL hit -> close (outcome "sl"/"be"/"trail" depending on trailing).
- TP hit -> close (outcome "target").
- Time cap (`cap_days`, default 30 days) -> market exit.
- Trailing stop and breakeven (`breakeven_r`) can ratchet the SL.

### 2.5 Costs / accounting
Fees and slippage subtracted in R. Daily loss limits, cumulative cost
tracking. Gray-leg (replay/seed) trades excluded from live stats.

### 2.6 Book params (Book 107)
chop_thresh=58.0, cooldown_bars=8, ext_stop_r=3.0, htf_rr=3.0,
atr_high_thresh=0.65, atr_low_thresh=0.35, sl_buf_atr=0.01,
window_end='exit', mode='atr_high', pivot_rule='leg',
exp_fs_entry_side='long', exp_persist=7, exp_partial_r=0.0,
max_consecutive_losses=0, max_positions=0

---

## 6. What remains (the open problem)

The incremental driver still calls the batch oracle (`simulate_htf_ltf_streak_halt`)
on the retained window whenever the structural signature changes (new 1h candle
or new swings). The **true O(1)-per-bar** goal — updating state incrementally
without re-running the engine — is not implemented. The plan's Step C design
lists the per-bar state to maintain:

- HTF window state per regime (flip / b2 / decisive): `htf_window_open`,
  `htf_window_dir`, `htf_window_start_ts`, `htf_entry_px`, `htf_sl`,
  `htf_hrisk`, `htf_current_r`.
- Open LTF trades: entry_ts, dir, sl, target, swing_no, htf_regime, cap_ts,
  status; evaluate SL/TP against each bar's OHLC.
- Cooldown counter, consecutive-loss streak, daily P&L R, daily-halted flag,
  last trade date.
- Swing chain (append-only; swings grow slowly).
- Per-bar update order: append 15m candle -> swing engine -> (if 1h closed)
  1h swing engine -> HTF window tracker -> LTF entry detection -> LTF exit
  evaluation -> rolling R / chop / ATR update.

**Parity gate:** incremental trade list must be byte-identical to the batch
sim on the same history (entry_ts, dir, outcome, r_multiple, exit_ts,
exit_price, entry_price, sl, target).

**Constraint:** every state mutation must be re-derivable from DB + candles
(crash recovery). `_journal_trades` dedups by (entry_ts, dir);
`close_ltf_trade` returns 0 if already closed.

---

## 7. Open questions for the reviewer

1. Is the retention approach (trim + re-index + straddle-safe cutoff) sound,
   or does it hide a latent correctness issue we have not caught?
2. For the true O(1) rewrite, what is the smallest correct incremental slice
   to tackle first — HTF window tracking, LTF exit evaluation, or LTF entry
   detection — given the parity gate?
3. The HTF side (`simulate_btc_trades_v7`) is itself stateful (busy_until,
   signal list, exits, trailing). Is there a clean way to make it incremental
   without duplicating the whole engine, or is a parallel reimplementation
   unavoidable?
4. Are there established patterns (event sourcing, incremental view
   maintenance) that fit this "re-derive trade list from history each bar"
   shape better than the current design?
5. Given that retention already brings the sim to ~0.2s, is the true O(1)
   rewrite actually necessary, or is the current architecture sufficient for
   production?

*No prescribed solution is intended here — these are open questions.*
