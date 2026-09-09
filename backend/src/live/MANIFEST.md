# live — Backbencher (v18) paper trader manifest

ONE engine. ONE strategy (v18, codename **Backbencher** — 36.4% win rate,
tops the life game). Zero dead code. This package is the ONLY
thing that gets deployed to the VPS.

## Imports from the research tree (the complete boil-list — verified 2026-09-09)

| Module | Used for |
|---|---|
| `src/walker.py` | FlowCandle, WalkerEngine (sealed pivots) |
| `src/firstswing.py` | SwingEngine (swing chain) |
| `src/btc/btc_swing.py` | compute_btc_swings / compute_btc_flow (continuous chain) |
| `src/btc/btc_engine.py` | _collect_signals, _trail_events, trade_stats |
| `src/btc/engines/v7_timecap.py` | simulate_btc_trades_v7 (HTF windows) |
| `src/btc/engines/htf_ltf/v18_streak_halt.py` | _chop_series_1h, _atr_pct_15m, v18 gate |
| `src/btc/btc_config.py` | CSV schema (replaced live by feeder) |

NOT imported by live: v1–v17, v19–v22, btc_routes FastAPI app, Nifty code,
debug scripts. Those are research-only.

## Parity contract

Live imports the shared modules — it never copies them. The contract that
makes this safe: `compare.py` diffs the live journal against the backtester
every day. If anyone changes a shared module and behavior shifts, the daily
diff fails the same day. Before any redeploy: 33-test checklist + full
backtest must still pass.

## Files

- `params.py` — frozen v18 production parameters
- `daily_fetch.py` (step 1) — UTC-midnight klines download, append to data/btc CSVs
- `compare.py` (step 2) — journal vs backtester diff → `PARITY OK` / mismatch report
- `feeder.py` (step 3) — websocket 1m → 15m/1h aggregates → on every 15m close:
  recompute chains over rolling history → re-run v18 gate for the newest bar
  → journal entry (never hand-maintained incremental chain state;
  truncation invariance is the proof this is safe)
- `journal.py` (step 3) — JSONL/SQLite state: marks, signals, orders, positions,
  cooldowns, halt counter; restart-safe
- `deploy/` (step 4) — systemd unit + cron for the daily loop

## Proven engine: stolen from `BTC_GhostStreak_Strategy 3` (live paper-traded Dec 2025)

`C:\Users\Pravin\Desktop\main\BTC_GhostStreak_Strategy 3` ran live for days
(data/2025-12-05..12 journals exist). We reuse its proven live infrastructure:

| Stolen | From | Becomes | Notes |
|---|---|---|---|
| `data_streamer.py` (684 ln) | tick `@trade` + `@kline_15m` dual stream | `feeder.py` base | async queues → sync callbacks via `to_thread`; tick-aggregated forming candle synced/overridden by official kline (official-priority prevents tick drift); REST backfill of missed klines on reconnect; fresh-start after 5 disconnects/hr; queue backlog draining; ping/pong |
| `streak_bot.py` skeleton | `start()` asyncio bridge, `_on_tick` / `_on_15min_candle` callback split, CSV-per-day journal with flush, graceful shutdown, reset-on-reconnect hooks | `journal.py` + bot shell | strategy callbacks REPLACED by v18 recompute-and-decide; keep the tick callback for SL/trail management between closes |
| `main.py` pattern | one-file entry | `main.py` | constructs bot, starts streamer |

**Adaptations required (do not skip):**
1. Add a `@kline_1h` stream — v18 needs 1h closes (HTF windows + chop regime). Keep 15m. 1m not streamed: fine-fill parity comes from the daily CSV download instead.
2. Timestamp convention: exchange sends UTC epoch ms; `data/btc` CSVs store **IST wall-clock strings with `ts` = epoch − 19800s** (btc_config convention). Feeder MUST convert identically or the daily compare will show phantom mismatches.
3. Paper phase: no API keys needed (public streams/REST). The old bot's key auth in backfill is optional.
4. Backtester exits check SL-before-target per 1m bar; live ticks exit on first touch — expect small favorable divergence; the daily/weekly compare quantifies it against the 0.05%+2pt cost model.

## VPS shape

One Python process (systemd, Restart=always), one cron job (daily compare).
1 vCPU / 1 GB RAM is plenty: chains recompute in milliseconds per candle
close; the process idles between closes. Paper phase needs no API keys —
orders are journal-only.
