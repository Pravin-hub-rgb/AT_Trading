# The cell's edge is a right tail, not a win rate. That is why nothing worked.

Date: 2026-10-07. Engine post-C17. Harness: `exp_cell_full.py`. Single source for
every number here; the earlier harnesses each printed a slice.

Four attempts were made to turn the `chop_HIGH / atr_low` cell into something
tradeable — as a book, as a sleeve, as a filter, as a persist retune. All four
failed. This file is the full metric dump that shows why they were going to fail,
and the one line that explains all of it at once.

## The three objects

Not the same thing, and comparing them carelessly is how the flattering number
gets quoted:

| | what it is |
|---|---|
| **BOOK** | shipping `fsent_champ_long`, `mode="atr_high"` |
| **CELL** | the subset of BOOK's trades that happen in the cell — chop > 58.0 and atrp < 0.65 |
| **GATE** | BOOK rebuilt to take only the cell, `mode="chop_hi_atr_lo_gate"` |
| **UNION** | BOOK plus the cell as extra permission |

CELL is a subset of BOOK. GATE and UNION are the two attempts to act on it.

## IS — 528 trades, +533.4R

| metric | BOOK | CELL | GATE | UNION |
|---|---:|---:|---:|---:|
| n | 528 | **75** | 144 | 531 |
| n_wins / n_losses | 211 / 317 | 34 / 41 | 40 / 104 | 213 / 318 |
| **win rate** | 40.0% | **45.3%** | 27.8% | 40.1% |
| net | +533.4 | +132.0 | +116.0 | +533.5 |
| **mean R** | +1.010 | **+1.760** | +0.806 | +1.005 |
| **median R** | −0.265 | **−0.247** | −1.049 | −0.259 |
| stdR | 4.73 | 6.95 | 5.89 | 4.72 |
| avg win | +3.74 | **+4.96** | +5.73 | +3.71 |
| avg loss | −0.81 | −0.90 | −1.09 | −0.81 |
| payoff | 4.64 | 5.54 | 5.27 | 4.61 |
| **PF** | 3.09 | **4.59** | 2.03 | 3.09 |
| max_dd | 13.4 | **7.6** | **25.2** | 13.4 |
| dd_dur | 22 | **9** | 34 | 22 |
| ulcer | 16.79 | 31.74 | 642.09 | 16.74 |
| sortino | 1.4 | 2.5 | 0.8 | 1.4 |
| calmar | 0.075 | **0.233** | 0.032 | 0.075 |
| max_streak | 11 | **6** | 12 | 11 |
| pos_month % | 71.1 | 58.8 | 39.5 | 71.1 |
| worst_month | −6.8 | −5.6 | −5.8 | −6.8 |
| top5_share % | 80.2 | **68.7** | **134.9** | 80.2 |
| trimmed | 0.298 | 0.653 | **−0.204** | 0.296 |

Per-trade distribution:

| | BOOK | CELL | GATE |
|---|---:|---:|---:|
| median | −0.265 | −0.247 | −1.049 |
| p10 | −1.198 | −1.164 | −1.349 |
| p90 | 4.24 | **5.40** | 4.42 |
| max | 48.64 | 48.64 | 48.64 |
| largest win = % of net | 9.1% | **36.9%** | 41.9% |
| without top 1 | +484.7 | +83.4 | +67.4 |
| without top 3 | +404.0 | +41.3 | +18.0 |
| losses worse than −1R | 166 | 28 | 74 |
| wins above +3R | 72 | 15 | 17 |

## OOS — 311 trades, +239.6R

| metric | BOOK | CELL | GATE | UNION |
|---|---:|---:|---:|---:|
| n | 311 | **42** | 58 | 307 |
| n_wins / n_losses | 115 / 196 | 18 / 24 | 12 / 46 | 109 / 198 |
| **win rate** | 37.0% | **42.9%** | 20.7% | 35.5% |
| net | +239.6 | +109.5 | +37.6 | +217.3 |
| **mean R** | +0.770 | **+2.607** | +0.648 | +0.708 |
| **median R** | −0.224 | **−0.262** | −1.051 | −0.298 |
| stdR | 3.41 | 6.35 | 4.13 | 3.42 |
| avg win | +3.32 | **+7.13** | +6.67 | +3.36 |
| avg loss | −0.72 | −0.79 | −0.92 | −0.75 |
| payoff | 4.58 | **9.06** | 7.23 | 4.46 |
| **PF** | 2.69 | **6.80** | 1.89 | 2.46 |
| max_dd | 11.9 | **4.7** | 11.0 | 13.8 |
| dd_dur | 29 | **5** | 14 | 35 |
| ulcer | 14.23 | 10.20 | 14.99 | 32.65 |
| sortino | 1.1 | 3.9 | 0.7 | 1.0 |
| calmar | 0.065 | **0.551** | 0.059 | 0.051 |
| max_streak | 15 | **5** | 13 | 15 |
| pos_month % | 70.8 | 57.1 | 33.3 | 62.5 |
| worst_month | −8.1 | **−2.3** | −3.5 | −7.7 |
| top5_share % | 81.1 | **41.7** | 100.4 | 89.4 |
| trimmed | 0.236 | **1.744** | 0.047 | 0.159 |

Per-trade distribution:

| | BOOK | CELL | GATE |
|---|---:|---:|---:|
| median | −0.224 | −0.262 | −1.051 |
| p10 | −1.125 | −1.122 | −1.285 |
| p90 | 3.23 | **9.42** | 4.51 |
| max | 26.13 | 26.13 | 19.49 |
| largest win = % of net | 10.9% | **23.9%** | 51.9% |
| without top 1 | +213.5 | +83.4 | +18.1 |
| without top 3 | +172.7 | +45.6 | **−9.6** |
| losses worse than −1R | 94 | 13 | 30 |
| wins above +3R | 33 | 9 | 8 |

## THE LINE THAT EXPLAINS ALL FOUR FAILURES

**The cell's win rate is barely better than the book's. The edge is the right
tail.**

| | BOOK | CELL | gap |
|---|---:|---:|---|
| IS win rate | 40.0% | 45.3% | **+5.3 pts** |
| IS avg win | +3.74R | +4.96R | +1.22R |
| IS **median R** | **−0.265** | **−0.247** | **+0.018** |
| IS p90 | 4.24 | 5.40 | +1.16 |
| OOS win rate | 37.0% | 42.9% | **+5.9 pts** |
| OOS avg win | +3.32R | +7.13R | +3.81R |
| OOS **median R** | **−0.224** | **−0.262** | **−0.038 (worse)** |
| OOS p90 | 3.23 | **9.42** | **+6.19** |

A 5-point win-rate gain is worth something. It is not worth +1.6R of mean IS.
The mean gap comes almost entirely from p90: out of sample the cell's 90th
percentile trade is +9.42R against the book's +3.23R. **The median trade in the
cell is slightly worse than the book's median in both eras** — OOS it is worse,
−0.262 against −0.224.

So the cell does not win more often in any durable sense. It loses at a similar
rate and loses about the same amount (−0.79 vs −0.72 avg loss, essentially
identical), and when it wins it wins much bigger. OOS, 9 of its 42 trades are
above +3R against the book's 33 of 311 — 21% versus 11%.

### Why that defeats all four attempts

| attempt | what a right tail does to it |
|---|---|
| **GATE** (book it) | Needs enough trades to await the tail. 42 OOS trades cannot. Its win rate collapses to 20.7% because the tail is gone, and `without_top3` goes to **−9.6R**. |
| **SLEEVE** (size it) | A tail trade at reduced size delivers reduced R while the fixed losing trades still cost their full weight. 0.65 correlation means no diversification to offset it. |
| **FILTER** (add it) | The additions are −19.0R OOS at persist=7. The tail arrives too rarely to pay for the losing trades that come with it. |
| **PERSIST** (retune it) | Cannot bind on a gate-shaped mode at all — see `CELL_THREE_WAYS.md`. |

Every one of them fails for the same reason, and that reason is visible in one
row: **the cell's edge does not repeat.** A strategy whose median trade is
slightly negative and whose profit is in the top decile is a strategy whose
profit arrives rarely and in size. That is a legitimate thing to own, and it is
exactly the thing that cannot be scaled, diversified, or tested on 42 trades.

It is also worth saying plainly what this does **not** mean. The cell's outlier
bar passes — +83.4R in both eras with the largest trade removed, +41.3R / +45.6R
with the top three removed. It is not carried by one trade. It is carried by
fewer, larger trades, which is a different and more durable thing than the single
outliers that closed ch=50 and ch=55. The finding is real. It just is not a
book, a sleeve, or a filter.

## What would make it one

Not another threshold, and not another weight. Two things:

1. **A sample where the tail recurs often enough to measure.** 42 OOS trades
   with 9 tail events is a small number of large numbers. This is a data problem.
2. **A rule that selects the tail rather than the regime.** The cell selects a
   regime and gets the tail as a side effect. `top5_share_pct` of 68.7 IS / 41.7
   OOS says the tail is present in both eras — which is the strongest thing in
   this entire thread. What is missing is a condition on the *trade* rather than
   on the *bar before it*.

The second is the real research question here, and neither the engine's current
knobs nor any threshold in `chop_thresh` / `atr_high_thresh` answers it.

**Nothing adopted. Shipping config untouched. No pins changed.**