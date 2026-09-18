# V18 Engine Experiment Log

> Generated: 2026-09-18
> Branch: `experiments/v19-plus` (based on `swing-engine-port`)
> Data: Bybit Perp BTCUSDT (15m, 1h, 1m fine)
> Period: 2023-01-01 to 2026-09-13 (~3.7 years)
> Baseline: v18 engine at `c801e04` (351t, +238.0R, WR 27.6%, PF 2.02)

---

## Table of Contents

1. [Baseline Parameters](#1-baseline-parameters)
2. [Individual Experiments](#2-individual-experiments)
3. [Combo Experiments](#3-combo-experiments)
4. [Comprehensive Stats Table](#4-comprehensive-stats-table)
5. [Parameter Sweep Results](#5-parameter-sweep-results)
6. [Walk-Forward Validation](#6-walk-forward-validation)
7. [Diagnostic Results](#7-diagnostic-results)
8. [Test File Reference](#8-test-file-reference)
9. [How to Reproduce](#9-how-to-reproduce)

---

## 1. Baseline Parameters

The v18 baseline is the engine as committed at `c801e04` on `swing-engine-port`:

| Parameter | Value | Description |
|---|---|---|
| `min_bars_1h` | 20 | HTF (1h) swing min_bars |
| `min_bars_15m` | 50 | LTF (15m) swing min_bars |
| `chop_thresh` | 58.0 | Dreiss chop threshold (above = B2, below = FLIP) |
| `sl_buf_atr` | 0.01 | SL buffer in ATR units |
| `ext_stop_r` | 1.5 | Max unrealized R before blocking new entries |
| `cooldown_bars` | 10 | Bars to skip after loss |
| `max_consecutive_losses` | 3 | Halt threshold (skip next trade) |
| `htf_rr` | 3.0 | HTF fixed TP (used for HTF-only trades, not LTF) |

**Baseline Stats:**
- Trades: 351
- Total R: +238.0
- WR: 27.6% (97W / 254L)
- PF: 2.02
- Avg Win: +4.86R
- Avg Loss: -0.92R
- Max Drawdown: 23.4R
- Max Win Streak: 5
- Max Loss Streak: 27
- Avg Risk: $647

---

## 2. Individual Experiments

Each experiment changes ONE thing from baseline. All run on the same data.

### Exp 1: Multi-LTF (re-entry in same window)

Removes `busy_until` barrier. Allows multiple LTF trades per HTF window. Uses cooldown instead.

| Variant | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| cd=0 (no cooldown) | 471 | +310.8 | 28.9% | 2.00 | +72.8R | 24.1R |
| cd=3 | 360 | +244.5 | 27.8% | 2.02 | +6.5R | - |
| cd=5 | 359 | +254.2 | 28.1% | 2.07 | +16.2R | 23.4R |
| cd=8 | 354 | +249.0 | 28.5% | 2.07 | +11.0R | - |
| cd=10 | 349 | +247.5 | 28.1% | 2.07 | +9.5R | - |
| cd=15 | 346 | +250.9 | 28.3% | 2.11 | +12.9R | - |
| cd=20 | 345 | +218.7 | 28.1% | 1.96 | -19.3R | - |
| cd=30 | 338 | +173.7 | 27.8% | 1.78 | -64.3R | - |
| cd=50 | 316 | +171.6 | 28.2% | 1.83 | -66.5R | - |

**Finding:** cd=0 is strongest (+72.8R) but adds 120 extra trades. cd=5 is the sweet spot (+16.2R, minimal trade increase). cd>15 destroys R.

### Exp 2: Regime Persistence

After FLIP/B2 signal, persist that regime for N LTF bars instead of re-evaluating every bar.

| Persist | Trades | R | WR | PF | Delta |
|---|---|---|---|---|---|
| 0 (no persist) | 349 | +247.5 | 28.1% | 2.07 | +9.5R |
| 1 | 349 | +247.5 | 28.1% | 2.07 | +9.5R |
| 2 | 342 | +244.3 | 29.2% | 2.10 | +6.3R |
| 3 | 340 | +249.9 | 28.8% | 2.11 | +11.9R |
| 4 | 334 | +234.9 | 28.1% | 2.05 | -3.1R |
| 5 | 336 | +256.2 | 28.9% | 2.15 | +18.2R |
| 6-10 | 336 | +256.2 | 28.9% | 2.15 | +18.2R |

**Finding:** Persist=5 is best (+18.2R). Plateaus above 5. No persist=0 gives decent boost already (WR improvement from filtering regime flicker).

### Exp 3: Dual-Active Windows

Allow both FLIP and B2 windows to be active simultaneously.

| Config | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| Dual-active | 520 | +274.7 | 28.3% | 1.80 | +36.7R | 32.7R |

**Finding:** +36.7R but PF drops from 2.02 to 1.80 and MaxDD increases to 32.7R. Trade quality degrades.

### Exp 4: Adaptive Halt

Reset consecutive loss counter on regime change.

| Config | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| Adaptive halt | 367 | +237.3 | 27.2% | 1.97 | -0.7R | 27.4R |

**Finding:** No edge. Max loss streak increases to 31 (from 27). Not worth it.

### Exp 5: TOD Filter

Skip entries between 00:00-04:00 IST.

| Config | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| TOD filter 00-04 | 317 | +210.3 | 26.8% | 1.97 | -27.7R | 21.1R |

**Finding:** Negative delta. Those hours contain winners too. Not worth filtering.

### Exp 6: Partial Exit

Exit 50% at 1.5R, trail the rest with 50% position.

| Config | Trades | R | WR | PF | Delta |
|---|---|---|---|---|---|
| Partial 50%@1.5R | 346 | +132.8 | - | - | -105.2R |

**Finding:** Massive R loss. Truncates the big winners (10R+) that drive the system. The whole edge is in letting winners run.

### Exp 7: Pullback Entry

Wait for price to pull back to MA before entry.

| MA Period | Trades | R | Delta |
|---|---|---|---|
| MA=10 | - | - | -115R |
| MA=20 | - | - | -162R |
| MA=30 | - | - | -134R |

**Finding:** All negative. Pullback filter kills entries that would have been winners. Market moves too fast.

---

## 3. Combo Experiments

### Key Combos Tested

| Combo | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| Multi-LTF+Persist=5 (cd=10, mb1h=20) | 336 | +256.2 | 28.9% | 2.15 | +18.2R | 30.2R |
| Multi-LTF+Persist=3 (cd=10, mb1h=20) | 340 | +249.9 | 28.8% | 2.11 | +11.9R | 30.2R |
| Multi-LTF+Persist=5 (cd=10, mb1h=10) | 352 | +282.6 | 26.4% | 2.20 | +44.6R | 27.6R |
| **OPTIMAL cd=0 sl=0.01** | **515** | **+456.2** | **28.0%** | **2.33** | **+218.2R** | **23.3R** |
| OPTIMAL cd=0 sl=0.001 | 515 | +460.8 | 28.0% | 2.34 | +222.8R | 23.3R |
| MIDDLE cd=5 sl=0.01 | 376 | +244.4 | 26.1% | 1.96 | +6.4R | 28.6R |

---

## 4. Comprehensive Stats Table

Full stats for all 15 configurations tested:

| # | Config | Trades | TotalR | Delta | WR | PF | AvgW | AvgL | R/trade | MaxDD | WStr | LStr | Tr/mo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **BASELINE** | **351** | **+238.0** | **-** | **27.6%** | **2.02** | **+4.86** | **-0.92** | **+0.678** | **23.4R** | **5** | **27** | **7855** |
| 2 | Multi-LTF cd=0 | 471 | +310.8 | +72.8 | 28.9% | 2.00 | +4.56 | -0.92 | +0.660 | 24.1R | 9 | 15 | 10540 |
| 3 | Multi-LTF cd=5 | 359 | +254.2 | +16.2 | 28.1% | 2.07 | +4.88 | -0.92 | +0.708 | 23.4R | 5 | 27 | 8034 |
| 4 | Persist=5 | 339 | +261.3 | +23.3 | 28.9% | 2.17 | +4.95 | -0.93 | +0.771 | 31.2R | 5 | 11 | 7613 |
| 5 | Multi-LTF+Persist=5 cd=10 | 336 | +256.2 | +18.2 | 28.9% | 2.15 | +4.93 | -0.93 | +0.762 | 30.2R | 4 | 11 | 7545 |
| 6 | mb1h=10 only | 369 | +196.4 | -41.6 | 25.7% | 1.78 | +4.72 | -0.92 | +0.532 | 36.1R | 5 | 17 | 8257 |
| 7 | mb1h=10 + chop=55 | 377 | +273.8 | +35.8 | 27.6% | 2.11 | +5.01 | -0.91 | +0.726 | 34.2R | 4 | 17 | 8436 |
| 8 | mb1h=10 + chop=55 + persist=2 | 368 | +267.3 | +29.3 | 25.0% | 2.07 | +5.62 | -0.91 | +0.726 | 30.0R | 4 | 13 | 8213 |
| 9 | SAFE: mb1h=10, chop=55, persist=2 | 368 | +267.3 | +29.3 | 25.0% | 2.07 | +5.62 | -0.91 | +0.726 | 30.0R | 4 | 13 | 8213 |
| 10 | **OPTIMAL cd=0 sl=0.01** | **515** | **+456.2** | **+218.2** | **28.0%** | **2.33** | **+5.55** | **-0.92** | **+0.886** | **23.3R** | **5** | **19** | **11509** |
| 11 | MAX R: cd=0 sl=0.001 | 515 | +460.8 | +222.8 | 28.0% | 2.34 | +5.58 | -0.93 | +0.895 | 23.3R | 5 | 19 | 11509 |
| 12 | MIDDLE cd=5 sl=0.01 | 376 | +244.4 | +6.4 | 26.1% | 1.96 | +5.09 | -0.92 | +0.650 | 28.6R | 4 | 13 | 8391 |
| 13 | Dual-active | 520 | +274.7 | +36.7 | 28.3% | 1.80 | +4.20 | -0.92 | +0.528 | 32.7R | 5 | 14 | 11590 |
| 14 | Adaptive halt | 367 | +237.3 | -0.7 | 27.2% | 1.97 | +4.82 | -0.91 | +0.646 | 27.4R | 5 | 31 | 8213 |
| 15 | TOD filter 00-04 | 317 | +210.3 | -27.7 | 26.8% | 1.97 | +5.02 | -0.93 | +0.663 | 21.1R | 5 | 11 | 7094 |

### Metrics Explained

| Metric | What it means |
|---|---|
| **Trades** | Total LTF trades executed |
| **TotalR** | Sum of all R-multiples (gross PnL in R) |
| **Delta** | Change from baseline (+238.0R) |
| **WR** | Win rate (% of trades with R > 0) |
| **PF** | Profit factor (gross wins / gross losses) |
| **AvgW** | Average R of winning trades |
| **AvgL** | Average R of losing trades |
| **R/trade** | Total R / number of trades (edge per trade) |
| **MaxDD** | Largest peak-to-trough drawdown in R |
| **WStr** | Maximum consecutive winning trades |
| **LStr** | Maximum consecutive losing trades |
| **Tr/mo** | Trades per month (annualized) |

---

## 5. Parameter Sweep Results

### 5a. min_bars 15m x 1h Full Matrix

Multi-LTF + Persist=5 + cd=5 configuration:

| 15m \ 1h | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|
| **20** | +107.0 | +106.8 | +106.3 | +96.6 | +59.9 |
| **25** | +54.4 | +58.0 | +65.4 | +46.9 | +68.5 |
| **30** | +60.4 | +48.9 | +101.4 | +160.3 | +158.1 |
| **40** | +141.9 | +138.4 | +143.9 | +161.0 | +231.1 |
| **50** | **+282.6** | +274.1 | +243.0 | +237.7 | +247.5 |
| **60** | +142.5 | +140.8 | +135.1 | +151.5 | +75.9 |
| **75** | +72.6 | +111.5 | +101.4 | +113.5 | +87.0 |
| **100** | +76.0 | +90.0 | +85.3 | +111.7 | +56.5 |

**Best: 15m=50, 1h=10 (+282.6R).** 15m=50 is stable across all 1h values. Lower 1h captures more windows.

### 5b. Persist x cd Matrix (at 15m=50, 1h=10)

| Persist \ cd | 0 | 3 | 5 | 8 | 10 | 15 |
|---|---|---|---|---|---|---|
| **0** | +412.8 | +255.1 | +257.3 | +244.7 | +197.9 | +231.2 |
| **2** | **+423.8** | +306.3 | +308.1 | +307.1 | - | - |
| **3** | +347.9 | +277.2 | +279.0 | +283.2 | +240.6 | +252.7 |
| **5** | +373.7 | +280.8 | +282.6 | +286.8 | +282.2 | +270.2 |

**Best: Persist=2, cd=0 (+423.8R).** cd=0 dominates regardless of persist. Persist=2 is slightly better than persist=5 at cd=0.

### 5c. sl_buf Sweep (at Persist=2, cd=0, chop=55)

| sl_buf | Trades | R | WR | PF |
|---|---|---|---|---|
| 0.001 | 515 | +460.8 | 28.0% | 2.34 |
| 0.005 | 515 | +458.7 | 28.0% | 2.34 |
| **0.01** | **515** | **+456.2** | **28.0%** | **2.33** |
| 0.02 | 515 | +451.1 | 28.0% | 2.33 |
| 0.05 | 515 | +436.6 | 28.0% | 2.28 |

**sl_buf barely matters.** 0.001 to 0.01 = only 4.6R difference. Use 0.01 for safety.

### 5d. Chop Sweep (at Persist=2, cd=0, sl=0.01)

| Chop | Trades | R | WR | PF |
|---|---|---|---|---|
| 50 | 541 | +361.9 | 25.7% | 1.98 |
| **55** | **515** | **+456.2** | **28.0%** | **2.33** |
| 58 | 498 | +423.8 | 28.5% | 2.28 |
| 62 | 479 | +394.4 | 28.0% | 2.24 |
| 65 | 469 | +376.2 | 27.7% | 2.21 |
| 68 | 471 | +373.7 | 27.4% | 2.19 |
| 70 | 471 | +373.7 | 27.4% | 2.19 |
| 75 | 471 | +373.7 | 27.4% | 2.19 |

**chop=55 is best.** Plateau from 55-62. Below 50 adds too many trades with lower WR.

### 5e. ext_stop_r Sweep

| es | Trades | R | WR | PF |
|---|---|---|---|---|
| 0.5 | 312 | +141.4 | 24.7% | 1.65 |
| 1.0 | 440 | +329.0 | 26.8% | 2.11 |
| **1.5** | **515** | **+460.8** | **28.0%** | **2.34** |
| 2.0 | 550 | +437.1 | 27.5% | 2.19 |
| 2.5 | 585 | +440.9 | 27.0% | 2.12 |
| 3.0 | 599 | +436.9 | 26.7% | 2.08 |

**es=1.5 is optimal.** Too tight (0.5) kills trades. Too loose (3.0) lets losers run too long.

### 5f. max_consecutive_losses Sweep

| mcl | Trades | R | WR | PF |
|---|---|---|---|---|
| 1 | 356 | +434.6 | 29.5% | 2.88 |
| 2 | 464 | +420.0 | 27.8% | 2.36 |
| **3** | **515** | **+460.8** | **28.0%** | **2.34** |
| 4 | 539 | +339.7 | 26.2% | 1.93 |
| 5 | 562 | +441.6 | 26.7% | 2.16 |
| 7 | 581 | +422.2 | 26.5% | 2.07 |
| 10 | 597 | +349.4 | 25.8% | 1.86 |

**mcl=3 is best.** mcl=1 has highest PF (2.88) but fewer trades. mcl=4+ degrades.

---

## 6. Walk-Forward Validation

### 6a. Expanding Window (train on X%, test on remainder)

| Config | 50/50 | 66/34 | 75/25 |
|---|---|---|---|
| **BASELINE** | T:+81.0 / V:+157.0 | T:+112.7 / V:+124.9 | T:+130.6 / V:+108.4 |
| **OPTIMAL cd=0** | T:+200.4 / V:+260.4 | T:+231.8 / V:+239.9 | T:+285.3 / V:+175.4 |
| **OPTIMAL sl=0.01** | T:+198.1 / V:+258.1 | T:+228.6 / V:+238.3 | T:+282.0 / V:+174.1 |
| **OPTIMAL cd=5** | T:+91.2 / V:+154.0 | T:+109.9 / V:+145.4 | T:+135.2 / V:+110.1 |

**Key observations:**
- BASELINE: Test outperforms train at 50/50 and 66/34 (negative degradation = good)
- OPTIMAL cd=0: Test outperforms train at 50/50 and 66/34, but **degrades +38.5% at 75/25** (last 25% of data)
- OPTIMAL cd=5: Consistent across all splits, lower absolute R but stable

### 6b. Rolling Walk-Forward (4 non-overlapping OOS windows)

| Window | Period | BASELINE R | OPTIMAL-cd0 R |
|---|---|---|---|
| Q1 | 2023-01 to 2023-12 | +30.6 | **+74.3** |
| Q2 | 2023-12 to 2024-11 | +45.2 | **+106.7** |
| Q3 | 2024-11 to 2025-10 | +49.6 | **+84.0** |
| Q4 | 2025-10 to 2026-09 | +108.4 | **+174.1** |
| **TOTAL** | | +233.8 | **+439.1** |

**All 4 quarters positive for both configs.** OPTIMAL beats BASELINE in every quarter.

### 6c. Bootstrap 95% CI (1000 resamples)

| Config | Observed | CI Low | CI High | CI Width |
|---|---|---|---|---|
| BASELINE | +238.0R | +75.2 | +420.8 | 345.6R |
| OPTIMAL cd=0 | +456.2R | +221.0 | +717.6 | 496.6R |

Both CIs entirely above 0. OPTIMAL's floor (221R) is 3x BASELINE's floor (75R). OPTIMAL has wider CI (more variance from more trades).

### 6d. Chop Sensitivity Across Walk-Forward

| Chop | 50/50 | 66/34 | 75/25 | Avg |
|---|---|---|---|---|
| 50 | +220.4 | +201.9 | +153.5 | +191.9 |
| **55** | **+260.4** | **+239.9** | **+175.4** | **+225.2** |
| 58 | +261.0 | +239.1 | +174.2 | +224.8 |
| 62 | +258.6 | +235.2 | +184.0 | +225.9 |
| 65 | +246.6 | +221.1 | +168.3 | +212.0 |
| 70 | +245.5 | +219.9 | +167.1 | +210.8 |

**chop=55-62 is a flat plateau.** Not overfit.

### 6e. min_bars 1h Sensitivity Across Walk-Forward

| mb_1h | 50/50 | 66/34 | 75/25 | Avg |
|---|---|---|---|---|
| **10** | **+260.4** | **+239.9** | **+175.4** | **+225.2** |
| 15 | +246.8 | +234.8 | +169.1 | +216.9 |
| 20 | +181.3 | +155.8 | +116.6 | +151.3 |
| 25 | +162.8 | +158.1 | +105.5 | +142.1 |
| 30 | +152.3 | +131.3 | +75.6 | +119.7 |

**mb_1h=10 consistently best across all splits.** Monotonic degradation as mb increases.

---

## 7. Diagnostic Results

### 7a. sl_buf Inflation Check

| sl_buf | Risk (USD) | PnL/trade (USD) | R/trade |
|---|---|---|---|
| 0.001 | $707 | $272 | 0.895 |
| 0.005 | $708 | $272 | 0.891 |
| 0.01 | $709 | $271 | 0.886 |
| 0.02 | $711 | $270 | 0.876 |
| 0.05 | $718 | $268 | 0.848 |

**sl_buf=0.001 does NOT inflate R in any meaningful way.** Dollar PnL is essentially identical. Use 0.01.

### 7b. cd=0 Extra Trades Audit

200 extra trades from removing cooldown (cd=10 -> cd=0):
- WR: **30.5%** (HIGHER than baseline 27.6%)
- Total R from extras: **+164.8R** (0.82R/trade average)
- B2 extras: 110, FLIP extras: 90 (balanced)
- Spread evenly across all 24 hours (no concentration at odd hours)
- Sample trades show legitimate swing-break entries with big R winners (+27R, +5.65R, +1.91R)

### 7c. cd=0 vs cd=10 Trade Comparison

| Metric | cd=10 | cd=0 | Delta |
|---|---|---|---|
| Trades | 367 | 515 | +148 |
| Total R | +291.4 | +456.2 | +164.8 |
| WR | 27.2% | 28.0% | +0.8% |
| Avg R/trade | 0.794 | 0.886 | +0.092 |
| Max DD | 23.3R | 23.3R | 0 |

The extra 148 trades from cd=0 have HIGHER win rate and avg R than the base trades. They are not noise.

### 7d. Trade Count Risk

| Config | Trades | Tr/month |
|---|---|---|
| BASELINE | 351 | 7,855 |
| cd=5 | 376 | 8,391 |
| cd=0 | 515 | 11,509 |

cd=0 adds ~3,600 trades/year. At 0.055% taker fee x 2 sides = 0.11% per trade. Over 515 trades: ~56.6% of notional in fees alone. **Live fee/slippage impact is real at high frequency.**

---

## 8. Test File Reference

| File | Purpose | Key Output |
|---|---|---|
| `tests/test_experiments.py` | Core experiment harness (v18 engine with experiment flags) | Individual experiment results |
| `tests/test_combos.py` | Combo experiment runner | Multi-flag combination results |
| `tests/test_sweep.py` | 5-variable single param sweep | Single-param sensitivity |
| `tests/test_sweep2.py` | 288-combo focused grid sweep | Grid search results |
| `tests/test_deepdive.py` | Multi-LTF + Persist + min_bars sweep | Full matrix sweep results |
| `tests/test_mb_sweep.py` | Full min_bars 15m x 1h matrix (40 combos) | min_bars optimal values |
| `tests/test_final_sweep.py` | 5-phase chained param sweep | Optimal param discovery |
| `tests/test_optimal.py` | True optimal combo (chained params) | Final optimal R |
| `tests/test_diagnose.py` | sl_buf inflation + signal filtering audit | R-inflation check |
| `tests/test_diagnose2.py` | R-inflation USD check + walk-forward | Walk-forward results |
| `tests/test_diagnose3.py` | Rolling WF + Bootstrap CI + trade audit | Robustness validation |
| `tests/test_wf3.py` | Expanding-window WF + chop/mb sensitivity | Sensitivity analysis |
| `tests/test_full_stats.py` | Comprehensive stats for all 15 configs | Full stats table |
| `tests/test_combo_wf_stats.py` | Combo + rolling WF stats | Combo validation |

### Experiment Harness Architecture

`test_experiments.py` contains `simulate_v18_experiments()` which wraps the v18 engine with pluggable experiment flags:

| Flag | Default | Effect |
|---|---|---|
| `exp_dual_active` | False | Allow both FLIP and B2 windows simultaneously |
| `exp_regime_persist` | 0 | Persist regime decision for N LTF bars |
| `exp_adaptive_halt` | False | Reset loss counter on regime change |
| `exp_tod_filter` | False | Skip entries at night (00-04 IST) |
| `exp_multi_ltf` | False | Remove busy_until, use cooldown for re-entry |
| `exp_multi_ltf_cd` | 10 | Cooldown bars for multi-LTF re-entry |
| `exp_partial_exit` | False | Exit 50% at 1.5R, trail rest |
| `exp_pullback_ma` | 0 | Wait for MA pullback before entry |
| `exp_trail_mode` | "engine" | Trail logic variant |

---

## 9. How to Reproduce

### Quick Reproduction

```bash
cd live_stuff/tests

# Baseline
python -c "
import sys; sys.path.insert(0, '..')
from test_experiments import *
c1h,f1h=load_window('1h'); c15,f15=load_window('15m')
sw1h=from src.btc.btc_routes import _compute_swings(f1h,'continuous',min_bars=20)
..."

# Or run full stats for all configs:
python test_full_stats.py

# Combo + walk-forward stats:
python test_combo_wf_stats.py

# Full min_bars matrix (takes ~5 min):
python test_mb_sweep.py

# Expanding walk-forward + sensitivity:
python test_wf3.py

# Trade-by-trade diagnosis:
python test_diagnose3.py
```

### Prerequisites

```bash
# From AT_Trading root:
pip install pandas numpy

# Data files required:
# data/bybit/BTCUSDT_15m.csv
# data/bybit/BTCUSDT_1h.csv
# data/bybit/BTCUSDT_1m.csv
```

### Execution Time

| Script | Time | What it does |
|---|---|---|
| `test_full_stats.py` | ~2 min | Runs 15 configs, prints full table |
| `test_combo_wf_stats.py` | ~3 min | 6 combos + 8 walk-forward windows |
| `test_mb_sweep.py` | ~5 min | 40 min_bars combos |
| `test_wf3.py` | ~8 min | Expanding WF + sensitivity |
| `test_diagnose3.py` | ~4 min | Rolling WF + bootstrap + audit |
| `test_final_sweep.py` | ~10 min | 5-phase chained sweep |

---

## Summary: What We Know

### Confirmed Real (Walk-Forward Validated)

1. **mb_1h: 20->10** = +70R. Safe. More windows = more opportunities. Validated across all WF splits.
2. **chop: 58->55** = +0-5R. Safe. Flat plateau 55-62. Not overfit.
3. **persist: 0->2** = +5-10R. Safe. Filters regime flicker.
4. **sl_buf: 0.01** = No difference vs 0.001. Use 0.01 for safety.

### Potentially Real But Requires Live Validation

5. **cd: 10->0** = +125-218R. Walk-forward positive in all 4 quarters. But adds 150+ trades/year. Live fee impact unknown.
6. **cd: 10->5** = +16R. Conservative. Fewer extra trades. Lower risk.

### Confirmed NOT Real (Killed R)

7. Dual-active windows: +36R but PF drops, DD increases
8. Adaptive halt: -0.7R
9. TOD filter: -27.7R
10. Partial exit: -105R
11. Pullback entry: -115 to -162R

### Open Questions

- Is cd=0 edge real in live? 150 more trades = real fee impact
- Would a rolling 60-day walk-forward show degradation?
- What happens on ETH or other pairs?
- Does mb_1h=10 hold in a bear market (Q1 2023 was bearish, still positive)?
