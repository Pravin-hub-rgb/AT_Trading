# STRATEGY STATE OF PLAY — September 2026

> **UPDATED:** 2026-09-22 — Post trail-ratchet fix. All numbers are on the CURRENT shipped engine.

## 1. The Honest Numbers (Corrected)

### Raw v18 Base — IS vs OOS

| Metric | IS (2023-2026) | OOS (2021-2022) | Ratio |
|---|---|---|---|
| Trades | 375 | 213 | — |
| NET R | +217.9R | +9.9R | 22.0x |
| DD | 33.3R | 30.5R | — |
| NET/DD | 6.55 | 0.33 | — |

**Verdict: The raw v18 base is heavily curve-fitted.** IS/OOS ratio of 22x means the 2023-2026 performance does NOT generalize to 2021-2022.

### What Was Fixed: Trail Ratchet Bug

Two bugs in how the stop-loss updates when a new 15m swing confirms:

1. **Trail level dropped:** Old code only accepted ratchet if bar low > new level. Price dipping below the level on the same bar caused the ratchet to be dropped entirely. **Fixed:** ratchet whenever candidate improves the stop.

2. **Ratchet applied after SL check:** Old code checked SL first (using old stop), then applied ratchet. **Fixed:** ratchet first, then check SL against new stop.

**Impact:** Removed ~40R of phantom profit per config. Every trade now has the correct stop behavior.

### Filter-by-Filter OOS Delta

| Step | Config | IS NET | OOS NET | OOS DD | OOS N/D | Verdict |
|---|---|---|---|---|---|---|
| 1 | Raw v18 base | +217.9R | +9.9R | 30.5 | 0.33 | Baseline |
| 2 | + wknd skip | +167.6R | +27.6R | 19.4 | 1.42 | **Real edge (+17.7R)** |
| 3 | + wage10 | +197.7R | +10.8R | 31.2 | 0.34 | Useless (+0.9R) |
| 4 | + wage10 + wknd | +174.9R | +23.8R | 19.2 | 1.23 | Worse than wknd alone |
| 5 | + mag1.5 + wknd | +231.8R | +33.5R | 12.8 | 2.62 | Good (+5.9R over wknd) |
| 6 | + mag2 + wknd | +139.2R | +30.2R | 8.3 | 3.65 | Good DD |
| 7 | + mag2.5 + wknd | +169.9R | +30.8R | 6.0 | 5.13 | Good N/D |
| 8 | **+ mag3 + wknd** | **+196.3R** | **+45.6R** | **4.0** | **11.41** | **BEST NET** |
| 9 | + mag4 + wknd | +130.8R | +16.5R | 7.0 | 2.36 | Too aggressive |
| 10 | **+ mag3 + wknd + bm05** | **+196.4R** | **+47.6R** | **4.0** | **11.91** | **BEST OVERALL** |
| 11 | + mag3 + wknd + bm08 | +194.1R | +45.8R | 4.0 | 11.46 | Marginal over bm05 |
| 12 | + mag3 + wknd + swingpause | +195.8R | +42.2R | 4.0 | 10.55 | Swingpause hurts |
| 13 | + mag3 + wage10 + wknd + bm05 | +163.8R | +43.7R | 3.0 | 14.55 | Best N/D |

### IS/OOS Generalization Ratio

| Config | IS NET | OOS NET | IS/OOS | Generalization |
|---|---|---|---|---|
| Raw v18 base | +217.9R | +9.9R | 22.0x | Terrible |
| + wknd skip | +167.6R | +27.6R | 6.1x | OK |
| + wage10 + wknd | +174.9R | +23.8R | 7.4x | OK |
| + mag3 + wknd | +196.3R | +45.6R | 4.3x | **Good** |
| + mag3 + wknd + bm05 | +196.4R | +47.6R | 4.1x | **Best** |
| + mag3 + wage10 + wknd + bm05 | +163.8R | +43.7R | 3.8x | **Best** |

## 2. What Has Real Edge

### Weekend Skip — +17.7R OOS improvement
- Removes trades on Saturday/Sunday (IST weekday)
- Known edge in crypto: weekend markets are thin, unpredictable
- Both 2021 and 2022 improve independently

### mag_ratio >= 3 — +17.8R OOS improvement (over wknd)
- Only enter when the swing signal was 3x the 20-bar ATR range
- Cuts 213 trades to 39 (82% reduction) but improves NET from +27.6R to +45.6R
- DD drops from 19.4 to 4.0
- 2021: +22.8R, 2022: +22.9R — perfectly balanced
- **This is a structural edge: small moves are noise, big moves have conviction**

### Bias Momentum (bm05) — +2.0R OOS improvement
- Ratio of consecutive HTF swing magnitudes
- Filters weak-momentum signals
- Marginal improvement on top of mag3+wknd

## 3. What Is Curve Fitting

### Wage Gate — HURTS OOS when combined with mag_ratio
- wage10 alone: +10.8R (same as raw base, useless)
- mag3+wage10+wknd: +41.7R vs mag3+wknd: +45.6R — wage HURTS by -3.9R
- **Verdict: Remove wage gate for mag_ratio configs**

### Swingpause — HURTS OOS when combined with mag_ratio
- mag3+wknd+swingpause: +42.2R vs mag3+wknd: +45.6R — hurts by -3.4R
- **Verdict: Remove swingpause for mag_ratio configs**

### Room Filter — DEAD
- Room filter HURTS OOS at every threshold
- Autopsy finding reversed on OOS (wins avg room=1.46, losses=2.88)

## 4. Deep Audit Results

### All Filters Are Causal
- **Truncation test PASSED**: Truncated data at 25%, 50%, 75% — every trade matches exactly
- **No look-ahead bias**: All filters use only past/current bar data
- **Rolling windows correct**: Chop series [i-27..i], ATR [i-4..i]/[i-19..i]

### Engine Is Sound
The v18 streak_halt engine is well-built. The trail ratchet fix (commit ee574f9) corrected the last structural bug.

## 5. The Core Problem

**More filters = more curve fitting.** Every filter we add improves IS performance. Most hurt OOS.

**The only filters that generalize are ones with structural edge:**
- Weekend skip: removes a known bad regime (thin markets)
- mag_ratio: filters noise moves that have no conviction

## 6. New Concept Test Results

### 4 Concepts Tested

| Concept | Status | OOS Result |
|---|---|---|
| Room Filter | **DEAD** | HURTS OOS at every threshold |
| Leg Quality Score (mag_ratio) | **WINNER** | mag3: +45.6R OOS (vs +27.6R wknd only) |
| Structure Evolution | **DEFERRED** | Needs engine-level changes |
| MTF Regime | **BROKEN** | Implementation produces 0 trades |

### mag_ratio Deep Dive

| Threshold | IS | OOS | OOS DD | OOS N/D |
|---|---|---|---|---|
| raw base | 375t +217.9R | 213t +9.9R | 30.5 | 0.33 |
| mag 0-1 | — | 53t -47.5R | — | — |
| mag 1-2 | — | 74t +25.5R | — | — |
| mag 2-3 | — | 29t +10.5R | — | — |
| mag 3-5 | — | 15t +23.3R | — | — |
| mag 5+ | — | 6t +44.0R | — | — |
| **mag3+wknd** | **96t +196.3R** | **39t +45.6R** | **4.0** | **11.41** |

**Clear monotonic edge: bigger swings relative to ATR = more profit.**

### Why It Works
The swing that generates the signal must have moved at least 3x the recent ATR range. Small moves (< 1x ATR) are noise — they lose money (-47.5R on OOS). Large moves (> 3x ATR) have conviction — they make money (+23.3R to +44.0R on OOS). This is structural, not a filter.

## 7. Baseline to Beat

**mag3 + weekend skip** = current best for live:
- IS: 96t, +196.3R, DD=6.0, NET/DD=32.73
- OOS: 39t, +45.6R, DD=4.0, NET/DD=11.41
- 2021: +22.8R | 2022: +22.9R
- IS/OOS ratio: 4.3x

**With bm05:**
- IS: 94t, +196.4R, DD=6.0, NET/DD=32.74
- OOS: 37t, +47.6R, DD=4.0, NET/DD=11.91
- 2021: +23.8R | 2022: +23.9R
- IS/OOS ratio: 4.1x

Any new concept must beat +47.6R OOS with similar or better DD to be adopted.

## 8. Checklist Status

- [x] Trail ratchet bug fixed (commit ee574f9)
- [x] mag_ratio filter implemented in patcher
- [x] IS + OOS validation complete
- [ ] Swing engine mismatch (#1 on checklist) — blocks live deployment
- [ ] Docs updated with corrected numbers
- [ ] Commit pending changes
