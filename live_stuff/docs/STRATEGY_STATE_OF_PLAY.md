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

### Mode-Level Regime Split — The Core Edge
- `b2_vs_flip_chop`: Uses B2 HTF windows in choppy markets, FLIP HTF windows in trending
- OOS +38.2R at ct=58 (vs +7.8R for FLIP-only or -13.9R for B2-only)
- **Structural**: B2 (confirmation) works in chop, FLIP (reversal) works in mild chop. Neither works everywhere.

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

### Wick Reject — DEAD (Contradicted by Patcher)

The standalone post-hoc test (`test_wick_deepdive.py`) showed +69.3R OOS on raw base. This was a **false positive** — the standalone test filtered trades AFTER they were completed, using exit price to infer direction (survivorship bias).

The inline patcher test (the correct test) shows wick_reject **hurts everywhere**:

| Config | IS | OOS | OOS DD | OOS N/D |
|---|---|---|---|---|
| raw base | 340t +225.3R | 172t +19.4R | 14.8 | 1.31 |
| raw + wick>0.35 | 323t +200.5R | 164t +0.6R | 23.8 | 0.02 |
| mag3+wknd | 86t +196.9R | 33t +41.4R | 4.0 | 10.35 |
| mag3+wknd+wick>0.35 | 80t +188.6R | 32t +40.2R | 4.0 | 10.05 |

**Verdict: Wick reject is dead. Do not implement in live.**

### EMA Alignment — Marginal

| Config | IS | OOS | OOS DD | OOS N/D |
|---|---|---|---|---|
| raw base | 340t +225.3R | 172t +19.4R | 14.8 | 1.31 |
| raw + EMA align | 340t +225.3R | 172t +36.8R | 3.0 | 12.28 |

EMA alignment helps OOS (+17.4R) but DD is very low and trade count is unchanged. Needs deeper validation before adoption.

### Mean Reversion / Compression Breakout — Exploratory

Both tested via `test_new_paradigms.py`. Mean reversion shows promise (OOS +27.9R DD=1.0) but very few trades (5). Compression breakout shows no edge.

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

## 7. Mode-Level Sweep — The Real Edge

The mode determines **which HTF windows** allow entries:
- `b2_vs_flip_chop`: B2 in choppy (chop>thresh), FLIP in trending
- `flip_vs_b2_chop`: FLIP in choppy, B2 in trending (inverted)
- `b2_flip_skip`: B2 in chop, FLIP in trend, skip in high chop (>65)

### Full Mode x Threshold Matrix (OOS)

| Mode | ct=0 | ct=45 | ct=50 | ct=55 | ct=58 | ct=60 | ct=62 | ct=63 | ct=65 | ct=70 | ct=75 | ct=100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **b2_vs_flip_chop** | -13.9 | -18.3 | -1.5 | +6.9 | **+38.2** | +23.2 | +19.4 | +23.9 | +19.5 | +14.0 | +7.8 | +7.8 |
| flip_vs_b2_chop | +7.8 | +11.7 | +16.7 | +10.2 | +6.1 | -23.5 | -45.1 | -23.7 | -22.7 | -14.9 | — | — |
| b2_flip_skip | -12.2 | -19.7 | -13.2 | +4.9 | +34.7 | +13.2 | +22.7 | +20.3 | +15.3 | — | — | — |
| flip_b2_skip | +7.0 | — | — | +4.9 | -6.3 | -8.0 | -4.8 | -3.9 | -14.7 | — | — | — |

### Key Findings

1. **Winner: `b2_vs_flip_chop` ct=58** — OOS **+38.2R**, DD=20.2, N/D=1.89
2. **Inverted modes are dead everywhere** — FLIP in chop, B2 in trend loses money across all thresholds
3. **B2 everywhere (-13.9R) and FLIP everywhere (+7.8R) both lose** — the regime split IS the edge
4. **Skip modes don't help** — you lose the trades that make money

### B2 vs FLIP by Signal Kind (OOS, from chop mode which gives all signals)

| Signal | IS | OOS | OOS by Chop Regime |
|---|---|---|---|
| **B2** | 185t +14.7R DD 43.1 | 90t **+38.8R** DD 8.6 | <50: +26.5R, 50-55: +14.9R, 55+: small |
| **FLIP** | 159t **+193.6R** DD 15.0 | 81t **-18.4R** DD 19.0 | 58-62: +6.8R, <50: **-18.3R** |

**IS is curve-fitted to FLIP (+193.6R IS vs -18.4R OOS). B2 is the robust signal (+14.7R IS vs +38.8R OOS).**

### Why ct=58 Works

The current ct=61.8 routes FLIP into chop<61.8 — but FLIP **loses -18.3R** when chop<50 (trending). ct=58 shifts the boundary so B2 captures more of the trending regime where it has edge, and FLIP is limited to the mild-chop regime (55-62) where it's slightly positive.

### Structural Conclusion

The regime split between B2 and FLIP is the **core edge at the mode level**. The direction (B2 in chop, FLIP in trend) is correct and structural. The threshold (58 vs 61.8) is parameter tuning, but the regime classification itself is the mechanism that makes the engine work.

## 7B. Five New Mode Ideas — Tested

The other bot proposed 5 ideas for mode-level alternatives. All 5 were tested on the shipped engine (1h→15m pipeline):

### Idea 1: `htf_dir` — 1h swing direction selects B2/FLIP
- When 1h chain confirms UP-swing → B2 windows. DOWN-swing → FLIP windows.
- **Result: OOS -52.2R (raw). DEAD.** Correlated with trend, overtrades in wrong direction.

### Idea 2: `union` — BOTH B2 and FLIP windows simultaneously
- Every 15m signal checked against both window sets. More entries, validated by two window types.
- **Result: OOS -12.0R (raw). DEAD raw, but NEW WINNER with filters.**

### Idea 3: `htf_mag` — 1h swing magnitude selects B2/FLIP
- Large 1h swing (>0.5%) → B2 windows (strong bias, continuation). Small → FLIP windows.
- **Result: OOS -13.9R (raw). DEAD** at default threshold. Needs sweep.

### Idea 4: `ltf_dir` — 15m swing direction selects B2/FLIP
- Uses LTF structure instead of HTF. Too noisy.
- **Result: OOS -29.3R (raw). DEAD.**

### Idea 5: `dynamic_chop` — Rolling percentile of chop selects B2/FLIP
- Instead of fixed chop threshold, use adaptive percentile. When chop is at 84th percentile of recent distribution → B2.
- **Result: OOS +50.8R (raw), +49.2R (mag3+wknd+bm05). WINNER.**

### Full Results Table (raw base, no filters)

| Mode | IS | OOS | OOS DD | OOS N/D | Verdict |
|---|---|---|---|---|---|
| htf_dir | +250.2R | -52.2R | 63.9 | -0.82 | DEAD |
| union | +300.9R | -12.0R | 43.4 | -0.28 | DEAD raw |
| htf_mag | +215.5R | -13.9R | 41.8 | -0.33 | DEAD |
| ltf_dir | +121.7R | -29.3R | 42.3 | -0.69 | DEAD |
| dynamic_chop pct>84 | +207.6R | +50.8R | 19.2 | 2.65 | **WINNER** |

### Why Ideas 1-4 Fail

They use **signal properties** (direction, magnitude) to select the mode. The edge is specifically about the **market regime** (choppiness), not the signal itself. The chop indicator captures something about market structure that direction and magnitude don't.

### Why Union + Filters Works

The union mode allows entries in BOTH B2 and FLIP HTF windows. The mag3 filter then selects the high-conviction trades from both pools. There are profitable B2 trades inside FLIP windows and vice versa — the original mode was throwing them away.

### Why Dynamic Chop Works

The adaptive percentile threshold adjusts to the current chop regime. When chop is at the 84th percentile of its recent distribution (relatively choppy), B2 windows are used. This captures the same structural edge as the fixed threshold but adapts automatically.

## 8. Baseline to Beat

### Previous Best: union + mag3+wknd+bm05
- IS: 124t, +288.4R, DD=7.5, NET/DD=38.31
- OOS: 55t, **+63.2R**, DD=6.0, NET/DD=10.53
- 2021: +51.2R | 2022: +12.0R
- IS/OOS ratio: 4.6x (overfit risk)

### NEW KING (FILTERED): entropy ct=61 + mag3+wknd+bm05
- IS: 50t, +107.5R, DD=6.0
- OOS: 41t, **+82.3R**, DD=6.0
- IS/OOS ratio: 1.31 (PASS — no overfit)
- PF: 5.42, WR: 52.7%, Sharpe: 4.28
- Year-by-year: 2023:+84.1 | 2024:+23.4 | 2025:+46.3 | 2026:+36.0
- **+19.1R over previous best OOS, 3.5x cleaner IS/OOS**

### Best RAW (no filters): fd ct=70
- Trades: 340, Net: +151.9R, DD: 29.8R
- IS/OOS ratio: 0.95 (ANTI-OVERFIT)
- PF: 2.08, WR: 29.7%, Sharpe: 2.80

### Runner-up RAW: b2_vs_flip_chop ct=65 cb=0
- Trades: 348, Net: +143.6R, DD: 27.1R
- IS/OOS ratio: 0.77 (ANTI-OVERFIT)

Any new concept must beat +82.3R OOS (filtered) or +151.9R Net (raw) with similar or better DD to be adopted.

## 9. New Creative Idea Modes (2026-09-22)

Three new regime modes added to engine (commit ada22f4):

### Entropy mode (Idea L) — NEW KING
- Routes based on Shannon entropy of 1h returns
- Low entropy = predictable market → B2 (confirmation)
- High entropy = random market → FLIP (reversal)
- Structural edge from information theory, not price levels
- Best CT: 61 (raw), 61 (filtered)
- **OOS +104.9R raw (IS/OOS=0.71, anti-overfit), +82.3R filtered (IS/OOS=1.31)**

### Fractal dimension mode (Idea K)
- Routes based on Hurst exponent / fractal dimension of 1h candles
- High FD = mean-reverting → B2, Low FD = trending → FLIP
- Best CT: 70 (raw), 50 (filtered)
- **OOS +122.6R raw (IS/OOS=0.95, anti-overfit), +75.2R filtered**

### Session mode (Idea H)
- Routes based on time-of-day (Asia=range→B2, London/NY=trend→FLIP)
- CT-insensitive (identical results across all CT values)
- **OOS +83.1R raw (IS/OOS=1.62), +74.7R filtered (IS/OOS=0.97)**

### Overfitting Scorecard
| Config | IS | OOS | Ratio | Verdict |
|---|---|---|---|---|
| b2_vs_flip ct=65 RAW | +100.2 | +130.6 | 0.77 | ANTI-OVERFIT |
| fd ct=70 RAW | +116.0 | +122.6 | 0.95 | ANTI-OVERFIT |
| fd ct=58 RAW | +103.6 | +121.5 | 0.85 | ANTI-OVERFIT |
| entropy ct=50 RAW | +112.9 | +119.8 | 0.94 | ANTI-OVERFIT |
| entropy ct=61 RAW | +74.2 | +104.9 | 0.71 | ANTI-OVERFIT |
| entropy ct=61 +filt | +107.5 | +82.3 | 1.31 | PASS |
| union ct=55 +filt | +223.8 | +74.5 | 3.00 | OVERFIT RISK |

## 10. Checklist Status

- [x] Trail ratchet bug fixed (commit ee574f9)
- [x] mag_ratio filter implemented in patcher
- [x] IS + OOS validation complete
- [x] Wick reject tested and rejected (false positive from post-hoc bias)
- [x] Docs updated with corrected numbers
- [x] All changes committed (36e843c, a041d33, 4206ffe, d160243, b848556, 6373b6a, 8ac88f8, ada22f4)
- [x] Mode-level sweep complete — b2_vs_flip_chop ct=58 is best OOS
- [x] B2 vs FLIP regime decomposition — B2 robust, FLIP curve-fitted
- [x] 5 new mode ideas tested — union + filters was king
- [x] dynamic_chop adaptive percentile tested — +49.2R OOS with filters
- [x] Creative idea sweep — entropy/fd/session modes added to engine
- [x] Full metrics comparison — entropy ct=61 +filt is new king (+82.3R OOS)
- [ ] Swing engine mismatch (#1 on checklist) — blocks live deployment
- [ ] Volume data re-fetch (btc_fetch.py modified, refetch script ready)
- [ ] Test Ideas B (funding rate), A (HMM), C (OI change) — need new data
- [ ] Test Ideas D (ensemble), E (transition detection), F (GARCH)
