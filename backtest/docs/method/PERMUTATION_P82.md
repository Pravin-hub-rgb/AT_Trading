# P82 — THE PERMUTATION TEST. Directional FS is not significant in any cell.

> Run 2026-09-29. Harness `exp_paired_bootstrap.py`. **NOT ADOPTED. CLOSED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **P80's arms fail the significance test in every cell. There is no third
> result coming, and this is the whole of it.**

## What this had to settle

P80 produced the best-looking result in the round — four of four cells
positive, the period partition passed everywhere (22 wins, 8 losses), both
mirror directions agreeing — and left one test outstanding: whether the
improvement is distinguishable from chance. **It is not.**

The test is a **permutation test** on the trade decomposition, and the
decomposition is exact, asserted per cell rather than assumed:

```
dNet = sum(net(arm) - net(ctl)) over survivors  +  net(NEW)  -  net(DROPPED)
```

**The survivors term is not optional.** Three versions of this harness got
it wrong and each was caught by the assertion:

| version | what it assumed | what the assertion caught |
|---|---|---|
| 1 | survivors cancel exactly | dNet +184.76R vs NEW−DROP +156.17R — a **28.6R** gap |
| 2 | survivors cancel as a **gross** R delta | closed to **1.41R** — the survivor **cost** difference, since a survivor can hold a different number of bars in the two books |
| 3 | survivors cancel as a **net** per-trade delta | **exact on every cell** |

A trade matched on `(entry_ts, direction)` in both books is not the same
trade: the arm's different gating changes the window it sits in, so its exit,
its hold length, and therefore both its R and its costs move. **Survivors
contribute — about +28.6R of the +184.8R.**

## And the null was wrong twice before it was right

The first null resampled NEW and DROPPED independently and subtracted. That
gives a null whose **mean is the observed cohort difference** — +207.8R on
champion IS — so the observed +184.8R sits comfortably inside its own
[+101.4R, +345.7R] band and `p(dNet ≤ 0)` comes out **0.0000**.

**That p-value is meaningless.** It says "both cohorts are profitable", not
"the arm adds anything". A null has to be centred on zero.

**A permutation test is centred on zero by construction**: pool every trade
in NEW, DROPPED and the survivor deltas, keep the three group **sizes**, and
reassign membership at random. Contiguous **blocks** are permuted rather
than individual trades, so serial correlation inside a bias window is not
scrambled — the same objection P63 raised against an IID bootstrap.

## Result

| lane / era | arm | observed dNet | permutation p | verdict |
|---|---|---|---|---|
| champion | IS | **+184.8R** | **0.6895** | not significant |
| champion | IS | **+237.2R** | **0.8590** | not significant |
| champion | OOS | **+172.9R** | **0.9197** | not significant |
| champion | OOS | **+160.3R** | **0.7712** | not significant |
| utcsat | IS | +42.5R | **0.3022** | not significant |

**Not one cell clears p < 0.05. Two are above 0.85 — the strongest possible
form of "the observed result is typical of noise."**

## How +184.8R and p = 0.69 fit together

This is the lesson of the round, so it is worth stating plainly.

The IS decomposition: survivors **+28.6R**, NEW cohort **+337.3R**, DROPPED
cohort **+181.1R**. The arm does not find hidden treasure — it **replaces a
cohort worth +181.1R with one worth +337.3R**. Both are profitable, similar
in shape, from the same market.

**A permutation of that pool produces differences near +184.8R routinely**,
because swapping ~400 similar trades for ~400 similar trades can obviously
land there. The observed figure is roughly the median of what chance does
to a swap of that size.

**The OOS case is sharpest.** There the DROPPED cohort was worth **+2.6R**
and the NEW cohort **+163.7R** — apparently enormous — and p = **0.92**. The
champion's OOS short entries were worth almost nothing, but *any* 253 trades
from that pool beat *any* 223 of them.


## Verdict

**Directional FS is closed.** Four of four cells positive, the partition
passed in every cell, both mirrors agreed — and none of it survives a test
of whether the improvement could have arisen by reshuffling the trades it
was already taking.

**This is not a close call dressed up as a caution.** The period partition
was always the weakest gate here — it compares R/trade between two
correlated books and cannot see a swap of similar cohorts. **The
permutation test asks the right question, and it says no.**

**What P80 actually found, restated honestly:** changing the entry trigger
on one side produces a *different* book with similar per-trade quality and a
somewhat different total, and the difference is inside the noise. The large
dNet numbers were always a difference of two large, similar numbers — which
is what a 500-trade book swapping 400 of its trades produces whether or not
the new trigger carries information.

## Stated limitations

- **20,000 permutations, one seed per block length**, with the **smallest**
  p across L ∈ {10, 20, 40} taken — so the reported p is the most
  *favourable* reading of the block-length choice, not the most
  conservative. The largest p would not change any verdict.
- **Both lanes are the same data**, and the utcsat cells are not independent
  evidence either way.
- **This tests the swap, not the architecture out of sample.** A significant
  result would not have made P80 adoptable either — the era gate and the
  forward pass would still be required.
- **The dropped cohort being worth +2.6R in OOS is itself a finding** about
  the champion's OOS short side, not followed up here.

## Status

**Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.**

**The answer to the owner's original question stands unchanged: the
champion is not replaceable on this evidence, and the live bot trades the
champion.** The long-side defect P78 identified is real, is causal, and is
reproducible live — but this run shows swapping the trigger is not how to
fix it, because the swap is indistinguishable from reshuffling.
