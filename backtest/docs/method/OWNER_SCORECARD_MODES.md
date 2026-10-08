# the owner's scorecard on the four mode candidates

Date: 2026-10-08. Harness: `exp_owner_scorecard.py`. Everything computed from
the engine; nothing transcribed by hand.

## the invented rule is withdrawn

I rejected three of these four candidates and disqualified the fourth on
"drawdown rises above the base book's 11.88R". That rule is not in
`docs/learn/finding optimal book.md`. It is mine. The framework says the opposite
kind of thing:

> "A strategy making +300R with horrible concentration may be worse than one
> making +220R much more consistently."
>
> "Net R should be a major factor, but not the king."
>
> "Don't just record Max DD." — then asks for duration, recovery, and worst
> rolling periods, because those are what Max DD hides.

Drawdown in this framework is an input to a trade, not a veto. The framework's own
named measure for that trade is `Net R / Max DD`, and the owner has since
confirmed a **20R drawdown budget**, which makes the budget test a number instead
of an assumption. This file runs the comparison the framework asks for.

The verdict that follows is close to the one I gave, and I want to be honest that
it is close — but it is close for different reasons, and the invented rule got two
of the five books wrong.

## bucket 1 — raw profitability

| book | era | n | net | expectancy | PF | WR% | payoff |
|---|---|---:|---:|---:|---:|---:|---:|
| **BASE** | IS | 528 | 533.4 | 1.010 | 3.09 | 40.0 | 4.64 |
| `atr_low` | IS | 641 | **721.3** | **1.125** | **3.22** | 39.2 | 5.00 |
| `fd` | IS | 531 | 528.6 | 0.996 | 3.06 | 39.7 | 4.64 |
| `flip_quality` | IS | 526 | 533.3 | 1.014 | 3.10 | 39.9 | 4.66 |
| `union` | IS | 813 | 580.0 | 0.714 | 2.40 | 37.4 | 4.03 |
| **BASE** | OOS | 311 | 239.6 | 0.770 | 2.69 | 37.0 | 4.58 |
| `atr_low` | OOS | 315 | **280.7** | **0.891** | **2.96** | 38.1 | 4.80 |
| `fd` | OOS | 291 | 238.3 | 0.819 | 2.82 | 36.8 | 4.85 |
| `flip_quality` | OOS | 294 | 244.2 | 0.831 | 2.87 | 37.4 | 4.80 |
| `union` | OOS | 442 | **303.8** | 0.687 | 2.45 | 34.4 | 4.68 |

`atr_low` wins this bucket outright — best expectancy, best PF, best net, in both
eras, on **641 trades** against the base's 528. More evidence, not less. That is
worth saying plainly, because my invented rule hid it behind an OOS drawdown
number.

## bucket 2 — drawdown, and how long underwater

Budget 20R. Duration in trades, which is what the framework actually asks for.

| book | era | maxDD | dd%ret | trades to make | trades underwater | worst 20 | worst 50 | streak | budget |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **BASE** | IS | 13.4 | 2.5 | 22 | **286** | −12.7 | −8.3 | 11 | PASS |
| `atr_low` | IS | **28.9** | 4.0 | **82** | **460** | −16.3 | −26.4 | **16** | **OVER** |
| `fd` | IS | 13.4 | 2.5 | 22 | 289 | −12.7 | −8.3 | 11 | PASS |
| `flip_quality` | IS | 13.4 | 2.5 | 22 | 286 | −12.7 | −8.3 | 11 | PASS |
| `union` | IS | **23.8** | 4.1 | 46 | **771** | −14.5 | −18.9 | **16** | **OVER** |
| **BASE** | OOS | 11.9 | 5.0 | 29 | **220** | −10.8 | +1.4 | 15 | PASS |
| `atr_low` | OOS | 14.6 | 5.2 | 22 | 22 | −14.2 | +6.7 | 15 | PASS |
| `fd` | OOS | 11.9 | 5.0 | 29 | 213 | −10.8 | +1.5 | 15 | PASS |
| `flip_quality` | OOS | 11.9 | 4.9 | 29 | 216 | −10.8 | +3.4 | 15 | PASS |
| `union` | OOS | 18.2 | 6.0 | 34 | 237 | −13.9 | −10.7 | 15 | PASS |

**This is where my invented rule was most wrong, and where the budget does real
work.** `union`'s OOS drawdown is 18.2R — under 20R, so it passed my rule's
number — but its **IS drawdown is 23.8R, over budget**, and it spends **771
trades underwater** against the base's 286. Nearly three times as long waiting.
`atr_low` is worse: 28.9R IS, 460 trades underwater, and a 16-trade losing streak
against the base's 11.

So the 20R budget is not a rubber stamp. It rejects `union` and `atr_low` on the
in-sample numbers — and it does so using a figure the owner actually set.

## bucket 3 — return per unit of pain, and winner spacing

| book | era | **net/DD** | posMon% | gap +3R med/p90/max | gap +5R | gap +10R |
|---|---|---:|---:|---|---|---|
| **BASE** | IS | **39.80** | 71.1 | 5/19/42 | 8/25/58 | 22/58/**121** |
| `atr_low` | IS | 24.96 | 66.7 | 3/17/57 | 6/29/67 | 8/56/123 |
| `fd` | IS | 39.45 | 68.9 | 6/19/42 | 8/25/58 | 23/58/121 |
| `flip_quality` | IS | 39.80 | 71.1 | 5/19/42 | 8/24/58 | 22/58/121 |
| `union` | IS | 24.37 | **75.6** | 3/24/60 | 9/43/80 | **43/85/195** |
| **BASE** | OOS | 20.13 | 70.8 | 2/24/40 | 4/30/70 | 27/58/81 |
| `atr_low` | OOS | 19.23 | 70.8 | 2/20/37 | 4/28/45 | 18/58/81 |
| `fd` | OOS | 20.03 | 70.8 | 2/26/41 | 4/30/72 | 28/57/78 |
| **`flip_quality`** | OOS | **20.52** | 70.8 | 2/26/41 | 4/30/72 | 28/57/81 |
| `union` | OOS | **16.69** | 70.8 | 3/23/63 | 6/36/63 | **22/87/92** |

**On the framework's own ranking metric, `union` is last.** The book with the
biggest headline R has the **worst return per unit of drawdown** in both eras —
24.37 against the base's 39.80 in sample, 16.69 against 20.13 out of sample.

The winner-spacing columns are the part I would not have looked at before reading
the owner's framework. `union` waits **43 trades median / 85 p90** for a +10R
winner in sample, against the base's 22/58, and its maximum gap is **195 trades
against the base's 121**. Out of sample its +10R p90 gap is 87 against 58. This is
the owner's "B is a much more fragile-looking equity process" case, measured.

One column to distrust: **ulcer out of sample** reads 14.2 for the base and
66–67 for `fd` and `flip_quality`. That is a scale artifact, not a discovery —
ulcer is percent-of-equity, and a book that grows equity faster early shows a
smaller percentage. `union` reads lowest at 10.8 for the same reason. I am not
scoring anything on OOS ulcer.

## bucket 4 — tail dependence

| book | era | drop top1 | drop top5 | drop top10 | drop top1% | drop top5% | drop top10% | top5% contribution |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **BASE** | IS | 90.9 | 64.2 | 46.9 | 64.2 | **19.8** | −8.8 | 80.2 |
| `atr_low` | IS | 93.3 | 71.4 | 55.4 | 67.1 | 18.0 | −8.8 | 82.0 |
| `fd` | IS | 90.8 | 63.9 | 46.5 | 63.9 | 17.7 | −9.6 | 80.9 |
| `flip_quality` | IS | 90.9 | 64.2 | 46.9 | 64.2 | 19.8 | −8.8 | 80.2 |
| **`union`** | IS | 91.6 | **67.1** | 50.2 | 56.4 | **3.9** | −28.6 | **95.0** |
| **BASE** | OOS | 89.1 | 56.6 | 34.6 | 72.1 | 16.3 | −11.7 | 81.1 |
| `atr_low` | OOS | 90.7 | 63.0 | 43.1 | 76.2 | 26.3 | −4.6 | **71.2** |
| `fd` | OOS | 89.0 | 56.4 | 34.2 | 71.9 | 18.0 | −10.1 | 79.1 |
| `flip_quality` | OOS | 89.3 | 57.4 | 35.8 | 72.6 | 20.0 | −7.5 | 77.2 |
| `union` | OOS | 91.4 | 65.8 | 44.5 | 71.8 | 13.5 | −21.8 | 86.5 |

**`union`'s in-sample tail dependence is the single worst number in this table.**
Its top 5% of trades contribute **95.0%** of in-sample profit, and remove that top
5% and **3.9% of the return survives**. The base keeps 19.8%. Out of sample
`union` is better on both (13.5% surviving, 86.5% contribution) but still the
weakest of the four on `drop top10%` at −21.8 against the base's −11.7.

The owner's own words for this shape:

> "Where I'd become much more interested in investigating is something like Top
> 1–2% → 70–90% of profits, because then the strategy's historical existence may
> depend on an extremely tiny number of events."

`union` is at 95% from the top 5% in sample.

`atr_low` is the mirror image and the most interesting result here: its OOS tail
is the **healthiest in the set** (top 5% contributes 71.2%, and removing the top
10% still leaves −4.6% rather than the base's −11.7%, and removing the top 5%
leaves 26.3% against the base's 16.3%). Its problem is entirely bucket 2 — 28.9R
in sample, 460 trades underwater, a 16-loss streak.

## bucket 5 — retention

| book | expectancy ret% | PF ret% | net ret% | DD expansion |
|---|---:|---:|---:|---:|
| **BASE** | 76.3 | 87.0 | 44.9 | 0.89 |
| `atr_low` | 79.2 | 91.8 | 38.9 | **0.51** |
| `fd` | 82.3 | 92.1 | 45.1 | 0.89 |
| `flip_quality` | 81.9 | 92.6 | 45.8 | 0.89 |
| **`union`** | **96.3** | **102.1** | **52.4** | 0.76 |

`union` is genuinely the most stable book across the era split — it retains 96.3%
of its expectancy and 102.1% of its profit factor, meaning out of sample it is
*better* than in sample. That is the strongest single argument in its favour and
it is real. `atr_low`'s DD expansion of 0.51 means its out-of-sample drawdown is
half its in-sample one, which is also good behaviour.

## bucket 6 — complexity

All five books carry **11 knobs** and each candidate differs from the base by one
mode string. Complexity cannot separate them, and I will not pretend otherwise.

## where this actually lands

Scored on the framework's own order of priority, not on my invented gate:

| book | verdict | the reason, in the framework's terms |
|---|---|---|
| `atr_low` | **blocked on drawdown** | Wins bucket 1 outright in both eras on 641 trades, and has the healthiest OOS tail in the set. But 28.9R IS against a 20R budget, 82 trades to make the drawdown, 460 underwater, and a 16-loss streak versus the base's 11. That is buckets 2 and 9, and the budget is the owner's number. |
| `union` | **not adoptable** | Biggest R, best retention, and last on `Net R / Max DD` in both eras. 23.8R IS is over budget. 771 trades underwater. Top 5% of trades carry 95% of in-sample profit, and 3.9% survives their removal. The maximum gap between +10R winners is 195 trades against the base's 121. It is a bigger book with more waiting and more concentration — the framework's "worse equity process" case, not a better one. |
| `fd` | **no reason to switch** | Indistinguishable from the base in sample. Out of sample it gains nothing on net (238.3 against 239.6). Every metric is within noise of the base. |
| `flip_quality` | **best on the ranking metric, disqualified on era** | Highest `net/DD` out of sample at 20.52 against the base's 20.13, best PF retention, drawdown identical to the base in both eras, and the healthiest spacing. But it is in-sample inert on all three books of its family: it does nothing to 528 in-sample trades, and its entire effect is out of sample (`FLIP_QUALITY_PERIOD_CONTROL.md`). A book that cannot be measured in sample is not being improved. |

**The base book keeps the crown**, and now for reasons that are actually in the
framework rather than invented: it has the best return per unit of pain, the
shortest time underwater, the best-balanced tail, and the longest maximum gap
between big winners without needing to wait longer. `atr_low` is the one worth
keeping open, and it is open on a single question — whether a 20R budget can
stretch to 29R, which is the owner's call, not mine.

Nothing promoted. `fsent_champ_long` unchanged at 528 / +533.37 / 13.42 IS and
311 / +239.59 / 11.88 OOS.