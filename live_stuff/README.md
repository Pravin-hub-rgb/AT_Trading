# Backbencher - Live Trading Engine

**Codename:** Backbencher
**The student who fails every win-rate exam (36.4%) yet tops the life game (+331R gross, PF 2.81).**

> ## ⚠️ NEW CHAT? START HERE
> **Read `docs/HANDOFF.md` FIRST.** It has the true build status, the verified v18
> parameter matrix, what to keep/kill in this folder, and the exact next steps.
> The code in `engine/` is a toy placeholder — do NOT trust it or extend it.

---

## What Is This?

A production-grade live trading engine for BTCUSDT that:
- Produces marks (B1, B2, FLIP) identical to full-history backtest
- Runs on a small VPS (1GB RAM, limited storage)
- Survives restarts, downtime (hours to weeks), and network gaps
- Tracks open trades (bias, SL, 3R, 16-day exit) across restarts
- Is verifiable: compare live marks against backtest daily

---

## Strategy

**v18 HTF-LTF Streak Halt 5L:**
- **HTF (1h):** Determines bias direction and regime
  - HIGH chop (>61.8): use B2 entries
  - LOW chop (≤61.8): use Flip entries
- **LTF (15m):** Precise entry after HTF bias established
- **Trade:** Entry at mark, SL at pivot (-1R), TP at 3R, cap at 16 days
- **Cooldown:** 20 bars after every loss
- **Streak halt:** Halt after 5 consecutive losses, resume on next winner

---

## Installation

### Local Development

```bash
# Clone the repo
git clone git@github.com:Pravin-hub-rgb/AT_Trading.git
cd AT_Trading/live_stuff

# No external dependencies for core engine!
# Only need websocket-client for live ticks:
pip install websocket-client
```

### VPS Deployment

```bash
# On VPS (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip

# Copy files to VPS
scp -r live_stuff/ user@vps:/home/user/

# On VPS
cd live_stuff
pip3 install websocket-client

# Run
python3 main.py
```

---

## Usage

### Run Forever (Live Trading)

```bash
python main.py
```

### Run for Testing (120 seconds)


## Architecture

### Core Principle

**Persist the walker's STATE, not the candles.**

- Walker state = 10 numbers (< 1KB)
- New candle arrives → take one step forward → save new state
- On restart → load state + replay missing candles = identical result

### 4 Layers

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


## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /marks?tf=15m&from=...&to=...` | Get marks for timeframe |
| `GET /verify?date=YYYY-MM-DD` | Daily parity check |

---

## Verification

### Daily Parity Check

Compare live journal against backtest for a given day:

```python
from verification.parity import daily_parity_check, format_parity_report

results = daily_parity_check(db, "2026-09-09", backtest_15m, backtest_1h)
print(format_parity_report(results))
```

### Replay

Replay candles through walker to verify state:

```python
from verification.replay import replay_15m

state, marks = replay_15m(candles, initial_state)
assert state.compute_hash() == expected_hash
```

---

## Database Schema

### walker_state
```sql
CREATE TABLE walker_state (
    tf TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
```

### marks (append-only)
```sql
CREATE TABLE marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    tf TEXT NOT NULL,
    kind TEXT NOT NULL,
    direction TEXT NOT NULL,
    price REAL NOT NULL,
    swing_no INTEGER NOT NULL,
    swing_kind TEXT NOT NULL,
    algo_version INTEGER NOT NULL DEFAULT 1,
    journaled_at INTEGER NOT NULL,
    UNIQUE (ts, tf, kind, direction, swing_no)
);
```

### htf_windows
```sql
CREATE TABLE htf_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    close_ts INTEGER,
    close_reason TEXT
);
```


## Testing

```bash
# Run all tests
python tests/test_walker.py
python tests/run_persistence_tests.py
python tests/test_trade_engine.py
python tests/test_data.py
python tests/test_loop.py
python tests/test_verification.py
```

---

## VPS Deployment Checklist

- [ ] Copy `live_stuff/` to VPS
- [ ] `pip3 install websocket-client`
- [ ] `python3 main.py 120` (test run)
- [ ] `python3 main.py` (live run)
- [ ] Set up systemd service for auto-restart
- [ ] Set up log rotation for `backbencher.db`

### Systemd Service

```ini
# /etc/systemd/system/backbencher.service
[Unit]
Description=Backbencher Trading Engine
After=network.target

[Service]
Type=simple
User=backbencher
WorkingDirectory=/home/backbencher/live_stuff
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

---

## References

- `docs/design.md` - Complete architecture design
- `docs/live_trading_doc.md` - Journey log and decisions
- `docs/backtest_checklist_v18.md` - v18 backtest validation
- `docs/design_challenge.md` - Original challenge sent to AIs

---

## License

Private - All rights reserved.

---

**Status:** Ready for VPS deployment
**Version:** 1.0.0
**Created:** 2026-09-09


### ltf_trades
```sql
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
```

+---------------------------------------------------------+
```

### Key Components

| Component | File | Purpose |
|---|---|---|
| Walker | `engine/walker.py` | Pure `step(state, candle)` function |
| WalkerState | `engine/walker_state.py` | 15m/1h state dataclasses |
| Mark | `engine/mark.py` | Swing break signals |
| HtfWindow | `engine/htf_window.py` | HTF bias window (16-day cap) |
| LtfTrade | `engine/ltf_trade.py` | LTF trade (entry/SL/TP/trailing) |
| TradeManager | `engine/trade_manager.py` | Orchestrates windows + trades |
| Database | `persistence/database.py` | SQLite schema + transactions |
| Binance | `data/binance.py` | REST API client |
| Streamer | `data/streamer.py` | WebSocket tick streamer |
| Bootstrap | `bootstrap.py` | First-run initialization |
| LiveLoop | `live_loop.py` | Main polling loop |


```bash
python main.py 120
```

### Run Paper Trading (default)

```bash
python main.py --paper
```

### Run Verification Server

```bash
python -c "from api.verify_endpoint import run_server; run_server()"
```
