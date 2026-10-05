      N  blocks       mean        min        max     spread
         20      25      +17.8       -4.6      +74.7       79.4
         40      12      +33.2       -4.8     +121.0      125.8
         60       8      +49.8      +15.6     +117.8      102.2
         80       6      +66.4      +24.7     +120.7       96.1
        100       5      +89.0      +37.8     +112.8       75.0
        120       4      +99.7      +50.1     +159.1      109.0
        160       3     +132.9      +75.1     +164.7       89.6
        200       2     +171.6     +143.2     +200.1       56.9

The naive read is "every block size clears M, even 20 trades, so a
20-trade forward slice could already decide things." **That read is wrong
and is not the conclusion.** See below.

## The method is underpowered and the number must not be quoted

**The `max − min` range across blocks is a severely biased-low estimate of
spread when there are only a few blocks.** With 2 blocks the "range" is the
gap between two samples and tells you almost nothing; with 25 it is better
but still biased low, because the range statistic systematically misses the
tails of a distribution. So "spread ≤ M at every N" is largely an artefact
of how few blocks each N produces, not evidence that 20 trades suffice.

**A 20-trade forward slice concluding that it has confirmed or ruled out
anything would be absurd, and this table is not a licence for one.** The
block count column is the honest diagnostic here, not the spread column.

Getting a usable answer needs a proper stationary-block bootstrap with many
resamples rather than a handful of disjoint blocks — a different estimator,
and not one this session has validated. **I am not quoting a required
forward length from this run.**

## What IS established

**1. The queue's forward entry is wrong by two orders of magnitude.** It
promises "~464 trades, so it can rule on things and confirm none." P61
measured the actual slice: **2 champion trades, 1 candidate trade, over
12.5 days.** That entry has been corrected in `method/OPEN_RESEARCH_QUEUE.md`.

**2. The practical planning number comes from the trade RATE, not from
block statistics.** The champion produces 500 trades in 3.7 years IS
(~135/yr) and 279 in 2 years OOS (~140/yr). **A 60–70 trade slice — the
range the queue considers minimally useful — is therefore about 5 to 6
months of forward data, not a fortnight.** From the 2026-09-25 slice
boundary that is roughly **March 2027**.

**3. The block spread is smaller than M = 193.4R, which is itself worth
noting but not acting on.** M is a deck-relative null from a two-year
block; these are per-era blocks of a single book. They are not the same
quantity, so their disagreement is expected and M is not thereby
invalidated. Nothing here changes M.

## Recommendation

**Correct the queue entry, do not run the forward pass yet, and do not
treat P62 as having specified the required length.** The right estimator for
that question is a stationary-block bootstrap with resampling, and it
should be built and validated before anyone plans a date around its
output. Until then the 5–6 month figure is a rate-based estimate offered as
an estimate, not a computed requirement.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
