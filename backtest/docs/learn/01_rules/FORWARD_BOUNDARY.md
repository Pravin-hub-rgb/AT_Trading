# Forward Testing Boundary — Sep 13 2026 Cutoff

**Document created: 2026-10-24.**

## 1. The Boundary

There is a single, hard, pre-registered boundary in the life of this system:

| side | range | purpose |
|---|---|---|
| **IS** | 2023-01-01 → 2026-09-13 10:02 IST | Where every book parameter was found. All numbers here are **search results**, not measurements. |
| **Forward** | 2026-09-13 10:03 IST → live | Data that has **never been used to select or tune anything.** The only clean data in the repository. |

The IS slice lives at `C:\Users\Pravin\Desktop\main\btc_data\is\BTCUSDT_{15m,1h,1m}.csv`.

The forward slice lives at `data/forward/bybit/BTCUSDT_{15m,1h,1m}.csv`. The forward CSVs are **append-only**. No IS row is ever revised. The boundary is a file-system property as much as a code one: forward data is never merged back into IS.

## 2. What the IS Slice Contains

The IS CSVs end at **2026-09-13 10:00:00**. The final fully-closed 15-minute candle on the IS sheet is therefore:

```
2026-09-13 10:00:00 — open 80948.5, high 80990.0, low 80900.0, close 80985.0
```

The first forward candle (same timestamp, in `data/forward/bybit/`) is the **close** of that bar. The forward evaluator at `backtest/tests/exp_forward_eval.py` concatenates IS + forward, deduplicates on `timestamp` (keeping the forward copy when there is overlap), and replays from 2023-01-01.

## 3. Book 107 — IS Ledger (Frozen)

Book 107 is `fsent_champ_long_mcloff_htf15`.

- **IS net R (is-only CSV): +539.8**
- **OOS net R: +270.2**
- **Combined net R: +809.9**
- **IS trades: 523** (Jan 2023 → Sep 13 2026 10:02)
- **IS max drawdown: 28.38 R**
- **IS avg R/trade: 0.9677**
- **IS roll10%: 66.8%**
- **IS ulcer index: 4.388**

The IS result is **frozen**. The CSV `data/bybit/BTCUSDT_15m.csv` (or its replacement at `btc_data/is/`) was last revised on Sep 13, 2026. No forward candle was ever seen during book construction.

## 4. Forward Candidates — Pre-Registered

Per `FORWARD_TESTING_CONTRACT.md` (2026-10-16), the two books carried into the forward window are:

| pre-reg | book config | IS net | forward (through Oct 19) |
|---|---|---:|---:|
| **110** | `fsent_champ_long_htf15_tskip6` | +539.8 | −3.61 (n=3) |
| **107** | `fsent_champ_long_mcloff_htf15` | +539.8 | +1.72 (n=8) |

The other three (109, 108, 106) are listed for history but overlap 85–93% with each other; they are one bet in three names.

### Decision Rules (R1–R5, fixed)

- **R1 — execution parity**: Trades entered before the cutoff must be identical to the isolated IS replay. No fill-model change allowed.
- **R2 — edge survival**: Positive cumulative R, avg R > 0.20, PF > 1.20.
- **R3 — no degradation**: Forward window must not do worse than IS for the same book.
- **R4 — drawdown containment**: Drawdown must stay inside the pre-registered kill-line.
- **R5 — sample size honesty**: Below 50 trades = provisional; 50–150 = first read; 150+ = verdict.

### Kill Lines (pre-registered)

| book | kill-line (R) |
|---|---|
| 110 (`fsent_champ_long_htf15_tskip6`) | — not registered before Oct 16 |
| 107 (`fsent_champ_long_mcloff_htf15`) | — not registered before Oct 16 |
| `fsent_sig_multi` | 46.0 |
| `fsent_champ_long` | 46.0 |

Books 107 and 110 were added to the forward eval on 2026-10-16 *after* the window already existed. Per rule 3 of `FORWARD_TESTING_CONTRACT.md`, this burns nothing — the window is only consumed when a change is proposed **because of** a forward result. They are scored for information only until the window closes.

## 4. Forward Results Log

### 2026-09-13 to 2026-10-19 (first scoring, 26 days) — superseded

| book | pre-cutoff trades | forward trades | net R | avg R | WR | PF | DD | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 107 (MCLOFF) | 520 | 8 | +1.72 | +0.205 | 37.5% | — | 3.8R | NOT PRE-REGISTERED |
| 110 (TSKIP6) | 377 | 3 | -3.61 | -1.180 | 0.0% | — | 3.6R | NOT PRE-REGISTERED |

### 2026-09-13 to 2026-10-24 (extended, 42 days)

Forward data extended to Oct 24 21:30 via `exp_append_forward_data.py` (Bybit REST).

| book | pre-cutoff trades | forward trades | net R | avg R | WR | PF | DD | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 107 (MCLOFF) | 520 | 17 | -2.6 | -0.152 | 29.4% | 1.15 | 5.6R | NOT PRE-REGISTERED |
| 110 (TSKIP6) | 377 | 13 | -5.9 | -0.455 | 30.8% | 0.71 | 6.3R | NOT PRE-REGISTERED |
| 108 (HTFESMCL4) | 737 | 20 | +7.5 | +0.377 | 35.0% | 2.40 | 8.4R | NOT PRE-REGISTERED |
| 106 (HTFFS) | 722 | 20 | +11.3 | +0.563 | 45.0% | 3.35 | 4.9R | NOT PRE-REGISTERED |

**Key observations:**
- Books 107 and 110 (the pre-registered candidates) are both **underwater** on the extended window. Neither has crossed 50 trades, so the verdict remains provisional.
- Books 108 and 106 are both in profit, but they were not pre-registered with kill-lines, so they carry no verdict — scored for information only.
- The combined dataset covers 133,697 15m candles (42 forward days added).

## 5. The Forward Evaluator

Script: `backtest/tests/exp_forward_eval.py`

### Method (read-only, no production change)

1. Concatenate IS + forward CSVs per timeframe (15m, 1h, 1m).
2. Recompute swings on the concatenated series (min_bars=50 for 15m, min_bars=10 for 1h).
3. Replay the engine on the full chain from 2023-01-01.
4. **R1**: trades entered before `CUTOFF_TS` must match the IS-only replay exactly.
5. Score only trades entered at/after `CUTOFF_TS` (2026-09-13 10:03 IST).

### Output

Results are written to `backtest/tests/_forward_eval.json` and printed to stdout.

### How to Run

```bash
cd backtest
python tests/exp_forward_eval.py
```

## 6. Extending Forward Data

The forward CSVs are downloaded in chunks from the Bybit REST API. New candles are **appended** to the existing CSVs. No existing row is ever modified.

### Download Script

```bash
# From repo root
python backtest/tests/exp_append_forward_data.py --tf 15m,1h,1m --start "2026-10-19 09:15"
```

This fetches candles from Bybit (`/v5/market/kline`, `category=linear&symbol=BTCUSDT`) starting just after the last row in each CSV and appends them. The `--start` parameter can be omitted to auto-detect from the last row.

### Manifest

`data/forward/bybit/_forward_manifest.json` tracks the forward slice metadata:

```json
{
  "forward_start_ist": "2026-09-13 10:03:00",
  "downloaded_utc": "2026-10-24T16:30:00+00:00",
  "rows": {"1m": 59731, "15m": 3983, "1h": 996}
}
```

The manifest is updated each time new forward data is downloaded.

## 7. Mark Verification Against TradingView

Oct 20, 2026 marks are extracted and cross-checked against TradingView's BTCUSDT.P chart (timezone IST). See `backtest/docs/learn/01_rules/FORWARD_MARK_VERIFICATION.md` for the daily verification log.

## 8. Forward Testing UI

The live dashboard at `/forward-testing` shows:

- Forward trade logs for each candidate
- Cumulative net R over the window
- Monthly net breakdown
- Drawdown vs kill-line
- Trade count vs 50-trade stop rule

The route is served from `backend/src/routes/forward_testing.py` and reads from `backtest/tests/_forward_eval.json`.
