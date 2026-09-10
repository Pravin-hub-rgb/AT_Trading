# Live Trading Engine — Design Challenge

## Problem Statement

Design a **production-grade live trading engine** that:
1. Produces marks (B1, B2, FLIP) identical to a full-history backtest
2. Runs on a small VPS (1GB RAM, limited storage)
3. Survives restarts, downtime (hours to weeks), and network gaps
4. Tracks open trades (bias, SL, 3R, 16-day exit) across restarts
5. Is verifiable: an endpoint returns marks for any date, comparable with backtest chart

---

## Context: The Trading System

### Instruments & Timeframes
- **BTCUSDT** (Binance spot/futures)
- **15m** and **1h** timeframes
- Both TFs run in parallel, independent chains

### Marks (Entry Signals)
The walker detects three types of swing breaks:
- **B1** (Breakout 1): First break of a swing extreme — continuation
- **B2** (Breakout 2): Second break — stronger continuation
- **FLIP**: Break in opposite direction — reversal

Each mark has: {timestamp, kind, direction, price, swing_no, swing_kind}

### Trade Lifecycle
1. **Entry**: A mark fires (rules below — which marks enter?)
2. **Stop Loss (SL)**: Swing extreme or touchable extreme since prev_end
3. **Take Profit (TP)**: 3R (3x the risk distance)
4. **Time Exit**: 16-day max hold (if neither SL nor TP hit)
5. **Exit**: Trade closes, PnL recorded as multiple of R

### Bias Window
- 1h TF determines the  bias (long/short/neutral)
- 15m TF marks are filtered by bias (only trade in bias direction?)
- Bias changes when 1h FLIP fires

---

## CONFIRMED: Entry Rules (from codebase)

### Tradeable Marks
Only **B2** and **FLIP** are tradeable. B1 is NOT traded.

### One Swing One Trade
Only the **first tradeable mark per swing** is taken. After a trade is entered from a swing, all later marks from the same swing are ignored.

### Stream Selection
Marks are processed in chronological order (stream), not just the final mark of a swing.

### MASTER #1 — 1h Flip Fixed 3R (cap 16d)
- **Entry**: FLIP marks only
- **SL**: swing start pivot (seg_start)
- **Target**: 3R
- **Time cap**: 16 days (market exit at cap)
- **Selection**: stream + one-swing-one-trade
- **Result**: 151tr, 39.7% win, +74.0 base → +57.8 net, PF 0.78, maxDD 10.0

### HTF-LTF v18 — Streak Halt 5L
- **HTF (1h)**: Determines regime via Chop Index (14-bar)
  - HIGH chop (>61.8): use B2 entries
  - LOW chop (≤61.8): use Flip entries
- **LTF (15m)**: Decisive (B2 or FLIP) for precise entry
- **SL**: pivot − 0.25·ATR (opposite side)
- **Window**: HTF entry → SL / target / 16-day cap
- **Cooldown**: 20 bars after every loss
- **Streak halt**: Halt after 5 consecutive losses, resume on next winner
- **Result**: 330tr, +331.1R gross, PF 2.81, 4/4 years positive

---

## CONFIRMED: SL Definition (from codebase)

### Standard SL (sl_mode=swing)
- **LONG**: SL = swing start pivot (seg_start)
- **SHORT**: SL = swing start pivot (seg_start)

### Touchable SL (pre-start churn or opposite-dir breaks)
- **LONG**: SL = lowest low since previous swing's end
- **SHORT**: SL = highest high since previous swing's end
- This fixes the 14 Jan 11:30 case: SL = 10:30 high (95465), not 07:45 high (95281)

### HTF-LTF SL (sl_buf_atr=0.25)
- SL = pivot − 0.25·ATR (opposite side)

---

## CONFIRMED: 16-Day Window (from codebase)

### What It Is
- **Max trade duration**: 16 days from entry
- **Exit**: Market exit at the close of the 16th day bar
- **For 1h**: 16 days = 384 bars
- **For 15m**: 16 days = 1536 bars

### How It Works
`
cap_bars = int(cap_days * 86400 / interval)
cap_idx = entry_idx + cap_bars

On each bar j > entry_idx:
  if j >= cap_idx:
    exit at candles[j].close
    outcome = time
`

### Why 16 Days
- Research: cap 16d = +57.8 net (best), cap 0 = +51.2, cap 30d = +50.5
- 27 Jan trade: 114d hold at -1R → capped at 16d = +0.289R (saved a loss)

---

## CONFIRMED: Multiple Trades (from codebase)

### One Trade at a Time
- usy_until: while a window is open, same-kind breaks are ignored
- New window opens only after current trade exits (SL/target/time)

### HTF-LTF Window
- One HTF window at a time
- One LTF trade per HTF window
- After LTF trade exits, next HTF break opens new window

---

## CONFIRMED: Bias Tracking (from codebase)

### Chop Index (14-bar on 1h)
`
CHOP = 100 · log10(ΣTR(14) / (maxHigh(14) − minLow(14))) / log10(14)
`
- **HIGH chop (>61.8)**: Market is choppy → use B2 entries
- **LOW chop (≤61.8)**: Market is trending → use Flip entries

### Why
- In choppy markets, breakouts work better
- In trends, pullbacks to value work better

---

## The Core Problem: Path-Dependence

### What We Discovered

The swing walker is **path-dependent**: the chain depends on where you start.

- Start from **Feb 24, 2026** → one chain
- Start from **March 1, 2026** → different chain initially
- After **3-4-5 months** of running, both chains converge to the same swings

**This means**: a rolling window produces a DIFFERENT chain than full history, so marks fall on wrong bars.

### Research Results

We tested rolling windows vs full-history (129,306 candles of 15m data):

| Window Size | Match with Full History | Result |
|---|---|---|
| 50 candles (~5 hours) | 4/28 marks match | ❌ MISMATCH |
| 100 candles (~10 hours) | 10/28 marks match | ❌ MISMATCH |
| 200 candles (~20 hours) | 26/28 marks match | ❌ MISMATCH |
| **300 candles (~3 days)** | **28/28 marks match** | ✅ OK |
| 500+ candles | 28/28 marks match | ✅ OK |

**For 1h data** (32,336 candles total):
- Minimum window: **150 candles** (~6 days)
- Safe window: **200 candles** (~8 days)

### The Rolling Window Dilemma

**Approach 1: Full History**
- ✅ Marks match backtest exactly
- ❌ 129k candles = ~50MB storage, slow boot
- ❌ Not feasible for small VPS
- ❌ Wastes resources on old data we don't need

**Approach 2: Rolling Window**
- ✅ Lean (500 candles = ~25KB)
- ✅ Fast boot
- ❌ **When oldest candle falls off, chain rebuilds**
- ❌ A big volatility candle falling off CAN change recent marks
- ❌ This is unacceptable for real money trading

**The user's concern**: if there is some volatility candle big one that might change it completely man... a single tick missed is going to cost a lost to be honest here so this is not joke

---

## Requirements

### Functional
1. **Marks must match backtest** — identical timestamps, kinds, directions, prices
2. **Immutable journal** — once a mark is recorded, it NEVER changes
3. **Trade state persistence** — open trades survive restarts
4. **Catch-up on restart** — download missing candles, process in order, emit marks
5. **SL/TP/16d monitoring** — check every candle, close trades correctly
6. **Verification endpoint** — return marks for any date, comparable with backtest

### Non-Functional
1. **Storage**: < 100KB for rolling windows + marks
2. **Memory**: < 100MB RAM usage
3. **Speed**: < 10ms per candle processing
4. **Downtime tolerance**: Handle hours, days, weeks of downtime
5. **No ambiguity**: Every mark and trade is deterministic and auditable

### Constraints
- **VPS**: 1GB RAM, small storage, Linux
- **Data source**: Binance REST API (no WebSocket dependency)
- **Polling**: Every 60 seconds for new closed candles
- **No external dependencies**: SQLite only (no PostgreSQL, no Redis)

---

## What We've Tried

### Attempt 1: Full History Seed
- Load all 129k candles from CSV on boot
- Chain matches backtest exactly
- **Problem**: Slow boot (~30s), high memory, not VPS-friendly

### Attempt 2: Rolling Window (naive)
- Keep last 500 candles, recompute chain on every new candle
- **Problem**: Marks change when volatile candles fall off

### Attempt 3: Rolling Window + Immutable Journal (current best)
- Keep last 500 candles
- On each new candle: compute chain, emit marks for THIS candle only
- Journal is append-only — past marks never change
- **Problem**: The mark on candle X is computed with a 500-candle window, not full history. Is this accurate enough?

### Research Validation
- 500-candle window reproduces full-history marks for the tail 200 candles ✅
- But the user is concerned about edge cases with volatile candles

---

## The Real Question

**How do we guarantee that a mark fired in live trading is IDENTICAL to the backtest mark, while keeping storage lean and handling restarts gracefully?**

This is the core design challenge. We need a solution that:
1. Is mathematically proven to produce correct marks
2. Handles the volatile candle falls off edge case
3. Survives any downtime duration
4. Tracks trades correctly across restarts
5. Runs on a small VPS

---

## Existing Solutions to Research

We want to know how other trading systems solve this:

1. **MetaTrader 4/5** — How do they handle indicator recalculation on new ticks?
2. **TradingView Pine Script** — How do they handle security() calls with different timeframes?
3. **QuantConnect / Lean** — How do they handle warm-up and rolling windows?
4. **Freqtrade** — How do they handle data persistence and restarts?
5. **Hummingbot** — How do they handle order book state across restarts?
6. **Backtrader** — How do they handle cerebro.run() with live data?
7. **Zipline** — How do they handle the handle_data() rolling window?
8. **Custom institutional systems** — What do prop shops do?

**Specific questions to research:**
- How do they handle path-dependent indicators in live trading?
- How do they ensure live signals match backtest signals?
- How do they handle the last N bars problem when old data falls off?
- How do they persist state across restarts?
- What data structures do they use for speed?

---

## Deliverables Needed

1. **Architecture**: Complete system design (data flow, state management, persistence)
2. **Data Structures**: Exact structures for candles, marks, trades, state
3. **Algorithms**: Chain computation, mark detection, SL/TP checking, catch-up
4. **Storage Schema**: SQLite schema (or alternative)
5. **API Design**: Verification endpoint specification
6. **Edge Case Handling**: Volatile candles, downtime, network gaps, exchange downtime
7. **Proof of Correctness**: How do we prove live marks = backtest marks?

---

## Success Criteria

1. ✅ Live marks match backtest marks for 30+ consecutive days
2. ✅ Bot can be killed and restarted without losing state
3. ✅ Bot can be down for 16+ days and correctly resolve open trades
4. ✅ Storage stays under 100KB
5. ✅ Processing time per candle < 10ms
6. ✅ Verification endpoint returns marks identical to backtest chart
7. ✅ No mark ever disappears or changes after being journaled

---

## Contact

This document is sent to multiple AI systems for analysis. The best solution will be selected based on:
- Mathematical correctness
- Simplicity
- Robustness
- Performance
- Real-world trading experience
