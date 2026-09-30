# Can the regime inversion be detected at runtime? No — and the reason is informative

> Run 2026-09-29. Harness `exp_regime_detect.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question this was meant to answer

P54 found the 1h swing geometry is strongly predictive **inside** each era
and **opposite across** them — IS wants big and long swings (`dur > 19 bars`
gives PF 3.59, WR 35.9% against a book WR of 29.9%), OOS wants small and
short (`dur ≤ 7 bars` gives PF 2.41 against a book PF of 1.77).

Three other features show the same shape: window age, leg position, and the
1h-decay gate. **If the current regime could be identified at the instant a
window opens, any of them could become a rule.** So: can it?

## The pre-registered pre-test, and it settles the family

**REGIME** = mean of `(swing travel / ATR)` over the last K confirmed 1h
swings, K ∈ {8, 16, 24} — a time-blended measure, because percentiles of
realised outcomes are not knowable live. Split point = the median of that
measure over its own trailing window, so nothing is fitted.

| K | champ IS p50 | champ OOS p50 | **gap** | | utcsat IS | utcsat OOS | **gap** |
|---|---|---|---|---|---|---|---|
| 8 | 4.79 | 4.78 | **0.01** | | 4.79 | 4.78 | **0.01** |
| 16 | 4.83 | 4.77 | **0.06** | | 4.83 | 4.73 | **0.10** |
| 24 | 4.79 | 4.73 | **0.05** | | 4.79 | 4.72 | **0.08** |

**The gaps are 0.01–0.10 on a measure whose own interquartile range is about
0.75** (p25 4.37 → p75 5.11 in champion IS). That is a separation of
roughly **1–13% of the spread** — for practical purposes zero, and it does
not improve with a longer window, which is what it would do if the eras
genuinely differed in volatility structure.

**PART B was therefore not run.** It was pre-registered to run only if
Part A separated, and running it against a signal that does not separate
would produce a table of noise that reads like results.

## What this actually tells us — and it is the important part

**The 1h swing-size distribution is essentially identical in the two eras,
and the book still prefers big swings in one and small swings in the
other.**

That is a much stronger statement than "the gate did not work". It means:

> **The input is the same. Only the response differs.**

The same swing geometry, drawn from the same distribution, produces a
PF 3.59 book in one era and a PF 1.45 book in the other. So the inversion
**is not a property of the market's structure that a live classifier could
read** — it is a property of how that structure paid off, which is an
outcome.

**Any classifier that could distinguish these two regimes would have to be
reading realised results. That is the future.** Which is exactly why four
separate attempts to gate on 1h structure have failed while the underlying
effects stayed real and strong inside each era.

## The consistent shape of the whole 1h thread

| feature | effect inside an era | eras agree | convertible to a rule |
|---|---|---|---|
| window age | p75 cohort beats book 4/4 | yes | no — era-flip on fade |
| leg position | PF 4.5 vs 1.05 | **no — reverses** | no — 0/15 ranges |
| 1h decay gate | negative IS, positive OOS | **no** | no — 0.13 × M |
| swing geometry | PF 3.59 vs 1.77 | **no — full inversion** | no — **regime undetectable** |
| 1h streak gate | +180.9R then −234.2R | — | **no — lookahead** |
| 1h oracle early read | DEAD is impossible | — | no — nothing to read |

**Six attempts, six structural reasons, one pattern: the 1h layer's
information is real, era-dependent, and not separable at decision time.**

## Verdict

**The family is closed, on evidence rather than on effort.** The 1h layer
cannot be improved by gating its structure, because the structure does not
carry the era and the era is what decides which structure to trade.

The remaining honest option is not a classifier but a **decision**: if the
1h layer's job is only to supply direction, and its own P&L is worth nothing
(P3), then the question worth asking is whether a *cheaper* direction source
— or none at all — does the same job. That is a different experiment, and
the queue does not currently contain it.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
