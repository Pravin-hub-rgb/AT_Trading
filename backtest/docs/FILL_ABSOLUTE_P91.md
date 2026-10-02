# P91 — THE DENOMINATOR DID MOVE. P90's headline is retracted.

> Run 2026-09-29. Harness `exp_entry_fill_absolute.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS as shipped.
> **P90's "+174.8R" is a denominator artefact and is withdrawn.**

## The question P90 left open

P90 re-filled the champion's entries at the next 15m bar's open and the
book got better everywhere — champion IS +325.8R → +500.6R, PF 2.38 → 5.39.
If true, +325.8R was a pessimistic figure and shipping it is conservative.

**P90's own caveat was that R-multiple is a ratio and its denominator moves.**
A later entry can shrink `risk` while barely moving `gain`, and R rises
without the trade being any more profitable. The mechanism falsifier had
already failed (corr(dR, ATR%) = −0.05 to −0.08 in all four cells).

## The test

Absolute price return at **one unit of notional**:

```
long   (exit - entry) / entry        summed across the book
```

**No denominator that can move.** Both arms measured the same way, shipped
as control.

## Result

| lane / era | fill | **absolute total** | implied R | mean/trade | win % | **P90 claimed** |
|---|---|---|---|---|---|---|
| champion **IS** | shipped | **+1.2018** | +131.4R | +0.00240 | 50.2% | — |
| champion **IS** | next open | **+1.2106** | +132.4R | +0.00242 | 51.0% | **+174.8R** |
| champion **OOS** | shipped | **−0.3795** | −23.9R | −0.00136 | 47.0% | — |
| champion **OOS** | next open | **−0.1188** | −7.5R | −0.00043 | 47.7% | **+144.0R** |

**The absolute change in IS is +0.0088 on a base of +1.2018 — 0.7%.** P90
reported +174.8R on that same change.

**And in OOS both arms are negative in absolute terms** — −0.3795 shipped,
−0.1188 re-filled.

## The verdict: it was the denominator

> **The re-fill does not make the book meaningfully more profitable. It
> makes each trade's R-multiple larger by shrinking the denominator, which
> is what raises the summed R from +325.8R to +500.6R.**

**P90's headline is retracted.** The decision it was commissioned to inform
— "is +325.8R a fill artefact?" — is answered, and the answer is **no**, but
not for the reason P90 gave.

## And the absolute view exposes something R never showed

**The per-side absolute split, on the same numbers R-multiple reported as
profitable on both sides:**

| lane / era | side | shipped | next open |
|---|---|---|---|
| champ IS | longs | **+1.6433** (273t) | **+2.3195** |
| champ IS | shorts | **−0.4415** (227t) | **−1.1089** |
| champ OOS | longs | +0.3676 (162t) | +1.1962 |
| champ OOS | shorts | **−0.7471** (117t) | **−1.3150** |

## Second sighting — 2026-10-01, `CONCURRENCY_P117_P120.md`

The short-side asymmetry has now been observed twice, independently. **It has
been treated as a local finding both times and it is not local.**

**Sighting 1 — this document.** Every short book loses money in absolute terms in
both eras, −0.4415/trade IS and −0.7471/trade OOS, while reading +53.2R and
+68.4R in R.

**Sighting 2 — P119, in `CONCURRENCY_P117_P120.md`.** On the leg book, capping
concurrency to 1 collapses the short side: **+81.5R → +5.9R, −92%** OOS, against
longs +26.9R → +10.4R. The shorts are disproportionately what the cap deletes.

**Correction to how this was first reported.** P119's short collapse was counted
as a third sighting alongside P117. It is not. P117 measured the cap grid and
contained no direction split at all; P119 measured the split. That is two
observations across two pieces of work, not three.

**The important caveat, which cuts against the second sighting.** P119's collapse
is measured **in R**. This document establishes that R is exactly the metric that
misrepresents the short side — the entire short-side profit is the denominator,
because shorts are taken with larger stops. So the −92% is an R-number about a
book whose R and absolute terms diverge badly on precisely this side.

**It is therefore not established that the short side collapsed.** It is
established that its R collapsed. The absolute number for the cap-1 short arm was
not computed and should be, before this is written up as a short-side result
rather than an R-accounting one.

That gap is the substance of the asymmetry being unresolved after two sightings.
Three would have been a pattern; two is a coincidence until the absolute arm is
measured.
**Every short book LOSES money in absolute terms in both eras — and the
re-fill makes the short side WORSE, not better.**

**In R units those same short books read +53.2R (IS) and +68.4R (OOS).** The
entire short-side profit is the denominator: shorts are taken with larger
stop distances, so each one's R-multiple looks healthy while the price
return is negative.

**This is the same class of error as P60 and P83, one level deeper.** Both
of those were gross-vs-net. **This is R-vs-absolute, and it is the most
consequential of the three because the R-multiple is the number the whole
programme reports on.**

## What this does to P89

P89 concluded the long side is structurally stronger in IS (+0.96 R/trade,
p = 0.0003). **That conclusion was measured in R and stands as measured.**
But in absolute terms the IS long book is +1.64 and the IS short book is
−0.44, so the asymmetry is **larger in absolute terms than the R-multiple
suggested** — not smaller.

**So P89's direction survives and P90's number does not.**

## What this does to the shipping decision

**The shipped figure stands: +325.8R IS / +70.1R OOS, and there is nothing
to change in production.**

But the honest statement about what that number is:

> **+325.8R is an R-multiple total. The book takes larger stops on shorts,
> which inflates their R relative to their price return. The absolute
> picture is: longs profitable in both eras, shorts unprofitable in both, and
> the OOS book negative in absolute terms overall.**

**That is a materially different way to describe the same backtest**, and
it is the description an owner sizing a live account needs. **It is not a
reason to abandon the strategy — the R convention is the programme's
stated basis and gates 1–3 are all defined in R — but the absolute view
should be reported alongside every headline from here.**

## Stated limitations

- **Both lanes are the same data.**
- **Implied R uses the book's own median risk**, so it is a comparable
  scale, not a per-trade reconstruction. The absolute column is the
  primary result; the implied-R column is for comparability only.
- **`ex-top5` is computed on R-multiples** because that is what the engine
  reports, so it inherits the same denominator caveat and is not evidence
  about absolute returns.
- **The 5bp slip arm uses the repo's existing entry-slip assumption.**
- **Absolute return per unit notional is not an account curve** — it
  ignores compounding and position overlap, and the one-slot rule means
  notional is deployed at most once at a time. It is a comparison measure
  between two arms of the same book, which is what it was built for.

## Status

**Nothing adopted. P90's headline withdrawn. The champion's shipped number
is unchanged and was never overstated — but it is an R number, and the
absolute view says the short side does not make money in price terms.**

Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS as shipped.
