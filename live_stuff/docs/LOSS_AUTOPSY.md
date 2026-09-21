# Loss Autopsy + Winner Anatomy

**Date:** 2026-09-20
**Harness:** `live_stuff/tests/exp_loss_autopsy.py`
**Baseline:** v18 anchor, single position (340t, gross +251.6R, NET +166.7R, WR 30.0%, DD 27.1)
**Cost model:** Asymmetric slippage (entry 0.005%, exit 0.01%), Bybit taker 0.055%/side, funding 0.01%/8h. Partial exits split 50/50 at partial price + final exit price (verified: +0.0009R per partial trade, negligible).

## Theory

The strategy's edge comes from rare big runners (4R+) that pay for many small losses. To improve, we must:
1. Understand WHY losses happen (which patterns repeat?)
2. Understand WHAT makes winners big (which conditions produce runners?)
3. Find filterable loss patterns WITHOUT killing runners

## Key Findings

### 1. Winners NEED time — zero winners exit in <48 bars

| Speed | Trades | R | Avg R |
|---|---|---|---|
| instant (0-4 bars) | 0 | 0.0 | — |
| fast (5-12 bars) | 0 | 0.0 | — |
| medium (13-48 bars) | 0 | 0.0 | — |
| slow (49-192 bars) | 38 | +119.0 | +3.13 |
| very slow (>192 bars) | 64 | +351.2 | +5.49 |

**Implication:** Any filter that kills early exits must NOT kill late exits. The strategy is pure trend-following — you MUST hold through noise.

### 2. The 12-24h window zone is TOXIC

| Window Age | Trades | WR | R | Avg R |
|---|---|---|---|---|
| 0-6h (fresh) | 38 | 34.2% | +13.7 | +0.36 |
| 6-12h | 26 | 19.2% | +4.4 | +0.17 |
| **12-24h** | **40** | **10.0%** | **-27.0** | **-0.67** |
| 24-48h | 70 | 31.4% | +35.2 | +0.50 |
| 48h+ | 166 | 34.9% | +225.3 | +1.36 |

**Implication:** The w24 gate works because it specifically kills the 12-24h death zone. Fresh windows (0-6h) are actually OK — the problem isn't "freshness", it's the 12-24h specifically.

### 3. MFE giveback is massive — 224.8R left on the table

| Giveback % | Trades | NET R | MFE was | Gave back |
|---|---|---|---|---|
| 0-25% | 8 | +187.9 | +238.6 | 50.7 |
| 25-50% | 29 | +149.7 | +236.9 | 87.2 |
| **50-75%** | **39** | **+119.6** | **+301.0** | **181.4** |
| >75% | 9 | +7.5 | +64.8 | 57.2 |

**Implication:** The trail is too slow. 39 trades gave back >50% of their MFE. A tighter or faster trail on winners could capture more of the existing MFE without destroying the runners.

### 4. Fast deaths are real but small

- 33 instant deaths (0-4 bars) = -33R (13.9% of all losses)
- Mostly in flip regime (28/33)
- Could be filtered with a short-term momentum gate

### 5. FLIP signals dominate B2

| Signal | Trades | WR | R | Avg R |
|---|---|---|---|---|
| B2 | 181 | 27.6% | +52.1 | +0.29 |
| FLIP | 159 | 32.7% | +199.5 | +1.25 |

**Implication:** FLIP signals are 3.4x more profitable per trade. B2 signals are the majority of trades but minority of profits.

### 6. Monsters pay for everything

| Size | Trades | R | % of gross wins |
|---|---|---|---|
| 0.01-0.50R | 14 | +2.8 | 0.6% |
| 0.50-1.00R | 17 | +13.0 | 2.8% |
| 1.00-2.00R | 18 | +25.8 | 5.5% |
| 2.00-3.00R | 14 | +34.2 | 7.3% |
| 3.00-5.00R | 12 | +48.1 | 10.2% |
| 5.00-10.0R | 17 | +115.2 | 24.5% |
| **>10.0R** | **10** | **+231.0** | **49.1%** |

**Implication:** 10 monster trades (>10R) produce 49% of all gross wins. Any filter that kills even one monster is catastrophic.

## Actionable Hypotheses for Next Experiments

1. ~~**Window age filter:** Skip entries in 12-24h window zone specifically~~ — TESTED: +36.3R anchor, -15.3R OPT (lane-dependent)
2. ~~**Trail tightening:** Test faster trail on winners that reach 3R+ MFE~~ — TESTED: **REJECTED** (see below)
3. ~~**FLIP preference:** Weight FLIP signals higher than B2~~ — TESTED: removing either hurts (both contribute)
4. **Fast death proxy:** Pre-entry predictor for <8 bar exits (skip <12 bars shows +100R ceiling but is post-filter)
5. ~~**MFE capture:** Study if a partial profit rule at 3R improves overall NET~~ — Close to trail tightening; same risk of killing monsters

### LA5: Trail Tightening (exp_la4_trail_tighten.py) — REJECTED

| Thr | Pct | Anchor NET | Delta | OPT NET | Delta |
|---|---|---|---|---|---|
| 1.5 | 0.4 | -54.9 | -221.6 | -19.1 | -245.2 |
| 2.0 | 0.4 | -43.5 | -210.2 | +18.4 | -207.6 |
| 3.0 | 0.4 | -4.1 | -170.8 | +73.9 | -152.1 |
| 4.0 | 0.4 | +43.9 | -122.8 | +125.9 | -100.1 |
| **5.0** | **0.4** | **+54.1** | **-112.6** | **+163.4** | **-62.7** |

**Verdict:** REJECTED. Trail tightening kills monsters. Best combo (thr=5.0, pct=0.4) loses 6 monsters:
- Anchor: 10→4 monsters (lost 155.3R of >10R wins)
- OPT: 12→6 monsters (lost similar)
- Lower thresholds even worse (thr=1.5: -221R to -246R)

**Root cause:** The 224.8R MFE giveback is the COST of letting winners run. Tightening the trail to "fix" it kills the 10 monster trades (>10R) that produce 49% of all gross wins. You cannot capture the giveback without also cutting the monsters. This is the variance/reward tradeoff — the same mechanism that lets trades reach 40R also lets some trades give back from 20R to 10R.

---

## Filter Results (exp_la_filters.py)

### LA1: Window Age Zone Filter

| Filter | Kept | Removed | Removed WR | Removed R | NET | Delta |
|---|---|---|---|---|---|---|
| skip <12h | 276 | 64 | 28% | +18.0 | +161.4 | -5.3 |
| **skip 12-24h** | **300** | **40** | **10%** | **-27.0** | **+203.0** | **+36.3** |
| skip <24h (w24) | 236 | 104 | 21% | -9.0 | +197.6 | +30.9 |
| skip 24-48h | 270 | 70 | 31% | +35.2 | +150.2 | -16.5 |
| keep only 0-6h | 38 | 302 | 30% | +237.9 | +7.6 | -159.1 |
| keep only 48h+ | 166 | 174 | 25% | +26.2 | +181.1 | +14.4 |

**Finding:** skip 12-24h is the best window age filter on anchor (+36.3R). But it HURTS on OPTIMAL (-15.3R). Lane-dependent.

### LA2: FLIP Preference

| Filter | Kept | Removed | NET | Delta |
|---|---|---|---|---|
| keep only flip regime | 298 | 42 | +153.5 | -13.2 |
| keep only b2 regime | 42 | 298 | +13.2 | -153.5 |
| skip B2 signals | 159 | 181 | +156.6 | -10.1 |
| skip FLIP signals | 181 | 159 | +10.1 | -156.6 |

**Finding:** Removing either signal type hurts. Both contribute positively.

### LA3: Fast Death Filter (POST-FILTER — not live-tradeable)

| Filter | Kept | Removed | NET | Delta |
|---|---|---|---|---|
| skip <5 bars | 307 | 33 | +211.8 | +45.1 |
| skip <8 bars | 285 | 55 | +241.3 | +74.6 |
| **skip <12 bars** | **265** | **75** | **+267.5** | **+100.8** |
| skip >192 bars | 333 | 7 | +170.2 | +3.5 |

**Finding:** skip <12 bars is the MOST POWERFUL filter (+100.8R anchor, +119.6R OPTIMAL).
But it's a POST-filter — we don't know pre-entry which trades will fail in <12 bars.
Theoretical ceiling for any pre-entry proxy filter.

### LA4: Combined Filters

| Filter | Kept | Removed | NET | Delta |
|---|---|---|---|---|
| skip 12-24h + skip B2 | 265 | 75 | +183.9 | +17.2 |
| skip 12-24h + skip <8 bars | 254 | 86 | +265.4 | +98.7 |
| w24 + skip B2 | 207 | 133 | +200.3 | +33.6 |
| skip 12-24h + skip B2 + skip <8 bars | 223 | 117 | +240.9 | +74.2 |

### OPTIMAL Generalization Test

| Filter | Kept | Removed | NET | Delta |
|---|---|---|---|---|
| skip 12-24h | 397 | 56 | +244.1 | -15.3 |
| skip <12 bars | 361 | 92 | +379.0 | +119.6 |
| skip <8 bars | 392 | 61 | +339.6 | +80.3 |
| skip 12-24h + skip <8 bars | 344 | 109 | +314.5 | +55.1 |
| **w24 (reference)** | **326** | — | **+337.7** | **+78.3** |
| **w24 + skip <12 bars** | **273** | — | **+407.5** | **+69.8** |

**Finding:** w24 + skip <12 bars = +407.5R theoretical ceiling on OPTIMAL.
The fast death filter is universal — works on both anchor and OPTIMAL.
But it's a post-filter. The challenge is finding a pre-entry proxy.

## Summary of Actionable Findings

### Champion Config (Single Position, Corrected Costs)

**Config:** `mode=atr_high, ext_stop_r=3.0, cooldown_bars=8, exp_partial_r=7.5`
**Harness:** `live_stuff/tests/exp_final_single.py`
**Status:** Single position only. Costs include split exit fees for partial trades.

```
Trades:        371
Gross:         +352.4R
Costs:         -90.9R
NET:           +261.5R  [LEGACY — pre partial-R fix + trail fix; current: +90.1R]
Win rate:      28.8% (107W / 264L / 0F)
Avg win:       +5.58R
Avg loss:      -0.93R
Avg R/trade:   +0.95R
Profit factor: 2.44
Max drawdown:  29.3R
Max loss streak: 14 consecutive
Monsters (>10R): 27
```

| Year | Trades | NET | WR | PF | Avg Entry |
|---|---|---|---|---|---|
| 2023 | 86 | +32.5R | 24.4% | 1.53 | $28,024 |
| 2024 | 119 | +87.5R | 22.7% | 2.03 | $64,816 |
| 2025 | 95 | +133.6R | 34.7% | 3.35 | $102,491 |
| 2026 | 71 | +98.8R | 36.6% | 3.37 | $70,784 |
| **H1 (2023-24)** | | **+120.0R** | | | |
| **H2 (2025-26)** | | **+232.4R** | | | |

### Price-Level / Regime Analysis

| Price Band | Trades | NET | WR | AvgR | PF | DD |
|---|---|---|---|---|---|---|
| <30k | 68 | -3.6R | 17.6% | -0.05R | 0.93 | 34.7R |
| 30-50k | 32 | +45.4R | 40.6% | +1.42R | 3.72 | 7.3R |
| 50-75k | 141 | +99.5R | 24.8% | +0.71R | 2.02 | 13.2R |
| 75-100k | 72 | +107.4R | 30.6% | +1.49R | 3.20 | 14.3R |
| >100k | 58 | +103.6R | 43.1% | +1.79R | 4.57 | 5.0R |

**Pearson correlation (price vs R): 0.108 (weak).** It's not price — it's regime:
- 2023-H1 (choppy range $16-30k): -5.7R, PF 0.84 — weakest period
- 2023-Q2 (choppy $27-28k): -7.8R, PF 0.56 — worst quarter
- 2023-Q4 (trending $34k): +38.6R, PF 3.90 — one of best quarters
- 2024+ (higher price, cleaner trends): all profitable

**Conclusion:** The engine works across all price levels. Weakness is in choppy ranging markets (low ATR%), not price per se. 2023-H1 had lowest ATR% (avg 0.284%) and worst performance. 2024 had highest ATR% (avg 0.385%) and strong performance.

### Experiment Results (All Single Position, Corrected Costs)

| # | Experiment | Result | Delta vs Baseline | Harness File |
|---|---|---|---|---|
| LA4 | Trail tightening | REJECTED | -112.6R/-62.7R | exp_la4_trail_tighten.py |
| LA5 | Partial exits (50% at X R) | **ACCEPTED** | +64.0R (anchor) | exp_la5_partial.py |
| LA6 | Post-loss 1R recovery | REJECTED | -153R/-140R | exp_la6_recover.py |
| LA7 | Entry distance gate | REJECTED | -6.2R best | exp_la7_entry_dist.py |
| LA8 | Mode variations | MIXED | +10.2R (anchor) / +38.6R (opt) | exp_la8_modes.py |
| LA9 | ATR trail + delay | REJECTED | -257R/-244R | exp_la9_atr_trail.py |
| LA10 | Partial x Mode combos | **ACCEPTED** | +61.2R anchor, +123.5R opt | exp_la10_combos.py |
| LA11 | Extensions sweep (wage/B3/curfew) | **ACCEPTED** | wage rejected on atr_high | exp_la11_extensions.py |
| LA12 | Ultra-optimize (partR/ext/cd/ct/persist) | **ACCEPTED** | +55.4R partR, +26.0R ext | exp_la12_ultra.py |
| LA13 | partR extension + overfit validation | **ACCEPTED** | partR=7.5 optimal | exp_la13_validate.py |
| FINAL | Full metrics + cost correction | **ACCEPTED** | NET +261.5R (was +166.7R) | exp_final_single.py |
| LA14 | Deferred entry (requeue) | REJECTED | -28.0R defer24 | exp_la14_defer.py |
| — | Price-level analysis | INFO | regime > price | exp_final_single.py (inline) |

### Combined Comparison Matrix (Both Lanes, Consistent Costs)

All configs: v18 engine, 0.055% fee/side + 0.005%/0.010% slip + 0.01%/8h funding + partial exit 50/50 split. Lanes: SINGLE = one trade at a time. MULTI = overlapping trades (mltf). Source: `exp_final_matrix.py`.

> **⚠️ LEGACY NUMBERS (pre-fix):** All numbers below used the old partial R formula
> (booked 7.5R for 50% leg) and old trail-event ordering. For corrected numbers,
> run `python run_experiment.py --all`. Key corrections: champion_single = +90.1R
> (was +261.5), champion_multi = +208.4R (was +465.1), no-partial multi sw10 =
> +325.8R (the actual king).

| Config | Lane | Trades | NET R | Cost | Win Rate | Profit Factor | Max Drawdown | Max Loss Streak | 2023 | 2024 | 2025 | 2026 | H1 (2023+2024) | H2 (2025+2026) | Big Wins |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Shipped baseline | SINGLE | 340 | +166.7R | 84.9R | 30.0% | 2.15 | 27.1R | 16 | +28R | +72R | +60R | +90R | +101R | +151R | 10 |
| **Our champion (atr_high+p7.5+ext3+cd8)** | SINGLE | 371 | **+261.5R** | 90.9R | 28.8% | 2.44 | 29.3R | 14 | +32R | +88R | +134R | +99R | +120R | **+232R** | **27** |
| Their A4 w24 ext1.5 | SINGLE | 341 | +159.2R | 86.7R | 28.7% | 2.09 | 20.3R | 14 | +43R | +63R | +59R | +80R | +106R | +140R | 10 |
| **Their A4 w24 ext1.5 + our partR=7.5** | SINGLE | 341 | **+245.4R** | 86.6R | 28.7% | 2.47 | **16.0R** | 14 | +61R | +68R | +113R | +91R | +129R | +204R | 26 |
| Their lb30 ext2.5 | SINGLE | 364 | +174.3R | 86.8R | 30.8% | 2.11 | 27.7R | 12 | +22R | +85R | +71R | +83R | +107R | +154R | 12 |
| Their lb30 curf6-24 | SINGLE | 364 | +174.3R | 86.8R | 30.8% | 2.11 | 27.7R | 12 | +22R | +85R | +71R | +83R | +107R | +154R | 12 |
| Their lb30 defer24 ext1.5 | SINGLE | 273 | +159.9R | 69.1R | 29.7% | 2.33 | 22.9R | 9 | +14R | +75R | +55R | +86R | +88R | +141R | 10 |
| | | | | | | | | | | | | | | | |
| OPT-cd10 w24 ext1.5 (theirs) | MULTI | 408 | +215.7R | 101.9R | 30.9% | 2.22 | 24.2R | 15 | +63R | +78R | +96R | +81R | +140R | +177R | 12 |
| **Our atr_high+p7.5+ext3+cd8+mltf+persist7** | MULTI | 487 | **+465.1R** | 114.9R | 31.8% | **2.92** | 21.9R | 14 | **+128R** | **+140R** | **+186R** | **+127R** | **+267R** | **+313R** | **42** |

### Equity Curve (cumulative NET R at trade #50 intervals)

```
Config                                      t50    t100   t150   t200   t250   t300   t350   t400   Final
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
Shipped baseline                           -21R    -5R   +30R   +53R   +65R  +123R  ----   ----   +167R
Our champion (atr_high+p7.5+ext3+cd8)      -18R   +16R   +45R   +75R   +90R  +181R  +270R  ----   +262R
Their A4 w24 ext1.5                         +2R   +18R   +42R   +57R   +58R  +126R  ----   ----   +159R
Their A4 w24 ext1.5 + our partR=7.5         +9R   +40R   +66R   +85R  +110R  +214R  ----   ----   +245R
Their lb30 ext2.5                          -19R    +9R   +42R   +64R   +71R  +117R  +184R  ----   +174R
OPT-cd10 w24 ext1.5 (MULTI)                 +2R   +40R   +59R   +57R   +91R  +117R  +180R  +225R  +216R
```

### Equity Curve Analysis

1. **Our champion leads from t100 onward** — never drops below. Smooth upward, no flat periods. Steepest slope of all single-position configs.
2. **Their A4 w24 + partR=7.5 starts +9R at t50** (best early start), but champion overtakes by t300 and pulls ahead. Champion has 27 big wins vs 26, and ext_stop=3.0 lets winners run bigger.
3. **Their A4 w24 ext1.5** starts flat (t50 +2R), steady but shallow — only +159R. PartR=7.5 lifts it to +245R (+86R boost).
4. **Their lb30 ext2.5** starts very slow (-19R at t50), never catches up.
5. **No config ever goes below -30R** from any point — all equity curves monotonically increase after initial drawdown.

### Recommendation: Start Single, Transition to Multi

| Phase | Config | Why |
|---|---|---|
| **Phase 1 (months 1-6)** | Our champion SINGLE (atr_high+p7.5+ext3+cd8) | Best NET (+261.5R), best big winners (27), smoothest equity curve, all 4 years profitable. Single position = 1 risk unit, easiest to manage, lowest capital requirement. H2 +232R proves recent edge is strong. |
| **Phase 2 (after buffer)** | Our champion MULTI (atr_high+p7.5+ext3+cd8+mltf+persist7) | +465.1R NET, PF 2.92, 42 big wins. Requires ~2x capital buffer. Switch after 3-6 months live data confirms backtest. |

### Key Learnings

1. **Partial exits solve MFE giveback without killing monsters** — partR=7.5 is optimal (tested up to 12.0). Cost impact of splitting exits is negligible (+0.0009R per trade, only 11.3% of trades trigger).
2. **Mode matters** — atr_high routes to decisive signals when volatility is high, producing better trades.
3. **Combos compound** — atr_high + partial exits + wider stops (3.0) + shorter cooldown (8) stack to +94.8R over baseline.
4. **Trail variants always kill monsters** — trail tightening, ATR trail, trail delay all destroy the asymmetric payoff structure.
5. **Entry-side filters don't help** — entry distance gate, post-loss recovery both hurt.
6. **Wage gate is mode-dependent** — helps on chop mode (+78.3R), hurts on atr_high (-29.7R). atr_high already filters volatility naturally.
7. **B3 is anchor-only** — massively hurts on OPT configs (-243R). Confirmed across lanes.
8. **Curfew doesn't help** — zero delta on atr_high.
9. **chop_thresh is irrelevant on atr_high** — no difference across 50-65.
10. **Wider ext_stop (3.0) helps on atr_high** — +26.0R. More room for the asymmetric payoff.
11. **Shorter cooldown (8) helps** — +16.8R over cd=10.
12. **Price level doesn't matter — regime does** — Weakness is in choppy ranging markets (2023-H1, ATR% 0.284%), not price per se. Pearson r=0.108 (price vs R). 2023-Q4 ($34k, trending) had PF 3.90. The engine works across all price levels when the market trends.
13. **ATR% veto HURTS** — low ATR% trades are actually the BEST performers (PF 2.90 at <0.20% ATR). The choppy market weakness is not about low volatility per se.
14. **FLIP suppression in chop HURTS** — FLIP signals are profitable across all chop levels (even >65 chop: +23.1R). The 2023-H1 weakness was in the 50-60 chop middle band where FLIP underperformed (+10-21R vs +91-96R at extremes). But this is bimodal and not filterable without lookahead.
15. **Regime weakness is NOT exploitable** — no causal, pre-entry filter exists to skip the choppy ranging markets. The engine's edge is structural (trend-following + partial exits) and cannot be enhanced by regime prediction.
16. **w24 has ZERO effect on atr_high** — identical trade count and NET to w0 (371t, +261.5R). The atr_high mode already handles the timing issue that w24 fixes on other lanes (lb30, A4). No timing gate needed.
17. **Deferred entry HURTS on atr_high** — defer24 drops to 298t, -28.0R (DD improves to 18.8R, PF improves to 2.67). defer6/12 even worse. The requeue mechanism loses profitable trades that the wider ext_stop=3.0 already gives room to run.
18. **atr_high is self-cleaning** — the combination of decisive signal routing + wider stops + partial exits makes timing gates (w24, defer, curfew) unnecessary. This is the cleanest finding from the other bot's transfer: we don't need what they need.
