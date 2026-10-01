# P84 — THE TREND-MA FIXES THE LONG SIDE AND BREAKS THE BOOK

> Run 2026-09-29. Harness `exp_long_trend_filter.py`. **NOT ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The owner's question is answered yes, and the answer does not help.**

## The question

> *"2021 was a breakdown — selling. How do we prevent the long side?"*

P78 located it: the champion's OOS long side is absent — 162 trades for
+1.8R at PF 1.22. P83 showed the shape: 2021 is a whole losing year at
−26.4R net with three of four quarters negative. BTC fell roughly $69k to
$15k. **A long book with no trend filter buys every rally into that.**

## The filter

Long entries kept only while the 1h close is **above** its trailing M-bar
mean; shorts only while **below**. Trend-with, both sides — a filter built
only for the failing side would not be evidence. Four windows pre-registered
(50/100/200/400 hours = 2/4/8/16 days), **family-wise**: all four must
beat in both eras both lanes, clear M = 193.4R, and survive the half-year
partition.

## The answer to the question: yes, it works on the long side

| | trades | net | PF |
|---|---|---|---|
| champion OOS **LONG** | 162 | **+1.8R** | **1.22** |
| MA200 OOS **LONG** | 102 | **+18.4R** | **1.48** |

**The dead side comes back to life.** That is a real mechanism and it is the
one the owner named.

## And it costs more than the long side was worth

| arm | champ IS | champ OOS | partition IS | partition OOS |
|---|---|---|---|---|
| MA50 | −183.0R | −26.1R | 4-4 | 2-2 |
| MA100 | −119.3R | −67.8R | 3-5 | 1-3 |
| MA200 | −80.6R | −49.1R | **6-2** | 2-2 |
| MA400 | **+31.9R** | −34.3R | **7-1** | 3-1 |

**Not one window is positive in both eras. None clears M.** The
family-wise criterion — four windows, all must pass — is met by nothing.

## Why: the filter is not a long-side filter in practice

**MA50 removes 161 IS trades and 101 OOS trades to save a side that was
worth +1.8R.** The long side was small; the short side was carrying the
book; and the same condition that blocks a bad long also blocks most of
the good shorts, because in a trending market most of *any* side's signals
sit against the average.

Look at the partition columns to see it moving:

| | MA200 | MA400 |
|---|---|---|
| IS half-years won | 6 of 8 | **7 of 8** |
| OOS half-years won | 2 of 4 | **3 of 4** |

**A longer window behaves better and better — MA400 wins 7 of 8 IS
half-years — while still losing money overall.** That is the signature of a
filter that removes more good than bad, in a period where the good is bigger
than the bad. **MA400 is the closest thing here to a real idea, and it is
still −34.3R in OOS.**

## What this tells the owner, plainly

**The long side can be defended. It is not worth defending, because it was
never the thing making money.**

> Champion IS: longs 273 trades **+272.6R**, shorts 227 trades **+53.2R**.
> Champion OOS: longs 162 trades **+1.8R**, shorts 117 trades **+68.4R**.

**The book earns on longs in IS and on shorts in OOS.** Protecting the
2021 long side costs the 2022 short side and the IS long side both, and
that is a worse trade than the one being hedged.

**This is the same conclusion P78 reached from the other direction** — the
defect is real, causal and reproducible live — **and this run adds the
missing half: there is no cheap way to remove it, because the side it
removes from is larger than the side it protects.**

## Stated limitations

- **A trailing MA is the crudest trend filter there is.** It was chosen
  deliberately, for the reason in the docstring: P55, P67 and P68 all failed
  to separate the eras with swing geometry, volatility and price, so if the
  simplest feature cannot, nothing simpler will. **A better-conditioned
  filter — slope, or an ATR-normalised distance — is untested, and testing
  one now would be searching after seeing these four.**
- **Both lanes are the same data**; the utcsat lane printed and is not
  reproduced here.
- **The partition column is the weakest gate** in this programme (P82) and
  MA400's 7-of-8 should not be read as support.
- **Two harness bugs on the way, both silent**: `mas["ts"]` was missing from
  the dict so the first run kept zero trades and printed "nothing kept" for
  every window, and a `%-14d` format string raised. The first is the
  eighth silent failure this round and the same species as P64's empty book:
  **a run that keeps nothing looks like a result unless you check the count.**

## Status

**Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.**

**And the honest answer to "how do we prevent the long side" is: we can,
and it costs more than it saves — because the book does not actually earn
on the long side outside IS.** Whether the live bot should stand aside
from longs in a live downtrend is a risk decision, not a backtest result,
and this table is the input to it rather than an argument for it.
