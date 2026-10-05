# HALT FIRING RATE — my own hypothesis, measured, and refuted

Date: 2026-09-28. `exp_halt_firing_rate.py` → `_halt_firing_rate.json` 61.7s.
Controls exact both eras.

## What I claimed, and what is true

I asserted in `method/KELLY_CONTINUOUS.md` that the IS/OOS autocorrelation split
is explained by the halt firing more often in IS — chopping the loss
sequence and mechanically de-correlating it. That was a story I had not
measured. Here it is measured.

| era | halt ON (k=3) fires | halt OFF (k=0) fires |
|---|---|---|
| IS | 51 fires / 500t = **10.20 per 100** | 54 / 557 = 9.69 |
| OOS | 29 / 279t = **10.39 per 100** | 35 / 320 = 10.94 |

**The halt fires at essentially the same rate in both eras — 10.20 vs 10.39
per 100 trades.** The hypothesis is **REFUTED.** The halt does not bite
harder in IS.

Run-length structure agrees: mean loss run 3.57 (IS) vs 4.02 (OOS), max 16
vs 15, 98 runs vs 50. Nearly identical, and the halt-OFF histograms are
just as similar.

## And the script's own verdict was wrong

The script printed `VERDICT: CONFIRMED` — because it compared the
*delta* between k=3 and k=0 across eras (IS +0.51, OOS −0.55) instead of
the **absolute** firing rate. Two eras whose rates are 10.20 and 10.39
produced a "confirmed" verdict off a ±0.5 difference in a derived quantity.

That is a bad test wearing a good label. It is recorded rather than fixed
in place, because the failure mode — a verdict that reads CONFIRMED on a
null result — is the one this repo has been bitten by repeatedly.

## So the OOS autocorrelation is now MORE unexplained, not less

Before this run the position was: "probably the halt, in IS." It is now:

**OOS trade-R ACF(lag1) = +0.498 against a ±0.117 band, with no measured
mechanism behind it.** Not the halt (fires equally). Not monthly
clustering (loss share is flat, 0.723 vs a 0.720 base). Not trade count
(279 vs 500 is ordinary density).

The remaining candidate worth naming: the ACF is computed on R values, and
this book is tail-concentrated. A handful of large R clustered in adjacent
trades would produce a high lag-1 ACF on its own, with no clustering of
*wins* or *losses* at all. **That is testable and unrun** — recompute the
ACF on the RANKS of R (or wins/losses only), which is immune to a few
dominant values. If the ACF collapses, the "+0.498" was three trades, and
the finding shrinks to "the tail clusters sometimes", which is a much
smaller claim.

## On the user's correction about `max_consecutive_losses=3`

The user was right and my "mid retrospective risk" label was wrong. The
distinction I blurred:

- **A fitted parameter** selects trades on data — genuinely dangerous.
- **A causal rule** is applied identically live whether you chose it by
  sweep or inherited it. `max_consecutive_losses=3` is the second kind.
  Live, three losses happen, the next entry is skipped. Nothing about that
  changes because the value was inherited.

What the sweep actually established is not "3 is a magic number" but
**"pausing after a loss streak is right, and 3 is a robust choice of
threshold"** — k=2 costs −77.7R and k=6 costs −103.7R, so the rule is not
fragile. That transfers. The *value* disagreement (IS 3, OOS 4) is a real
but minor caveat, not a methodological problem.

The finding worth keeping from the pair of runs is the pairing:
**OOS shows losses cluster (ACF +0.498), and a pause-after-streak rule is
the causally correct response to clustering.** The two facts are one idea.
The rule needs no prediction to work — it responds.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
