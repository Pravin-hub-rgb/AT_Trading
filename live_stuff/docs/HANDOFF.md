# HANDOFF — Read This First (New Chat Entry Point)

**Date:** 2026-09-10
**Purpose:** Continue the live trading engine build in a NEW chat without re-doing research.
**If you (the AI) were told "read this file and continue": THIS is that file. Read it fully, then read the files in Section 6 in order. Do NOT skip. Do NOT trust your memory over the code.**

---

## 0. The One Rule (learned the hard way)

> **NEVER reimplement strategy logic from memory or from doc summaries. ALWAYS copy/lift/import the actual backtester code. The backtester is ground truth. Any live-vs-backtest difference is a live bug until proven otherwise.**

### Why this rule exists (the failures of the previous chat)

1. **The toy walker failure.** The previous chat wrote `live_stuff/engine/walker.py` from scratch (a simplified "close breaks seg_start" swing logic) instead of lifting the real v18 logic. Result: different swings than the backtester (user's chart showed a B1 at Sept-9 11:45 that live never fired). The 6-phase build produced a wrong engine.
2. **The fake parity test.** `verify_parity.py` compared the toy walker against **itself** and reported "MATCH — guaranteed!". Self-parity proves only determinism, not correctness. **The only valid parity check is against actual backtester output.**
3. **The 1.5R misread.** Previous chat called "1.5R ext stop" an exit level. WRONG. Verified in code: `ext_stop_r=1.5` is an **entry gate** (blocks fresh same-direction LTF entries once the 1h leg is >1.5R unrealized). The profit target is **fixed 3R** (`rr_target=3.0`). User remembered correctly. **Lesson: verify every parameter in engine code before stating it.**

---

## 1. Project Context

- **Repo:** `C:\Users\Pravin\Desktop\main\AT_Trading` (branch `swing-engine-port`)
- **Strategy:** **v18 Streak Halt 5L** = "HTF-LTF, 15m inside 1h" — codename **Backbencher**
- **Backtest engine:** `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` (function `simulate_htf_ltf_streak_halt`)
- **Live engine (being rebuilt):** `live_stuff/`
- **Old live attempt (superseded):** `backend/src/live/` — reference only; its `aggregator.py` (tick→candle core, replay-verified) and Ghost-Streak streamer patterns remain valuable
- **Instrument:** BTCUSDT, 15m execution inside 1h bias windows, 1m fine data for fills
- **Stats:** IS-2025/26: 151tr 39.7% +74.0 → +57.8R net (cap16) | FULL: 330tr +331.1R gross — every filter survived a sweep; this IS the edge

---

## 2. VERIFIED v18 Parameter Matrix (from engine code — trust this, not memory)

Verified in `v18_streak_halt.py` and `btc_routes.py` v18 branch (~lines 834-853):

| Parameter | Value | What it actually does |
|---|---|---|
| `mode` | `"b2_vs_flip_chop"` | 1h chop > 61.8 → **Decisive (B2\|FLIP)** windows; else **FLIP** windows |
| `chop_thresh` | `61.8` | chop = `100·log10(ΣTR(14)/range(14))/log10(14)` on 1h (`_chop_series_1h`) |
| `atr_low_thresh` | `0.35` | LOW-vol: 15m ATR% < 0.35 also routes to Decisive (v11 lineage) |
| `window_end` | `"exit"` | HTF window lives as long as its 1h trade (SL / 3R / 16d). `r_touch`(v19) REJECTED −50R; `bias_flip` REJECTED |
| `rr_target` | `3.0` | **Fixed 3R target** on BOTH 1h window trades (`simulate_btc_trades_v7(..., rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, cap_days=16)`) and 15m LTF trades |
| `sl_mode` | `"swing"` | SL = extreme-since-prev-leg-end (touchable) |
| `sl_buf_atr` | `0.25` | SL = that extreme **± 0.25·ATR(14)** (15m ATR) |
| `ext_stop_r` | `1.5` | **ENTRY GATE, not an exit — dynamic per-bar, re-opens on pullback** (`v18_streak_halt.py:179-183`: `ext=(close−pe)*d/hrisk; if ext>1.5: continue` — if 1h leg >1.5R extended, pause new LTF entries; pull back <1.5R → re-allowed; window itself stays open until −1R/3R/16d) |
| `cap_days` | `16` | HTF window time cap |
| `cooldown_bars` | `20` | After a LOSING LTF trade skip signals 20 bars (`last_loss_bar`) |
| `max_consecutive_losses` | `5` | Streak halt: the 5th consecutive losing trade is itself SKIPPED (`skip_trade=True`), clears on next winner (loop lines 324-336) |
| one-swing-one-trade | yes | `busy_until=exit_idx`; one LTF trade at a time |
| `ltf_trailing` | `"swing"` (MB50) | 15m trades trail via MB50 swing pivots, ratchet only |
| fills | **1m fine data** | SL/trail fills on 1m bars (`fine_ltf`), gap fill `max(sl, open)` |
| `entry_selection` | `"stream"` | chronological stream order, not "final mark" |
| prev-unconfirmed entries | **ALLOWED** | skipping costs −50R gross / −28R net (v23 A/B REJECTED, checklist line 1174) |
| costs | `0.05% + 2pt` | fee 0.05%/side + 2pt slippage (`_trade_costs`) |
| swings | **1h: `min_bars=20`, 15m: `min_bars=50`**, mode `"continuous"` | Computed via `_compute_swings(FlowCandle[], "continuous", min_bars=...)` — 1h bias chain mb20, **15m execution chain mb50** (this IS the frontend overlay "strategy chain (mb50) 1h 15m execution") |

### What v18 is NOT
- NOT a 1.5R exit (that's the entry gate) • NOT r_touch window end (v19 rejected) • NOT breakeven moves (`*_breakeven=0`) • NOT mb20 on 15m (15m is mb50; only the 1h chain is mb20)

### 2b. THE GOLDEN TEST — `backend/debug/test_cat_f.py` (the exact 330t / +331.1R recipe)

This file is the acceptance test that reproduces the headline numbers. **Its exact invocation is the recipe the live engine must copy.** Run it any time to verify the engine + data are intact:

```python
# From backend/debug/test_cat_f.py (verified 2026-09-10):
from src.btc.btc_config import load_btc_df                      # CSV loader (data/btc/BTCUSDT_{tf}.csv)
from src.btc.btc_routes import _compute_swings, _load_fine_1m

c1h, f1h = load_window("1h")      # dicts: {date, ts, open, high, low, close, volume:0, oi:0}
c15, f15 = load_window("15m")     # + parallel FlowCandle list (from src.walker) for swings

sw1h = _compute_swings(f1h, "continuous", min_bars=20)   # 1h chain: mb20
sw15 = _compute_swings(f15, "continuous", min_bars=50)   # 15m chain: mb50  <-- the "mb50" overlay

fine = _load_fine_1m(t0, t1)      # 1m fine data spanning the full window (fills)

tr = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]
    # NOTE: window_end not passed -> defaults to "exit" (the +331.1R config)
```

**Assertions (all must PASS):** F1 trades == 330 · F2 total R == +331.1 (|Δ|<0.2) · F3 win rate ≈ 36.4% (330 trades: 120W/210L) · F4 PF ≈ 2.81 · F5 maxDD 9.7R (<25) · F6 all years positive: 2023 +52.8 / 2024 +86.3 / 2025 +123.0 / 2026 +69.0 (max 4 consecutive losses — 5th halt-skipped).

Cross-check: `backend/debug/_chop_sweep_results.txt` — thresh=61.8, lb=14 → `{"trades": 330, "totalR": 331.1, "win%": 36.4, "maxDD": 9.7, "flip_trades": 305, "b2_trades": 25}`.

**Rule: if the live engine's rolling-window run of this exact call does not reproduce these numbers on the full dataset, the port is broken. Period.**

### 2c. Clarifications (from the checklist changelog, lines 1270-1308 — don't get confused like the previous chat almost did)

- **r_touch chronology:** changelog line 1289 says a "bug fix" changed HTF windows to r_touch (330→242 trades). That fix was **A/B tested and REJECTED** (line 1291: r_touch +200.6R vs exit +331.1R) and **reverted**. `_r_touch_end()` remains in the engine but is INACTIVE unless `window_end="r_touch"` (wired as selectable v19 only). Golden test = exit window. **Line 1270: 33/33 PASS with `window_end="exit"`.**
- **How the 3R actually exits (test_cat_c.py / D2 amended):** the 3R target level exists on BOTH sides, but **LTF winners exit via MB50 trail, 120/120 — zero "target" exits on 15m**. The 3R target exit fires on the HTF (1h) side (447 sl / 162 target / 30 time). So on the 15m execution book: losers exit at initial SL (never beyond, worst exactly −1.000R), winners exit via MB50 trail ratchet. **Do not "fix" this by hard-exiting 15m at 3R — that's not what the backtest does.**
- **HTF side has NO trailing** (`trailing="off"` on 1h window trades — C6 verified).
- **Streak halt numbers (test_cat_b.py):** halt=5 → +331.09R (86 skipped, 99% losers, −64.4R removed); halt=0 → +265.30R (exact v12+cd20 baseline reproduction); max loss-run in trade list = 4.
- **Cost insensitivity (test_cost_sensitivity.py):** 0× +331.09R, 1× +282.88R, 2× +234.67R, 3× +186.46R, DD 9.73R unchanged.
- **Data gaps (E5):** BTC 24/7 data is 99.96% continuous — 2 gaps total, max 11h, no trades straddle gaps. Live gap-handling must mirror backtest assumptions (fetch-and-fill, never skip).
- **First swing never trades (E4):** swing_no 0 is never traded; min traded swing_no = 8 in the 330.
- **Volatile (sweep) bar edge case:** B1-low breach can be swallowed by a green sweep-recover bar that seals its own low same bar. Decision procedure is documented in the checklist's "LIVE IMPLEMENTATION GUIDE: The Volatile (Sweep) Bar Edge Case" — the live engine MUST use the same close-time decision (v21 firing on volatile bars was REJECTED: −40R on 1h).

---

## 3. Current Build Status (honest)

### live_stuff/ verdict table

| Path | Verdict |
|---|---|
| `engine/v18_params.py` | **DONE** — verified parameter matrix, each value citing backtest source |
| `engine/walker.py`, `walker_state.py`, `bias.py`, `candle.py`, `mark.py` | **DELETED** — replaced by `PersistentSwingEngine` + `SwingEngine` from `backend/src/firstswing.py` |
| `engine/original_walker.py` | **DELETED** — was wrong target (NIFTY flowline, not v18) |
| `persistence/` (database, state_store, trade_store) | **DONE** — SQLite WAL, atomic transactions, append-only marks, HTF window CRUD, streak halt persistence |
| `data_streamer.py` | **DONE** — spot API (`api.binance.com`), `backfill_klines()` + `fetch_klines_from()`, mock-friendly |
| `live_loop.py` | **DONE** — 8 phases: foundation, HTF window tracker, signal filter, trade execution, streak halt, cleanup, seed pipeline, IST+spot fix |
| `main.py` | **DONE** — CLI with positional timestamp args (arg1=15m, arg2=1h), normal Binance seed fallback |
| `docs/CHECKLIST.md` | **DONE** — all 8 phases marked with tests |
| `docs/live_trading_doc.md` | **DONE** — D1-D7 decisions, architecture, seed-by-timestamp (IST convention, spot API) |

### Works today
- Binance REST candle fetching (15m/1h) with timestamp-based seeding
- SwingEngine replay with PersistentSwingEngine (SQLite state persistence)
- Full v18 simulation on rolling windows (HTF windows, LTF trades, streak halt)
- HTF window tracking with chop/regime, extension stop gate
- Signal filter diagnostics (REJECT/PASS/TAKEN per signal)
- Trade execution with MB50 trail, conservative gap fill, ATR-scaled tolerance
- Streak halt (5L → halt, resume on next winner)
- Seed-by-timestamp API (`POST /api/btc/seed`) + CLI args

### Phase 7: Seed Pipeline (new)
- `POST /api/btc/seed` — takes `{"1h": "timestamp", "15m": "timestamp"}`
- `python main.py "15m_time" "1h_time" --exchange bybit` — positional CLI (arg1=15m, arg2=1h)
- Timestamps are IST wall-clock (matching CSV convention)
- **15m: timestamp IS the first candle** — no lookback. Engine fetches forward from timestamp to now.
- **1h: timestamp IS the first candle for swings** — but fetches 14 bars before for chop calculation.
- Live/incomplete candles filtered out (close_time > now).
- Engine state saved to SQLite, v18 simulation primed on boot

### Phase 8: IST + Spot API Fix
- All Binance fetches use spot API (`api.binance.com`), not futures (`fapi.binance.com`)
- All candle date strings use IST wall-clock (matching CSV convention)
- WebSocket uses spot stream (`stream.binance.com`)
- Verified: Sept 9 backtest marks match seed engine marks exactly

### Not yet deployed to VPS
- WebSocket live streaming (needs VPS testing)
- Daily parity check (L1/L2/L3 compare vs backtest)
- systemd unit + cron for auto-restart

---

## 4. The Approved Rebuild Plan (user agreed to this direction)

**Core decision:** reuse the REAL v18 code; recompute over a rolling window; verify daily against the backtester.

1. **Kill the toy walker** (delete files + tests).
2. **Import the real modules** (sys.path to `backend/`): `src.btc.btc_swing.compute_btc_swings`, `src.btc.engines.htf_ltf.v18_streak_halt`. Prefer **calling `simulate_htf_ltf_streak_halt` on the rolling window** and diffing its per-bar signals, rather than hand-porting the loop.
3. **Rolling window:** ~60 days ≈ 5,760 × 15m + 1,440 × 1h (+ recent 1m fine, size TBD). Recompute full v18 at every 15m close (~ms cost — fine on 1GB VPS). Chains converge well before 60 days; the daily compare proves it.
4. **Signal diffing:** after each recompute, diff full signal/trade list vs the stored journal; only NEW signals (entry_ts > last processed) trigger actions. Journaled signals never mutate (append-only).
5. **Between closes:** ticks manage live positions — SL touch, 3R touch, 16d cap, MB50 trail updates. Fill model mirrors v18's 1m-fill logic.
6. **Daily parity check (L1/L2/L3):** run the true backtester over the same window daily; diff vs live journal at marks level, trade level, R level. Any diff = live bug. Catches drift within 24h.
7. **Keep:** persistence, data layer, bootstrap/loop skeleton, atomic transactions, append-only journaling.

### Open items
- 1m fine-data strategy for live (fetch per trade window vs rolling 1m buffer)
- WebSocket vs 60s REST polling (Ghost Streak dual-stream vs simpler; VPS-friendly)
- ~~IST wall-clock vs epoch convention (docs say IST; bit the old build — be consistent)~~ **FIXED**: all timestamps are IST wall-clock, converted to UTC epoch for Binance API
- DB retention + 1m buffer sizing
- systemd unit + cron for daily parity (checklist build order: daily_fetch → compare → feeder → systemd)

---

## 5. Ground Rules for the New Chat

1. **Read code before claiming behavior.** Cite file:line when stating a rule.
2. If a doc and the code disagree → **the code wins**, then FIX THE DOC (user explicitly asked for this).
3. Never say "exact 100% match" unless proven against backtester output.
4. One-swing-one-trade, stream order, and prev-unconfirmed entries are part of the edge — do not "clean them up".
5. Every v18 parameter lives in ONE params module mirrored from the routes' v18 branch — no magic numbers scattered.
6. The user is the strategy owner and remembers sweep results. When he says "X was best", check `fix/research_v12_to_v18.md` — he's been right (the 3R case).
7. Don't declare victory from self-tests. The only test that matters: **live journal == backtester output on the same window**.

---

## 6. Reading Order for the New Chat

1. **THIS FILE** (`live_stuff/docs/HANDOFF.md`)
2. `fix/backtest_checklist_v18.md` — the v18 bible (esp. Part 1 theory; lines 1170-1240 for live decisions)
3. `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` — the WHOLE file, top to bottom
4. **`backend/debug/test_cat_f.py` — THE GOLDEN TEST (Section 2b). The exact recipe for 330t/+331.1R. Copy its invocation verbatim.**
5. `backend/src/btc/btc_routes.py` lines ~690-910 — how frontend settings map to the v18 call (+ `_compute_swings`, `_load_fine_1m` helpers live here)
6. `fix/live_trading_doc.md` — decisions log (D1 separation, rolling window, L1/L2/L3 compare protocol)
7. `backend/src/live/` — old attempt: steal `aggregator.py`, `params.py`; read `MANIFEST.md`
8. `live_stuff/persistence/` + `live_stuff/data/` — what's kept
9. `fix/research_v12_to_v18.md` — why each filter exists (v11→v18 lineage)
10. `BTC_GhostStreak_Strategy 3/data_streamer.py` (on Desktop/main) — proven WebSocket+REST dual-stream pattern

---

## 7. Where We Left Off (the immediate next step)

**Phase 7 done.** Seed pipeline is built and tested:
- `POST /api/btc/seed` endpoint works
- `_seed_from_timestamps()` method works (tested with real Binance data)
- CLI positional args (arg1=15m, arg2=1h) work
- Backtest still passes (330t +331.1R)

**Next: Deploy to VPS and test live.**

1. Deploy `live_stuff/` + `backend/` to VPS
2. Run `python main.py "15m_time" "1h_time" --exchange bybit` with backtest timestamps
3. Verify WebSocket streamer connects and candle data flows
4. Verify marks appear correctly on 15m close
5. Run for 1 week → daily parity check vs backtest
6. If parity OK → paper trade for 1 month → GO/NO-GO for real money

**Or:** test the seed API via Postman:
```
POST http://localhost:8003/api/btc/seed
Body: {"1h": "2026-09-09 15:00:00", "15m": "2026-09-10 04:30:00"}
```
