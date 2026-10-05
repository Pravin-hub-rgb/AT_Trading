# P113 — the break-even clamp on the swing ratchet

**Date:** 2026-09-30 · **Branch:** `agents/champion-reality-audit`
**Harness:** `backtest/tests/exp_v19_be.py`

P112 reported that 163 of 313 trail exits (52.1%) close negative, and asked whether
the stop should be forced to entry.

The proposal: *the ratchet sits below entry; put the trail stop at entry, so nothing
can sit between -1R and 0R.*

**Tested. It is much worse, and loses money out of sample. But the proposed
mechanism turned out to be exactly right, which is the more interesting part.**

---

## First: why the negative trails exist at all

From `v19_champion.py` L622–L658:

```python
sl0=sl; sl_cur=sl          # initial stop, below entry
...
cand = swing start_px       # a newly confirmed swing
if sl_cur < cand: sl_cur=cand   # ratchet up
if lo <= sl_cur: exit
```

No break-even clamp. The stop follows swing structure and only crosses entry once
price has actually formed a swing above it. Until then it stays below, so a trade
that never gets going is closed by a trail sitting *slightly tighter than the
original stop* — landing between -1R and 0R.

## The arms

| Arm | Change |
|---|---|
| **A** | champion as-is |
| **B** | every ratchet snaps the stop to entry if it is still below |
| **C** | break-even only after the trade has moved 1.0R in favour |

Patched at all four ratchet sites (coarse long/short, fine long/short), each anchor
asserted to match exactly once.

## The mechanism works exactly as proposed

Instrumenting arm B to record the stop level at each exit:

```
stop was AT entry (clamp fired)        : 69 of 69 paired exits
stop was BELOW entry (clamp never fired):  0
```

**Zero failures.** No trail sat between -1R and entry. The clamp did precisely what
it was asked to do, on every trade it touched.

**And yet arm B still reported 129 negative trails.** Those are not clamp failures.
The stop sits at entry, but the fill is

```python
if lo <= sl_cur_f:
    fill = min(sl_cur_f, float(c["open"]))
```

so when the one-minute bar **opens below the stop**, the fill is the open, not the
stop. A worked example:

```
long   entry 21209.50   stop 21209.50   bar open 21118.50   fill 21118.50
```

91 points below entry inside a single minute, during a cascade. A stop cannot
protect against a gap. This is real and unavoidable, and it is why the count did not
go to zero.

## Results

**IS 2023–2026**

| Arm | n | net | PF | win rate | negative trails |
|---|---|---|---|---|---|
| A champion as-is | 500 | **+325.78R** | **2.384** | 30.0% | 163 |
| B ratchet snaps to entry | 521 | +129.52R | 1.982 | 15.9% | 129 |
| C break-even at +1R MFE | 506 | +65.09R | 1.754 | 19.6% | 95 |

**OOS unseen**

| Arm | n | net | PF | win rate | negative trails |
|---|---|---|---|---|---|
| A champion as-is | 279 | **+70.15R** | **1.591** | 28.0% | 101 |
| B ratchet snaps to entry | 299 | **−44.45R** | 0.962 | 13.4% | 61 |
| C break-even at +1R MFE | 292 | +16.30R | 1.412 | 18.5% | 50 |

## Where the R actually went

Splitting arm A against arm B by sign:

| | n | sum of negatives | sum of positives | winners | ≥3R runners |
|---|---|---|---|---|---|
| A | 500 | −321.81 | **767.03** | 150 | **63** |
| B | 521 | **−254.10** | 503.62 | 83 | 41 |
| Δ | +21 | **+67.71** | **−263.41** | −67 | −22 |

**The clamp does exactly what it promised.** Losing R improves by +67.71. The idea
was not wrong about the mechanics.

**It buys that with −263.41R of winning R.** Runners above 3R fall from 63 to 41, and
the single best trade in the whole set (55.73R) is gone in arm B. Average winner
actually *rises*, 5.11R to 6.07R — the survivors are better, there are just 83 of them
instead of 150.

This strategy funds its 70% failure rate out of a thin tail. Any rule that improves
the losing half by cutting trades off before they run is paying for the losing half
with the only thing that pays the bills.

**Arm B is worse OOS than IS, which is the damning part.** −44.45R at PF 0.962 is not
underperformance, it is no edge out of sample. A change that looks free in-sample and
turns negative out of sample is fitted, not real.

## Decision

**Rejected. The champion keeps its unclamped ratchet.** Arm A stands.

The finding worth keeping: **"the stop is never worse than the original" is
load-bearing.** 163 trades are permitted to close between -1R and 0R precisely so
that the remainder can trail out past +3R. That is a deliberate trade, and P113
quantifies both sides of it.

A secondary finding, not acted on: the stop cannot be assumed to fill at its level.
A one-minute bar opening through it costs real R, and moving the stop closer to
price — as the clamp does — multiplies how often that happens. Worth remembering
whenever a stop is tightened.

## Reproduce

    cd backtest/tests
    python exp_v19_be.py

Roughly a minute: six full simulations across IS and OOS.