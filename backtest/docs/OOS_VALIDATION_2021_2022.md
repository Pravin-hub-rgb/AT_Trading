# Out-of-Sample Validation: 2021-2022 Unseen Data

**Date:** 2026-09-22
**Status:** COMPLETE — OOS validation + causal SL applied
**Data:** Bybit BTCUSDT Perpetual, 2021-01-01 to 2022-12-31
**Separation:** Data stored in `data/unseen/bybit/` — never touches `data/bybit/`

---

## Table of Contents

1. [Setup](#setup)
2. [OOS Leaderboard](#oos-leaderboard)
3. [Detailed Results by Strategy](#detailed-results-by-strategy)
4. [Yearly Breakdown](#yearly-breakdown)
5. [FTX Collapse Analysis](#ftx-collapse-analysis)
6. [OOS/IS Ratio Analysis](#oosis-ratio-analysis)
7. [Key Findings](#key-findings)
8. [Implications](#implications)

---

## Setup

### Data Separation
- **In-sample (development):** `data/bybit/BTCUSDT_{15m,1h,1m}.csv` — 2023-01-01 to 2026-09-21
- **Out-of-sample (validation):** `data/unseen/bybit/BTCUSDT_{15m,1h,1m}.csv` — 2021-01-01 to 2022-12-31
- **Zero overlap** between the two datasets

### OOS Data Stats
| Timeframe | Candles | Range |
|---|---|---|
| 15m | 70,058 | 2021-01-01 to 2022-12-31 |
| 1h | 17,515 | 2021-01-01 to 2022-12-31 |
| 1m (fine fills) | 1,050,870 | 2021-01-01 to 2022-12-31 |

### Engine & Params
- **Engine:** v18_streak_halt (patched via test_experiments_craze.py)
- **Basis:** Fine fills (1m exit precision) — identical to in-sample
- **Cost model:** 0.055% fee/side, 0.005% entry slip, 0.010% exit slip, 0.01%/8h funding
- **Swing chain:** sw10 (min_bars_1h=10) for all strategies

---

## OOS Leaderboard

Ranked by NET R (after costs + funding) on 2021-2022 OOS data:

| # | Strategy | IS NET | OOS NET | OOS/IS | WR | DD | Ann.NET |
|---|---|---|---|---|---|---|---|
| 1 | **chopband_multi** | +350.7R | **+85.8R** | **47%** | 29.0% | 29.1R | +42.9R/yr |
| 2 | **champion_multi** | +325.8R | **+70.1R** | **41%** | 28.0% | 37.3R | +35.1R/yr |
| 3 | **multi (utcsat)** | +359.0R | **+60.2R** | **32%** | 29.6% | 22.1R | +30.1R/yr |
| 4 | fullstack_single | +282.9R | +21.0R | 14% | 25.5% | 25.4R | +10.5R/yr |
| 5 | single (king) | +310.7R | +16.9R | 10% | 25.0% | 27.9R | +8.4R/yr |
| 6 | wage12_single | +278.6R | +13.0R | 9% | 25.3% | 19.1R | +6.5R/yr |
| 7 | fliponly_multi | +242.7R | **-17.3R** | -14% | 18.4% | 46.4R | -8.7R/yr |

### Key Observations
- **Multi strategies dominate** — top 3 are all multi-position
- **Simpler is better** — fewer filters = better OOS generalization
- **fliponly is dead** — completely fails OOS
- **All strategies are profitable OOS** except fliponly (6 out of 7)

---

## Detailed Results by Strategy

### 1. chopband_multi (BEST OOS)
**Config:** mltf + persist7 + chop band [55,61)
```
  Trades:           255
  Gross R:          +120.6R
  Cost R:           -29.1R
  Funding R:        -5.7R
  NET R:            +85.8R
  Win Rate:         29.0%
  Max DD:           29.1R
  Avg R:            +0.47R
  Max Streak:       16 consecutive losses
  NET/Max DD:       3.0
  Annual NET:       +42.9R/yr
```
- **Yearly:** 2021: +0.1R | 2022: +120.6R
- **OOS/IS ratio:** 47% (retains nearly half its in-sample edge)

### 2. champion_multi
**Config:** mltf + persist7 (no utc skip)
```
  Trades:           279
  Gross R:          +105.7R
  Cost R:           -29.6R
  Funding R:        -6.0R
  NET R:            +70.1R
  Win Rate:         28.0%
  Max DD:           37.3R
  Avg R:            +0.38R
  Max Streak:       15 consecutive losses
  NET/Max DD:       1.9
  Annual NET:       +35.1R/yr
```
- **Yearly:** 2021: **-11.0R** | 2022: +116.7R
- **Note:** Lost money in 2021 (bull run), made it all back in 2022 (crash)

### 3. multi (utcsat) — KING MULTI
**Config:** mltf + persist7 + utc-sat skip
```
  Trades:           253
  Gross R:          +92.6R
  Cost R:           -27.3R
  Funding R:        -5.1R
  NET R:            +60.2R
  Win Rate:         29.6%
  Max DD:           22.1R
  Avg R:            +0.37R
  Max Streak:       9 consecutive losses
  NET/Max DD:       2.7
  Annual NET:       +30.1R/yr
```
- **Yearly:** 2021: +13.2R | 2022: +79.5R
- **Best DD control** — only 22.1R max DD (vs 37.3R for champion_multi)

### 4. fullstack_single
**Config:** swingpause + weekend + chop band + ATR ratio
```
  Trades:           149
  Gross R:          +42.6R
  Cost R:           -18.7R
  Funding R:        -2.9R
  NET R:            +21.0R
  Win Rate:         25.5%
  Max DD:           25.4R
  Avg R:            +0.29R
  Max Streak:       13 consecutive losses
  NET/Max DD:       0.8
  Annual NET:       +10.5R/yr
```
- **Yearly:** 2021: +12.6R | 2022: +30.1R
- **OOS/IS ratio:** 14% — most edge lost

### 5. single (king) — KING SINGLE
**Config:** fullstack + wage10 + cd=0
```
  Trades:           140
  Gross R:          +38.0R
  Cost R:           -18.5R
  Funding R:        -2.7R
  NET R:            +16.9R
  Win Rate:         25.0%
  Max DD:           27.9R
  Avg R:            +0.27R
  Max Streak:       13 consecutive losses
  NET/Max DD:       0.6
  Annual NET:       +8.4R/yr
```
- **Yearly:** 2021: +12.9R | 2022: +25.1R
- **OOS/IS ratio:** 10% — almost all edge gone

### 6. wage12_single
**Config:** swingpause + weekend + wage 12h
```
  Trades:           154
  Gross R:          +35.0R
  Cost R:           -19.3R
  Funding R:        -2.8R
  NET R:            +13.0R
  Win Rate:         25.3%
  Max DD:           19.1R
  Avg R:            +0.23R
  Max Streak:       15 consecutive losses
  NET/Max DD:       0.7
  Annual NET:       +6.5R/yr
```
- **Yearly:** 2021: +12.4R | 2022: +22.6R

### 7. fliponly_multi (DEAD OOS)
**Config:** mltf + persist7 + FLIP entries only
```
  Trades:           152
  Gross R:          +8.2R
  Cost R:           -22.6R
  Funding R:        -3.0R
  NET R:            -17.3R
  Win Rate:         18.4%
  Max DD:           46.4R
  Avg R:            +0.05R
  Max Streak:       15 consecutive losses
  NET/Max DD:       -0.4
  Annual NET:       -8.7R/yr
```
- **Yearly:** 2021: **-38.9R** | 2022: +47.2R
- **Worst strategy** — massive DD, negative NET

---

## Yearly Breakdown

| Strategy | 2021 | 2022 | Total OOS |
|---|---|---|---|
| chopband_multi | +0.1R | +120.6R | +85.8R |
| champion_multi | **-11.0R** | +116.7R | +70.1R |
| multi (utcsat) | +13.2R | +79.5R | +60.2R |
| fullstack_single | +12.6R | +30.1R | +21.0R |
| single (king) | +12.9R | +25.1R | +16.9R |
| wage12_single | +12.4R | +22.6R | +13.0R |
| fliponly_multi | **-38.9R** | +47.2R | **-17.3R** |

### Key Pattern
- **2021 (Bull Run):** Most strategies flat or slightly positive. Only champion_multi lost money.
- **2022 (Crash):** All strategies profitable. FTX collapse drove massive gains.
- **Conclusion:** The edge is event-driven (crisis alpha), not a consistent statistical edge.

---

## FTX Collapse Analysis

### What Happened
FTX was the 2nd largest crypto exchange. Collapsed Nov 6-11, 2022.
BTC dropped from ~$21K to ~$15.5K in days.

### Impact on OOS Results

**chopband_multi top 3 trades:**
| # | Date | Direction | R |
|---|---|---|---|
| 1 | Nov 6-11, 2022 | SHORT | +33.1R |
| 2 | Nov 7-11, 2022 | SHORT | +19.8R |
| 3 | Nov 6-11, 2022 | SHORT | +16.3R |

**Total from FTX event:** +69.2R out of +85.8R total = **80.6% of OOS profit from one event**

**Without FTX:**
- chopband_multi: +85.8R - 69.2R = **+16.6R on 2 years** (barely profitable)
- champion_multi: +70.1R - ~69R = **+1.1R on 2 years** (flat)
- multi (utcsat): +60.2R - ~69R = **-8.8R on 2 years** (slightly negative)

### Conclusion
The OOS edge is **heavily dependent on a single black swan event**. The strategies are crisis alpha — they profit from extreme volatility, not from consistent market inefficiency.

---

## OOS/IS Ratio Analysis

### What is OOS/IS Ratio?
OOS/IS = (Annual OOS NET R) / (Annual IS NET R) × 100%

Measures how much of the in-sample edge survives out-of-sample.

### Industry Benchmarks
| OOS/IS | Interpretation |
|---|---|
| 80-100% | Suspiciously good (likely curve-fitted to OOS) |
| 50-80% | Excellent (rare in practice) |
| 30-50% | Good (typical for quant strategies) |
| 10-30% | Poor (most edge is overfitting) |
| <10% | Terrible (strategy is mostly curve-fitted) |
| Negative | Strategy is noise |

### Your Strategies
| Strategy | OOS/IS | Verdict |
|---|---|---|
| chopband_multi | **47%** | Good — retains nearly half its edge |
| champion_multi | **41%** | Good — solid generalization |
| multi (utcsat) | **32%** | Decent — retains a third |
| fullstack_single | **14%** | Poor — most edge is overfitting |
| single (king) | **10%** | Poor — almost all edge gone |
| wage12_single | **9%** | Poor — edge doesn't generalize |
| fliponly_multi | **-14%** | Dead — negative OOS |

### Key Insight
**Multi strategies (32-47%) outperform single strategies (9-14%) on OOS/IS ratio.**

This is because:
1. Multi has fewer filters (3 vs 5) — less overfitting
2. Multi takes more positions (250+ vs 150) — more diverse sample
3. Single strategies have 5 stacked filters that pick up regime-specific patterns

---

## Key Findings

### 1. Multi Beats Single on OOS
| Metric | Multi (avg) | Single (avg) |
|---|---|---|
| OOS NET R | +53.0R | +17.0R |
| OOS/IS ratio | 40% | 11% |
| Max DD | 32.8R | 24.1R |

**Why?** Multi strategies are simpler. Fewer filters = less overfitting.

### 2. Simpler Filters Generalize Better
| Strategy | # Filters | OOS/IS |
|---|---|---|
| champion_multi | 2 (mltf + persist) | 41% |
| chopband_multi | 3 (+ chop band) | 47% |
| multi (utcsat) | 3 (+ utc skip) | 32% |
| fullstack_single | 5 (all filters) | 14% |
| single (king) | 6 (+ wage) | 10% |

**Adding the chop band actually improved OOS/IS from 41% to 47%.** This is because the chop band is a structural filter (removes choppy markets) rather than a curve-fitted filter.

### Causal SL Impact on OOS

Causal SL replaces the retroactive `swing_start_px` with a running extreme computed from the previous confirmed swing's end to the current bar. This is what a live trader can actually compute at candle close.

| Strategy | Batch OOS NET | Causal OOS NET | Delta | Batch OOS DD | Causal OOS DD | Causal OOS/IS |
|---|---|---|---|---|---|---|
| champion_multi | +70.1R | **+80.0R** | +9.9R | 37.3R | 36.0R | **53%** |
| utcsat_multi | +60.2R | **+72.8R** | +12.6R | 22.1R | 20.7R | **49%** |
| king_single | +16.9R | **+22.1R** | +5.2R | 27.9R | 20.5R | **14%** |

**Key insight:** Causal SL *improves* OOS by +5 to +13R while reducing DD. The retroactive SL sometimes survived trades it shouldn't have (masking losses). Causal SL catches these earlier → better OOS/IS ratios.

### Causal SL Impact on In-Sample

| Strategy | Batch IS NET | Causal IS NET | Delta | Batch IS DD | Causal IS DD |
|---|---|---|---|---|---|
| champion_multi | +325.8R | +248.0R | −77.8R | 17.8R | 21.2R |
| utcsat_multi | +359.0R | +295.7R | −63.2R | 14.8R | 16.0R |
| king_single | +310.7R | +244.5R | −66.2R | 11.2R | 16.6R |

**Why IS is worse but OOS is better:** The retroactive SL advantage in-sample was a form of overfitting — it used future knowledge to set tighter stops that happened to survive. In-sample, this looks great. But it doesn't generalize — on OOS, the causal SL is more honest and more robust.

### 3. The Edge is Event-Driven
- 2021 (bull run): Most strategies flat
- 2022 (crash): All strategies profitable
- FTX collapse drove 70-80% of OOS profit

**The strategies are crisis alpha — they profit from extreme volatility, not consistent inefficiency.**

### 4. All Strategies Have Similar Top Winners
Every strategy's top 5 winners include the same trades:
- Nov 2022 FTX collapse shorts
- Feb 2021 long (+12.2R)
- Apr 2021 short (+7.7R)
- Jun 2022 short (+7.2R)

**The core signal is the same across all strategies.** The filters just add/remove trades around the edges.

### 5. Drawdown is Worse OOS
| Strategy | IS DD | OOS DD | DD Increase |
|---|---|---|---|
| chopband_multi | 17.6R | 29.1R | +65% |
| champion_multi | 17.8R | 37.3R | +109% |
| multi (utcsat) | 14.8R | 22.1R | +49% |
| single (king) | 11.2R | 27.9R | +149% |

**OOS drawdowns are 1.5-2.5x worse than in-sample.** This is expected — overfitting underestimates risk.

---

## Implications

### For Live Trading
1. **Use causal SL** — retroactive SL inflates numbers by 63-78R in-sample
2. **Use multi strategies** — they generalize better (49-53% OOS/IS vs 14%)
3. **Expect lower returns** — OOS is 50% of causal-SL IS, not 100% of batch IS
4. **Expect higher DD** — OOS DD is 1.5-2x IS
5. **Position size accordingly** — if IS says 1% risk, use 0.5% live

### For Strategy Development
1. **Fewer filters = better OOS** — every filter adds overfitting risk
2. **Multi > Single** — more positions = more diverse sample = less overfitting
3. **Structural filters work** — chop band (market regime) generalizes; wage (time-based) doesn't
4. **Don't trust IS DD** — OOS DD is 1.5-2.5x worse

### For Expectations
1. **Annual OOS return (causal SL):** +36-40R/yr for best multi strategies
2. **Annual OOS return (causal SL):** +11R/yr for single strategies
3. **On Rs.30K account with 250 INR risk:**
   - Multi: Rs.9,000-10,000/yr (30-33% return)
   - Single: Rs.2,750/yr (9% return)

---

## Files

| File | Description |
|---|---|
| `data/unseen/bybit/BTCUSDT_15m.csv` | 2021-2022 15m data (70K candles) |
| `data/unseen/bybit/BTCUSDT_1h.csv` | 2021-2022 1h data (17.5K candles) |
| `data/unseen/bybit/BTCUSDT_1m.csv` | 2021-2022 1m data (1M candles) |
| `scripts/download_bybit_unseen.py` | Download script for unseen data |
| `backtest/tests/test_oos_2022.py` | OOS backtest runner |
| `backtest/tests/test_causal_sl.py` | Causal SL comparison (IS) |
| `backtest/tests/test_causal_sl_oos.py` | Causal SL comparison (OOS) |

---

## Appendix: Raw OOS Numbers

### chopband_multi
```
Yearly: 2021: +0.1R | 2022: +120.6R
Top 5 Winners: +33.1R, +19.8R, +16.3R, +13.6R, +12.2R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### champion_multi
```
Yearly: 2021: -11.0R | 2022: +116.7R
Top 5 Winners: +33.1R, +19.8R, +16.3R, +13.6R, +12.2R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### multi (utcsat)
```
Yearly: 2021: +13.2R | 2022: +79.5R
Top 5 Winners: +33.1R, +19.8R, +16.3R, +12.2R, +8.5R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### fullstack_single
```
Yearly: 2021: +12.6R | 2022: +30.1R
Top 5 Winners: +19.8R, +13.6R, +12.2R, +7.7R, +7.2R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### single (king)
```
Yearly: 2021: +12.9R | 2022: +25.1R
Top 5 Winners: +19.8R, +13.6R, +12.2R, +7.7R, +7.2R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### wage12_single
```
Yearly: 2021: +12.4R | 2022: +22.6R
Top 5 Winners: +19.8R, +13.6R, +12.2R, +7.7R, +7.2R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```

### fliponly_multi
```
Yearly: 2021: -38.9R | 2022: +47.2R
Top 5 Winners: +33.1R, +16.3R, +7.2R, +7.2R, +6.9R
Top 5 Losers: -1.0R, -1.0R, -1.0R, -1.0R, -1.0R
```
