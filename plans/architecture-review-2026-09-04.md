# AT_Trading — Architecture Review & Improvement Plan

**Date:** 2026-09-04
**Mode:** Architect

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AT_Trading                              │
├─────────────────────────────────────────────────────────────────┤
│  FRONTEND (Next.js)          │  BACKEND (Python FastAPI)        │
│  ├── LightweightCharts        │  ├── Data fetcher (Upstox API)   │
│  ├── Swing SR primitives     │  ├── Bias engine                 │
│  ├── Flow line primitives    │  ├── First swing engine          │
│  └── Intraday panel          │  ├── Swing engine                │
│                              │  ├── Intraday (5min + 1min)      │
│                              │  └── Walker (pivot detection)   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Upstox API → Python Backend → CSV files → Python Engines → JSON API → Next.js UI → LightweightCharts
```

---

## 2. Current Architecture Analysis

### 2.1 Backend Components (`backend/src/`)

| Component          | File                        | Purpose                             | Status        |
| ------------------ | --------------------------- | ----------------------------------- | ------------- |
| **Walker**         | `walker.py`                 | Pivot detection (fractal-based)     | ✅ Mature     |
| **FirstSwing**     | `firstswing.py`             | Detects 1st & 2nd swing per day     | ✅ Mature     |
| **Bias**           | `bias.py`                   | Initial bias (pre-open) computation | ✅ Mature     |
| **Swing**          | `swing.py`                  | Full swing detection engine         | ✅ Mature     |
| **Intraday 5min**  | `intraday.py`               | 5min-based entry system             | ✅ Mature     |
| **Intraday 1min**  | `intraday_1m_standalone.py` | 1min independent entry system       | ✅ Mature     |
| **Scheduler**      | `scheduler.py`              | Data download scheduling            | ✅ Functional |
| **Upstox Fetcher** | `upstox_fetcher.py`         | API data fetching                   | ✅ Functional |

### 2.2 Frontend Components (`frontend/src/`)

| Component             | Purpose                           | Status           |
| --------------------- | --------------------------------- | ---------------- |
| **StockChart**        | Main chart with LightweightCharts | ✅ Rich features |
| **SwingSRPrimitive**  | Swing S/R level rendering         | ✅ Functional    |
| **FlowLinePrimitive** | Flow line visualization           | ✅ Functional    |
| **PositionPrimitive** | Trade markers & P&L display       | ✅ Functional    |
| **IntradayPanel**     | Intraday controls & settings      | ✅ Functional    |

### 2.3 Key Architectural Decisions (Good)

| Decision                             | Rationale                                          |
| ------------------------------------ | -------------------------------------------------- |
| **Python ↔ TypeScript parity**       | Backend `firstswing.py` is port of `firstswing.ts` |
| **Two engine modes**                 | 5min (reference) + 1min (precise entry)            |
| **Caching**                          | Data mtime-based cache invalidation                |
| **Walker is single source of truth** | Consistent pivot detection across engines          |

---

## 3. Current Performance Issues

### From `fix/ideas.md` and `fix/problems.md`:

| Metric       | Value   | Assessment                      |
| ------------ | ------- | ------------------------------- |
| Total Trades | 262     | ⚠️ Low frequency                |
| Win Rate     | 43.5%   | ❌ Below breakeven              |
| Total R      | -33.32  | ❌ Negative expectancy          |
| Avg R        | -0.13   | ❌ Small losses                 |
| Long/Short   | 155/107 | ⚠️ Bias long (no short filter?) |

### Known Issues Fixed (per `fix/problems.md`)

| #   | Issue                            | Status      |
| --- | -------------------------------- | ----------- |
| 1   | Conservative FS2 pivot dedup     | ✅ Resolved |
| 2   | Aggressive FS pivot dedup        | ✅ Resolved |
| 3   | SL prev_pivot wrong side         | ✅ Resolved |
| 4   | Reference rearm reset            | ✅ Resolved |
| 5   | Swing-end guard (close vs level) | ✅ Resolved |
| 6   | Broken level key (float only)    | ✅ Resolved |
| 7   | V-reversal same-bar arm          | ✅ Resolved |

### Open Questions from `fix/ideas.md`

1. **Trade count filter** — Want ability to set 1 or 2 trades/day
2. **Post-SL behavior** — Take another trade or wait for opposite swing?
3. **First swing entry timing** — Entry on next candle vs waiting
4. **System verification** — Confirm code does what theory says

---

## 4. Improvement Opportunities

### 4.1 Trade Management Filters

```
PROPOSED: Trade count per day + post-SL behavior
```

| Filter               | Options                               | Description                 |
| -------------------- | ------------------------------------- | --------------------------- |
| `max_trades_per_day` | 1, 2, unlimited                       | Stop trading after N trades |
| `post_sl_action`     | "new_swing", "same_swing", "skip_day" | What to do after SL hit     |
| `post_target_action` | "new_swing", "same_swing", "skip_day" | What to do after target hit |

**Implementation location:** `intraday_1m_standalone.py` `_can_trade()` + `simulate_day_1min()`

### 4.2 Short Selling Filter

```
PROBLEM: 155 long / 107 short — system may not be filtering shorts properly
```

| Config         | Purpose                                                      |
| -------------- | ------------------------------------------------------------ |
| `allow_shorts` | boolean — enable/disable short entries                       |
| `bias_respect` | "strict" / "loose" — how much bias must agree with direction |

### 4.3 First Swing Entry Timing

```
CURRENT: Entry on next candle after FS confirmation
ALTERNATIVE: Wait for retracement + confirmation
```

Add config:

```
fs_entry_mode: "immediate" | "retracement"
retracement_min_pct: 0.3  # 30% retracement required
```

### 4.4 Backend API Enhancements

| Endpoint                | Current             | Proposed                                             |
| ----------------------- | ------------------- | ---------------------------------------------------- |
| `/api/backtest`         | Returns all results | Add `?filters=trades,summary` for selective response |
| `/api/bias`             | Returns labels      | Add `?date=YYYY-MM-DD` for specific day              |
| New: `/api/diagnostics` | N/A                 | Run integrity checks, return JSON                    |

### 4.5 Performance Optimizations

| Area                   | Current       | Optimization                     |
| ---------------------- | ------------- | -------------------------------- |
| **Cache invalidation** | Mtime-based   | Add LRU with TTL                 |
| **Data loading**       | Full CSV read | Use `chunksize` for large files  |
| **Swing detection**    | Per-day loop  | Vectorized pandas where possible |

### 4.6 Testing Infrastructure

```
PROPOSED: Automated diagnostic runner
```

| Test                       | Scope                                      | Frequency  |
| -------------------------- | ------------------------------------------ | ---------- |
| `test_swing_engine_parity` | Backend vs frontend swing detection        | Per PR     |
| `test_pivot_regression`    | Walker pivot consistency                   | Daily      |
| `test_entry_theory`        | Verify code matches `docs/entry theory.md` | Per change |
| `test_stats_stability`     | Detect WR/R changes > 5%                   | Weekly     |

---

## 5. Proposed Architecture Diagram

```mermaid
flowchart TB
    subgraph Data["Data Layer"]
        CSV[CSV Files<br/>nifty_5min.csv<br/>nifty_1min.csv<br/>nifty_daily.csv]
        ENV[.env<br/>Upstox credentials]
    end

    subgraph Services["Backend Services"]
        Fetcher[Upstox Fetcher<br/>scheduler.py]
        Bias[Bias Engine<br/>bias.py]
        Walker[Walker Engine<br/>walker.py]
        FS[First Swing<br/>firstswing.py]
        Swing[Intraday 5min<br/>intraday.py]
        Intra1m[Intraday 1min<br/>intraday_1m_standalone.py]
    end

    subgraph API["FastAPI Server"]
        GET[/api/bias]
        POST[/api/backtest]
        GET[/api/swings]
        GET[/api/data/status]
    end

    subgraph Frontend["Next.js Frontend"]
        Chart[StockChart.tsx<br/>LightweightCharts]
        Panel[IntradayPanel]
        Primitives[Swing/Flow<br/>Primitives]
    end

    CSV --> Fetcher
    CSV --> Bias
    CSV --> Walker
    Walker --> FS
    Walker --> Swing
    Walker --> Intra1m
    Bias --> Swing
    Bias --> Intra1m
    FS --> Swing
    FS --> Intra1m

    Fetcher -->|HTTP| Upstox[Upstox API]

    Swing --> API
    Intra1m --> API
    API -->|JSON| Frontend
    Frontend --> Chart
    Frontend --> Panel
```

---

## 6. Recommended Next Steps (Priority Order)

| Priority | Task                          | Rationale              | Effort |
| -------- | ----------------------------- | ---------------------- | ------ |
| P0       | **Add trade count filter**    | User-requested feature | Low    |
| P0       | **Verify system correctness** | Confirm theory=code    | Medium |
| P1       | **Short selling filter**      | Fix directional bias   | Low    |
| P1       | **Post-SL behavior config**   | User-requested feature | Low    |
| P2       | **Diagnostic API endpoint**   | Improve debuggability  | Medium |
| P2       | **Test harness**              | Prevent regressions    | Medium |
| P3       | **Performance optimization**  | Future scalability     | Medium |

---

## 7. Questions for Discussion

1. **Trade count** — Do you want hard stop (no more trades) or skip-to-end-of-day?
2. **Short selling** — Should shorts be completely disabled, or just require stronger confirmation?
3. **First swing entry** — Immediate entry or wait for retracement?
4. **Win rate concern** — Is negative expectancy expected given market conditions, or is there a logic bug?

---

_This document is a starting point for discussion. Let me know which improvements you'd like to prioritize, and I'll create detailed specifications for them._
