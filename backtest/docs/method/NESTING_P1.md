# P1 — nested swing containment, measured before building

> Run 2026-09-29. Harness `exp_nesting.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Closes `method/OPEN_RESEARCH_QUEUE.md` P1.

## The item, and the decision this file makes

The chain is a strict tiling — `btc_swing.py:150` restarts the engine on
the bar after each swing's end extreme, and `walker.py:76
_enforce_alternation` collapses same-kind neighbours into the more extreme
mark, deleting every inner counter-leg. So the system cannot say *"this 15m
pullback sits inside a 15m up-leg that sits inside a 1h up-leg."* Letting
legs nest changes **which marks exist**, so it is not a filter, and it
requires editing both files.

**This file does not do that edit.** It measures containment on the
*existing* chain first, because the falsifier does not need the rebuild —
and because a rebuild moves the control off the pinned 500t/+325.8R, which
would make any negative result uninterpretable against the old book.

Containment here: the 15m swing that produced the trade sits inside the
price range of the 1h leg containing it in time, measured on fine 1m.

**The queue's falsifier, pre-registered and working against us:**

> if the containment cohort is a subset of the one `RANGE_PEAK_GRAY`
> already showed is the book's best (WR 41–42% vs 27.8%), nesting is
> re-discovering range position and fails 4/4 the same way.

---

## Result — the falsifier fires, from the other direction

| WR | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| **CONTAINED** | **29.1%** | **25.9%** | **30.0%** | **27.2%** |
| OUTSIDE | 33.8% | **37.0%** | 33.7% | **37.2%** |
| whole book | 30.0% | 28.0% | 30.8% | 29.6% |

**Containment's win rate is BELOW the book's in all four cells.** Not near
41–42% — below the 27.8% baseline it was supposed to beat.

**And the cohort it would have to beat is the wrong one.** The `OUTSIDE`
cohort is the best in every cell (33.8% / 37.0% / 33.7% / 37.2%) and is
where the OOS P&L actually lives:

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| CONTAINED | +322.3R (419t) | +38.9R (197t) | +352.8R (370t) | +27.4R (173t) |
| OUTSIDE | +2.2R (80t) | **+46.6R** (46t) | +4.9R (83t) | **+46.2R** (43t) |

**In OOS, the non-contained trades carry 66% and 77% of the book.** In IS
they carry nothing. Another era-dependent split, in the opposite direction
from containment.

### Depth within containment does not rescue it

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| inner half (deepest) | +270.6R WR 26.3% | **−4.5R** WR 20.4% | +313.5R WR 29.2% | **−6.7R** WR 22.1% |
| outer half | +52.8R WR 32.1% | +44.4R WR 31.6% | +39.3R WR 30.8% | +35.2R WR 32.6% |

**The deepest contained trades are the worst in OOS in both lanes** —
negative net, WR 20–22%. Deep containment is not a stronger signal, it is
the book being tightly coiled in a range, which is what
`RANGE_PEAK_GRAY` already described.

## Verdict: **do not build it**

The rebuild was expensive — two engine files, a control that moves, and no
way to score a negative against the old book. The cheap pre-test says the
falsifier fires, and not narrowly:

1. **Containment is below the book, 4/4.** It is not the 41–42% cohort.
2. **The cohort that is good is the one nesting would *exclude*** — the
   non-contained trades, which is the opposite of the thesis.
3. **Depth makes it worse, not better** — the deepest contained trades lose
   money OOS in both lanes.

Nesting would have to be built to be refuted, and the evidence says it
would be refuted. **Recorded as closed with the reasoning, not as a
rejected-then-forgotten item** — if someone revisits it, this is why.

## A caveat worth keeping

`NOIV` (no parent interval matched) is 36/279 and 37/253 in OOS, ~1 in 7,
and it is the worst cohort in both lanes (PF 0.52 / 0.60, negative net).
Unrelated to containment, but it is the same ~1-in-7 unmapped fraction seen
in the P3-B oracle run. Recorded, unexplained, not load-bearing here.
