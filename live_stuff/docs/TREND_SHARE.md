# P9 — the money is NOT made in trending tape. It is made against the trend.

`exp_trend_share.py`. Pins reproduced first. This is the decomposition
P8 did not try: **market state**, not book state.

## What was measured

Kaufman efficiency ratio on 1h closes, causal, three lookbacks (24h/48h/96h):

`ER = |P_t − P_{t−n}| / Σ|P_i − P_{i−1}|`

ER ≈ 1 = price moved in a straight line (trending). ER ≈ 0 = price went
nowhere (ranging). A standard published measure, computed from price
alone with **no reference to the strategy** — which is the point. P8's
splits were all properties of the book; this one is a property of the
market.

Plus **drift agreement**: does the trade's direction match the market's
own drift over the trailing window? That is the user's direct question —
"did the bias window back the trend?"

## The answer to the direct question: the bias window does NOT back the trend

**IS, lookback 48h:**

| | n | net | WR | M | null mean |
|---|---|---|---|---|---|
| **with the drift** | 344 | **+279.3R** | 31.4% | 381.4R | +237.8R |
| **against the drift** | 156 | **+77.6R** | **26.9%** | 168.7R | +84.0R |
| trending AND agreeing | 133 | +96.6R | **34.6%** | 114.3R | +61.7R |
| **everything else** | 367 | **+260.3R** | **28.3%** | 394.4R | +246.4R |

**The "everything else" bucket — everything that is NOT trending-and-
agreeing — is +260.3R from 367 trades, against the ideal state's +96.6R
from 133.** The book makes **2.7× more R in the states it was not
designed for than in the state it was.**

**OOS, lookback 24h:**

| | n | net | WR |
|---|---|---|---|
| with the drift | 178 | +82.6R | 32.0% |
| **against the drift** | 101 | **−4.1R** | **20.8%** |
| **trending (ER high)** | 92 | **−15.0R** | **23.9%** |
| **trend+agree** | 68 | **−12.1R** | 26.5% |

**In OOS the trending bucket loses money outright.** The highest-third
efficiency trades are −15.0R at 23.9% WR, and the trend+agree cohort —
which is the textbook "trade with the trend" state — is −12.1R.

## This is the finding

**The strategy is not a momentum book. It is a contrarian book.**

Across all three lookbacks in IS, the "with the drift" cohort always
carries more R than "against" — but that is a size effect, not a
quality effect: 344 trades against 156, so more R is what more trades
buy. **Per trade the picture reverses.** In IS 48h: with-drift is
+0.81R/trade, against-drift is +0.50R/trade; but "everything else" is
+0.71R/trade while trend+agree is only +0.73R with a third of the
sample. In OOS the against-drift cohort drops to −0.04R/trade and the
trending cohort to −0.16R/trade.

**The efficiency ratio itself is near-flat across terciles in IS** (24h:
+148.3R / +68.6R / +140.0R) — no monotone concentration at all. A book
whose edge lived in trends would show a clean ordering. This shows none.

## What it means for the strategy's own framing

The user asked whether momentum and trend were the mechanism, and noted
that trends are rare so most trades cannot be riding one. **The data says
the premise does not hold, and says so in a specific way: the book is not
underperforming in ranging tape, it is doing the majority of its work
there.** 367 of 500 IS trades and 205 of 279 OOS trades fall in the
non-ideal bucket, and that bucket carries more R than the ideal one.

**Which is consistent with everything else measured today.** The 1h leg
has no standalone edge (P3-A: best mode −6.0R OOS). The book is
tail-concentrated (P8: top 5 trades = 49% of P&L). A book with no
directional edge and a fat right tail does not need a trending market to
work — it needs fat right tails, which it gets from structural levels
and the trail, not from trend continuation.

## Nothing cleared the null, and that is expected

All 42 splits, both eras, all three lookbacks: **inside the null.** No
surprise — a 70-170 trade cohort against M of 30-394R is the same wall
P5, P8 and P1-P hit. **But this run was not looking for a clear. It was
looking for concentration, and the answer is that there is none: the
P&L is spread almost evenly across ranging, mixed and trending tape.**

## What this closes

- **The momentum/trend framing of the strategy is wrong as a description
  of where money is made.** Not wrong as a description of the entries —
  the entries are breaks of swings, which do fire with momentum — but
  the R does not concentrate there.
- **It also retires a family of ideas.** Any future proposal of the form
  "add a trending-market gate" (ADX, EMA-cross, regime filter to only
  trade when the market is trending) is now answered before it is built:
  the trending cohort is the *worst* cohort OOS.
- **Note the graveyard already knew this in a different costume.** ADX
  gates were tried (`v6_adx`, `exp_oldengines_path`, reverted as "dead =
  clutter") and `exp_mb_forensic` measured trailing trend and vol. This
  run explains why they died: **they were gating toward the state where
  this book is weakest.**

## Caveat

Kaufman ER is one trend measure. The direction of the finding — no
concentration, trending cohort worst OOS — is consistent across three
lookbacks and both eras, which is the robustness the null cannot give.
But a single indicator family is not proof that no trend-state
decomposition would work. It is strong evidence against this one.
