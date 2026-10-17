# External methodological review, and what we are doing about it

2026-10-16. This is an outside critique of how the candidates were chosen,
written by a separate reviewer with no stake in the outcome. It is recorded
verbatim in intent and answered point by point below, because the useful part
of a review is the response to it, not the review itself.

---

## The critique, in full

The headline finding, in the reviewer's own framing:

> The biggest problem isn't that you have too many metrics. It's that the
> research process lets the data influence which candidates survive, which
> metrics matter, and which validation tests get run — without a predeclared
> rule that controls those choices. That is a classic route to researcher
> degrees of freedom.

The review separates three questions that the current process mixes together:

| # | question | can a statistic settle it? |
|---|---|---|
| 1 | Is there evidence of an edge, or is it noise / selection? | yes, partly |
| 2 | Is the edge robust enough to survive implementation? | yes, partly |
| 3 | Is the risk acceptable given capital and psychology? | **no — owner's call** |

**A strategy can pass one and fail another.** High p-value does not disqualify;
low p-value does not make deployable. Smooth equity does not establish an edge.

### What was wrong with the selection method

1. **Only five books reached the scorecard.** Eight of the thirteen active
   multi-position books were removed earlier by ad-hoc judgment. Their exclusion
   is part of the selection process, not an irrelevant detail.
2. **The metric weights were implicit.** Nothing was specified about how much
   smoothness, significance, return or parameter stability mattered *before*
   reading the results. That leaves freedom to rationalise a preference after
   the fact.
3. **Validation followed selection.** The heat maps, walk-forward and stress
   tests ran *after* 107 and 110 were chosen, so they cannot validate the choice.
4. **The effective trial count is unknown.** Fifty-four pinned books are not
   fifty-four independent trials. Correlated variants are not independent, but
   the actual research universe — including discarded sweeps and repeated
   decisions — is probably larger than fifty-four.

> My verdict: the table is a useful diagnostic dashboard, but the human selection
> procedure is an uncalibrated model-selection algorithm. It needs to be treated
> as such.

### The specific warnings

- **107:** its p=0.0112 comes from a repeatedly examined era. That is a reason to
  investigate the evidence further, not to waive robustness requirements.
- **110:** its smoothness is a reason to investigate the risk profile further,
  not to waive the parameter-inversion warning.
- **Neither earns a live green light from these results alone.**

On 110's payoff shape specifically: median trade −1.05R with mean +1.63R is
*acceptable in principle* for a trailing-stop trend follower, but it demands a
tail audit — and crucially, **deleting individual winners understates episode
concentration**, because several overlapping trades can all benefit from one BTC
move.

### The prescription

Re-run the same validation battery across the **whole candidate set**, not just
the winners, under a pre-declared decision procedure:

1. Reject invalid implementations.
2. Reject candidates breaching pre-declared risk limits.
3. Reject candidates whose performance depends on an unacceptably narrow
   parameter peak.
4. Assess survivors with selection-aware evidence and conservative portfolio
   returns.
5. Among survivors, owner preference — or admit the data cannot distinguish them.
6. Freeze and forward test.

Plus: a research ledger of everything tried, honest data labels, selection-bias
assessment (Reality Check / PBO / Deflated Sharpe), and portfolio-time rather
than trade-level resampling.

---

## What we accept, without argument

| critique | our position |
|---|---|
| Selection was an uncalibrated human read of a wide table | **Accepted in full.** `exp_pick_scorecard.py` computes no score, no weights, no ranking. It is a 40-metric presentation. The choice was ours, not the tool's. |
| Only 5 of 13 multi books were considered | **Accepted.** The other eight were removed by judgment, not measurement. |
| 2021–2022 is not independent validation | **Accepted, and already partly acted on** — relabelled "reused OOS era" across the docs, and the chop-high reveal was pre-registered *after* that era had already been used for filtering, which is exactly the error being described. |
| Validation ran after selection | **Accepted.** All four techniques test whether 107/110 survive on their own terms. They say nothing about whether they were the right pair. |
| Trial count unknown | **Accepted.** The repo's own `exp_degfrees.py` concluded the 464 figure was an estimate from 58 logged experiments × 8 assumed arms, not an audited count. |
| Selection-bias correction missing | **Accepted and not yet done.** This is the largest genuine gap. |
| Trade-level resampling breaks overlap | **Accepted and fixed** in `exp_sizing_ruin.py` and `exp_capital_headtohead.py`. |
| Ruin must be defined in equity terms, not R | **Accepted and fixed** in the same two files. |
| Recovery must separate censored from completed | **Accepted and fixed.** |

## What we dispute, or cannot yet answer

| critique | our position |
|---|---|
| "A parameter moving 400R may not mean fragility — it may mean it controls exposure or the economic mechanism" | **This is right and we under-weighted it.** `max_positions` moving results by 358–491R is not fragility, it is a different portfolio. We were about to treat it as a tuning knob. It should not be heat-mapped like one. |
| "Don't heat-map everything equally — cover every material mechanism and spend effort where the result is most sensitive" | **Accepted.** Our first heat map covered two knobs that turned out to be nearly inert. |
| "50 trades or 6 months is not a defensible stopping rule" | **Partly disputed.** We are not claiming it is statistically sufficient — we are claiming it is an *operational* checkpoint. The review is right that it cannot settle the comparison, and the contract says so. But a pre-declared checkpoint is still better than an open-ended look. |
| "A p-value of 0.3824 is not evidence that 110 has no edge" | **Agreed, and it cuts against us.** We have been treating 110's non-significance as disqualifying when it is not. |
| Selection-bias methods (PBO, DSR, Reality Check) | **Not yet attempted.** This is the real outstanding work. |

## What the review changed in our plan

1. **Run the same four techniques on 106, 108 and 109** — the eight unmeasured
   multi books aside, these three were on the original scorecard and were
   eliminated on net and drawdown alone, without ever facing a walk-forward or a
   survivability test. If the battery promotes one, the shortlist was wrong.
2. **Stop treating `max_positions`, `htf_rr` and `mode` as tuning knobs.** They
   are structural. They change exposure and mechanism, not edge quality.
3. **Build the research ledger** — every configuration tried, with the date and
   reason for each removal.
4. **Attempt a selection-bias correction**, with its assumptions stated rather
   than assumed away.

## What has NOT changed

The review did not tell us which book to pick, and neither will it. Its own
conclusion is that neither candidate wins on current information, and that
"the owner decides acceptable risk; the research procedure decides whether the
evidence meets the bar. Keep those decisions separate."

That separation is the thing we had been collapsing. Significance and smoothness
are not points on one scale to be traded off. They are two different questions,
and a candidate has to clear a bar on each before preference is allowed to
operate.

---