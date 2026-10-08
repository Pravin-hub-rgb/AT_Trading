# underwater duration in calendar time, and where the four modes actually rank

Date: 2026-10-08. Harness: `exp_duration_calendar.py`.

## three bugs in my own reporting, in order of how badly they misled

**1. "Underwater" in trades was not underwater at all.** The first version never
fired its recovery detector and printed "trades from the peak to the end of the
sample". That produced 286 for the base book, 460 for `atr_low`, 771 for `union`,
and I built an argument on `union` sitting underwater three times longer than the
base. **That argument was false.** The corrected trade counts are 25, 99 and 47.

**2. Trades are the wrong unit for this question.** The framework's complaint is
about wall-clock pain:

> "Not only 'How deep did it fall?' but 'How long was I underwater?'"

But this set spans 528 to 813 trades on books that differ by one knob, so a book
with more trades shows more "underwater trades" for the same elapsed time. Only
calendar time compares across books.

**3. The episode counter reported one episode per book and always unrecovered.**
Rewritten; the counts below are real. All five books sit underwater at some point
in ~100% of the era across 63–132 separate episodes, which is normal for a book
with a right tail: it bleeds in many small bites and one real dip. The number that
carries information is the **longest single episode**, not the total.

## the max drawdown, in calendar units

**IS — 44.3 months of data**

| book | maxDD | make (wk) | make (mo) | recover (wk) | recover (mo) | underwater (mo) | % of era |
|---|---:|---:|---:|---:|---:|---:|---:|
| **BASE** | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 2.2 | **5.0%** |
| `atr_low` | **28.9** | **24.9** | **5.7** | 3.1 | 0.7 | **6.5** | **14.7%** |
| `fd` | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 2.2 | 5.0% |
| `flip_quality` | 13.4 | 9.3 | 2.2 | 0.3 | 0.1 | 2.2 | 5.0% |
| `union` | 23.8 | 13.3 | 3.1 | 0.3 | 0.1 | 3.1 | 7.1% |

**OOS — 23.9 months of data**

| book | maxDD | make (wk) | make (mo) | recover (wk) | recover (mo) | underwater (mo) | % of era |
|---|---:|---:|---:|---:|---:|---:|---:|
| **BASE** | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 2.7 | 11.2% |
| **`atr_low`** | 14.6 | **7.6** | **1.8** | **0.0** | **0.0** | **1.8** | **7.4%** |
| `fd` | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 2.7 | 11.2% |
| `flip_quality` | 11.9 | 11.1 | 2.5 | 0.6 | 0.1 | 2.7 | 11.2% |
| `union` | 18.2 | 8.4 | 1.9 | 0.6 | 0.1 | 2.1 | 8.7% |

## every episode, not just the deepest

| book | era | episodes | longest (mo) | median (mo) | deepest (R) | unrecovered |
|---|---|---:|---:|---:|---:|---:|
| **BASE** | IS | 104 | **5.1** | 0.1 | 13.4 | 1 |
| `atr_low` | IS | 132 | 7.0 | 0.0 | 28.9 | 1 |
| `fd` | IS | 104 | 5.1 | 0.1 | 13.4 | 1 |
| `flip_quality` | IS | 104 | 5.1 | 0.1 | 13.4 | 1 |
| `union` | IS | 119 | 7.3 | 0.0 | 23.8 | 1 |
| **BASE** | OOS | 65 | 2.7 | 0.1 | 11.9 | 1 |
| `atr_low` | OOS | 72 | 2.3 | 0.1 | 14.6 | 1 |
| `fd` | OOS | 63 | 2.7 | 0.1 | 11.9 | 1 |
| `flip_quality` | OOS | 66 | 2.7 | 0.1 | 11.9 | 1 |
| `union` | OOS | 74 | **3.9** | 0.1 | 18.2 | 1 |

## the two things worth reading off this

**Recovery is fast for everyone. The pain is in falling, not in getting back.**
Every book's worst recovery is 3.1 weeks (`atr_low`, in sample) and everything else
is under a week. Nobody sits underwater for months after the turn. The duration
that matters is the descent: `atr_low` takes **5.7 months to fall 28.9R**, against
the base book's 2.2 months to fall 13.4R. That is a slow bleed, and it is the
real objection to `atr_low` — not the depth alone.

**Out of sample the base book's underwater time is the worst of the five.** It
spends 11.2% of the OOS era under water and takes 2.5 months to fall 11.9R, while
`atr_low` takes 1.8 months and is under water 7.4% of the time. **The base book is
the shallowest book in sample and the most drawn-out one out of sample.** That is
the opposite of what I reported before the metric was fixed.

## where each book actually ranks

Rank order on the framework's own priority list — OOS performance, then retention,
then drawdown and duration, then tail, with raw Net R last.

| criterion | 1st | 2nd | 3rd | 4th | 5th |
|---|---|---|---|---|---|
| OOS net | `union` 303.8 | `atr_low` 280.7 | `flip` 244.2 | **BASE** 239.6 | `fd` 238.3 |
| OOS expectancy | **`atr_low`** 0.891 | `fd` 0.819 | `flip` 0.831 | — | BASE 0.770 |
| OOS profit factor | **`atr_low`** 2.96 | `fd` 2.82 | `flip` 2.87 | — | BASE 2.69 |
| OOS Net R / Max DD | `flip` 20.52 | **BASE** 20.13 | `fd` 20.03 | `atr_low` 19.23 | `union` 16.69 |
| OOS max DD | **BASE** 11.9 | `atr_low` 14.6 | `union` 18.2 | | |
| OOS underwater % | **`atr_low`** 7.4 | `union` 8.7 | **BASE** 11.2 | | |
| OOS tail, survive drop top 5% | **`atr_low`** 26.3 | `flip` 20.0 | `fd` 18.0 | BASE 16.3 | `union` 13.5 |
| OOS expectancy retention | **`union`** 96.3 | `fd` 82.3 | `flip` 81.9 | `atr_low` 79.2 | BASE 76.3 |
| IS net | **`atr_low`** 721.3 | `union` 580.0 | **BASE** 533.4 | | |
| IS Net R / Max DD | **BASE** 39.80 | `fd` 39.45 | `atr_low` 24.96 | `union` 24.37 | |
| IS max DD vs 20R budget | **BASE** 13.4 | `atr_low` **28.9** OVER | `union` 23.8 OVER | | |

## the answer

**`atr_low` is the best-performing book in this set.** It is first or second on
almost every out-of-sample criterion — expectancy, profit factor, underwater time,
tail survival — and first outright in sample on net, expectancy and profit factor,
on 641 trades against the base book's 528. It is the only candidate that improves
on the base in sample *and* out of sample rather than trading one for the other.

It is blocked on one number, and it is the owner's number: **28.9R of in-sample
drawdown against a 20R budget, reached over 5.7 months.** Its out-of-sample
drawdown is 14.6R, inside budget, and its out-of-sample underwater time is the
shortest of the five at 7.4% — so the budget objection is an in-sample figure and
a slow-descent figure, not an out-of-sample pain figure.

**`union` is the biggest earner and the worst-adjusted.** Highest OOS net and
highest retention in the set, last on Net R / Max DD in both eras, top 5% of
in-sample trades carrying 96.1% of the profit with 3.9% surviving their removal,
and the longest single underwater episode at 7.3 months.

**The base book** keeps the best in-sample Net R / Max DD and the lowest drawdown,
and has the worst out-of-sample underwater time of the five at 11.2%.

`fd` is indistinguishable from the base in sample and gains nothing out of sample.
`flip_quality` has the best out-of-sample Net R / Max DD and stays disqualified on
the separate era finding — it does nothing to any in-sample trade.

**So the single question standing between the repo and a better book is whether a
20R budget can stretch to 29R. That is a capital decision, not a research one.**
Nothing promoted; `fsent_champ_long` unchanged at 528 / +533.37 / 13.42 IS and
311 / +239.59 / 11.88 OOS.