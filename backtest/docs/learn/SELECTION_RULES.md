# THE SELECTION RULES — written before the results are read

2026-10-16, branch `research/four-validation-techniques`.

**This file is written before the 13-book battery finishes. Do not edit it
after seeing the numbers.** That is the entire point. A rule written after the
results is a rationalisation wearing a rule's clothes, and this repo has three
examples of that already: `exp_trail_skip_n=16`, `htf_rr=4.0`, and the
scorecard's own shortlist.

---

## Why this file exists

The shortlist was made by reading a table of ~40 metrics with no weights, then
defended on a single number — out-of-sample net. Both halves were wrong:

- **Unweighted table**: any of five books can be preferred by picking the axis
  that favours it. That is an uncalibrated selection algorithm wearing a
  dashboard's clothes.
- **Net alone**: a book with fewer trades and better expectancy per trade gets
  dismissed as worse. That is how `sigm` — 51.4% win rate, 91.5% positive
  rolling-10 windows, best tail profile in the registry — ended up excluded on
  +184.9R against +313.4R.

So the rule is stated here, once, before the numbers exist.

---

## The gate sequence

Not a weighted composite. **A book must clear each gate in order.** A book that
fails any gate is out, regardless of how it scored elsewhere. This is the
structure the external reviewer proposed and it is the right one: it removes the
freedom to trade a weakness against a strength after the fact.

### Gate 1 — Evidence the edge is real

| test | pass condition |
|---|---|
| Net after removing the best 10 winners | **positive in both eras** |
| Top 10% of winners carrying the result | **below 120% in both eras** |
| Out-of-sample net | **positive** |
| Out-of-sample sign consistency | no era negative |

Rationale: a book whose profit disappears when ten trades are removed is ten
episodes, not a strategy.

### Gate 2 — The book survives on its own terms

| test | pass condition |
|---|---|
| T1 parameter span, IS | **below 60R** |
| T1 parameter span, OOS | **below 60R** |
| T2 walk-forward, re-optimised vs registered | **at least 2 wins of 3 folds, or a tie** |
| No cliff | no single adjacent parameter value collapsing the result by more than half |

Rationale: the doc's cliff test, plus walk-forward. A book that only works at
one setting is not an edge.

### Gate 3 — Execution tolerance

| test | pass condition |
|---|---|
| Break-even stop slippage, IS | **at or above 100 bps** |
| Break-even stop slippage, OOS | **at or above 90 bps** |
| Cost at 3x | still profitable |
| Trades lost at 1000 bps slippage | **below 50%** |

Rationale: the live bot fills at market on a stop. A book that dies below 100
bps of slippage cannot be traded live at all.

### Gate 4 — Survivability

| test | pass condition |
|---|---|
| Paths above 25R drawdown, IS | **below 5%** |
| Paths above 50R drawdown | **zero, both eras** |
| Worst 50-trade window, OOS | **positive** |
| Ruin rate at 1% risk per trade, p95 safe | **at least 1%** |
| Observed drawdown percentile | **below the 99th** |

Rationale: the doc's survivability section. Not "can you stomach it" — whether
an unlucky ordering can take the account below half.

### Gate 5 — Preference (owner, after the gates)

Among books clearing **all four gates**, rank by owner preference on:

1. worst 50-trade window, OOS — patience
2. R per trade, OOS — quality per trade
3. net, OOS — total

**In that order.** Patience first, then quality, then size. If two books are
within noise on the first two, the larger net wins and nothing else is
consulted.

---

## What this explicitly forbids

- **Adding a book to the shortlist because it scored well on something not
  listed here.** If a metric matters, it goes above, in advance.
- **Weighting.** No metric trades against another. Gates are pass/fail.
- **"Except for" clauses.** No gate gets waived.
- **Changing a threshold after seeing results.** If 60R is wrong, change it now,
  before the run lands, and say why.
- **Using the forward window to choose.** The forward window is scored once, at
  the end. Looking at it to decide is the one thing that would make it worthless.

---

## The tie-break that matters most

If more than one book clears all four gates, **that is a real finding and not a
failure of the method.** It means the strategy family contains several robust
books and the choice between them is a risk-preference decision, not a
measurement.

If NO book clears all four, that is also a real finding. In that case nothing
goes live yet and the answer is more data, not a re-ranked shortlist.

---

## Known weaknesses of these rules

Stated now, not later:

1. **The gates were written by someone who has seen these thirteen books.** They
   are not blind. They are less biased than an unweighted table because every
   threshold is explicit and any later change is visible in a diff.
2. **The books are correlated.** 106, 108 and 109 overlap 85–93% and are one
   bet under three names, so "five candidates" is really three. Agreement among
   them is not independent evidence and the rules above do not claim it is.
3. **2021–2022 is not independent.** It has been used for filtering throughout.
   A book that passes Gate 1 on it has not been validated, it has been checked.
4. **Effective sample size is small.** Two eras, one market, one engine.
5. **The forward window is 3–15 trades per book.** It cannot settle this, and
   these rules do not pretend otherwise.