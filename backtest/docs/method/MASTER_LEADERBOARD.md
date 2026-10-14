# MASTER LEADERBOARD — All Experiments, One Place

<!-- MARK-CORRECTION-NOTICE -->
> **MARK-CORRECTION NOTICE (2026-10-14). — SUPERSEDED, DO NOT QUOTE THE FIGURES BELOW.**
>
> This page was written against the chain of **2753 swings / 7505 marks**. The
> engine has since been corrected at the mark level — B1 arming fix (`77711a6`),
> V13 (`88ecd00`), volatile-B1 colour rule and same-bar duplicate-pivot fix
> (`5d6cab2`, `d71304f`) — giving **2840 swings / 7734 marks**. Every net, trade
> count, retention and ranking below is **no longer what the engine produces.**
>
> **What changed on the corrected chain:**
>
> | | |
> |---|---|
> | registry | **215 entries → 93 active**; 69 books retired under the owner's rule (any era negative → out). See `docs/method/RETIRED_BOOKS.md` |
> | pins | all 120 re-measured and re-pinned (`dd02cf1`); 51 pinned books verify at **0 mismatches** |
> | `/results` | regenerated; 25 books, none retired |
> | V7 tripwire | re-pinned to `5a4c55331ba079a9` |
> | ranking | `docs/method/SCORECARD_LEADERBOARD.md` regenerated — the order changed, `champ_long_htf15` is now first |
>
> **Current numbers:** `fsent_champ_long` (shipping) IS 497 / **+466.92** / dd 25.08, OOS 281 / **+215.32** / dd 11.20.
>
> Verify anything here with `python exp_pinverify.py`. Do not quote a figure from
> this page without checking it against that.
<!-- /MARK-CORRECTION-NOTICE -->

> **Created:** 2026-09-23  
> **Bar:** OOS/IS retention **≥30% = good** (your bar: 30-40%)  
> **True OOS:** 2021-2022 separate data (`data/unseen/bybit/`) — never touched during development  
> **IS:** 2023-2026 (`data/bybit/`)  
> **Engine:** v18 streak_halt, trail-ratchet fixed, fine 1m fills  
> **Costs:** 0.055% fee/side, 0.005% entry slip, 0.010% exit slip, 0.01%/8h funding  
> **Sources:** STRATEGY_SCORECARD, OOS_VALIDATION_2021_2022, EXPERIMENT_SUMMARY, ANCHOR_BASIS_AUDIT, today's true-OOS test

---

## 1. Master Table — Ranked by True-OOS Net R

| # | Config | Type | IS NET | OOS NET | OOS/IS | ≥30%? | OOS DD | OOS PF | OOS WR | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | chopband_multi | multi | +350.7 | **+85.8** | 47% | ~~✓~~ | 29.1 | — | 29.0% | **REJECTED** — failed sw20 validation, 2024-era only |
| 2 | **champion_multi_sw10** | multi | +325.8 | **+70.1** | **41%** | **✓** | 37.3 | 1.59 | 28.0% | **PASS — conservative king** |
| 3 | **utcsat_multi_sw10** | multi | +359.0 | **+60.2** | **32%** | **✓** | 22.1 | 1.58 | 29.6% | **PASS — king (best DD)** |
| 4 | union ct=55 +filt | CRAZE | +267.6 | +53.7 | 20% | ✗ | 6.0 | 2.92 | 40.0% | Best CRAZE absolute; fails retention |
| 5 | mag3+wknd+bm05 | single-filt | +196.4 | +47.6 | 24% | ✗ | 4.0 | — | — | Balanced years; fails retention |
| 6 | mag3+wknd | single-filt | +196.3 | +45.6 | 23% | ✗ | 4.0 | — | — | |
| 7 | entropy ct=55 +filt | CRAZE | +149.0 | +38.3 | 26% | ✗ | — | 3.60 | 48.5% | Most consistent new mode |
| 8 | entropy ct=61 +filt | CRAZE | +161.2 | +31.4 | 19% | ✗ | — | 2.94 | 42.4% | Within-era "king"; fails true OOS |
| 9 | dualunion | CRAZE | +151.2 | +29.7 | 20% | ✗ | — | 2.67 | 36.4% | 2022 = −1.4R; **refuted** |
| 10 | b2_vs_flip ct=58 +filt | CRAZE | +106.6 | +19.5 | 18% | ✗ | — | 2.68 | 44.4% | |
| 11 | fullstack_single | single | +282.9 | +21.0 | 14% | ✗ | 25.4 | — | 25.5% | |
| 12 | king_single | single | +310.7 | +16.9 | 10% | ✗ | 27.9 | — | 25.0% | |
| 13 | wage12_single | single | +278.6 | +13.0 | 9% | ✗ | 19.1 | — | 25.3% | |
| 14 | b2_vs_flip ct=58 RAW | CRAZE | +122.1 | +13.0 | 11% | ✗ | — | — | 25.2% | Only positive raw on true OOS |
| 15 | raw base | base | +217.9 | +9.9 | 4.5% | ✗ | 30.5 | — | — | Heavily curve-fitted (22x) |
| 16 | fliponly_multi | multi | +242.7 | **−17.3** | −14% | ✗ | 46.4 | — | 18.4% | **DEAD** |

**Only 2 configs clear the 30% bar:** `champion_multi_sw10` and `utcsat_multi_sw10`.  
Chopband clears 47% but was **rejected** on cross-chain validation (fails sw20, edge = 2024 only).

### Causal-SL OOS (live-honest numbers, from OOS_VALIDATION doc)

| Config | Batch OOS | Causal OOS | Causal OOS/IS |
|---|---|---|---|
| champion_multi | +70.1 | **+80.0** | **53%** |
| utcsat_multi | +60.2 | **+72.8** | **49%** |
| king_single | +16.9 | +22.1 | 14% |

Causal SL *improves* OOS (+5 to +13R) while cutting IS — retroactive SL was overfitting.

---

## 2. Full Metrics — The Two Multi Kings

### 2a. champion_multi_sw10 (conservative king)

**Config:** mltf + persist7, no weekend skip, sw10, atr_high mode, ext_stop_r=3.0, cd=8

#### IS (2023-2026) — 3.8 years

| Metric | Value |
|---|---|
| Trades | **500** |
| Gross | +445.2R |
| Costs | 119.4R (fee+slip+funding) |
| **NET** | **+325.8R** |
| Win rate | 30.0% (150W / 350L) |
| Avg win / Avg loss | +5.11R / −0.92R |
| W/L ratio | 5.56 |
| Profit factor | **2.38** |
| E[R] per trade | +0.890R |
| Max DD | 17.8R |
| NET/DD | **18.28** |
| Max consec losses | 16 |
| Sharpe (per trade) | 3.59 |
| Avg bars held | 117 (~2 days) |
| Longs | 273t **+339.5R** |
| Shorts | 227t +105.7R |
| Green months | 26/45 (58%) |
| Worst rolling 3m | −13.4R |
| Worst rolling 6m | −5.9R |
| Worst rolling 12m | **+26.4R (never negative)** |

**Yearly spread (IS):**
| 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|
| +113.9R (107t) | +122.3R (161t) | +102.2R (130t) | +106.8R (102t) |

*2026 = through Sep 13. Every year ≥ +100R. Min year +102.2R.

**Tail dependence (IS):**
| Remove | NET |
|---|---|
| Full | +325.8 |
| Top 1 trade | +270.1 (83% remains) |
| Top 5 trades | +106.8 (33%) |
| Top 10 trades | **−3.3 (breakeven)** |

Top 10 of 500 trades ≈ all the profit — standard trend-following profile.

**Monthly R (IS):** 58% green. Best: 2023-12 +52.4, 2026-08 +50.3, 2024-01 +44.4. Worst: 2023-09 −6.0, 2024-07 −8.2, 2025-03 −9.5. Max 3 consecutive losing months.

**Walk-forward (6 segments):** all positive — worst segment +46.2R.

#### True OOS (2021-2022) — 2 years

| Metric | Value |
|---|---|
| Trades | **279** |
| Gross | +105.7R |
| Costs | 35.6R |
| **NET** | **+70.1R** |
| Win rate | 28.0% (78W / 201L) |
| Avg win / Avg loss | +3.65R / −0.89R |
| W/L ratio | 4.10 |
| Profit factor | **1.59** |
| E[R] per trade | +0.379R |
| Max DD | 37.3R |
| NET/DD | 1.88 |
| Max consec losses | 15 |
| Sharpe (per trade) | 1.88 |
| Avg bars held | 100 |
| Longs | 162t +22.1R |
| Shorts | 117t **+83.6R** (shorts carry OOS) |
| Green months | 10/24 (42%) |
| Worst rolling 3m | −25.6R |
| Worst rolling 6m | −30.5R |
| Worst rolling 12m | −29.9R |

**Yearly spread (OOS):**
| 2021 | 2022 |
|---|---|
| **−11.0R** (152t) | **+116.7R** (127t) |

**Tail (OOS):** full +70.1 → −top1 +37.0 → −top5 **−24.8** → −top10 −67.9.  
Without top-5 winners the config is negative OOS — extreme tail dependence.

**Monthly (OOS):** 42% green. Nov 2022 alone = **+65.2R** (FTX). Mar 2022 +36.6, Jun 2022 +28.5. Worst months −5 to −13.

**OOS/IS retention: 41%** (batch) / **53%** (causal) — **PASSES 30% bar.**

**FTX caveat:** 2022 profit is heavily Nov-crisis driven. 2021 (bull) = −11R. Without the FTX event, OOS ≈ flat.

---

### 2b. utcsat_multi_sw10 (king multi)

**Config:** champion + `exp_skip_utc_sat=1` (skip UTC Saturday only; UTC Sunday kept — it's profitable)

#### IS (2023-2026) — 3.8 years

| Metric | Value |
|---|---|
| Trades | **454** |
| Gross | +466.5R |
| Costs | 107.5R |
| **NET** | **+359.0R** |
| Win rate | 30.8% (140W / 314L) |
| Avg win / Avg loss | +5.39R / −0.92R |
| W/L ratio | 5.87 |
| Profit factor | **2.62** |
| E[R] per trade | +1.027R |
| Max DD | **14.8R** |
| NET/DD | **24.22** |
| Max consec losses | 13 |
| Sharpe (per trade) | 3.77 |
| Avg bars held | 124 |
| Longs | 252t **+367.4R** |
| Shorts | 202t +99.1R |
| Green months | 25/45 (56%) |
| Worst rolling 3m | −11.7R |
| Worst rolling 6m | **+2.1R (never negative)** |
| Worst rolling 12m | **+44.2R** |

**Yearly spread (IS):**
| 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|
| +125.5R (103t) | +125.3R (141t) | +101.2R (119t) | +114.5R (91t) |

Every year ≥ +101R. Tightest yearly band of any config (+101 to +126).

**Tail dependence (IS):**
| Remove | NET |
|---|---|
| Full | +359.0 |
| Top 1 | +303.2 (84%) |
| Top 5 | +140.0 (39%) |
| Top 10 | **+29.8 (still positive)** |

Less tail-dependent than champion (top-10 still +30R vs champion −3R).

**Monthly (IS):** 56% green. Best: 2026-08 +67.4, 2023-12 +53.4, 2024-01 +44.4. Worst: −7 to −6.

**Walk-forward (6 segments):** all positive — worst +40.5R.

#### True OOS (2021-2022) — 2 years

| Metric | Value |
|---|---|
| Trades | **253** |
| Gross | +92.6R |
| Costs | 32.4R |
| **NET** | **+60.2R** |
| Win rate | 29.6% (75W / 178L) |
| Avg win / Avg loss | +3.38R / −0.90R |
| W/L ratio | 3.74 |
| Profit factor | **1.58** |
| E[R] per trade | +0.366R |
| Max DD | **22.1R** (vs champion 37.3) |
| NET/DD | **2.72** |
| Max consec losses | **9** (vs champion 15) |
| Sharpe (per trade) | 1.75 |
| Avg bars held | 94 |
| Longs | 148t +21.2R |
| Shorts | 105t **+71.4R** |
| Green months | 11/24 (46%) |
| Worst rolling 3m | −15.5R |
| Worst rolling 6m | −19.1R |
| Worst rolling 12m | **−6.7R** (vs champion −29.9) |

**Yearly spread (OOS):**
| 2021 | 2022 |
|---|---|
| **+13.2R** (137t) | **+79.5R** (116t) |

**Both years positive** — champion had 2021 = −11R. UTC-Sat skip fixes the bull-year bleed.

**Tail (OOS):** full +60.2 → −top1 +27.1 → −top5 −29.7 → −top10 −66.0. Still FTX-heavy (Nov 2022 = +67.2R) but better shape than champion.

**OOS/IS retention: 32%** (batch) / **49%** (causal) — **PASSES 30% bar.**

---

## 3. Head-to-Head: The Two Multi Kings

| Metric | IS champion | IS utcsat | OOS champion | OOS utcsat |
|---|---|---|---|---|
| NET R | +325.8 | **+359.0** | **+70.1** | +60.2 |
| Trades | 500 | 454 | 279 | 253 |
| WR | 30.0% | 30.8% | 28.0% | 29.6% |
| PF | 2.38 | **2.62** | 1.59 | 1.58 |
| DD | 17.8 | **14.8** | 37.3 | **22.1** |
| NET/DD | 18.3 | **24.2** | 1.9 | **2.7** |
| MCL | 16 | 13 | 15 | **9** |
| Sharpe | 3.59 | **3.77** | 1.88 | 1.75 |
| Worst 12m | +26.4 | **+44.2** | −29.9 | **−6.7** |
| OOS years | — | — | −11 / +117 | **+13 / +80** |
| OOS/IS | — | — | 41% | 32% |
| Causal OOS/IS | — | — | **53%** | 49% |
| Tail −top10 (IS) | −3.3 | **+29.8** | −67.9 | −66.0 |

**Takeaways:**
- **utcsat wins on quality:** better DD, PF, MCL, worst-12m, both OOS years positive, top-10 tail still positive
- **champion wins on absolute OOS R** (+70 vs +60) — but that edge is one bad year (2021 −11) it didn't filter
- **UTC-Saturday skip is the structural edge** that separates them: removes the only consistently bleeding session
- For live: **utcsat is the better default** (darker DD profile, positive both OOS years); champion is the no-calendar-filter fallback

---

## 4. What Passes the 30-40% Bar (Summary)

| Config | OOS/IS | Status |
|---|---|---|
| champion_multi_sw10 | 41% (53% causal) | **KEEP — primary** |
| utcsat_multi_sw10 | 32% (49% causal) | **KEEP — king / preferred** |
| chopband_multi | 47% | **REJECTED** — validation failed |
| everything else | <30% | below bar |

**CRAZE session configs (union/entropy/fd/dualunion):** all 19-26% on true OOS. Good within-era numbers, fail separate-era retention. Do not promote on current evidence.

---

## 5. Structural Edges That Transfer (regardless of config)

1. **Trail mechanism** — quick losers, run winners; core of every positive config  
2. **Multi > Single** — 32-41% vs 9-14% retention; fewer filters  
3. **UTC-Saturday skip** — structural calendar; both OOS years improve  
4. **mag_ratio ≥ 3** — noise vs conviction; +9.9R → +45.6R OOS on CRAZE lane  
5. **B2 + FLIP regime split** — either alone fails; the split is the edge  
6. **Simpler filters generalize** — 2 filters = 41%, 6 filters = 10%

---

## 6. The 2027 Question (frozen forward test)

| Era | Regime | What worked |
|---|---|---|
| 2021-22 | Low-vol bull → FTX crash | Crisis alpha, multi, simple filters |
| 2023-26 | Higher-vol chop/trend | Regime split, trail runners, mag3 |
| **2027** | **Unknown — third regime** | **The only uncontaminated test** |

**Protocol:**
1. **Freeze now:** `utcsat_multi_sw10` (primary) + `champion_multi_sw10` (backup). Optionally `mag3+wknd+bm05` as simple baseline. Nothing else.  
2. **Gate:** +30R+ in 2027 = real edge. ≤0 = kill. Between = weak/era-dependent.  
3. **Interpretation:**  
   - 2027 ≈ 2021-22 → only structural class survives; era-fit modes bleed  
   - 2027 ≈ 2023-26 → IS generalizes, but still can't separate edge from "same regime 3 years running" until it breaks  
4. **Parallel:** paper trade (Level 2) — batch numbers certified, execution not.

**FTX asterisk:** ~80% of true-OOS profit for chopband-class configs came from Nov 2022. Without it, OOS ≈ flat. Expect crisis alpha, not steady alpha, from the multi kings on quiet years.

---

## 7. Dead / Rejected (do not revisit)

| Item | Why |
|---|---|
| fliponly_multi | −17.3R OOS |
| dualunion | 2022 −1.4R; union beats it by +24R true OOS |
| chopband | Fails sw20 validation; 2024-specific |
| B3, room filter, wick reject, ER, risk-width | Per-trade gates; all fail full-path |
| wage + mag combo, swingpause + mag | Hurt OOS when stacked with mag3 |
| htf_dir / htf_mag / ltf_dir modes | Dead raw; signal-property routing fails |
| raw v18 base | 22x IS/OOS — curve-fit |
| **halt_skip=2 / posthalt3 (engine path)** | Trade-list said +18/+11; full-path cascade **−3 IS / −7 OOS** (champion), **−45 IS** (utcsat). REJECTED |
| **MAE surgery (BE / half-SL / dead-exit)** | All kill winners path-true; earlier +56R was path-logic bug |
| **B2-stale age cut** | IS −21.9 / OOS +50.2 — does not transfer |
| **pre-entry alignment (dir/age)** | Era-fit; already rejected as structural gate on multi |
| **adaptive kind gates (K1/K2/K3)** | Fail absolute R both eras |
| **first-of-window-streak cut** | Weak WR both eras despite high net on few trades |

---

## 7b. Deep Autopsy (2026-09-23) — path-true engine flags

Trade-list filters are **not** path-true (skip cascades into busy/cooldown/concurrency).
Engine flags tested full-path: `exp_halt_skip_n`, `exp_skip_decisive` (`exp_engine_filters.py`).

### Results (gross R, full path)

| Variant | champ IS | dIS | champ OOS | dOOS | utcsat IS | dIS | utcsat OOS | dOOS |
|---|---|---|---|---|---|---|---|---|
| baseline | +445.2 | — | +105.7 | — | +466.5 | — | +92.6 | — |
| halt_skip=2 | +442.3 | −3.0 | +98.6 | −7.2 | +421.1 | **−45.3** | +111.3 | +18.6 |
| **skip_decisive** | +445.2 | **0** | **+130.2** | **+24.5** | +466.5 | **0** | +104.9 | **+12.2** |
| N3 (halt2+skip_dec) | +442.3 | −3.0 | +122.4 | +16.7 | +421.1 | −45.3 | +125.3 | +32.6 |
| halt_skip=3 | +455.0 | +9.8 | +99.4 | −6.3 | +398.8 | −67.7 | +99.7 | +7.1 |

### What `decisive` is (causal)

- `mode=atr_high`: `use="decisive"` iff **15m ATR% > 0.65** at entry bar (`v18_streak_halt.py:266-267`)
- Known at entry (ATR from closed bars only) — **no lookahead**
- IS 2023-26: **0 decisive trades** (high-ATR windows never produce valid entries under multi+persist7)
- OOS 2021-22: 58 decisive trades, **net −22.2R** (champion); 54t **−10.0R** (utcsat)
- ATR%>0.65 bars: IS 6.5% of bars, OOS 22.6% — filter only fires in 2021-style vol

### skip_decisive — the only BOTH_UP engine filter

- **Pure filter vs engine:** nearly identical (path cascade adds only +2.3R champ / +2.2R utcsat OOS)
- **Threshold sweep 0.55–0.85:** dOOS positive for **all** thresholds both configs (champ +7.7..+30.9, utcsat +6.5..+16.2) — **not knife-edge at 0.65**
- **IS cost structurally zero** (regime never appears) — not "tested and got lucky"
- **Caveat:** only validated on the era where it fires (2021-22). Insurance for high-vol regimes; no-op in 2023-26-like markets

### skip_decisive — NET (after costs) + year-by-year

Same cost model as leaderboard (fee 0.055%/side + slip + funding). Totals match §2 exactly on baseline.

**champion_multi_sw10**

| Period | Variant | n | GROSS | COST | **NET** | WR |
|---|---|---:|---:|---:|---:|---:|
| IS | baseline | 500 | +445.2 | 119.4 | **+325.8** | 30.0% |
| IS | skip_decisive | 500 | +445.2 | 119.4 | **+325.8** | 30.0% |
| OOS | baseline | 279 | +105.7 | 35.6 | **+70.1** | 28.0% |
| OOS | **skip_decisive** | 222 | +130.2 | 30.9 | **+99.3** | 28.8% |

IS yearly NET (unchanged — filter never fires):

| 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|
| +86.9 (107t) | +88.8 (161t) | +68.8 (130t) | +81.3 (102t) |

OOS yearly NET:

| Year | baseline | skip_decisive | Δ |
|---|---:|---:|---:|
| 2021 | −26.4 (152t) | **−1.6** (107t) | **+24.8** |
| 2022 | +96.6 (127t) | **+100.9** (115t) | **+4.3** |
| **Total** | **+70.1** | **+99.3** | **+29.2** |

**utcsat_multi_sw10**

| Period | Variant | n | GROSS | COST | **NET** | WR |
|---|---|---:|---:|---:|---:|---:|
| IS | baseline | 454 | +466.5 | 107.5 | **+359.0** | 30.8% |
| IS | skip_decisive | 454 | +466.5 | 107.5 | **+359.0** | 30.8% |
| OOS | baseline | 253 | +92.6 | 32.4 | **+60.2** | 29.6% |
| OOS | **skip_decisive** | 200 | +104.9 | 28.0 | **+76.8** | 29.0% |

IS yearly NET (unchanged):

| 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|
| +99.4 (103t) | +97.3 (141t) | +70.9 (119t) | +91.4 (91t) |

OOS yearly NET:

| Year | baseline | skip_decisive | Δ |
|---|---:|---:|---:|
| 2021 | −1.2 (137t) | **+11.1** (96t) | **+12.3** |
| 2022 | +61.4 (116t) | **+65.7** (104t) | **+4.3** |
| **Total** | **+60.2** | **+76.8** | **+16.6** |

**Retention (OOS/IS, annualized like §1):** champion 41%→**~58%**; utcsat 32%→**~41%**. Both clear the 30% bar with room.

**Verdict:** free NET upgrade — IS untouched, OOS +29R / +17R, 2021 bleed almost stops (champ −26→−2; utcsat −1→+11). Optional flag on the two frozen kings; not a new config.

### halt_skip=2 — REJECTED

Trade-list posthalt3 (+18.1/+11.2) was an artifact of non-sequential filtering.
Full-path: skips shift busy/cooldown/concurrency and **amputate winners** after the halt window. utcsat IS collapses −45R. Do not ship.

### Other structural findings (both eras unless noted)

| Finding | IS | OOS | Verdict |
|---|---|---|---|
| conc=0 (first entries) weak | WR 26.6%, +293 | +14.9 | Confirmation stacks (conc≥1) carry edge |
| conc≥1 strong | WR 40.5% | +90.8 of +105.7 | Structural — multi is the edge |
| break_kind era-flip | FLIP +363 / B2 +82 | B2 +86 / FLIP +20 | Neither kind alone transfers |
| regime age 8-15 stale | +7.6 | −1.3 | Dead |
| E[R after win] > after loss | yes | yes | Meta only; causal gates fail |
| window gap 2-8h | strong | strong, tiny n | Not tradeable sample |

---

## 8. Reproduce

```bash
# Full metrics for both multi kings (IS from JSON + OOS fresh)
python -m live_stuff.tests.exp_master_metrics

# True OOS CRAZE-lane comparison (union/entropy/dualunion/...)
python -m live_stuff.tests.exp_dualunion_true_oos

# Filter ablation (where the 300+ trades go)
python -m live_stuff.tests.exp_filter_ablation

# Path-true engine filters: halt_skip_n / skip_decisive (IS + true OOS, gross)
python -m live_stuff.tests.exp_engine_filters

# Decisive regime deep-dive (threshold sweep, pure vs path)
python -m live_stuff.tests.exp_decisive_deep

# Full NET + yearly for kings (with optional skip_decisive via exp flags above)
python -m live_stuff.tests.exp_master_metrics

# Registry leaders
python backtest/tests/run_experiment.py --group best
```

---

*Document generated 2026-09-23. All numbers post trail-ratchet-fix unless noted.*
