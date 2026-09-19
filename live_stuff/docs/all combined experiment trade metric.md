# All Combined Experiment Trade Metrics (v31)

**Every viable config from BOTH lanes, run on the SHIPPED engine (identity-gated), production params (chop=58, cd=10, halt=3, sl_buf=0.01, ext_stop=1.5, mode b2_vs_flip_chop), FINE 1m fills, 2023-01 -> 2026-09 (3.7y). NET = gross - modeled costs (fee+entry slip+exit slip from production route), distributed uniformly per trade for per-trade/per-year/DD metrics. DD on net equity. Generated 2026-09-19. Source: tests/exp29_final_metrics.py.

## Main table (sorted by NET)

| Config | Trades | Tr/yr | Gross R | **NET R** | NET/trd | Gross/trd | WR% | AvgWin | AvgLoss | Payoff | PF | MaxDD(net) | DD dur (trd/days) | MaxConsecL | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | 515 | 140 | +456.2 | **+348.0** | +0.676 | +0.886 | 24.9 | +6.02 | -1.09 | 5.51 | 1.82 | 35.8 | 86 / 225 | 19 | 28.3 |
| mltf+mb1h10+chop55 (S9) | 460 | 125 | +432.1 | **+335.6** | +0.730 | +0.939 | 25.7 | +5.98 | -1.08 | 5.52 | 1.91 | 49.4 | 53 / 196 | 17 | 28.7 |
| B3-OPT+halt6 cd10 | 250 | 68 | +391.5 | **+335.5** | +1.342 | +1.566 | 30.8 | +6.74 | -1.06 | 6.36 | 2.83 | 19.9 | 32 / 138 | 11 | 32.3 |
| B3-OPT cd0 (no mltf) | 243 | 66 | +360.9 | **+307.2** | +1.264 | +1.485 | 31.3 | +6.37 | -1.06 | 6.02 | 2.74 | 17.4 | 30 / 138 | 10 | 32.6 |
| multi-LTF+persist5 | 409 | 111 | +389.1 | **+307.2** | +0.751 | +0.951 | 29.3 | +5.17 | -1.08 | 4.77 | 1.98 | 45.0 | 58 / 247 | 11 | 30.6 |
| B3-OPT cd10 (prod cooldown) | 239 | 65 | +357.9 | **+306.6** | +1.283 | +1.498 | 31.4 | +6.38 | -1.05 | 6.08 | 2.78 | 17.2 | 30 / 138 | 10 | 32.5 |
| OPTIMAL+halt6 (S19) | 574 | 156 | +423.1 | **+301.1** | +0.525 | +0.737 | 23.7 | +5.73 | -1.09 | 5.25 | 1.63 | 44.8 | 63 / 131 | 18 | 27.8 |
| B3+halt6 combo | 216 | 59 | +325.2 | **+278.1** | +1.288 | +1.506 | 37.0 | +5.29 | -1.07 | 4.96 | 2.92 | 23.4 | 31 / 247 | 16 | 33.8 |
| B3 k8-close | 207 | 56 | +303.7 | **+258.3** | +1.248 | +1.467 | 36.2 | +5.33 | -1.07 | 4.98 | 2.83 | 19.7 | 28 / 245 | 15 | 33.3 |
| multi-LTF alone | 421 | 114 | +306.5 | **+217.0** | +0.515 | +0.728 | 27.3 | +4.82 | -1.10 | 4.37 | 1.64 | 32.8 | 63 / 247 | 27 | 27.6 |
| v18 anchor (production) | 351 | 95 | +238.0 | **+163.7** | +0.466 | +0.678 | 25.6 | +5.02 | -1.10 | 4.55 | 1.57 | 29.6 | 34 / 157 | 27 | 26.6 |

## Per-year NET + halves (strict both-halves rule)

| Config | 2023 | 2024 | 2025 | 2026 (9mo) | H1 | H2 | both>0? |
|---|---|---|---|---|---|---|---|
| their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10) | +69.4 | +102.7 | +52.5 | +123.4 | +172.1 | +175.9 | PASS |
| mltf+mb1h10+chop55 (S9) | +59.8 | +138.4 | +44.2 | +93.2 | +198.2 | +137.4 | PASS |
| B3-OPT+halt6 cd10 | +78.9 | +131.1 | +50.5 | +75.0 | +210.0 | +125.5 | PASS |
| B3-OPT cd0 (no mltf) | +83.4 | +135.5 | +51.8 | +36.6 | +218.9 | +88.3 | PASS |
| multi-LTF+persist5 | +73.0 | +84.3 | +70.7 | +79.2 | +157.3 | +149.9 | PASS |
| B3-OPT cd10 (prod cooldown) | +79.7 | +135.8 | +53.4 | +37.7 | +215.5 | +91.1 | PASS |
| OPTIMAL+halt6 (S19) | +66.9 | +79.3 | +41.9 | +113.0 | +146.3 | +154.9 | PASS |
| B3+halt6 combo | +51.2 | +108.8 | +69.0 | +49.0 | +160.0 | +118.1 | PASS |
| B3 k8-close | +54.9 | +100.8 | +56.3 | +46.4 | +155.6 | +102.7 | PASS |
| multi-LTF alone | +69.8 | +54.6 | +42.9 | +49.7 | +124.4 | +92.5 | PASS |
| v18 anchor (production) | +20.8 | +57.8 | +17.7 | +67.4 | +78.6 | +85.1 | PASS |

## Notes & caveats

- All configs share the same engine, data, and cost model; differences are config only.
- multi-LTF configs (mltf, S9, their-OPTIMAL, OPTIMAL+halt6) can hold concurrent positions (max 5 observed; 80-88% of time <=1) -- needs concurrency design before live.
- cd0 configs (their-OPTIMAL, OPTIMAL+halt6, B3-OPT cd0) remove the loss cooldown -- cd=0 latency/re-entry behavior needs live validation (their lane's own caveat).
- B3-OPT cd10 and B3-OPT+halt6 cd10 are fully production-parameter single-position configs (no concurrency, no cd0).
- their-OPTIMAL fine gross (+456.2R) vs coarse (+429.8R): fine fills HELP this engine (Exp 28 Q3 reconciliation, 515/515 matched).
- halt4 cliff on OPTIMAL (Exp 28 Q5): single-halt sensitivity exists; halt=3 is the shipped default.
- NOT yet done: true re-optimizing walk-forward (fixed-config 3-cut stability passed for OPTIMAL/B3-OPT); cd=0 live latency validation; concurrency-cap variants (cap 2/3).
- Decisions DEFERRED until experiment list exhausted (user process).
