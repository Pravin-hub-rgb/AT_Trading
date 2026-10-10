# Every metric used in this family, explained from zero

**Written 2026-10-10.** Four terms arrived in one answer without being defined —
R, expectancy, p, fixed effect — and the owner was right to stop and ask. This
document defines each one before it is used anywhere else, and states the basis
on which any book in this family is called good or bad.

Numbers throughout are from `exp_htffs_metrics.py` → `_htffs_metrics.json`.

---

## PART 1 — The money unit

### R (r-multiple)

We cannot measure profit in rupees or dollars, because position size and price
both move. So **everything is measured in R**, where:

> **1R = the amount you stand to lose if this trade's stop-loss is hit.**

If a trade risks ₹10,000:

| result | R |
|---|---:|
| stop hit | **−1.00R** |
| target hit at 3× the risk | **+3.00R** |
| closed at +₹5,000 with a ₹10,000 risk | **+0.50R** |

**Why this matters:** it makes every trade comparable. A ₹5,000 win on a ₹2,000
risk and a ₹25,000 win on a ₹50,000 risk are both **+2.5R**, even though the rupee
numbers differ by 10×.

### net

Add up every trade's R.

> `net = +533.37` means the book made **533 times its per-trade risk** over the
> whole period, compounding aside.

It is the headline number and it is the *worst* number to rank on, because it
grows when you simply take more trades. Every book here can be made to have a
bigger net by trading more, regardless of whether it is any better.

---

## PART 2 — Why win rate is not the metric

### win rate

The percentage of trades that ended positive.

> `win 40.0%` = 4 out of every 10 trades made money.

**This number is close to meaningless on its own**, and the table below proves it.

### avg win / avg loss

The average R of the trades that won, and of the trades that lost.

### expectancy (the one that actually matters)

> **expectancy = average R per trade = (share of wins × avg win) − (share of losses × avg loss)**

It answers: *over all trades, how much did I make on an average trade?* A book
only makes money if this number is above zero.

### profit factor

> **PF = (total R won) ÷ (total R lost)**

Above 1.0 means more came in than went out.

### Worked example from our own books

`fsent_champ_long` in sample: win rate **40.0%**, net **+533.37**.

Yes — **60% of the trades lose money**, and the book is profitable. The reason:

| | value |
|---|---:|
| win rate | 40.0% |
| avg win | **+3.739R** |
| avg loss | **−0.806R** |
| expectancy | **+1.010R per trade** |

> Losses are about **4.6× smaller** than wins. Four losses cost 3.2R; one win
> returns 3.7R. The book wins by being *right big when right*, not by being right
> often.

**This is the whole reason trend-following works with a sub-50% win rate.** If
someone quotes you a win rate without an average win and an average loss, they
have given you the least informative half of the number.

---

## PART 3 — The pain metrics

### max drawdown (max DD)

> The largest peak-to-trough fall in the equity curve, in R.

```
equity ↑
        |        peak (say 300R)
        |       / \
        |      /   \
        |     /     \___ trough (say 200R)
        |__________________________→ time
                     ↑
             drawdown = 300 − 200 = 100R
```

**This is what stops you quitting.** A book with +900R net and a 105R drawdown can
make you walk away at exactly the wrong moment. This is why the owner set a
**29R ceiling** — the point past which holding the book becomes psychologically
impossible, and an account that is abandoned is an account that never collects.

### ulcer

> The **average** size of the drawdown across every moment in time, not the worst.

A book can have one catastrophic drawdown and an otherwise smooth curve; ulcer
weighs that against all the shallow ones. **Low ulcer means the pain is
consistent rather than occasional.**

### underwater % (uw%)

> The percentage of time the equity sits **below its own previous record**.

84% underwater means: of 100 trades, 84 left you below the highest value you had
ever reached. **Completely normal** for trend-following — it earns by being
underwater most of the time and spiking occasionally.

### longest underwater (maxUW)

> The longest unbroken run of consecutive trades spent below the peak.

**This is the number that matters more than uw%.** One day underwater and two
months underwater both read as "underwater"; only `maxUW` tells you how long you
wait for a new record.

### worst losing streak (worstLS)

> The most consecutive losing trades in a row.

The most human metric on this page. It is the answer to "how many losses in a row
do I have to sit through before the next win?"

---

## PART 4 — The owner's gates

A book is judged on **three gates**, not on net. All three must pass.

| # | gate | why |
|---|---|---|
| 1 | **max DD ≤ 29R**, both eras | the quitting threshold |
| 2 | **zero negative half-years** | no calendar stretch of 6 months may lose money |
| 3 | **p < 0.05 in both eras** | see Part 5 |

**Net is reported, never used to rank.** That is not modesty — it is the thing
that stops a book from being adopted for being big.

---

## PART 5 — What "p" actually is

This is the one that has been used most and explained least.

### The question it answers

You have a new book. It made more money than the book it came from. But you
**chose that new book partly by looking at this data**, so some of the
improvement is guaranteed to be luck — you will always find *some* variation that
looks better, if you look at enough of them.

> **The p-value asks: if I took the parent book's trades and just randomly threw
> some away and kept others, how often would I land on something this much
> better — by pure chance?**

That experiment is called a **permutation test**. The engine shuffles the trade
selections 4,000 times and counts how many shuffles matched or beat the real
result.

### How to read the number

| p | plain meaning |
|---|---|
| **p < 0.05** | fewer than 5 in 100 random shuffles beat it — the edge is probably real |
| **p ≈ 0.50** | half of random shuffles did this well — indistinguishable from luck |
| **p = 1.0000** | every shuffle did at least this well — no evidence at all |

### What it does NOT mean

- **It is not a measure of profit.** A book can be hugely profitable and have a
  bad p.
- **It is not absolute.** It compares the arm against **its own parent**, not
  against zero. It asks "is this arm's *choice of trades* better than the
  parent's", not "is this book good".
- **It is not a guarantee.** p = 0.03 still means a 3% chance under the null.

### Why both eras must pass

If you test 20 ideas, one will look great at p < 0.05 **by luck alone** — that is
the entire reason the 5% threshold exists. A result that holds in the data used
to *find* the idea and vanishes on data used only to *check* it is the signature
of having found luck.

> **In sample** = the data the idea was chosen on.
> **Out of sample** = data that was not used to choose it.

---

## PART 6 — Period control / fixed effect

A book can pass its p-value and still be a period artifact. What does "period
artifact" mean?

> The book made money **in certain years** because those years happened to be
> good, not because the idea works.

The test: **subtract each calendar year's own average from both books**, then see
what advantage is left.

- If the advantage **survives** → it is not just the year.
- If it **vanishes** → the book only worked in the good years.

> **`t` is the strength of what survived.** |t| near 0 means nothing survived.

We report two versions: `t_year` (remove each year's average) and `t_half`
(remove each half-year's average — stricter). The 2026-10-09 test reported a
"period control" that was actually reading the *first trade* of each half-year;
see `HTF_FS_ENTRY_CORRECTED.md`.

---

## PART 7 — The results, side by side

### In sample

| book | n | net | win% | avgW | avgL | PF | expect | maxDD | ulcer | neg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `champ_long` (shipping) | 528 | +533.37 | 40.0 | 3.739 | −0.806 | 3.09 | 1.010 | 13.42 | 3.43 | 1 |
| `mcloff` | 575 | +566.59 | 39.7 | 3.716 | −0.809 | 3.02 | 0.985 | 15.13 | 3.58 | **0** |
| **`htffs`** | 770 | **+897.94** | 42.3 | 3.884 | −0.829 | **3.44** | **1.166** | 19.78 | 3.83 | **0** |
| `htf15_htffs` | 761 | **+925.79** | 42.8 | 3.952 | −0.834 | 3.55 | **1.217** | **29.62** | 4.13 | 0 |
| `sig_multi_htffs` | 434 | +666.32 | **45.2** | **4.550** | −0.947 | **3.96** | **1.535** | 17.82 | **2.81** | 1 |
| `htfesmcl4` | 793 | +917.80 | 43.0 | 3.786 | −0.825 | 3.46 | 1.157 | 27.74 | 4.30 | 0 |
| `htf15` | 520 | +567.57 | 41.2 | 3.839 | −0.830 | 3.23 | 1.091 | 17.28 | 3.29 | 0 |

### Out of sample (reused 2021-22 — **not a holdout**)

| book | n | net | win% | avgW | avgL | PF | expect | maxDD | ulcer | neg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `champ_long` | 311 | +239.59 | 37.0 | 3.318 | −0.724 | 2.69 | 0.770 | 11.88 | 2.99 | 0 |
| `mcloff` | 337 | +270.91 | 37.1 | 3.388 | −0.720 | 2.77 | 0.804 | 14.16 | 3.07 | 0 |
| `htffs` | 415 | +300.43 | 36.9 | 3.211 | −0.728 | 2.58 | 0.724 | 14.35 | 3.43 | **1** |
| `htf15_htffs` | 393 | +304.17 | 37.9 | 3.226 | −0.724 | 2.72 | 0.774 | 14.35 | 3.11 | **1** |
| **`sig_multi_htffs`** | 220 | +234.48 | **46.8** | 3.323 | −0.922 | **3.17** | **1.066** | **7.99** | **1.86** | 0 |
| `htfesmcl4` | 437 | +326.22 | 37.8 | 3.168 | −0.722 | 2.66 | 0.747 | 14.20 | 3.39 | 0 |
| `htf15` | 280 | +254.88 | 37.1 | 3.685 | −0.729 | 2.99 | 0.910 | 16.86 | 3.67 | 0 |

### The three gates

| book | DD IS | DD OOS | budget | neg IS+OOS | p IS / p OOS |
|---|---:|---:|---|---:|---|
| `champ_long` | 13.42 | 11.88 | ✅ | **1 + 0** ❌ | — (it is the parent) |
| **`mcloff`** | 15.13 | 14.16 | ✅ | **0 + 0** ✅ | **0.0312 / 0.0117** ✅ |
| `htffs` | 19.78 | 14.35 | ✅ | 0 + 1 ❌ | 0.0272 / 0.5956 ❌ |
| `htf15_htffs` | **29.62** | 14.35 | ❌ **over** | 0 + 1 ❌ | 0.0105 / 0.4904 ❌ |
| `sig_multi_htffs` | 17.82 | 7.99 | ✅ | **1 + 0** ❌ | 0.5091 / 0.9708 ❌ |
| `htfesmcl4` | 27.74 | 14.20 | ✅ | 0 + 0 ✅ | 0.0285 / 0.5311 ❌ |
| `htf15` | 17.28 | 16.86 | ✅ | 0 + 0 ✅ | 0.1927 / 0.5021 ❌ |

**Only `mcloff` passes all three.**

---

## PART 8 — The one that teaches the most

Read the `sig_multi_htffs` rows again:

> It has the **highest win rate** (45.2% / 46.8%), the **highest expectancy**
> (1.535 / 1.066), the **highest profit factor** (3.96 / 3.17), the **lowest
> drawdown** (17.82 / 7.99), the **lowest ulcer** (2.81 / 1.86), and the
> **shortest underwater stretch** (31 trades vs 60).
>
> **On every single descriptive measure it is the best book in the table.**
>
> And its p is **0.5091 / 0.9708**, and its out-of-sample gap is **−5.11R**.

**Nothing is wrong with the numbers. They are measured correctly. They simply do
not add up to an edge we can tell apart from reshuffling the parent.**

This is the hardest idea in the whole project and it is the one that keeps being
skipped:

> **Being good is not the same as being better than chance.**

A book can be beautifully behaved and still be indistinguishable from noise. The
descriptive metrics describe the book. **The p-value is the only thing on this
page that addresses whether the book is *doing something*.**

---

## PART 9 — Why nothing is adopted

- The 2021-22 out-of-sample era was **already looked at** many times during
  development, so it is not a holdout. See `OOS_IS_NOT_A_HOLDOUT.md`.
- `mcloff` passes all three gates on data that has been reused. That is the
  strongest evidence available and it is still not proof.
- Forward data is the only untouched evidence: **n ≥ 50** provisional, **n ≥ 150**
  first verdict, **n ≥ 300** publishable. At roughly 20 trades per book per
  month, n = 150 is about **2.7 years**.

**Shipping book unchanged.**