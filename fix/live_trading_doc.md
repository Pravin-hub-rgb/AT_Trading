# Live Trading Doc — Backbencher (v18 paper trader)

Backbencher — okay, that's genuinely perfect. Better than all of mine, because the metaphor isn't just sarcastic, it's structurally exact:

Sits at the back, looks like a failure — 36.4% win rate. If win rate were the exam, this bot fails every semester.
Doesn't follow the rules — skips most "good setups" (85 trades outlive their windows, most marks ignored), takes naps mid-class (20-bar silent treatment after every loss), and walks out of school entirely after 5 failures (streak halt).
But when the exam that matters comes — the window opens, one entry, +24R. Topper in real life.
And the report card at the end: +331R gross, PF 2.81, 4/4 years positive — while the front-benchers (high win-rate strategies) grind out 100 tiny trades and bleed costs.
"Backbencher" also carries the exact lesson of this whole project: the toppers-by-metrics (v16, v17, v19–v22 — every "looks better on one chart" candidate) flunked the A/B, and the backbencher v18 just quietly keeps winning. Let me make it official:

*Created 2026-09-09. This is the journey log for moving v18 from validated
backtest to live paper trading. Backtest master doc: `backtest_checklist_v18.md`.*

**Codename — Backbencher:** the student who fails every win-rate exam
(36.4%) yet tops the life game (+331R gross, PF 2.81, 4/4 years positive).
Skips most "good setups", takes the 20-bar silent treatment after every loss,
walks out after 5 straight failures — and aces every real exam (the big
trend windows) with entries like +24R. Every fancier-named candidate
(v16, v17, v19–v22) flunked its A/B; the backbencher keeps winning.
Journal log lines use the name, e.g.:
`Backbencher | L1 ✓ | entry BLOCKED (sulk mode, 14 bars left)`.

## Status: validation COMPLETE → live build phase

- v18 = final strategy: 330 trades, +331.1R gross (~+200R net), PF 2.81, 4/4 years positive
- 33/33 mechanics tests pass; truncation invariance 44/44 (no lookahead, decisions = pure function of past data)
- Live-readiness verdict: cleared for paper trading (1 month) before any real money

## Decision log

### D1 — Backtester and live trader are SEPARATE processes
The research repo (AT_Trading) keeps the backtester, engines v1–v22, FastAPI
frontend — untouched. The live trader is a NEW package (`backend/src/live/`)
that imports only the 7 shared parity-tested modules (see
`backend/src/live/MANIFEST.md`). VPS deployment = the live package alone.
Nothing that happens in research can break live, and vice versa; the daily
parity compare is the bridge between the two worlds.

### D2 — Data: not whole years, not "just the latest swing" — rolling window
The tempting design (bootstrap with only the current swings + marks, engine
figures out the rest) is the "proper" live state design, but it has a
bootstrap-correctness risk: SL = extreme-since-prev-leg-end, and if the
current leg's origin lies before the bootstrap point, SLs come out wrong.
The boring design is provably safe and still tiny:

- **Boot:** REST-fetch a rolling window from Binance — last 30 days of 15m
  (~2,900 candles) + last 20 days of 1h (~500 candles). A few MB, 3 API
  calls, no pre-existing data needed on the VPS.
- **Every 15m/1h close:** recompute the full chains over the rolling window
  and re-run the v18 gate for the newest bar. No hand-maintained state.
- **Why safe:** every decision is determined by (a) the chains (causal) and
  (b) trade state (entry/SL/cooldown/halt) in the journal. `cap_days=16`
  bounds any HTF trade's life → a 20-day 1h window reconstructs every
  still-relevant window; cooldown 20 bars fits easily in 30 days of 15m.
- **The full-year CSVs stay on the laptop** — ground truth for the compare.

### D3 — Dead code clarified (the user's actual point)
The concern was never v18 itself: the SHARED modules (btc_engine.py,
btc_routes.py...) contain functions used only by other versions (v1–v17,
Nifty) — dead code *from v18's perspective*. Two layers:

1. **Now (paper month):** dead functions are inert — live imports the 7
   modules but CALLS only the boil-listed functions. Uncalled code has zero
   behavioral risk, and keeping it preserves the single source of truth the
   parity contract depends on.
2. **Later (optional):** a mechanically extracted "hard-boiled" single-file
   engine (only the called functions), verified by running it vs the original
   over the full 4-year backtest — 100% trade-identical before it replaces
   the imports. Only after the paper month proves parity.

### D4 — No visuals for live. Logs are the UI
The live trader produces: console log (INFO), a daily marks journal, and a
trade journal. No charts, no dashboard. Review happens by reading the logs
and the daily compare output.

### D4b — Code mirror map (live ≡ backtest, function by function)

The live engine imports the SAME functions the backtest uses — no rewrites, no copies:

| Layer | Function | File | Live import |
|---|---|---|---|
| Pivot walker (incl. volatile bar logic) | `WalkerEngine.process_bar()` | `walker.py:141` | `mark_engine.py:8` |
| Swing chain | `compute_btc_swings()` | `btc_swing.py:33` | `mark_engine.py:7` |
| Signal gating | `_collect_signals()` | `btc_engine.py:33` | (L2 when wired) |
| Trail ratchet | `_trail_events()` | `btc_engine.py:179` | (L3 when wired) |
| Outcome stats | `trade_stats()` | `btc_engine.py:537` | (L3 when wired) |

**Consequence:** the volatile sweep-bar edge case (walker.py:261-290, DOUBLE-BREAK marker-band logic) is shared — "sweep-reversal bar re-anchors instead of firing B2" is identical in both engines by construction, not by testing. When L2/L3 are wired, they will use the same `_collect_signals` + `_trail_events` the backtest uses — the daily compare is the backstop, but the shared code is the primary guarantee.

### D5 — Journal EVERY mark, not just trades (compare protocol)
To answer "are marks printed on the RIGHT candles?" the journal records three
levels, and the daily compare checks them in order:

| Level | Journal content | Compare against |
|---|---|---|
| L1 marks | every B1/B2/FLIP mark: kind, dir, bar timestamp, px, swing_no | backtester `_compute_swings` marks for the same bars |
| L2 signals | tradeable signals: kind, dir, swing_no, entry px, SL px | backtester `_collect_signals` (stream) |
| L3 trades | entries, exits (reason, px, R), cooldowns, halt events | backtester v18 `ltf_trades` |

Expected each day: L1 100% identical, L2 100% identical, L3 100% identical
(except fills — ticks touch SL before the 1m bar closes; that divergence is
measured, not treated as failure). First mismatching level = exactly where
the port is broken.

### D6 — Timestamp convention (the silent killer)
Exchange = UTC epoch ms. `data/btc` CSVs = IST wall-clock strings with
`ts = epoch − 19800s` (btc_config). The feeder/journal MUST convert
identically or the daily compare drowns in phantom mismatches.

## Architecture

```
VPS (live package)                       Laptop (research repo)
┌───────────────────────────┐            ┌──────────────────────────────┐
│ feeder (stolen streamer)  │            │ data/btc CSVs (full history) │
│  tick@trade + kline 15m+1h│            │ v18 backtester               │
│  → closed candle events   │            │  (ground truth)              │
│ engine: recompute chains  │            │                              │
│  → v18 gate → decision    │   journal  │ compare.py:                  │
│ journal: L1+L2+L3 (JSONL) │ ─────────→ │  L1/L2/L3 diff vs backtester │
│ (paper: no orders)        │ daily sync │  → PARITY OK / MISMATCH      │
└───────────────────────────┘            └──────────────────────────────┘
     cron: daily_fetch.py appends the day's klines to the dataset
```

## Build order

1. `daily_fetch.py` — Binance REST klines → append to `data/btc` CSVs (IST convention)
2. `journal.py` — L1/L2/L3 JSONL writer (+ reader for compare)
3. `compare.py` — backtester-vs-journal diff, three levels, status line output
4. `feeder.py` — stolen streamer + 1h kline stream + recompute-and-decide loop
5. `main.py` entry point; `deploy/` — systemd unit + cron
6. Run 1 month paper → weekly R comparison → GO/NO-GO gate for minimal real size

### Step 4 progress: aggregation core DONE and replay-verified (2026-09-09)

`backend/src/live/aggregator.py` = the stolen streamer's candle core,
stripped of websocket I/O. Replay test `backend/debug/test_backbencher_feeder.py`
(3 days of 1m CSV → 17,160 pseudo-ticks O/H/L/C):

- 285/285 closed 15m candles == official 15m CSV rows (date/ts/OHLC exact)
- 71/71 closed 1h candles == official 1h CSV rows (exact)
- 71/71 hours produced exactly **4× 15m closes + 1× 1h close**
- hour-boundary order: 1h close emitted BEFORE the 4th 15m close of the
  finished hour (HTF window state updates before the LTF decision) — 0 violations
- IST wall-clock conversion (utc + 19800 → CSV `date` string; ts = utc epoch)
  matches all CSV rows — D6 convention implemented and proven

Per-hour answer to "what do we get": every hour boundary tick emits
`[1h close of the finished hour, 15m close of the finished 15m]` —
the engine receives 4× 15m OHLC + 1× 1h OHLC per hour, exactly as required.

### First LIVE run (2026-09-09) + a key discovery about the compare protocol

`backend/src/live/main.py` boots: REST-seeds 2,879 × 15m + 479 × 1h rolling
candles (spot REST, BTCUSDT — note: symbol must be UPPERCASE in REST, lowercase
in stream names), connects to `wss://stream.binance.com` combined kline stream,
and on every closed 15m/1h candle prints OHLC + any B1/B2/FLIP mark that fired
on that bar (chains recomputed per close over the rolling window), journaling
L1 to `data/live/marks_YYYYMMDD.jsonl`.

**Discovery (`backend/debug/test_rolling_vs_full.py`, `_data_probe.py`):**
rolling-window chain (30d, also re-tested 60d) reproduces **all 10/10**
full-history marks of the overlap region EXACTLY (same bar/kind/dir/px) — but
the live chain had **3 extra** B1/B2 marks near the CSV's tail. Data verified
byte-identical between CSV and REST for those bars → the cause is **tail
re-attribution**: the last swing of any chain is still open, and later price
action re-segments it, moving/absorbing marks printed days earlier. This is
inherent swing-chain behavior (the "marks print pre-confirmation" fact
generalized: *the chain's tail is provisional until structure seals*).

**Protocol consequence (refines D5):** `compare.py` must NOT diff the live
journal against the full-history final chain — tail re-attribution would show
phantom mismatches. Instead, for each day D it must recompute the backtester
chain on data TRUNCATED at end of day D (which is exactly the chain state the
live engine had) and diff that against the journal. L2/L3 trade comparisons
are safe on full history (truncation invariance proved decisions don't change),
but L1 mark comparisons are truncated-day by truncated-day.

## Fill-Data button + live log (2026-09-09)

### How to watch the live log

The live engine (`backend/src/live/main.py`) writes to `backend/src/live/_run_live.txt`.
PowerShell `Get-Content -Wait` hits file-locking issues — use the watcher instead:

```powershell
python backend/debug/tail_logs.py              # last 25 lines, then follow
python backend/debug/tail_logs.py --once       # print once, no follow
python backend/debug/tail_logs.py --lines 50    # last 50, then follow
```

Output format — every 15m close prints OHLC, every 1h close prints OHLC, and any
B1/B2/FLIP mark fires inline with its bar:

```
[15m CLOSE] 2026-09-09 12:15:00 | O 79187.42  H 79198.69  L 79117.88  C 79159.03
[15m] no marks on this candle (chain: 58 swings)
[ 1h CLOSE] 2026-09-09 11:30:00 | O 78923.43  H 79290.63  L 78865.71  C 79159.03
[ 1h] no marks on this candle (chain: 15 swings)
[MARK] 15m B2   up   sw123 @ 99800.5  (bar 2026-09-09 12:15)  swing[...] confirmed@...
```

### Fill-Data button (on /btc page)

Added between the Trades toggle and the VERSION selector. Calls `POST /api/btc/fetch`
which appends new Binance candles to the CSVs (idempotent — only new timestamps).

**Backend** (`backend/src/btc/btc_fetch.py` — extracted from the proven
`debug/_btc_fetch_update.py` logic):
- `POST /api/btc/fetch` — body `{"tfs":["15m","1h"]}` or empty for all 5 TFs
- `GET /api/btc/fetch/status` — last stored timestamp per TF
- Verified: import clean, both routes registered, data path resolves correctly
  (15m last: 2026-09-05 23:00, 1h last: 2026-09-06 08:30)

**Frontend** (`frontend/src/app/btc/page.tsx`, `frontend/src/lib/btcApi.ts`):
- `fetchBtcData()` API function
- Button states: idle / Filling… (amber pulse) / Filled ✓ (green, 4s reset)
- Status message: `appended N rows across 5 TFs` or error detail

**Usage:** click once a day (or after market hours) to pull the latest candles.
The live engine's rolling window picks them up on its next boot — or, when the
feeder is extended to call `refresh_tf` inline, within the same run.

## Provenance of live infrastructure
Stolen from the user's own `BTC_GhostStreak_Strategy 3` (paper-traded live
Dec 2025): `data_streamer.py` (tick+kline dual stream, async queue bridge,
REST backfill, fresh-start guard) and `streak_bot.py` skeleton (callback
split, per-day CSV journal, shutdown/reconnect hooks). Adaptations: +1h
kline stream, IST timestamp conversion, no API keys for paper. Details in
`backend/src/live/MANIFEST.md`.

2. **Later (optional):** a mechanically extracted "hard-boiled" single-file
   engine (only the called functions), verified by running it vs the original
   over the full 4-year backtest — 100% trade-identical before it replaces
   the imports. Only after the paper month proves parity.
