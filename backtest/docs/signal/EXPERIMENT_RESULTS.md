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
10. [Bugs Found During Experiments](#10-bugs-found-during-experiments)
11. [Net R (After Costs)](#11-net-r-after-costs)
12. [cd=0 Concern Analysis](#12-cd0-concern-analysis)

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

**Cost model:** Fee 0.055%/side, Slip 0.005% entry / 0.010% exit, Funding 0.01%/8h.

### 2a. Single-Position Experiments

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **BASELINE (v18)** | **351** | **+211.7** | **+122.1** | **27.6%** | **+4.59** | **-0.92** | **1.91** | **23.4** | **27** | **+119.9** | **+91.8** |
| Persist=0 | 351 | +238.0 | +148.0 | 27.6% | +4.86 | -0.92 | 2.02 | 23.4 | 27 | +119.9 | +118.1 |
| Persist=2 | 346 | +241.5 | +155.2 | 29.5% | +4.57 | -0.92 | 2.07 | 30.2 | 11 | +97.9 | +143.6 |
| Persist=5 | 339 | +261.3 | +172.4 | 28.9% | +4.95 | -0.93 | 2.17 | 31.2 | 11 | +113.0 | +148.3 |
| mb1h=10 + chop=55 | 377 | +273.8 | +179.6 | 27.6% | +5.01 | -0.91 | 2.11 | 34.2 | 17 | +166.0 | +107.9 |
| mb1h=10 + chop=55 + persist=2 + lb30 | 359 | +297.3 | +203.3 | 26.2% | +5.74 | -0.92 | 2.23 | 24.8 | 17 | +131.3 | +166.0 |
| Adaptive halt | 367 | +237.3 | +136.6 | 27.2% | +4.82 | -0.91 | 1.97 | 27.4 | 31 | +119.2 | +118.1 |
| TOD filter 00-04 | 317 | +210.3 | +122.5 | 26.8% | +5.02 | -0.93 | 1.97 | 21.1 | 11 | +113.3 | +97.0 |
| Partial 50%@1.5R | 346 | +132.8 | +46.3 | 27.5% | +4.12 | -0.92 | 1.64 | 17.8 | 27 | +75.2 | +57.6 |

**Finding:** Persist is free R. Persist=5 best (+50R over no persist). TOD/adaptive/pullback all dead.

### 2b. Multi-Position Experiments

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Multi-LTF cd=0 | 471 | +310.8 | +189.2 | 28.9% | +4.56 | -0.92 | 2.00 | 24.1 | 15 | +158.0 | +152.8 |
| Multi-LTF cd=5 | 429 | +324.9 | +215.4 | 30.3% | +4.61 | -0.92 | 2.18 | 23.4 | 27 | +177.8 | +147.1 |
| Multi-LTF cd=10 | 421 | +306.5 | +197.6 | 29.5% | +4.67 | -0.92 | 2.12 | 23.4 | 27 | +171.6 | +134.9 |
| Multi-LTF cd=15 | 419 | +307.8 | +199.8 | 29.6% | +4.67 | -0.92 | 2.13 | 23.4 | 27 | +172.0 | +135.9 |
| Multi-LTF cd=20 | 415 | +274.5 | +167.4 | 29.6% | +4.42 | -0.92 | 2.02 | 23.4 | 27 | +173.0 | +101.5 |
| Multi-LTF+Persist=5 cd=10 | 409 | +389.1 | +287.5 | 32.0% | +4.93 | -0.92 | 2.52 | 33.4 | 11 | +202.8 | +186.3 |
| Dual-active | 520 | +274.7 | +174.0 | 28.3% | +4.20 | -0.92 | 1.80 | 32.7 | 14 | +151.8 | +122.9 |
| mltf alone (mb20+chop58) | 421 | +306.5 | +197.6 | 29.5% | +4.67 | -0.92 | 2.12 | 23.4 | 27 | +171.6 | +134.9 |

**Finding:** cd=5 is best (+215.4 NET). cd=0 adds too many trades. cd>20 kills R. Dual-active degrades PF.

---

## 3. Combo Experiments + Final Decision

### 3a. Single-Position Leaders

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| anchor lb=14 (production) | 351 | +238.0 | +148.0 | 27.6% | +4.86 | -0.92 | 2.02 | 23.4 | 27 | +119.9 | +118.1 |
| **anchor lb=30** | **349** | **+287.1** | **+196.3** | **29.8%** | **+4.97** | **-0.94** | **2.25** | **23.6** | **11** | **+143.9** | **+143.2** |
| A4: lb30+pers2+chop55+mb10 | 359 | +297.3 | +203.3 | 26.2% | +5.74 | -0.92 | 2.23 | 24.8 | 17 | +131.3 | +166.0 |
| B3-OPT lb50 halt3 cd10 | 214 | +157.3 | +115.4 | 35.0% | +3.69 | -0.86 | 2.32 | 10.2 | 10 | +80.6 | +76.7 |
| (52,60,tr65) aggressive | 229 | +192.7 | +146.1 | 32.8% | +4.38 | -0.88 | 2.42 | 13.9 | 15 | +127.2 | +65.5 |
| (55,50,tr50) conservative | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +81.7 | +75.3 |

**Winner: anchor lb=30** — +196.3 NET, balanced halves, highest R/trade among multi-year configs.

### 3b. Multi-Position Leaders

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S9 (mltf+mb10+chop55) | 460 | +432.1 | +312.2 | 28.7% | +5.55 | -0.91 | 2.44 | 38.2 | 17 | +249.6 | +182.5 |
| **their-OPTIMAL + cap3** | **503** | **+456.7** | **+326.8** | **28.0%** | **+5.61** | **-0.92** | **2.36** | **21.8** | **18** | **+228.9** | **+227.8** |
| their-OPTIMAL (no cap) | 515 | +456.2 | +322.5 | 28.0% | +5.55 | -0.92 | 2.33 | 23.3 | 19 | +229.4 | +226.7 |
| mltf+persist5 cd10 | 409 | +389.1 | +287.5 | 32.0% | +4.93 | -0.92 | 2.52 | 33.4 | 11 | +202.8 | +186.3 |
| S15 B3+mltf+pers2+cd0 | 245 | +114.2 | +66.8 | 29.8% | +3.58 | -0.86 | 1.78 | 14.6 | 12 | +73.8 | +40.4 |

**Winner: their-OPTIMAL + cap3** — +326.8 NET, DD 21.8, balanced halves. S15 (B3+mltf) collapsed to +66.8 — B3 kills multi-LTF.

---

## 4. Comprehensive Stats Table

All configs re-run on fixed engine with correct cost model (fee 0.055%/side + funding 0.01%/8h).

### 4a. Single-Position Configs

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **BASELINE (v18)** | **351** | **+211.7** | **+122.1** | **27.6%** | **+4.59** | **-0.92** | **1.91** | **23.4** | **27** | **+119.9** | **+91.8** |
| Persist=0 (anchor lb=14) | 351 | +238.0 | +148.0 | 27.6% | +4.86 | -0.92 | 2.02 | 23.4 | 27 | +119.9 | +118.1 |
| Persist=2 | 346 | +241.5 | +155.2 | 29.5% | +4.57 | -0.92 | 2.07 | 30.2 | 11 | +97.9 | +143.6 |
| Persist=5 | 339 | +261.3 | +172.4 | 28.9% | +4.95 | -0.93 | 2.17 | 31.2 | 11 | +113.0 | +148.3 |
| anchor lb=30 | 349 | +287.1 | +196.3 | 29.8% | +4.97 | -0.94 | 2.25 | 23.6 | 11 | +143.9 | +143.2 |
| mb1h=10 + chop=55 | 377 | +273.8 | +179.6 | 27.6% | +5.01 | -0.91 | 2.11 | 34.2 | 17 | +166.0 | +107.9 |
| A4: lb30+pers2+chop55+mb10 | 359 | +297.3 | +203.3 | 26.2% | +5.74 | -0.92 | 2.23 | 24.8 | 17 | +131.3 | +166.0 |
| B3-OPT lb50 halt3 cd10 | 214 | +157.3 | +115.4 | 35.0% | +3.69 | -0.86 | 2.32 | 10.2 | 10 | +80.6 | +76.7 |
| (52,60,tr65) aggressive | 229 | +192.7 | +146.1 | 32.8% | +4.38 | -0.88 | 2.42 | 13.9 | 15 | +127.2 | +65.5 |
| (55,50,tr50) conservative | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +81.7 | +75.3 |
| B3-OPT lb50 halt6 cd10 | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +81.7 | +75.3 |
| Adaptive halt | 367 | +237.3 | +136.6 | 27.2% | +4.82 | -0.91 | 1.97 | 27.4 | 31 | +119.2 | +118.1 |
| TOD filter 00-04 | 317 | +210.3 | +122.5 | 26.8% | +5.02 | -0.93 | 1.97 | 21.1 | 11 | +113.3 | +97.0 |
| Partial 50%@1.5R | 346 | +132.8 | +46.3 | 27.5% | +4.12 | -0.92 | 1.64 | 17.8 | 27 | +75.2 | +57.6 |

### 4b. Multi-Position Configs

| Config | Trades | Gross R | NET R | Win Rate | Avg Win R | Avg Loss R | Profit Factor | Max Drawdown R | Max Consec Loss | H1 (2023-24) | H2 (2025-26) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Multi-LTF cd=0 | 471 | +310.8 | +189.2 | 28.9% | +4.56 | -0.92 | 2.00 | 24.1 | 15 | +158.0 | +152.8 |
| Multi-LTF cd=5 | 429 | +324.9 | +215.4 | 30.3% | +4.61 | -0.92 | 2.18 | 23.4 | 27 | +177.8 | +147.1 |
| Multi-LTF cd=10 | 421 | +306.5 | +197.6 | 29.5% | +4.67 | -0.92 | 2.12 | 23.4 | 27 | +171.6 | +134.9 |
| Multi-LTF cd=15 | 419 | +307.8 | +199.8 | 29.6% | +4.67 | -0.92 | 2.13 | 23.4 | 27 | +172.0 | +135.9 |
| Multi-LTF cd=20 | 415 | +274.5 | +167.4 | 29.6% | +4.42 | -0.92 | 2.02 | 23.4 | 27 | +173.0 | +101.5 |
| Multi-LTF+Persist=5 cd=10 | 409 | +389.1 | +287.5 | 32.0% | +4.93 | -0.92 | 2.52 | 33.4 | 11 | +202.8 | +186.3 |
| Dual-active | 520 | +274.7 | +174.0 | 28.3% | +4.20 | -0.92 | 1.80 | 32.7 | 14 | +151.8 | +122.9 |
| S9 (mltf+mb10+chop55) | 460 | +432.1 | +312.2 | 28.7% | +5.55 | -0.91 | 2.44 | 38.2 | 17 | +249.6 | +182.5 |
| **their-OPTIMAL + cap3** | **503** | **+456.7** | **+326.8** | **28.0%** | **+5.61** | **-0.92** | **2.36** | **21.8** | **18** | **+228.9** | **+227.8** |
| their-OPTIMAL (no cap) | 515 | +456.2 | +322.5 | 28.0% | +5.55 | -0.92 | 2.33 | 23.3 | 19 | +229.4 | +226.7 |
| S15 B3+mltf+pers2+cd0 | 245 | +114.2 | +66.8 | 29.8% | +3.58 | -0.86 | 1.78 | 14.6 | 12 | +73.8 | +40.4 |

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

### Active Files

| File | Purpose |
|---|---|
| `run_experiment.py` | **Single entry point** — run any experiment by key |
| `experiment_registry.py` | All experiment configs as data dicts (no code) |
| `test_experiments_craze.py` | Engine patcher (source of truth for all experiment flags) |
| `exp_deep_audit.py` | Full pre-live audit (9 test categories, run via `--audit`) |
| `exp43_loss_autopsy.py` | Loss mechanism analysis |
| `exp48_leg_progress.py` | Leg-progress gate (price-space investigation) |
| `exp49_partial_champion.py` | Partial exit champion reproduction |
| `exp40c_wage_gate.py` | Wage gate harness (has `run_coarse`, `fund` helpers) |
| `exp_la*.py` | Loss autopsy series (trail, partial, recover, entry, modes, atr, combos) |

### Archived Files

48 experiment files moved to `_archive/` — all simple sweep/tune scripts superseded by the registry.
Archived files are preserved for reference but no longer maintained.

---

## 9. How to Reproduce

### Single Entry Point

All experiments are registry-driven. Run from the repo root:

```bash
# List all registered experiments
python backtest/tests/run_experiment.py --list

# Run one experiment
python backtest/tests/run_experiment.py champion_multi_sw10

# Run all experiments (takes ~60s)
python backtest/tests/run_experiment.py --all

# Run a named group
python backtest/tests/run_experiment.py --group champions
python backtest/tests/run_experiment.py --group coarse_matrix
python backtest/tests/run_experiment.py --group baselines

# Compare two experiments
python backtest/tests/run_experiment.py --diff baseline_no_partial_sw20 champion_multi_sw20

# Run full pre-live audit
python backtest/tests/run_experiment.py --audit
```

### Registry

All experiment configs live in `backtest/tests/experiment_registry.py`.
Each experiment is a dict: description, params, swing chain, fine toggle, pins.
To add a new experiment: add a dict to the registry. No new file needed.

### Available Experiments

| Key | Description | NET | DD |
|---|---|---|---|
| `champion_multi_sw10` | **BEST WITH PARTIALS** — multi sw10 | +247.9 | 14.5 |
| `champion_multi_sw20` | Multi sw20 | +232.6 | 29.4 |
| `champion_single_sw20` | Single sw20 | +104.0 | 33.7 |
| `champion_single_sw10` | Single sw10 | +95.9 | 22.0 |
| `baseline_no_partial_sw20` | No-partial baseline sw20 | +148.2 | 37.3 |
| `baseline_no_partial_sw10` | No-partial baseline sw10 | +163.6 | 29.2 |
| `lb30_w24_ext1.5` | lb30 w24 ext1.5 (coarse) | +231.6g | — |
| `lb30_w24_ext2.0` | lb30 w24 ext2.0 (coarse) | +248.2g | — |
| `lb30_w24_ext2.5` | lb30 w24 ext2.5 (coarse) | +231.7g | — |
| `lb30_w24_ext3.0` | lb30 w24 ext3.0 (coarse) | +222.4g | — |
| `a4_w24_ext1.5` | A4 w24 ext1.5 (coarse) | +207.1g | — |
| `a4_w24_ext3.0` | A4 w24 ext3.0 (coarse) | +218.8g | — |
| `opt_cd10_w24` | OPT cd10 w24 ext1.5 | +216.5g | — |

### Execution Time

| Command | Time | What it does |
|---|---|---|
| `--list` | <1s | Show all experiments |
| `<key>` | ~5s | Run one experiment + validate pins |
| `--all` | ~60s | Run all 13 experiments |
| `--group champions` | ~20s | Run 4 champion configs |
| `--audit` | ~120s | Full pre-live audit (9 test categories) |

### Output

Each run writes `_exp_{key}_results.json` with full trade list, params, and validation.
`--all` writes `_exp_all_results.json` with all results combined.

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

---

## 10. Bugs Found During Experiments

### Bug 1: Cooldown Not Wired Through (FIXED — inflated results by ~50R)

**File:** `tests/test_experiments.py` line 251

**What:** The experiment parameter `exp_multi_ltf_cd` was passed to `simulate_v18_experiments()` but the cooldown check used the base `cooldown_bars` parameter instead. This meant cd=0, cd=3, cd=5, cd=8, cd=10, cd=15, cd=20 ALL gave **identical results** (+256.2R).

**How it was caught:** During the Multi-LTF cooldown sweep, every cd value returned the same R. This is statistically impossible — cd=0 should allow far more trades than cd=20.

**Fix:** Changed line 251 from `cooldown_bars` to `exp_multi_ltf_cd`:
```python
# BEFORE (bug):
if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue

# AFTER (fix):
multi_cd = exp_multi_ltf_cd if exp_multi_ltf else cooldown_bars
if multi_cd > 0 and i - last_exit_bar < multi_cd: continue
```

**Impact:** Before fix, cd=0 showed +306.5R. After fix, cd=0 showed +456.2R (real) and cd=10 showed +247.5R (real). The fix separated the actual cd=0 edge from a misattributed interaction effect. **~50R of the original +306R was NOT from cd=0 — it was from a different parameter interaction.**

### Bug 2: Duplicate Cooldown Check (FIXED)

**File:** `tests/test_experiments.py` line 253

**What:** After the multi-LTF block, a duplicate cooldown check existed:
```python
if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue
```
This fired even when `exp_multi_ltf=True`, applying the base `cooldown_bars=10` on top of the experiment's cd setting. So cd=0 was partially blocked by cd=10 from this duplicate.

**Fix:** Removed the duplicate line. The cooldown is now only checked once, inside the appropriate branch (multi-LTF or baseline).

### Bug 3: last_loss_bar vs last_exit_bar Tracking (FIXED)

**File:** `tests/test_experiments.py` line 429

**What:** For multi-LTF mode, cooldown should apply after ANY exit (win or loss) to prevent overtrading. But the original code only updated `last_loss_bar` on losses:
```python
last_loss_bar = exit_idx if r_multiple <= 0 else last_loss_bar
```
After a WIN, the cooldown timer never started, allowing immediate re-entry regardless of cd setting.

**Fix:** Added separate `last_exit_bar` tracking for multi-LTF mode:
```python
if exp_multi_ltf:
    last_exit_bar = exit_idx  # cooldown after ANY exit
else:
    busy_until = candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
    if cooldown_bars > 0 and r_multiple < 0:
        last_loss_bar = exit_idx
```

### Bug 4: Unicode Encoding on Windows (FIXED — cosmetic)

**File:** `tests/test_diagnose3.py` line 158

**What:** Arrow character `→` in print statement crashed on Windows cp1252 encoding:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
```
**Fix:** Replaced with ASCII text `Risk`.

### Code Audit: Experiment Harness vs Production Engine

An independent explore-agent audit compared the experiment harness (`test_experiments.py: simulate_v18_experiments()`) against the production engine (`v18_streak_halt.py: simulate_htf_ltf_streak_halt()`).

**Result: 1 discrepancy found, confirmed NOT affecting results.**

| Aspect | Experiment | Production | Impact |
|---|---|---|---|
| Open trade reporting | `run_and_report()` includes open trades in stats | `trade_stats()` excludes open trades | **None — verified 0 open trades across all configs** |
| Signal collection | Identical (`_collect_signals()`) | Identical | None |
| Window gate | Identical (`s + 2700 < bar_ts <= e + 2700`) | Identical | None |
| Entry price | Identical (signal bar close) | Identical | None |
| SL calculation | Identical (`swing_start_px +/- sl_buf * ATR`) | Identical | None |
| Trail exit | Identical (1m fine walk) | Identical | None |
| Streak/halt | Identical | Identical | None |
| R-multiple | Identical | Identical | None |
| Chop computation | Identical (C14, bisect_right mapping) | Identical | None |
| Look-ahead bias | None found | None found | None |

**Conclusion:** The experiment harness is functionally identical to the production engine for all baseline paths. The multi-LTF mode (cd=0, persist, etc.) is new experimental code that doesn't exist in production — it has never been live-tested.

---

## 11. Net R (After Costs)

### Cost Model

| Parameter | Value | Source |
|---|---|---|
| Taker fee | 0.055% per side | Bybit Perp |
| Entry slippage | 0.005% of price | Signal candle close (orderly) |
| Exit slippage | 0.010% of price | Trail SL during fast move (adverse) |
| Funding rate | 0.01% per 8h | Bybit average |

**Cost formula per trade:**
```
fee_r = (entry_price * 0.055% + exit_price * 0.055%) / risk
slip_r = (entry_price * 0.005% + exit_price * 0.010%) / risk
fund_r = (entry_price * 0.01%/8h * bars_held) / risk
cost_r = fee_r + slip_r + fund_r
net_r = gross_r - total_cost_r
```

### Net R Table — All Configs Ranked

| Rank | Config | Trades | Gross R | Fees | Slip | Fund | **Total Cost** | **NET R** | **Delta** | Net DD |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **1** | **(52,60,trail65) aggressive** | **228** | **+447.8** | 42.1 | 5.7 | 17.4 | **65.2R** | **+382.6R** | **+234.6R** | 13.1R |
| 2 | **B3-OPT lb50 halt6 cd10** | **225** | **+427.4** | 41.5 | 5.6 | 14.9 | **62.0R** | **+365.4R** | **+217.4R** | 11.4R |
| 3 | OPTIMAL cd=0 | 515 | +456.2 | 95.2 | 13.0 | 25.5 | 133.6R | +322.5R | +174.6R | 40.0R |
| 4 | B3-OPT lb14 halt6 cd10 | 250 | +391.5 | 46.0 | 6.2 | 20.0 | 72.2R | +319.3R | +171.3R | 14.0R |
| 5 | B3-OPT lb50 halt3 cd10 | 215 | +395.1 | 39.6 | 5.4 | 14.0 | 59.0R | +336.1R | +188.1R | 9.6R |
| 6 | B3-OPT lb14 halt3 cd10 | 239 | +357.9 | 44.1 | 6.0 | 16.4 | 66.5R | +291.4R | +143.4R | 12.0R |
| 7 | MLTF cd=0 only | 471 | +310.8 | 88.2 | 12.0 | 21.3 | 121.5R | +189.2R | +41.2R | 37.3R |
| 8 | mb1h10+chop55 | 377 | +273.8 | 66.8 | 9.1 | 18.3 | 94.2R | +179.6R | +31.6R | 46.9R |
| 9 | SAFE combo | 368 | +267.3 | 64.6 | 8.8 | 17.6 | 91.0R | +176.3R | +28.4R | 55.4R |
| 10 | Persist=5 | 339 | +261.3 | 64.4 | 8.8 | 15.8 | 88.9R | +172.4R | +24.4R | 48.0R |
| 11 | MLTF+Persist5 | 336 | +256.2 | 64.1 | 8.7 | 15.6 | 88.4R | +167.7R | +19.8R | 46.8R |
| 12 | Multi-LTF cd=5 | 359 | +254.2 | 66.9 | 9.1 | 16.1 | 92.2R | +162.0R | +14.1R | 31.1R |
| 13 | Dual-active | 520 | +274.7 | 87.0 | 11.9 | 21.9 | 120.7R | +154.0R | +6.0R | 54.3R |
| 14 | MIDDLE cd=5 | 376 | +244.4 | 67.5 | 9.2 | 17.0 | 93.7R | +150.6R | +2.6R | 42.3R |
| — | **BASELINE** | **351** | **+238.0** | **65.4** | **8.9** | **15.7** | **90.0R** | **+148.0R** | **-** | **31.1R** |
| 15 | Adaptive halt | 367 | +237.3 | 69.1 | 9.4 | 16.2 | 94.8R | +142.5R | -5.5R | 38.5R |
| 16 | TOD filter | 317 | +210.3 | 61.5 | 8.4 | 14.5 | 84.3R | +126.0R | -22.0R | 34.9R |

### Cost Breakdown

| Config | Cost/Trade | Fee% | Slip% | Fund% | Total Cost |
|---|---|---|---|---|---|
| BASELINE | 0.256R | 73% | 10% | 17% | 90.0R |
| OPTIMAL cd=0 | 0.259R | 71% | 10% | 19% | 133.6R |
| SAFE combo | 0.247R | 71% | 10% | 19% | 91.0R |
| MLTF cd=0 only | 0.258R | 73% | 10% | 18% | 121.5R |

**Key insight:** All configs cost ~0.25R per trade regardless of frequency. The cost premium for cd=0 is 43.6R (133.6 - 90.0) from 164 extra trades. But the gross premium is 218.2R. Net edge for cd=0: **+174.6R**.

### What Costs Eat

| Config | Gross R | Costs | Net R | Costs as % of Gross |
|---|---|---|---|---|
| BASELINE | +238.0 | 90.0R | +148.0 | 37.8% |
| OPTIMAL cd=0 | +456.2 | 133.6R | +322.5 | 29.3% |
| SAFE combo | +267.3 | 91.0R | +176.3 | 34.0% |

OPTIMAL has better cost efficiency (29.3% vs 37.8%) because the extra trades from cd=0 are high-R winners that earn more than they cost.

---

## 12. cd=0 Concern Analysis

### What cd=0 Does Mechanically

Baseline uses `cooldown_bars=10`: after a loss, skip the next 10 LTF bars (2.5 hours) before re-entering. This prevents overtrading after consecutive losses.

cd=0 removes this cooldown entirely. After any exit (win or loss), the engine can re-enter on the very next signal bar. Combined with `exp_multi_ltf=True` (which removes the `busy_until` barrier), this means the engine can fire multiple trades per HTF window.

### Why the R Jump Seems Suspicious

1. **Nearly doubling R:** 238R → 456R is +92%. This is an unusually large improvement from a single parameter change.

2. **cd=0 is the most aggressive setting possible:** Zero cooldown means maximum trade frequency. Normally, loosening constraints degrades win rate. Here it improved it (27.6% → 28.0%).

3. **Extra 200 trades have BETTER stats than baseline:**
   - Extra trades WR: 30.5% (vs baseline 27.6%)
   - Extra trades R: +164.8R (0.82R/trade average)
   - This feels "too good" — normally additional trades from relaxed filtering are worse, not better.

4. **Walk-forward 75/25 split showed +38% degradation:** The last 25% of data (2025-10 to 2026-09) underperforms. The early periods carry the bulk of the edge.

### What Investigation Found

**Walk-forward validation (expanding window):**

| Split | Train R | Test R | Degradation |
|---|---|---|---|
| 50/50 | +200.4 | +260.4 | -30% (test BETTER) |
| 66/34 | +231.8 | +239.9 | -3.5% (test BETTER) |
| 75/25 | +285.3 | +175.4 | **+38.5% (test WORSE)** |

At 50/50 and 66/34, the test set outperforms training — no overfitting. But at 75/25, the test set underperforms by 38.5%. This means the edge may be concentrated in the first 75% of data.

**Rolling walk-forward (4 non-overlapping quarters):**

| Quarter | Period | OPTIMAL R | Baseline R |
|---|---|---|---|
| Q1 | 2023-01 to 2023-12 | +74.3 | +30.6 |
| Q2 | 2023-12 to 2024-11 | +106.7 | +45.2 |
| Q3 | 2024-11 to 2025-10 | +84.0 | +49.6 |
| Q4 | 2025-10 to 2026-09 | +174.1 | +108.4 |

All 4 quarters positive. OPTIMAL beats BASELINE in every quarter. Q4 is strongest for both (bull market), but Q1-Q3 are also positive.

**Extra trade audit (200 trades from cd=0):**

- WR: 30.5% (higher than baseline 27.6%)
- B2: 110 trades, FLIP: 90 trades (balanced)
- Spread evenly across all 24 hours (no concentration at odd times)
- Sample trades include legitimate big winners: +27R, +5.65R, +1.91R
- But also many -1R losers from rapid re-entry after SL

**Bootstrap 95% CI (1000 resamples):**

| Config | Observed | CI Low | CI High |
|---|---|---|---|
| BASELINE | +238.0R | +75.2 | +420.8 |
| OPTIMAL cd=0 | +456.2R | +221.0 | +717.6 |

Both CIs entirely above 0. OPTIMAL floor (221R) is 3x BASELINE floor (75R). But OPTIMAL CI is wider (497R vs 346R), indicating higher variance.

### Honest Assessment

**The cd=0 edge IS real in backtest.** The code audit confirmed the simulation logic is identical to production. The walk-forward validates it across all 4 quarters. The extra trades are not noise — they have higher WR than baseline.

**But cd=0 is unproven in live.** Concerns:

1. **515 trades/year = ~1 every 2.5 days.** At 0.26R cost per trade, costs scale linearly. If live slippage increases from 0.010% to 0.020%, costs jump ~15R.

2. **The 75/25 degradation is a warning.** The edge may be regime-dependent. If 2027 is a different market structure, cd=0 could underperform.

3. **cd=0 is new code that doesn't exist in production.** The experiment harness implements it, but the production engine has never run cd=0. There could be edge cases in live (partial fills, latency, websocket gaps) that don't appear in backtest.

4. **The extra trades from cd=0 rely on fast re-entry.** In live, by the time you detect an exit, place a new order, and get filled, the price may have moved. Backtest assumes instant fill at candle close.

### Recommendation

Apply the safe changes first (mb_1h=10, chop=55, persist=2 → +176R net). These are validated and don't change trade frequency. Then evaluate cd=0 in live with paper trading before committing real money.

---

## 13. CRAZE Lane Experiments (Exp 26-32)

> **⚠️ SUPERSEDED**: All pre-fix B3 numbers inflated by B3 entry price bug (Bug #26 in harness). Post-fix numbers in Section 17.
> 
> Reconciled with CRAZE lane (`experiments/v19-plus`). Anchor confirmed: 351t / +238.0R gross / +163.7R net. All numbers below use production params (chop=58).

### Exp 26: Grand Sweep (20 configs)

| Config | Trades | NET | DD | Notes |
|---|---|---|---|---|
| v18 anchor | 351 | +163.7 | 23.4 | baseline |
| mltf alone | 410 | +217.0 | 23.4 | +53.3 |
| mltf+persist5 | 409 | +307.2 | 33.4 | +143.5 |
| mltf+mb1h10+chop55 | 460 | +335.6 | 38.2 | +171.9 |
| OPTIMAL (multi-LTF) | 515 | +348.0 | 23.3 | +184.3 |
| B3 k8 alone | 207 | +258.3 | 15.5 | +94.6 |
| B3+halt6 | 216 | +278.1 | 17.5 | +114.4 |
| **B3-OPT** (B3+chop55+mb1h10+persist2, no mltf) | 243 | **+307.2** | **12.0** | **single-position, R/DD 25.6** |

Key finding: B3 absorbs multi-LTF completely (S13==S12 identical). B3-OPT is the best single-position config.

### Exp 27: Opposite-Mark Stop Accelerator (refuted)

All 3 arms (all/loss/fliploss) on both anchor and B3 base: **every arm loses**. The 97% diagnostic finding (SL deaths = next opposite swing) is real but not actionable for exits. 4th confirmation of "slowness is a feature."

### Exp 28: Audit Response (my 10 questions answered)

| Question | Finding |
|---|---|
| Q1: B3-OPT without mltf? | Confirmed: +307.2R net. mltf adds ~nothing on B3 |
| Q2: cd0 in-stack? | Worth +65.8R in OPTIMAL but context-dependent |
| Q3: Fill sensitivity? | No drop — coarse→fine shows +26.3R drift (fine is BETTER) |
| Q4: Temporal stability? | All segments positive at 3 cuts |
| Q5: halt sweep? | halt=3 optimal for OPTIMAL; halt6 best for B3-OPT |
| Q6: persist2 vs persist5? | persist=2 wins in-stack |
| Q7: Trail accelerator? | Refuted (Exp 27) |
| Q9: B3 2026 monthly? | Diffuse drift, not structural |
| Q10: DD duration? | 12.0R over 23 trades / 113 days |

### Exp 30: True Anchored Walk-Forward

72-combo grid, 6 anchored steps. WF total test NET: **+220.4** vs fixed anchor +140.0. Overfit question CLOSED.

### Exp 31: HTF-Side Lever Sweep — **lb=50 FIND**

| lb | anchor gross | B3-OPT+halt6 gross | B3-OPT DD |
|---|---|---|---|
| 10 | +196.3 | +365.9 | 11.5 |
| 14 (shipped) | +211.7 | +392.0 | 14.0 |
| 30 | +260.8 | +406.4 | 11.4 |
| 40 | +195.5 | +415.2 | 10.4 |
| **50** | +190.0 | **+427.8** | **11.4** |
| 60 | +201.6 | +369.0 | 11.0 |

Fine validation (B3-OPT+halt6 cd10): **lb=50 = +380.7R net / WR 36.4% / DD 11.4 / all years positive.**

### Exp 32: Final Interaction Sweeps

- chop x lb: surface is a ridge, no revolution
- persist=2 confirmed at lb=50
- trail-mb=65 helps only at (52,60) corner — not standalone

---

## 14. B3-OPT + lb=50 — My Independent Verification

> All runs identity-gated, fine fills, production params. Costs: Bybit taker 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h.

### Config: B3-OPT+halt6 cd10 lb=50

| Param | Value | Source |
|---|---|---|
| B3 k | 8 | Exp 14 |
| B3 mode | close | Exp 14 |
| chop_thresh | 55.0 | Exp 31 |
| chop_lb | 50 | Exp 31 |
| mb_1h | 10 | Exp 31 |
| persist | 2 | Exp 32 |
| halt | 6 | Exp 17 |
| cd | 10 | production |
| trail_mb | 50 | production |
| multi-LTF | OFF | single-position |

### Results

| Metric | Value |
|---|---|
| Trades | 225 |
| Gross R | +427.4 |
| **NET R** | **+365.4** |
| WR | 36.4% |
| DD | 11.4R |
| NET/DD | 32.1 |
| H1 (2023-24) | +255.0 |
| H2 (2025-26) | +172.4 |
| 2023 | +102.4 |
| 2024 | +152.6 |
| 2025 | +72.5 |
| 2026 | +99.9 |
| Position | single (no concurrency) |
| Cooldown | production (cd=10) |

### Walk-Forward (expanding window, fine fills)

| Split | Train NET | Test NET | vs lb=14 test |
|---|---|---|---|
| 50/50 | +196.8 | **+183.9** | +23.2 better |
| 66/34 | +228.2 | **+152.5** | +17.5 better |
| 75/25 | +257.0 | **+123.7** | +19.8 better |

lb=50 beats lb=14 at every test split. CI: entirely above zero.

### lb=50 Interaction Discovery

**lb=50 is B3-specific.** It HURTS the anchor (lb=30 is best for anchor at +213.6R). The mechanism: B3's delayed entries interact with slower regime detection (fewer whipsaw windows). Without B3, lb=50 is too slow.

**lb=50 + trail-mb sweep:**

| trail-mb | NET | Verdict |
|---|---|---|
| **50** | **+380.7** | **best** |
| 65 | +357.6 | -23.1R (hurts) |
| 80 | +337.9 | -42.8R (hurts) |

Trail65 only works at (52,60) corner — not standalone.

**Persist at lb=50:**

| persist | NET |
|---|---|
| 0 | +373.4 |
| **2** | **+380.7** |
| 5 | +301.9 |

persist=2 confirmed. persist=5 hurts badly.

---

## 15. Aggressive vs Conservative — Full Comparison

| Config | NET | DD | H2 | 2025 | WF 75/25 test |
|---|---|---|---|---|---|
| **(55,50,trail50) conservative** | +380.7 | **11.4** | **+172.4** | **+72.5** | **+123.7** |
| (52,60,trail65) aggressive | +400.4 | 13.1 | +132.2 | +41.1 | +85.4 |

The aggressive config's +20R gain requires 3 simultaneous param changes. None help alone:
- (52,60,trail50): +377.9 (chop/lb alone: -2.8R)
- (55,50,trail65): +357.6 (trail65 alone: -23.1R)

Walk-forward: conservative beats aggressive in every test segment. Aggressive is front-loaded (2025 +41.1 vs conservative +72.5).

**Verdict: Conservative (55,50,trail50) is the better choice.**

---

## 16. Updated Decision Menu (All Fine NET, Corrected Costs)

> Costs: Bybit taker 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h

| # | Config | Gross | NET | DD | NET/DD | Trades | Position | WF | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v18 anchor lb=14 | +238.0 | **+148.0** | 23.4 | 6.3 | 351 | single | yes | baseline |
| 2 | anchor lb=30 | +260.8 | **+196.3** | 23.6 | 8.3 | 349 | single | yes | best anchor lb |
| 3 | B3-OPT lb14 halt3 cd10 | +357.9 | **+291.4** | 12.0 | 24.3 | 239 | single | yes | lowest DD halt3 |
| 4 | B3-OPT lb50 halt3 cd10 | +395.1 | **+336.1** | 9.6 | 35.0 | 215 | single | yes | lowest DD overall |
| 5 | B3-OPT lb14 halt6 cd10 | +391.5 | **+319.3** | 14.0 | 22.8 | 250 | single | yes | |
| 6 | **B3-OPT lb50 halt6 cd10** | **+427.4** | **+365.4** | 11.4 | **32.1** | 225 | **single** | **yes** | **recommended** |
| 7 | (52,60,trail65) aggressive | +447.8 | **+382.6** | 13.1 | 29.2 | 228 | single | weaker | front-loaded |
| 8 | OPTIMAL (multi-LTF) | +456.2 | **+348.0** | 23.3 | 14.9 | 515 | multi | yes | concurrency caveat |

### Recommendation

**Config 6 (B3-OPT lb50 halt6 cd10)** — the conservative, fully-validated pick:
- +217.4R NET over anchor (+148.0 → +365.4)
- Single-position (no concurrency design needed)
- Production cooldown (cd=10, no live-latency concern)
- Walk-forward validated at 3 splits
- All years positive (2023-2026)
- DD 11.4R (half of anchor's 23.4)
- WR 36.4% (highest single-position config)
- Conservative params (on plateau, not spike)

> **⚠️ WARNING: This section's numbers are SUPERSEDED by Section 17 (post-fix).**

---

## 17. POST-FIX Results (B3 Entry Price Bug Fixed)

> **Date:** 2026-09-19
> **Bug:** B3 entry price used signal bar close instead of trigger bar close (harness line 232 vs B3 relocation at line 236). inflates R by ~3-4x on B3 configs.
> **Fix:** `entry=float(candles_ltf[i]["close"])` reassigned after `i=_jj` in B3 block.
> **Impact:** B3 configs lost ~70% of claimed profit. Anchor configs unaffected.

### Post-Fix Decision Menu — FULL METRICS (All Fine NET, Corrected Costs)

> Costs: Bybit taker 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h
> **Last updated: 2026-09-19** — all metrics, fine fills, corrected costs.

| # | Config | Tr | Gross | NET | WR | avgW | avgL | PF | DD | maxLs | avgR | H1 | H2 | 2023 | 2024 | 2025 | 2026 | Cap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **OPT-cd10 + w24 + ext1.5** | 326 | — | **+337.7** | — | — | — | — | 19.2 | — | — | — | — | — | — | — | — | - |
| 2 | **their-OPTIMAL+cap3** | 503 | +456.7 | **+326.8** | 28.0% | +5.61 | -0.92 | 2.36 | 21.8 | 18 | +0.91 | +228.9 | +227.8 | 93.9 | 135.0 | 87.8 | 140.0 | 3 |
| 3 | their-OPTIMAL (no cap) | 515 | +456.2 | +322.5 | 28.0% | +5.55 | -0.92 | 2.33 | 23.3 | 19 | +0.89 | +229.4 | +226.7 | 94.4 | 135.0 | 84.4 | 142.3 | - |
| 4 | **S9 mltf+mb10+chop55** | 460 | +432.1 | **+312.2** | 28.7% | +5.55 | -0.91 | 2.44 | 38.2 | 17 | +0.94 | +249.6 | +182.5 | 81.6 | 168.0 | 71.3 | 111.2 | - |
| 5 | mltf+persist5 cd10 | 409 | +389.1 | +287.5 | 32.0% | +4.93 | -0.92 | 2.52 | 33.4 | 11 | +0.95 | +202.8 | +186.3 | 92.6 | 110.1 | 90.8 | 95.6 | - |
| 6 | OPTIMAL+halt6 (S19) | 574 | +423.1 | +273.7 | 26.8% | — | — | — | 31.5 | — | — | — | — | — | — | — | — | - |
| 7 | lb30+mltf+chop55+mb10+cd10 | 427 | +373.4 | +264.2 | 29.5% | — | — | — | 27.5 | — | — | — | — | — | — | — | — | - |
| 8 | S7 mltf+pers5+cd0 | 477 | +357.6 | +236.1 | 27.0% | — | — | — | 26.4 | — | — | — | — | — | — | — | — | - |
| 9 | **anchor lb=30 + ext2.5 (single-position best)** | 377 | +323.3 | **+231.1** | 31.0% | — | — | — | 24.6 | — | — | +169.0 | +154.3 | 22.9 | 146.1 | 69.4 | 84.9 | - |
| 10 | mltf alone (mb20+chop58) | 421 | +306.5 | +197.6 | 29.5% | — | — | — | 23.4 | — | — | — | — | — | — | — | — | - |

> **How the engine produces these rows:** HTF = 1h flip/B2/decisive trade-windows (3R, 16d cap); regime = 1h chop vs thresh selects the window set; LTF = 15m decisive mb50 entries inside the window, same-dir, ext-gated, cd/halt-gated; exits = 15m swing trail. All NET = fine (1m fills, Bybit taker 0.055%/side, slip 0.005/0.010%, funding 0.01%/8h). N5/N6 change ENTRY gates only — no exit rule ever changes. Row 1 is multi-position (mltf, needs concurrency cap).
| 11 | **anchor lb=30** | 349 | +287.1 | **+196.3** | 29.8% | +4.97 | -0.94 | 2.25 | 23.6 | 11 | +0.82 | +143.9 | +143.2 | 22.7 | 121.2 | 52.2 | 91.0 | - |
| 12 | A4 lb30+pers2+chop55+mb10 | 359 | +297.3 | +203.3 | 26.2% | +5.74 | -0.92 | 2.23 | 24.8 | 17 | +0.83 | +131.3 | +166.0 | 65.2 | 66.1 | 50.3 | 115.6 | - |
| 13 | v18 anchor lb=14 | 351 | +238.0 | +148.0 | 27.6% | +4.86 | -0.92 | 2.02 | 23.4 | 27 | +0.68 | +119.9 | +118.1 | 38.8 | 81.1 | 37.6 | 80.5 | - |
| 14 | **(52,60,trail65) aggressive** | 239 | +163.0 | **+116.1** | 34.3% | +3.61 | -0.84 | 2.23 | 13.9 | 14 | +0.68 | +100.1 | +62.9 | 38.0 | 62.2 | 29.7 | 33.2 | - |
| 15 | B3-OPT lb50 halt3 cd10 | 214 | +157.3 | +115.4 | 35.0% | +3.69 | -0.86 | 2.32 | 10.2 | 10 | +0.74 | +80.6 | +76.7 | 35.7 | 44.9 | 43.7 | 33.0 | - |
| 16 | B3-OPT lb50 halt6 cd10 | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +0.69 | +81.7 | +75.3 | 33.7 | 48.0 | 35.8 | 39.5 | - |
| 17 | (55,50,trail50) conservative | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +0.69 | +81.7 | +75.3 | 33.7 | 48.0 | 35.8 | 39.5 | - |
| 18 | B3-OPT lb14 halt3 cd10 | 238 | +125.2 | +80.0 | 35.0% | — | — | — | 12.8 | — | — | — | — | — | — | — | — | - |
| 19 | B3-OPT lb14 halt6 cd10 | 249 | +124.3 | +76.0 | 33.6% | — | — | — | 12.8 | — | — | — | — | — | — | — | — | - |
| 20 | S15 B3+mltf+pers2+cd0 | 245 | +114.2 | +66.8 | 29.8% | +3.58 | -0.86 | 1.78 | 14.6 | 12 | +0.47 | +73.8 | +40.4 | 28.5 | 45.4 | 29.7 | 10.7 | - |
| 21 | **A4 + w24 + ext1.5 (single risk-adjusted best)** | 261 | +257.0g | **+223.1** | 33.0% | — | — | — | 19.8 | — | — | — | — | — | — | — | — | - |
| 22 | **lb14 + w24 + ext1.5 (sleep-well)** | 272 | — | **+193.7** | — | — | — | — | 15.7 | — | — | — | — | — | — | — | — | - |
| 23 | lb30 + w24 + ext1.5 (VALIDATED REBUILD) | 265 | +257.9g | **+185.0** | 32.1% | — | — | — | 19.4 | 9 | — | +118.4 | +113.2 | 25.9 | 92.5 | 54.6 | 58.6 | - |
| — | N6 wage × ext_stop matrix — see [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) for full matrix | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | - |

### Post-Fix Walk-Forward (B3-OPT lb50, expanding window, fine)

| Split | Train NET | Test NET |
|---|---|---|
| 50/50 | +56.9 | **+66.0** |
| 66/34 | +62.7 | **+60.2** |
| 75/25 | +84.1 | **+38.8** |

All test segments positive. Edge is real but modest.

### Post-Fix Walk-Forward (B3-OPT lb14, expanding window, fine)

| Split | Train NET | Test NET |
|---|---|---|
| 50/50 | +37.4 | **+49.4** |
| 66/34 | +40.0 | **+46.8** |
| 75/25 | +62.5 | **+24.2** |

All test segments positive but lower than lb50.

### Key Changes from Pre-Fix

1. **Multi-LTF configs are the real leaders** — their-OPTIMAL (+322.5) and S9 (+312.2) never used B3, so they were unaffected by the fix. They remain the top 2 configs.
2. **S15 (B3+OPTIMAL) collapsed** — from +300.4 to +66.8. B3 + multi-LTF together is dead.
3. **B3 doesn't help anything** — best B3 variant (aggressive +116.1) still loses to anchor lb=30 (+196.3) by 80R.
4. **halt3 > halt6 at lb50** — +115.4 vs +112.5 (opposite of pre-fix)
5. **lb50 still beats lb14** — +35.4R at halt3, +36.5R at halt6 (direction survived)
6. **lb30+ext2.5 is best single-position (N6)** — +231.1R (ext 1.5→2.5, +34.8R). Stock anchor lb=30 +196.3R remains the no-change fallback
7. **Edge is modest** — ~0.5-0.6R/trade across all configs

### New Experiments (2026-09-19)

### Theory primer — how the engine works (plain words, read first)

- **HTF = 1h bias.** Engine simulates 1h swing trades first (flip / B2 / decisive legs, 3R target, SL/3R/16-day cap). Every closed 1h trade becomes a *window* `[entry_ts, exit_ts, dir, entry_price, sl]` = "bias is long/short from here until here".
- **Pipeline in order (what runs when):** (1) build 1h windows from closed 1h trades; (2) compute 1h chop per 15m bar from the last CLOSED 1h candle; (3) chop vs threshold picks the window set for that bar (B2 set vs FLIP set); (4) collect 15m decisive signals (swing mb50, stream); (5) keep a signal only if inside the active window + same dir + ext/wage/nth + cd/halt pass; (6) manage the kept trade on the stock 15m swing trail to SL/target. N5/N6 touch step (5) only — entries live or die, exits never change.
- **Worked example (numbers):** 1h flip prints long at 60000, SL 59000 → risk = 1000, window = [Jan 10 23:30, Jan 12 08:18, long]. A 15m decisive long fires Jan 11 06:00 at 61200. wage = 6.5h (entry − window start). ext = (61200 − 60000)/1000 = 1.2R → passes ext1.5 AND ext2.5. Same signal at 62500 → ext = 2.5R → passes ext2.5, fails ext1.5 (this is the +28-trade pocket N6 harvests). Same signal at Jan 10 23:45 → wage = 15min → fails w24, passes w0 (this is what N5 cut).
- **LTF = 15m entries.** 15m decisive signals (swing mb50) become real trades ONLY if: inside the active HTF window + same direction + ext check + cooldown/halt pass. Exits = 15m swing trail, always.
- **Regime picks the window set.** 1h chop vs threshold: chop > thresh → B2 windows, else FLIP windows (`b2_vs_flip_chop`). Chop = 100·log(TRsum/range)/log(lb): high chop = trendless chop, low chop = trending.
- **Knob glossary:** `lb` = chop lookback in 1h bars (14 twitchy, 30 slow). `mb` = swing min_bars (mb20 default 1h swings, mb10 = more windows). `persistN` = regime must repeat N bars before switching (hysteresis). `mltf` = allow overlapping positions (multi). `cap3` = max 3 concurrent (post-filter, causal). `haltN` = stop entries after N consecutive losses until a winner. `cd`/`cooldown` = 15m bars to skip after any loss. `ext_stop` = skip entry if HTF leg already >X·R in profit (ENTRY gate, not exit — the LTF signal dies, SL/trail never change). `wage` = entry_ts − window_start (window age, entry-knowable). `nth` = 1st/2nd/3rd+ LTF signal inside the same HTF window (entry-knowable counter).
- **Causality (C14/C15):** regime uses the last CLOSED 1h candle only (running candle's chop is future data, up to 45min lookahead — banned). Window start is fixed at its entry-candle close. Both wage and nth are known before the entry bar closes, so they are legal entry gates.
- **Coarse vs fine:** coarse = 15m-bar exits (fast sweep). Fine = 1m-precise fills + Bybit taker 0.055%/side + 0.005/0.010% slip + 0.01%/8h funding. Tables say which. NET = gross − fees − funding.
- **Harness:** patched-shipped-source with identity gate (flags-off must reproduce shipped trade list exactly) — no retyped engine, no lookahead. H1 = 2023+2024 R, H2 = 2025+2026 R.

#### Exp N1: lb30+mltf combo (NEVER TESTED)

**Harness:** never created (experiment was never run — lb30 kills multi-LTF by 58-122R based on exp26 results, so this was marked DEAD without a dedicated script).

**What it is:** take the multi-LTF winner (their-OPTIMAL, lb14 chop base) and swap its regime to slow chop lb30 — the chop lookback that won single-position. Question: does the regime that helps single (fewer flip-flops between B2 vs FLIP window-sets) also help multi?
**How we run it:** same engine, same multi stack (mb10 windows, chop55, persist2, mltf on), only `exp31_lb` 14→30 (+ cd0/cd10 variants). Fine fills, same costs. Compare NET vs lb14 ref.

| Config | NET | DD | vs their-OPTIMAL |
|---|---|---|---|
| their-OPTIMAL (lb14 base) | +322.5 | 23.3 | ref |
| lb30+mltf+chop55+mb10+persist2 | +200.1 | 26.5 | **-122.4R** |
| lb30+mltf+chop55+mb10+persist2+cd10 | +264.2 | 27.5 | -58.3R |
| lb30+mltf+persist5+cd0+chop55+mb10 | +250.0 | 25.2 | -72.5R |

**Verdict: lb30+mltf DEAD.** lb30 kills multi-LTF by 58-122R. lb30 is single-position only.

#### Exp N2: chop veto (from Lane D loss autopsy)

**Harness:** `backtest/tests/exp_n2_chop_veto.py` — identity-gated, fine fills, bucket-split by chop-at-entry on anchor lb14/lb30 + OPTIMAL.

**What it is:** Lane D autopsy on anchor-lb30 showed chop 0-50 = 147t but H1 −3.6R (chop-bleed), vs chop 50-58 = 138t +174.3R (sweet spot). Question: is low-chop all trash we can veto at entry? (chop is entry-knowable from the last closed 1h candle).
**How we run it:** split the trade list by chop-at-entry into buckets (chop<50 only / 50-58 / ≥50) on BOTH anchor and OPTIMAL bases, fine NET each. Adopt only if it wins on both — a veto that helps one base but hurts the other is regime overfit.

| Filter | anchor NET | OPTIMAL NET |
|---|---|---|
| Full (no filter) | +148.0 | +322.5 |
| chop<50 only | -9.8 | +77.5 |
| chop 50-58 sweet | +181.8 | +178.2 |
| chop>=50 only | +157.8 (+9.8R) | +245.0 (-77.5R) |

**Verdict: chop veto REJECTED globally.** Helps anchor (+9.8R) but hurts OPTIMAL (-77.5R). chop<50 is still +77.5R on OPTIMAL — can't cut it.

#### Exp N3: atrpct 60-80 veto (from Lane D)

**Harness:** `backtest/tests/exp_n3_atrpct_veto.py` — identity-gated, fine fills, bucket-split by ATR% percentile on anchor lb14/lb30.

**What it is:** Lane D showed atrpct 60-80 = 68t −11.5R (H1 −27.4R) on anchor-lb30 — the only volatility bucket underwater. Question: does skipping entries when 15m ATR% sits in that percentile band remove losses for free?
**How we run it:** same bucket-split method as N2 (veto band vs full list) on anchor-lb14 production base, fine NET. Note: bucket was measured on the lb30 trade set (349t); lb14 production is a different trade set (351t) with a different ATR distribution, so the veto may catch nothing.

| Filter | anchor NET | OPTIMAL NET |
|---|---|---|
| Full | +148.0 | +322.5 |
| No atrpct 60-80 | +148.0 | +322.5 |

**Verdict: DEAD.** Zero trades filtered on lb14 base (different trade set from lb30). No effect.

#### Exp N4: Concurrency cap (the winner)

**Harness:** `backtest/tests/exp_n4_cap.py` — identity-gated, fine fills, greedy causal post-filter on OPTIMAL trade list, cap {2,3,4,5}.

**What it is:** their-OPTIMAL holds up to 5 concurrent positions (mltf on, cd=0) — flagged unlivable. Question: does capping concurrency to N slots (greedy causal post-filter by entry order: keep a trade only if <N positions open at its entry_ts) cost R, or does it cut bad overlap?
**How we run it:** take the OPTIMAL fine trade list, apply cap {2,3,4,5} post-filters (entry-ordered, exit-aware — no lookahead), recompute fine NET + DD each. cap5 = identity check (max observed concurrency is 5, so cap5 must equal no-cap). Adopt the cap with best NET/DD.

| Cap | NET | DD | NET/DD | Trades |
|---|---|---|---|---|
| No cap | +322.5 | 23.3 | 13.8 | 515 |
| cap2 | +326.7 | 23.5 | 13.9 | 470 |
| **cap3** | **+326.8** | **21.8** | **15.0** | **503** |
| cap4 | +323.8 | 22.7 | 14.2 | 513 |
| cap5 | +322.5 | 23.3 | 13.8 | 515 |

**Concurrent position distribution (no cap):**

| Concurrent | Trades | NET |
|---|---|---|
| 0 | 362t | +224.4 |
| 1 | 108t | +102.3 |
| 2 | 33t | +0.1 |
| 3 | 10t | -3.0 |
| 4 | 2t | -1.2 |

**Verdict: cap3 is the pick.** Removes 2+ concurrent positions (breakeven/worse). Same NET as no cap, -1.5R DD, best NET/DD (15.0). Positions at 2+ concurrent are -4.1R total — cutting them is pure improvement.

#### Exp N5: wage>=24h gate — the experiment WITHOUT the exit rule (SUPERSEDED by N6)

**Harness:** `backtest/tests/exp40c_wage_gate.py` (rebuild — the original was deleted). See [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §10.3 for the non-authoritative old numbers.

**What this experiment is:** N5 is the ENTRY-gate-only run — stock engine, stock exits, one new skip rule (the wage gate). N6 next door is the experiment that CHANGES the exit-side knob (ext_stop) — read N6 for that. Here, nothing about how a live trade is managed changes: same SL, same 15m trail, same target logic.

**Setup (full):** stock v18_streak_halt, ext_stop=1.5 untouched, exits untouched (15m swing trail). The ONLY addition is the wage gate: skip any LTF signal whose window is <24h old (`entry_ts − window_start < 86400s`). Causal: window start is fixed at its entry-candle close, chop uses last CLOSED 1h candle.

**How it runs, step by step (what the code does with the gate on):**
1. 1h legs print → windows exist (e.g. long window Jan 10 23:30 → Jan 12 08:18, entry 60000, risk 1000).
2. Chop at each 15m bar picks the set: chop>thresh → B2 windows, else FLIP windows.
3. 15m decisive signal fires (say Jan 11 06:00 long at 61200).
4. Gate checks in order: inside window? yes → same dir? yes → wage = 6.5h < 24h → SKIP (this signal dies here; nothing is entered, no SL is placed).
5. Same signal on Jan 12 02:00 (wage 26.5h) → passes wage → ext = (61200−60000)/1000 = 1.2 ≤ 1.5 → passes → cd/halt check → ENTER at 15m close, SL = swing pivot − buffer, trail = stock 15m events.
Downgrade path for live: wage needs only two stored timestamps per active window (start_ts, dir) — no extra data feed.

**Theory — what the engine does (v18_streak_halt, no changes to exits):**

- **HTF bias = 1h trade windows.** The engine first simulates 1h swing trades (flip / B2 / decisive legs, rr 3.0, SL/3R/16-day cap). Every closed 1h trade becomes a *window*: `[entry_ts, exit_ts, dir, entry_price, sl]`. A window is a claim: "from this 1h entry until this 1h exit, bias is long (or short)".
- **Regime picks the window set.** At each 15m bar, 1h chop decides: chop > thresh → use B2 windows, else FLIP windows (mode `b2_vs_flip_chop`). lb = chop lookback (lb14 twitchy, lb30 slow). mb = 1h swing min_bars (mb20 default, mb10 = more windows).
- **LTF = 15m decisive entries inside the window.** A 15m decisive signal becomes a trade ONLY if: (a) its bar sits inside the active HTF window, (b) same direction as the window, (c) HTF extension check passes (see N6), (d) cooldown/halt pass. Exits are always the stock 15m swing trail — N5 changes nothing about exits.
- **wage = window age at entry, entry-knowable.** `wage = LTF entry_ts − HTF window_start_ts`. Both timestamps are fixed before the entry bar closes, so the gate is causal (C14/C15: regime from last CLOSED 1h candle, window knowable from its entry candle close). The N5 gate is one line: skip the signal if `wage < 24h`. In plain words: when a fresh 1h leg prints, sit out for one day, then trade its continuation.
- **Why it should work:** a newborn HTF leg is unproven — the first LTF signals pay the discovery cost (false starts, chop reversals). A 3-day-old leg that is still alive has survived; its pullbacks are trend-continuation entries. The autopsy confirmed exactly this shape before we ever gated on it. Trader's version: when a fresh 1h trend prints, everyone front-runs it and the first pullbacks chop; a leg that survives a day has shown it can hold — then you buy its dips instead of its birth.

**Motivation (autopsy v2 on anchor-lb30, 349t — entry-knowable buckets only):**
- Window age (hrs since HTF window start, known at entry): 0-24h 75t -11.9R WR 24% | 24-72h 85t +15.0 | 72-168h 79t +94.1 | 168h+ 83t +116.3. Fresh windows lose, mature windows win.
- nth-in-window: 1st 152t +10.5 | 2nd 71t -5.0 | 3rd+ 99t +207.9 WR 37.4% (both halves green).
- Dead ends from the same autopsy: direction (long +149.5 vs short +111.3 — no edge), tighter trail (giveback-4R+ bucket makes +312R — trail cost IS the edge, Exp22 already rejected), time-stop (bars-held 80+ carries +461R).

**Gate:** skip the LTF entry if its HTF window is <24h old (entry_ts − window_start < 24h). Run at stock ext_stop=1.5 — i.e. WITHOUT any exit-rule change.

| Base | Base NET | +w24 NET (old, NON-AUTHORITATIVE) | +w24 NET (validated rebuild) | Δ (validated) |
|---|---|---|---|---|
| lb30 (349t, +196.3) | +196.3 | ~~275t +224.5~~ | 265t **+185.0** | **−11.3 (w24 HURTS)** |
| lb14 production (351t, +148.0) | +148.0 | ~~281t +201.9~~ | (not re-run) | — |
| A4 (359t, +203.3) | +203.3 | ~~266t +228.6~~ | 261t **+223.1** | **+19.8 (w24 helps)** |

> **⚠️ NON-AUTHORITATIVE:** The old N5 numbers (struck through) came from the
> deleted Exp40/41 harness whose wage-age convention is unrecoverable (13+
> candidates tested, none reproduces these rows). The validated rebuild numbers
> use `(bar_ts-s)/3600.0` (raw window start, no +2700 shift), identity-gated
> against the shipped engine, 1m fills + fee + slip + funding. Coarse matrix
> validated 4/4, fine table validated 4/4. See [method/EXP40C_EXP41_WAGE_EXT.md
> §10.3](method/EXP40C_EXP41_WAGE_EXT.md#103-deleted-harness-n5-rows---non-authoritative-the-honest-version).

**Verdict: w24 is base-dependent, not universal.** On lb30 it HURTS by −11.3R;
on A4 it helps by +19.8R. The 24h wait was a workaround for a too-tight ext
gate, not a universal edge (see N6 — ext2.5 supersedes w24 on lb30).

#### Exp N6: wage × ext_stop matrix (REVISED 2026-09-20 — w24 not dead, see N6/41/42 updates below)

**Harness:** `backtest/tests/exp40c_wage_gate.py` (Phase B/C) + `backtest/tests/exp41_wf_leaders.py` (walk-forward). See [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) for full record.

**What this experiment is (vs N5):** N5 kept every exit-side rule stock and moved ONE entry knob (the wage gate). N6 turns a SECOND entry knob at the same time: `ext_stop_r` — the "don't chase an extended HTF leg" ceiling. Grid = wage {0, 24h} × ext {1.5, 2.0, 2.5, 3.0, OFF} on lb30. Still no exit changes anywhere — trail, SL buffer, 3R HTF windows all stock. The question: do the two knobs cooperate (mature + headroom) or fight (mature = no headroom left)? The verdict picks the winning ENTRY combination.

**Setup (full):** same stock engine as N5, but TWO knobs move together. `ext_stop_r` = entry gate on HTF extension: `ext = (LTF close − HTF entry_price) × dir / HTF risk`; skip signal if `ext > ext_stop_r`. Grid = wage {0, 24h} × ext {1.5, 2.0, 2.5, 3.0, OFF} on lb30. Everything else stock (mb20 windows, chop lb30 vs 58, cd10/halt3, 15m trail exits). Moving right ADDS late-window entries; moving down REMOVES early-window entries.

**How it runs, step by step (same window, different knob settings):**
1. Window prints: long Jan 10 23:30 → Jan 12 08:18, HTF entry 60000, risk 1000.
2. 15m long fires Jan 11 18:00 at 62500: ext = (62500−60000)/1000 = 2.5R. w0-ext1.5 → SKIP (over cap — this winner dies). w0-ext2.5 → ENTER (one of the +28 pocket trades). w24-ext1.5 → SKIP twice (young AND over cap).
3. 15m long fires Jan 12 02:00 at 62300 (wage 26.5h, ext 2.3R): w24-ext2.5 → ENTER — but price already ran a full day to get here; this is the "buying the top" bucket (−52R vs w0-ext2.5).
4. Every kept trade runs the same stock 15m trail — the knobs only vote dead/alive at the signal bar close, never touch management.
Downgrade path for live: ext needs HTF entry_price + risk per active window (already stored); wage needs window start_ts. No new feeds.

**Theory — what ext_stop is and why it fights the wage gate:**

- **ext_stop = "don't chase an extended HTF leg".** For each candidate 15m entry, the engine measures how far the HTF leg has already run: `ext = (LTF close − HTF entry_price) × dir / HTF risk`. If `ext > ext_stop_r`, the entry is skipped (engine line ~188-192). Stock default `ext_stop_r = 1.5`: once the 1h leg is 1.5R in profit, no new same-direction 15m entries until the leg ends and a new window opens. It is an ENTRY gate, not an exit — nothing about SL/trail changes.
- **Why 1.5 existed:** late entries into a mature leg have bad geometry (tight room to the HTF extreme, wide LTF risk) — historically the 1.5-2R extension bucket bled. So the cap protected WR at the cost of trade count.
- **Why it fights w24:** 24h of HTF drift mechanically pushes `ext` toward/above 1.5. The wage gate therefore keeps only the entries the ext cap is most likely to reject — the two knobs select opposite ends of the window (w24 = late, ext1.5 = early-only). One of them must give. The matrix tests which: open ext to {2.0, 2.5, 3.0, OFF} × wage {0, 24h} on lb30.
- **Reading the matrix:** moving right (wider ext) ADDS late entries; moving down (w24) REMOVES early entries. If the late entries are good, right wins. If early entries are trash, down wins. If both, the off-diagonal (w24 + wide ext) wins. The data says: right wins, down loses, off-diagonal is worst (waiting 24h then buying at 2.0-2.5R extension = buying the top).

**Hunch:** 24h of HTF drift pushes price near the 1.5R ext cap, leaving w24 survivors no headroom — the gate and the cap fight each other. Cross wage {0, 24h} × ext {1.5, 2.0, 2.5, 3.0, OFF} on lb30.

**Coarse (gross, lb30):**

| wage | ext1.5 | ext2.0 | ext2.5 | ext3.0 | extOFF |
|---|---|---|---|---|---|
| w0 | 349t +260.8 | 370t +284.1 | 378t +297.0 | 382t +299.3 | 382t +298.4 |
| w24 | 265t +231.6 | 294t +248.2 | 304t +231.7 | 307t +222.4 | 309t +223.1 |

**Fine (NET, funding-inclusive):**

| Config | Trades | NET | DD |
|---|---|---|---|
| w0-ext1.5 (stock) | 349 | +196.3 | 23.6 |
| **w0-ext2.5 (ADOPTED)** | **377** | **+231.1** | **24.6** |
| w24-ext2.0 | 293 | +197.2 | 23.6 |
| w24-ext2.5 | 303 | +179.1 | 23.6 |

**Mechanism:** ext1.5→2.5 admits 28 late entries (+36 gross, fees flat 73.6R — same trades, more headroom). ext3.0 adds nothing (+2 gross coarse) — 2.5 is the ceiling. w24+wide ext is anti-synergistic: waiting 24h then entering at 2.0-2.5R extension = buying the top (w24-ext2.5 loses to w0-ext2.5 by 52R).

**Verdict: KILL w24 on lb30, set ext_stop 1.5→2.5.** New single-best: **lb30+ext2.5 = 377t / +231.1 / DD 24.6** (+34.8 over stock lb30). Validated rebuild confirmed: w24×ext matrix coarse 4/4 + fine 5/5 exact match. w24 + wide ext is anti-synergistic (buying the top). Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md). Open next: ext2.5 on A4 base + OPTIMAL.

#### Exp N6b: ext2.5 on A4 + OPTIMAL (Exp40b — REJECTED on 2 of 3)

**Harness:** `backtest/tests/exp40c_wage_gate.py` Phase B/C (the validated rebuild — identity gate + user coarse matrix 4/4; the table below IS its Phase C output, all 6 cells exact). The original file `exp40b_ext25_a4_opt.py` is STALE — its `main()` predates the current `build_module()` signature and crashes (`build_module(split_mb=True)`); kept for record only, do not run. N6b also adds w24 variants of the same cells (see method/EXP40C_EXP41_WAGE_EXT.md §5).

**Gate audit first (2026-09-19):** before running, audited the ext gate + craze patcher end-to-end for B3-style inflation. Verdict: gate is causal — runs pre-fill on the signal-bar close (= the fill price), HTF pe/psl from closed 1h windows, C15/C14 knowable-instant shifts intact; the 1m fine path only re-times EXITS (`f_start` = bar after entry, cannot move the entry). No bug found. One B3-only nuance flagged: for B3 entries the ext gate evaluates at the signal bar, not the trigger bar (stale by ≤ b3_k bars — past data, not lookahead; B3 is dead anyway). Harness `exp40b_ext25_a4_opt.py`, identity gate PASSED (flags-off == shipped, n=351, exact R-list).

**What this experiment is:** N6 adopted ext2.5 on the lb30 anchor. N6b propagates the SAME single stock kwarg (no patcher code) to the two fine leaders, paired ext1.5-vs-2.5 so deltas are per-config exact.

| Config | ext | Trades | NET | npt | WR | DD | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| A4-lb30chop55mb10p2 | 1.5 | 359 | **+203.3** | +0.566 | 26.2% | **24.8** | +131.3 | +166.0 |
| A4-lb30chop55mb10p2 | 2.5 | 390 | +141.3 | +0.362 | 25.1% | 28.4 | +81.2 | +156.4 |
| OPT-mltf-cd0 | 1.5 | 515 | **+322.5** | +0.626 | 28.0% | **23.3** | +229.4 | +226.7 |
| OPT-mltf-cd0 | 2.5 | 585 | +290.0 | +0.496 | 27.0% | 25.0 | +229.3 | +206.9 |
| OPT-mltf-cd10 | 1.5 | 453 | +259.4 | +0.573 | 28.5% | 32.7 | +156.4 | +216.5 |
| OPT-mltf-cd10 | 2.5 | 512 | **+291.4** | +0.569 | 29.1% | **27.1** | +193.0 | +222.7 |

**Mechanism:** ext2.5 admits ~30-70 late entries everywhere, but on A4 (−62.0) and OPT-cd0 (−32.5) those entries are net-NEGATIVE. Only OPT-cd10 gains (+32.0) AND cuts DD 32.7→27.1 — cd10 already thins re-entries, so its admitted late entries arrive post-cooldown.

**Verdict: REJECT ext2.5 on A4 and OPT-cd0 (keep stock 1.5). ADOPT only on OPT-cd10 (+32.0R, DD −5.6).** N6's lb30-anchor adoption stands (+34.8 there). ext2.5 is config-specific, not a global upgrade — matches N6's own matrix, where ext3.0 already added nothing.

#### Exp 41: segmented walk-forward on the leaders (2026-09-20)

**Harness:** `backtest/tests/exp41_wf_leaders.py` — Phase 1 missing OPT-cd10×ext2.0 cells + Phase 2 six-segment walk-forward (~225d each, configs FIXED, fine NET: 1m fills + fee + slip + funding). Ledger bucketing by entry_ts of the causal full-history sim; no per-fold re-fit. Raw output: `_exp41_out.txt` / `_exp41_results.json`.

| Config | Trades | NET | worst seg | H1/H2 |
|---|---|---|---|---|
| **OPTcd10 w24 e1.5** | 326 | **+337.7** | **+13.6** | +183.0 / +154.6 |
| OPTcd0 w0 e1.5 | 515 | +322.5 | +9.6 | +174.1 / +148.4 |
| OPTcd10 w24 e2.0 | 350 | +329.8 | +9.7 | +168.6 / +161.3 |
| A4 w24 e1.5 | 261 | +223.1 | −1.1 | +46.6 / +176.5 |
| lb30 w0 e2.5 | 377 | +231.1 | **−31.1** | +95.2 / +135.9 |
| lb30 w0 e1.5 (prod base) | 349 | +196.3 | −29.6 | +69.0 / +127.4 |

**Verdict:** only the two OPT leaders have zero losing segments; everything lb30-based bleeds in segment 1 (oldest data). Champion = OPT-cd10 + w24 + ext1.5. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §6.

#### Exp 42: wage-threshold sweep + lb14 recheck (2026-09-20)

**Harness:** `backtest/tests/exp42_wage_sweep.py` — wage ∈ {0,12,18,24,36,48} × lanes {lb30, A4, OPT-cd10, lb14} at ext1.5, fine NET, plus segmented WF on the same ledgers. Gates: identity + user coarse matrix 4/4 + 6 fine pins to exp40c Phase C (aborts on mismatch). Raw output: `_exp42_out.txt` / `_exp42_results.json`.

| wage | lb30 | A4 | OPT-cd10 | lb14 |
|---|---|---|---|---|
| 0h | **+196.3** | +203.3 | +259.4 | +148.0 |
| 12h | +147.6 | **+110.1** | +324.9 | +151.2 |
| 18h | +160.4 | +217.8 | +265.3 | +160.5 |
| 24h | +185.0 | **+223.1** | **+337.7** | **+193.7** (DD 15.7) |
| 36h | +166.7 | +203.3 | +329.4 | +187.7 |
| 48h | +181.6 | +201.9 | +271.0 | +146.3 |

**Verdict:** "kill w24" is lb30-only (argmax 0h there). 24h is argmax on 3/4 lanes but ±70R noisy between neighbors — adopt the **18–36h band**, not the point. DD/npt improve monotonically with wage on every lane. 12h ruled out everywhere except OPT-cd10. lb14-w24 revalidated under the rebuilt gate (272t +193.7 DD 15.7 — the old DD-king lane is real). Robustness picks: OPT-cd10+w36h (+329.4, worst seg +17.3), A4+w36h (+203.3 = w0's NET at DD 16.5, all-positive segs). Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §13.

#### Exp 43: loss autopsy + runner preservation + parent-window diagnostics (2026-09-20)

**Harness:** `backtest/tests/exp43_loss_autopsy.py` — gates: identity + user coarse matrix + 8 fine pins (aborts on mismatch). Decomposes each lane's w24 effect into **removal** vs **chain re-timing**, checks runner amputation (≥3/4/5/10R in the removed bucket), R-by-year of removed trades, and parent-HTF-window inheritance. Raw output: `_exp43_out.txt` / `_exp43_results.json`. Full record: [method/EXP43_method/LOSS_AUTOPSY.md](method/EXP43_method/LOSS_AUTOPSY.md).

Key results (fine NET, all gates passed, RQ1 join canary clean = no bugs):
* **Mechanism corrected:** the w24 gate is a timing intervention, not just a quality filter. Champion OPT-cd10: +78.3 total = **+25.6 removal + 52.7 chain re-timing**. lb30: removal is genuinely good (+35.7, systematic across years) but chain-shift is **−47.0**, flipping the sign — that is the lb30 mystery solved.
* **Runner amputation:** removed young buckets contain real runners (OPT-cd10: 6×≥4R + one ≥10R = 136R amputated; lb30: 5×≥4R = +31.2). The champion still nets +78 because delayed entries recapture runners elsewhere.
* **Cleanest case lb14:** removal negative in all 4 years (−16.3/−14.4/−5.2/−0.9), WR 15.5% removed — most systematic; matches its DD-king status. A4 caveat: +20.7 of its removal gain sits in 2023 alone (cluster flavor).
* **HTF side:** parent-window fate strongly predicts LTF R (won-parent avgR +3.1 vs lost-parent −0.6) but is non-causal; causal age profile is U-curved on lb30 (0–6h fine, 6–24h bad) and rising on OPT-cd10 → next-experiment candidate: a **curfew gate** (skip only 6–24h), tested pre-fill.

#### Exp 44: curfew gate — skip only 6–24h (2026-09-20)

**Harness:** `backtest/tests/exp44_curfew_gate.py` — new knob `exp_curfew_a/b` in the craze patcher (skips only a ≤ age < b; no-op when b=0, identity-gated). Variants w0 / w24 / curf6-24 / curf6-30 × 4 lanes, ext1.5, fine NET + segmented WF. Gates: identity + user coarse matrix + 8 fine pins + curfew canary (0 in-band violations). Raw output: `_exp44_out.txt` / `_exp44_results.json`. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §14.

| variant | lb30 | A4 | lb14 | OPT-cd10 |
|---|---|---|---|---|
| w0 | +196.3 | +203.3 | +148.0 | +259.4 |
| w24 | +185.0 | **+223.1** | **+193.7** | **+337.7** |
| curf6-24 | **+217.4** | +198.8 | +188.7 | +302.6 |
| curf6-30 | +163.9 | +202.4 (DD 16.1) | +160.9 | +273.9 |

**Verdict:** the curfew wins **only on lb30** (+217.4 = +21.1 over w0, +32.3 over w24) — exactly where exp43's U-curve predicted; new best lb30-based single without touching ext (DD caveat: 26.8 vs 23.6). On A4/lb14/OPT-cd10 plain w24 stays best — **overall champion unchanged** (OPT-cd10 + w24 + ext1.5 = +337.7 / DD 19.2). Band edge: curf6-30 worse everywhere → 24h is the right lower edge; A4 curf6-30 (+202.4, DD 16.1, worst seg +3.9) ties A4-w36h as a robust alternative.

#### Exp 45: curfew edge-plateau map + curf×ext combo (2026-09-20)

**Harness:** `backtest/tests/exp45_curfew_plateau.py` — lb30 edge grid (lower {4,6,8} × upper {24,30,36}), the curf6-24×ext2.5 combo cell, A4 edge checks, + segmented WF. Gates: identity + user coarse matrix + 6 fine pins + canaries (0 violations). Raw output: `_exp45_out.txt` / `_exp45_results.json`. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §15.

| lb30 (ext1.5) | skip→24 | skip→30 | skip→36 |
|---|---|---|---|
| skip from 4 | +172.0 | — | — |
| skip from 6 | **+217.4** | +163.9 | +161.9 |
| skip from 8 | **+219.4** | — | — |

**Verdict:** lower edge has a small plateau (6–8h, +217–219); upper edge is pinned at 24h by mechanism (the ≥24h bucket is where the good trades live — widening costs ~−54R), same structure as the ext ceiling. **Combo killed:** lb30 curf6-24 + ext2.5 = +215.0 < ext2.5 alone (+231.1) — the two lb30 edges don't stack (both act via entry re-timing, per exp43). A4: c4-24 bad (+166.9, seg3 −41.4); w24 stays A4 king (+223.1); c6-30 confirmed as A4 robustness alt. Single board unchanged: A4+w24 balanced king, lb30+ext2.5 raw king, lb30+c6-24 third.

#### Exp 46: deferred entry — requeue young signals (2026-09-20)

**Harness:** `backtest/tests/exp46_defer_entry.py` — new knob `exp_defer_h` in the craze patcher: a too-young signal is requeued to the first 15m bar at/after `s + horizon` provided the SAME window is still open, the original SL pivot was never touched meanwhile, and ext still passes at the defer bar (all causal, known at entry time). `filtered` re-sorted by final bar (causal ledger; no-op when off). Variants w0/w24/defer{6,12,24} × 3 lanes, ext1.5, fine NET + WF. Gates: identity + user coarse matrix + 6 fine pins + defer canary (0 age<horizon violations). Raw output: `_exp46_out.txt` / `_exp46_results.json`. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §16.

| variant | lb30 | A4 | lb14 |
|---|---|---|---|
| w0 | +196.3 | +203.3 | +148.0 |
| w24 | +185.0 | **+223.1** | **+193.7** |
| defer6 | +183.8 | +209.0 (worst seg **+7.7**) | +151.7 |
| defer12 | +198.6 | +206.5 | +145.9 |
| **defer24** | **+203.1** (DD 21.6) | +183.1 | +181.6 |

**Verdict:** **defer24 beats w24 by +18.1R on lb30** (+203.1 vs +185.0) at the same horizon — "wait a day, enter if the setup is still alive" > "drop everything young", directly confirming exp43's mechanism finding (the gate's value is timing, not removal). lb30 timing ranking: curf6-24 (+217.4) > defer24 (+203.1) > w0 > w24. A4: w24 stays king; A4-d6 (+209.0, worst seg +7.7) is the best worst-segment of any A4 variant. lb14: w24 stays king. Champion (multi) unchanged (+337.7).

#### Exp 47: full stats board + per-year NET (2026-09-20)

**Harness:** `backtest/tests/exp47_yearly_stats.py` — gross/net/avgR/DD/WR + calendar-year NET (2023–26) + delta vs anchor for 9 configs (all singles on the board + multi champion reference). Gates: identity + matrix + 5 fine pins. Raw output: `_exp47_out.txt` / `_exp47_results.json`. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §17.

Key per-year finding: **lb30 family is 2024-dependent** (anchor 43% of NET from 2024; ext2.5 +146.3 in 2024), **A4/lb14 families are balanced** (A4-w24's best year is 2026 +126.2; lb14-w24 min year +40.1), and the **multi champion is balanced AND big** (min year +79.7). Confirms: entry-timing fixes don't change regime dependence.

#### Exp 48: price-space autopsy + leg-progress gate (2026-09-20)

**Harness:** `backtest/tests/exp48_leg_progress.py` (v2) — the "relative to price" family: leg anchor = first window of the current same-dir streak; progress = (close − anchor)·d ÷ window risk. Phase A autopsy (progress/pullback buckets), Phase B legskip gate {4,6,8,10,12} on lb30+A4, Phase C WF. Gates: identity + matrix + 4 fine pins + canaries. Raw output: `_exp48_out.txt` / `_exp48_results.json`. Full record: [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md) §18.

**Verdict:** **legskip REJECTED on both lanes** (lb30 −102.7R vs w0; A4 −124.6R): legs are BIMODAL in price-space — either fighting (prog < −1R, avgR +0.75/+1.20, still profitable) or ran ≥20R (avgR +0.92/+0.39) — with an EMPTY middle, so every threshold removes exactly the profitable ride bucket. In a trend-following system, late legs ARE the edge. New structural fact + follow-up candidate: A4 pullback gate (skip entries 1.5–3R off the leg extreme, avgR −0.54, n=24 — needs pre-fill + WF discipline first). Process note: v1 harness had a nested-loop bug (documented in §18.3).

### Honest Assessment

The B3 entry price bug inflated all B3 results by ~3-4x. Multi-LTF configs were unaffected (no B3).

**FINAL ANSWER (both lanes signed):**
- **OPT-cd10 + w24 + ext1.5 = +337.7R / DD 19.2** — overall champion (multi-position, needs concurrency cap; see row 1)
- their-OPTIMAL + cap3 = +326.8R / DD 21.8 — second-best multi-position
- their-OPTIMAL alone = +322.5R / DD 23.3

**Update 2026-09-20 (post N5/N6b validation — see method/EXP40C_EXP41_WAGE_EXT.md §11/§13):** these rankings predate the wage-gate validation. Current champion: **OPT-cd10 + w24(wage≥24h) + ext1.5 = +337.7 / DD 19.2**, zero losing WF segments; robustness alternate OPT-cd10 + w36h = +329.4 / DD 18.4. The lb30+ext2.5 "+231.1 single-best" line below is now third-tier.

**Multi-position leaders (need concurrency design before live):**
- **their-OPTIMAL + cap3**: +326.8R over 3.7y = +88R/year, ~0.65R/trade, DD 21.8R, cd0, multi, max 3 concurrent
- **S9 (mltf+mb10+chop55)**: +312.2R over 3.7y = +84R/year, ~0.68R/trade, DD 38.2R, multi

**Single-position leaders (production-ready):**
- **Anchor lb=30 + ext2.5 (N6, NEW single-best)**: +231.1R over 3.7y = +62R/year, DD 24.6R
- **Anchor lb=30 (stock fallback)**: +196.3R over 3.7y = +53R/year, ~0.56R/trade, DD 23.6R
- **B3-OPT lb50 halt3**: +115.4R over 3.7y = +31R/year, ~0.54R/trade, DD 10.2R
- **Aggressive (52,60,tr65)**: +116.1R over 3.7y = +31R/year, ~0.49R/trade, DD 13.9R

**What died:** B3+multi-LTF (S15 collapsed from +300 to +67). B3 doesn't help any config. lb30+mltf (-122R). chop veto. atrpct veto. ~~wage>=24h gate~~ (N5 — status REVISED 2026-09-20: not dead globally; base-dependent — champion lane OPT-cd10+w24 = +337.7, but it HURTS on lb30-ext1.5 and the 12h threshold is poison everywhere except OPT-cd10; see method/EXP40C_EXP41_WAGE_EXT.md §13).

### Multi-LTF Caveats

- **Concurrency**: their-OPTIMAL holds up to 4 concurrent positions without cap; cap3 limits to 3. R-DD understates real dollar risk during overlaps.
- **cd=0**: their-OPTIMAL has no loss cooldown — needs live-latency validation.
- **Not single-position**: Cannot run with the same simplicity as anchor/B3-OPT.
- **Cap3 recommended**: +4.3R over no cap, -1.5R DD. Pure improvement.

---

## 13. LA Experiments — Single Position, Corrected Costs (2026-09-20)

> All harnesses in `backtest/tests/`. Single position only. Costs include split exit fees for partial trades.

### Champion: ATR_HIGH + partR=7.5 + ext=3.0 + cd=8

**Harness:** `exp_final_single.py`

> **⚠️ LEGACY NUMBERS (pre-fix):** These results used the old partial R formula
> (booked 7.5R for 50% leg) and old trail-event ordering. Current corrected
> numbers: champion_single_sw20 = +90.1R NET (372t), champion_single_sw10 =
> +82.0R NET (396t). See `run_experiment.py --all` for authoritative numbers.

```
Config:  mode=atr_high, ext_stop_r=3.0, cooldown_bars=8, exp_partial_r=7.5
Trades:  371 | Gross: +352.4R | Costs: -90.9R | NET: +261.5R  [LEGACY]
WR: 28.8% | Avg win: +5.58R | Avg loss: -0.93R | PF: 2.44
Max DD: 29.3R | Max loss streak: 14 | Monsters (>10R): 27
```

| Year | Trades | NET | WR | PF | Avg Entry |
|---|---|---|---|---|---|
| 2023 | 86 | +32.5R | 24.4% | 1.53 | $28,024 |
| 2024 | 119 | +87.5R | 22.7% | 2.03 | $64,816 |
| 2025 | 95 | +133.6R | 34.7% | 3.35 | $102,491 |
| 2026 | 71 | +98.8R | 36.6% | 3.37 | $70,784 |

### Progression

| Config | NET | Delta | File |
|---|---|---|---|
| Shipped baseline | +166.7R | — | (engine default) |
| + partR=5.0 | +230.7R | +64.0R | exp_la5_partial.py |
| + atr_high mode | +208.3R | -22.4R | exp_la8_modes.py |
| + partR=7.5 + ext=3.0 + cd=8 | **+261.5R** | **+94.8R** | exp_final_single.py |

### Experiment Table

| # | Experiment | Verdict | Delta | File |
|---|---|---|---|---|
| LA4 | Trail tightening | REJECTED | -112.6R | exp_la4_trail_tighten.py |
| LA5 | Partial exits (50% at X R) | ACCEPTED | +64.0R | exp_la5_partial.py |
| LA6 | Post-loss 1R recovery | REJECTED | -153R | exp_la6_recover.py |
| LA7 | Entry distance gate | REJECTED | -6.2R | exp_la7_entry_dist.py |
| LA8 | Mode variations | MIXED | +10.2R/+38.6R | exp_la8_modes.py |
| LA9 | ATR trail + delay | REJECTED | -257R | exp_la9_atr_trail.py |
| LA10 | Partial x Mode combos | ACCEPTED | +123.5R opt | exp_la10_combos.py |
| LA11 | Extensions sweep | ACCEPTED | wage rejected | exp_la11_extensions.py |
| LA12 | Ultra-optimize | ACCEPTED | +55.4R/+26.0R | exp_la12_ultra.py |
| LA13 | Validation + overfit | ACCEPTED | partR=7.5 opt | exp_la13_validate.py |
| FINAL | Corrected costs | ACCEPTED | +261.5R NET | exp_final_single.py |
| LA14 | Deferred entry (requeue) | REJECTED | -28.0R defer24 | exp_la14_defer.py |

### Price-Level / Regime Analysis (from exp_final_single.py)

- Pearson r (price vs R) = 0.108 (weak)
- <30k: -3.6R (68t, 17.6% WR, PF 0.93) — choppy regime, not price
- >100k: +103.6R (58t, 43.1% WR, PF 4.57)
- Regime matters more: 2023-Q2 choppy (-7.8R) vs 2023-Q4 trending (+38.6R, PF 3.90)
- All years profitable. No price-level edge to exploit.
- w24 has ZERO effect on atr_high (identical to w0). Atr_high is self-cleaning.
- Deferred entry (requeue) hurts on atr_high (-28.0R). No timing gate needed.

### Combined Comparison Matrix (Both Lanes, Consistent Costs)

Source: `exp_final_matrix.py`. All configs: v18 engine, 0.055% fee/side + 0.005%/0.010% slip + 0.01%/8h funding.

> **⚠️ LEGACY (pre trail-fix):** These numbers used old trail-event ordering.
> Post trail-fix: champion_single = +90.1R, champion_multi = +208.4R.
> No-partial multi sw10 = +325.8R (actual king). Run `--all` for current.

**Single Position:**

| Config | Trades | NET R | Cost | Win Rate | Profit Factor | Max Drawdown | Max Loss Streak | 2023 | 2024 | 2025 | 2026 | H1 | H2 | Big Wins |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Shipped baseline | 340 | +166.7R | 84.9R | 30.0% | 2.15 | 27.1R | 16 | +28R | +72R | +60R | +90R | +101R | +151R | 10 |
| **Our champion (atr_high+p7.5+ext3+cd8)** | 371 | **+104.0R** | 90.9R | 28.8% | 2.44 | 33.7R | 14 | +32R | +88R | +134R | +99R | +120R | **+232R** | **27** |
| Their A4 w24 ext1.5 | 341 | +159.2R | 86.7R | 28.7% | 2.09 | 20.3R | 14 | +43R | +63R | +59R | +80R | +106R | +140R | 10 |
| **Their A4 w24 ext1.5 + partR=7.5** | 341 | **+245.4R** | 86.6R | 28.7% | 2.47 | **16.0R** | 14 | +61R | +68R | +113R | +91R | +129R | +204R | 26 |
| Their lb30 ext2.5 | 364 | +174.3R | 86.8R | 30.8% | 2.11 | 27.7R | 12 | +22R | +85R | +71R | +83R | +107R | +154R | 12 |

**Multi Position:**

| Config | Trades | NET R | Cost | Win Rate | Profit Factor | Max Drawdown | Max Loss Streak | 2023 | 2024 | 2025 | 2026 | H1 | H2 | Big Wins |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OPT-cd10 w24 ext1.5 (theirs) | 408 | +215.7R | 101.9R | 30.9% | 2.22 | 24.2R | 15 | +63R | +78R | +96R | +81R | +140R | +177R | 12 |
| **Our atr_high+p7.5+ext3+cd8+mltf+persist7** | 487 | **+232.6R** | 114.9R | 31.8% | **2.92** | 29.4R | 14 | **+128R** | **+140R** | **+186R** | **+127R** | **+267R** | **+313R** | **42** |

**Cooldown-Family Experiments (2026-09-20, see signal/ANCHOR_BASIS_AUDIT.md §7):**

| Config | Trades | NET R | DD | NET/DD | Verdict |
|---|---|---|---|---|---|
| **swingpause_single_sw10** | **357** | **+174.8R** | **23.4** | **7.5** | **NEW best single (+37R, −5.8DD vs baseline)** |
| swingpause_cd0_single_sw10 | 357 | +174.7R | 23.4 | 7.5 | cd=0 ≡ cd=8 (pause replaces timer) |
| swingpause_single_sw20 | 338 | +120.0R | 34.1 | 3.5 | ~neutral on sw20 |
| swingpause_multi_sw10 | 443 | +231.0R | 19.8 | 11.7 | hurts the king (−94.8R) |
| skipwinhalt_multi_sw10 | 323 | +102.6R | 20.1 | 5.1 | DEAD |
| skipwinhalt_single_sw10 | 276 | +71.8R | 27.0 | 2.7 | DEAD |
| skipwin1_multi_sw10 | 144 | −1.1R | 38.8 | — | DEAD |
| skipwin2_multi_sw10 | 105 | −26.1R | 34.2 | — | DEAD |
| skipwin1_single_sw10 | 138 | −4.3R | 40.0 | — | DEAD |
| skip1pause_multi_sw10 | 144 | −1.1R | 38.8 | — | DEAD |

### Recommendation

**UPDATE (2026-09-20):** Three fixes applied: (1) partial R formula corrected, (2) trail-event ordering fixed (ratchet before SL check), (3) cooldown-family research complete. All numbers below are POST-FIX.

**Two kings (final corrected):**
- **KING (multi): champion_multi_sw10** = +325.8R / DD 17.8 / NET/DD 18.3 — multi (cap 4-5 positions), no partials, sw10
- **KING (single): swingpause_single_sw10** = +174.8R / DD 23.4 / NET/DD 7.5 — single position, structural swing-pause after loss (replaces bar-cooldown timer)

**Cooldown-family research (see signal/ANCHOR_BASIS_AUDIT.md §7):**
- HTF window skip after losses = DEAD in every variant
- Swing-pause ("no re-entry until a swing formed AFTER the loss confirms") = new best single
- cd=0 + pause ≡ cd=8 + pause (174.7 vs 174.8 — pause fully replaces timer)
- Do NOT add swing-pause to the multi king (overlapping runners need those entries; −94.8R)

**Other strong configs:**
- opt_ml_cd0_mb10 = +296.7R / DD 23.3 (old "OPTIMAL", single)
- lb30_w24_ext2.0 = +171.3R / DD 23.6 (best single without pause)
- baseline_no_partial_sw10 = +137.7R / DD 29.2 (old baseline)

**Key insight:** partial exits hurt ALL configs. Partials are dead weight.
