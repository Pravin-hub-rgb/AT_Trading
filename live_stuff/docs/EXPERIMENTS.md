# Experiments — v19+ Branch

**Branch:** `experiments/v19-plus`
**Base:** v18 (C14+C15 causal) — 351t / +238.0R / WR 27.6% / PF 2.02
**Data:** BTCUSDT Bybit Perp, 2023-01 to 2026-09
**Params:** sl_buf=0.01, chop=58.0, cd=10, halt=3, ext_stop=1.5

> **Full results doc:** [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md)

---

## Experiment Summary

| # | Name | Trades | Gross R | WR | PF | Delta | MaxDD | Verdict |
|---|------|--------|---------|----|----|-------|-------|---------|
| 0 | **BASELINE** | **351** | **+238.0** | **27.6%** | **2.02** | **-** | **23.4R** | - |
| 1 | Dual-Active Windows | 520 | +274.7 | 28.3% | 1.80 | +36.7R | 32.7R | Reject (PF drop, DD increase) |
| 2 | Regime Persistence=5 | 339 | +261.3 | 28.9% | 2.17 | +23.3R | 31.2R | Good (stable, WF validated) |
| 3 | Adaptive Halt | 367 | +237.3 | 27.2% | 1.97 | -0.7R | 27.4R | Reject |
| 4 | TOD Filter 00-04 | 317 | +210.3 | 26.8% | 1.97 | -27.7R | 21.1R | Reject |
| 5 | Multi-LTF cd=0 | 471 | +310.8 | 28.9% | 2.00 | +72.8R | 24.1R | Strong (but cd=0 aggressive) |
| 5b | Multi-LTF cd=5 | 359 | +254.2 | 28.1% | 2.07 | +16.2R | 23.4R | Good (conservative option) |
| 6 | Partial Exit 50%@1.5R | 346 | +132.8 | - | - | -105.2R | - | Reject (kills big winners) |
| 7 | Pullback MA=10/20/30 | - | - | - | - | -115R to -162R | - | Reject |
| 8 | min_bars 1h=10 | 369 | +196.4 | 25.7% | 1.78 | -41.6R | 36.1R | Reject alone (needs chop) |
| 8b | min_bars 1h=10 + chop=55 | 377 | +273.8 | 27.6% | 2.11 | +35.8R | 34.2R | Good (WF validated) |
| 9 | persist=2 on mb1h=10+chop55 | 368 | +267.3 | 25.0% | 2.07 | +29.3R | 30.0R | Good (stable) |

---

## Combined Configs

| Config | Trades | R | WR | PF | Delta | MaxDD |
|---|---|---|---|---|---|---|
| SAFE: mb1h=10, chop=55, persist=2, cd=10, sl=0.01 | 368 | +267.3 | 25.0% | 2.07 | +29.3R | 30.0R |
| MIDDLE: mb1h=10, chop=55, persist=2, cd=5, sl=0.01 | 376 | +244.4 | 26.1% | 1.96 | +6.4R | 28.6R |
| **OPTIMAL: mb1h=10, chop=55, persist=2, cd=0, sl=0.01** | **515** | **+456.2** | **28.0%** | **2.33** | **+218.2R** | **23.3R** |
| MAX R: mb1h=10, chop=55, persist=2, cd=0, sl=0.001 | 515 | +460.8 | 28.0% | 2.34 | +222.8R | 23.3R |

---

## Walk-Forward: Rolling 4-Quarter OOS

### BASELINE

| Quarter | Period | Trades | R | WR | MaxDD |
|---|---|---|---|---|---|
| Q1 | 2023-01 to 2023-12 | 79 | +30.6 | 20.3% | 23.4R |
| Q2 | 2023-12 to 2024-11 | 105 | +45.2 | 24.8% | 14.3R |
| Q3 | 2024-11 to 2025-10 | 84 | +49.6 | 27.4% | 12.2R |
| Q4 | 2025-10 to 2026-09 | 84 | +108.4 | 39.3% | 7.5R |
| **TOTAL** | | **352** | **+233.8** | | |

### OPTIMAL (cd=0, sl=0.01)

| Quarter | Period | Trades | R | WR | MaxDD |
|---|---|---|---|---|---|
| Q1 | 2023-01 to 2023-12 | 110 | +74.3 | 25.5% | 20.4R |
| Q2 | 2023-12 to 2024-11 | 145 | +106.7 | 22.1% | 14.7R |
| Q3 | 2024-11 to 2025-10 | 135 | +84.0 | 28.1% | 23.3R |
| Q4 | 2025-10 to 2026-09 | 128 | +174.1 | 36.7% | 14.0R |
| **TOTAL** | | **518** | **+439.1** | | |

All 4 quarters positive for both configs. OPTIMAL beats BASELINE in every quarter.

---

## Bootstrap 95% Confidence Intervals

| Config | Observed | CI Low | CI High | Width |
|---|---|---|---|---|
| BASELINE | +238.0R | +75.2 | +420.8 | 345.6R |
| OPTIMAL cd=0 | +456.2R | +221.0 | +717.6 | 496.6R |

Both CIs entirely above 0. OPTIMAL floor (221R) is 3x BASELINE floor (75R).

---

## Confirmed NOT Worth Pursuing

- **Dual-active windows**: +36.7R but PF drops from 2.02 to 1.80, MaxDD spikes to 32.7R
- **Adaptive halt**: -0.7R, increases max loss streak to 31
- **TOD filter**: -27.7R, removes winning trades from filtered hours
- **Partial exit**: -105.2R, truncates the big winners that drive the system
- **Pullback entry**: -115R to -162R, kills valid entries
- **mb1h=10 alone**: -41.6R, needs chop=55 to work

## Open Questions

- cd=0 edge in live with real fees/slippage
- ETH/other pair performance
- Bear market robustness of mb_1h=10
