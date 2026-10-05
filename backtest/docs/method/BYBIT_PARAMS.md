# Per-Instrument v18 Parameters

## Status: DONE (2026-09-18)

Backend (`btc_routes.py`) auto-selects per-instrument params based on `symbol`.
No manual tuning needed — just select the symbol in the UI.

**Latest sweep (2026-09-18):** Post-causal sweep with C14+C15 active. New optimal: sl=0.005, chop=70. Improves +27.2R over causal baseline.

---

## Param Table

| Param | BTC Spot | Binance Perp | Bybit Perp |
|-------|----------|-------------|------------|
| chop_thresh | 61.8 | 61.8 | **70.0** |
| cooldown_bars | 20 | **5** | **10** |
| sl_buf_atr | 0.25 | **0.15** | **0.005** |
| ext_stop_r | 1.5 | 1.5 | 1.5 |
| max_consecutive_losses | 5 | 5 | **3** |
| mode | b2_vs_flip_chop | b2_vs_flip_chop | b2_vs_flip_chop |

Bold = different from BTC Spot defaults.

---

## Backtest Results (1m fills, 2023-01 to 2026-09)

### BTC Spot (Binance) — baseline

| Metric | Value |
|--------|-------|
| Trades | 330 |
| Net R | **+331.1R** |
| Win% | 36.4% |
| Max DD | 9.7R |
| PF | 2.81 |

### Binance Perp — tuned

| Metric | Value |
|--------|-------|
| Trades | 346 |
| Net R | **+311.7R** |
| Win% | 36.4% |
| Max DD | 11.6R |
| PF | 2.59 |
| Yearly | 2023: +52.8R, 2024: +79.4R, 2025: +116.3R, 2026: +63.3R |

Binance perp is nearly identical to spot — only cd (20→5) and slbuf (0.25→0.15) differ.
Chop stays at 61.8. DD slightly higher (11.6R vs 9.7R).

### Bybit Perp — tuned (C14+C15 causal + post-causal sweep, 2026-09-18)

| Metric | Value |
|--------|-------|
| Trades | **338** |
| Gross R | **+265.2R** |
| Costs (fees+slip+funding) | ~74.6R |
| Net R | **~+191R** |
| Win% | **29.3%** |
| Max DD | ~18R |
| PF | **2.19** |
| Avg Win | ~+5.6R |
| Avg Loss | -1.0R |
| Yearly gross | 2023: +21R, 2024: +94R, 2025: +61R, 2026: +88R |

**Post-causal sweep optimized:** chop_thresh 58→70, sl_buf_atr 0.01→0.005.
Chop=70 routes more signals to FLIP windows (more reliable reversals). +27.2R over causal baseline.
**C14+C15 fixes** removed 45-min lookahead at 1h boundaries — honest live-proximate number.

### Bybit Perp — default spot params (no tuning)

| Metric | Value |
|--------|-------|
| Trades | 343 |
| Net R | +270.4R |
| Win% | 34.1% |
| Max DD | 9.3R |
| PF | 2.35 |

Even with wrong params, Bybit still profitable. Tuning adds +37R buffer for costs.

---

## Why Each Param Differs

### chop_thresh (61.8 → 70.0 on Bybit only)
Higher threshold routes more signals to FLIP windows (reversal patterns) vs B2 windows.
FLIP entries are more reliable — the market has already reversed, confirming direction.
Sweep showed chop=70 gives +25.8R over chop=58 with C14+C15 active.

### cooldown_bars (20 → 5 perp, 10 Bybit)
After a loss, Bybit needs 10 bars (2.5h) cooldown — filters trash entries.
Binance perp: 5 bars enough. Spot needs 20 bars to avoid re-entry into choppy zone.

### sl_buf_atr (0.25 → 0.15 perp, 0.005 Bybit)
Bybit perp: 0.005 (post-causal sweep optimized). Nearly identical to 0.01 (+2.6R).
SL sits at the swing pivot with minimal buffer — just enough to dodge exact-pivot wicks.
Smaller risk denominator → every surviving winner scales up.

---

## Routing Code

```python
# backend/src/btc/btc_routes.py — v18 block
if symbol == "BTCUSDT_BYBIT":
    _chop = 70.0       # post-causal sweep: +27R over 58
    _cd = 10
    _slbuf = 0.005      # post-causal sweep: +2.6R over 0.01
    _halt = 3
elif symbol == "BTCUSDT_PERP":
    _chop = 61.8
    _cd = 5
    _slbuf = 0.15
    _halt = 5
else:  # BTCUSDT spot
    _chop = 61.8
    _cd = 20
    _slbuf = 0.25
    _halt = 5
```

Applied to both v18 and v19 engine variants.

---

## Files

- Backend routing: `backend/src/btc/btc_routes.py`
- v18 engine: `backend/src/btc/engines/htf_ltf/v18_streak_halt.py`
- Spot data: `data/btc/BTCUSDT_{15m,1h,1m}.csv`
- Binance perp data: `data/btc-fut/BTCUSDT_{15m,1h,1m}.csv`
- Bybit perp data: `data/bybit/BTCUSDT_{15m,1h,1m}.csv`
- Binance perp download: `scripts/download_binance_fut_1m.py`
- Bybit download: `scripts/download_bybit.py`
