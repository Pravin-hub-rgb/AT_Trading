# P78 — THE MECHANISM: the hybrid's edge is the LONG side in the bear era

> Run 2026-09-29. Harness `exp_fs_mechanism.py`. **Diagnostic. Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **This does not make the candidate adoptable — P77 already closed it. It
> says what the candidate was actually doing, which is worth more.**

## Part A first: the utcsat lane, which truncated at P77

| period | champion n / R/t | hybrid n / R/t | winner |
|---|---|---|---|
| 2021H1 | 69 / +0.041 | 89 / +0.083 | hyb |
| 2021H2 | 68 / +0.152 | 77 / +0.513 | hyb |
| 2022H1 | 60 / +0.465 | 79 / +1.177 | hyb |
| 2022H2 | 56 / +0.921 | 81 / +1.126 | hyb |

**utcsat OOS: 4 wins, 0 losses. utcsat IS: 2 wins, 6 losses.**

Identical in shape to the champion lane (4-0 and 2-6), so the two lanes
agree and the P77 verdict is not a champion-lane artefact. **The truncated
cell is now read, and it changes nothing.**

## The hypothesis

BTC in 2021H2–2022H2 was a sustained bear market. In a falling market a
**break** entry fires when price breaks a structure extreme — which in a
downtrend are rallies that fail, so the entry is **late**. An **FS** entry
fires when structure is first declared, which in a downtrend is nearer the
high, so it is **early**.

**If that is the mechanism, the hybrid's edge should sit on the SHORT side.**
It does not. **It sits almost entirely on the LONG side** — which is the
opposite of the prediction, and far more interesting.

## Part B — the finding

**OOS (2021–2022, the bear era):**

| book | LONG | SHORT | ALL |
|---|---|---|---|
| champion | 162t **+1.8R** R/t +0.011 **PF 1.22** | 117t +68.4R R/t +0.584 PF 2.10 | 279t +70.1R PF 1.59 |
| FS hybrid | 199t **+93.3R** R/t +0.469 **PF 2.44** | 165t **+140.2R** R/t +0.850 PF 3.22 | 364t +233.6R PF 2.81 |

**IS (2023–2026):**

| book | LONG | SHORT | ALL |
|---|---|---|---|
| champion | 273t +272.6R R/t +0.998 PF 3.01 | 227t +53.2R R/t +0.234 PF 1.69 | 500t +325.8R PF 2.38 |
| FS hybrid | 350t **+346.0R** R/t +0.989 **PF 4.24** | 296t +59.2R R/t +0.200 PF 1.78 | 646t +405.2R PF 2.99 |

**Read the two tables together and the mechanism is unambiguous:**

1. **The champion's OOS long side is effectively dead: +1.8R across 162
   trades at PF 1.22.** Not weak — *nothing*. The champion's entire OOS
   result is its 117 short trades.
2. **The hybrid rescues precisely that dead side: +93.3R at PF 2.44.** Its
   long book goes from worthless to 2.4 PF.
3. **In IS the same long side is already healthy for both** (+272.6R PF 3.01
   champion, +346.0R PF 4.24 hybrid) — so **the hybrid's long-side edge is
   a bear-era rescue, not a general long-side improvement.**
4. **The short side is near-identical between the two books in both eras**
   (IS +53.2R vs +59.2R; OOS +68.4R vs +140.2R on more trades).

## So the bear-market story was half right and half wrong

**Right:** the advantage is era-dependent and concentrated in the bad years.

**Wrong:** it is not a "be earlier in downtrends" story. **A downtrend would
help SHORTS, and the short sides are unchanged.** What actually happened is
that **the champion cannot trade long in a bear market at all, and the FS
book can.** The hybrid did not get better at falling markets — it got
*unstuck*, on the side that was broken.

That is a materially different finding, and it is the kind that would have
been reported wrongly if the run had stopped at the aggregate. The
hypothesis was stated in advance, the data refuted its main clause, and the
refutation is the useful part.

## What is generalisable from this

Not "use the FS engine" — that loses 6 of 8 IS half-years.

**The finding worth carrying forward is narrower and more useful:**

> **Break-entry triggers systematically fail on the long side in sustained
> downtrends, and an earlier structural trigger recovers them. The long side
> is where the champion is fragile, and it is fragile in a way that is
> visible without any regime detection.**

That is actionable in a way the regime-switch idea was not. P55, P67 and
P68 all failed because the eras could not be told apart *at decision time*.
**This does not require telling them apart** — it says one specific side of
one book has a structural defect in one kind of market, and that defect is
visible in the trade record rather than in a classifier.

**Which does not make it a rule yet**, because "detect a downtrend" is the
same separation problem that has already failed three times. What it does
establish is *where to look*: the long side, not the timeframe, not the
regime, not the exit.

## Stated limitations

- **`dir` is the trade's direction, not a verified exposure.** Shorts in a
  bear market may still be hedged elsewhere; nothing here checks the rest of
  the book.
- **Hold length moves the opposite way from the hypothesis.** Median hold is
  **63 → 99 bars** (OOS) and **58 → 111 bars** (IS) — the hybrid holds
  *longer*, not less. So the "earlier entry" half of the story is not
  supported by the pace data either. **The only clause the data supports is
  the long-side one.**
- **The utcsat direction split is not printed** — only its half-year split.
  The mechanism claim rests on the champion lane.
- **Both lanes are the same data.**
- **Nothing here was grouped by a realised field.** Direction and hold
  length are properties of when a trade happened, not what it earned, so the
  P52 lookahead does not apply — but that is an argument, not a proof.

## Status

**The candidate stays closed (P77). The mechanism is now named, and it points
somewhere this programme has not looked: the long side of a break-entry book,
rather than the timeframe, the regime or the exit.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS. Nothing adopted.
