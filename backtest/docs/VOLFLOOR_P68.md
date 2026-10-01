# P68: my preregistration was backwards; the owner's price hypothesis is 4/4

> Run 2026-09-29. Harness `exp_volfloor.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **Two findings: I built the volatility rule in the wrong direction, and
> the owner's price hypothesis holds in all four cells.**

## First, a bug from P67 that had to be fixed before anything else

P67 defined `trailing_atr_pct` with a docstring promising the value was
*"divided by the close at that point"* and a body that divided by nothing.
The numbers it reported — IS low-bound 151.8, OOS low-bound 140.2 — are
**absolute true range in dollars, not a percentage.**

That is not cosmetic. Absolute ATR is a product of price level and
volatility, so **P67 never tested volatility at all.** It tested a variable
that moved because BTC went from roughly $40k in 2021–22 to roughly $60k in
2023–26. P67's observation that "the tertile bounds differ between eras"
was therefore mostly a **price** observation wearing a volatility label, and
the conclusion drawn from it — that the eras' volatility distributions
overlap — was not supported by the test that produced it.

**The owner had raised price before that test and it was silently dropped
by a divide that was never written.** Fixed here:
`ATR% = mean(TR over 96 × 15m) / close`, using only bars at or before the
trade's own `entry_ts`.

## Second, I pre-registered the volatility rule backwards

P67 established that the book works in the **calm** third of its volatility
distribution. The live-computable rule for that is a **ceiling** — trade
only when volatility is not unusually high.

**I built a floor.** The harness docstring says *"a floor is the only
live-computable form of that"* and that is simply false: a ceiling is
exactly as computable, and it is the one P67's own numbers support.

| floor | champ IS | champ OOS |
|---|---|---|
| 0.40% | 105t +6.0R PF 1.29 | 173t **−41.6R PF 0.78** |
| 0.60% | 19t +2.7R PF 1.40 | 70t **−17.3R PF 0.74** |
| 0.80% | 2t −1.1R | 36t **−12.8R PF 0.53** |
| 1.00–1.50% | 1t −0.1R | 10–20t PF 0.49–1.14 |

**Every floor removes most of the book and makes OOS worse, in a monotone
run from PF 0.78 down to 0.49.** Taking the *high* volatility trades is the
worst thing available. **The ceiling is the rule P67 was pointing at, and it
is untested here.**

This is a pre-registration error, not a threshold search: the grid was fixed
before running, all six arms are reported, none was selected after the fact.
But the grid is still the wrong grid, and re-running it with the sign
flipped is a **new** pre-registration — not a fix to this one.

## Third — and this is the finding worth keeping: PRICE, 4 out of 4

The owner's original question, asked before P67 and never actually tested.

| book | era | half | n | net | R/t | PF |
|---|---|---|---|---|---|---|
| 15m | champ **IS** | **LOW px** | 251 | **+207.5R** | **+0.827** | **2.60** |
| 15m | champ IS | HIGH px | 249 | +118.3R | +0.475 | 2.14 |
| 15m | champ **OOS** | **LOW px** | 140 | **+41.7R** | **+0.298** | **1.68** |
| 15m | champ OOS | HIGH px | 139 | +28.4R | +0.205 | 1.50 |
| 15m | utcsat **IS** | **LOW px** | 228 | **+250.2R** | **+1.098** | **3.08** |
| 15m | utcsat IS | HIGH px | 226 | +108.7R | +0.481 | 2.13 |
| 15m | utcsat **OOS** | **LOW px** | 127 | **+38.5R** | **+0.303** | **1.72** |
| 15m | utcsat OOS | HIGH px | 126 | +21.7R | +0.172 | 1.44 |

**Low price beats high price in every cell: 4 out of 4, both eras, both
lanes, same direction, PF gap 1.14–1.71.** Medians are $67,032 / $66,933 in
IS against $38,242 / $38,166 in OOS, so this is a genuine split on the
feature rather than a relabelled one.

**This is the thing that has been missing all round.** Every adaptive gate
attempted since P55 has been a feature the eras could not be separated on —
swing geometry (P55), absolute ATR (P67, buggy). Price is not latent, needs
no identification, and is readable at decision time from a single quote.

**And it is consistent in the era that was never fitted, which is the test
that killed `cand_4h1h`.** `cand_4h1h` was 4-4 in IS. This is 4-4 across
both eras.

## Why it is still not adopted

**Both halves are profitable.** A price filter cannot work by halving a book
whose halves are both profitable — LOW px is **+207.5R of the +325.8R** in
IS and **+41.7R of the +70.1R** in OOS. Dropping the high-price half
removes ~59% of IS trades and ~40% of OOS trades to buy a PF improvement on
what remains, and the removed trades were net positive. **That is a smaller,
slightly better book — a trade, not a free gain, and exactly the shape of
every candidate that has come before.**

**The median is the threshold problem again.** The split point is a quantile
of the trade distribution rather than an absolute price level, so a live
threshold would have to be recomputed continuously or searched — and
searching an absolute price level now, with these four cells already in
view, is fitting to a known answer.

**And a rising price is not something you can gate on.** A price floor is
monotone in time by construction: any fixed threshold trades in 2021 and
stops trading in 2026. **That is not a regime detector, it is a clock.** It
would have to be relative — against the era's own median or a longer-term
mean — and *that* version is untested.


## What is now queued, and what is not

| item | status |
|---|---|
| **Volatility CEILING** (corrected direction) | **new pre-registration, not run.** This run's grid was the wrong sign and is not reused. |
| **Relative-price feature** (price ÷ trailing median) | **untested, and this is the live-computable form** — worth more than the level, because a level is a clock. |
| Price/volatility interaction | not run — stacking two filters and testing the product is how fitted artefacts get built. |

## Stated limitations

- **Price halves are ~125–251 trades** — enough to see a 1.14–1.71 PF gap,
  not enough to call it.
- **Both lanes are the same data.** Their agreement is not independent.
- **The IS price range spans $16,640–$124,108**, a full bull and bear cycle
  inside one era, so the low/high split mixes regimes rather than only
  separating quiet from loud markets.
- **Price and volatility are not independent** — that is exactly the bug
  P67 made — so neither this table nor the ceiling test isolates one from
  the other. Relative measures of both are required before attributing
  anything.
- **No threshold was searched, and the next run must not search one.**

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
