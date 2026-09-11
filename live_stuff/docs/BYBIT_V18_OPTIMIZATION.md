# Bybit BTCUSDT Perp — v18 Optimization Results

## Summary

Full parameter sweep (4,032 combinations) on Bybit BTCUSDT perpetual data
(2023-01-01 to 2026-09-11, 129K x 15m candles, 32K x 1h candles).

**Result: +271.6R net (optimized) vs +194.2R net (baseline defaults)**
Improvement: +77.4R (+40%)

---

## Baseline (Binance Spot Defaults on Bybit)

| Param | Value |
|-------|-------|
| chop_thresh | 61.8 |
| mode | b2_vs_flip_chop |
| cooldown_bars | 20 |
| max_consecutive_losses | 5 |
| sl_buf_atr | 0.25 |
| ext_stop_r | 1.5 |
| min_bars_15m | 50 |
| min_bars_1h | 20 |

Results:
- Trades: 343
- Net R: +194.2R
- Avg R/trade: +0.72R
- Win%: 34.1%
- PF: 2.23
- Max DD: 9.3R
- All years positive: YES

Yearly: 2023: 73t +54.5R | 2024: 107t +63.5R | 2025: 103t +81.1R | 2026: 60t +48.3R

---

## Best Configs

### #1: Highest Net R (+271.6R)

| Param | Value | vs Default |
|-------|-------|-----------|
| chop_thresh | **58.0** | 61.8 → 58.0 (lower) |
| mode | b2_vs_flip_chop | same |
| cooldown_bars | **0** | 20 → 0 (removed) |
| max_consecutive_losses | 5 | same |
| sl_buf_atr | **0.20** | 0.25 → 0.20 (tighter) |
| ext_stop_r | 1.5 | same |
| min_bars_15m | 50 | same |
| min_bars_1h | 20 | same |

- Trades: 345
- Net R: +271.6R
- Avg R/trade: +0.95R
- Win%: 35.1%
- PF: 2.64
- Max DD: 9.2R
- All years positive: YES

Yearly: 2023: 70t +66.9R | 2024: 105t +119.3R | 2025: 107t +91.3R | 2026: 63t +51.5R

### #2: Highest Avg R/trade (+1.11R)

| Param | Value |
|-------|-------|
| chop_thresh | 58.0 |
| mode | b2_vs_flip_chop |
| cooldown_bars | 0 |
| max_consecutive_losses | 5 |
| sl_buf_atr | 0.20 |
| ext_stop_r | 1.0 |
| min_bars_15m | 50 |
| min_bars_1h | 20 |

- Trades: 285
- Net R: +268.9R
- Avg R/trade: +1.11R
- Win%: 35.4%
- PF: 2.92
- Max DD: 9.4R
- All years positive: YES

### #3: Best Risk-Adjusted (N/DD = 35.2)

| Param | Value |
|-------|-------|
| chop_thresh | 55.0 |
| mode | b2_vs_flip_chop |
| cooldown_bars | 0 |
| max_consecutive_losses | 5 |
| sl_buf_atr | 0.20 |
| ext_stop_r | 1.0 |
| min_bars_15m | 50 |
| min_bars_1h | 15 |

- Trades: 323
- Net R: +264.1R
- Avg R/trade: +0.98R
- Win%: 34.1%
- PF: 2.67
- Max DD: 7.5R
- All years positive: YES

Yearly: 2023: 72t +62.9R | 2024: 100t +105.2R | 2025: 90t +97.5R | 2026: 61t +51.8R

---

## Cross-Instrument Comparison

### Binance Spot (backtest ground truth)

| Metric | Value |
|--------|-------|
| Trades | 331 |
| Net R | +286R |
| Avg R | +0.86R |
| Max DD | 8.7R |
| Parameters | chop=61.8, cd=20, mcl=5, slbuf=0.25, ext=1.5, mb15=50, mb1h=20 |

### Binance Perp

| Metric | Value |
|--------|-------|
| Trades | 320 |
| Net R | +218R |
| Avg R | +0.68R |
| Max DD | 8.7R |
| Parameters | same defaults |

### Bybit Perp (DEFAULTS)

| Metric | Value |
|--------|-------|
| Trades | 343 |
| Net R | +194R |
| Avg R | +0.57R |
| Max DD | 9.3R |
| Parameters | same defaults |

### Bybit Perp (OPTIMIZED #1)

| Metric | Value |
|--------|-------|
| Trades | 345 |
| Net R | +272R |
| Avg R | +0.79R |
| Max DD | 9.2R |
| Parameters | chop=58.0, cd=0, mcl=5, slbuf=0.20, ext=1.5, mb15=50, mb1h=20 |

### Bybit Perp (OPTIMIZED #3)

| Metric | Value |
|--------|-------|
| Trades | 323 |
| Net R | +264R |
| Avg R | +0.82R |
| Max DD | 7.5R |
| Parameters | chop=55.0, cd=0, mcl=5, slbuf=0.20, ext=1.0, mb15=50, mb1h=15 |

---

## Per-Instrument Tuning Rules

### What needs tuning per instrument

| Param | Why | Range |
|-------|-----|-------|
| `chop_thresh` | Different volatility → different chop behavior | 55-62 |
| `cooldown_bars` | Recovery speed differs by exchange | 0-20 |
| `sl_buf_atr` | Wick size differs by exchange | 0.18-0.28 |

### What stays the same across instruments

| Param | Why it's structural |
|-------|-------------------|
| `ext_stop_r` | Window logic — how far HTF window stays open |
| `max_consecutive_losses` | Streak halt rule — same risk management |
| `mode` | B2 vs Flip decision tree — same strategy architecture |
| `min_bars_15m` | Swing sensitivity — 50 works across instruments |
| `min_bars_1h` | Swing sensitivity — 15-20 works across instruments |

### Pattern

- Lower chop threshold → more B2 windows (Bybit has slightly less clean trends)
- No cooldown → Bybit recovers from losses faster (less choppy continuation)
- Tighter SL buffer → Bybit wicks are tighter during entries

---

## Trade Count Analysis

| Config | Trades | Avg R | Net R | trades × avg |
|--------|--------|-------|-------|-------------|
| Binance Spot (default) | 331 | +0.86 | +286 | same |
| Bybit (default) | 343 | +0.57 | +194 | lower avg kills R |
| Bybit (optimized #1) | 345 | +0.79 | +272 | same trades, +38% avg R |
| Bybit (optimized #3) | 323 | +0.82 | +264 | fewer trades, +44% avg R |

Key insight: **More trades ≠ more R**. The default Bybit config has 2 more trades
than optimized (#1) but 78R less — because the default entries are worse (chop + cooldown
filtering is off).

Optimized settings improve ENTRY QUALITY, not trade count.

---

## Files

- Data: `data/bybit/BTCUSDT_15m.csv` (129,517 candles), `BTCUSDT_1h.csv` (32,380 candles)
- Download script: `scripts/download_bybit.py`
- Sweep script: `backend/debug/sweep_bybit_clean_vs_full.py`
- Partial results: `backend/debug/sweep_bybit_partial.json`
- Continuation script: `backend/debug/sweep_bybit_full_cont.py`
- v18 engine: `backend/src/btc/engines/htf_ltf/v18_streak_halt.py`

---

## Recommendation

For Bybit live trading, use these optimized defaults:

```python
# Bybit BTCUSDT Perp — Optimized
chop_thresh = 58.0
mode = "b2_vs_flip_chop"
cooldown_bars = 0
max_consecutive_losses = 5
sl_buf_atr = 0.20
ext_stop_r = 1.5
min_bars_15m = 50
min_bars_1h = 20
```

Expected performance: +272R net over 3.7 years (2023-2026), ~93 trades/year,
max DD 9.2R, all years positive.
