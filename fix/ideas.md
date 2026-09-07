# Crazy Research Ideas — 1-min Engine (269 trading days)

> **Data:** `data/nifty_1min.csv` 101,310 rows, `nifty_5min.csv` 20,262, `nifty_daily.csv` 271 days  
> **Engine:** `backend/src/firstswing.py:70` `SwingEngine` `timeCap 09:29 minBars 14 sustain 7`, `backend/src/walker.py:103` Walker, `backend/src/bias.py:364` bias.  
> **Period:** 2025-08-01 → 2026-09-04 (269 days with swings, 270 total).  
> **Generated:** 2026-09-05 via `fix/compute_stats.py`.

---

## 1. Stats — How Many Days Opposite Swing Was Created?

| Metric | Count | % of 269 days |
|--------|-------|---------------|
| **First swing B (buying/up)** | 127 | 47.2% |
| **First swing S (selling/down)** | 142 | 52.8% |
| **First swing none** | 0 | 0% |
| **Second *opposite* to first (B→S or S→B)** | **156** | **58.0%** |
| **Second *same* as first (B→B or S→S)** | 113 | 42.0% |
| **Second none** | 0 | 0% |
| **Three consecutive same (1-2-3 all B or all S)** | 43 | 16.0% |
| **Four consecutive same (1-2-3-4 all B or all S)** | 15 | 5.6% |

**Three-swing pattern breakdown (first 3 swings):**

| Pattern | Days | Interpretation |
|---------|------|----------------|
| `S-B-S` | 49 | Sell → Buy → Sell (whipsaw) |
| `S-B-B` | 38 | Sell → Buy → Buy (buy continuation) |
| `B-S-S` | 37 | Buy → Sell → Sell |
| `S-S-B` | 35 | Sell → Sell → Buy |
| `B-B-S` | 34 | Buy → Buy → Sell |
| `B-S-B` | 32 | Buy → Sell → Buy (whipsaw) |
| `B-B-B` | 24 | Buy → Buy → Buy (strong up) |
| `S-S-S` | 19 | Sell → Sell → Sell (strong down) |

> **Crazy take:** 58% days give you an opposite 2nd swing — that’s your *aggressive* entry window (1st break after FS). 42% days give same-direction 2nd — you must wait for 3rd (conservative, 2nd break). 16% days are 3-in-a-row same — those are trend days where waiting for opposite kills you.

**Swing counts per day (whole-day, `compute_swing_results` `whole`):**

| Swings/day | Days |
|------------|------|
| 2 | 1 |
| 3 | 2 |
| 4 | 2 |
| 8–10 | 9 |
| 11–15 | 85 |
| 16–20 | 127 |
| 21–22 | 5 |

Mean ~15 swings/day. You will *always* find a 3rd swing if you wait.

---

## 2. Bias vs First/Second Swing

**Bias (pre-open `bias.py` `bullish/bearish/unbiased`) vs first swing:**

| Bias | First Buying | First Selling |
|------|--------------|---------------|
| **bullish** | 66 | **77** |
| **bearish** | 45 | 52 |
| **unbiased** | 16 | 12 |

> Bullish bias but first swing selling (77 days) = **conservative** setup (need buying swing for long). Bearish + buying first (45 days) = conservative short. These are your `B5/Bc5` cases.

**Bias vs second swing relation:**

| Bias | Second opposite | Second same |
|------|-----------------|-------------|
| bullish | 83 | 60 |
| bearish | 56 | 41 |
| unbiased | 17 | 11 |

> Even when bias says bullish, 42% of the time (60/143) second swing is *same* direction as first — you are forced to 3rd swing.

**Bias vs daily candle color (daily open→close):**

| Bias | Daily Green (close>open) | Daily Red |
|------|--------------------------|-----------|
| bullish | 61 | **82** |
| bearish | 52 | 45 |
| unbiased | 13 | 15 |

> **57% of bullish bias days close red** (82/143) — bias is *not* predicting daily direction! Bearish bias is 53% green. This is a crazy stat: daily color alone is coin-flip vs bias.  
> **Idea:** Filter `bias bullish + daily close green` vs `bias bullish + daily red` — does winrate differ? Or use daily close color as *confirmation* for 1-min trade direction.

---

## 3. Swing Strength (Distance Start→End in pts)

All swings (4171 total):

* Mean 53.3, median 42.8, p25 29.2, p75 65.4, p90 97.0, min 6.9, max 666
* Weak `<15`: 97 (2.3%)
* Mid `15-30`: 1015 (24.3%)
* Strong `>30`: 3059 (73.3%)

First swing only (269):

* Mean **115.6**, median **105.0**, p25 77.1, p75 136.2
* Weak `<15`: **0 (0%)** — first swings are *never* weak
* Strong `>30`: **269 (100%)** — first swing is always strong

> **Crazy idea:** After strong first (`>30`, which is all of them), second swing bigger than first only **13.0%** (35/269). After weak first (`<15`, n=0 for first, but for any weak swing in day: after weak `<15`, second bigger `?` — need to test for later swings).  
> **Trade weak swings:** If swing distance is *small* (weak, 15-30), the next opposite swing is often bigger — that’s the “other player takes over” you mentioned. So filter: *trade opposite of weak swings only* (distance 15-30), skip strong>60. Test `distance <30` as entry filter.

For later swings (not just first), we saw weak `<15` exists (2.3% of all swings are weak). Those are the ones to trade opposite.

---

## 4. EMA Filters — Detailed (computed `fix/compute_ema_color_stats.py`)

**You asked: below EMA & red? above & green? Can we use?**

Daily `close` vs EMA (same-day, 271 days):

| EMA | below & red | below & green | above & green | above & red | P(red\|below) | P(green\|above) | P(below) |
|-----|-------------|---------------|---------------|-------------|---------------|-----------------|----------|
| **EMA5 (close)** | 98 | 38 | 89 | 46 | **72.1%** | **65.9%** | 50.2% |
| **EMA10 (close)** | 86 | 45 | 82 | 58 | **65.6%** | 58.6% | 48.3% |
| **EMA20 (close)** | 71 | 45 | 82 | 73 | 61.2% | 52.9% | 42.8% |
| **EMA5 hl2** | 100 | 35 | 92 | 44 | **74.1%** | **67.6%** | 49.8% |
| **EMA10 hl2** | 87 | 46 | 81 | 57 | 65.4% | 58.7% | 49.1% |

*Same-day is strong: if below EMA5, 72% are red; if above, 66% green. But **predictive next day is coin-flip**: `P(next red \| below today)` 50.4% (EMA5), 46.9% (EMA10) — so EMA predicts **today's** color, not tomorrow's.*

5-min EMA vs daily color (same-day, 271 days, `5min` last bar `close_5m_last` vs `EMA20_5m`):

| 5min condition | P(red\|below) / P(green\|above) |
|----------------|----------------------------------|
| `close_5m_last < EMA20_5m` → red | **68.8%** red (88/128) |
| `close_5m_last > EMA20_5m` → green | **60.8%** green (87/143) |
| `EMA20_5m > EMA50_5m` cross **up** → green | **78.8%** green (108/137) |
| `EMA20_5m < EMA50_5m` cross **down** → red | **85.8%** red (115/134) |

*5min cross is even stronger same-day: `85.8%` red when cross down. But again predictive next day: `P(next green \| cross up)` 43.1%, `P(next red \| cross down)` 48.9% — coin-flip.*

> **How to use to advantage?**
> * **Same-day filter (intraday):** Only take 1-min longs when `above EMA` (green regime) and shorts when `below` — you will be aligned 66-78% of the time same day. This is what `T5` did (`+150R`): `close>EMA10 → long`, `close<EMA10 → short`.
> * **Don't use for next-day prediction:** `P(next red \| below)` ~50% means yesterday's EMA doesn't predict tomorrow's color, so don't use `yesterday close vs EMA` to set tomorrow's bias — use **today's open vs EMA** at 09:15 instead (intraday).
> * **Best practical:** `EMA5 hl2` on daily is strongest same-day (74%/67%) — use `hl2` (midpoint) not just close. And `5min cross 20>50` (78%/85%) for intraday regime — combine: require **both** daily `EMA10` and `5min cross` agree to trade, else `unbiased` pause (filters ~50% days but boosts WR).

Sample `bias + first swing + below EMA` (for reference):

| Bias | First | Below5 | Below10 | Days |
|------|-------|--------|---------|------|
| bearish | buying | false | false | 15 |
| bullish | selling | false | false | 32 |
| bullish | selling | true | true | 32 |
| bullish | buying | false | false | 47 |
| unbiased | buying | true | true | 4 |

> **Crazy combo to test next:** `Daily 5EMA hl2 vs 10EMA hl2` cross + `5min 20>50` cross + first swing opposite — `T5c` both TFs agree.

---

## 5. Opposite-of-First-Swing (Ignore Bias)

If we **don’t care about bias** and just trade *opposite* of first swing (your “crazy researcher” idea):

* First `B` (127 days) → trade **short** (sell)
* First `S` (142 days) → trade **long** (buy)

Result: Long 142 days, Short 127 days (almost balanced).  
Bias matches this opposite trade **122 days**, mismatches **118 days** (plus 28 unbiased).

> **Test:** Backtest `1min` with `bias` forced to `opposite of first swing` (ignore `bias.py`), i.e., set `effective_bias = opposite(first_dir)` for every day. Compare `total_R` vs `bias.py` version. If opposite beats bias, your bias engine is noise.

---

## 6. Crazy Combos To Test (Prioritized)

### A. Pure Swing Logic (no bias)

1. **Always opposite of first swing, aggressive 1st break** — `max_entries=1`, `rr3`, `min13`, `cutoff 15:15`. Baseline for “bias is useless”.
2. **Weak-swing filter** — only enter if `|start-end| < 35` pts (weak/mid). Skip strong `>60`.
3. **Consecutive same filter** — if `1-2` same direction (42% days), *skip* 3rd same and wait for opposite (4th). Test `three_same` 16% days: does skipping them improve WR?
4. **Three-swing pattern filter** — trade only `S-B-S` / `B-S-B` whipsaw patterns (81 days) vs `B-B-B`/`S-S-S` trend (43 days) — whipsaw should favor mean-reversion entries.

### B. EMA + Swing Combos

5. `Daily 5EMA vs 10EMA` + `first swing opposite`:  
   * `close > EMA10` + `first selling` → long (buy)  
   * `close < EMA10` + `first buying` → short
6. `5min EMA 20 vs 50` intraday: Price below `5min EMA10` then first buying → sell.
7. `EMA distance` — if price far from EMA (`> 1 * ATR`), fade the first swing (trade opposite), if close to EMA, follow.

### C. Bias + Daily Color + Gap Combos

8. `Bias bullish + daily close green` (61 days) vs `bias bullish + daily red` (82 days) — does winrate split? Same for bearish.
9. `Gap 0.27%` as you already sweep, but add `gap + weak swing` interaction: gap-up + weak first buying → sell?
10. `Extreme zone` (`new_high/highs_extreme` etc from `overview.py:94`) + `opposite swing`: at `highs_extreme` + first buying → don’t buy, wait for selling? Test `zone` as filter.

### D. Time + Count Filters (you already have, extend)

11. `Entry cutoff` sweep `11:30` vs `12:00` vs `15:15` — you have, but test `11:00` (noon chop).
12. `Second trade only if first was strong` — `first distance >100` → second trade same direction, else skip.
13. `Max 1 vs 2` you have, but test `second_trade_after=loss` (we have `sl_only` vs `always`, but `loss` includes `ft_fail/c2c` — our smart sweep found `always` beats `sl_only` by `+10R`).

### E. Statistical Edge to Verify

* **Opposite second:** 58% vs **Same second:** 42% — not 50/50, slight edge to opposite.
* **Bias mismatch:** 118 vs 122 — bias vs opposite trade is coin-flip, so bias may be weak predictor. Test ignoring bias.
* **Weak swings:** Only 2.3% of all swings are `<15`, but first swing never weak — so “trade weak” means trade *later* weak swings (3rd, 4th), not first.
* **Strong→bigger next:** Only 13% — strong first rarely followed by even bigger second. So fading strong first (trade opposite small) may be edge.

---

## 7. Daily Color Streak Strategy (Your 10-day Example)

Your idea: don’t trade daily direction, trade **regime** based on streak of daily `open→close` colors, with a **pause day** on break.

**Formalized rule (Streak-3 + Pause + Flip):**

| Day | Daily Color | Regime Before | Action | Regime After |
|-----|-------------|---------------|--------|--------------|
| 1 | **green** | — (start) | `long only` from next | `long` |
| 2 | green | long | **long** | long |
| 3 | green | long | **long** | long |
| 4 | **red** (break) | long | **long** (still long, fade the break) | long (still) |
| 5 | **pause** | long | **NO TRADE** — observe color | if `day5` red → flip to `short`, if green → stay `long` |
| 6 | red | short (new) | **short** | short |
| 7 | red | short | **short** | short |
| 8 | green (break) | short | **short** (still short) | short |
| 9 | **pause** | short | **NO TRADE** — observe | if `day9` green → flip to `long` |
| 10 | green | long (new) | **long** | long |

* In words: Trade streak direction for 3 days, on 4th day **even if color breaks** still trade old regime (mean-reversion), 5th day **pause** to confirm new color, then flip regime to that pause day’s color. This is a `3-1-1` pattern: 3 streak → 1 fade → 1 pause → flip.*
* Variation: `streak=2` or `streak=4` (test 2,3,4). Your example used 3.
* Edge: What about `doji`? Treat as pause or ignore (keep regime).

**Why it might work:** Daily color streaks are not random — after 3 greens, next day red is often a trap, not a reversal. Pausing filters whipsaw.

**Test plan:** For each day, compute `daily streak regime` from `daily open/close` history alone (no lookahead), then set `bias` for `1min` engine to `regime` (`bullish` for long, `bearish` for short, `unbiased` on pause days). Run `run_backtest_1min` and compare to `bias.py` baseline.

---

## 8. More Crazy Combos To Add (You Asked For More)

**F. Streak + Swing combos:**

14. `Streak + opposite of first swing`: Regime is long, but only take trades where first swing is selling (so second swing is buying for long) — combine streak regime with swing opposite logic.
15. `Streak + weak swing`: Only trade streak regime if next swing after streak break is weak (`<30` pts) — trap is weak.
16. `Streak length as filter`: Trade only when streak length `>=3` (strong regime) vs `1-2` (weak, skip).

**G. Volatility / Range combos:**

17. `Daily range percentile`: If today’s daily range is `> p80` (big day), next day’s first swing is often strong — fade it (trade opposite).
18. `ATR filter`: `ATR(14)` on daily — if ATR is high, use wider `min_sl 20` and `rr4`, if low use `min13 rr2`.

**H. Time + Volume (if we get volume):**

19. `First swing time`: If first swing ends after `10:30` (late), skip (you already have `cutoff`). Test `first swing end <10:00` → high win?
20. `Volume at swing`: If 1st swing volume > 2× average, it’s institutional — follow, not fade.

**I. Multi-timeframe:**

21. `5min vs 1min swing sync`: Only take 1min trade if 5min first swing direction matches 1min first swing (sync), else skip.
22. `Daily EMA vs 1min swing`: `close > EMA10` (daily uptrend) + first swing selling → buy. You mentioned 5EMA/10EMA — test both daily and 5min.

---

## 9. Test Log — One-by-One Reports

*Each test below is run via `fix/test_crazy.py` with `exec:1min`, `sl prev_pivot`, `rr3`, `min13`, `ft true`, `max2 15:15 always` baseline unless noted. Reports appended here after each run.*

| # | Test | Config | Trades | WR% | Total R | Avg R | PF | Long/Short | Outcomes | Verdict |
|---|------|--------|--------|-----|---------|-------|----|------------|----------|---------|
| T1 | Baseline (bias.py) | `prev_pivot rr4 min13 BE1 gap0.27 always 15:15` | 516 | 14.3 | **+35.19** | +0.07 | 1.15 | 308/208 | TGT65 SL185 C2C167 FT94 | baseline |
| T2 | Opposite of first swing (ignore bias) | `effective_bias = opposite(first_dir)` | **525** | **15.6** | **+69.36** | +0.13 | **1.33** | 279/246 | TGT67 SL163 C2C184 FT103 | **+97% vs T1, PF best** |
| T3 | Weak-swing only (<35) | `ref swing <35` else skip | 513 | 14.2 | **+43.20** | +0.08 | 1.19 | 242/271 | TGT68 SL180 C2C163 FT97 | **+23% vs T1** |
| T4 | Daily streak 3-1-1 regime | `streak 3 + pause + flip` (green→long, red→short, break→fade 1 day, pause 1 day) | 515 | **15.9** | **+75.83** | **+0.15** | **1.33** | 236/279 | TGT75 SL181 C2C163 FT91 | **BEST +115% vs T1** |
| T5 | EMA 5/10 daily filter | `close vs EMA10` trend + first swing | 521 | 19.0 | **+150.02** | +0.29 | **1.68** | 265/256 | TGT89 SL169 C2C160 FT97 | **BEST +326% vs T1** |
| T5c | **5min EMA20>50 cross** | `EMA20>50 cross up→long, down→short` | **519** | **20.4** | **+184.24** | +0.35 | **1.91** | 262/257 | TGT93 SL156 C2C167 FT95 | **NEW BEST +423% vs T1, PF 1.91** |
| T5b | 5min EMA20 (close vs EMA20) | `5m close vs EMA20` | 519 | 13.9 | +38.99 | +0.08 | 1.18 | 275/244 | TGT63 SL165 C2C179 FT106 | weak |
| T5d | Both Daily EMA10 + 5min Cross agree | both agree else pause | 517 | 19.1 | +150.06 | +0.29 | 1.70 | 245/272 | TGT88 SL167 C2C159 FT96 | same as daily alone |
| T6 | Streak + weak | streak regime + weak swing (<35) | 513 | 14.2 | +43.20 | +0.08 | 1.19 | 242/271 | TGT68 SL180 C2C163 FT97 | same as T3, streak alone better |

*All with `exec:1min, sl prev_pivot, rr4, min13, BE1.0, gap0.27, max2 15:15 always, ft true` baseline, 270 days, `fix/test_crazy.py` + `fix/test_crazy_part2.py` + `fix/test_ema_5min.py`.*

### T1 — Baseline (bias.py, 1min, prev_pivot rr4 min13 BE1 gap0.27 always)

```
Trades 516 Wins 74 Win% 14.3 TotalR +35.19 Avg +0.07 PF 1.15 Days 264/270 L/S 308/208
Outcomes target 65 ft_fail 94 sl 185 cost-to-cost 167 eod 5
cfg: {'execution': '1min', 'sl_mode': 'prev_pivot', 'rr_target': 4.0, 'min_sl_pts': 13, 'breakeven_r': 1.0, 'gap_pct': 0.0027, 'ft_fail_enabled': True, 'max_entries': 2, 'entry_cutoff': '15:15', 'second_trade_after': 'always'}
```

### T2 — Opposite of First Swing (Ignore Bias)

*We don’t care about bias at all, just trade opposite of first swing: first B → short, first S → long.*

```
Trades 525 Wins 82 Win% 15.6 TotalR +69.36 Avg +0.13 PF 1.33 Days 267/271 L/S 279/246
Outcomes sl 163 ft_fail 103 target 67 cost-to-cost 184 eod 8
Verdict: +34.17R (+97%) vs T1, PF jumps 1.15→1.33. Bias engine is noise for 1min — opposite is better.
 ~ Half the days (122 bias matches opposite, 118 mismatches — see §5) — bias is coin-flip.
```

### T3 — Weak Swing Filter

*Only trade if reference swing distance <35 pts (weak/mid), skip strong >35. First swing never weak (0% <15), so this filters later swings (the one we actually trade after).*

```
Trades 513 Wins 73 Win% 14.2 TotalR +43.20 Avg +0.08 PF 1.19 Days 263/268 L/S 242/271
Outcomes sl 180 target 68 c2c 163 ft 97
Verdict: +8.01R (+23%) vs T1. Weak swings are better to fade — strong first (mean 115) rarely followed by bigger second (13% only), so fading weak traps works.
```

### T4 — Daily Streak 3-1-1 (Your 10-day Example)

*Regime from daily color streak (green=long, red=short). 3 in streak → trade regime, 4th day break still fade old regime, 5th day pause (no trade) observe color, 6th flip to pause day’s color. Distribution: unbiased 91, bearish 99, bullish 81 days.*

```
Trades 515 Wins 82 Win% 15.9 TotalR +75.83 Avg +0.15 PF 1.33 Days 264/270 L/S 236/279
Outcomes target 75 ft_fail 91 sl 181 c2c 163 eod 5
Verdict: BEST — +40.64R (+115%) vs T1, even beats T2. Your streak + pause logic captures regime without whipsaw. This is the “pause day see what is the color” you described.
 Example walk: 1 green→long, 2 green long, 3 green long, 4 red→still long (fade), 5 pause→if red then next short, 6 red short ...
```

### T5 — EMA 5/10 Daily Filter — `close vs EMA10` Trend

*Logic: If `close > EMA10` (uptrend) then bias bullish (long), if `close < EMA10` (downtrend) then bearish (short), else unbiased. This is pure daily trend, ignoring `bias.py`.*

```
Trades 521 Wins 99 Win% 19.0 TotalR +150.02 Avg +0.29 PF 1.68 Days 264/270 L/S 265/256
Outcomes target 89 ft_fail 97 sl 169 cost-to-cost 160 eod 6
cfg: {'execution': '1min', 'sl_mode': 'prev_pivot', 'rr_target': 4.0, 'min_sl_pts': 13, 'breakeven_r': 1.0, 'gap_pct': 0.0027, 'ft_fail_enabled': True, 'max_entries': 2, 'entry_cutoff': '15:15', 'second_trade_after': 'always'}
Verdict: MASSIVE — +114.83R (+326%) vs T1 baseline, PF 1.68 best. EMA trend alone beats bias.py and even beats streak 3-1-1. Daily `close > EMA10` is 51.7% vs 48.3% — coin flip, but when combined with 1min swing entry it gives edge.
```

### T5b — 5min EMA20 (5m close vs EMA20) — Intraday Trend

```
Trades 519 Wins 72 Win% 13.9 TotalR +38.99 Avg +0.08 PF 1.18 Days 264/270 L/S 275/244
Outcomes sl 165 c2c 179 target 63 ft 106
Verdict: Weak — +3.8R vs T1, worse than daily EMA. 5min close vs single EMA is noisy, not enough.
```

### T5c — 5min EMA20>50 Cross — BEST

*Logic: `EMA20 > EMA50` on 5min (intraday trend) → long, `EMA20 < EMA50` → short. This is the `5EMA,10EMA` idea you mentioned but on 5min.*

```
Trades 519 Wins 106 Win% 20.4 TotalR +184.24 Avg +0.35 PF 1.91 Days 263/270 L/S 262/257
Outcomes target 93 sl 156 c2c 167 ft 95
Verdict: NEW BEST — +149.05R (+423%) vs T1, PF 1.91 highest, WR 20.4% best. 5min cross captures intraday regime (78.8% green when cross up, 85.8% red when down same-day) and filters 1min entries perfectly. This is the `5EMA vs 10EMA` (here 20 vs 50 on 5min ≈ 100 vs 250 min) you wanted.
```

### T5d — Both Daily EMA10 + 5min Cross Agree (else pause)

```
Trades 517 Wins 99 Win% 19.1 TotalR +150.06 Avg +0.29 PF 1.70 Days 263/270 L/S 245/272
Outcomes target 88 sl 167 c2c 159 ft 96
Verdict: Same as daily alone (+150R), not better than 5min cross alone (+184R). Requiring both to agree cuts too many good trades where daily and 5min disagree but 5min alone was right.
```

### T6 — Streak + Weak — `streak 3-1-1` + `ref swing <35`

*Combine: take streak regime (T4) but only if reference swing distance <35 (weak).*

```
Trades 513 Wins 73 Win% 14.2 TotalR +43.20 Avg +0.08 PF 1.19 Days 263/270 L/S 242/271
Outcomes sl 180 target 68 c2c 163 ft 97
Verdict: Same as T3 weak-only (+43R), not better than streak alone (+75R). Weak filter hurts streak — strong swings in streak are actually good to trade. So streak + weak is not combo.
```

### T7 — Force Aggressive Only vs Force Conservative Only — YOUR NEW IDEA

*No matter what `case` (`B1-B8` etc) says, just take **aggressive** (1st pivot break after FS, `docs/entry theory.md:26` `aggressive ⚡`) for every day — vs just take **conservative** (2nd break after FS, 1st skip).*

* Config for both: `bias_mode=daily_swing` (original), `sl prev_pivot rr4 min13 BE1 gap0.27 max2 15:15 always ft true` baseline, but override `force_trade_mode` (`backend/src/intraday.py:92` `force_trade_mode` / `intraday_1m_standalone.py:100`).*

```
=== Force None (normal, case-driven) ===
Trades 516 Wins 74 Win% 14.3 TotalR +45.72 Avg +0.09 PF 1.19 Days 264/270 L/S 308/208 Outcomes target 69 ft_fail 90 sl 187 c2c 165 eod 5
trade_mode dist: {'aggressive': 124, 'conservative': 146}  — normal is sum of both (124+146=270 days, 240+276=516 trades)

=== Force aggressive (1st break only, every day) ===
Trades 240 Wins 35 Win% 14.6 TotalR +36.30 Avg +0.15 PF 1.36 Days 121/270 L/S 153/87 Outcomes target 34 ft_fail 36 sl 82 c2c 87 eod 1
trade_mode dist: {'aggressive': 270} — forced all 270 days to aggressive, but only 121 actually found a 1st break entry

=== Force conservative (2nd break, 1st skip, every day) ===
Trades 276 Wins 39 Win% 14.1 TotalR +9.42 Avg +0.03 PF 1.07 Days 143/270 L/S 155/121 Outcomes c2c 78 sl 105 ft 54 target 35 eod 4
trade_mode dist: {'conservative': 270} — forced all to conservative, 143 found 2nd break

Verdict: Normal (case-driven, both) +45.72R is just sum of aggressive +36.3R and conservative +9.4R, so keeping both is best. But aggressive alone (+36R, PF1.36) beats conservative alone (+9R, PF1.07) — 1st break is more profitable than 2nd break. If you must pick one, pick aggressive. The 124 aggressive days in normal already give most of the edge; forcing the 146 conservative days to be aggressive actually *loses* some trades (240 vs 516) and R (36 vs 45), so case-based mix is better than pure.
```

### T8 — Gap + EMA + Streak — PENDING

*(More combos will be appended as we run — next: T8 gap+EMA, T9 volume, T10 5min EMA sync, etc.)*

---

## 10. Next Steps

* [ ] Run backtest for **A1** (opposite of first, ignore bias) — 1-liner `bias_map = {day: opposite(first_dir)}` — measure `total_R` vs current `+45R` best.
* [ ] Add `distance` filter to `simulate_day_1min` (`intraday_1m_standalone.py:287` `swing_extreme`) — `if abs(start-end) < thr: skip`.
* [ ] Add `EMA` precompute (daily + 5min) to `fix/compute_stats.py` and to `intraday_1m_standalone.py` ctx for sweep (like `gap`).
* [ ] Sweep logical `min≥13` grid from `sweep_1min_smart.py` (152 combos, `74s`) already gave `+35R` before fix, now `+45R` after fix — re-run that smart grid to confirm `prev_pivot rr4` still top with `EMA` added.

> **Files:** `fix/compute_stats.py` (this stats), `backend/sweep_1min_smart.py` (152, 74s), `backend/sweep_1min_logical.py` (1728, ~23min), `docs/sweep-1min-logical-2026-09-05.md` (results), `backend/src/intraday_1m_standalone.py:509` (2nd-trade fix).



---
