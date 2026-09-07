# Research — Does Flip Candle Strength Matter? Why Trade Fails vs 3R?

> **Data:** `1h Flip cap16` `151tr` `39.7% win` `+57.8 net` `PF0.78` `v1` + `15m Decisive 446tr` `21.7% +5.4 net` `PF1.30` honest `stream+touchable+one-swing-one-trade+1m` `0.05%+2pt` `FULL Jan-25→Sep-26`.
> **Method:** For each trade, entry candle body/ATR, wick/ATR, swing leg (pts), bars, angle/ATR vs R. `research_flip_strength.py:1`.

---

## 1h Flip cap16 (151 trades)

- **Wins 60 vs Losses 91:** `body/ATR 1.11 vs 0.96`, `wick/ATR 0.59 vs 0.55`, `angle/ATR 0.69 vs 0.76`, `leg 4806 vs 2774 pts`, `bars 21.9 vs 13.6`
- **3R trades (54) vs -1R (87):** `body 1.12 vs 0.97`, `wick 0.60 vs 0.54`, `angle 0.73 vs 0.75` — almost same
- **Corr body vs R: 0.10**, `angle vs R: -0.03` — **no correlation**
- **Example strong flip that failed:** `3.36 body/ATR` `2025-12-26 07:30 FLIP` `R -1.0` with `3.36` body, `5.74` body `2026-01-19` `R +3.0` — both extremes can win or lose
- **Weak flip that won:** `0.03 body/ATR` `2025-11-21 22:30 FLIP` `R +3.0` with tiny `0.03` body

**Takeaway:** Flip candle strength (body size) doesn't predict R. Weak flips can give 3R, strong flips can fail.

---

## 15m Decisive (446 trades)

- **Wins 97 vs Losses 349:** `body/ATR 0.78 vs 0.73`, `wick 0.45 vs 0.42`, `angle 0.30 vs 0.39`, `leg 2827 vs 2016 pts`, `bars 42.2 vs 29.5`
- **3R (37) vs -1R (309):** `body 0.64 vs 0.69`, `wick 0.39 vs 0.42`, `angle 0.35 vs 0.41` — even closer
- **Corr body vs R: -0.00**, `angle vs R: -0.01` — **zero correlation**
- **Smallest body `0.00` `2025-07-07 04:30 FLIP` `R -1.0` vs `0.01` `2025-08-23 11:00 FLIP` `R +7.06` — `0.01` body gave `+7R`**

**Takeaway:** Same — no correlation. Leg size matters a bit: wins have larger legs `2827 vs 2016` `+40%`, `1h` `4806 vs 2774` `+73%`. Larger legs give more room to 3R.

---

## Why Trade Fails vs 3R — What Actually Leads?

**Not flip strength, not wick, not angle.** What does lead:

1. **Leg size (swing length):** Wins have `+40%` (`15m`) to `+73%` (`1h`) larger legs. Bigger leg = more distance to target, but also more room before SL? Actually larger leg means SL farther (risk larger) but target even farther (3R). Larger legs correlate with wins, but correlation angle/ATR is near 0, so not strong.

2. **HTF context:** `1h Flip` wins more when HTF trend is with trade? Not tested here, but `v6 ADX` `15m` gave `+90.5` vs `+5.4` by filtering `ADX>25` — chop vs trend matters more than candle strength. `1h` `15m` `HTF-LTF 204tr +127` vs `446tr +5` shows HTF window filters `60%` trades but `win% 22→30` and `PF 1.30→2.25`.

3. **Session:** `15m` `16-20 UTC 100tr +131` `avg 1.31` vs `04-08 UTC 62tr -24` `sweep_E2_E5_E8_E9.py:1` — `US/EU overlap` wins, `Asia` loses.

4. **Hold time:** `15m` wins `42.2 bars` vs losses `29.5 bars` — winners hold longer `+43%`. `1h` wins `21.9` vs `13.6` `+61%`. Longer hold correlates with win, but that's tautology (winners need time to reach 3R).

**Failing trade where flip was good:** `2025-12-26 07:30 FLIP body 3.36/ATR` `R -1.0` — body `3.36` is top 2% strongest, still failed. `2025-07-07 04:30 FLIP body 0.00` `R -1.0` — weakest also failed. So strength not predictive.

**3R trades:** `2025-11-21 22:30 FLIP body 0.03` `R +3.0` — weakest body gave 3R. `2026-01-19 04:30 FLIP body 5.74` `R +3.0` — strongest gave 3R. Both can give 3R.

---

## All Stats to Do Research

From `trade_stats` `btc_engine.py:537` we now log:
- `trades/closed/open, wins/losses, win_rate, total_r, avg_r, avg_win_r, avg_loss_r, profit_factor, payoff, expectancy`
- `max_drawdown_r, max_drawdown_duration_trades, max_drawdown_start/end`
- `max_consecutive_losses, max_consecutive_wins`
- `avg_bars_held, max_bars_held, longs/shorts, outcomes, equity`

For `1h cap16` `101→151tr`: `PF 1.78→0.78`, `maxConLoss 9L`, `maxConWin 6W`, `maxDD 10.0R` `DDdur 14 trades`, `avgHold 55.6 bars` `maxHold 384 bars` `16d`, `win 39.7%`. For `15m` `446tr`: `PF1.30`, `maxConLoss 22L`, `maxConWin 4W`, `maxDD40.3` `DDdur154` `avgHold101 bars` `maxHold1165` `win21.7%`.

**Next research (no strategy yet, just stats):**
- Does HTF bias at entry predict win? Check `bias_timeline` `btc_engine.py:340` `up/down` vs win%
- Does session `16-20 UTC` predict win? Already `+131` vs `-24`
- Does ADX at entry predict win? `v6` `+90.5` says yes
- Does leg ATR ratio predict win? `leg/ATR 5.75` `fix/btc_ideas.md:59` no weak legs, but larger leg wins `+40%`
- Does previous swing same-dir `40.7%` `fix/btc_ideas.md:60` predict?
- Does volume (if we fetch `BTC_TFS` `volume` `btc_config.py:3` `x,y` `0,0` currently) predict?

**No flip strength edge — focus on HTF, session, ADX, leg size, not candle body.**

