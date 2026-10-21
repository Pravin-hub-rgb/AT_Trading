# Backbencher - Book 107 Live Engine

Self-contained live/paper engine for **book 107** (`fsent_champ_long_mcloff_htf15`).
Deploy this folder on its own; it has no imports from `backend/` or `backtest/`.

> **Status: paper/demo only.** Book 107 won the Gate-5 ordering but no book has
> cleared PBO/DSR yet. Do not point this at live capital until forward evidence
> clears the gate.

## Book 107

| | |
|---|---|
| Engine | vendored `unified` (`simulate_htf_ltf_streak_halt`) |
| Data | **15m + 1h only - no 1m** |
| Swing series | `htf15` (1h continuous, minBars 15) / 15m minBars 50 |
| Side | long-only |
| Chop | 58.0 |
| Cooldown | 8 bars |
| SL buffer | 0.01 ATR |
| Ext stop | 3.0R |
| HTF RR | 3.0 |
| Cap | 16 days |
| Streak halt | off (`max_consecutive_losses=0`) |

Parity on the IS dataset (2023-01-01 to 2026-09-13):

- pin basis (with 1m): **525 trades / +538.40R / DD 28.38R**
- live basis (no 1m): **526 trades / +537.13R / DD 29.65R**
- delta: +1 trade, -1.27R, +1.27R DD - accepted.

## Layout

| Path | Purpose |
|---|---|
| `main.py` | CLI entry point, paper/live switch, risk banner |
| `live_loop.py` | compatibility shim; import `LiveLoop` from here |
| `live/loop.py` | `LiveLoop` composition + event handlers |
| `live/feed.py` | seeding, crash recovery, backfill, candle normalisation |
| `live/state.py` | HTF metrics, swing/trade caches, restores, status |
| `live/signals.py` | engine run, journaling, regime/window tracking |
| `live/execution.py` | Bybit entry/exit, sizing, reconciliation |
| `live/risk.py` | daily loss, streak persistence, R maths |
| `live/trading.py` | live ticks and SL ratchet |
| `_vendored/` | sealed engine copy - see `_vendored/MANIFEST.md` |
| `persistence/` | SQLite schema, trade/mark/state stores |
| `book.py` | book 107 params + swing settings |
| `config.py` | symbol, windows, leverage, database path |
| `data_streamer.py` | Binance WebSocket + REST candles |
| `bybit_streamer.py` | Bybit WebSocket + REST candles |
| `bybit_order.py` | Bybit order execution and position queries |
| `rate_manager.py` | INR/USDT rate |
| `docs/seed_marks.json` | seed marks for fast cold start |

## Install

Python 3.10+.

```bash
pip install -r requirements.txt
```

## Run

```bash
# paper mode (default), Binance, forever
python main.py

# 120-second test run
python main.py 120

# Bybit paper
python main.py --exchange bybit --symbol BTCUSDT_BYBIT

# Bybit live orders - not advised until the gate clears
python main.py --live --exchange bybit --symbol BTCUSDT_BYBIT

# cold start with explicit seed timestamps (15m, then 1h)
python main.py "2026-09-01 00:00" "2026-09-01 00:00"
```

State is stored in `backbencher.db`. Edit `risk_inr.txt` to change risk per
trade without a restart. `.env` (see `.env.example`) holds API keys and is
ignored by git.

## Deploy

Copy only this folder to the VPS. Exclude `.env`, `backbencher.db`,
`last_rate.json`, `test_out.txt`, `test_err.txt`, and `__pycache__`.

```bash
scp -r live_stuff/ user@vps:/home/user/
cd live_stuff
pip3 install -r requirements.txt
python3 main.py
```

Keep it under systemd with `Restart=always`; the loop recovers from downtime by
replaying candles from the database/seed and re-running the vendored engine.

## Verifying parity

The pin check needs the research dataset, so it is run from the repo, not from
the deployed folder. Expected: 525 trades / +538.40R / DD 28.38R with 1m data.
Do not edit `_vendored/` in place; re-vendor and re-run the parity check.

## Operational caveats

- Restart recovery (`_recover_from_crash`) rebuilds swing history only from the
  last completed swing, not the full rolling window. After long downtime, start
  with explicit seed timestamps so the whole chain is rebuilt.
- `docs/seed_marks.json` is vendored but not auto-loaded yet; it is a tail seed
  reserved for a future boot path.
- Live basis (no 1m) is +1 trade / -1.27R versus the pins. Accepted.
- Paper mode honours the book's `max_positions=0` (multiple concurrent trades).
  Live order execution now uses one exchange net position plus one attached
  partial SL per leg, capped at `LIVE_MAX_LEGS=10`, with an aggregate notional
  cap (`MAX_AGGREGATE_NOTIONAL`).   Demo-tested with 3 and 10 legs, one triggered
  SL, reconcile of only that leg, and exit of the remaining legs; DB restore
  with an open leg also passed. Full hard-kill restart recovery is now
  demo-tested both ways: leg alive at boot (restore + boot SL sync + clean
  exit) and SL fired while the process was down (boot reconcile closes the
  leg from the actual SL executions and re-arms cooldown/streak). Real
  partial fill is still pending; do not treat live as production-ready.
- Min-qty rejects (`qty < 0.001 BTC`) are kept as internal gray shadow legs when
  `GRAY_MIN_QTY_ENABLED=true` (default). They consume no exchange order or
  margin, but occupy a live leg slot and update cooldown/streak state on a
  shadow SL/trail/cap exit. They are excluded from exchange reconcile, fees,
  funding, and the daily live-risk limit. Set the env var to `false` to restore
  the old skip behaviour.
