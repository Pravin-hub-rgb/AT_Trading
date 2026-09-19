# All Combined Experiment Trade Metrics (v31)

**Every viable config from BOTH lanes, run on the SHIPPED engine (identity-gated), production params (chop=58, cd=10, halt=3, sl_buf=0.01, ext_stop=1.5, mode b2_vs_flip_chop), FINE 1m fills, 2023-01 -> 2026-09 (3.7y). COST MODEL (v2, both-lane-agreed): NET = Gross - (fee+entry slip+exit slip) - FUNDING (0.01%/8h on notional, hold-time weighted, leverage-adjusted; notional/risk = entry/SL-distance). CONVENTION: WR, AvgWin/Loss, Payoff, PF, MaxDD, per-year on RAW trade R (gross); NET its own column. Matches the other lane's corrected harness to the decimal on all halt6/anchor variants. Generated 2026-09-19. Source: tests/exp29_final_metrics.py.

## Main table (sorted by NET)

| Config | Trades | Tr/yr | Gross R | Fees | Funding | **NET R** | NET/trd | WR%% | AvgWin | AvgLoss | Payoff | PF | MaxDD | DD dur (trd/days) | MaxConsecL | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | 515 | 140 | +456.2 | 108.2 | 25.5 | **+322.5** | +0.626 | 28.0 | +5.55 | -0.92 | 6.00 | 2.33 | 23.3 | 57 / 153 | 19 | 28.3 |
| mltf+mb1h10+chop55 (S9) | 460 | 125 | +432.1 | 96.5 | 23.4 | **+312.2** | +0.679 | 28.7 | +5.55 | -0.91 | 6.07 | 2.44 | 38.2 | 53 / 196 | 17 | 28.7 |
| multi-LTF+persist5 | 409 | 111 | +389.1 | 81.9 | 19.8 | **+287.5** | +0.703 | 32.0 | +4.93 | -0.92 | 5.34 | 2.52 | 33.4 | 58 / 247 | 11 | 30.6 |
| OPTIMAL+halt6 (S19) | 574 | 156 | +423.1 | 122.0 | 27.5 | **+273.7** | +0.477 | 26.8 | +5.26 | -0.92 | 5.71 | 2.09 | 31.5 | 63 / 131 | 18 | 27.8 |
| multi-LTF alone | 421 | 114 | +306.5 | 89.5 | 19.4 | **+197.6** | +0.469 | 29.5 | +4.67 | -0.92 | 5.08 | 2.12 | 23.4 | 27 / 119 | 27 | 27.6 |
| v18 anchor (production) | 351 | 95 | +238.0 | 74.4 | 15.7 | **+148.0** | +0.422 | 27.6 | +4.86 | -0.92 | 5.29 | 2.02 | 23.4 | 27 / 119 | 27 | 26.6 |
| (52,60,trail65) aggressive (post-fix) | 229 | 62 | +192.7 | 34.3 | 12.2 | **+146.1** | +0.638 | 32.8 | +4.38 | -0.88 | 4.97 | 2.42 | 13.9 | 17 / 71 | 15 | 41.3 |
| B3-OPT lb50 halt6 cd10 (post-fix) | 226 | 61 | +157.0 | 34.1 | 10.4 | **+112.5** | +0.498 | 33.6 | +3.77 | -0.86 | 4.36 | 2.21 | 12.2 | 15 / 71 | 10 | 34.5 |
| B3 k4 h3 lb14 p0 (post-fix best B3) | 202 | 55 | +151.0 | 32.7 | 9.3 | **+109.1** | +0.540 | 34.7 | +3.79 | -0.87 | 4.37 | 2.32 | 9.4 | 10 / 69 | 10 | 33.3 |
| B3+halt6 combo (post-fix) | 213 | 58 | +114.9 | 32.8 | 8.9 | **+73.2** | +0.343 | 37.6 | +2.91 | -0.89 | 3.28 | 1.97 | 20.6 | 29 / 247 | 19 | 33.8 |
| B3 k8-close (post-fix) | 206 | 56 | +99.6 | 31.8 | 8.3 | **+59.6** | +0.289 | 36.4 | +2.88 | -0.89 | 3.24 | 1.85 | 19.6 | 28 / 247 | 19 | 33.1 |
| S16 B3+mltf+persist5 (post-fix) | 200 | 55 | +94.1 | 30.2 | 8.1 | **+55.9** | +0.279 | 37.0 | +2.77 | -0.88 | 3.14 | 1.85 | 26.6 | 32 / 266 | 12 | 33.6 |

## Per-year R + halves (strict both-halves rule, raw R)

| Config | 2023 | 2024 | 2025 | 2026 (9mo) | H1 | H2 | both>0? |
|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | +94.4 | +135.0 | +84.4 | +142.3 | +229.4 | +226.7 | PASS |
| mltf+mb1h10+chop55 (S9) | +81.6 | +168.0 | +71.3 | +111.2 | +249.6 | +182.5 | PASS |
| multi-LTF+persist5 | +92.6 | +110.1 | +90.8 | +95.6 | +202.8 | +186.3 | PASS |
| OPTIMAL+halt6 (S19) | +95.2 | +115.9 | +77.2 | +134.8 | +211.1 | +212.0 | PASS |
| multi-LTF alone | +91.1 | +80.5 | +67.3 | +67.5 | +171.6 | +134.9 | PASS |
| v18 anchor (production) | +38.8 | +81.1 | +37.6 | +80.5 | +119.9 | +118.1 | PASS |
| (52,60,trail65) aggressive (post-fix) | +60.8 | +66.4 | +31.0 | +34.5 | +127.2 | +65.5 | PASS |
| B3-OPT lb50 halt6 cd10 (post-fix) | +33.7 | +48.0 | +35.8 | +39.5 | +81.7 | +75.3 | PASS |
| B3 k4 h3 lb14 p0 (post-fix best B3) | +30.7 | +54.3 | +32.6 | +33.4 | +85.0 | +66.0 | PASS |
| B3+halt6 combo (post-fix) | +15.9 | +35.5 | +36.1 | +27.4 | +51.4 | +63.5 | PASS |
| B3 k8-close (post-fix) | +16.9 | +31.1 | +25.8 | +25.8 | +48.0 | +51.6 | PASS |
| S16 B3+mltf+persist5 (post-fix) | +3.5 | +36.0 | +28.5 | +26.2 | +39.4 | +54.7 | PASS |

## Notes & caveats

- All configs share the same engine, data, and cost model; differences are config only.
- multi-LTF configs (mltf, S9, their-OPTIMAL, OPTIMAL+halt6) can hold concurrent positions (max 5 observed; 80-88% of time <=1) -- needs concurrency design before live.
- cd0 configs (their-OPTIMAL, OPTIMAL+halt6, B3-OPT cd0) remove the loss cooldown -- cd=0 latency/re-entry behavior needs live validation (their lane's own caveat).
- B3-OPT cd10 and B3-OPT+halt6 cd10 are fully production-parameter single-position configs (no concurrency, no cd0).
- their-OPTIMAL fine gross (+456.2R) vs coarse (+429.8R): fine fills HELP this engine (Exp 28 Q3 reconciliation, 515/515 matched).
- halt4 cliff on OPTIMAL (Exp 28 Q5): single-halt sensitivity exists; halt=3 is the shipped default.
- NOT yet done: true re-optimizing walk-forward (fixed-config 3-cut stability passed for OPTIMAL/B3-OPT); cd=0 live latency validation; concurrency-cap variants (cap 2/3).
- Decisions DEFERRED until experiment list exhausted (user process).
