# P113 — the break-even clamp on the swing ratchet

**Date:** 2026-09-30 · **Branch:** `agents/champion-reality-audit`
**Harness:** `live_stuff/tests/exp_v19_be.py`

Question that prompted this: P112 reported that 163 of 313 trail exits (52.1%) close
negative, and asked whether the stop should be forced to entry instead.

The proposal, in full: *the ratchet sits below entry; put the trail stop at entry.*

**Tested. It is much worse, and on unseen data it loses money.**

---

## First, why the negative trails exist at all

From `v19_champion.py` L622–L658:

```python
sl0=sl; sl_cur=sl          # initial stop, below entry
...
cand = swing start_px       # a newly confirmed swing
if sl_cur < cand: sl_cur=cand   # ratchet up
if lo <= sl_cur: exit
```

There is no break-even clamp. The stop follows swing structure, and it only crosses
entry once price has actually formed a swing above entry. Until then it stays below,
so a trade that never gets going is closed by a trail that sits *slightly tighter
than the original stop*. That is why those exits land between -1R and 0R.

So the 163 are not a defect. They are the design working as written: **the stop is
allowed to improve without ever being forced forward.**

## The arms

| Arm | Change |
|---|---|
| **A** | champion as-is |
| **B** | every ratchet snaps the stop to entry (`sl_cur = entry` if still below) |
| **C** | break-even only after the trade has moved 1.0R in favour — the standard rule |

Patched at all four ratchet sites (coarse long/short, fine long/short), each anchor
asserted to match exactly once.

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

## Why it fails

The clamp does what it was asked to do — negative trails fall from 163 to 129, and
C reduces them further to 95. The problem is what it costs.

**The win rate collapses: 30.0% → 15.9% in arm B.** Roughly 150 winners become 83.
The clamp does not merely rescue losers, it takes runners out before they run: a
trade that needed to survive a further 0.8R drawdown before ratcheting is closed at
scratch instead, and the +3R tail never arrives.

This strategy pays for its 70% failure rate out of a thin set of runners. Any rule
that improves the average trade by truncating the left tail is trading the only
thing that funds the account for the thing that hurts it.

**Arm B is worse on OOS than on IS, which is the damning part.** −44.45R with a
profit factor of 0.962 means it does not merely underperform, it has no edge out of
sample. A change that looks like a free win in-sample and turns negative out of
sample is the signature of a fitted rule, not a real one.

## Decision

**Rejected. The champion keeps its unclamped ratchet.** Arm A stands.

The finding worth keeping is not that the clamp is bad — it is that **"the stop never
gets worse than the original" is load-bearing.** 163 trades are allowed to close
between -1R and 0R specifically so that the remainder can trail out past +2R. That
trade is deliberate in the engine and should not be "cleaned up" again.

## Reproduce

    cd live_stuff/tests
    python exp_v19_be.py

Roughly a minute: six full simulations across IS and OOS.