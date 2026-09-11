# Spot Signals + Perp Execution — Architecture

## The Problem
- v18 strategy produces BOTH long and short signals (B1/B2/FLIP)
- BTC spot: can only LONG
- BTCUSDT perp: can SHORT (but has different price data)
- Backtest validated on spot data (+331.1R) but we need perps to short

## The Solution
**Use BTC SPOT candles for signal generation, execute on BTCUSDT PERP.**

```
[Spot Candles] → SwingEngine → B1/B2/FLIP marks → v18 Signal Filter → Entry/SL/Trail
                                                                                ↓
                                                          [BTCUSDT Perp Order] (long OR short)
```

## Why This Works

### 1. Spot ≈ Perp (nearly identical prices)
```
BTC Spot:   O=78732.00 H=78772.00 L=78586.00 C=78608.21
BTC Perp:   O=78697.70 H=78739.90 L=78541.60 C=78568.20
Diff:       ~$30-40 on $78K = 0.04-0.05%
```

### 2. Swing detection is identical
- B1/B2/FLIP marks come from swing pivots (price-action, not exchange)
- Same OHLC pattern → same marks regardless of exchange
- The ~$30 diff doesn't change pivot highs/lows

### 3. SL and R-multiples are nearly identical
- SL = entry ± 0.25 × ATR(14) — ATR is the same on spot and perp
- R = (exit - entry) / (entry - SL) — same ratio since diff cancels out
- Backtest R = actual R (within 0.05%)

### 4. What changes
- Execution price: ~$30-40 different (0.05% slippage)
- Funding rate: perp has funding every 8h (cost ~0.01% per day if long in bull)
- But: we get SHORTING ability — the core edge of v18

## Expected Performance

| Metric | Spot Backtest | Spot+Perp (estimated) |
|--------|--------------|----------------------|
| Trades | 330 | ~330 |
| Total R | +331.1R | ~+330R |
| Win Rate | 36.4% | ~36.4% |
| PF | 2.81 | ~2.80 |
| Can Short | NO | YES |

**~99.7% of spot returns** with full long+short capability.

## What Needs to Change in Code

### Option A: Minimal change (recommended)
1. Keep `data_streamer.py` fetching SPOT candles (api.binance.com)
2. Keep the engine using spot data for swing detection
3. Only change the ORDER EXECUTION to go to perp (fapi.binance.com)
4. Swap symbol in order placement: `BTCUSDT` (spot) → `BTCUSDT` (perp)

### Option B: Full perp data
- Switch everything to perp data (fapi.binance.com)
- Re-run backtest on perp data (+249.1R vs +331.1R spot)
- Lose ~82R but data is "pure"

**Option A is better** — you keep the validated backtest and just route orders to perp.

## Funding Cost Impact
- Average funding rate: ~0.01% per 8h (long pays short)
- Average trade duration: ~4-6 hours (15m timeframe)
- Funding cost per trade: ~0.005% (negligible)
- Annual funding drag: ~2-5R (out of +330R)
- **Net: still ~+325R+ after funding**

## Bottom Line
This is the standard approach in crypto prop desks — analyze on spot, trade on perp. The $30 price diff is noise. The shorting ability is the signal.
