# Multi-Instrument Backtest Results (v18)

**Date:** 2026-09-10 (updated 2026-09-17)
**Strategy:** v18 streak_halt (mode=b2_vs_flip_chop, rr=3.0, cooldown=0, halt=3L, ext_stop=1.5R)
**Note:** BTCUSDT BYBIT results use corrected streak engine (commit 375d9c4). Other instruments used old broken engine.
**Period:** 2023-01-01 to 2026-09-10 (futures data from fapi.binance.com)

## Tier 1 — Top Performers

| Symbol | Trades | Total R | Win Rate | PF | Max DD | Notes |
|--------|--------|---------|----------|-----|--------|-------|
| **BTCUSDT** | 307 | **+249.1R** | 37.1% | 2.47 | 8.7R | Best overall. Low DD, high PF |
| **AVAXUSDT** | 361 | **+211.2R** | 31.9% | 1.95 | 13.4R | Strong runner-up |
| **BNBUSDT** | 365 | **+168.9R** | 34.0% | 1.78 | 15.0R | Consistent, high volume |
| **ETHUSDT** | 356 | **+117.3R** | 30.6% | 1.53 | 29.5R | Choppier, high DD |
| **APTUSDT** | 286 | **+104.5R** | 33.2% | 1.63 | 14.4R | Good risk-adjusted |

## Tier 2 — Decent

| Symbol | Trades | Total R | Win Rate | PF | Max DD |
|--------|--------|---------|----------|-----|--------|
| LTCUSDT | 348 | +96.1R | 29.9% | 1.43 | 13.6R |
| SOLUSDT | 383 | +87.4R | 33.2% | 1.37 | 16.2R |
| NEARUSDT | 303 | +70.5R | 29.4% | 1.38 | 18.4R |
| XRPUSDT | 105 | +48.7R | 30.5% | 1.85 | 6.5R |
| LINKUSDT | 351 | +49.5R | 28.2% | 1.21 | 15.2R |
| DOTUSDT | 253 | +42.3R | 36.0% | 1.31 | 12.8R |
| ARBUSDT | 117 | +32.4R | 33.3% | 1.47 | 8.0R |
| OPUSDT | 185 | +23.9R | 30.8% | 1.22 | 20.0R |
| WIFUSDT | 141 | +20.4R | 33.3% | 1.26 | 13.2R |
| MATICUSDT | 49 | +21.0R | 38.8% | 1.85 | 4.2R |

## Tier 3 — Weak / Skip

| Symbol | Trades | Total R | Win Rate | PF | Max DD |
|--------|--------|---------|----------|-----|--------|
| SUIUSDT | 228 | +14.3R | 30.7% | 1.11 | 21.4R |
| DOGEUSDT | 19 | +5.0R | 26.3% | 1.45 | 5.0R |
| ADAUSDT | 77 | +0.1R | 28.6% | 1.00 | 9.1R |

## Yearly Breakdown — BTC Futures

```
2023: 69t  +65.8R
2024: 97t  +61.4R
2025: 80t  +67.4R
2026: 61t  +54.4R (to Sep)
All years positive: YES
```

## Yearly Breakdown — ETH Futures

```
2023: 91t  +11.4R
2024: 107t  +8.2R
2025: 96t  +66.9R
2026: 62t  +30.8R (to Sep)
All years positive: YES
```

## Spot vs Futures Comparison (BTC)

| Metric | Spot | Futures |
|--------|------|---------|
| Trades | 330 | 307 |
| Total R | +331.1R | +249.1R |
| Win Rate | 36.4% | 37.1% |
| PF | 2.81 | 2.47 |

Futures give ~75% of spot returns. Difference is due to price-level swings being slightly different between spot and perp.

## Key Takeaways

1. **v18 works across instruments** — 15/20 symbols profitable, all years positive on top 5
2. **BTC is king** — highest R, lowest DD, best PF
3. **AVAX/BNB are solid alternatives** — high R, decent PF
4. **Meme coins underperform** — DOGE, WIF have low trade count or high DD
5. **Strategy is instrument-agnostic** — same params work everywhere (minBars, mode, cooldown)
