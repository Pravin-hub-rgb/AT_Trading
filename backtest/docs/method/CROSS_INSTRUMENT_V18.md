# Cross-Instrument v18 Performance


> **UPDATE 2026-09-26 (24.82): the single-period "defaults" claims below are
> SUPERSEDED.** Frozen-champion IS/OOS run on Binance BTCUSDT perp (same
> era windows as bybit, Bybit cost model, zero retune, bybit controls
> 12/12 exact): base edge transfers WEAKLY - champion 490t/+255.4 IS
> (0.78x bybit) & 286t/+17.8 OOS (0.25x), utcsat 451t/+208.1 & 258t/+7.6
> (0.13x), age10 118t/+182.6 & 78t/+94.2 (2.18x OOS); binance IS curve
> rough (ulcer ~4-8x bybit). Sizing flags: M2 + uMZX transfer 6/6;
> ZC (bybit-volume ratio threshold) and X do NOT. "Architecture
> universal" holds for engine/structure + M2/uMZX, not for edge
> magnitude or ZC/X thresholds. Harness
> `backtest/tests/exp_cross_instrument_transfer.py`.
## All Instruments — Same Engine, Tuned Parameters

| Instrument | Trades | Net R | Avg R | Max DD | PF | Params |
|-----------|--------|-------|-------|--------|----|--------|
| Binance Spot | 331 | +286R | +0.86R | 8.7R | 2.5 | defaults |
| Binance Perp | 320 | +218R | +0.68R | 8.7R | 2.5 | defaults |
| Bybit Perp (default) | 343 | +194R | +0.57R | 9.3R | 2.23 | defaults |
| Bybit Perp (optimized) | 345 | +272R | +0.79R | 9.2R | 2.64 | tuned |

## What's Different

### Binance Spot → Binance Perp (-68R)

- Same OHLC data source (fapi.binance.com vs api.binance.com)
- Slightly different wicks and fills
- Perp more volatile → more SL hits during volatile moments
- Structural impact: -20% of gross R

### Binance Spot → Bybit Perp Default (-92R)

- Different exchange, different order flow
- Chop threshold 61.8 too high for Bybit → missing B2 windows
- Cooldown 20 bars too long → sitting out good setups
- SL buffer 0.25 too wide → entries too conservative

### Bybit Default → Bybit Optimized (+78R)

- Chop: 61.8 → 58.0 (more B2 windows)
- Cooldown: 20 → 0 (no waiting after loss)
- SL buffer: 0.25 → 0.20 (tighter entries)

## Key Insight

**Strategy architecture is universal.** The same engine, same logic, same rules
work across all instruments. Only the sensitivity knobs need per-instrument tuning:

- Chop threshold (where to draw the line between trending/choppy)
- Cooldown (how long to wait after a loss)
- SL buffer (how much room to give the entry)

Everything else (ext_stop_r, mcl, mode, min_bars) stays the same.

## Trade Count Doesn't Determine R

| Config | Trades | Net R |
|--------|--------|-------|
| Bybit default | 343 | +194R |
| Bybit optimized | 345 | +272R |

Same trades, +78R difference. **Entry quality matters more than quantity.**
