# Startup risk, calendar-year returns, and a rolling-weighted ranking

**Run 2026-10-10. `exp_startup_yearly.py` → `_startup_yearly.json`. All 35
registered fsent books with pins — not a top-N slice, because the new arms changed
the count and the owner asked for every contender in both families.**

Three questions this answers that nothing else here did.

---

# PART 1 — "If I deploy today, how bad can it get?"

The owner's understanding was correct, and it exposed that the answer had been
given in the wrong units.

> "29.62% is the worst thing that can happen. We should be prepared for it."

**That is not what happens.** That is maximum drawdown, measured from a running
peak the book may not reach until trade 200. What a new deployer feels is the dip
below where they **started**, before the book has ever printed a profit. Those are
different numbers, and the second is the one that decides whether you switch the
thing off in week three.

## Startup drawdown — the deepest the account goes below zero before its first new high

| book | **startup DD** | at trade | **% @1% risk** | ₹ on ₹5 lakh | first +50 trades | trades to first profit |
|---|---:|---:|---:|---:|---:|---:|
| `utcsat_short` | 11.37R | 68 | **11.37%** | ₹56,850 | +1.13 | 1 |
| `champ_short` | 10.61R | 68 | **10.61%** | ₹53,050 | +1.90 | 1 |
| `mode_union` | 5.06R | 14 | **5.06%** | ₹25,300 | +11.54 | 17 |
| `sig_sw10_long` | 4.76R | 11 | 4.76% | ₹23,800 | +12.11 | 2 |
| `both_trail_half` | 3.32R | 49 | 3.32% | ₹16,600 | −0.48 | 1 |
| `htfesmcl4` | 3.31R | 15 | 3.31% | ₹16,550 | +15.19 | 2 |
| `sig_sw10_short` | 2.75R | 35 | 2.75% | ₹13,750 | +6.42 | 1 |
| `sig_sw20_short` | 2.22R | 13 | 2.22% | ₹11,100 | +13.78 | 1 |
| `mode_atr_low` / `mode_chop` / `mode_fd` / `flip_quality` | 1.87R | 6 | 1.87% | ₹9,350 | +37.40 | 2 |
| `champ_trailhalf` / `utcsat_trailhalf` | 1.66R | 16 | 1.66% | ₹8,300 | +48.48 | 3 |
| `htf15_htffs` | 1.05R | 1 | **1.05%** | ₹5,250 | +15.96 | 2 |
| **`htffs`** | 1.05R | 1 | **1.05%** | ₹5,250 | +10.62 | 2 |
| **`champ_long`** ⭐ shipping | 1.01R | 1 | **1.01%** | ₹5,050 | +15.31 | 2 |
| **`mcloff`** / `nohalt` / `causalfloor` / `htf15` / `mcloff_htf15` / `utcsat_long` / `biasmom05` | 1.01R | 1 | **1.01%** | ₹5,050 | +7.15 to +29.95 | 2 |
| `sig_half_crossed` | 0.70R | 4 | **0.70%** | ₹3,500 | +84.97 | 1 |
| **`sig_multi` / `sig_full` / `sig_multi_htffs` / `sig_trail_delay1` / `sig_fs_mom` / `sig_decay_crossed` / `sig_wk_pause_short`** | **0.00R** | 0 | **0.00%** | **₹0** | +40.07 to +81.13 | **1** |

## The three numbers, and which one is the worst case

| | shipping book | what it means |
|---|---|---|
| **startup DD** | **1.01%** | ₹5,050. The dip below where you put the money in. **This is the "deploy today" worst case.** |
| **max DD** | **13.42%** | ₹67,100. The deepest fall from any peak — and it happens *later*, once the book is already up. |
| **worst 50-trade window** | **−8.3R** | −8.3% at 1% risk. What a mid-life bad patch looks like. |

**The owner's fear — going live and immediately seeing ₹4-5 thousand of loss
without a single profit — is roughly what the startup number actually is: ₹5,050
for the shipping book, and ₹0 for the entire sig family.**

**And it is not rare in the way feared.** Every book here hit its startup drawdown
at trade 1 to 68. For the shipping book it is trade 1. But the *depth* is 1.01%,
not 13.42%, because the maximum drawdown happens after the book has already
accumulated equity — which is exactly the difference between the two metrics.

**The honest worst case for the shipping book, expressed as rupees on ₹5 lakh at
1% risk per trade:**

| | |
|---|---|
| worst moment right after starting | **−₹5,050 (−1.01%)** |
| first 50 trades together | **+₹76,550 (+15.31R)** |
| worst 50-trade stretch later in life | −₹41,500 (−8.3R) |
| worst peak-to-trough at any point | −₹67,100 (−13.42%) |

---

# PART 2 — The "45% returns with 3% drawdown" claim

## First: why the claim is not yet comparable

> "It just says 45%."

**45% of what period?** 45% in a month is 540% a year. 45% a year is a different
animal entirely. The website states a number without a period, which makes it
impossible to evaluate as stated. That is not scepticism about the seller — it is
that the figure does not carry the information needed to compare it to anything.

## Second: what our books actually do per calendar year

R per year. At 1% risk per trade, **1R = 1% of the account**, so the R column is
also the account percent. 2026 is partial (8.4 months).

| book | net | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---:|---:|---:|---:|---:|---:|---:|
| `htfesmcl4` | 1244 | 144 | 182 | 294 | 289 | 147 | 188 |
| `htf15_htffs` | 1230 | 124 | 180 | **307** | **315** | 152 | 152 |
| `htffs` | 1198 | 122 | 178 | **324** | **292** | 129 | 153 |
| `mode_atr_low` | 1002 | 98 | 182 | 235 | 204 | 91 | 191 |
| **`sig_multi_htffs`** | 901 | 132 | 102 | 245 | 264 | 85 | 72 |
| `mcloff_htf15` | 894 | 98 | 180 | 179 | 133 | 179 | 124 |
| `champ_short` | 840 | 33 | 206 | 190 | 124 | 162 | 125 |
| **`mcloff`** | 838 | 91 | 180 | 185 | 115 | 144 | 123 |
| `htf15` | 822 | 87 | 168 | 154 | 126 | 176 | 111 |
| `causalfloor` | 779 | 78 | 171 | 163 | 116 | 143 | 108 |
| **`champ_long`** ⭐ | 773 | 78 | 161 | 172 | 114 | 138 | 109 |
| **`sig_multi`** | 704 | 80 | 139 | 140 | 141 | 106 | 98 |
| `sig_trail_delay1` | 601 | 61 | 121 | 236 | 103 | 47 | 32 |
| **`sig_full`** | 490 | 75 | 119 | 92 | 114 | 55 | 35 |
| `sig_half_crossed` | 483 | 49 | 93 | 178 | 97 | 36 | 30 |

**On raw annual percentage, our books are far ahead of the claim** — the shipping
book averages **about 135% a year at 1% risk**, and `htffs` reached **324% in
2023 alone**.

## Third: and that is exactly the wrong comparison

A 45% return with a 3% drawdown implies **very small position sizing**. Scale a
strategy down and the return falls in the same proportion as the drawdown — so the
number that actually distinguishes the two is **return divided by drawdown**.

| | annual return | max DD | **ratio** |
|---|---:|---:|---:|
| the website's claim | 45% | 3% | **15.0** |
| `sig_half_crossed` | ~91% | 8.46% | **10.7** |
| `champ_long` ⭐ | ~135% | 13.42% | 10.1 |
| `htffs` | ~190% | 19.78% | 9.6 |
| `mcloff` | ~143% | 15.13% | 9.4 |
| `sig_multi` | ~121% | 13.39% | 9.1 |
| `sig_full` | ~81% | 10.78% | 7.5 |

**The claim's ratio of 15.0 is better than anything we have.**

That is stated plainly because it is the honest reading and it cuts against our
own books. Three things about it, though:

1. **A 3% maximum drawdown over multiple years is extremely unusual.** If the
   largest peak-to-trough fall in the whole track record is 3%, then no stretch of
   that record was ever painful. Our books have been between −8% and −13% at
   their worst, and every book here spends most of its life underwater.
2. **No period is attached**, so it cannot be checked against the table above.
3. **The number is self-reported.** It has not been reproduced by anything we can
   run, and this project has spent a cycle establishing that a headline return is
   not the same as an edge.

**A fair conclusion:** on the metric that matters, the claim is stronger than
anything measured here, and it should be treated as a claim until a track record
with dates, drawdown and period is produced. It is not a reason to change our
books — our books are the ones we can reproduce.

---

# PART 3 — Rolling-weighted ranking

The owner's instruction: **rolling windows should be weighted above simply being
profitable.** Encoded as:

```
roll10 .30   roll20 .30   roll50 .25   roll100 .15
half-years .60   years .40   tail spread .30
```

**Net is deliberately not scored** — it is already inside the half-year and
rolling measures, and scoring it again would just reward taking more trades. **The
null is a gate, not a score**: a p-value cannot be scaled against an R/trade
number, and pretending otherwise hides the one metric that does not trade off
against anything.

| # | book | **SCORE** | roll10 | roll20 | **roll50** | roll100 | neg halves | neg years | p IS / p OOS |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **`sig_multi`** | **200.3** | 84.8% | 98.2% | **100%** | 100% | **0** | 0 | 0.9283 / 0.9138 |
| 2 | `sig_decay_crossed` | 199.3 | 92.0% | 99.3% | 100% | 100% | 1 | 0 | 0.9215 / 0.9823 |
| 3 | **`sig_multi_htffs`** | **199.1** | 79.2% | 93.1% | **100%** | 100% | **0** | 0 | 0.5091 / 0.9708 |
| 4 | **`sig_full`** | **198.8** | 85.6% | 97.0% | **100%** | 100% | **0** | 0 | 0.7428 / 0.9223 |
| 5 | `sig_half_crossed` | 197.4 | 90.0% | **100%** | 100% | 100% | 1 | 0 | 0.9878 / 0.9923 |
| 6 | `sig_fs_mom` | 193.0 | 74.9% | 94.0% | 100% | 100% | **0** | 0 | 0.6476 / 0.7991 |
| 7 | `sig_trail_delay1` | 191.3 | 82.7% | 95.0% | 100% | 100% | 1 | 0 | 0.9398 / 0.9330 |
| 8 | `sig_wk_pause_short` | 189.7 | 73.4% | 92.3% | 100% | 100% | **0** | 0 | 0.1367 / 0.4414 |
| 9 | **`mcloff_htf15`** | **188.8** | 68.0% | 81.5% | 98.6% | 100% | **0** | 0 | **0.0115** / 0.1445 |
| 10 | **`htf15`** | **186.7** | 65.6% | 80.8% | 95.9% | 100% | **0** | 0 | 0.1927 / 0.5021 |
| 11 | `causalfloor` | 186.5 | 65.8% | 80.3% | 98.8% | 100% | **0** | 0 | 0.7256 / **0.0230** |
| 12 | `biasmom05` | 186.1 | 65.9% | 81.6% | 97.5% | 100% | **0** | 0 | — |
| 13 | **`mcloff`** / `nohalt` | **185.1** | 66.2% | 78.2% | 96.8% | 100% | **0** | 0 | **0.0312 / 0.0117** |
| 14 | `sig_sw10_short` | 184.5 | 70.5% | 79.9% | 97.7% | 100% | **0** | 0 | 0.0267 / 0.1137 |
| 15 | `htfesmcl4` | 183.2 | 65.2% | 76.6% | 90.2% | 95.8% | **0** | 0 | 0.0285 / 0.5311 |
| 16 | `mode_atr_low` | 182.9 | 67.4% | 76.6% | 88.2% | 96.7% | **0** | 0 | 0.1045 / 0.0987 |
| 17 | `champ_short` | 181.7 | 67.9% | 75.9% | 94.1% | 100% | **0** | 0 | 0.6888 / 0.9993 |
| 18 | **`champ_long`** ⭐ | **180.1** | 66.0% | 79.5% | 97.7% | 99.7% | 1 | 0 | — (is the parent) |
| 19 | `champ_trailhalf` | 179.9 | 61.9% | 73.9% | 93.0% | 99.1% | **0** | 0 | 0.9378 / 0.4974 |
| 20 | `htf15_htffs` | 179.4 | 67.1% | 78.1% | 90.4% | 95.6% | 1 | 0 | **0.0105** / 0.4904 |
| 21 | `htffs` | 177.8 | 64.0% | 76.1% | 92.8% | 98.6% | 1 | 0 | 0.0272 / 0.5956 |
| 22 | `mode_union` | 175.8 | 59.6% | 71.5% | 88.2% | 95.9% | **0** | 0 | 0.7276 / 0.2104 |
| 23 | `utcsat_short` | 174.7 | 66.8% | 72.1% | 94.1% | 99.5% | 1 | 0 | 0.7061 / 0.9180 |
| 24 | `sig_sw10_long` | 156.9 | 59.7% | 76.5% | 84.7% | 91.6% | 2 | **1** | — |
| 25 | `both_trail_half` | 144.9 | 53.0% | 65.1% | 81.7% | 89.2% | 3 | **1** | — |

---

# PART 4 — The shortlist: zero negative half-years **and** high rolling

The owner asked for books that pass **both** the half-year rule and the rolling
test, with rolling weighted more. These are all of them:

| book | score | roll50 | neg halves | neg years | p IS / p OOS | startup DD |
|---|---:|---:|---:|---:|---|---:|
| **`sig_multi`** | 200.3 | 100% | 0 | 0 | 0.9283 / 0.9138 | **0.00%** |
| **`sig_multi_htffs`** | 199.1 | 100% | 0 | 0 | 0.5091 / 0.9708 | **0.00%** |
| **`sig_full`** | 198.8 | 100% | 0 | 0 | 0.7428 / 0.9223 | **0.00%** |
| `sig_fs_mom` | 193.0 | 100% | 0 | 0 | 0.6476 / 0.7991 | **0.00%** |
| `sig_wk_pause_short` | 189.7 | 100% | 0 | 0 | 0.1367 / 0.4414 | **0.00%** |
| `mcloff_htf15` | 188.8 | 98.6% | 0 | 0 | **0.0115** / 0.1445 | 1.01% |
| `htf15` | 186.7 | 95.9% | 0 | 0 | 0.1927 / 0.5021 | 1.01% |
| `causalfloor` | 186.5 | 98.8% | 0 | 0 | 0.7256 / **0.0230** | 1.01% |
| `biasmom05` | 186.1 | 97.5% | 0 | 0 | — | 1.01% |
| **`mcloff`** | 185.1 | 96.8% | 0 | 0 | **0.0312 / 0.0117** | 1.01% |
| `sig_sw10_short` | 184.5 | 97.7% | 0 | 0 | 0.0267 / 0.1137 | 2.75% |
| `htfesmcl4` | 183.2 | 90.2% | 0 | 0 | 0.0285 / 0.5311 | 3.31% |
| `mode_atr_low` | 182.9 | 88.2% | 0 | 0 | 0.1045 / 0.0987 | 1.87% |
| `champ_short` | 181.7 | 94.1% | 0 | 0 | 0.6888 / 0.9993 | **10.61%** |
| `champ_trailhalf` | 179.9 | 93.0% | 0 | 0 | 0.9378 / 0.4974 | 1.66% |
| `mode_union` | 175.8 | 88.2% | 0 | 0 | 0.7276 / 0.2104 | 5.06% |

## The three that answer different questions

| question | answer | why |
|---|---|---|
| **most holdable** | **`sig_multi_htffs`** | 100% rolling-50 and rolling-100, zero negative half-years, zero negative years, **zero startup drawdown**, survives deleting its top 10% of trades at +85R |
| **only book with evidence of an edge** | **`mcloff`** | p 0.0312 / 0.0117 — the sole book significant in both eras |
| **highest in-sample evidence** | **`htf15_htffs`** | p 0.0105, but 90.4% rolling-50, one negative half-year, p 0.4904 out of sample |

**`sig_multi_htffs` and `mcloff` are not competitors.** They answer different
questions and the difference between them is the whole state of this project:

> **`sig_multi_htffs` behaves better. `mcloff` has shown more evidence of an edge.**
>
> Behaviour is measured and reproducible. Evidence of an edge is a p-value that
> has so far cleared in exactly one book.

## On the deploy-today question

**Nothing in this family is dangerous to start.** The worst startup drawdown in
all 35 books is 11.37% (`utcsat_short`), and for the shipping book it is
**1.01%** — ₹5,050 on a ₹5 lakh account, at trade 1, back to profit at trade 2.
Seven books including every leading sig candidate go **below zero never at all**.

The uncomfortable number is not the startup dip. It is that all 35 books spend
**most of their life underwater** and the worst peak-to-trough on the shipping
book is **13.42%**, which at 1% risk is ₹67,100 and takes about 49 trades and two
years of calendar time to make back.

## Reproduce

```
python backtest/tests/exp_startup_yearly.py
```

**Shipping book unchanged.**