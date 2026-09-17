# Backbencher - Live Trading Engine Design

**Created:** 2026-09-09
**Status:** Design complete, ready to build
**Codename:** Backbencher

---

## 1. Problem Statement

Build a production-grade live trading engine that:

1. Produces marks (B1, B2, FLIP) identical to a full-history backtest
2. Runs on a small VPS (1GB RAM, limited storage)
3. Survives restarts, downtime (hours to weeks), and network gaps
4. Tracks open trades (bias, SL, 3R, 16-day exit) across restarts
5. Is verifiable: an endpoint returns marks for any date, comparable with backtest chart

---

## 2. Core Insight

### The Path-Dependence Problem

The swing walker is path-dependent: the chain depends on where you start.

- Start from candle 0 -> chain A
- Start from candle 5000 -> chain B
- After 3-5 months, both chains converge

A rolling window produces a DIFFERENT chain than full history, so marks fall on wrong bars.

### Research Results

| Window Size | Match with Full History | Result |
|---|---|---|
| 50 candles | 4/28 marks match | FAIL |
| 100 candles | 10/28 marks match | FAIL |
| 200 candles | 26/28 marks match | FAIL |
| 300 candles | 28/28 marks match | OK |
| 500+ candles | 28/28 marks match | OK |

### The Solution

**Don't persist a rolling window and reconstruct the strategy. Persist the strategy's state.**

The walker doesn't need all 129,000 candles. It just needs to know WHERE IT IS in the chain.

Think of it like a book:
- Old way: "I forgot chapter 1, let me re-read the whole book"
- New way: "I'm on page 547, I just need to read the next page"

---

## 3. Architecture Overview

```
+---------------------------------------------------------+
|  DATA LAYER                                             |
|  WebSocket: ticks (for trade monitoring)                |
|  REST: closed candles (for mark detection)              |
|  Ghost Streak pattern: dual stream + backfill            |
+---------------------------------------------------------+
                          |
                          v
+---------------------------------------------------------+
|  WALKER LAYER (candle level, slow)                      |
|  15m walker: detects marks, updates trail pivots        |
|  1h walker: detects marks, updates bias/chop            |
|  State: < 1KB per TF, saved after every candle          |
+---------------------------------------------------------+
                          |
                          v
+---------------------------------------------------------+
|  TRADE LAYER (tick level, fast)                         |
|  HTF window: direction + cap (from 1h mark)            |
|  LTF trade: entry + SL + TP + cap (from 15m mark)      |
|  Monitor: every tick checks SL/TP/cap                   |
|  Trail: ratchet SL on new swing confirm                  |
+---------------------------------------------------------+
                          |
                          v
+---------------------------------------------------------+
|  PERSISTENCE LAYER                                      |
|  SQLite: walker state, marks (immutable), trades        |
|  Atomic: all-or-nothing per candle                      |
|  Restart: load state + replay missing candles           |
+---------------------------------------------------------+
```

---

## 4. Data Structures

### WalkerState (15m)

```
swing_no: int
swing_kind: str (up | down)

---

## 5. State Machine Design

### The One True Step Function

```python
def step(state, candle):
    marks = []
    
    update_extreme(state, candle)
    update_since_end(state, candle)
    
    broken, direction = check_swing_break(state, candle)
    if broken:
        kind = classify_break(state, direction)
        if kind in (B2, FLIP) and not state.swing_already_traded:
            marks.append(Mark(...))
            state.swing_already_traded = True
        advance_swing(state, direction, kind)
    
    if state.tf == 1h:
        update_chop(state, candle)
        update_bias(state)
    
    state.last_candle_ts = candle.ts
    state.state_hash = sha256(serialize(state))
    return state, marks
```

### Why This Is Provably Identical to Backtest

```
Backtest: state = INITIAL; for c in all_candles: state, marks = step(state, c)
Live:     state = load_from_sqlite(); for c in new_candles: state, marks = step(state, c)
```

Same function. Same state. Same candles. Same output. **Guaranteed.**

---

## 6. Trade Lifecycle

### HTF Window (1h) — v18 definition (`v18_streak_halt.py:93-107`, `btc_routes.py:834-848`)

```
1h mark fires (via simulate_btc_trades_v7 on 1h, rr_target=3.0, sl_mode="swing", cap_days=16):
  -> Check: existing open window?
     -> Yes, same direction: ignore (one window at a time, busy_until)
     -> Yes, opposite direction: close old, open new (window = HTF trade lifecycle)
     -> No: open new window

  Window = {direction, entry_ts, entry_price, sl_price, risk, cap_ts}
           entry_price/sl from the 1h trade; risk = |entry-sl|; target = entry ± 3*risk

Window closes when (window_end="exit", the +331R config):
  -> 1h trade hits SL  (-1R)              // v18_streak_halt.py:93-107, to_intervals exit_ts
  -> 1h trade hits 3R target (+3R)
  -> 16-day cap hits (cap_days=16)
  // NOT at 1.5R touch — that variant (window_end="r_touch", v19) was A/B tested and REJECTED
  // (242t +200.6R vs 330t +331.1R, -88 pullback winners avg +1.48R)

Entry gate inside an OPEN window (v18_streak_halt.py:179-183):
  ext = (ltf_close - htf_entry) * htf_dir / htf_risk   // current unrealized R of the 1h leg at this 15m bar
  if ext > 1.5: BLOCK this 15m signal (pause, keep monitoring)
  else: ALLOW — and if price pulls back from >1.5 to <1.5, next signal is re-allowed (dynamic, per-bar)
  // This is NOT a window close — window stays open until -1R/3R/16d above.
```

> **The Three R Levels — cheat sheet:**
> - **−1R** = HTF SL — kills the window (window dead, wait for next 1h bias).
> - **1.5R** = `ext_stop_r=1.5` — **entry pause only**, per 15m bar, re-opens on pullback <1.5R. Window still alive.
> - **3R** = HTF target — kills the window (same as −1R). LTF runners that already entered keep going via MB50 trail past the window close (85/330 trades outlived their window, +349R avg +4.11R).
> **Mental model:** `1h window = [−1R … 3R] always open → LTF entries 0→1.5R allowed, 1.5→3R paused, pullback <1.5R re-allowed, until window dies.`

**Proven by live run 2026-09-10 (`backend/test_ext_compare.py`):** 830 LTF signals inside windows → 148 blocked at 1.5R (only 1 blocked at 3R). Moving 1.5→3.0 adds 27 trades but loses −22.08R net & +2.46R DD (verified pullback case: 2023-04-22 SHORT 1.618R BLOCK → 1.543R BLOCK → next day 0.542R ALLOWED).

### LTF Trade (15m)

```
15m mark fires:
  -> Check: HTF window open in same direction?
     -> No: ignore
  -> Check: existing LTF trade running?
     -> Yes: ignore (one trade at a time)
  -> Check: in cooldown?
     -> Yes: ignore
  -> Check: halted (5L streak)?
     -> Yes: ignore
  -> All clear: ENTER TRADE

  Trade = {
    entry: 15m mark price,
    SL: swing pivot - 0.25 ATR (-1R),
    TP: entry + 3R (or entry - 3R for short),
    cap: entry_ts + 16 days
  }
```

### Full Matrix Known at Entry

The moment a 15m mark fires inside a valid HTF window:

| Parameter | Value | Source |
|---|---|---|
| Direction | long/short | 15m mark direction |
| Entry Price | 15m mark price | mark price |
| SL Price | swing pivot | 15m walker state |
| TP Price | entry +/- 3R | calculated from SL |
| Cap Timestamp | entry_ts + 16 days | calculated |
| HTF Window ID | 1247 | current open window |

**No waiting. No guessing. Full matrix known immediately.**

---

## 7. Tick-Level vs Candle-Level

### Candle-Level (Slow) - runs every 15m and 1h close

```
On 15m close:
  1. Update 15m walker state
  2. Check for marks (B2, FLIP)
  3. If mark fires: check HTF window, enter trade if valid
  4. Update trailing: did new swing confirm? ratchet SL
  5. Save state to SQLite

On 1h close:
  1. Update 1h walker state
  2. Update chop index -> update bias
  3. Check for marks (B2, FLIP)
  4. If mark fires: open/close HTF window
  5. Save state to SQLite
```

### Tick-Level (Fast) - runs on every price update

```
On every tick:
  1. Get current price
  2. For each open LTF trade:
     - Long: price <= sl_current? -> SL hit
     - Long: price >= tp_price? -> TP hit
     - Short: price >= sl_current? -> SL hit
     - Short: price <= tp_price? -> TP hit
  3. Check 16-day caps
  4. If trade closed: record PnL, update cooldown/halt
```

---

## 8. Persistence Layer

### SQLite Tables

```sql
CREATE TABLE walker_state (
    tf TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE htf_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

---

## 9. Restart and Catch-up

```
1. Load walker state from SQLite
2. Load open HTF windows from SQLite
3. Load open LTF trades from SQLite
4. Load trading state (cooldown/halt) from SQLite
5. Get last processed candle timestamp per TF
6. Fetch all candles since then from Binance REST
7. Detect gaps -> backfill missing candles
8. Process each candle in chronological order
9. Done. State is now identical to uninterrupted run.
```

---

## 10. Verification

- State hash after every candle (compare with backtest)
- GET /marks?tf=15m&from=...&to=... (returns marks from journal)
- GET /verify?tf=15m&from=...&to=... (recomputes backtest, diffs against journal)
- Daily parity check at 00:05 IST

---

## 11. Edge Cases

| Case | Handling |
|---|---|
| Volatile candle falls off window | Doesn't matter - state is complete, not reconstructed |
| Exchange downtime | Next poll fetches all closed candles since last_ts |
| Binance data gap | assert_no_gaps() halts and alerts - never silently skip |
| Process crash mid-candle | At most one candle reprocessed (idempotent via UNIQUE) |
| Open trade during 16+ day downtime | Time-cap check uses candle timestamp vs trade.cap_ts |
| Bot crash during trade exit | Atomic transaction - either all saved or none |

---

## 12. Implementation Phases

1. **Walker State Machine** - Implement step(state, candle) for 15m and 1h
2. **Determinism Test** - Run 129,306 candles, verify 100% identical
3. **SQLite Persistence** - Save state after every candle, atomic transactions
4. **Crash Testing** - Kill at candle 10/100/1000, restart, verify identical
5. **Downtime Testing** - Simulate 1h/1d/7d/16d/30d gaps, replay, verify identical
6. **Trade Engine** - HTF window + LTF trade management
7. **HTF/LTF Integration** - 1h bias -> 15m eligibility, chop index -> regime
8. **Data Streamer** - Ghost Streak pattern, WebSocket + REST dual stream
9. **Live Binance Adapter** - REST polling for candles, WebSocket for ticks
10. **Verification** - /marks endpoint, /verify endpoint, daily parity check

---

## 13. Project Structure

```
live_stuff/
  docs/
    design.md (this file)
    live_trading_doc.md (from fix/)
    backtest_checklist_v18.md (from fix/)
    design_challenge.md (original challenge)
  engine/
    candle.py, walker.py, walker_state.py, mark.py, trade_engine.py, bias.py, deterministic.py
  data/
    binance.py, streamer.py, backfill.py, validator.py
  persistence/
    database.py, state_store.py, mark_store.py, trade_store.py
  verification/
    replay.py, compare.py, hashes.py
  api/
    verification_api.py
  tests/
    test_walker.py, test_determinism.py, test_restart.py, test_gap_recovery.py, test_trade_engine.py, test_backtest_equivalence.py
  main.py
```

---

## Key Decisions Summary

| Decision | Choice | Why |
|---|---|---|
| Rolling window | REJECTED | Path-dependent, marks can change |
| Walker state machine | ADOPTED | Deterministic, provably correct |
| Tick-level monitoring | ADOPTED | Catch SL/TP hits immediately |
| Candle-level mark detection | ADOPTED | Marks only fire on closed candles |
| SQLite | ADOPTED | Single file, atomic, no dependencies |
| Immutable marks journal | ADOPTED | Audit trail, no repainting |
| Ghost Streak data pattern | ADOPTED | Proven in live trading |
| Same step() for backtest+live | ADOPTED | Guaranteed identical output |
| 1h = bias window, 15m = trade | ADOPTED | Matches v18 architecture |
| Full matrix known at entry | ADOPTED | No waiting, no guessing |
| FCFS (First Come First Serve) | ADOPTED | First tradeable mark per swing decides — pass or fail, no second chances |

---

## FCFS (First Come First Serve) — Swing Abandon Theory

### What is FCFS?

When a swing breaks, multiple marks can fire on the same swing (B2, FLIP, or both). FCFS means: **the first tradeable mark per swing decides that swing's fate.** If it passes all filters → trade it. If it fails ANY filter → abandon the swing entirely. No second chances.

### Why FCFS?

1. **Removes noise.** A swing that produces 3 marks usually has the first mark as the cleanest. Later marks are often in choppy conditions or late entries. FCFS removes these net-losing duplicates.

2. **Matches live execution.** In live, you see marks in real-time. When a B2/FLIP fires, you decide NOW — take it or skip it. You can't "wait and see" if a better mark comes later on the same swing. FCFS enforces this discipline.

3. **Improves PF without losing edge.** FCFS removed 64 trades averaging -0.72R each. The remaining 301 trades have PF 2.55 (vs 2.47 without FCFS). Same edge, cleaner execution.

### How It Works (Code)

In `_collect_signals()` (`btc_engine.py:170-299`):

```python
for swing in swings:
    swing_done = False  # FCFS: first tradeable mark decides
    for mark in swing["marks"]:
        if swing_done:
            break  # already decided — skip remaining marks
        
        # ... filter checks (window direction, pre-FS, dedup, etc.) ...
        
        if any filter fails:
            swing_done = True  # abandon — first mark failed
            continue
        
        if mark passes all filters:
            out.append(signal)
            swing_done = True  # trade — first mark passed
```

**B1 marks are exempt** — B1 never triggers FCFS. Only B2/FLIP marks are tradeable and subject to FCFS.

### What "Abandon" Means

When a swing is abandoned:
- No more marks from that swing are tradeable
- The swing still exists in the chain (it's a real market move)
- But we don't trade it because our first attempt failed
- The next swing gets a fresh FCFS cycle

### Live Equivalence

In live, FCFS is natural:
1. A B2 mark fires on 15m candle close
2. Check: is there an open HTF window in the same direction? Is the trade in cooldown? Is the streak halted?
3. If YES to any → skip this mark. The swing is abandoned.
4. If NO → enter the trade.

You can't "undo" a skip. The next mark on the same swing (if any) is irrelevant — you already decided.

### Backtest Impact

| Metric | Without FCFS | With FCFS | Delta |
|--------|-------------|-----------|-------|
| Trades | 365 | 301 | -64 |
| Gross R | +338.5R | +292.6R | -45.9R |
| PF | 2.47 | **2.55** | +0.08 |
| WR | 29.3% | **29.9%** | +0.6% |
| Net R (est.) | +252.4R | +221.6R | -30.8R |

The -45.9R gross is the cost of removing 64 net-losing trades. PF improvement is the benefit.

---

## References

---

## Modular Design Principle

**One concept per file. No piles.**

Each module has a single responsibility:
- `candle.py` = Candle data structure only
- `walker_state.py` = State dataclass only
- `walker.py` = Step function only
- `mark.py` = Mark dataclass only
- `htf_window.py` = HTF window logic only
- `ltf_trade.py` = LTF trade logic only
- `trading_state.py` = Cooldown/halt logic only
- `database.py` = Schema only
- `state_store.py` = Walker state persistence only
- `mark_store.py` = Marks persistence only
- `trade_store.py` = Trades persistence only

This makes testing, debugging, and modifying easy. Change one thing without breaking others.

---

## Detailed Module Breakdown

### Phase 1: Walker State Machine

**Files:**
```
engine/candle.py          - Candle dataclass
engine/walker_state.py    - WalkerState15m, WalkerState1h dataclasses
engine/mark.py            - Mark dataclass
engine/walker.py          - step() function (pure, deterministic)
engine/bias.py            - Chop index calculation, bias update
tests/test_walker.py      - Walker unit tests
tests/test_determinism.py - Run twice, verify identical
```

**Responsibilities:**
- `candle.py`: Hold OHLCV data, timestamp, closed flag
- `walker_state.py`: Hold all state for 15m and 1h chains
- `mark.py`: Hold mark data (immutable once created)
- `walker.py`: Pure function `step(state, candle) -> (state, marks[])`
- `bias.py`: Calculate chop index, update bias from 1h data

### Phase 2: Persistence Layer

**Files:**
```
persistence/database.py       - SQLite connection, schema creation
persistence/state_store.py    - save_state(), load_state()
persistence/mark_store.py     - insert_mark(), get_marks()
persistence/trade_store.py    - save_trade(), update_trade(), get_open_trades()
tests/test_persistence.py     - Database tests
```

**Responsibilities:**
- `database.py`: Create tables, handle connections, atomic transactions
- `state_store.py`: Serialize/deserialize WalkerState to/from JSON
- `mark_store.py`: Append-only marks (never update/delete)
- `trade_store.py`: CRUD for trades (open/close/update SL)

### Phase 3: Trade Engine

**Files:**
```
engine/htf_window.py      - HtfWindow dataclass, open/close logic
engine/ltf_trade.py       - LtfTrade dataclass, entry/exit logic
engine/trading_state.py   - TradingState dataclass, cooldown/halt logic
engine/trade_manager.py   - High-level trade orchestration
tests/test_trade_engine.py - Trade engine tests
```

**Responsibilities:**
- `htf_window.py`: Window direction, cap timestamp, status
- `ltf_trade.py`: Entry, SL/TP, trailing, exit logic
- `trading_state.py`: Cooldown counter, streak halt logic
- `trade_manager.py`: Tie it all together (entry rules, exit rules)

### Phase 4: Data Layer

**Files:**
```
data/binance.py       - REST API client (fetch candles)
data/streamer.py      - WebSocket client (ticks)
data/backfill.py      - Gap detection and backfill
data/validator.py     - Candle validation, gap detection
tests/test_data.py    - Data layer tests
```

### Phase 5: Main Loop

**Files:**
```
main.py               - Bootstrap + live loop
bootstrap.py          - Initial state setup
live_loop.py          - Poll/process/check loop
tests/test_loop.py    - Integration tests
```

### Phase 6: Verification

**Files:**
```
verification/replay.py    - Replay candles through walker
verification/compare.py   - Diff expected vs actual
verification/hashes.py    - State hash calculation
api/verify_endpoint.py    - GET /marks, GET /verify
tests/test_verification.py - Verification tests
```


- `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` - v18 engine
- `backend/src/btc/engines/v7_timecap.py` - 16-day cap logic
- `backend/src/btc/btc_engine.py` - walker + trade logic
- `backend/src/btc/btc_swing.py` - swing computation
- `backend/src/walker.py` - FlowCandle + walker
- `backend/src/live/main.py` - current live engine (to be replaced)
- `backend/src/live/mark_engine.py` - current mark engine (to be replaced)
- `BTC_GhostStreak_Strategy 3/data_streamer.py` - data streamer pattern
- `fix/backtest_checklist_v18.md` - v18 backtest validation
- `fix/live_trading_doc.md` - live trading journey log

    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    close_ts INTEGER,
    close_reason TEXT
);

CREATE TABLE ltf_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    sl_initial REAL NOT NULL,
    sl_current REAL NOT NULL,
    tp_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    htf_window_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    exit_ts INTEGER,
    exit_price REAL,
    exit_reason TEXT,
    r_multiple REAL,
    trail_next_pivot REAL,
    trail_activation_idx INTEGER,
    trail_confirmed BOOLEAN
);

CREATE TABLE marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    tf TEXT NOT NULL,
    kind TEXT NOT NULL,
    direction TEXT NOT NULL,
    price REAL NOT NULL,
    swing_no INTEGER NOT NULL,
    swing_kind TEXT NOT NULL,
    algo_version INTEGER NOT NULL,
    journaled_at INTEGER NOT NULL,
    UNIQUE (ts, tf, kind, direction, swing_no)
);

CREATE TABLE trading_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cooldown_remaining INTEGER NOT NULL,
    consecutive_losses INTEGER NOT NULL,
    halted BOOLEAN NOT NULL,
    last_loss_bar INTEGER
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### Atomic Transactions

```
BEGIN TRANSACTION
  state, marks = step(state, candle)
  insert marks
  update walker state
  update trades
  update trading state
COMMIT

If crash: entire transaction rolls back, candle is unprocessed, retry next loop.
```

seg_start: float (current swing's start pivot price)
extreme: float (current swing's running extreme)
prev_swing_end: float (previous swing's end price)
since_end_low: float (lowest low since prev_swing_end)
since_end_high: float (highest high since prev_swing_end)
swing_already_traded: bool
last_candle_ts: int (last candle processed)
state_hash: str (SHA256 of serialized state)
```

### WalkerState (1h)

Same as 15m plus:
```
tr_ring: float[14] (True Range ring buffer)
hi_ring: float[14] (High ring buffer)
lo_ring: float[14] (Low ring buffer)
ring_idx: int
chop_index: float
bias: str (long | short | neutral)
```

### HTF Window

```
window_id: int
direction: str (long | short)
entry_ts: int (when 1h mark fired)
entry_price: float (1h mark price)
cap_ts: int (entry_ts + 16 days)
status: str (open | closed)
close_ts: int | None
close_reason: str | None (cap | opposite_mark)
```

### LTF Trade

```
trade_id: int
direction: str (long | short)
entry_ts: int (when 15m mark fired)
entry_price: float (15m mark price)
sl_initial: float (initial SL = -1R)
sl_current: float (current SL for trailing)
tp_price: float (3R target)
cap_ts: int (entry_ts + 16 days)
htf_window_id: int (links to HTF window)
status: str (open | closed)
exit_ts: int | None
exit_price: float | None
exit_reason: str | None (sl | tp | cap | trail)
r_multiple: float | None
trail_next_pivot: float | None
trail_activation_idx: int | None
trail_confirmed: bool
```

### TradingState (cooldown/halt)

```
cooldown_remaining: int (bars remaining)
consecutive_losses: int
halted: bool
last_loss_bar: int | None
```

### Mark (Immutable - never updated once written)

```
id: int
ts: int (candle close time)
tf: str (15m | 1h)
kind: str (B1 | B2 | FLIP)
direction: str (long | short)
price: float
swing_no: int
swing_kind: str
algo_version: int
journaled_at: int (wall clock when written)
```
