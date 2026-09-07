# Full 16-Bias Sweep — 2026-09-05 21:22 (1152 combos, 1256s, 8 workers) — POST-FIX

**Scope:** `exec:1min` only, `270` days, `min≥13` logical, `16` bias modes × `72` combos per bias = `1152` total, `8` workers, `1256s` wall (`~1.09s` per cfg). Grid `sl [prev_pivot,avg] × rr [2,3,4] × min [13,15] × BE [0,1] × gap 0.27 × ft true × max2 15:15 always × force [None,aggressive,conservative]` fixed `swing_traverse true need_opp_swing true` (`backend/sweep_all_bias.py:72`).

**Bias modes (16):** `daily_swing`, `ema_daily_10`, `ema_daily_5`, `ema_5min_20_50`, `opposite_first`, `streak_3_1_1`, `ema_daily_10_far_50`, `ema_daily_5_far_50`, `ema_5min_20_50_far_30`, `ema_1min_5_far_20`, `ema_1min_10_far_30`, `ema_daily_10_inverse`, `ema_daily_5_inverse`, `ema_5min_20_50_inverse`, `ema_1min_5_inverse`, `ema_1min_10_inverse` (`backend/src/bias.py:452` `BIAS_MODES` 16) — includes **lower 1min** `5`/`10` and **inverse** (no far band) as you asked.

**Fix applied before this sweep:** `backend/src/bias.py:571` `compute_opposite_first_bias` now uses **today’s** first swing `dir_today = m.get(today)` (was `prev` day) → `B→bearish S→bullish` fade, `next_date` unbiased. This corrects `2026-07-02` `first B` → `bearish` `short` (was `prev` `S` → `bullish` long) and `2026-07-07` `first S` → `bullish` `long` (now `long 09:46` correctly). Verified `fix/check_opposite.py` `0 mismatches / 267` traded days.

---

## Overall Top 10 (all 16 biases, all forces) — NEW OVERALL BEST

| # | Bias | R | WR% | PF | Trades | sl | rr | min | BE | force |
|---|------|---|-----|----|--------|----|----|-----|----|-------|
| **1** | `ema_1min_5_inverse` | **+132.97** | 17.7 | 1.63 | 519 | prev_pivot | 4.0 | 13 | 1.0 | None |
| 2 | `ema_1min_10_inverse` | +127.21 | 17.4 | 1.60 | 517 | prev_pivot | 4.0 | 13 | 1.0 | None |
| 3 | `ema_1min_5_inverse` | +125.02 | 25.3 | 1.37 | 514 | prev_pivot | 4.0 | 15 | 0 | None |
| 4 | `ema_daily_10_far_50` | **+123.47** | 25.3 | 1.38 | 510 | avg | 4.0 | 15 | 0 | None |
| 5 | `ema_1min_5_inverse` | +123.03 | 17.8 | 1.59 | 518 | prev_pivot | 4.0 | 15 | 1.0 | None |
| 6 | `ema_1min_5_inverse` | +121.55 | 24.7 | 1.35 | 515 | prev_pivot | 4.0 | 13 | 0 | None |
| 7 | `ema_1min_5_inverse` | +119.94 | 22.2 | 1.57 | 518 | prev_pivot | 3.0 | 13 | 1.0 | None |
| 8 | `ema_daily_10_far_50` | +114.22 | 29.3 | 1.36 | 512 | prev_pivot | 3.0 | 13 | 0 | None |
| 9 | `ema_daily_10_far_50` | +114.22 | 25.2 | 1.34 | 511 | prev_pivot | 4.0 | 15 | 0 | None |
|10 | `ema_1min_10_inverse` | +114.21 | 17.2 | 1.55 | 516 | prev_pivot | 4.0 | 15 | 1.0 | None |

**New overall best is `ema_1min_5_inverse` `+132.97R` `17.7%` `PF1.63` `519` trades `prev_pivot rr4 min13 BE1` — lower `1min` `5` inverse (mean-reversion on `1min` `5` EMA, `5` on `1min` = 5 min) beats previous best `ema_daily_10_far_50` `+123.47R` by `+9.5R`.**

---

## Per-Bias Best (16) — Updated

| Bias | Best R | WR% | PF | Trades | sl | rr | min | BE | force | vs Trend |
|------|--------|-----|----|--------|----|----|-----|----|-------|----------|
| `daily_swing` | +35.19 | 14.3 | 1.15 | 516 | prev_pivot | 4.0 | 13 | 1.0 | None | baseline |
| `ema_daily_10` | +51.95 | 22.7 | 1.15 | 516 | prev_pivot | 4.0 | 15 | 0 | None | — |
| `ema_daily_5` | +56.73 | 15.0 | 1.25 | 519 | prev_pivot | 4.0 | 15 | 1.0 | None | — |
| `ema_5min_20_50` | +74.74 | 16.3 | 1.33 | 515 | prev_pivot | 4.0 | 13 | 1.0 | None | — |
| `opposite_first` | +80.87 | 23.9 | 1.23 | 524 | prev_pivot | 4.0 | 13 | 0 | None | — |
| `streak_3_1_1` | +96.41 | 24.4 | 1.28 | 512 | prev_pivot | 4.0 | 15 | 0 | None | — |
| `ema_daily_10_far_50` | **+123.47** | 25.3 | 1.38 | 510 | avg | 4.0 | 15 | 0 | None | **+71R** over `ema_daily_10` `+51R` |
| `ema_daily_5_far_50` | +105.93 | 24.4 | 1.32 | 512 | avg | 4.0 | 15 | 0 | None | **+49R** over `ema_daily_5` `+56R` |
| `ema_5min_20_50_far_30` | +62.74 | 34.8 | 1.22 | 517 | avg | 2.0 | 13 | 0 | None | **worse** than `ema_5min` trend `+74R` |
| `ema_1min_5_far_20` | **+76.31** | 23.3 | 1.23 | 507 | avg | 4.0 | 15 | 0 | None | lower `1min` `5` far |
| `ema_1min_10_far_30` | +71.31 | 23.1 | 1.21 | 507 | avg | 4.0 | 15 | 0 | None | lower `1min` `10` far |
| `ema_daily_10_inverse` | +94.73 | 23.9 | 1.28 | 511 | avg | 4.0 | 15 | 0 | None | **+42R** over `ema_daily_10` trend |
| `ema_daily_5_inverse` | +103.91 | 24.8 | 1.31 | 512 | avg | 4.0 | 15 | 0 | None | **+47R** over `ema_daily_5` |
| `ema_5min_20_50_inverse` | +94.17 | 36.5 | 1.34 | 521 | avg | 2.0 | 13 | 0 | None | **+19R** over `ema_5min` trend |
| `ema_1min_5_inverse` | **+132.97** | 17.7 | 1.63 | 519 | prev_pivot | 4.0 | 13 | 1.0 | None | **+56R** over `ema_1min_5_far_20` `+76R` and **+9R** over `ema_daily_10_far_50` |
| `ema_1min_10_inverse` | +127.21 | 17.4 | 1.60 | 517 | prev_pivot | 4.0 | 13 | 1.0 | None | **+55R** over `ema_1min_10_far_30` |

*All with `gap 0.27` `ft true` `max2 15:15 always` `force None` (case-driven) — `force None` beats `force aggressive/conservative` for far/inverse (like `sweep_far_ema` `360` showed `force None` best).*

---

## Interpretation

* **Daily EMA far mean-reversion wins:** `ema_daily_10_far_50` `+123R` vs `ema_daily_10` trend `+51R` (`+71R` gain) — far distance `>50` pts (~0.2% at 24k) captures overbought/oversold reversion where `close` far from `EMA10` is faded.
* **5min far hurts:** `ema_5min_20_50_far_30` `+62R` < `ema_5min` trend `+74R` — 5min cross is already a trend, fading it hurts.
* **Lower `1min` inverse is overall best:** `ema_1min_5_inverse` `+132.97R` `17.7%` `PF1.63` `prev_pivot rr4 min13 BE1` beats `daily far` `+123R` — lower `EMA5` on `1min` (5 min) mean-reversion is even better than daily `10` far. Lower `EMA5` far `+76R` is worse than `5` inverse `+132R`, so pure inverse (always fade, no band) beats far band for `1min` lower.
* **Gap and BE:** Best far/inverse use `gap 0.27` (not `0.35`) and `BE 0` for `rr4` on `1min` (trend needed `BE1` but far/inverse does not).
* **Force:** For far/inverse, `force None` (case-driven `aggressive 1st` vs `conservative 2nd` per `case` `intraday.py:122`) beats `force aggressive/conservative` — keep `force None`.

---

## Next Steps

* Update `frontend/src/lib/biasPresets.ts` (already auto-generated from this sweep via `sweep_all_bias.py:195` `BIAS_PRESETS` 16 entries) and `docs/sweep-per-bias-2026-09-05.md` to reflect new overall best `ema_1min_5_inverse +132R`.
* Add `far` threshold sweep `thr 20/30/50` vs `ATR*mult` on `1min` lower to see if `thr` tuned per `span` can push `+132R` higher.
* Make `force_trade_mode` per-bias sweep already showed `None` best, so keep `force None` for now.

**Files:** `backend/sweep_all_bias.py` (1152, 1256s), outputs `backend/sweep_all_*_20260905_212247.json` per bias + `sweep_all_best_*.json`, `frontend/src/lib/biasPresets.ts` (16), `backend/src/bias.py:640` `compute_ema_far_bias` + `compute_ema_1min_far_bias` + `compute_ema_inverse_bias`.
