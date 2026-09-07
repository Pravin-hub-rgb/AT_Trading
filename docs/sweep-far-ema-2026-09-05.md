# Far-from-EMA + Force Trade Mode Sweep — 2026-09-05 14:29

**Scope:** `exec:1min` only, `270` days, `min≥13` logical, `5` bias modes × `72` combos per bias = `360` total, `8` workers, `370s` wall. Grid `sl [avg,prev_pivot] × rr [2,3,4] × min [13,15] × BE [0,1] × gap 0.27 × ft true × max2 15:15 always × force [None,aggressive,conservative]` fixed `swing_traverse true need_opp true` (`backend/sweep_far_ema.py:1`).

**Bias modes tested:**
- `ema_daily_10_far_50` — daily EMA10, thr 50 pts, inverse (far above → short, far below → long) `backend/src/bias.py:640` `compute_ema_far_bias` `span10 thr50`
- `ema_daily_5_far_50` — daily EMA5, thr 50
- `ema_5min_20_50_far_30` — 5min EMA20>50 cross, thr 30 pts `compute_ema_5min_far_bias` `fast20 slow50 thr30`
- `ema_daily_10` (trend, no far, baseline)
- `ema_5min_20_50` (trend, no far, baseline)

---

## Results

### Overall Top 10 (all biases, all forces)

| # | Bias | R | WR% | PF | Trades | sl | rr | min | BE | force |
|---|------|---|-----|----|--------|----|----|-----|----|-------|
| 1 | `ema_daily_10_far_50` | **+123.47** | 25.3 | 1.38 | 510 | avg | 4.0 | 15 | 0 | None |
| 2 | `ema_daily_10_far_50` | +114.22 | 29.3 | 1.36 | 512 | prev_pivot | 3.0 | 13 | 0 | None |
| 3 | `ema_daily_10_far_50` | +114.22 | 25.2 | 1.34 | 511 | prev_pivot | 4.0 | 15 | 0 | None |
| 4 | `ema_daily_10_far_50` | +109.97 | 25.0 | 1.32 | 511 | prev_pivot | 4.0 | 13 | 0 | None |
| 5 | `ema_daily_10_far_50` | +106.22 | 24.3 | 1.32 | 510 | avg | 4.0 | 13 | 0 | None |
| 6 | `ema_daily_5_far_50` | +105.93 | 24.4 | 1.32 | 512 | avg | 4.0 | 15 | 0 | None |
| 7 | `ema_daily_10_far_50` | +105.58 | 37.5 | 1.39 | 514 | avg | 2.0 | 13 | 0 | None |
| 8 | `ema_daily_10_far_50` | +105.58 | 37.5 | 1.39 | 514 | avg | 2.0 | 13 | 0 | None |
| 9 | `ema_daily_10_far_50` | +101.19 | 28.5 | 1.32 | 512 | avg | 3.0 | 13 | 0 | None |
|10 | `ema_daily_5_far_50` | +100.93 | 28.5 | 1.31 | 515 | prev_pivot | 3.0 | 13 | 0 | None |

**Far beats trend:** `ema_daily_10_far_50` `+123R` vs `ema_daily_10` trend `+51R` (`docs/sweep-per-bias-2026-09-05.md:1` `+51R`) and `ema_5min_20_50` trend `+74R` — **mean-reversion far is 2.4× better than trend** for daily EMA10.

### Per-bias best

| Bias | Best R | WR | PF | Trades | sl | rr | min | BE | force | vs Trend |
|------|--------|----|----|--------|----|----|-----|----|-------|----------|
| `ema_daily_10_far_50` | **+123.47** | 25.3 | 1.38 | 510 | avg | 4.0 | 15 | 0 | None | **+71R** over `ema_daily_10` `+51R` |
| `ema_daily_5_far_50` | **+105.93** | 24.4 | 1.32 | 512 | avg | 4.0 | 15 | 0 | None | **+49R** over `ema_daily_5` `+56R` (but `+56R` was prev best with different min) |
| `ema_5min_20_50_far_30` | **+62.74** | 34.8 | 1.22 | 517 | avg | 2.0 | 13 | 0 | None | **worse** than `ema_5min_20_50` trend `+74R` — far hurts 5min cross |
| `ema_daily_10` (trend, no far) | +51.95 | 22.7 | 1.15 | 516 | prev_pivot | 4.0 | 15 | 0 | None | baseline |
| `ema_5min_20_50` (trend) | +74.74 | 16.3 | 1.33 | 515 | prev_pivot | 4.0 | 13 | 1.0 | None | baseline |

*`force` comparison for far: `None` (case-driven) beats `aggressive` and `conservative` for all far biases — `force None` is best, `force aggressive` gave `+42R` for `ema_daily_10` trend but not for far. So keep `force None` (case-split) for far.*

### Lower EMA

* `ema_daily_5_far_50` `+105R` vs `ema_daily_10_far_50` `+123R` — **higher period (10) better than lower (5)** for far on daily. Lower is noisier, more trades but lower PF.
* `5min` lower `EMA5` not tested here, but `ema_5min_20_50_far_30` with `thr30` is already lower threshold (30 vs 50) and is worse than `thr50` for daily.

---

## Interpretation

* **Daily EMA far mean-reversion works:** `+123R` with `avg sl` `rr4` `min15` is best overall, beating previous `streak +96R` and `opposite +80R` and `ema_5min trend +74R`. Far distance `>50 pts` (~0.2% at 24k) captures overbought/oversold reversion where `close` far from `EMA10` is faded.
* **5min far does NOT work:** `ema_5min_20_50_far_30` `+62R` < `ema_5min trend +74R` — 5min cross is already a trend, fading it hurts.
* **Force trade mode:** For far, `force None` (case-driven) beats `force aggressive/conservative` — the `B1/B5` case logic is still needed even when far, don't force all to one mode.
* **Gap and BE:** Best far uses `gap 0.27` (not 0.35) and `BE 0` (no breakeven) for `rr4` — trend needed `BE1` but far does not.

---

## Next Steps

* Test lower EMA for 1min: `ema_1min_5` and `ema_1min_10` with `thr 20/30` on `1min` data (not daily/5min) — your “more lower ema like for 5min or 1min” idea.
* Test `thr` as `%` (`0.3%` ≈72 pts) or `ATR*mult` (`ATR14 *0.8/1.0`) instead of fixed pts `30/50`, to adapt to volatility (like `volatilityforge` ATR idea).
* Add `far` to `MASTER BIAS` dropdown (`frontend/src/lib/api.ts:359` `BIAS_MODES` already has `ema_daily_10_far_50` etc., `frontend/src/lib/biasPresets.ts` will be updated with these best).

**Files:** `backend/src/bias.py:640` `compute_ema_far_bias`, `backend/sweep_far_ema.py` (360, 370s), outputs `backend/sweep_far_*_20260905_142944.json` per bias + `sweep_far_best_*.json`, `frontend/src/lib/biasPresets.ts` (to be updated with far best).
