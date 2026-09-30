# P69: the volatility ceiling works in OOS and the relative-price form dies

> Run 2026-09-29. Harness `exp_ceiling_relprice.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **Both of P68's queued corrections were run. One is 3/4 positive, one is
> dead in all four — and the dead one is the form of the owner's own
> hypothesis.**

## A — volatility CEILING, correct sign

`ATR% = mean(TR over 96 × 15m) / close`, P68's fixed version. Keep trades
at or below the ceiling. Grid pre-registered: 0.30 / 0.40 / 0.50 / 0.60%.

| ceiling | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 0.30% | −131.3R | +2.5R | −128.7R | +17.3R |
| **0.40%** | **−9.0R** | **+41.6R** | **+5.6R** | **+37.1R** |
| 0.50% | −9.0R | +33.1R | −5.2R | +20.4R |
| 0.60% | −5.7R | +17.3R | −5.8R | +10.0R |

**The corrected direction is the right one.** At 0.40% the champion's OOS
profit factor goes **1.59 → 3.06** and utcsat's **1.58 → 2.94** — roughly
doubled — on 391 of 500 IS trades and 106 of 279 OOS trades. Three of four
cells are positive, and utcsat IS is +5.6R rather than negative.

**It still fails family-wise**, on two counts:

- **IS is −9.0R and −5.7R.** Small, but negative, and the criterion requires
  both eras.
- **Nothing clears M = 193.4R.** The best cell is +41.6R, **21.5% of the
  null.**

**And the ceiling curve is not monotone in a way that invites a threshold.**
0.40% is the peak in both lanes, and it is the arm with the *second*-most
OOS trades. Choosing it because it is the peak of a four-point grid on an
answer already in view is exactly the search this programme has refused
everywhere else, so it is reported as "the family fails" and not as "0.40 is
probably right."

**The honest reading: the volatility effect P67 found is real, and it is
largest in OOS, and that is still the era-split signature.** IS gives up
almost all of its return for a profit factor the OOS book already had. This
is the sixth and seventh appearance of that pattern, not a new result.

## B — RELATIVE PRICE, and why it dies in all four cells

`REL = close at entry / median(close over the trailing 30 days = 2880 × 15m
bars)`. Both terms historical, both available live. Grid pre-registered:
keep REL at or below 0.85 / 0.90 / 0.95 / 1.00.

| REL ≤ | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 0.85 | −326.5R | −72.2R | −359.6R | −56.1R |
| 0.90 | −313.2R | −74.5R | −346.1R | −66.3R |
| 0.95 | −300.2R | −84.9R | −347.5R | −73.4R |
| **1.00** | **−125.4R** | **−75.8R** | **−135.0R** | **−69.2R** |

**Dead in every cell, by −56R to −360R.** The loosest version is the least
bad, and even at REL ≤ 1.00 — keeping trades priced at or below their own
one-month median, which is half the book — the champion's OOS falls from
+70.1R to **−5.6R at PF 1.12.**

**The ranges explain it.** REL spans 0.774–1.371 in IS and 0.630–1.482 in
OOS, so REL ≤ 1.00 retains 236 of 500 IS trades and 144 of 279 OOS trades.
**In a market that trends, price sits at or below its one-month median only
when it has recently fallen** — so the filter is not selecting "cheap", it
is selecting "recently down", and in this book that is the wrong cohort.

## What this does to the owner's price hypothesis

P68 found **low absolute price beats high absolute price in 4 of 4 cells**
(PF 2.60 vs 2.14, 1.68 vs 1.50, 3.08 vs 2.13, 1.72 vs 1.44). That result is
untouched and still stands.

**But the scale-free version of it — the only version that could be traded
— is dead in 4 of 4.** Those two facts together are the finding:

> **"Low price" is a statement about the level, and the level is a clock. It
> is not a regime. A rule keyed to it stops trading as the market rises, and
> the relative form that removes the clock dependence selects the wrong
> cohort entirely.**

P68 already said a fixed price floor is "a clock, not a regime detector."
**This run is the confirmation, and it is the negative half: making it
scale-free did not rescue it, it destroyed it.**

**The distinction worth keeping: the absolute-price effect was never an edge
claim.** Both halves of that split were profitable — LOW px held +207.5R of
the champion's +325.8R in IS and +41.7R of +70.1R in OOS. It described the
champion's *character* (it earns more when it trades in a cheaper market),
which is a genuine observation and a terrible filter. Those are easy to
confuse and the queue should keep them apart.


## Family-wise verdict

| grid | cells | result |
|---|---|---|
| ceiling 0.30% | −131.3R, +2.5R, −128.7R, +17.3R | fails |
| **ceiling 0.40%** | **−9.0R, +41.6R, +5.6R, +37.1R** | **fails (IS negative, max 21.5% of M)** |
| ceiling 0.50% | −9.0R, +33.1R, −5.2R, +20.4R | fails |
| ceiling 0.60% | −5.7R, +17.3R, −5.8R, +10.0R | fails |
| REL ≤ 0.85–1.00 | −326.5R … −56.1R | **fails, all four** |

**Nothing adopted. Nothing survives the family.**

## What is left, honestly

- **The volatility CEILING at 0.40% is the strongest surviving candidate of
  the entire round on the OOS leg alone** — three of four cells positive,
  OOS profit factor roughly doubled. It fails the IS leg and the null. Per
  P63 a 40–70 trade forward slice can *rule out* and never confirm, and this
  is a rule that could be killed on one. That is its only remaining route.
- **Relative price is closed.** Do not re-run it in another form without a
  reason; the cohort it selects is wrong, not merely mis-scaled.
- **Absolute price stays as a description of the champion's character**, not
  as a candidate.

## Stated limitations

- **Ceiling cells are 52–477 trades**; the 0.30% arm is 239 IS / 52 OOS,
  which is why it swings to −131.3R in IS.
- **4 trades fail to featurise in IS and 2 in OOS** (insufficient trailing
  history at the series start), so arms are computed on the featurised
  subset. The 0.40 and 0.50 rows showing an identical −9.0R in IS are two
  levels that keep the same 391 trades, not a bug.
- **Both lanes are the same data.** Their agreement is not independent.
- **Price and volatility are not independent features.** P67's bug was
  treating absolute ATR as volatility; ATR% here is properly normalised, but
  ATR% and REL still both move with how violently the market is moving.
- **The 30-day REL median was fixed before the run and not varied.** A
  different window is untested, and varying it now would be a search on a
  grid that has already failed in all four cells.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
