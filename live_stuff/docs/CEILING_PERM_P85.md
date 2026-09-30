# P85 — THE CEILING SURVIVES, AND THE PERMUTATION TEST HAS NO POWER HERE

> Run 2026-09-29. Harness `exp_ceiling_perm.py`. **UNRESOLVED, not killed.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The candidate is NOT closed. The test came back p = 0.96–0.99 and that
> result is an artefact of low power, not evidence of absence — and saying
> otherwise would repeat P82's mistake in the opposite direction.**

## The instrument

P69's ATR% ceiling at 0.40% is the last standing candidate: 3 of 4 cells
positive, OOS profit factor **1.59 → 3.06** and **1.58 → 2.94**, drawdown
nearly halved in OOS, period partition 6-2 and 4-0 on the champion lane.
It never got P82's permutation test, and it should have — so here it is.

**The ceiling is a DROP, not a swap**, so the test is sharper than P80's:

```
dNet = net(arm) - net(control) = -net(DROPPED)
```

Identity asserted on every cell and **exact every time** — the one
instrument in this round that needed no correction.

## Result — "not significant" on all four cells

| lane / era | p | period partition |
|---|---|---|
| champion IS | 0.9634 | 5-2-1 |
| champion OOS | 0.9728 | **4-0** |
| utcsat IS | 0.9888 | 6-1-1 |
| utcsat OOS | 0.9871 | **4-0** |

## And the cohorts say something entirely different

| lane / era | kept n | R/t | PF | dropped n | R/t | PF |
|---|---|---|---|---|---|---|
| champion IS | 395 | **+1.074** | 2.70 | 105 | **+0.198** | 1.29 |
| champion OOS | 106 | **+1.235** | 3.06 | 173 | **−0.145** | 0.78 |
| utcsat IS | 359 | **+1.286** | 3.09 | 95 | **+0.051** | 1.07 |
| utcsat OOS | 99 | **+1.162** | 2.94 | 154 | **−0.145** | 0.78 |

**Kept R/t is +1.07 to +1.29 in all four cells. Dropped is −0.145 to
+0.198. A 5–8× separation, same sign, every cell, and in OOS the dropped
cohort is negative on both lanes.** And the permutation reports p ≈ 0.97
for all of it.

## Why both are true, and which to believe

**The permutation block-permutes contiguous runs of L trades. With L = 40
and a KEPT cohort of 99–106 trades, that is two to three independent
blocks.** The 20,000 draws are almost entirely repetitions of a handful of
arrangements, so the null is far coarser than the effect it must detect.

**The test cannot resolve this candidate. p = 0.97 here is a statement
about the test, not about the market.**

**This is the mirror image of P82, and the discipline is the same.** P82's
first null was centred at +207.8R and I rejected it as meaningless rather
than quoting p = 0.0000. **P85's null is correctly centred at zero but has
almost no power, and quoting p = 0.97 as "no edge" would be the same
mistake in the other direction.** A filter that removes 20–62% of the book
cannot be assessed by reshuffling a book of 100–500 trades.

**Note also what makes this candidate structurally different from the ones
P82 killed.** Directional FS replaced ~400 trades with ~400 others and the
cohorts had similar means (+181.1R dropped, +337.3R new), so
"not significant" was the *right* answer there. **Here kept and dropped
differ by 5–8× in R per trade, with the dropped cohort NEGATIVE in both OOS

## What is actually needed

**A statistic that respects the clustering without collapsing it.**

1. **Cluster bootstrap on half-years** — resample the 8 IS and 4 OOS
   half-years rather than trades. That respects regime persistence but
   gives only 8 and 4 draws, so it can rule and not confirm (P63's
   finding, in a new place).
2. **A two-sample test on the cohorts with a variance estimate that
   accounts for the window structure** — the blocks inside which trades
   share a regime. Report the effect size and the interval, not a bare p.
3. **A trend/regime-split on IS alone**, since the OOS legs are already
   consistent 4-0 with a negative dropped cohort on both lanes.

**None of these has been run.** The honest status is **unresolved**, and the
right next action is to build the instrument rather than to accept a number
that the instrument cannot support.

## What is NOT open to doubt

Independent of significance, these are measurements, not inferences:

- **In OOS the trades the ceiling removes are net negative** — −41.6R and
  −37.1R, PF 0.78 on both lanes.
- **In IS they are near-zero** — +6.0R and −8.5R, PF 1.29 and 1.07.
- **The period partition passes on the champion lane, 6-2 and 4-0.**
- **The identity holds exactly**, so the decomposition is not the issue.

**A rule that removes trades which lose money in the held-out era and are
worth nothing in the fitted era is a better rule than one that does not, on
any reading that does not require a significance claim this sample cannot
support.**

## Stated limitations

- **20,000 draws, one seed per L**, and the **smallest** p across
  L ∈ {10, 20, 40} reported — the most favourable reading of a test that is
  underpowered anyway.
- **Both lanes are the same data.**
- **The 0.40% ceiling was chosen from P69's four-point grid where it peaked
  in both lanes.** That is a grid peak and it is not pre-registered as a
  family — a genuine weakness, and the reason a fresh grid must not be
  explored on the strength of this.
- **The low-power argument is made, not formally measured.** A direct power
  calculation on the cohort difference would settle it and is cheap; it has
  not been run.

## Status

**NOT ADOPTED. NOT CLOSED. UNRESOLVED — and the resolution needs a better
instrument, not another number from this one.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS. This is now the only
open candidate in the programme, and the only one whose blocker is
methodological rather than a negative result.

lanes.** Those are not two samples from the same pool — they are two
visibly different populations, which is precisely what a permutation test
is bad at seeing and what a direct comparison sees immediately.
