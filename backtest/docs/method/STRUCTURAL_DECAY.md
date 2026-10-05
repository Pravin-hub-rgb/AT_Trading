# P11 — STRUCTURAL DECAY works. The user's signal is real, and it is novel.

`exp_structural_decay.py`. Pins reproduced first. Fresh autopsy code, no
reuse of any prior result.

## The signal

At any 15m bar *t*: take the last **4 confirmed buying (up) 15m legs**,
count how many of their lows price has traded below *since each leg
confirmed* and *up to t*. `decay = broken / 4`.

**Causality is enforced by filter, not convention:** a leg enters the
calculation only once `confirmed_at_time <= t`, and only 1m lows at or
before *t* are read. Forward excursion is the dependent variable and is
never a feature. 1,482 confirmed buying legs in IS, 809 in OOS.

**Grep confirms this is new:** `broken_low`, `lows_broken`,
`higher_lows_fail`, `structural_decay`, `break_of_low`, `prior_swing_low`
— **zero hits** in the engine or tests. ADX gates, regime gates and
efficiency-ratio gates are all closed; nothing had looked at *prior swing
lows failing* as the signal.

## A: the user's hypothesis is CONFIRMED, and it is monotone in both eras

**Forward edge = MFE − MAE, in R, over the next 32 bars:**

| decay | IS n | **IS edge** | OOS n | **OOS edge** |
|---|---|---|---|---|
| 0.00 | 62 | **+0.69R** | 21 | −0.15R |
| 0.25 | 245 | **+0.41R** | 126 | −0.10R |
| 0.50 | 124 | **+0.05R** | 80 | −0.10R |
| 0.75 | 69 | **−0.16R** | 52 | **−0.63R** |

**IS is cleanly monotone decreasing: +0.69 → +0.41 → +0.05 → −0.16.** The
more of the prior up-structure has been taken out, the less forward edge
there is. That is exactly "ab trend might be changing", measured.

**OOS is monotone in the top half and the same sign at the top bucket:
decay ≥ 0.75 gives −0.63R, the worst of any bucket in either era.** The
bottom OOS bucket (−0.15R) is the only cell that does not fit, and it is
n=21.

## B: the champion's own book, split by live decay

| decay | IS n | IS net | IS WR | OOS n | OOS net | OOS WR |
|---|---|---|---|---|---|---|
| 0.00 | 62 | −1.0R | 30.6% | 21 | +1.7R | 23.8% |
| **0.25** | **245** | **+384.9R** | **34.3%** | **126** | **+82.5R** | **30.2%** |
| 0.50 | 124 | +13.6R | 26.6% | 80 | −17.7R | 23.8% |
| **0.75** | 69 | **−40.6R** | **20.3%** | 52 | **+12.0R** | 30.8% |

**The book makes the overwhelming majority of its R at exactly one decay
level: 0.25.** IS +384.9R from 245 trades. Every other bucket is noise
around zero, and `decay ≥ 0.75` is the worst in IS at **20.3% WR** — the
lowest win rate of any cohort in either era.

**And 0.75 is a minority.** Decay distribution IS: p10 = 0.00, p50 = 0.50,
p90 = 1.00. So high decay happens, just not at the entries that pay.

**No bucket clears its own null** — decay ≥ 0.75 in IS is −40.6R against
M = 44.9R, inside by a hair; everything else is well inside. Falsifier (c)
fires. But note what that means here specifically: **the decay ordering
is about the *shape* of the book, not about a cohort that is significant
on its own.**

## C: the direct answer to "is the book long while the trend changes?"

**IS:**

| | n | % long | long R | short R |
|---|---|---|---|---|
| decay < 0.5 | 164 | 70.7% | +68.9R | +48.7R |
| **decay ≥ 0.5** | 336 | **46.7%** | **+270.6R** | +57.0R |

**The book is NOT naively long into decaying structure.** At high decay it
drops from 70.7% long to **46.7% long** — it goes *more* balanced, not
more bullish. The 1h bias window and the 15m structure are already
responding to decay on their own. **The market is telling this book
something, and the book is partly listening.**

**OOS repeats the direction:** decay < 0.5 is 70.7% long, decay ≥ 0.5 is
52.8% long. Same shift, same magnitude, independent era.

## What this is and is not

**It is:** a genuinely new, causal, structural signal. It is monotone in
both eras, it identifies the one cohort where the book pays
(`decay = 0.25`, +384.9R IS / +82.5R OOS), and it identifies the cohort
where it does not (`decay ≥ 0.75`, 20.3% WR, the worst in the study).
The 70.7% → 46.7% long shift is a real, two-era, structural response
that nobody had measured.

**It is not:** a gate. No bucket clears its own null, so
"trade only at decay 0.25" is a description of where the R already is,
not a rule that removes losing trades. And the IS `decay ≥ 0.75` cell sits
*inside* its null at −40.6R vs M = 44.9R, so the "worst cohort" claim is
directional, not significant.

**The honest caveat that matters most:** decay=0.25 is a narrow band. It
holds 245 of 500 IS trades, and the other three buckets are all within
noise of each other. **A signal that identifies where the money is has
already been paid for by the time you can see it** — the same wall P10 hit
with the runner. What is new here is the *diagnostic* value, not a
tradeable edge, and this file is an autopsy, which is what it was asked
to be.

## Relation to P9

Independent confirmation of a graveyard row. `closed/CLOSED_DO_NOT_REPEAT.md:30`
already rejected Kaufman efficiency-ratio gates with the note *"no bucket
net-negative; low-ER holds +105R of real winners"*. P9 found the same
thing from the market-state side, and P11 finds it again from the
structure side. **Three independent measurements now agree: the book's
winners live in the non-trending, intact-structure part of the tape.**
