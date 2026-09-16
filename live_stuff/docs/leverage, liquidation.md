# Leverage, Liquidation & Funding Rate

**Status:** 1x leverage (no leverage) — live system  
**Decision Date:** 2026-09-12  
**Reason:** Capital too small for leverage to matter. Funding is the real cost, not leverage.

---

## 1. Current Setup (1x Leverage)

| Parameter | Value |
|-----------|-------|
| Risk per trade | Rs.250 (1R) |
| BTC price | ~$77,000 |
| SL distance | ~0.6% of BTC price |
| Position size | ~0.004 BTC |
| Notional value | ~$302 |
| Margin required (1x) | ~$302 |
| Leverage | 1x (none) |

**Why 1x:**
- At 1x, you need the full notional as margin ($302 = ~Rs.28,000)
- If your demo capital is Rs.20,000, you literally can't open a trade at 1x
- But we're starting with 1x to keep it simple and safe
- We'll revisit leverage when capital grows

---

## 2. What Leverage Actually Does

Leverage does NOT change:
- Your risk (Rs.250 per trade)
- Your position size (0.004 BTC)
- Your fees (same notional = same fees)
- Your funding cost (charged on notional, not margin)

Leverage ONLY changes:
- How much margin you deposit (capital efficiency)
- Your liquidation distance

| Leverage | Margin Needed | Free Capital | Liq Distance from Entry |
|----------|--------------|-------------|------------------------|
| 1x | $302 | $0 | ~100% |
| 2x | $151 | $151 | ~50% |
| 3x | $101 | $201 | ~33% |
| 5x | $60 | $242 | ~20% |
| 10x | $30 | $272 | ~10% |

---

## 3. Liquidation Formula (Bybit V5, Isolated Margin)

### Long Position
```
Liquidation Price = Entry × (1 - 1/Leverage + MMR)
Liquidation Distance = (1/Leverage - MMR) × 100%
```

### Short Position
```
Liquidation Price = Entry × (1 + 1/Leverage - MMR)
Liquidation Distance = (1/Leverage - MMR) × 100%
```

**MMR (Maintenance Margin Rate)** for small positions (<= $300k notional): **0.33%**  
This is the minimum margin Bybit holds before liquidating you.

### Max Safe Leverage Formula
```
Max Safe Leverage = 1 / (SL_Distance% + MMR)
```

### Our Numbers
| SL Distance | MMR | Max Safe Leverage | Safe? |
|-------------|-----|-------------------|-------|
| 0.3% (tightest) | 0.33% | 166x | Yes |
| 0.6% (average) | 0.33% | 107x | Yes |
| 1.2% (widest) | 0.33% | 61x | Yes |

**Any leverage up to 50x is liquidation-safe for our SL distances.**

---

## 4. Bybit MMR Tiers (BTCUSDT, Live Data)

| Tier | Position Value (USDT) | MMR | Max Leverage |
|------|----------------------|-----|-------------|
| 1 | 0 - 300,000 | 0.33% | 150x |
| 2 | 300k - 2M | 0.50% | 100x |
| 3 | 2M - 2.6M | 0.56% | 90x |
| 4 | 2.6M - 3.2M | 0.63% | 80x |
| 5 | 3.2M - 3.8M | 0.67% | 75x |
| 10 | 8.5M - 10M | 1.30% | 45x |
| 15 | 38M - 50M | 2.90% | 20x |
| 20 | 70M - 75M | 4.00% | 15x |
| 25 | 95M - 100M | 6.50% | 10x |
| 30 | 120M - 150M | 12.0% | 5x |
| 35 | 800M - 1.2B | 60.0% | 1x |

For our position ($302 notional), we're in **Tier 1** — MMR = 0.33%, max leverage = 150x.

---

## 5. Funding Rate Impact (Backtested with Real Data)

### What is Funding Rate?
Every **8 hours** (00:00, 08:00, 16:00 UTC), a small payment is exchanged:
- Positive rate → Longs pay Shorts
- Negative rate → Shorts pay Longs

Charged on **notional value** (position size × price), not on margin.

### Historical Rates (BTCUSDT Bybit)
| Period | Typical Rate per 8h | Notes |
|--------|-------------------|-------|
| 2023 | +0.01% to +0.015% | Bull market, longs paid a lot |
| 2024 | +0.008% to +0.012% | Still mostly positive |
| 2025-2026 | +0.004% to +0.008% | Milder |
| Current | -0.003% to +0.007% | Fluctuates |

**Average across 2023-2026: +0.0045% per 8h**

### Backtest Results (335 Trades, Bybit Perp, Real Historical Funding)

| Metric | Value |
|--------|-------|
| Gross R | +385.7R |
| Fees + slippage | -59.3R |
| Net R after fees | +326.4R |
| **Funding cost** | **-32.0R** |
| **True Net R** | **+294.4R** |

Funding eats **8.3% of gross profits** (32R out of 385.7R).

### Funding Cost per Trade
| Metric | Value |
|--------|-------|
| Avg funding/trade | 0.096R (~Rs.24) |
| Avg trade duration | 32.7 hours (~4 settlements) |
| Avg settlements/trade | 4-5 |

### Key Insight
**Leverage does NOT increase funding cost.** Our position is sized by risk (Rs.250), so notional is the same ($302) regardless of 1x or 100x leverage. Funding is charged on notional.

---

## 6. When to Implement Leverage (Future)

### Prerequisites
1. Demo capital > Rs.50,000 (need margin buffer)
2. 50+ live trades completed successfully
3. Strategy edge confirmed in live conditions
4. Understanding of funding rate management

### Recommended Leverage Tiers

| Capital | Risk/Trade | Recommended Leverage | Why |
|---------|-----------|---------------------|-----|
| < Rs.20,000 | Rs.250 | 1x (none) | Can't afford margin even at 1x |
| Rs.20,000 - Rs.50,000 | Rs.250 | 1x-3x | Start small |
| Rs.50,000 - Rs.1,00,000 | Rs.500 | 3x-5x | Enough margin buffer |
| Rs.1,00,000+ | Rs.1,000 | 5x-10x | Capital efficient |

### Safety Rules for Leverage
1. **Always use Isolated Margin** — risk only the margin for that trade, not your whole account
2. **Max leverage: 3x** to start — even though math allows 50x, be conservative
3. **Check available margin before entry** — if margin < required, skip the trade
4. **Monitor liquidation price** — ensure it's always >2x the SL distance away
5. **Set leverage on Bybit API** — call `session.set_leverage()` on startup

### Implementation Checklist (When Ready)
- [ ] Add `MAX_LEVERAGE` to `config.py` (start with 3)
- [ ] Add `set_leverage()` method to `bybit_order.py`
- [ ] Call `set_leverage()` on startup in `main.py`
- [ ] In `_calculate_qty()`, check available margin before entry
- [ ] Log leverage + margin usage per trade
- [ ] Test on demo for 2 weeks before live

---

## 7. Liquidation Price Calculator

### For Long Position
```
Liq Price = Entry × (1 - 1/Leverage + MMR)
```

### For Short Position
```
Liq Price = Entry × (1 + 1/Leverage - MMR)
```

### Example (3x Leverage, Long at $77,000)
```
Liq Price = 77000 × (1 - 1/3 + 0.0033)
         = 77000 × (1 - 0.3333 + 0.0033)
         = 77000 × 0.67
         = $51,590

Distance from entry = 33.1%
Our SL distance = 0.6%
Safety margin = 33.1% / 0.6% = 55x safety factor
```

---

## 8. Golden Rules

1. **Risk is defined by position size + SL, NOT by leverage**
2. **Liquidation is dangerous only if it comes BEFORE your SL**
3. **Funding rate is the silent killer on multi-day holds**
4. **With small capital, survival > maximizing leverage**
5. **Never risk more than 1-2% of total capital per trade**
6. **Leverage doesn't increase fees or funding — it only changes capital efficiency**

---

## 9. Summary

| Question | Answer |
|----------|--------|
| Should we use leverage now? | No — 1x for now |
| Is leverage dangerous? | No — up to 50x is safe for our SL distances |
| Does leverage increase costs? | No — same notional, same fees, same funding |
| When to add leverage? | When capital > Rs.50,000 and 50+ live trades |
| What leverage to start with? | 3x (conservative) |
| How to implement safely? | Isolated margin, check margin before entry, monitor liq price |
