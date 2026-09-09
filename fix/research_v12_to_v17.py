# BTC HTF-LTF Strategy Research: v12 to v17

**Date:** 2026-09-08  
**Author:** Pravin  
**Status:** v12+cd20 FROZEN BASELINE | v16, v17 REJECTED

---

## Executive Summary

After extensive research across 6 strategy versions (v12-v17), the **v12+cd20** configuration remains the best performing strategy. Two proposed filters (entry distance, ATR) were tested and rejected — they remove the runner trades that generate the strategy's edge.

| Version | Filter | Trades | Net R | Status |
|---|---|---|---|---|
| **v12+cd20** | None (baseline) | 414 | +265.30 | **FROZEN BASELINE** |
| v13+cd30 | Cooldown 30 bars | ~400 | ~+250 | Not better |
| v15 | Recover 1R mode | ~410 | ~260 | Not better |
| v16 | Entry distance <=30% | 347 | +230.46 | REJECTED |
| v17 | ATR<0.5% | 389 | +261.94 | REJECTED |

---

## v12+cd20 — Frozen Baseline

### Configuration
- **Engine:** `simulate_htf_ltf_conditional` (v11 engine + cooldown)
- **Cooldown:** 20 bars after a loss
- **Mode:** `b2_vs_flip_chop` (B2 when chop>61.8, else Flip)
- **SL buffer:** 0.25 ATR
- **Ext stop R:** 1.5

### Performance
| Metric | Value |
|---|---|
| Trades | 414 |
| Net R | +265.30 |
| Avg R/trade | +0.641 |
| Win rate | ~35% |
| Max drawdown | ~21R |

### Per-Year Breakdown
| Year | Trades | Net R | Avg R |
|---|---|---|---|
| 2023 | 106 | +24.4 | +0.230 |
| 2024 | 129 | +70.3 | +0.545 |
| 2025 | 105 | +111.2 | +1.059 |
| 2026 | 74 | +59.4 | +0.803 |

**All 4 years positive.** 2023 (chop) weakest but still +24R.

---

## 8-Test Robustness Panel

### 1. Entry Distance into Swing
| Bucket | Trades | Avg R | Net |
|---|---|---|---|
| 0-30% | 268 | +0.823 | +220.55 |
| 30-50% | 27 | +0.641 | +17.31 |
| 50-70% | 29 | +0.278 | +8.08 |
| 70-100% | 90 | +0.215 | +19.37 |

83% of net comes from first 30% of swing. But this is descriptive, not predictive.

### 2. Runner Durability (cap winners)
| Cap | Net |
|---|---|
| 3R | **−28.36** |
| 5R | +48.71 |
| 10R | +155.02 |
| 15R | +195.17 |
| ∞ | +265.30 |

**The edge IS the runners.** Cap at 3R → disaster. Tail-dependent strategy.

### 3. Trim-the-Top Robustness
| Trim | Net |
|---|---|
| 0 | +265.30 |
| 1 | +235.96 |
| 5 | +129.93 |
| 10 | +55.63 |

Even without top 10 trades, still +55R. Edge is concentrated but not fragile.

### 4. Volatility at Entry
| Vol | Trades | Net |
|---|---|---|
| Low | 157 | +176.73 |
| Med | 137 | +65.42 |
| High | 120 | +23.15 |

### 5. Bootstrap Confidence
- **95% CI: [+113R, +432R]**
- Mean: +264R
- Note: Trades may not be IID. Not proof of significance.

### 6. Shuffle-Order MC
- Actual DD: 21.01R at 46th percentile
- **Sequencing is neutral**
