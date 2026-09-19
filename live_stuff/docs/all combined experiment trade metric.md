# All Combined Experiment Trade Metrics (v31)

**Every viable config from BOTH lanes, run on the SHIPPED engine (identity-gated), production params (chop=58, cd=10, halt=3, sl_buf=0.01, ext_stop=1.5, mode b2_vs_flip_chop), FINE 1m fills, 2023-01 -> 2026-09 (3.7y). CONVENTION (same as every session readout): WR, AvgWin/AvgLoss, Payoff, PF, MaxDD, per-year are all computed on RAW trade R (gross), no cost adjustment. NET = Gross - Costs (production fee+entry slip+exit slip), its own column. Generated 2026-09-19. Source: tests/exp29_final_metrics.py.

## Main table (sorted by NET)

| Config | Trades | Tr/yr | Gross R | Costs | **NET R** | NET/trd | WR% | AvgWin | AvgLoss | Payoff | PF | MaxDD | DD dur (trd/days) | MaxConsecL | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | 515 | 140 | +456.2 | 108.2 | **+348.0** | +0.676 | 28.0 | +5.55 | -0.92 | 6.00 | 2.33 | 23.3 | 57 / 153 | 19 | 28.3 |
| mltf+mb1h10+chop55 (S9) | 460 | 125 | +432.1 | 96.5 | **+335.6** | +0.730 | 28.7 | +5.55 | -0.91 | 6.07 | 2.44 | 38.2 | 53 / 196 | 17 | 28.7 |
| B3-OPT+halt6 cd10 | 250 | 68 | +391.5 | 56.1 | **+335.5** | +1.342 | 34.4 | +6.24 | -0.89 | 7.05 | 3.70 | 14.0 | 25 / 113 | 11 | 32.3 |
| B3-OPT cd0 (no mltf) | 243 | 66 | +360.9 | 53.6 | **+307.2** | +1.264 | 35.0 | +5.90 | -0.89 | 6.63 | 3.56 | 12.0 | 23 / 113 | 9 | 32.6 |
| multi-LTF+persist5 | 409 | 111 | +389.1 | 81.9 | **+307.2** | +0.751 | 32.0 | +4.93 | -0.92 | 5.34 | 2.52 | 33.4 | 58 / 247 | 11 | 30.6 |
| B3-OPT cd10 (prod cooldown) | 239 | 65 | +357.9 | 51.4 | **+306.6** | +1.283 | 35.1 | +5.90 | -0.89 | 6.64 | 3.60 | 12.0 | 23 / 113 | 9 | 32.5 |
| OPTIMAL+halt6 (S19) | 574 | 156 | +423.1 | 122.0 | **+301.1** | +0.525 | 26.8 | +5.26 | -0.92 | 5.71 | 2.09 | 31.5 | 63 / 131 | 18 | 27.8 |
| B3+halt6 combo | 216 | 59 | +325.2 | 47.1 | **+278.1** | +1.288 | 39.8 | +5.13 | -0.89 | 5.75 | 3.81 | 17.5 | 21 / 196 | 16 | 33.8 |
| B3 k8-close | 207 | 56 | +303.7 | 45.4 | **+258.3** | +1.248 | 39.1 | +5.14 | -0.90 | 5.74 | 3.69 | 15.5 | 19 / 194 | 15 | 33.3 |
| B3+mltf+persist5 (S16, WR champion) | 202 | 55 | +299.7 | 43.3 | **+256.5** | +1.270 | 40.1 | +5.05 | -0.90 | 5.60 | 3.75 | 24.8 | 33 / 266 | 12 | 33.8 |
| multi-LTF alone | 421 | 114 | +306.5 | 89.5 | **+217.0** | +0.515 | 29.5 | +4.67 | -0.92 | 5.08 | 2.12 | 23.4 | 27 / 119 | 27 | 27.6 |
| v18 anchor (production) | 351 | 95 | +238.0 | 74.4 | **+163.7** | +0.466 | 27.6 | +4.86 | -0.92 | 5.29 | 2.02 | 23.4 | 27 / 119 | 27 | 26.6 |

## Per-year R + halves (strict both-halves rule, raw R)

| Config | 2023 | 2024 | 2025 | 2026 (9mo) | H1 | H2 | both>0? |
|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | +94.4 | +135.0 | +84.4 | +142.3 | +229.4 | +226.7 | PASS |
| mltf+mb1h10+chop55 (S9) | +81.6 | +168.0 | +71.3 | +111.2 | +249.6 | +182.5 | PASS |
| B3-OPT+halt6 cd10 | +91.0 | +147.3 | +67.1 | +86.2 | +238.2 | +153.3 | PASS |
| B3-OPT cd0 (no mltf) | +95.4 | +150.2 | +67.7 | +47.6 | +245.6 | +115.3 | PASS |
| multi-LTF+persist5 | +92.6 | +110.1 | +90.8 | +95.6 | +202.8 | +186.3 | PASS |
| B3-OPT cd10 (prod cooldown) | +90.9 | +150.2 | +68.7 | +48.2 | +241.1 | +116.9 | PASS |
| OPTIMAL+halt6 (S19) | +95.2 | +115.9 | +77.2 | +134.8 | +211.1 | +212.0 | PASS |
| B3+halt6 combo | +61.7 | +121.4 | +83.0 | +59.1 | +183.1 | +142.1 | PASS |
| B3 k8-close | +64.7 | +112.8 | +69.9 | +56.3 | +177.5 | +126.1 | PASS |
| B3+mltf+persist5 (S16, WR champion) | +45.3 | +127.7 | +70.1 | +56.7 | +173.0 | +126.7 | PASS |
| multi-LTF alone | +91.1 | +80.5 | +67.3 | +67.5 | +171.6 | +134.9 | PASS |
| v18 anchor (production) | +38.8 | +81.1 | +37.6 | +80.5 | +119.9 | +118.1 | PASS |

## Notes & caveats

- All configs share the same engine, data, and cost model; differences are config only.
- multi-LTF configs (mltf, S9, their-OPTIMAL, OPTIMAL+halt6) can hold concurrent positions (max 5 observed; 80-88% of time <=1) -- needs concurrency design before live.
- cd0 configs (their-OPTIMAL, OPTIMAL+halt6, B3-OPT cd0) remove the loss cooldown -- cd=0 latency/re-entry behavior needs live validation (their lane's own caveat).
- B3-OPT cd10 and B3-OPT+halt6 cd10 are fully production-parameter single-position configs (no concurrency, no cd0).
- their-OPTIMAL fine gross (+456.2R) vs coarse (+429.8R): fine fills HELP this engine (Exp 28 Q3 reconciliation, 515/515 matched).
- halt4 cliff on OPTIMAL (Exp 28 Q5): single-halt sensitivity exists; halt=3 is the shipped default.
- NOT yet done: true re-optimizing walk-forward (fixed-config 3-cut stability passed for OPTIMAL/B3-OPT); cd=0 live latency validation; concurrency-cap variants (cap 2/3).
- Decisions DEFERRED until experiment list exhausted (user process).
