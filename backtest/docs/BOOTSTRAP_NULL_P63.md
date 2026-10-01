# P63: the forward null, sized properly — and it is a *worse* null than M

> Run 2026-09-29. Harness `exp_bootstrap_null.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## What replaced P62

P62 cut the champion's trades into disjoint blocks and read `max − min` as
the spread. With 2–25 blocks that is a severely biased-low estimator, so
P62 withdrew its own conclusion. This is a **stationary block bootstrap**
(Politis & Romano): `ceil(n/L)` blocks of `L` consecutive trades, each
starting at a random position **independently** — that independence is what
makes it stationary rather than non-overlapping — concatenated to length `n`
and summed, 20 000 draws, seed fixed.

`L ∈ {10, 20, 40}` is a **sensitivity check, not a search**. P62's caveat
already fixed block length 20 to match `exp_montecarlo_dd.py`, and noted
that shorter blocks give a wider null while much longer ones destroy the
serial structure the method exists to preserve. **The band reported is the
widest of the three**, which is the conservative choice. No `L` is selected
for giving a nicer answer.

## The band, 5th–95th percentile

| n | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 40 | 104.0R | 94.3R | 110.5R | 89.0R |
| 60 | 132.0R | 118.5R | 136.8R | 104.3R |
| 80 | 148.7R | 138.5R | 156.6R | 123.0R |
| 100 | 169.5R | 158.2R | 175.9R | 142.0R |
| 140 | **198.4R** | 187.7R | **212.2R** | 167.9R |
| 180 | 224.8R | **212.4R** | 236.6R | 190.9R |
| 220 | 249.0R | 236.1R | 264.9R | **212.5R** |
| 279 | 279.4R | 268.4R | — | — |

**M = 193.4R sits inside this table between 100 and 180 trades**, and the
answer is the uncomfortable one:

> **A forward slice's own null is TIGHTER than M at ~100 trades and WIDER
> than M at ~140–220 trades.**

**The first `n` whose band is under M is 40** — which is the same wrong
answer P62 reached, and it is wrong for a different reason. The band does
not shrink with sample size and then stabilise; **it grows**, because the
quantity being resampled is the *total R of an n-trade run*, whose spread
scales with n. Comparing that width to a fixed two-year null is
comparing two different things.

## What this actually means for the forward pass

**M = 193.4R is not the bar a forward slice should be measured against.**
It is a two-year, whole-era null. A forward slice of n trades must be
measured against **its own row in this table**, and that row's *position*
relative to the era matters as much as its width: a 40-trade slice has a
narrow band centred near zero, so it is excellent at **ruling things out**
and structurally incapable of **confirming** anything.

**This is the real constraint on the plan.** A 60–70 trade forward slice —
the range the queue treats as minimally useful — has a band of roughly
105–137R centred near zero. It can rule a candidate out. **It cannot
confirm one, and no number of extra months changes that**, because the
asymmetry is structural: short runs of a book with a small positive drift
and high per-trade variance simply cannot separate from zero at 95%.

**So the family-wise forward pass as the queue describes it — "rule on
things and confirm none" — is the right instinct and the wrong arithmetic.**
It can rule on things. It was never going to confirm anything, and
promising it a confirmation role is what made the 12.5-day / 2-trade slice
look like a near-miss instead of the non-starter it is.

## The honest planning number

At ~135 trades/year (IS) and ~140/yr (OOS):

| forward trades | months of data | its own null band | can it rule out? | can it confirm? |
|---|---|---|---|---|
| 2 (today) | 0.5 | not measurable | no | no |
| 40 | 3.4 | ~89–111R | **yes** | no |
| 60 | 5.3 | ~104–137R | **yes** | no |
| 100 | 8.9 | ~142–176R | borderline | no |

**~3 to 5 months of forward data is the point at which the pass becomes
worth running** — because from ~40 trades it can start eliminating
candidates — and **no plausible horizon makes it able to confirm one.**
M remains the right bar for full-era comparisons, which is what it was
derived for.

## Stated limitations

- **Bootstrap bands are smooth estimates from 20 000 draws** of a single
  realised trade sequence. They assume the future resembles the champion's
  own past; a regime not represented in 3.7 years is outside what this can
  price.
- **`L` is a sensitivity, not a chosen value.** The widest band is reported
  precisely so the answer does not depend on that choice. A block-length
  sweep beyond {10, 20, 40} is still available and would be worth running
  before anyone treats the 40-trade figure as precise.
- **Percentiles are 5th–95th, a 90% band**, chosen before the run to match
  the two-sided convention. A 95% band would be wider and a one-sided band
  narrower; neither was searched.
- **These bands describe the champion's own statistics.** They size the
  noise floor for judging a *candidate against* it; they are not a null for
  whether the champion itself is profitable, which `M` already addresses.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
