# AT Trading

A BTC trading strategy research platform: backtesting engine, live bot, and a Next.js
charting frontend. The project spent ~3 months (2026-08 to 2026-10) searching for a
deployable book across 54+ parameter variants. The verdict is settled — see below.

> **Start here for the verdict**: [`START_HERE.md`](./START_HERE.md)
> summarizes the conclusion in four lines. Read it first if you haven't.

---

## The Bottom Line

**No book is cleared for deployment.**

Thirteen candidate books were explored on real Bybit perpetual data
(1-minute candles, 2021-2025). The best-looking variant (`107` / CAUSAL)
came closest — failing exactly one gate criterion out of eighteen. PBO
(probability of backtest overfitting) and Deflated Sharpe Ratio (DSR) were
then run to confirm statistically: **all thirteen books fail in both the
in-sample and out-of-sample eras.**

The backtest is the only evidence available because the forward-testing
window is thin (~1 month, a handful of trades). It has not been tuned against
that window — see the forward-testing contract in
`backtest/docs/learn/01_rules/FORWARD_TESTING_CONTRACT.md`.

---

## Architecture

```
.
├── backend/                     # FastAPI backend (Python + venv)
│   ├── server.py                # Uvicorn entrypoint, mounts BTC + NSE routers
│   ├── dev-py.ps1               # Auto-restart wrapper for server.py
│   ├── requirements.txt
│   ├── start_server.bat
│   └── src/
│       ├── btc/                 # BTC-only subsystem (no NSE/session deps)
│       │   ├── btc_engine.py    # Position engine: entries, SL, trail, exit
│       │   ├── btc_swing.py     # HTF swing chain (B1/B2/FLIP marks)
│       │   ├── btc_fetch.py     # Bybit CSV download + forward fill
│       │   ├── btc_config.py    # Symbols, timeframes, paths
│       │   ├── btc_routes.py    # API routes: swings, backtest, forward
│       │   ├── btc_results_routes.py  # /results endpoint
│       │   ├── btc_display_walk.py    # Trade walk for chart overlay
│       │   ├── forward_testing_routes.py
│       │   └── engines/         # 19 versioned engines (v1–v19)
│       │       ├── v1_5m.py, v1_15m.py   # legacy single-TF engines
│       │       ├── v7_timecap.py         # exit-on-time-cap
│       │       ├── v11_conditional_htf.py
│       │       ├── v17_atr_filter.py
│       │       ├── v18_streak_halt.py
│       │       ├── v19_champion.py       # pre-unified champion
│       │       └── htf_ltf/unified.py    # SHIPPING ENGINE — all 13 books run here
│       └── walker.py            # Shared FlowCandle type (NSE + BTC)
│
├── frontend/                  # Next.js charting UI (bun)
│   ├── src/
│   │   ├── app/               # Pages: home, /btc, /chart, /forward-testing, /results, /download
│   │   ├── components/         # Chart primitives (SwingSR, HTFWindow, Position, etc.)
│   │   └── lib/
│   │       ├── books.ts       # The ONE dropdown — every book config in one list
│   │       ├── btcApi.ts      # BTC API client
│   │       ├── btcMaster.ts   # Master strategy orchestration
│   │       ├── btcCache.ts    # LRU cache for backtest results
│   │       └── resultsApi.ts  # /results artifact loader
│   └── package.json
│
├── live_stuff/                # Live trading bot
│   ├── live_loop.py           # 2149 LOC — position lifecycle + reporting (needs modularising)
│   └── backbencher.db         # Live paper-book state (gitignored)
│
├── backtest/                  # Research harnesses + documentation
│   ├── experiments/           # exp_*.py — standalone harnesses (gate eval, PBO/DSR, sweeps)
│   ├── checks/                # Verification harnesses (parity, invariant checks)
│   ├── sweeps/                # Parameter sweep harnesses
│   ├── tests/                 # Pin verification + registry
│   │   ├── test_experiments_craze.py   # Source-patch harness for book variants
│   │   ├── exp_repin_stale.py          # Batch re-pin all books
│   │   ├── exp_results_export.py       # Regenerate _results.json (8-12 min)
│   │   ├── _results.json               # UI artifact (regenerate after any engine change)
│   │   └── results.db                  # SQLite results database
│   └── docs/learn/            # The full research record (178+ markdown docs)
│       ├── 00_reference/      # Source material
│       ├── 01_rules/          # Pre-decided selection rules (written before results)
│       ├── 02_verdict/        # The answer: PBO/DSR gate, 13-book gate evaluation
│       ├── 03_methodology_corrections/  # Bugs found + retractions
│       └── 04_experiments/    # Raw evidence (superseded but kept for record)
│
├── data/                    # Gitignored — market data lives OUTSIDE the repo
│   └── (Bybit CSVs are at ../btc_data/{is,oos} — see btc_config.py)
│
├── dev.js                   # Dev orchestrator: starts frontend (3002) + backend (8003)
├── backend.js               # Backend-only helpers: bun run sb (start) / kb (kill)
├── start.bat                # One-click dev start
└── package.json
```

> **Key architectural note**: The project has **19 versioned engines** (v1–v19),
but only `htf_ltf/unified.py` is the **shipping engine**. All 13 champion books
run through it. The older v1–v19 files are archived for reference. The dropdown
in `frontend/src/lib/books.ts` maps each book name to a complete config — there
is no second control that can get out of sync.

---

## The 3 Engine Bugs (Fixed)

During the final measurement pass, three bugs were found that inflated performance:

1. **Cooldown look-ahead** (`unified.py`): The cooldown check used
   `i - last_loss_bar < cooldown_bars`, which read the current bar index
   against a future-aware comparison. Fixed to `last_loss_bar >= 0` with no
   future visibility. This is the single largest number mover.

2. **`filter_pre_fs` regression** (`unified.py`): A prior edit had added
   `and causal_lookahead` to the pre-FS gate condition, which incorrectly
   disabled the gate in causal mode. Reverted per theory doc §9.

3. **SL pivot range** (`btc_engine.py:_collect_signals`): The stop-loss pivot
   leg extreme was read from `seg.start_idx` only, missing candles between the
   previous swing's end and the current swing's start. Extended to
   `prev_end+1`, capturing the true extreme low/high.

**Impact**: Book 107 dropped from pinned +325.78R net to measured 788 trades /
+273.38R. All 54 registered books reran; every book lost 15–70% of gross R.
Commit: `8e033637`.

---

## Verdict

**No book is cleared for deployment.** PBO = 0.81 OOS / 0.99 IS (against a 0.15 bar)
and Deflated Sharpe fails for all 13 variants in both eras — the multiple-testing
correction was not applied when the shortlist was made. The shipping book
`fsent_champ_long` measures IS 665 / +118.4R but OOS 354 / **−20.51R** (oos_sign = false).
The best OOS performer, `fsent_champ_long_htf15_tskip6`, reaches +110.95R OOS but
at 73.0R max-DD — well above the 29R budget ceiling. See
`backtest/docs/learn/02_verdict/PBO_DSR_GATE.md` for the full statistical gate
and `backtest/docs/method/BASE_BOOK_NULL.md` for the null audit on `champion_multi_sw10`.

---

## Compensation Brainstorm (Book 107)

Five options were tested to recover the 342R IS loss from the bug fixes:

- **Option A** — cap lookback (extend cooldown window): +23.6R IS, +48.2R OOS
- **Option B** — ATR-floor stop (cap=2.0×ATR): best recovery
- **Option C** — quality filter (entry-side gate): minimal gain
- **Option D** — tiered stop (move to breakeven at 2R): mixed
- **Option E** — trailing stop extension: negative

**No option recovers the full loss.** The conclusion is that the original
numbers were inflated by the bugs, and the true performance of these books is
lower. This is why the PBO/DSR gate exists — to catch exactly this class of
problem.

---

## How to Run

### Prerequisites

- Python 3.10+ (backend, in `backend/venv`)
- Node.js 18+ / bun (frontend)
- Bybit 1-minute CSV data (NOT in the repo — see `data/` note below)

### Quick Start

```bash
# Terminal 1 — start backend + frontend
start.bat

# Or manually:
bun run dev          # starts both frontend (3002) + backend (8003)
bun run sb           # start backend only (foreground)
bun run kb           # kill backend on port 8003 (safe — verifies ownership)
```

**Frontend**: http://localhost:3002
**Backend API**: http://localhost:8003

### Data

The Bybit CSV files that every registry pin was measured against
**are not in this repository**. They were lost in an accidental `git clean -fdx`
(see commit `f345fe59` and `backtest/docs/learn/03_methodology_corrections/`).
They now live at:

```
../btc_data/{is,oos}/
```

i.e. a sibling directory to the repo root. See `backend/src/btc/btc_config.py`
for `BTC_FORWARD_DATA_DIR` and the path resolution logic. Without this data,
the backtest harnesses will fail to load candles.

### Key Commands

```bash
# Regenerate the results artifact the /results UI reads (8-12 min)
backend\venv\Scripts\python.exe backtest\tests\exp_results_export.py
backend\venv\Scripts\python.exe backtest\experiments\exp_enrich_results.py

# Run the selection gate (applies SELECTION_RULES.md)
backend\venv\Scripts\python.exe backtest\experiments\exp_gate_eval.py

# Run PBO / Deflated Sharpe Ratio
backend\venv\Scripts\python.exe backtest\experiments\exp_pbo_dsr.py

# Re-pin all books against the current engine
backend\venv\Scripts\python.exe backtest\tests\exp_repin_stale.py

# Run tests
cd backend && venv\Scripts\python.exe -m pytest tests/ -x -q
```

### Frontend Build

```bash
cd frontend
bun run build        # production build
bun run dev          # dev server on 3002
```

---

## How to Understand the Research

Start here, in this order:

1. **`START_HERE.md`** — the verdict in four lines
2. **`backtest/docs/learn/README.md`** — the research index
3. **`backtest/docs/learn/02_verdict/PBO_DSR_GATE.md`** — the statistical gate
4. **`backtest/docs/learn/01_rules/SELECTION_RULES.md`** — the 18-criterion gate
5. **`backtest/docs/learn/03_methodology_corrections/`** — bugs found and retracted

The docs are organised into five folders by epistemic status:

| Folder | Purpose |
|--------|---------|
| `00_reference/` | Source material the method came from |
| `01_rules/` | Decisions written **before** the results they govern (no peeking) |
| `02_verdict/` | The answer — PBO/DSR gate, 13-book gate evaluation |
| `03_methodology_corrections/` | What went wrong, and what fixed it |
| `04_experiments/` | Raw evidence (superseded, kept for record) |

---

## Known Problems

1. **`live_loop.py` is 2149 lines.** It works and is stable, which is exactly why
   it's dangerous to refactor casually. Needs splitting into signal, position
   lifecycle, risk, and reporting.
2. **Forward window is thin** — ~1 month, handful of trades. The standard
   operational gate is 20–50 round trips or one quarter. Not yet reached.
3. **`_results.json` may be stale** — regenerate with
   `exp_results_export.py` after any engine change. The UI serves this file
   from `backtest/tests/_results.json` at `/results`.
4. **Data files are not in the repo.** See the data section above.
5. **Multiple testing is controlled for** — PBO 0.57 to 1.00 against 0.15 bar,
   DSR fails for all books. This is the gate, not a bug to fix.

---

## Project Conventions

- **Costs**: 5.5 bps Bybit taker per side, 2×, 5 bps slippage, 1 bp funding,
  1 bp cost. Measured against live demo fills.
- **Time**: `ts` fields are true UTC epochs; `date` strings are IST
  wall-clock. The loaders subtract the IST offset at load time.
- **Determinism**: 338 metrics across 13 books and 2 eras, re-run from scratch:
  zero differences. If you re-run and get different numbers, something changed.
- **Port allocation**: Frontend=3002, Backend=8003. Do NOT use 3000/3001/8001/8002/
  8765 — those belong to other projects in the workspace.

---

## License

This is a research codebase. There is no deployment recommendation. See the
statistical gates in `backtest/docs/learn/02_verdict/` before considering
any live application.
