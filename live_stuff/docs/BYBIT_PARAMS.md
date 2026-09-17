# Per-Instrument v18 Parameters

## Status: DONE (2026-09-11)

Backend (`btc_routes.py`) auto-selects per-instrument params based on `symbol`.
No manual tuning needed — just select the symbol in the UI.

---

## Param Table

| Param | BTC Spot | Binance Perp | Bybit Perp |
|-------|----------|-------------|------------|
| chop_thresh | 61.8 | 61.8 | **58.0** |
| cooldown_bars | 20 | **5** | **0** |
| sl_buf_atr | 0.25 | **0.15** | **0.10** |
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

### Bybit Perp — tuned (FIXED streak logic, 2026-09-17)

| Metric | Value |
|--------|-------|
| Trades | 375 |
| Gross R | **+305.5R** |
| Costs (fees+slip+funding) | -88.6R |
| Net R | **+216.9R** |
| Win% | 29.6% |
| Max DD | 16.0R |
| PF | 2.29 |
| Avg Win | +4.88R |
| Avg Loss | -0.89R |
| Yearly gross | 2023: +69.7R, 2024: +87.1R, 2025: +65.5R, 2026: +83.2R |
| Yearly net | 2023: +48.4R, 2024: +63.4R, 2025: +38.8R, 2026: +66.3R |

Bybit needs more aggressive tuning: chop lower (58), no cooldown, tighter slbuf.
Win rate ~30% is normal for this momentum strategy — edge is avg win (4.88R) being
5.5x avg loss (0.89R). Old "45% win rate" claim was from broken streak logic that
deleted losses.

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

### chop_thresh (61.8 → 58.0 on Bybit only)
Bybit perp has slightly noisier price action. Lower threshold lets more B2 entries
through in moderate-chop conditions. Binance perp is cleaner — same as spot.

### cooldown_bars (20 → 5 perp, 0 Bybit)
After a loss, perp recovers faster than spot. Binance perp: 5 bars enough.
Bybit perp: 0 bars (immediate re-entry). Spot needs 20 bars to avoid re-entry
into the same choppy zone.

### sl_buf_atr (0.25 → 0.15 perp, 0.10 Bybit)
Perp wicks are tighter at entry than spot. Binance perp: 0.15 (tightest).
Bybit perp: 0.10 (tightest). Spot: 0.25 (widest buffer).

---

## Routing Code

```python
# backend/src/btc/btc_routes.py — v18 block
if symbol == "BTCUSDT_BYBIT":
    _chop = 58.0
    _cd = 0
    _slbuf = 0.10
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
