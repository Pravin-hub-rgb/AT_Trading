grok:
**Solution: Immutable Journal + Seeded Path-Dependent Walker with Safe Rolling Window**

This design guarantees live marks match a full-history backtest, stays under 100 KB storage / 100 MB RAM, survives arbitrary downtime, and runs on a 1 GB VPS using only SQLite + Binance REST.

### Core Insight (Why This Works)

The swing walker is path-dependent, but research shows:

- A 300-candle window already reproduces the full-history chain on the most recent ~200 bars for 15 m data.
- A 200-candle window is sufficient for 1 h.
- Once a mark is *emitted and journaled*, it is frozen forever. Subsequent window slides cannot change past marks.
- The only requirement is that, when a new closed candle arrives, the window used to compute the chain *at that moment* is large enough that the mark on the newest bar is identical to the full-history mark.

Therefore we never recompute past marks. We only ever compute the mark(s) that belong to the *current* closed candle, using a sufficiently large recent window, then append them immutably.

This is exactly analogous to how professional systems treat confirmed bars (MT5 closed-bar logic, TradingView non-repainting `request.security` with offset + lookahead, QuantConnect warm-up + online indicators, Freqtrade trade persistence).

### 1. Architecture Overview

```
┌─────────────────┐     poll every 60 s      ┌──────────────────────┐
│  Binance REST   │ ───────────────────────► │  Candle Downloader   │
└─────────────────┘                          └──────────┬───────────┘
                                                       │
                                                       ▼
┌─────────────────┐   append-only            ┌──────────────────────┐
│  SQLite Journal │ ◄─────────────────────── │  Walker + Mark Engine│
│  (marks, trades,│                          │  (per TF)            │
│   state)        │                          └──────────┬───────────┘
└────────▲────────┘                                     │
         │                                              ▼
         │                                   ┌──────────────────────┐
         └───────────────────────────────────│  Trade Manager       │
                                             │  (SL / 3R / 16 d)    │
                                             └──────────────────────┘
                                                       │
                                                       ▼
                                             ┌──────────────────────┐
                                             │  Verification API    │
                                             └──────────────────────┘
```

Two independent chains run in parallel (15 m and 1 h). Bias is taken only from the 1 h chain.

### 2. Data Structures (exact)

```python
# Candle (in-memory ring + SQLite)
@dataclass
class Candle:
    ts: int          # open time ms
    o, h, l, c: float
    v: float
    closed: bool

# Mark (immutable once written)
@dataclass
class Mark:
    ts: int
    tf: str          # "15m" | "1h"
    kind: str        # "B1" | "B2" | "FLIP"
    direction: int   # +1 / -1
    price: float
    swing_no: int
    swing_kind: str
    candle_idx: int  # absolute index in the full stream (for audit)

# Open Trade
@dataclass
class Trade:
    id: str
    entry_ts: int
    entry_price: float
    direction: int
    sl: float
    tp: float            # 3R
    cap_ts: int          # entry_ts + 16*86400*1000
    tf: str
    mark_kind: str
    swing_no: int
    status: str          # "open" | "closed"
    exit_ts: Optional[int]
    exit_price: Optional[float]
    outcome: Optional[str]  # "sl" | "tp" | "time"
    r_multiple: Optional[float]
```

### 3. Persistence Schema (SQLite – total size stays << 100 KB)

```sql
CREATE TABLE candles_15m (
    ts INTEGER PRIMARY KEY,
    o REAL, h REAL, l REAL, c REAL, v REAL
);
-- same for candles_1h (keep only last 600 / 300 respectively)

CREATE TABLE marks (
    ts INTEGER,
    tf TEXT,
    kind TEXT,
    direction INTEGER,
    price REAL,
    swing_no INTEGER,
    swing_kind TEXT,
    PRIMARY KEY (ts, tf, kind, direction)   -- immutable
);

CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    entry_ts INTEGER,
    entry_price REAL,
    direction INTEGER,
    sl REAL,
    tp REAL,
    cap_ts INTEGER,
    tf TEXT,
    mark_kind TEXT,
    swing_no INTEGER,
    status TEXT,
    exit_ts INTEGER,
    exit_price REAL,
    outcome TEXT,
    r_multiple REAL
);

CREATE TABLE engine_state (
    key TEXT PRIMARY KEY,
    value TEXT          -- JSON for last_processed_ts, busy_until, bias, streak, etc.
);
```

- Candles tables are truncated to the safe window after every successful cycle.
- Marks and trades are append-only / update-only; never deleted.
- Total footprint after months of running: a few dozen KB.

### 4. Algorithms

#### A. Safe Window Sizes (proven by your research)

| TF  | Min for exact tail | Safe production window | Bars kept on disk |
|-----|--------------------|------------------------|-------------------|
| 15m | 300                | 500                    | 600               |
| 1h  | 150                | 250                    | 300               |

#### B. Boot / Restart / Catch-up

1. Load last N candles from SQLite (or download if empty).
2. Load last processed timestamp + open trades + bias + busy_until + streak from `engine_state`.
3. Query Binance for every missing closed candle from `last_processed_ts + interval` up to now (paginate with `startTime` / `endTime`).
4. Process the missing candles **in chronological order**, exactly as if the bot had never stopped.
5. For each new closed candle:
   - Append to the in-memory ring buffer (drop oldest if over limit).
   - Re-run the walker **only on the current window**.
   - Emit any mark whose timestamp == current candle open time (or the bar that just closed).
   - Journal the mark(s) immediately (INSERT OR IGNORE).
   - Run trade management (SL/TP/time) against the new candle.
   - Update state atomically.
6. After catch-up, enter the normal 60-second poll loop.

Because the journal is immutable and processing is strictly sequential, downtime of hours, days or weeks is handled identically.

#### C. Mark Emission (the critical part)

```python
def process_closed_candle(candle, window, journal, state):
    # window already contains the safe number of prior candles + this one
    chain = compute_swing_chain(window)          # your existing walker
    new_marks = [m for m in chain.marks if m.ts == candle.ts]
    
    for m in new_marks:
        if not journal.has_mark(m):              # immutable
            journal.append_mark(m)
            maybe_open_trade(m, state)           # apply entry rules
```

Because the window is ≥ the proven minimum, `new_marks` on the newest bar are identical to the full-history backtest.

#### D. Trade Management (runs every candle)

- For every open trade:
  - If candle high/low touches SL → close at SL, record –1 R.
  - Else if touches TP → close at TP, record +3 R.
  - Else if `candle.ts >= trade.cap_ts` → market close at candle.close, record time outcome.
- Update `busy_until`, streak, cooldown, bias (from 1 h FLIP).
- Persist trade row and engine_state.

Entry rules (already confirmed):
- Only B2 and FLIP are tradeable.
- One-swing-one-trade.
- HTF-LTF or MASTER #1 logic applied on top of the journaled marks.
- Bias filter from 1 h Chop Index.

### 5. Verification Endpoint

```
GET /marks?from=YYYY-MM-DD&to=YYYY-MM-DD&tf=15m
```

Returns the exact journaled marks in the range. Because they are immutable and were produced with a window that matches full history on those bars, they are bit-for-bit identical to a backtest chart run on the same data.

You can also expose `/trades` and `/state` for full auditability.

### 6. Edge-Case Handling

| Scenario                        | Handling |
|---------------------------------|----------|
| Volatile candle falls out of window | Irrelevant – past marks already journaled and never recomputed |
| Network gap / exchange downtime | Catch-up downloads every missing closed candle in order |
| Bot killed mid-candle           | On restart, last_processed_ts is the last fully processed closed bar |
| Open trade during 16-day downtime | Cap is absolute timestamp; on catch-up the trade is closed at the correct bar |
| Partial candle on restart       | Only process fully closed candles (Binance `klines` with `closed=true`) |
| Clock skew                      | Use exchange server time for all timestamps |
| Storage growth                  | Truncate candle tables after every cycle; marks/trades stay tiny |

### 7. Proof of Correctness

1. **Inductive invariant**: At every closed candle *t*, the mark(s) emitted for *t* are computed from a window that research has shown produces the identical mark as the full-history walker.
2. Once emitted, the mark is written with a unique primary key and never updated or deleted.
3. Therefore the sequence of journaled marks is identical to the sequence a full-history backtest would have produced.
4. Trade state is a pure function of the journaled marks + subsequent candles → also matches.
5. Restart + catch-up simply continues the same sequential process from the last committed state.

You can prove it empirically by running the live engine for 30+ days and comparing the verification endpoint output against a full-history backtest on the same date range.

### 8. Performance & Resource Profile

- Memory: ring buffer of 600 × 15 m + 300 × 1 h candles ≈ 50–80 KB + Python overhead → well under 100 MB.
- Storage: candles truncated + marks/trades ≪ 100 KB even after a year.
- CPU: walker on 500 bars is microseconds; total per-candle work < 2 ms.
- Boot: load 600 candles from SQLite or download → < 2 s.

### 9. Implementation Notes (practical)

- Use a single-threaded loop (or asyncio with one task) – no concurrency needed.
- Atomic state updates: write marks → trades → engine_state inside a single SQLite transaction.
- On every successful cycle: `PRAGMA wal_checkpoint(TRUNCATE)` if you want to keep the DB file tiny.
- Log every emitted mark and every trade open/close with the exact candle that caused it (audit trail).
- Optional: keep a second “shadow” full-history CSV on a larger machine and periodically compare the last 200 marks as a continuous integration check.

This design is the minimal, mathematically grounded solution that satisfies every requirement you listed. It is what serious systematic desks do when they have path-dependent state: freeze confirmed signals forever and only advance the frontier with a proven-sufficient look-back.

---

gemini:

**System Architecture**
The engine uses a stateless ingestion loop coupled with an **Anchored State Snapshot + Immutable Journal** pattern to eliminate rolling-window volatility drift while maintaining lean VPS resource usage.

**Data Flow & State Management**

* **Polling Loop:** Every 60 seconds, fetch the latest closed candles via Binance REST API.
* **Checkpoint Engine:** Every 24 hours (or at structural swing boundaries), serialize and persist the complete swing graph topology to SQLite.
* **Immutable Journal:** Once a mark (B1, B2, FLIP) or trade lifecycle event writes to the SQLite journal, it is cryptographic-append-only and never recalculated or overwritten.

**SQLite Schema (< 100KB Footprint)**

```sql
CREATE TABLE candles (
    tf TEXT, timestamp INTEGER PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL
);
CREATE TABLE checkpoints (
    tf TEXT, timestamp INTEGER PRIMARY KEY, swing_state_json TEXT
);
CREATE TABLE marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, tf TEXT, kind TEXT, direction TEXT, price REAL, swing_no INTEGER, swing_kind TEXT
);
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY, entry_time INTEGER, direction TEXT, entry_price REAL, sl REAL, tp REAL, status TEXT, exit_time INTEGER, pnl_r REAL
);

```

**Solving the Volatility Fall-Off Problem**
Naive rolling windows cause cascade shifts when a large historical volatility candle drops off the edge. To guarantee 100% backtest parity without storing all 129k candles:

* **Anchored Warm-up:** Instead of running the walker raw from the edge of a 500-candle window, load the **last validated structural checkpoint** (saved when the swing was locked deep in history) plus the delta candles.
* Because swings lock permanently after a fixed confirmation threshold, freezing the graph topology via daily checkpoints ensures that dropping old boundary candles alters nothing upstream of the anchor.

**Catch-Up & Restart Algorithm**

1. **Boot & State Load:** Query SQLite for the latest checkpoint and active trade states.
2. **Gap Detection:** Compare local latest candle timestamp with Binance server time.
3. **Delta Ingestion:** Fetch missing candles during downtime.
4. **Replay Execution:** Run the walker forward strictly over the delta candles using the loaded checkpoint state. Emit any missed marks to the immutable journal and evaluate open trades against high/low extremes for SL, TP, or 16-day time-outs.

**Trade & Bias Execution Rules**

* **1h Bias Filter:** 1h determines market state (Long/Short/Neutral via FLIP marks). 15m signals execute only when matching active 1h bias. Neutral halts new entries.
* **Entry & Risk:** B1 and B2 triggers enter in the direction of the bias. Stop-loss anchors to the swing extreme candle; Take Profit targets fixed 3R.
* **Simultaneous Limits:** Maximum 1 active trade per timeframe chain (independent 15m and 1h tracks).

**Verification Endpoint**
A lightweight FastAPI route (`GET /verify?date=YYYY-MM-DD`) re-runs the exact chain calculation using the closest prior checkpoint and delta candles, returning a JSON array of marks. This allows direct programmatic comparison with the historical backtest chart.

---

deep seek:
Based on the detailed problem statement, the search results, and established practices in quantitative trading systems, here is a comprehensive architectural design for a production-grade live trading engine.

The core of the solution lies in a paradigm shift: **state is ground truth, and computation is a deterministic function of that state.** This means we treat the immutable, append-only journal of market data and events as the source of truth, from which we can deterministically reconstruct the entire system state for any point in time.

### 🏛️ Core Architectural Principles

The design is governed by the following principles, drawn from industry best practices.

1.  **Journal is the Source of Truth**: All incoming market data (candles) and generated signals (marks) are appended to an immutable, write-once log. This eliminates ambiguity and forms the basis for determinism. The system state (open trades, active swings) is a materialized view derived from replaying this journal .
2.  **Separation of State and Behavior**: The system's "state" (open positions, active swing context) and its "behavior" (mark detection, SL calculation) are decoupled. This is critical for hot-reload or recovery scenarios, allowing the core logic to be updated without corrupting the state .
3.  **External Services are State, Too**: Dependencies like Binance are treated as external state providers. Caching static or externally derived data (like historical candles) ensures that the engine's startup and recovery do not depend on unreliable network calls .
4.  **Determine Minimum Viable Context**: The path-dependence problem is solved by defining a **minimum, fixed-length lookback window** that is mathematically proven to produce a stable swing chain. Your research showing that 300 candles (15m) and 150-200 candles (1h) are sufficient windows is the key. This sets the **Minimum Viable History (MVH)**.

### 💾 State Persistence and Data Structure

This design uses **SQLite** as the persistent store, which provides durability, ACID compliance, and simple crash recovery.

#### 1. The Immutable Journal (Fact Table)

*   **`candles`**: Stores all downloaded candles. Indexed by `(symbol, timeframe, timestamp)`. This table is **append-only**.
*   **`marks`**: The append-only journal of emitted signals. `{id, timestamp, kind, direction, price, swing_no, swing_kind, computed_by_window_hash}`. This table is the canonical record of all decisions made. Once written, a mark is never deleted or changed. It is the `journal` that is replayed for recovery .

#### 2. Materialized State Tables (Current State)

*   **`active_swings`**: Stores the currently active swing information for each timeframe. `{symbol, timeframe, swing_no, swing_kind, seg_start_idx, ...}`.
*   **`open_trades`**: Stores the current open trade. `{id, entry_time, direction, entry_price, sl_price, tp_price, cap_idx, ...}`. This is the state that must survive a restart.
*   **`system_metadata`**: Stores key-value pairs for system control. `{key, value}` e.g., `('last_processed_ts', '2026-03-15 16:00:00')`, `('last_processed_mark_id', '1234')`.
*   **`walker_state`**: Stores the necessary state for the walker to resume computation at a given timestamp, derived from the MVH. This is the critical state that enables fast recovery.

### 🔄 Operational Flow and Recovery

The engine operates as a simple loop, processing closed candles one by one.

#### 1. Normal Startup (Cold Boot)

1.  **`initialize()`**: Connect to SQLite. Load **`system_metadata`** and **`open_trades`**.
2.  **`fetch_missing_candles()`**:
    *   Determine the `last_candle_ts` from the `candles` table.
    *   Fetch all missing 1h and 15m candles from Binance **from the last known timestamp minus the MVH** (e.g., 300 candles prior). This ensures the walker has enough context to rebuild the chain correctly from a known-good state.
3.  **`restore_state()`**:
    *   Load `walker_state` from SQLite. This contains the exact state of the swing detection algorithm as of the `last_processed_ts`.
    *   If no `walker_state` exists (first run), build the swing chain from the beginning of the downloaded data.
4.  **`catch_up()`**: For each new candle timestamp since the last processed time:
    *   Load the **local** window of candles (from MVH to current) into memory.
    *   Using the loaded `walker_state` as a starting point, process the new candle through the `SwingWalker`.
    *   This is **deterministic** because the state and the input candles are identical to what would be used in a backtest .

#### 2. Continuous Operation (Steady State)

For each new closed candle (`t`):

1.  **Fetch**: Pull the latest closed candle from Binance for the required timeframes.
2.  **Append**: Write the new candle to the `candles` table.
3.  **Update State**: Process the new candle using the in-memory `walker_state`.
    *   The `SwingWalker` updates its internal state (`active_swings`). Emitted marks are written to the `marks` table.
    *   Trade state (`open_trades`) is checked against the new candle for SL, TP, or time-exit conditions. On exit, the trade is closed and recorded.
4.  **Persist**: Commit the updated `walker_state` and any closed trades to the SQLite database. This ensures the system can pick up exactly where it left off.

#### 3. Downtime Recovery

If the engine is down for a period (e.g., 1 hour, 1 day, 1 week):

1.  **Startup**: The `initialize()` function loads the last saved state.
2.  **Fetch**: Download all candles from the `last_processed_ts` (from metadata) to the current time, **plus the MVH** before that point.
3.  **Catch-up**: The `catch_up()` loop processes each missing timestamp sequentially, re-applying the same logic as during normal operation.
4.  **Completion**: The system is now up-to-date, and its state is identical to one that had been running continuously. No information is lost, and no external state is required .

### 📜 Proof of Correctness & Verification

The verification endpoint is not a separate process but a view of the immutable journal.

*   **Endpoint**: `/marks?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
*   **Logic**: `SELECT * FROM marks WHERE timestamp BETWEEN from_date AND to_date ORDER BY timestamp ASC;`
*   **Proof**: The marks in the database are the exact marks that were emitted during processing. Because the processing is deterministic from the state and the `candles` table, and because the `candles` table is a complete history, the marks emitted in live trading are **structurally identical** to those from a full-history backtest .
*   **Edge Cases**: The immutability of the `marks` table guarantees that a "volatile candle falling off" the rolling window will not change a past mark, because past marks have already been journaled. The only challenge was for current processing, which is solved by using the MVH and persisted state.

### 🧠 Alternative Solutions Considered

*   **MetaTrader/TradingView**: They calculate indicators on a fixed number of bars. This is the "naive rolling window" approach described in the problem and is known to be unreliable for path-dependent indicators like the swing walker. Our solution fixes this by persisting the walker's state.
*   **QuantConnect/Freqtrade**: They use a data warehouse or database that is loaded during warm-up. This is similar to our "Full History Seed" approach but with a more efficient and smaller MVH to minimize resource usage.
*   **Hot-Reload Architecture**: The design of the `SwingWalker` as a stateful object that can be serialized/deserialized is the foundation for advanced features like hot-reload, as described in search results .

### 📈 Conclusion

This architecture solves the Core Problem by making state durable and processing deterministic. By persisting the `walker_state` and using a Minimum Viable History window, the system eliminates the path-dependence issue, ensuring that every signal generated in live trading is exactly the same as what a full-history backtest would produce. The immutable journal and robust catch-up process guarantee correctness across restarts and arbitrary downtime, all within the tight constraints of a 1GB VPS.

---

claude:
# Live Trading Engine — Design Document

## 0. The Key Reframe

Every attempt in the problem statement treats the chain as something you **recompute** from a window of raw candles. That's the actual bug. Recomputing from a window is *inherently* path-dependent, no matter how big the window is — you've just empirically found the window size where path-dependence becomes statistically rare (300–500 candles), not where it becomes impossible. A big enough volatility candle can still poison any fixed window; you've only pushed the failure probability down, not to zero. For real money, "usually correct" is not correct.

The fix is to change the unit of persistence:

> **Persist the walker's internal algorithmic state (a small struct), not a window of candles.** Advance that state forward exactly one candle at a time, in the same order the backtest would process it. Never recompute the chain from history. Only ever *extend* it.

This is not a novel trick — it's literally how a backtest already works. A backtest is a `for candle in history: walker.step(candle)` loop that happens to also keep every historical candle around out of convenience, not necessity. The walker itself only looks at:
- the current active swing (start pivot, extreme, direction, swing_no)
- a handful of "since prev swing end" extremes (for touchable SL)
- the last 14 bars of TR/H/L (for Chop Index on 1h)
- open-trade state

None of that requires the full 129k-candle history to be *held in memory* — it requires the full history to have been *walked through once* to get to the current state. Walking through it once and checkpointing the result is a one-time cost, not a per-boot cost.

This single reframe resolves points 2, 3, and 7 of your "Real Question" simultaneously: correctness (no recompute → no divergence), storage (state is KB, not MB), and restart survival (checkpoint + tiny replay, not a window rebuild).

---

## 1. Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │              BOOTSTRAP (one-time)         │
                    │  Full history → walker.step() per candle  │
                    │  → WalkerState @ T0  (checkpoint #0)       │
                    └───────────────────┬───────────────────────┘
                                         │
                                         ▼
┌────────────┐   poll 60s   ┌──────────────────────┐   append-only   ┌──────────────┐
│  Binance    │─────────────▶│   Live Engine Loop    │────────────────▶│  marks table  │
│  REST API   │  closed      │  1. fetch new candle  │                 │  (immutable)  │
└────────────┘  candles      │  2. walker.step()     │                 └──────────────┘
                              │  3. emit marks (if any)│
                              │  4. trade monitor step │───────────────▶┌──────────────┐
                              │  5. checkpoint state    │                │ trades table  │
                              └──────────┬──────────────┘                └──────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  SQLite (single file)  │
                              │  candles / marks /      │
                              │  trades / walker_state /│
                              │  checkpoints             │
                              └──────────────────────┘
                                         ▲
                                         │
                              ┌──────────────────────┐
                              │  Verification API      │
                              │  GET /marks?from&to    │
                              └──────────────────────┘
```

Two processes conceptually, one binary in practice:
1. **Bootstrap** — runs once, ever, per instrument/TF (or once per "we changed the algorithm" event). Not part of the restart path.
2. **Live loop** — runs forever, advances state one candle at a time, checkpoints after every candle.

Restart = load last checkpoint, fetch candles since checkpoint's `last_candle_ts`, replay those (typically 1–a few thousand for weeks of downtime), done. This is *catch-up*, not *bootstrap* — same code path as the live loop, just run in a tight loop without the 60s sleep.

---

## 2. Data Structures

### 2.1 Candle
```
Candle {
  ts: int          // unix seconds, candle OPEN time
  o, h, l, c: float
  v: float
  closed: bool     // only closed candles are ever processed
}
```

### 2.2 WalkerState (the thing that replaces "the window")
This is the entire point of the design — keep it small and complete.

```
WalkerState {
  // identity
  instrument: "BTCUSDT"
  tf: "15m" | "1h"
  algo_version: int          // bump on any logic change (see §8)

  // swing chain position
  swing_no: int
  swing_kind: "up" | "down"
  seg_start: { ts, price }        // current swing's start pivot
  extreme: { ts, price }          // current swing's running extreme
  prev_swing_end: { ts, price }   // for touchable-SL calc

  // touchable SL tracking (since prev_swing_end)
  since_end_low: float
  since_end_high: float

  // one-swing-one-trade tracking
  swing_already_traded: bool      // reset when swing_no increments

  // chop index rolling buffers (1h only) — fixed-size ring buffers, 14 elements
  tr_ring: float[14]
  hi_ring: float[14]
  lo_ring: float[14]
  ring_idx: int

  // bias (derived from 1h, consumed by 15m)
  bias: "long" | "short" | "neutral"
  bias_since_ts: int

  // bookkeeping
  last_candle_ts: int             // last candle this state has processed
  state_hash: string              // sha256 of the serialized struct above, for tamper/corruption detection
}
```

Serialized this is **well under 1KB** per (instrument, TF) pair. Two TFs → under 2KB total for walker state.

### 2.3 Mark
```
Mark {
  id: int (autoincrement, monotonic)
  ts: int              // candle close time the mark fired on
  tf: "15m" | "1h"
  kind: "B1" | "B2" | "FLIP"
  direction: "long" | "short"
  price: float
  swing_no: int
  swing_kind: "up" | "down"
  algo_version: int
  journaled_at: int    // wall clock when written, for audit
}
```
**Append-only. Never UPDATE, never DELETE.** Enforced at the DB layer (see §4 — no UPDATE grants on this table from the app's runtime role, or a trigger that rejects it).

### 2.4 Trade
```
Trade {
  id: int
  entry_mark_id: int (FK -> marks.id)
  tf: "15m" | "1h"
  direction: "long" | "short"
  entry_ts: int
  entry_price: float
  sl: float
  sl_mode: "swing" | "touchable" | "htf_ltf_atr"
  target: float           // 3R level
  time_cap_ts: int         // entry_ts + 16 days
  status: "open" | "closed"
  exit_ts: int | null
  exit_price: float | null
  exit_reason: "sl" | "target" | "time" | null
  r_multiple: float | null
  strategy: "master1" | "htf_ltf_v18"
  htf_window_id: int | null   // groups the HTF window for HTF-LTF strategy
}
```

### 2.5 Checkpoint
```
Checkpoint {
  id: int
  ts: int                      // matches last_candle_ts of the WalkerState it captures
  tf: "15m" | "1h"
  walker_state_json: text       // full WalkerState serialized
  open_trade_ids: text          // JSON array, redundant snapshot for fast restart
}
```
Checkpoints are cheap (KB each) — keep every N-th one (e.g. daily) plus the latest, prune older ones. You do *not* need every single checkpoint forever; you only ever need the most recent one to restart. Keeping a rolling history of checkpoints (say, last 30 days) is a nice-to-have for debugging, not a requirement.

---

## 3. Algorithms

### 3.1 The One True Step Function
This is the crux: bootstrap, live processing, and catch-up replay are **literally the same function call**, just invoked in different loops.

```
function step(state: WalkerState, candle: Candle) -> (WalkerState', Mark[]):
    marks = []

    update_extreme(state, candle)              // extend current swing's extreme if candle beats it
    update_since_end_ring(state, candle)        // touchable SL bookkeeping
    update_chop_rings(state, candle)            // 1h only

    broken, direction = check_swing_break(state, candle)
    if broken:
        kind = classify_break(state, direction)  // B1 / B2 / FLIP, from existing swing-break count logic
        if kind in (B2, FLIP) and not state.swing_already_traded:
            marks.append(Mark(ts=candle.ts, kind=kind, direction=direction,
                               price=break_price, swing_no=state.swing_no, ...))
            state.swing_already_traded = true
        # regardless of tradeability, advance the chain
        state.prev_swing_end = state.extreme
        state.seg_start = break_price_pivot
        state.extreme = break_price_pivot
        state.swing_no += 1
        state.swing_kind = flip(state.swing_kind) if kind==FLIP else state.swing_kind
        state.swing_already_traded = false

    if state.tf == "1h":
        recompute_bias(state)   // chop index -> regime -> feeds 15m bias filter

    state.last_candle_ts = candle.ts
    state.state_hash = sha256(serialize(state))
    return state, marks
```

**Why this is provably identical to backtest**: the backtest is just `state = INITIAL; for c in all_candles: state, marks = step(state, c)`. Live is `state = load_checkpoint(); for c in candles_since_checkpoint: state, marks = step(state, c)`. Since `step()` is a pure function of `(state, candle)` with no hidden dependence on window size or position, and since `state` fully captures everything `step()` needs, the sequence of states and marks produced live is byte-identical to backtest **by construction**, not by empirical convergence. This is the proof of correctness (expanded in §7).

### 3.2 Bootstrap (run once)
```
function bootstrap(instrument, tf, full_history):
    state = WalkerState.initial(instrument, tf)
    all_marks = []
    for candle in full_history:   # chronological, closed candles only
        state, marks = step(state, candle)
        all_marks.extend(marks)
    persist_marks(all_marks)                 # backfill the marks table
    persist_checkpoint(state)                 # this becomes checkpoint #0 / T0
    return state
```
This can run offline, on a beefy machine, exactly once. Its output (one checkpoint per TF, ~1KB each) is what you actually deploy to the VPS — **not** the 129k candles.

### 3.3 Live Loop
```
function live_loop():
    state = load_latest_checkpoint()
    loop every 60s:
        new_candles = fetch_closed_candles_since(state.last_candle_ts)  # Binance REST
        for candle in new_candles:                                     # in order, no gaps allowed
            store_candle(candle)              # small ring buffer, see §3.5
            state, marks = step(state, candle)
            for m in marks:
                journal_mark(m)                # INSERT only
                maybe_open_trade(m, state)      # entry rules from §3.4
            monitor_open_trades(candle)          # SL/TP/16d check, every candle, every open trade
            persist_checkpoint(state)             # after EVERY candle, not batched
```
Checkpointing after every candle, not batching, is deliberate: if the process dies mid-loop, worst case you reprocess one candle on restart (idempotent — see §3.6), never lose one.

### 3.4 Trade Entry
```
function maybe_open_trade(mark, state):
    if strategy == "master1":
        if mark.kind != "FLIP": return
        if has_open_trade(tf="1h"): return         # one trade at a time
        sl = state.seg_start.price
        open_trade(mark, sl=sl, target=3R(mark.price, sl), cap=mark.ts + 16d)

    if strategy == "htf_ltf_v18":
        if not decisive(mark): return                # B2 or FLIP only
        if not htf_window_open(): return              # need an active HTF window
        if has_open_ltf_trade(): return                # one LTF trade per HTF window
        if in_cooldown() or streak_halted(): return
        regime = "high_chop" if chop_1h > 61.8 else "low_chop"
        if regime == "high_chop" and mark.kind != "B2": return
        if regime == "low_chop" and mark.kind != "FLIP": return
        sl = pivot - 0.25 * atr(mark.tf) * direction_sign
        open_trade(mark, sl=sl, target=3R(...), cap=mark.ts + 16d)
```

### 3.5 SL / TP / Time Monitoring
Runs on every closed candle, for every open trade — O(#open_trades) which is ≤ 2 (one per TF) for these strategies, so effectively O(1).
```
function monitor_open_trades(candle):
    for trade in open_trades:
        if trade.tf's candle != candle.tf: continue     # 15m trades check 15m candles etc.
        if hit_sl(trade, candle): close_trade(trade, reason="sl", price=trade.sl, ts=candle.ts)
        elif hit_target(trade, candle): close_trade(trade, reason="target", price=trade.target, ts=candle.ts)
        elif candle.ts >= trade.time_cap_ts: close_trade(trade, reason="time", price=candle.c, ts=candle.ts)
```
This needs the *raw* candle (high/low/close), which is why a small rolling candle buffer is still kept (§3.6) — but only for open-trade monitoring, never for chain recomputation.

### 3.6 Candle Storage — small, and for a different purpose than you think
You still store recent candles, but **only** to:
1. Serve the verification endpoint's OHLC context, and
2. Detect gaps / do catch-up fetching.

Keep a rolling window (e.g. last 2,000 candles per TF ≈ 100KB) purely as a cache — it is **never read by the walker**, only by monitoring and API code. This is the crucial distinction from Attempt 2/3: candles are now a *cache*, not a *source of truth for the chain*. The chain's source of truth is `WalkerState`. Since it's just a cache, you can prune it as aggressively as you like without correctness risk — worst case you refetch from Binance.

### 3.7 Catch-up / Restart (the property you actually asked for)
```
function catch_up():
    cp = load_latest_checkpoint()
    gap_start = cp.ts + interval
    now = current_closed_candle_ts()
    missing = fetch_closed_candles(gap_start, now)     # from Binance REST, paginated
    assert_no_gaps(missing)                              # verify contiguous by ts, else halt + alert
    state = cp.walker_state
    for candle in missing:
        state, marks = step(state, candle)
        journal_marks(marks)                              # idempotent insert (see below)
        maybe_open_trade(...)
        monitor_open_trades(candle)
        persist_checkpoint(state)
    resume_live_loop(state)
```
This is **the same 60-second-poll code**, just with the sleep removed and a bounded loop instead of infinite. For 16 days of downtime on 15m candles, that's 1,536 candles to replay — at well under 10ms/candle this is under 15 seconds of catch-up. Even a year of downtime (35k 15m candles) is under 6 minutes. This is the actual answer to "survives downtime hours to weeks": *replay is cheap because the state is cheap, not because the replay is fast per se.*

**Idempotency**: `journal_mark` should be `INSERT OR IGNORE` keyed on `(tf, ts, kind, swing_no)` (unique constraint), so if a crash happens between "mark journaled" and "checkpoint persisted" and you reprocess that one candle on restart, you don't double-journal. Since `state.last_candle_ts` only advances after a full step completes, at most one candle is ever reprocessed.

---

## 4. Storage Schema (SQLite)

```sql
PRAGMA journal_mode = WAL;   -- crash-safe, and doesn't block the 60s poller on reads

CREATE TABLE candles (
  tf        TEXT NOT NULL,
  ts        INTEGER NOT NULL,
  o REAL, h REAL, l REAL, c REAL, v REAL,
  PRIMARY KEY (tf, ts)
);
-- pruned periodically to last ~2000 rows per tf; cache only, not authoritative

CREATE TABLE marks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  tf           TEXT NOT NULL,
  ts           INTEGER NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('B1','B2','FLIP')),
  direction    TEXT NOT NULL CHECK (direction IN ('long','short')),
  price        REAL NOT NULL,
  swing_no     INTEGER NOT NULL,
  swing_kind   TEXT NOT NULL,
  algo_version INTEGER NOT NULL,
  journaled_at INTEGER NOT NULL,
  UNIQUE(tf, ts, kind, swing_no)
);
-- append-only by convention; enforce with a trigger:
CREATE TRIGGER marks_no_update BEFORE UPDATE ON marks BEGIN
  SELECT RAISE(ABORT, 'marks table is append-only');
END;
CREATE TRIGGER marks_no_delete BEFORE DELETE ON marks BEGIN
  SELECT RAISE(ABORT, 'marks table is append-only');
END;

CREATE TABLE trades (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_mark_id INTEGER NOT NULL REFERENCES marks(id),
  tf            TEXT NOT NULL,
  strategy      TEXT NOT NULL,
  direction     TEXT NOT NULL,
  entry_ts      INTEGER NOT NULL,
  entry_price   REAL NOT NULL,
  sl            REAL NOT NULL,
  sl_mode       TEXT NOT NULL,
  target        REAL NOT NULL,
  time_cap_ts   INTEGER NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('open','closed')),
  exit_ts       INTEGER,
  exit_price    REAL,
  exit_reason   TEXT,
  r_multiple    REAL,
  htf_window_id INTEGER
);

CREATE TABLE checkpoints (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  tf                TEXT NOT NULL,
  ts                INTEGER NOT NULL,
  walker_state_json TEXT NOT NULL,
  open_trade_ids    TEXT NOT NULL,
  created_at        INTEGER NOT NULL
);
CREATE INDEX idx_checkpoints_tf_ts ON checkpoints(tf, ts DESC);
-- retention: keep latest N (e.g. 50) per tf, prune rest in a periodic job

CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
-- e.g. algo_version, bootstrap_completed_at, instrument list
```

Total footprint estimate: candles cache (~100KB for 2 TFs × 2000 rows) + marks (a few hundred rows/year × ~150 bytes ≈ tens of KB) + checkpoints (50 × 2 TFs × ~1KB ≈ 100KB) + trades (negligible). **Comfortably under 1MB**, well inside your "<100KB for rolling windows + marks" if you count only the live-critical tables and prune the candle cache tighter (e.g. 500 rows instead of 2000).

---

## 5. Verification API

```
GET /marks?tf=15m&from=2026-01-01T00:00:00Z&to=2026-02-01T00:00:00Z
→ 200 OK
{
  "tf": "15m",
  "algo_version": 3,
  "marks": [
    {"id": 1042, "ts": 1735776000, "kind": "FLIP", "direction": "short",
     "price": 95465.0, "swing_no": 214, "swing_kind": "down"},
    ...
  ],
  "count": 28
}

GET /trades?status=open
GET /trades?from=&to=&strategy=master1
GET /state/checkpoint?tf=1h            # latest WalkerState, for debugging/audit
GET /verify?tf=15m&from=&to=           # runs a fresh bootstrap-style replay over
                                        # the requested range from stored candles
                                        # (or refetched from Binance) and diffs
                                        # against the journaled marks table.
                                        # Returns {"match": true} or a list of diffs.
```

`/verify` is the important one: it's a standing, on-demand proof. Point it at the same date range you'd chart in the backtest, and it tells you programmatically whether live and backtest agree — you don't have to eyeball two charts.

---

## 6. Edge Cases

| Case | Handling |
|---|---|
| **Volatile candle "falling off"** | Doesn't apply — nothing ever falls off. State only grows forward. This entire class of bug is eliminated by construction. |
| **Exchange downtime / missed poll** | Next successful poll fetches all closed candles since `last_candle_ts` via Binance's paginated klines endpoint; §3.7 replay handles any gap size. |
| **Gap with actually-missing exchange data** (Binance itself has a hole) | `assert_no_gaps` in §3.7 halts processing and alerts rather than silently skipping — silent skips are how you get a divergent chain. Manual review required; this should be rare and is a Binance-side data integrity issue, not an engine bug. |
| **Process crash mid-candle** | At most one candle is reprocessed on restart (checkpoint is per-candle, mark insert is idempotent via UNIQUE constraint). |
| **Open trade spanning a restart, still open after 16+ days of downtime** | Time-cap check in `monitor_open_trades` is driven by candle timestamp vs `trade.time_cap_ts`, not wall-clock "now" — so replaying the missed candles during catch-up closes it at the *correct* historical bar, exactly as if the bot had never gone down. |
| **Algorithm change (bug fix, new rule)** | Bump `algo_version`. Do **not** retroactively touch journaled marks. Re-run bootstrap from `algo_version`'s effective date forward into a *new* checkpoint lineage; old marks stay attributed to the old version for audit. Never mutate history. |
| **Clock skew / candle timestamp ambiguity** | Always use candle **open time** as canonical `ts` (matches Binance kline convention) and only ever act on `closed=true` candles; never process a provisional/forming candle. |
| **SQLite corruption** | WAL mode + `state_hash` field in WalkerState lets you detect a corrupted checkpoint on load (hash mismatch) and fall back to the next-most-recent checkpoint, replaying the difference. This is why keeping a handful of recent checkpoints (not just the latest) is worth the extra ~50KB. |
| **Duplicate/out-of-order candles from REST API** | `PRIMARY KEY (tf, ts)` on the candles cache plus explicit sort-by-ts before feeding `step()` in sequence guards this. |

---

## 7. Proof of Correctness (sketch)

**Claim**: For any sequence of closed candles `C = [c_1, ..., c_n]` in chronological order, running `step()` over `C` starting from `WalkerState.initial()` produces the same final state and same mark sequence regardless of whether it's done in one pass (backtest) or in multiple passes with checkpointing in between (live + restarts).

**Argument**: `step: (State, Candle) -> (State, Mark[])` is a pure, deterministic function — it reads only its two arguments, has no reference to "how many candles came before" or "what the window looks like," and produces a new `State` that is a complete summary of everything `step` will ever need going forward (this is the invariant you must guarantee when writing `step` — see §7.1 below for what that requires). Given that, folding `step` over `C` is associative:

```
fold(step, C, init) == fold(step, C[k:], fold(step, C[:k], init))   for any k
```

This is just function composition — splitting the fold at any checkpoint boundary `k` and resuming from the intermediate state is mathematically identical to never splitting it. That's the entire proof. It's not an empirical property you verify by testing window sizes; it's a structural property of the function signature. The `/verify` endpoint (§5) exists to give you an *empirical* re-check of this *structural* guarantee, which is good practice, but the guarantee itself doesn't depend on the check passing — it depends on `step()` being written to the invariant.

### 7.1 The One Discipline This Requires
`step()` must never read anything except `state` and `candle`. In particular:
- No "look back N candles" logic inside `step` — anything it needs from the past must already be captured in `state` (this is exactly why `WalkerState` has the chop rings, the since-end extremes, etc., as explicit fields rather than "go compute this from the last 14 candles").
- No wall-clock reads inside `step` (time-cap logic uses `candle.ts`, never `now()`).
- No I/O, no randomness.

This is a code-review checklist item, not a runtime check: audit `step()` (and everything it calls) once, confirm it only touches its arguments, and the correctness proof holds for all time, including logic you haven't written yet — as long as new logic obeys the same discipline.

---

## 8. How Existing Systems Handle This (for context)

You asked how others solve it — the honest answer is that most of them **don't fully solve it**, which is exactly the failure mode you're worried about:

- **MetaTrader 4/5**: indicators recalculate over the visible chart buffer on every tick; MT4 in particular is notorious for "indicator repaint" on history vs. live precisely because of this window-recompute pattern. It works fine for indicators where a redraw is cosmetic, but it's a known source of backtest/live mismatch for path-dependent logic — which is your exact complaint.
- **TradingView Pine Script `security()`**: has the well-documented "repainting" problem when pulling higher-timeframe data, for the same underlying reason — it recomputes against the currently visible/available bars rather than maintaining forward-only state. TradingView's own docs warn against using `security()` naively for this reason.
- **QuantConnect/Lean**: uses an explicit "warm-up period" (`SetWarmUp`) — conceptually close to your bootstrap step — where indicators are fed historical data once at start to reach a valid state, then updated incrementally tick-by-tick/bar-by-bar afterward. This is the same forward-only-state pattern recommended above; Lean's indicators are literally implemented as incremental/streaming objects, not window-recompute objects.
- **Freqtrade**: uses a `startup_candle_count` to warm up indicators before the strategy is considered "ready," then processes new candles incrementally; state persistence across restarts is handled via its SQLite trade database, though its indicator/signal state itself is typically recomputed from a bounded dataframe window on each cycle (closer to your Attempt 2/3 than to full incremental state) — which is a known limitation people work around by using sufficiently long `startup_candle_count`.
- **Backtrader/Zipline**: both process bar-by-bar with indicator objects that maintain internal incremental state (ring buffers sized to what the indicator actually needs, e.g. a 14-period SMA only needs a 14-slot buffer, not the whole history) — structurally the same idea as `WalkerState`'s chop rings.
- **Prop/institutional systems**: generally lean hardest into exactly the pattern above — deterministic, pure "event → state transition" cores (often literally implemented as event-sourced systems) precisely because "live must match backtest, provably" is a hard requirement, not a nice-to-have, when real capital is on the line. Event sourcing (append-only event log + derivable state) is the same shape as your `marks` table (append-only) + `WalkerState` (derived, checkpointed) — you've actually already arrived at the right architecture family from first principles.

The pattern across the ones that get it right: **incremental/streaming state that's warmed up once, not windowed and recomputed.** That's the whole design above.

---

## 9. Success Criteria Mapping

| Criterion | How this design satisfies it |
|---|---|
| Live marks match backtest 30+ days | Structural guarantee via §7, not empirical luck |
| Kill/restart without losing state | Per-candle checkpoint, §3.7 |
| Down 16+ days, resolve trades correctly | Time-cap uses candle ts not wall clock; catch-up replay closes trades on the correct historical bar |
| Storage < 100KB | WalkerState + marks + trimmed checkpoints; candle cache is prunable/optional |
| < 10ms/candle | `step()` touches O(1) state, no window scans |
| Verification endpoint | `/marks` + `/verify` (§5) |
| No mark ever changes | DB-enforced append-only trigger (§4) |

---

## 10. Suggested Build Order

1. Implement `step()` as a pure function with unit tests that feed it hand-crafted candle sequences and assert exact marks — this is where the actual trading logic risk lives, get it right in isolation first.
2. Run `step()` over your existing 129k-candle CSV in both "one pass" and "split at candle 60,000, checkpoint, resume" modes; diff the two mark sequences. They should be byte-identical — this is your empirical proof that the fold is associative in your actual implementation, not just in theory.
3. Wire up SQLite schema, bootstrap script, live loop, catch-up.
4. Add the verification API last, once you trust the core.
5. Run against Binance testnet or a paper-trading feed for a couple weeks before real capital, watching `/verify` daily.

---

chatgpt:
Absolutely. **If you're going to hand this to your coder, I would change the current design direction now.**

The key instruction to your coder should be:

> **Do NOT rebuild the swing walker from the last 500 candles after every restart. The live engine must persist the walker's state and continue the state machine from the last committed candle.**

That is the central solution.

### The architecture I recommend

```text
                    Binance REST
                         │
                         ▼
                 Closed Candle Fetcher
                         │
                ┌────────┴────────┐
                ▼                 ▼
             15m Queue           1h Queue
                │                 │
                ▼                 ▼
          ┌────────────┐    ┌────────────┐
          │ 15m Walker │    │ 1h Walker  │
          │ persistent │    │ persistent │
          │ state      │    │ state      │
          └─────┬──────┘    └─────┬──────┘
                │                  │
                ▼                  ▼
             Marks              HTF Bias
                │                  │
                └────────┬─────────┘
                         ▼
                  Trade Engine
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
             SL          3R        16-day
              │          │          │
              └──────────┼──────────┘
                         ▼
                   Trade Journal
                         │
                         ▼
                      SQLite
```

The important thing is that the **walker is a state machine**, not a function that needs to rediscover its entire history every time.

QuantConnect's LEAN uses a related idea during live startup: historical data is replayed through the algorithm to establish its state before live processing begins. ([QuantConnect][1])

---

# 1. Kill the "rolling window = source of truth" idea

Your current:

```text
500 candles
    ↓
recalculate walker
    ↓
look at latest mark
    ↓
discard old state
```

is **not guaranteed equivalent** to:

```text
129,306 historical candles
    ↓
walker
    ↓
state at candle N
```

Your own experiments already demonstrate this.

The fact that 500 candles happened to reproduce your tested tail doesn't prove that it always will.

A future volatility event could expose exactly the failure you're worried about.

So:

### Rolling candles should be a cache.

Not the source of truth.

---

# 2. Persist the walker state

Your coder needs to identify **every variable inside the swing walker that depends on previous candles**.

Something conceptually like:

```python
WalkerState(
    last_processed_ts,
    swing_no,
    swing_kind,

    seg_start,
    prev_end,

    current_pivot,
    current_extreme,

    direction,

    # whatever your actual walker uses
    ...
)
```

The exact fields must come from your existing walker implementation.

The rule is:

> If changing the value can change what the walker does on the next candle, it belongs in persistent state.

Then after candle `N`:

```text
state(N)
   +
candle(N+1)
   ↓
state(N+1)
```

rather than:

```text
candle[N-500:N+1]
   ↓
reconstruct everything
```

---

# 3. The database becomes the memory of the strategy

I would use SQLite with roughly these tables.

### `engine_state`

```sql
CREATE TABLE engine_state (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    last_candle_ts INTEGER NOT NULL,

    state_blob BLOB NOT NULL,

    state_version INTEGER NOT NULL,

    updated_at INTEGER NOT NULL,

    PRIMARY KEY(symbol, timeframe)
);
```

This stores the **exact serialized walker state**.

For example:

```text
BTCUSDT
15m
2026-09-09 18:45
[state after 18:45]
```

and independently:

```text
BTCUSDT
1h
2026-09-09 18:00
[state after 18:00]
```

The 15m and 1h chains remain completely independent.

---

# 4. Marks must be immutable

Use an append-only table:

```sql
CREATE TABLE marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    candle_ts INTEGER NOT NULL,

    kind TEXT NOT NULL,
    direction TEXT NOT NULL,

    price REAL NOT NULL,

    swing_no INTEGER NOT NULL,
    swing_kind TEXT NOT NULL,

    state_hash TEXT NOT NULL,

    created_at INTEGER NOT NULL,

    UNIQUE(symbol, timeframe, candle_ts, kind, direction, swing_no)
);
```

Once:

```text
2026-09-09 14:15
B2
LONG
111234.50
swing 827
```

is inserted, **never UPDATE it**.

If your algorithm later produces something different, that's not something to silently overwrite.

That's an integrity failure that needs investigation.

---

# 5. Even more important: persist a state hash

This is one thing I'd strongly recommend adding.

After processing every candle:

```python
state_hash = SHA256(
    canonical_json(walker_state)
)
```

Store it.

So you have:

```text
candle
   ↓
walker
   ↓
state
   ↓
SHA256
   ↓
SQLite
```

Now you can prove:

```text
State after candle 1000
        ==
State after candle 1000 during backtest
```

not merely:

```text
"the mark looks right"
```

That's much stronger.

---

# 6. Your backtest and live engine must share ONE walker

This is probably the most important coding rule.

Don't have:

```text
backtest_walker.py
live_walker.py
```

with similar logic.

Have:

```text
walker.py
```

and both systems call the same function:

```python
state = walker.process(candle, state)
```

For example:

```python
result = walker.process(
    state=current_state,
    candle=candle
)

new_state = result.state
marks = result.marks
```

Then:

### Backtest

```text
historical candles
       ↓
walker.process()
       ↓
state
       ↓
marks
```

### Live

```text
REST candle
       ↓
walker.process()
       ↓
state
       ↓
marks
```

Same input.

Same state.

Same function.

Therefore the deterministic result should be the same.

---

# 7. Restart becomes extremely simple

Suppose the VPS dies at:

```text
15m candle:
2026-09-01 12:45
```

SQLite contains:

```text
last_processed = 12:45
state = S(12:45)
```

Bot starts again.

It asks Binance:

```text
Give me candles after 12:45
```

Suppose the bot was down for 10 days.

It gets:

```text
12:45
13:00
13:15
...
10 days later
```

Then:

```python
for candle in missing_candles:
    process(candle)
```

**in chronological order.**

That's it.

It doesn't matter whether downtime was:

```text
1 hour
1 day
16 days
3 months
```

The algorithm just replays the missing candles.

---

# 8. Do NOT process the latest candle if it isn't closed

This is another critical rule.

Your engine should operate on:

```text
closed candles only
```

not:

```text
currently forming candle
```

TradingView itself distinguishes historical/confirmed bars from the realtime bar, and its execution model recalculates an open realtime bar as its OHLC values change. ([TradingView][2])

Your engine can avoid this entire class of problems:

```text
Binance
   ↓
latest candle
   ↓
is it CLOSED?
   │
   ├── NO → ignore
   │
   └── YES
          ↓
       process
```

This also makes your mark journal much safer.

---

# 9. Candle identity must be timestamp-based

Don't trust:

```python
last_candle_index += 1
```

Use the exchange candle's open timestamp.

For example:

```text
15m:

12:00
12:15
12:30
12:45
13:00
```

Before processing:

```python
if candle.open_time <= state.last_candle_ts:
    ignore()
```

And verify:

```python
expected = previous_ts + interval
actual = candle.open_time
```

If:

```text
actual != expected
```

you have a gap.

---

# 10. Gaps must trigger catch-up, not improvisation

Suppose:

```text
10:00
10:15
10:30
10:45
```

but REST gives:

```text
10:00
10:15
10:45
```

Never do:

```text
10:15 → 10:45
```

as though nothing happened.

Instead:

```text
GAP DETECTED
      ↓
REST backfill
      ↓
10:30
      ↓
process
      ↓
10:45
      ↓
process
```

Freqtrade has a similar concept around detecting stale/outdated candle data rather than simply treating it as valid current data. ([Freqtrade][3])

---

# 11. Atomic transaction per candle

This is how you survive a VPS crash **without corrupting the state machine**.

When processing candle X:

```text
BEGIN TRANSACTION

    insert candle / update candle metadata

    walker.process()

    insert marks

    update engine_state

    process trade

    insert trade events

    update trade state

COMMIT
```

Only after `COMMIT` is the candle considered processed.

Therefore you never want this:

```text
walker state updated
       ↓
CRASH
       ↓
mark wasn't saved
```

or:

```text
mark saved
       ↓
CRASH
       ↓
walker state wasn't saved
```

Both create inconsistencies.

---

# 12. Use the database transaction as the checkpoint

This gives you a beautiful invariant:

> **Either the entire candle processing succeeds, or none of it exists.**

Example:

```text
Candle 10:00

walker state S0
       ↓
process
       ↓
S1
       ↓
B2 generated
       ↓
trade opened
       ↓
COMMIT
```

After commit:

```text
SQLite:

last_candle = 10:00
state = S1
mark = B2
trade = OPEN
```

If the VPS dies **before commit**:

```text
SQLite still says:

last_candle = 09:45
state = S0
```

So on restart:

```text
10:00 gets replayed
```

Correctly.

---

# 13. Trade state should also be event-based

Don't just store:

```text
trade.status = OPEN
```

I'd have:

```sql
CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    direction TEXT NOT NULL,

    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,

    sl REAL NOT NULL,
    target REAL NOT NULL,

    risk REAL NOT NULL,

    exit_ts INTEGER,
    exit_price REAL,

    exit_reason TEXT,

    pnl_r REAL,

    status TEXT NOT NULL
);
```

And optionally:

```sql
CREATE TABLE trade_events (
    id INTEGER PRIMARY KEY,

    trade_id INTEGER NOT NULL,

    event_ts INTEGER NOT NULL,

    event_type TEXT NOT NULL,

    price REAL,

    payload TEXT
);
```

Then you can see:

```text
ENTRY
SL_UPDATE
TARGET_CHECK
TIME_CAP
EXIT
```

This makes debugging dramatically easier.

---

# 14. The 16-day rule becomes deterministic

Store:

```text
entry candle index
```

or preferably:

```text
entry timestamp
```

Then derive:

```python
cap_ts = entry_ts + 16 days
```

But because your backtest specifically defines the cap in **bars**, I would preserve the exact backtest semantics:

```python
cap_idx = entry_idx + cap_bars
```

For 15m:

```text
16 × 24 × 4 = 1536
```

For 1h:

```text
16 × 24 = 384
```

Don't replace this with a vaguely equivalent wall-clock implementation unless the backtest itself is changed.

---

# 15. SL/TP checking needs the exact same ambiguity rules as backtest

This is an area where your coder needs to be extremely careful.

Suppose one candle is:

```text
HIGH = 110
LOW  = 90
```

and your trade has:

```text
SL = 95
TP = 108
```

Both were touched.

With OHLC candles alone, you don't know whether price did:

```text
95 → 108
```

or:

```text
108 → 95
```

during the candle.

Therefore your backtest must have a deterministic rule such as:

```text
SL wins
```

or:

```text
TP wins
```

or a lower-timeframe/tick reconstruction.

**Live must use exactly the same rule.**

Otherwise:

```text
Backtest = +3R
Live     = -1R
```

even though both consumed the exact same candle.

---

# 16. HTF/LTF should also be event-driven

Don't make the 15m engine constantly ask:

```python
"what is the current 1h bias?"
```

Instead persist the HTF state:

```text
1h walker
   ↓
FLIP
   ↓
bias changes
   ↓
SQLite
```

Then 15m reads the latest **committed 1h bias**.

Conceptually:

```text
1h:

candle
 ↓
walker
 ↓
FLIP?
 ↓
bias = LONG
 ↓
persist
```

Then:

```text
15m:

mark = B2 LONG
bias = LONG
      ↓
eligible
```

---

# 17. Your verification endpoint should be more powerful than `/marks`

I recommend:

```http
GET /verify/marks
```

Parameters:

```text
symbol=BTCUSDT
timeframe=15m
from=2026-08-01
to=2026-09-01
```

Return:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "from": "...",
  "to": "...",
  "engine_version": "walker-v18",
  "state_version": 3,
  "marks": [
    {
      "timestamp": "...",
      "kind": "B2",
      "direction": "LONG",
      "price": 111234.5,
      "swing_no": 827
    }
  ]
}
```

But I'd add:

```json
{
  "state_hash": "...",
  "mark_count": 17,
  "journal_hash": "..."
}
```

Now you can compare live vs backtest mechanically.

---

# 18. Better: create a replay verifier

This is the tool I'd have your coder build **before real money goes anywhere near the system**.

```bash
python verify.py \
    --symbol BTCUSDT \
    --timeframe 15m \
    --from 2026-01-01 \
    --to 2026-09-01
```

It downloads/loads historical candles and runs:

```text
Backtest walker
       │
       ▼
Expected marks

        VS

Persisted live journal
       │
       ▼
Actual marks
```

Then produces:

```text
Candles compared: 23,481

Marks expected: 384
Marks actual:   384

Timestamp mismatches: 0
Kind mismatches:      0
Direction mismatches: 0
Price mismatches:     0
Swing mismatches:     0

STATE HASH MISMATCHES: 0

RESULT: PASS
```

That is much more meaningful than visually checking a TradingView chart.

---

# 19. Your 100 KB requirement is the one I'd challenge

This is important.

You said:

> Storage <100 KB for rolling windows + marks.

If you want:

> **mathematical guarantee of recovery after arbitrary downtime**

then **100 KB cannot be treated as an absolute requirement for arbitrary historical retention**.

But there's a good solution.

You don't need to store all historical candles.

You need to store:

```text
1. current state
2. marks
3. open trades
4. metadata/checkpoints
```

Historical candles can be fetched again from Binance during recovery.

So:

```text
LOCAL STORAGE
────────────────────
walker state
marks
trades
checkpoints
configuration
────────────────────

REMOTE / EXCHANGE
────────────────────
historical candles
```

This is the crucial distinction.

---

# 20. But don't delete all candles blindly

Keep a small cache:

```text
15m: 500–1000 candles
1h:  300–500 candles
```

for:

* debugging
* verification
* SL/TP processing
* recent API recovery
* operational visibility

But the cache is **not the source of strategy truth**.

The source of truth is:

```text
persisted state + immutable journal
```

---

# 21. What happens if the VPS is down for 3 weeks?

This is where the design really shines.

Suppose:

```text
Last state:

2026-08-15 12:00
```

Bot comes back:

```text
2026-09-09
```

It queries:

```text
Binance REST
```

for the missing candles.

Then:

```text
S(08/15 12:00)
       ↓
08/15 12:15
       ↓
08/15 12:30
       ↓
...
       ↓
09/09
```

Every candle gets processed **exactly once in chronological order**.

The walker never needs to know that the VPS was dead.

It simply sees:

```text
previous candle
→ next candle
```

This is essentially the same philosophy behind warm-up/replay systems such as LEAN: historical data is fed through the algorithm to reconstruct its operational state before live processing resumes. ([QuantConnect][1])

---

# 22. What if Binance itself changes historical candle data?

This is a different problem.

Your guarantee is only:

> Given the same candle sequence and same initial state, the walker produces the same marks.

If Binance later corrects historical OHLC data, then:

```text
old candle ≠ new candle
```

and therefore the deterministic output can legitimately differ.

So your coder should store a **candle fingerprint** for every processed candle, at least for candles used during live operation.

For example:

```text
SHA256(
    timestamp |
    open |
    high |
    low |
    close |
    volume
)
```

Then you know exactly which market data generated your mark.

---

# 23. This gives you the real mathematical guarantee

Your proof becomes:

### Assumption 1

Backtest and live use identical candle data.

### Assumption 2

Backtest and live use the same walker implementation/version.

### Assumption 3

The initial state is identical.

### Assumption 4

Candles are processed in identical chronological order.

### Assumption 5

Each candle is committed atomically.

Then:

```text
S0
 │
 ├── C1 → S1
 │
 ├── C2 → S2
 │
 ├── C3 → S3
 │
 ...
 │
 └── Cn → Sn
```

is deterministic.

Therefore:

```text
Backtest(S0, C1...Cn)
          =
Live(S0, C1...Cn)
```

and consequently:

```text
Marks_backtest = Marks_live
```

That's the guarantee you're actually looking for.

Not:

> "500 candles seems to work."

---

# 24. What your coder should build first

I would give your coder this exact development order:

### Phase 1 — Extract the walker

Create:

```text
walker/
    state.py
    walker.py
    marks.py
```

with:

```python
new_state, marks = process(state, candle)
```

No database yet.

---

### Phase 2 — Determinism test

Run:

```text
129,306 candles
```

through it.

Save:

```text
state hash
marks
```

Then run it again.

Must produce:

```text
100% identical
```

---

### Phase 3 — Checkpointing

Add:

```text
SQLite engine_state
```

After every candle:

```text
state → SQLite
```

---

### Phase 4 — Crash testing

Artificially kill the program:

```text
after candle 10
after candle 100
after candle 1000
...
```

Restart.

Verify:

```text
marks == uninterrupted run
state_hash == uninterrupted run
```

This is **extremely important**.

---

### Phase 5 — Downtime testing

Simulate:

```text
1 hour
1 day
7 days
16 days
30 days
```

of missing candles.

Restart and replay.

Expected:

```text
same final state
same marks
same trades
```

---

### Phase 6 — Trade engine

Only after the walker is proven.

Implement:

```text
entry
SL
3R
16-day cap
exit
PnL
```

as a separate deterministic state machine.

---

### Phase 7 — HTF/LTF

Then combine:

```text
1h state
     ↓
bias
     ↓
15m eligibility
```

---

### Phase 8 — Live Binance adapter

Only now connect:

```text
Binance REST
```

The exchange adapter should be stupid.

Its job is only:

```text
download candles
validate candles
sort candles
feed candles to engine
```

It should **not contain trading logic**.

---

# 25. The final project structure I'd give your coder

```text
trading_engine/

├── engine/
│   ├── candle.py
│   ├── walker.py
│   ├── walker_state.py
│   ├── mark.py
│   ├── trade_engine.py
│   ├── bias.py
│   └── deterministic.py
│
├── data/
│   ├── binance.py
│   ├── backfill.py
│   └── validator.py
│
├── persistence/
│   ├── database.py
│   ├── state_store.py
│   ├── mark_store.py
│   └── trade_store.py
│
├── verification/
│   ├── replay.py
│   ├── compare.py
│   └── hashes.py
│
├── api/
│   └── verification_api.py
│
├── tests/
│   ├── test_walker.py
│   ├── test_determinism.py
│   ├── test_restart.py
│   ├── test_gap_recovery.py
│   ├── test_trade_engine.py
│   └── test_backtest_equivalence.py
│
└── main.py
```

---

# The one sentence I'd send your coder

> **Don't persist a rolling window and reconstruct the strategy; persist the strategy's state and use the rolling window only as a cache. On restart, load the last committed state and replay missing closed candles from Binance in chronological order. Backtest and live must call the exact same deterministic `process(state, candle)` function, with atomic SQLite checkpoint + journal commits per candle.**

That's the architecture I'd be comfortable putting through serious validation.

And importantly, **TradingView's execution model reinforces why confirmed/closed bars and committed state matter**, while LEAN's warm-up approach reinforces the replay-from-history model. ([TradingView][2])

If your coder gives you a design that says **"we'll just keep 500 candles and recalculate the walker on startup"**, I would reject that design for your stated requirement.

[1]: https://www.quantconnect.com/docs/v2/writing-algorithms/historical-data/warm-up-periods?utm_source=chatgpt.com "Warm Up Periods - QuantConnect.com"
[2]: https://www.tradingview.com/pine-script-docs/language/execution-model/?utm_source=chatgpt.com "Language / Execution model"
[3]: https://docs.freqtrade.io/en/stable/faq/?utm_source=chatgpt.com "FAQ - Freqtrade"

